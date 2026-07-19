from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from app.config import settings
from tender.llm.client import LLMExtractionResponse, TenderLLMClient
from tender.schemas import (
    ExtractedLineItem,
    ExtractionStructuredOutput,
    ProjectContext,
    TenderDocumentPage,
)

QAState = Literal["auto_pass", "needs_review"]


@dataclass(frozen=True)
class ExtractionFlag:
    flag_type: Literal["arithmetic_inconsistency"]
    severity: Literal["warning"]
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


@dataclass(frozen=True)
class ExtractionResult:
    line_items: tuple[ReconciledLineItem, ...]
    flags: tuple[ExtractionFlag, ...]
    llm: LLMExtractionResponse
    quote_total_cents: int | None = None


async def extract_line_items(
    *,
    pages: Sequence[TenderDocumentPage],
    context: ProjectContext,
    llm_client: TenderLLMClient,
    stated_total_cents: int | None = None,
    confidence_threshold: float | None = None,
    reconciliation_tolerance: float | None = None,
) -> ExtractionResult:
    schema = ExtractionStructuredOutput.model_json_schema()
    llm_response = await llm_client.extract(pages, schema, context)
    return materialize_extraction(
        llm_response.data,
        stated_total_cents=stated_total_cents,
        confidence_threshold=confidence_threshold,
        reconciliation_tolerance=reconciliation_tolerance,
        model=llm_response.model,
        prompt_version=llm_response.prompt_version,
        request_id=llm_response.request_id,
    )


def materialize_extraction(
    data: dict[str, Any],
    *,
    stated_total_cents: int | None = None,
    confidence_threshold: float | None = None,
    reconciliation_tolerance: float | None = None,
    model: str = "cache",
    prompt_version: str = "0.1.0",
    request_id: str | None = None,
) -> ExtractionResult:
    """Reconcile + gate a structured extract payload (LLM or cache hit)."""
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
    quote_total = (
        structured.quote_total_cents
        if stated_total_cents is None
        else stated_total_cents
    )
    flags = _reconcile(structured, quote_total, tolerance)
    flagged_pages = {
        flag.page_no
        for flag in flags
        if flag.scope == "page" and flag.page_no is not None
    }
    quote_has_issue = any(flag.scope == "quote" for flag in flags)

    reconciled = tuple(
        _gate_item(
            item,
            threshold=threshold,
            page_has_issue=item.page_no in flagged_pages,
            quote_has_issue=quote_has_issue,
        )
        for item in structured.line_items
    )
    return ExtractionResult(
        line_items=reconciled,
        flags=tuple(flags),
        llm=llm_response,
        quote_total_cents=structured.quote_total_cents,
    )


def _reconcile(
    structured: ExtractionStructuredOutput,
    stated_total_cents: int | None,
    tolerance: float,
) -> list[ExtractionFlag]:
    flags: list[ExtractionFlag] = []
    for subtotal in structured.page_subtotals:
        actual = sum(
            item.amount_cents or 0
            for item in structured.line_items
            if item.page_no == subtotal.page_no
        )
        if _outside_tolerance(subtotal.amount_cents, actual, tolerance):
            flags.append(
                _flag(
                    scope="page",
                    page_no=subtotal.page_no,
                    expected_cents=subtotal.amount_cents,
                    actual_cents=actual,
                    label=f"page {subtotal.page_no} subtotal",
                )
            )

    if stated_total_cents is not None:
        actual = sum(item.amount_cents or 0 for item in structured.line_items)
        if _outside_tolerance(stated_total_cents, actual, tolerance):
            flags.append(
                _flag(
                    scope="quote",
                    page_no=None,
                    expected_cents=stated_total_cents,
                    actual_cents=actual,
                    label="quote total",
                )
            )
    return flags


def _gate_item(
    item: ExtractedLineItem,
    *,
    threshold: float,
    page_has_issue: bool,
    quote_has_issue: bool,
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
    )


def _flag(
    *,
    scope: Literal["page", "quote"],
    page_no: int | None,
    expected_cents: int,
    actual_cents: int,
    label: str,
) -> ExtractionFlag:
    delta_ratio = _delta_ratio(expected_cents, actual_cents)
    return ExtractionFlag(
        flag_type="arithmetic_inconsistency",
        severity="warning",
        scope=scope,
        headline="Arithmetic inconsistency",
        detail=(
            f"Extracted item amounts do not reconcile to the printed {label} "
            f"within the configured tolerance."
        ),
        page_no=page_no,
        expected_cents=expected_cents,
        actual_cents=actual_cents,
        delta_ratio=delta_ratio,
    )


def _outside_tolerance(expected_cents: int, actual_cents: int, tolerance: float) -> bool:
    return _delta_ratio(expected_cents, actual_cents) > tolerance


def _delta_ratio(expected_cents: int, actual_cents: int) -> float:
    if expected_cents == 0:
        return 0.0 if actual_cents == 0 else 1.0
    return abs(actual_cents - expected_cents) / abs(expected_cents)
