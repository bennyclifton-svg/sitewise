import asyncio
import uuid
from dataclasses import dataclass

import structlog
from fastapi import HTTPException, status

from app.config import settings
from app.database.project import Project
from app.database.workspace_files import get_workspace_file_by_path, upsert_workspace_file
from app.inbox.paths import InboxPathError, build_inbox_workspace_path, build_storage_key, sanitize_filename
from app.storage.project_files import upload_project_file
from ingest.hashing import bytes_content_hash
from ingest.hosted import ingest_hosted_file, source_document_id_for_path
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class InboxUploadItem:
    filename: str
    content: bytes
    relative_path: str | None = None


@dataclass(frozen=True, slots=True)
class InboxUploadOutcome:
    id: uuid.UUID
    filename: str
    workspace_path: str
    content_hash: str
    size_bytes: int
    ingest_status: str
    message: str | None = None


class InboxUploadValidationError(ValueError):
    def __init__(self, filename: str, detail: str) -> None:
        self.filename = filename
        self.detail = detail
        super().__init__(detail)


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return f".{filename.rsplit('.', maxsplit=1)[-1].lower()}"


def validate_upload_item(item: InboxUploadItem) -> None:
    try:
        filename = sanitize_filename(item.filename)
    except InboxPathError as exc:
        raise InboxUploadValidationError(item.filename, str(exc)) from exc

    extension = _extension(filename)
    if extension not in settings.ingest_supported_extensions_set:
        raise InboxUploadValidationError(
            filename,
            f"Unsupported file type '{extension or 'unknown'}'. "
            f"Supported: {', '.join(sorted(settings.ingest_supported_extensions_set))}",
        )

    if not item.content:
        raise InboxUploadValidationError(filename, "File is empty")


def validate_upload_batch(items: list[InboxUploadItem]) -> None:
    if not items:
        msg = "At least one file is required"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    errors: list[str] = []
    for item in items:
        try:
            validate_upload_item(item)
        except InboxUploadValidationError as exc:
            errors.append(f"{exc.filename}: {exc.detail}")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Upload validation failed", "errors": errors},
        )


async def upload_inbox_files(
    session: AsyncSession,
    *,
    project: Project,
    items: list[InboxUploadItem],
) -> list[InboxUploadOutcome]:
    validate_upload_batch(items)
    outcomes: list[InboxUploadOutcome] = []

    for item in items:
        outcome = await _upload_single_file(session, project=project, item=item)
        outcomes.append(outcome)

    await session.commit()
    return outcomes


async def _upload_single_file(
    session: AsyncSession,
    *,
    project: Project,
    item: InboxUploadItem,
) -> InboxUploadOutcome:
    filename = sanitize_filename(item.filename)
    extension = _extension(filename)
    content_hash = bytes_content_hash(item.content)
    workspace_path = build_inbox_workspace_path(
        project.workspace_path,
        filename=filename,
        relative_path=item.relative_path,
    )
    storage_key = build_storage_key(str(project.id), workspace_path)
    bucket = settings.supabase_storage_bucket

    existing = await get_workspace_file_by_path(
        session,
        project_id=project.id,
        workspace_path=workspace_path,
    )
    if existing is not None and existing.content_hash == content_hash:
        if existing.ingest_status in {"ingested", "skipped"}:
            return InboxUploadOutcome(
                id=existing.id,
                filename=filename,
                workspace_path=workspace_path,
                content_hash=content_hash,
                size_bytes=existing.size_bytes,
                ingest_status=existing.ingest_status,
                message="Identical content already uploaded",
            )

    try:
        await asyncio.to_thread(
            upload_project_file,
            storage_key=storage_key,
            content=item.content,
            filename=filename,
        )
    except Exception as exc:
        logger.exception("inbox_storage_upload_failed", workspace_path=workspace_path)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to store '{filename}' in object storage",
        ) from exc

    record = await upsert_workspace_file(
        session,
        project_id=project.id,
        workspace_path=workspace_path,
        filename=filename,
        storage_bucket=bucket,
        storage_key=storage_key,
        content_hash=content_hash,
        size_bytes=len(item.content),
        ingest_status="pending",
        ingest_error=None,
        source_document_id=None,
    )

    ingest_status = "failed"
    ingest_error: str | None = None
    message: str | None = None

    try:
        ingested = await asyncio.to_thread(
            ingest_hosted_file,
            content=item.content,
            workspace_path=workspace_path,
            project_slug=project.slug,
            project_phase=project.phase,
            filename=filename,
            extension=extension,
            skip_if_unchanged=True,
        )
        if ingested:
            ingest_status = "ingested"
            message = "Uploaded and ingested"
        else:
            ingest_status = "skipped"
            message = "Uploaded; ingest skipped because content is unchanged"
    except Exception as exc:
        ingest_error = str(exc)
        message = "Uploaded but ingest failed"
        logger.exception("inbox_ingest_failed", workspace_path=workspace_path)

    source_doc_id = await asyncio.to_thread(source_document_id_for_path, workspace_path)
    record = await upsert_workspace_file(
        session,
        project_id=project.id,
        workspace_path=workspace_path,
        filename=filename,
        storage_bucket=bucket,
        storage_key=storage_key,
        content_hash=content_hash,
        size_bytes=len(item.content),
        ingest_status=ingest_status,
        ingest_error=ingest_error,
        source_document_id=source_doc_id,
    )

    return InboxUploadOutcome(
        id=record.id,
        filename=filename,
        workspace_path=workspace_path,
        content_hash=content_hash,
        size_bytes=len(item.content),
        ingest_status=ingest_status,
        message=message,
    )
