from __future__ import annotations

import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.project import Project
from app.database.source_document import SourceDocument
from app.database.workspace_file import WorkspaceFile
from app.inbox.paths import is_inbox_workspace_path
from app.projects.document_selections import file_has_retention_lock

logger = structlog.get_logger(__name__)


async def delete_project_evidence(
    session: AsyncSession,
    *,
    project: Project,
    evidence_id: uuid.UUID,
) -> list[str]:
    """Remove a project evidence document and all of its derived records.

    Deletes the source document (cascading to its chunks and citations via the
    database FK constraints) and any workspace_files rows that point at it, then
    commits. Returns the object-storage keys for the backing files so the caller
    can remove them out of band (a background task) — keeping the slow storage
    round-trip off the request's response path. The document disappears from the
    repository view as soon as the database delete commits.
    """

    document = await session.scalar(
        select(SourceDocument).where(
            SourceDocument.id == evidence_id,
            SourceDocument.project_id == project.id,
            SourceDocument.source_type == "project_evidence",
        )
    )
    if document is None:
        workspace_file = await session.scalar(
            select(WorkspaceFile).where(
                WorkspaceFile.id == evidence_id,
                WorkspaceFile.project_id == project.id,
            )
        )
        if workspace_file is None or not is_inbox_workspace_path(workspace_file.workspace_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        storage_keys = [workspace_file.storage_key]
        if await file_has_retention_lock(
            session, project_id=project.id, workspace_file_id=workspace_file.id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document is retained by an active or approved workflow",
            )
        await session.execute(
            delete(WorkspaceFile).where(WorkspaceFile.id == workspace_file.id)
        )
        await session.commit()

        logger.info(
            "inbox_workspace_file_deleted",
            project=project.slug,
            evidence_id=str(workspace_file.id),
            relative_path=workspace_file.workspace_path,
        )
        return storage_keys

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
    storage_keys = [record.storage_key for record in workspace_files]

    for record in workspace_files:
        if await file_has_retention_lock(
            session, project_id=project.id, workspace_file_id=record.id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document is retained by an active or approved workflow",
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

    return storage_keys
