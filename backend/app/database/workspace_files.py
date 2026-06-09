import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.workspace_file import WorkspaceFile


async def list_workspace_files_for_project(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> list[WorkspaceFile]:
    result = await session.execute(
        select(WorkspaceFile)
        .where(WorkspaceFile.project_id == project_id)
        .order_by(WorkspaceFile.workspace_path.asc())
    )
    return list(result.scalars().all())


async def list_workspace_files_under_prefix(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    path_prefix: str,
) -> list[WorkspaceFile]:
    normalised = path_prefix.rstrip("/") + "/"
    result = await session.execute(
        select(WorkspaceFile)
        .where(
            WorkspaceFile.project_id == project_id,
            WorkspaceFile.workspace_path.startswith(normalised),
        )
        .order_by(WorkspaceFile.workspace_path.asc())
    )
    return list(result.scalars().all())


async def get_workspace_file_by_path(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    workspace_path: str,
) -> WorkspaceFile | None:
    result = await session.execute(
        select(WorkspaceFile).where(
            WorkspaceFile.project_id == project_id,
            WorkspaceFile.workspace_path == workspace_path,
        )
    )
    return result.scalar_one_or_none()


async def upsert_workspace_file(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    workspace_path: str,
    filename: str,
    storage_bucket: str,
    storage_key: str,
    content_hash: str,
    size_bytes: int,
    ingest_status: str,
    ingest_error: str | None = None,
    source_document_id: uuid.UUID | None = None,
) -> WorkspaceFile:
    existing = await get_workspace_file_by_path(
        session,
        project_id=project_id,
        workspace_path=workspace_path,
    )
    if existing is None:
        record = WorkspaceFile(
            project_id=project_id,
            workspace_path=workspace_path,
            filename=filename,
            storage_bucket=storage_bucket,
            storage_key=storage_key,
            content_hash=content_hash,
            size_bytes=size_bytes,
            ingest_status=ingest_status,
            ingest_error=ingest_error,
            source_document_id=source_document_id,
        )
        session.add(record)
        await session.flush()
        await session.refresh(record)
        return record

    existing.filename = filename
    existing.storage_bucket = storage_bucket
    existing.storage_key = storage_key
    existing.content_hash = content_hash
    existing.size_bytes = size_bytes
    existing.ingest_status = ingest_status
    existing.ingest_error = ingest_error
    existing.source_document_id = source_document_id
    await session.flush()
    await session.refresh(existing)
    return existing
