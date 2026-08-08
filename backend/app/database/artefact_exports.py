"""Persistence helpers for immutable artefact export cache entries."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.artefact_export import ArtefactExport


async def get_artefact_export(
    session: AsyncSession,
    *,
    draft_id: uuid.UUID,
    export_type: str,
) -> ArtefactExport | None:
    result = await session.execute(
        select(ArtefactExport).where(
            ArtefactExport.draft_id == draft_id,
            ArtefactExport.export_type == export_type,
        )
    )
    return result.scalar_one_or_none()


async def cache_ready_artefact_export(
    session: AsyncSession,
    *,
    current: ArtefactExport | None,
    project_id: uuid.UUID,
    draft_id: uuid.UUID,
    revision: int,
    export_type: str,
    workspace_path: str,
    storage_key: str,
    content_hash: str,
) -> ArtefactExport:
    record = current or ArtefactExport(
        project_id=project_id,
        draft_id=draft_id,
        revision=revision,
        export_type=export_type,
        workspace_path=workspace_path,
        storage_key=storage_key,
    )
    if current is None:
        session.add(record)
    record.revision = revision
    record.workspace_path = workspace_path
    record.storage_key = storage_key
    record.status = "ready"
    record.content_hash = content_hash
    record.error = None
    record.attempt_count = (record.attempt_count or 0) + 1
    await session.flush()
    return record
