"""Canonical project files linked to a procurement firm; no ingestion side effects."""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.workspace_file import WorkspaceFile
from app.procurement.strategy import ProcurementStrategyValidationError

SUBMISSION_SUFFIXES = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".md",
    ".markdown",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
}


async def resolve_submission_files(
    session: AsyncSession, *, project_id: uuid.UUID, file_ids: list[uuid.UUID]
) -> list[WorkspaceFile]:
    if len(file_ids) > 30 or len(file_ids) != len(set(file_ids)):
        raise ProcurementStrategyValidationError(
            "Select up to 30 unique files per firm"
        )
    if not file_ids:
        return []
    result = await session.execute(
        select(WorkspaceFile).where(
            WorkspaceFile.project_id == project_id, WorkspaceFile.id.in_(file_ids)
        )
    )
    by_id = {file.id: file for file in result.scalars().all()}
    if set(by_id) != set(file_ids):
        raise ProcurementStrategyValidationError(
            "Every submission file must belong to this project"
        )
    files = [by_id[value] for value in file_ids]
    for file in files:
        if not file.storage_key or not file.content_hash or file.size_bytes <= 0:
            raise ProcurementStrategyValidationError(
                f"{file.filename} has not finished uploading"
            )
        if PurePosixPath(file.filename).suffix.lower() not in SUBMISSION_SUFFIXES:
            raise ProcurementStrategyValidationError(
                f"{file.filename}: use PDF, Word, Excel, text or an image"
            )
    return files
