from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.source_document import SourceDocument
from app.web_research.nsw_legislation import instrument_id_from_url
from app.web_research.service import WebSource, _bounded_excerpt

OFFICIAL_ATTACHMENT_MAX_AGE_DAYS = 7


def official_relative_path(url: str) -> str:
    instrument_id = instrument_id_from_url(url)
    if instrument_id:
        return f"official/{instrument_id}"
    name = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1] or "instrument"
    slug = re.sub(r"[^a-z0-9._-]+", "-", name.casefold()).strip("-")
    return f"official/{slug or 'instrument'}"


async def find_official_attachment(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    url: str,
    max_age_days: int | None = OFFICIAL_ATTACHMENT_MAX_AGE_DAYS,
) -> SourceDocument | None:
    document = (
        await session.execute(
            select(SourceDocument).where(
                SourceDocument.project_id == project_id,
                SourceDocument.relative_path == official_relative_path(url),
            )
        )
    ).scalar_one_or_none()
    if document is None:
        return None
    metadata = document.document_metadata or {}
    if metadata.get("knowledge_scope") != "official":
        return None
    if max_age_days is None:
        return document
    retrieved_at = _parsed_retrieved_at(metadata.get("retrieved_at"))
    if retrieved_at is None:
        return None
    if datetime.now(UTC) - retrieved_at > timedelta(days=max_age_days):
        return None
    return document


async def persist_official_attachment(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    project_slug: str,
    source: WebSource,
    text: str,
) -> SourceDocument:
    existing = await find_official_attachment(
        session,
        project_id=project_id,
        url=source.url,
        max_age_days=None,
    )
    previous_hash = existing.content_hash if existing is not None else None
    metadata = _official_metadata(source, previous_hash=previous_hash)
    if existing is not None:
        existing.source_type = "reference"
        existing.document_class = "planning_instrument"
        existing.document_type = "planning_instrument"
        existing.ingest_mode = "full_text"
        existing.filename = source.title[:512]
        existing.normalized_content = text
        existing.content_hash = source.content_hash
        existing.document_metadata = metadata
        return existing

    document = SourceDocument(
        project_id=project_id,
        project=project_slug,
        phase="reference",
        document_type="planning_instrument",
        document_class="planning_instrument",
        ingest_mode="full_text",
        document_metadata=metadata,
        content_hash=source.content_hash,
        source_type="reference",
        filename=source.title[:512],
        relative_path=official_relative_path(source.url),
        normalized_content=text,
    )
    session.add(document)
    await session.flush()
    return document


def web_source_from_attachment(
    document: Any,
    *,
    section_hint: str | None = None,
) -> WebSource:
    metadata = document.document_metadata or {}
    text = document.normalized_content or ""
    return WebSource(
        url=str(metadata.get("official_url") or ""),
        title=str(document.filename or metadata.get("title") or "Official instrument"),
        publisher=str(metadata.get("publisher") or ""),
        jurisdiction=str(metadata.get("jurisdiction") or ""),
        authority_class=str(metadata.get("authority_class") or "government_guidance"),
        source_type=str(metadata.get("source_type") or "web_reference"),
        version_status=str(metadata.get("version_status") or "unknown"),
        effective_date=metadata.get("effective_date")
        if isinstance(metadata.get("effective_date"), str)
        else None,
        section=section_hint,
        excerpt=_bounded_excerpt(text, section_hint=section_hint),
        content_hash=str(document.content_hash or ""),
        retrieved_at=str(metadata.get("retrieved_at") or ""),
    )


def _official_metadata(source: WebSource, *, previous_hash: str | None) -> dict[str, str]:
    metadata = {
        "knowledge_scope": "official",
        "official_url": source.url,
        "publisher": source.publisher,
        "jurisdiction": source.jurisdiction,
        "authority_class": source.authority_class,
        "source_type": source.source_type,
        "version_status": source.version_status,
        "retrieved_at": source.retrieved_at,
    }
    if source.effective_date:
        metadata["effective_date"] = source.effective_date
    if previous_hash:
        metadata["previous_content_hash"] = previous_hash
    return metadata


def _parsed_retrieved_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
