"""Worker handler for the extract_line_items stage."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.llm.client import TenderLLMClient
from tender.models import (
    ROLE_TO_ITEM_STATUS,
    TenderComparison,
    TenderDocument,
    TenderFlag,
    TenderLineItem,
    TenderPage,
    TenderQuote,
    TenderQuoteReconciliation,
)
from tender.schemas import TenderDocumentPage
from tender.services import extract_cache, jobs, telemetry
from tender.services.context import context_for_quote
from tender.services.extraction import extract_line_items, materialize_extraction
from tender.services.reconciliation import reconcile_quote


async def extract_line_items_job(
    session: AsyncSession,
    job,
    *,
    llm_client: TenderLLMClient | None = None,
) -> None:
    llm_client = llm_client or _default_llm_client()
    document_id = uuid.UUID(job.payload["document_id"])
    document = await session.get(TenderDocument, document_id)
    if document is None:
        raise ValueError(f"extract_line_items: document {document_id} not found")

    quote = await session.get(TenderQuote, document.quote_id)
    comparison = await session.get(TenderComparison, job.comparison_id)
    stated_total = quote.stated_total_cents if quote is not None else None
    gst_treatment = quote.gst_treatment if quote is not None else "unclear"

    result = None
    if document.content_hash and comparison is not None:
        cached = await extract_cache.get_cached_extract(
            session,
            project_id=comparison.project_id,
            content_hash=document.content_hash,
        )
        if cached is not None:
            result = materialize_extraction(
                cached.payload,
                stated_total_cents=stated_total,
                gst_treatment=gst_treatment,
                model=cached.model or "cache",
                prompt_version=cached.extractor_version,
            )
            usage = telemetry.current_stage_usage()
            if usage is not None:
                usage.cache_hits += 1
                usage.merge_metadata({"extract_cache": "hit"})

    if result is None:
        context = await context_for_quote(session, document.quote_id)
        pages = await _document_pages(session, document.id)
        result = await extract_line_items(
            pages=pages,
            context=context,
            llm_client=llm_client,
            stated_total_cents=stated_total,
            gst_treatment=gst_treatment,
        )
        if document.content_hash and comparison is not None:
            await extract_cache.put_cached_extract(
                session,
                project_id=comparison.project_id,
                content_hash=document.content_hash,
                extractor_version=extract_cache.EXTRACTOR_VERSION,
                payload=result.llm.data,
                model=result.llm.model,
            )
            usage = telemetry.current_stage_usage()
            if usage is not None:
                usage.merge_metadata({"extract_cache": "miss"})

    if (
        quote is not None
        and quote.stated_total_cents is None
        and result.quote_total_cents is not None
    ):
        quote.stated_total_cents = result.quote_total_cents
        quote.stated_total_source = "extracted"
        # Re-run ledger against the backfilled stated total (I2).
        if result.ledger is not None:
            from app.config import settings

            figures = [reconciled.item for reconciled in result.line_items]
            ledger = reconcile_quote(
                figures,
                stated_total_cents=quote.stated_total_cents,
                gst_treatment=quote.gst_treatment,
                tol_ratio=settings.tender_reconciliation_tolerance,
            )
            # Rebuild counted flags on reconciled items from new ledger.
            by_key = {fig.figure_key: fig for fig in ledger.figures}
            result = result.__class__(
                line_items=tuple(
                    reconciled.__class__(
                        item=reconciled.item,
                        qa_state=reconciled.qa_state,
                        effective_confidence=reconciled.effective_confidence,
                        issues=reconciled.issues,
                        counted_in_total=bool(
                            by_key.get(reconciled.item.figure_key)
                            and by_key[reconciled.item.figure_key].counted_in_total
                        ),
                        amount_ex_gst_cents=(
                            by_key[reconciled.item.figure_key].amount_ex_gst_cents
                            if reconciled.item.figure_key in by_key
                            else reconciled.amount_ex_gst_cents
                        ),
                        duplicate_of_figure_key=(
                            by_key[reconciled.item.figure_key].duplicate_of_figure_key
                            if reconciled.item.figure_key in by_key
                            else reconciled.duplicate_of_figure_key
                        ),
                    )
                    for reconciled in result.line_items
                ),
                flags=result.flags,
                llm=result.llm,
                quote_total_cents=result.quote_total_cents,
                ledger=ledger,
                uncaptured=result.uncaptured,
                census_tokens=result.census_tokens,
            )

    await session.execute(
        delete(TenderLineItem).where(TenderLineItem.document_id == document.id)
    )

    key_to_id: dict[str, uuid.UUID] = {
        reconciled.item.figure_key: uuid.uuid4() for reconciled in result.line_items
    }
    pending = {r.item.figure_key: r for r in result.line_items}
    inserted: set[str] = set()
    while pending:
        batch = [
            key
            for key, reconciled in pending.items()
            if not reconciled.item.parent_figure_key
            or reconciled.item.parent_figure_key in inserted
            or reconciled.item.parent_figure_key not in pending
        ]
        if not batch:
            batch = list(pending.keys())
        for key in batch:
            reconciled = pending.pop(key)
            item = reconciled.item
            parent_id = (
                key_to_id.get(item.parent_figure_key)
                if item.parent_figure_key in inserted
                else None
            )
            dup_key = reconciled.duplicate_of_figure_key or item.duplicate_of_figure_key
            duplicate_of_id = key_to_id.get(dup_key) if dup_key in inserted else None
            session.add(
                _line_item_row(
                    row_id=key_to_id[key],
                    document=document,
                    reconciled=reconciled,
                    parent_id=parent_id,
                    duplicate_of_id=duplicate_of_id,
                )
            )
            inserted.add(key)

    if quote is not None and result.ledger is not None:
        await _upsert_reconciliation(
            session,
            quote=quote,
            comparison_id=job.comparison_id,
            ledger=result.ledger,
            uncaptured=list(result.uncaptured),
        )

    for flag in result.flags:
        session.add(
            TenderFlag(
                comparison_id=job.comparison_id,
                quote_id=document.quote_id,
                flag_type=flag.flag_type,
                severity=flag.severity,
                headline=flag.headline,
                detail=flag.detail,
                include_in_report=flag.flag_type == "unreconciled_residual",
                evidence={
                    "document_id": str(document.id),
                    "page_no": flag.page_no,
                    "expected_cents": flag.expected_cents,
                    "actual_cents": flag.actual_cents,
                    "delta_ratio": flag.delta_ratio,
                },
            )
        )

    if quote is not None:
        quote.stage = "embed_items"
    await jobs.enqueue(
        session,
        kind="embed_items",
        comparison_id=job.comparison_id,
        quote_id=document.quote_id,
        payload={"document_id": str(document.id)},
    )
    await session.flush()


def _line_item_row(
    *,
    row_id: uuid.UUID,
    document: TenderDocument,
    reconciled,
    parent_id: uuid.UUID | None,
    duplicate_of_id: uuid.UUID | None,
) -> TenderLineItem:
    item = reconciled.item
    role = item.role
    item_status = item.item_status or ROLE_TO_ITEM_STATUS.get(role, "included")
    return TenderLineItem(
        id=row_id,
        quote_id=document.quote_id,
        document_id=document.id,
        page_no=item.page_no,
        bbox=item.bbox.model_dump() if item.bbox else None,
        description_raw=item.description_raw,
        section_path=item.section_path or None,
        qty=item.qty,
        unit=item.unit,
        rate_cents=item.rate_cents,
        amount_cents=item.amount_cents,
        item_status=item_status,
        allowance_cents=item.allowance_cents,
        extraction_confidence=reconciled.effective_confidence,
        parent_id=parent_id,
        role=role,
        is_rollup=bool(item.is_rollup),
        duplicate_of_id=duplicate_of_id,
        gst_basis=item.gst_basis,
        amount_ex_gst_cents=reconciled.amount_ex_gst_cents,
        counted_in_total=bool(reconciled.counted_in_total),
        figure_key=item.figure_key,
    )


async def _upsert_reconciliation(
    session: AsyncSession,
    *,
    quote: TenderQuote,
    comparison_id: uuid.UUID,
    ledger,
    uncaptured: list,
) -> None:
    existing = await session.scalar(
        select(TenderQuoteReconciliation).where(
            TenderQuoteReconciliation.quote_id == quote.id
        )
    )
    if existing is None:
        existing = TenderQuoteReconciliation(
            quote_id=quote.id,
            comparison_id=comparison_id,
            status=ledger.status,
        )
        session.add(existing)
    existing.comparison_id = comparison_id
    existing.stated_total_cents = quote.stated_total_cents
    existing.stated_basis = ledger.stated_basis
    existing.gst_line_cents = ledger.gst_line_cents
    existing.counted_total_cents = ledger.counted_total_cents
    existing.computed_ex_gst_cents = ledger.computed_ex_gst_cents
    existing.residual_cents = ledger.residual_cents
    existing.status = ledger.status
    existing.checks = list(ledger.checks)
    existing.uncaptured = uncaptured


async def _document_pages(
    session: AsyncSession, document_id: uuid.UUID
) -> list[TenderDocumentPage]:
    pages = (
        await session.scalars(
            select(TenderPage)
            .where(TenderPage.document_id == document_id)
            .order_by(TenderPage.page_no)
        )
    ).all()
    return [
        TenderDocumentPage(
            document_id=str(document_id),
            page_no=page.page_no,
            text_content=page.text_content,
            image_path=page.image_path,
        )
        for page in pages
    ]


def _default_llm_client() -> TenderLLMClient:
    from tender.llm.openai_client import AsyncOpenAITenderClient

    return AsyncOpenAITenderClient()
