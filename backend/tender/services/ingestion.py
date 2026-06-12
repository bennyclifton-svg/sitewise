"""Document ingestion stage (PRD §7.4 / §9.1). Implemented in Task 8."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import TenderJob


async def ingest_document(session: AsyncSession, job: TenderJob) -> None:
    raise NotImplementedError("ingest_document lands in the next commit")
