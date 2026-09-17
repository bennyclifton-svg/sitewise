"""Identify submission issuers from canonical document text without changing the strategy."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Literal

import structlog
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.source_document import SourceDocument
from app.procurement.candidate_submissions import resolve_submission_files

logger = structlog.get_logger(__name__)
_PROMPT = Path(__file__).with_name("prompts") / "submission_identity_v1.txt"


class IdentifyFirmRequest(BaseModel):
    workspace_file_ids: list[uuid.UUID] = Field(min_length=1, max_length=30)


class FirmIdentity(BaseModel):
    status: Literal["identified", "needs_name", "different_firms"]
    company_name: str | None = None
    message: str | None = None


class DocumentIssuer(BaseModel):
    file_id: str
    company_name: str | None
    evidence_quote: str | None


class SubmissionIssuers(BaseModel):
    documents: list[DocumentIssuer]


async def extract_identities(documents: dict[str, str]) -> SubmissionIssuers | None:
    async with AsyncOpenAI(api_key=settings.openai_api_key, max_retries=0) as client:
        response = await client.responses.parse(
            model=settings.openai_chat_model,
            instructions=_PROMPT.read_text(encoding="utf-8"),
            input=json.dumps(documents),
            text_format=SubmissionIssuers,
            max_output_tokens=4000,
            timeout=20.0,
            store=False,
        )
    return response.output_parsed


def _normalized(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold()))


async def identify_submission_firm(
    session: AsyncSession, *, project_id: uuid.UUID, file_ids: list[uuid.UUID]
) -> FirmIdentity:
    files = await resolve_submission_files(session, project_id=project_id, file_ids=file_ids)
    result = await session.execute(
        select(SourceDocument).where(
            SourceDocument.project_id == project_id,
            SourceDocument.id.in_([file.source_document_id for file in files]),
        )
    )
    sources = {source.id: source for source in result.scalars().all()}
    documents: dict[str, str] = {}
    # Bound the request while retaining letterheads and signatures on long submissions.
    limit = min(12000, 48000 // len(files))
    for file in files:
        source = sources.get(file.source_document_id)
        if not source or not source.normalized_content.strip() or file.ingest_status != "ingested":
            return FirmIdentity(
                status="needs_name",
                message="Document text is not ready. Enter the firm name, or try again after processing.",
            )
        content = source.normalized_content
        documents[str(file.id)] = (
            content if len(content) <= limit
            else content[:limit * 3 // 4] + "\n[Middle omitted]\n" + content[-limit // 4:]
        )
    fallback = FirmIdentity(
        status="needs_name", message="The submitting firm is unclear. Enter its name to link these documents."
    )
    try:
        extracted = await extract_identities(documents)
    except (OpenAIError, ValidationError) as exc:
        logger.warning("submission_identity_failed", error_type=type(exc).__name__)
        return FirmIdentity(status="needs_name", message="Could not identify the firm. Enter its name, or try again.")
    if not extracted or len(extracted.documents) != len(documents):
        return fallback
    if {item.file_id for item in extracted.documents} != set(documents):
        return fallback
    names: dict[str, str] = {}
    unresolved = False
    for item in extracted.documents:
        name = " ".join((item.company_name or "").split())
        quote = _normalized(item.evidence_quote or "")
        if (
            not name or len(name) > 512 or not quote
            or not _normalized(name) or f" {_normalized(name)} " not in f" {quote} "
            or f" {quote} " not in f" {_normalized(documents[item.file_id])} "
        ):
            unresolved = True
            continue
        names[_normalized(name)] = name
    if len(names) > 1:
        return FirmIdentity(
            status="different_firms",
            message="These documents identify different firms. Select documents for one firm at a time.",
        )
    if unresolved or not names:
        return fallback
    return FirmIdentity(status="identified", company_name=next(iter(names.values())))
