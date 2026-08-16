"""Remove an owned project and collect object-storage keys for cleanup."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cost_plan.models import CostPlanVersion
from app.programme.models import ProgrammeVersion
from app.database.artefact_export import ArtefactExport
from app.database.chat_thread import ChatThread
from app.database.procurement_request import ProcurementRequest
from app.database.project import Project
from app.database.project_document_selection import (
    ProjectDocumentSelectionItem,
    WorkflowInputRetentionLock,
)
from app.database.workspace_file import WorkspaceFile


async def delete_owned_project(
    session: AsyncSession,
    *,
    project: Project,
) -> list[str]:
    """Delete the project row and its chat threads. Children cascade.

    Chat threads only SET NULL on project delete, so they are removed first
    or they linger in the user's thread list. Cost plans, procurement
    requests, and document-selection locks RESTRICT drafts and workspace
    files; those rows must go first or Postgres rejects the project delete.
    The project itself is removed with a SQL DELETE so SQLAlchemy does not
    null out loaded child project_id columns. Storage objects are deleted
    after the response by the caller.
    """
    # Select keys only. Loading WorkspaceFile/ArtefactExport rows would keep
    # them in the session; session.delete(project) then UPDATEs project_id to
    # NULL and trips the NOT NULL constraint.
    file_keys = list(
        (
            await session.scalars(
                select(WorkspaceFile.storage_key).where(
                    WorkspaceFile.project_id == project.id
                )
            )
        ).all()
    )
    export_keys = list(
        (
            await session.scalars(
                select(ArtefactExport.storage_key).where(
                    ArtefactExport.project_id == project.id
                )
            )
        ).all()
    )
    storage_keys = [key for key in (*file_keys, *export_keys) if key]

    for model in (
        ProgrammeVersion,
        CostPlanVersion,
        ProcurementRequest,
        WorkflowInputRetentionLock,
        ProjectDocumentSelectionItem,
        ChatThread,
    ):
        await session.execute(delete(model).where(model.project_id == project.id))
    await session.execute(delete(Project).where(Project.id == project.id))
    await session.flush()
    await session.commit()
    return list(dict.fromkeys(storage_keys))
