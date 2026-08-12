from __future__ import annotations

import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.artefact_export import ArtefactExport
from app.database.draft_artifact import DraftArtifact
from app.database.draft_artifacts import get_latest_draft_artifact
from app.database.procurement_request import ProcurementRequest
from app.database.project import Project
from app.database.workspace_file import WorkspaceFile

logger = structlog.get_logger(__name__)


async def delete_project_draft(
    session: AsyncSession,
    *,
    project: Project,
    draft_id: uuid.UUID,
) -> tuple[list[str], DraftArtifact | None]:
    """Remove a generated draft artefact and its published workspace exports.

    Clears procurement-request pointers first (FK is RESTRICT), deletes any
    draft-status register rows that pointed at this revision, removes matching
    workspace_files rows, then deletes the draft (cascading artefact_exports).

    Returns storage keys for deferred object-storage cleanup and the new latest
    draft for the same workflow type, if one remains.
    """
    draft = await session.get(DraftArtifact, draft_id)
    if draft is None or draft.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )

    workflow_type = draft.workflow_type
    export_rows = list(
        (
            await session.scalars(
                select(ArtefactExport).where(ArtefactExport.draft_id == draft.id)
            )
        ).all()
    )
    workspace_paths = {
        draft.workspace_path,
        *(row.workspace_path for row in export_rows if row.workspace_path),
    }
    storage_keys = [row.storage_key for row in export_rows if row.storage_key]

    workspace_files = list(
        (
            await session.scalars(
                select(WorkspaceFile).where(
                    WorkspaceFile.project_id == project.id,
                    WorkspaceFile.workspace_path.in_(workspace_paths),
                )
            )
        ).all()
    )
    storage_keys.extend(
        record.storage_key for record in workspace_files if record.storage_key
    )

    linked_requests = list(
        (
            await session.scalars(
                select(ProcurementRequest).where(
                    ProcurementRequest.current_draft_artifact_id == draft.id
                )
            )
        ).all()
    )
    for request in linked_requests:
        request.current_draft_artifact_id = None
        if request.status == "draft":
            await session.delete(request)

    if workspace_files:
        await session.execute(
            delete(WorkspaceFile).where(
                WorkspaceFile.id.in_([record.id for record in workspace_files])
            )
        )

    await session.delete(draft)
    await session.flush()

    latest = await get_latest_draft_artifact(
        session,
        project_id=project.id,
        workflow_type=workflow_type,
    )
    await session.commit()

    logger.info(
        "draft_artifact_deleted",
        project=project.slug,
        draft_id=str(draft_id),
        workflow_type=workflow_type,
        workspace_files=len(workspace_files),
        storage_keys=len(storage_keys),
    )
    return list(dict.fromkeys(storage_keys)), latest
