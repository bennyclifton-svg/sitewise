import asyncio
import uuid
from dataclasses import dataclass

import structlog
from fastapi import HTTPException, status

from app.config import settings
from app.database.activity_events import record_activity_events
from app.database.project import Project
from app.database.workspace_files import get_workspace_file_by_path, upsert_workspace_file
from app.inbox.paths import InboxPathError, build_inbox_workspace_path, build_storage_key, sanitize_filename
from app.projects.event_spine import record_project_verb, verb_dedup_key
from app.projects.locks import lock_project
from app.schemas.projects import WorkflowTraceEvent
from app.schemas.project_snapshot import ProjectSnapshot
from app.schemas.workflow_runs import WorkflowRunStartRequest
from app.storage.project_files import upload_project_file
from app.workflows.runs import start_workflow_run
from ingest.hashing import bytes_content_hash
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)
ACTIVITY_SOURCE = "document_ingest"


@dataclass(frozen=True, slots=True)
class InboxUploadItem:
    filename: str
    content: bytes
    relative_path: str | None = None
    ingest_metadata: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class InboxUploadOutcome:
    id: uuid.UUID
    filename: str
    workspace_path: str
    content_hash: str
    size_bytes: int
    ingest_status: str
    message: str | None = None
    workflow_run_id: uuid.UUID | None = None


class InboxUploadValidationError(ValueError):
    def __init__(self, filename: str, detail: str) -> None:
        self.filename = filename
        self.detail = detail
        super().__init__(detail)


def _activity_trace(
    step: str,
    status: str,
    message: str,
    **metadata,
) -> WorkflowTraceEvent:
    return WorkflowTraceEvent(
        step=step,
        status=status,
        message=message,
        metadata={key: value for key, value in metadata.items() if value is not None},
    )


async def _record_file_activity(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    workspace_file_id: uuid.UUID | None,
    events: list[WorkflowTraceEvent],
) -> None:
    await record_activity_events(
        session,
        project_id=project_id,
        source=ACTIVITY_SOURCE,
        run_id=run_id,
        reference_type="workspace_file" if workspace_file_id else None,
        reference_id=workspace_file_id,
        events=events,
    )


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
    user_id: uuid.UUID,
    snapshot: ProjectSnapshot,
) -> list[InboxUploadOutcome]:
    validate_upload_batch(items)
    outcomes: list[InboxUploadOutcome] = []

    for item in items:
        outcome = await _upload_single_file(
            session,
            project=project,
            item=item,
            user_id=user_id,
            snapshot=snapshot,
        )
        outcomes.append(outcome)

    await session.commit()
    return outcomes


async def _upload_single_file(
    session: AsyncSession,
    *,
    project: Project,
    item: InboxUploadItem,
    user_id: uuid.UUID,
    snapshot: ProjectSnapshot,
) -> InboxUploadOutcome:
    run_id = uuid.uuid4()
    filename = sanitize_filename(item.filename)
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
            await _record_file_activity(
                session,
                project_id=project.id,
                run_id=run_id,
                workspace_file_id=existing.id,
                events=[
                    _activity_trace(
                        "dedupe",
                        "skipped",
                        "Identical content already exists in the project workspace.",
                        filename=filename,
                        workspace_path=workspace_path,
                        ingest_status=existing.ingest_status,
                    )
                ],
            )
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
        storage_key = await asyncio.to_thread(
            upload_project_file,
            storage_key=storage_key,
            content=item.content,
            filename=filename,
        )
    except Exception as exc:
        logger.error(
            "inbox_storage_upload_failed",
            workspace_path=workspace_path,
            storage_key=storage_key,
            error_type=type(exc).__name__,
        )
        await _record_file_activity(
            session,
            project_id=project.id,
            run_id=run_id,
            workspace_file_id=None,
            events=[
                _activity_trace(
                    "store",
                    "failed",
                    f"Could not store {filename} in project storage.",
                    filename=filename,
                    workspace_path=workspace_path,
                    error_type=type(exc).__name__,
                )
            ],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not store the file in project storage. Please try again.",
        ) from exc

    project = await lock_project(session, project_id=project.id)
    if project is None:
        raise RuntimeError("Project was deleted while the file upload was in progress")

    record = await upsert_workspace_file(
        session,
        project_id=project.id,
        workspace_path=workspace_path,
        filename=filename,
        storage_bucket=bucket,
        storage_key=storage_key,
        content_hash=content_hash,
        size_bytes=len(item.content),
        ingest_status="queued",
        ingest_error=None,
        source_document_id=None,
    )
    await record_project_verb(
        session,
        project_id=project.id,
        verb="document.received",
        reference_type="workspace_file",
        reference_id=record.id,
        message=f"Received {filename}",
        deduplication_key=verb_dedup_key(
            "document.received",
            reference_type="workspace_file",
            reference_id=record.id,
            extra=content_hash,
        ),
        metadata={"filename": filename, "content_hash": content_hash},
    )
    await _record_file_activity(
        session,
        project_id=project.id,
        run_id=run_id,
        workspace_file_id=record.id,
        events=[
            _activity_trace(
                "store",
                "complete",
                "Stored file in the project workspace.",
                filename=filename,
                workspace_path=workspace_path,
                size_bytes=len(item.content),
            )
        ],
    )

    request = WorkflowRunStartRequest(
        idempotency_key=f"document-ingest:{record.id}:{content_hash}",
        expected_snapshot_fingerprint=snapshot.content_fingerprint,
        expected_profile_revision=snapshot.profile.profile_revision,
        expected_decision_set_revision=snapshot.decisions.set_revision,
        parameters={
            "workspace_file_id": str(record.id),
            "document_metadata": item.ingest_metadata or {},
        },
    )
    workflow_run, _ = await start_workflow_run(
        session,
        project=project,
        user_id=user_id,
        workflow_type="ingest_project_document",
        request=request,
        snapshot=snapshot,
    )
    await _record_file_activity(
        session,
        project_id=project.id,
        run_id=run_id,
        workspace_file_id=record.id,
        events=[
            _activity_trace(
                "workspace_status",
                "queued",
                "Uploaded; ingestion queued.",
                filename=filename,
                workspace_path=workspace_path,
                ingest_status="queued",
            )
        ],
    )

    return InboxUploadOutcome(
        id=record.id,
        filename=filename,
        workspace_path=workspace_path,
        content_hash=content_hash,
        size_bytes=len(item.content),
        ingest_status="queued",
        message="Uploaded; ingestion queued",
        workflow_run_id=workflow_run.id,
    )
