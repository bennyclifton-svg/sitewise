"""Remove an owned project and collect object-storage keys for cleanup."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.artefact_export import ArtefactExport
from app.database.chat_thread import ChatThread
from app.database.project import Project
from app.database.workspace_file import WorkspaceFile


async def delete_owned_project(
    session: AsyncSession,
    *,
    project: Project,
) -> list[str]:
    """Delete the project row and its chat threads. Children cascade.

    Chat threads only SET NULL on project delete, so they are removed first
    or they linger in the user's thread list. Storage objects are deleted
    after the response by the caller.
    """
    workspace_files = list(
        (
            await session.scalars(
                select(WorkspaceFile).where(WorkspaceFile.project_id == project.id)
            )
        ).all()
    )
    exports = list(
        (
            await session.scalars(
                select(ArtefactExport).where(ArtefactExport.project_id == project.id)
            )
        ).all()
    )
    storage_keys = [
        record.storage_key
        for record in (*workspace_files, *exports)
        if getattr(record, "storage_key", None)
    ]

    await session.execute(
        delete(ChatThread).where(ChatThread.project_id == project.id)
    )
    await session.delete(project)
    await session.flush()
    await session.commit()
    return list(dict.fromkeys(storage_keys))
