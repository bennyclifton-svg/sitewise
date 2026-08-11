import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.workspace_file import WorkspaceFile


async def list_workspace_files_for_project(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> list[WorkspaceFile]:
    result = await session.execute(
        select(WorkspaceFile).options(selectinload(WorkspaceFile.source_document))
        .where(WorkspaceFile.project_id == project_id)
        .order_by(WorkspaceFile.workspace_path.asc())
    )
    return list(result.scalars().all())


async def search_workspace_files_for_project(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    query: str | None = None,
    path_prefix: str | None = None,
    limit: int = 50,
) -> list[WorkspaceFile]:
    stmt = (
        select(WorkspaceFile)
        .options(selectinload(WorkspaceFile.source_document))
        .where(WorkspaceFile.project_id == project_id)
    )
    if path_prefix:
        prefix = path_prefix.rstrip("/")
        stmt = stmt.where(
            or_(
                WorkspaceFile.workspace_path == prefix,
                WorkspaceFile.workspace_path.startswith(prefix + "/"),
            )
        )
    if query:
        stmt = stmt.where(
            func.lower(
                WorkspaceFile.workspace_path + " " + WorkspaceFile.filename
            ).contains(query.lower())
        )
    result = await session.execute(
        stmt.order_by(WorkspaceFile.workspace_path.asc(), WorkspaceFile.id.asc()).limit(
            limit
        )
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
    # Atomic upsert avoids races between workbook rebuild and other writers that
    # target the same (project_id, workspace_path) unique key.
    statement = insert(WorkspaceFile).values(
        id=uuid.uuid4(),
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
    statement = statement.on_conflict_do_update(
        constraint="uq_workspace_files_project_workspace_path",
        set_={
            "filename": filename,
            "storage_bucket": storage_bucket,
            "storage_key": storage_key,
            "content_hash": content_hash,
            "size_bytes": size_bytes,
            "ingest_status": ingest_status,
            "ingest_error": ingest_error,
            "source_document_id": source_document_id,
            "updated_at": func.now(),
        },
    ).returning(WorkspaceFile.id)
    result = await session.execute(statement)
    record_id = result.scalar_one()
    record = await session.get(WorkspaceFile, record_id)
    if record is None:
        raise RuntimeError("workspace file upsert did not return a row")
    return record
