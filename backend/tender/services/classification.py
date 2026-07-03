"""Worker handler for document classification."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.llm.client import TenderLLMClient
from tender.models import DOC_TYPES, TenderDocument, TenderPage, TenderQuote
from tender.services import jobs
from tender.services.context import context_for_quote

PROMPT_VERSION = "0.1.0"


async def classify_document(
    session: AsyncSession,
    job,
    *,
    llm_client: TenderLLMClient | None = None,
) -> None:
    llm_client = llm_client or _default_llm_client()
    document_id = uuid.UUID(job.payload["document_id"])
    document = await session.get(TenderDocument, document_id)
    if document is None:
        raise ValueError(f"classify_document: document {document_id} not found")

    page_texts = await _first_page_texts(session, document.id)
    context = await context_for_quote(session, document.quote_id)
    decision = await llm_client.adjudicate(
        "Classify this tender document into one doc_type.",
        list(DOC_TYPES),
        {
            "filename": document.original_filename,
            "first_pages_text": page_texts,
        },
        context,
        prompt_version=PROMPT_VERSION,
        model_key="tender_model_adjudicate_small",
    )

    document.doc_type = decision.choice
    document.classification_confidence = decision.confidence

    quote = await session.get(TenderQuote, document.quote_id)
    if quote is not None:
        quote.stage = "extract_line_items"
    await jobs.enqueue(
        session,
        kind="extract_line_items",
        comparison_id=job.comparison_id,
        quote_id=document.quote_id,
        payload={"document_id": str(document.id)},
    )
    await session.flush()


async def _first_page_texts(session: AsyncSession, document_id: uuid.UUID) -> list[str]:
    result = await session.execute(
        select(TenderPage.text_content)
        .where(TenderPage.document_id == document_id)
        .order_by(TenderPage.page_no)
        .limit(2)
    )
    return list(result.scalars().all())[:2]


def _default_llm_client() -> TenderLLMClient:
    from tender.llm.openai_client import AsyncOpenAITenderClient

    return AsyncOpenAITenderClient()
