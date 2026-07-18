"""Project-scoped extract cache keyed by (project_id, content_hash, extractor_version)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.llm.openai_client import PROMPT_VERSION
from tender.models import TenderExtractCache

EXTRACTOR_VERSION = PROMPT_VERSION


async def get_cached_extract(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    content_hash: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> TenderExtractCache | None:
    result = await session.execute(
        select(TenderExtractCache)
        .where(
            TenderExtractCache.project_id == project_id,
            TenderExtractCache.content_hash == content_hash,
            TenderExtractCache.extractor_version == extractor_version,
        )
        .limit(1)
    )
    return result.scalars().first()


async def put_cached_extract(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    content_hash: str,
    payload: dict[str, Any],
    model: str | None = None,
    extractor_version: str = EXTRACTOR_VERSION,
) -> TenderExtractCache:
    existing = await get_cached_extract(
        session,
        project_id=project_id,
        content_hash=content_hash,
        extractor_version=extractor_version,
    )
    if existing is not None:
        existing.payload = payload
        existing.model = model
        await session.flush()
        return existing

    row = TenderExtractCache(
        project_id=project_id,
        content_hash=content_hash,
        extractor_version=extractor_version,
        payload=payload,
        model=model,
    )
    session.add(row)
    await session.flush()
    return row
