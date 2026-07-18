"""Worker handler for the extract_line_items stage."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.llm.client import TenderLLMClient
from tender.models import (
    TenderComparison,
    TenderDocument,
    TenderFlag,
    TenderLineItem,
    TenderPage,
    TenderQuote,
)
from tender.schemas import TenderDocumentPage
from tender.services import extract_cache, jobs, telemetry
from tender.services.context import context_for_quote
from tender.services.extraction import extract_line_items, materialize_extraction


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

    result = None
    if (
        document.content_hash
        and comparison is not None
    ):
        cached = await extract_cache.get_cached_extract(
            session,
            project_id=comparison.project_id,
            content_hash=document.content_hash,
        )
        if cached is not None:
            result = materialize_extraction(
                cached.payload,
                stated_total_cents=stated_total,
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

    await session.execute(
        delete(TenderLineItem).where(TenderLineItem.document_id == document.id)
    )

    for reconciled in result.line_items:
        item = reconciled.item
        session.add(
            TenderLineItem(
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
                item_status=item.item_status,
                allowance_cents=item.allowance_cents,
                extraction_confidence=reconciled.effective_confidence,
            )
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


async def _document_pages(
    session: AsyncSession, document_id: uuid.UUID
) -> list[TenderDocumentPage]:
    result = await session.execute(
        select(TenderPage)
        .where(TenderPage.document_id == document_id)
        .order_by(TenderPage.page_no)
    )
    return [
        TenderDocumentPage(
            document_id=str(page.document_id),
            page_no=page.page_no,
            text_content=page.text_content,
            image_path=page.image_path,
        )
        for page in result.scalars().all()
    ]


def _default_llm_client() -> TenderLLMClient:
    from tender.llm.openai_client import AsyncOpenAITenderClient

    return AsyncOpenAITenderClient()
