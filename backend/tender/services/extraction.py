"""Windowed, census-verified line-item extraction (I1) + ledger reconcile (I2)."""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from app.config import settings
from tender.llm.client import LLMExtractionResponse, TenderLLMClient
from tender.schemas import (
    ExtractedLineItem,
    ExtractionStructuredOutput,
    ProjectContext,
    TenderDocumentPage,
)
from tender.services.census import CensusToken, census_page
from tender.services.reconciliation import LedgerResult, reconcile_quote

QAState = Literal["auto_pass", "needs_review"]
WINDOW_SIZE = 4
WINDOW_OVERLAP = 1


@dataclass(frozen=True)
class ExtractionFlag:
    flag_type: Literal[
        "arithmetic_inconsistency",
        "unreconciled_residual",
        "suspect_number_format",
    ]
    severity: Literal["warning", "caution"]
    scope: Literal["page", "quote"]
    headline: str
    detail: str
    page_no: int | None = None
    expected_cents: int | None = None
    actual_cents: int | None = None
    delta_ratio: float | None = None


@dataclass(frozen=True)
class ReconciledLineItem:
    item: ExtractedLineItem
    qa_state: QAState
    effective_confidence: float
    issues: tuple[str, ...]
    counted_in_total: bool = False
    amount_ex_gst_cents: int | None = None
    duplicate_of_figure_key: str | None = None


@dataclass(frozen=True)
class ExtractionResult:
    line_items: tuple[ReconciledLineItem, ...]
    flags: tuple[ExtractionFlag, ...]
    llm: LLMExtractionResponse
    quote_total_cents: int | None = None
    ledger: LedgerResult | None = None
    uncaptured: tuple[dict[str, Any], ...] = ()
    census_tokens: tuple[CensusToken, ...] = ()


def window_pages(
    pages: Sequence[TenderDocumentPage],
    *,
    size: int = WINDOW_SIZE,
    overlap: int = WINDOW_OVERLAP,
) -> list[list[TenderDocumentPage]]:
    ordered = sorted(pages, key=lambda p: p.page_no)
    if not ordered:
        return []
    step = max(1, size - overlap)
    windows: list[list[TenderDocumentPage]] = []
    for start in range(0, len(ordered), step):
        chunk = list(ordered[start : start + size])
        if not chunk:
            break
        if windows and chunk == windows[-1]:
            break
        windows.append(chunk)
        if start + size >= len(ordered):
            break
    return windows


def merge_window_figures(
    window_outputs: Sequence[ExtractionStructuredOutput],
) -> list[ExtractedLineItem]:
    """Merge by figure_key; later windows win on overlap pages."""
    by_key: dict[str, ExtractedLineItem] = {}
    for output in window_outputs:
        for item in output.line_items:
            by_key[item.figure_key] = item
    return list(by_key.values())


def _cents_multiset(items: Sequence[ExtractedLineItem], page_no: int) -> Counter[int]:
    return Counter(
        item.amount_cents
        for item in items
        if item.page_no == page_no and item.amount_cents is not None
    )


def missing_census_tokens(
    tokens: Sequence[CensusToken],
    items: Sequence[ExtractedLineItem],
) -> list[CensusToken]:
    missing: list[CensusToken] = []
    by_page: dict[int, list[CensusToken]] = {}
    for token in tokens:
        by_page.setdefault(token.page_no, []).append(token)
    for page_no, page_tokens in by_page.items():
        extracted = _cents_multiset(items, page_no)
        for token in page_tokens:
            if extracted[token.cents] > 0:
                extracted[token.cents] -= 1
            else:
                missing.append(token)
    return missing


async def extract_line_items(
    *,
    pages: Sequence[TenderDocumentPage],
    context: ProjectContext,
    llm_client: TenderLLMClient,
    stated_total_cents: int | None = None,
    gst_treatment: str = "unclear",
    confidence_threshold: float | None = None,
    reconciliation_tolerance: float | None = None,
) -> ExtractionResult:
    schema = ExtractionStructuredOutput.model_json_schema()
    threshold = (
        settings.tender_extraction_confidence_threshold
        if confidence_threshold is None
        else confidence_threshold
    )
    tolerance = (
        settings.tender_reconciliation_tolerance
        if reconciliation_tolerance is None
        else reconciliation_tolerance
    )
    concurrency = max(1, settings.tender_extraction_concurrency)
    semaphore = asyncio.Semaphore(concurrency)

    census_tokens = tuple(
        token
        for page in pages
        for token in census_page(page.text_content, page.page_no)
    )
    windows = window_pages(pages)
    prior_headings: list[str] = []
    window_outputs: list[ExtractionStructuredOutput] = []
    last_llm: LLMExtractionResponse | None = None

    async def _call_window(
        window: list[TenderDocumentPage],
        *,
        headings: Sequence[str],
        page_images: Sequence[bytes] | None = None,
        already_found: Sequence[dict[str, Any]] | None = None,
        reextract_hint: str | None = None,
    ) -> LLMExtractionResponse:
        async with semaphore:
            return await llm_client.extract(
                window,
                schema,
                context,
                page_images=page_images,
                prior_section_headings=list(headings) or None,
                already_found=already_found,
                reextract_hint=reextract_hint,
            )

    # Sequential windows so prior headings accumulate; LLM calls still
    # semaphore-limited if we later fan-out retries.
    for window in windows:
        response = await _call_window(window, headings=prior_headings)
        last_llm = response
        structured = ExtractionStructuredOutput.model_validate(response.data)
        window_outputs.append(structured)
        for item in structured.line_items:
            if item.is_rollup and item.description_raw:
                prior_headings.append(item.description_raw)

    merged = merge_window_figures(window_outputs)
    quote_total = None
    for output in window_outputs:
        if output.quote_total_cents is not None:
            quote_total = output.quote_total_cents

    missing = missing_census_tokens(census_tokens, merged)
    pages_by_no = {page.page_no: page for page in pages}
    retried_pages: set[int] = set()
    for token in missing:
        if token.page_no in retried_pages:
            continue
        retried_pages.add(token.page_no)
        page = pages_by_no.get(token.page_no)
        if page is None:
            continue
        page_items = [item for item in merged if item.page_no == page.page_no]
        page_tokens = [t for t in census_tokens if t.page_no == page.page_no]
        images: list[bytes] | None = None
        if len(page_tokens) > 3 * max(1, len(page_items)):
            images = _load_page_images([page])
        response = await _call_window(
            [page],
            headings=prior_headings,
            page_images=images,
            already_found=[
                {
                    "figure_key": item.figure_key,
                    "printed_text": item.printed_text,
                    "amount_cents": item.amount_cents,
                }
                for item in page_items
            ],
            reextract_hint=(
                "every $ figure on this page; here are the ones already found; "
                "find the rest"
            ),
        )
        last_llm = response
        structured = ExtractionStructuredOutput.model_validate(response.data)
        # Prefer re-extract figures for this page.
        merged = [item for item in merged if item.page_no != page.page_no]
        merged.extend(structured.line_items)
        if structured.quote_total_cents is not None:
            quote_total = structured.quote_total_cents

    still_missing = missing_census_tokens(census_tokens, merged)
    uncaptured = tuple(
        {
            "page_no": token.page_no,
            "raw": token.raw,
            "context": token.context,
            "cents": token.cents,
        }
        for token in still_missing
    )

    effective_stated = (
        stated_total_cents if stated_total_cents is not None else quote_total
    )
    ledger = reconcile_quote(
        merged,
        stated_total_cents=effective_stated,
        gst_treatment=gst_treatment,
        tol_ratio=tolerance,
    )
    ledger_by_key = {fig.figure_key: fig for fig in ledger.figures}

    flags = _flags_from_ledger(ledger, census_tokens, tolerance)
    quote_has_issue = any(flag.scope == "quote" for flag in flags)
    flagged_pages = {
        flag.page_no for flag in flags if flag.scope == "page" and flag.page_no is not None
    }

    reconciled = tuple(
        _gate_item(
            item,
            threshold=threshold,
            page_has_issue=item.page_no in flagged_pages,
            quote_has_issue=quote_has_issue,
            ledger_node=ledger_by_key.get(item.figure_key),
        )
        for item in merged
    )

    if last_llm is None:
        last_llm = LLMExtractionResponse(
            data={"line_items": [], "page_subtotals": [], "quote_total_cents": quote_total},
            model="none",
            prompt_version="0.2.0",
        )
    else:
        last_llm = LLMExtractionResponse(
            data={
                "line_items": [item.model_dump(mode="json") for item in merged],
                "page_subtotals": [],
                "quote_total_cents": quote_total,
            },
            model=last_llm.model,
            prompt_version=last_llm.prompt_version,
            request_id=last_llm.request_id,
        )

    return ExtractionResult(
        line_items=reconciled,
        flags=tuple(flags),
        llm=last_llm,
        quote_total_cents=quote_total,
        ledger=ledger,
        uncaptured=uncaptured,
        census_tokens=census_tokens,
    )


def materialize_extraction(
    data: dict[str, Any],
    *,
    stated_total_cents: int | None = None,
    gst_treatment: str = "unclear",
    confidence_threshold: float | None = None,
    reconciliation_tolerance: float | None = None,
    model: str = "cache",
    prompt_version: str = "0.2.0",
    request_id: str | None = None,
) -> ExtractionResult:
    """Reconcile + gate a structured extract payload (cache hit path)."""
    threshold = (
        settings.tender_extraction_confidence_threshold
        if confidence_threshold is None
        else confidence_threshold
    )
    tolerance = (
        settings.tender_reconciliation_tolerance
        if reconciliation_tolerance is None
        else reconciliation_tolerance
    )
    llm_response = LLMExtractionResponse(
        data=data,
        model=model,
        prompt_version=prompt_version,
        request_id=request_id,
    )
    structured = ExtractionStructuredOutput.model_validate(llm_response.data)
    effective_stated = (
        stated_total_cents
        if stated_total_cents is not None
        else structured.quote_total_cents
    )
    ledger = reconcile_quote(
        list(structured.line_items),
        stated_total_cents=effective_stated,
        gst_treatment=gst_treatment,
        tol_ratio=tolerance,
    )
    ledger_by_key = {fig.figure_key: fig for fig in ledger.figures}
    flags = _flags_from_ledger(ledger, (), tolerance)
    quote_has_issue = any(flag.scope == "quote" for flag in flags)
    reconciled = tuple(
        _gate_item(
            item,
            threshold=threshold,
            page_has_issue=False,
            quote_has_issue=quote_has_issue,
            ledger_node=ledger_by_key.get(item.figure_key),
        )
        for item in structured.line_items
    )
    return ExtractionResult(
        line_items=reconciled,
        flags=tuple(flags),
        llm=llm_response,
        quote_total_cents=structured.quote_total_cents,
        ledger=ledger,
        uncaptured=(),
        census_tokens=(),
    )


def _flags_from_ledger(
    ledger: LedgerResult,
    census_tokens: Sequence[CensusToken],
    tolerance: float,
) -> list[ExtractionFlag]:
    flags: list[ExtractionFlag] = []
    for check in ledger.checks:
        delta = abs(int(check.get("delta_cents") or 0))
        printed = int(check.get("printed_cents") or 0)
        if printed and (delta / abs(printed)) > tolerance:
            flags.append(
                ExtractionFlag(
                    flag_type="arithmetic_inconsistency",
                    severity="warning",
                    scope="page",
                    headline="Arithmetic inconsistency",
                    detail=(
                        f"Rollup {check.get('figure_key')} does not match child sum "
                        f"(delta {delta} cents)."
                    ),
                    page_no=None,
                    expected_cents=printed,
                    actual_cents=int(check.get("child_sum_cents") or 0),
                    delta_ratio=delta / abs(printed),
                )
            )
    if ledger.status == "residual" and ledger.residual_cents != 0:
        flags.append(
            ExtractionFlag(
                flag_type="unreconciled_residual",
                severity="warning",
                scope="quote",
                headline="Unreconciled residual",
                detail=(
                    "Counted figures do not reconcile to the stated total within "
                    "tolerance; residual retained on the ledger."
                ),
                expected_cents=None,
                actual_cents=ledger.counted_total_cents,
                delta_ratio=None,
            )
        )
    for token in census_tokens:
        if token.suspect_format:
            flags.append(
                ExtractionFlag(
                    flag_type="suspect_number_format",
                    severity="caution",
                    scope="page",
                    headline="Suspect number format",
                    detail=f"Malformed currency grouping near {token.raw!r}.",
                    page_no=token.page_no,
                )
            )
    return flags


def _gate_item(
    item: ExtractedLineItem,
    *,
    threshold: float,
    page_has_issue: bool,
    quote_has_issue: bool,
    ledger_node: Any | None,
) -> ReconciledLineItem:
    issues: list[str] = []
    effective_confidence = item.extraction_confidence
    if page_has_issue:
        issues.append("page_reconciliation_mismatch")
        effective_confidence = min(effective_confidence, 0.5)
    if quote_has_issue:
        issues.append("quote_reconciliation_mismatch")
        effective_confidence = min(effective_confidence, 0.5)
    if effective_confidence < threshold:
        issues.append("low_extraction_confidence")

    return ReconciledLineItem(
        item=item,
        qa_state="auto_pass" if not issues else "needs_review",
        effective_confidence=effective_confidence,
        issues=tuple(issues),
        counted_in_total=bool(getattr(ledger_node, "counted_in_total", False)),
        amount_ex_gst_cents=getattr(ledger_node, "amount_ex_gst_cents", None),
        duplicate_of_figure_key=getattr(ledger_node, "duplicate_of_figure_key", None)
        or item.duplicate_of_figure_key,
    )


def _load_page_images(pages: Sequence[TenderDocumentPage]) -> list[bytes] | None:
    images: list[bytes] = []
    for page in pages:
        if not page.image_path:
            return None
        path = Path(page.image_path)
        if not path.is_file():
            return None
        images.append(path.read_bytes())
    return images or None
