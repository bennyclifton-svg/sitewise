from __future__ import annotations

import asyncio
import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.project import Project
from app.database.source_document import SourceDocument
from app.database.workspace_file import WorkspaceFile
from app.storage.project_files import delete_project_file

logger = structlog.get_logger(__name__)


async def delete_project_evidence(
    session: AsyncSession,
    *,
    project: Project,
    evidence_id: uuid.UUID,
) -> None:
    """Remove a project evidence document and all of its derived records.

    Deletes the source document (cascading to its chunks and citations via the
    database FK constraints), any workspace_files rows that point at it, and the
    backing object-storage file. A storage delete failure is logged but does not
    block the database cleanup so the document still disappears from the
    repository view.
    """

    document = await session.scalar(
        select(SourceDocument).where(
            SourceDocument.id == evidence_id,
            SourceDocument.project == project.slug,
            SourceDocument.source_type == "project_evidence",
        )
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    result = await session.execute(
        select(WorkspaceFile).where(
            WorkspaceFile.project_id == project.id,
            or_(
                WorkspaceFile.source_document_id == document.id,
                WorkspaceFile.workspace_path == document.relative_path,
            ),
        )
    )
    workspace_files = list(result.scalars().all())

    for workspace_file in workspace_files:
        try:
            await asyncio.to_thread(
                delete_project_file, storage_key=workspace_file.storage_key
            )
        except Exception:
            logger.warning(
                "evidence_storage_delete_failed",
                storage_key=workspace_file.storage_key,
                workspace_path=workspace_file.workspace_path,
            )

    if workspace_files:
        await session.execute(
            delete(WorkspaceFile).where(
                WorkspaceFile.id.in_([record.id for record in workspace_files])
            )
        )

    await session.execute(
        delete(SourceDocument).where(SourceDocument.id == document.id)
    )
    await session.commit()

    logger.info(
        "evidence_deleted",
        project=project.slug,
        evidence_id=str(document.id),
        relative_path=document.relative_path,
        workspace_files=len(workspace_files),
    )
