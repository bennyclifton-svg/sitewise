from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.activity_events import record_activity_events
from app.database.project import Project
from app.database.source_document import SourceDocument
from app.database.workspace_file import WorkspaceFile
from app.schemas.projects import WorkflowTraceEvent
from app.storage.project_files import download_project_file
from ingest.hosted import ingest_hosted_file, source_document_id_for_path


@dataclass(frozen=True, slots=True)
class DocumentIngestResult:
    workspace_file_id: str
    ingest_status: str
    status: str = "complete"


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return f".{filename.rsplit('.', maxsplit=1)[-1].lower()}"


async def _record(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    workspace_file_id: uuid.UUID,
    events: list[WorkflowTraceEvent],
) -> None:
    await record_activity_events(
        session,
        project_id=project_id,
        source="document_ingest",
        run_id=run_id,
        reference_type="workspace_file",
        reference_id=workspace_file_id,
        events=events,
    )


async def ingest_project_document(
    session: AsyncSession,
    *,
    project: Project,
    run_id: uuid.UUID,
    workspace_file_id: uuid.UUID,
    document_metadata: dict[str, object] | None = None,
) -> DocumentIngestResult:
    record = await session.get(WorkspaceFile, workspace_file_id)
    if record is None or record.project_id != project.id:
        raise ValueError("Queued workspace file no longer exists in this project")

    record.ingest_status = "ingesting"
    record.ingest_error = None
    await session.commit()

    trace: list[WorkflowTraceEvent] = []

    def collect_trace(
        step: str,
        status: str,
        message: str,
        metadata: dict[str, object],
    ) -> None:
        trace.append(
            WorkflowTraceEvent(
                step=step,
                status=status,
                message=message,
                metadata=metadata,
            )
        )

    try:
        content = await asyncio.to_thread(
            download_project_file, storage_key=record.storage_key
        )
        ingested = await asyncio.to_thread(
            ingest_hosted_file,
            content=content,
            workspace_path=record.workspace_path,
            project_id=project.id,
            project_slug=project.slug,
            project_phase=project.phase,
            filename=record.filename,
            extension=_extension(record.filename),
            skip_if_unchanged=True,
            trace_callback=collect_trace,
        )
        record.source_document_id = await asyncio.to_thread(
            source_document_id_for_path,
            record.workspace_path,
            project_id=project.id,
        )
        if document_metadata and record.source_document_id is not None:
            document = await session.get(SourceDocument, record.source_document_id)
            if document is not None:
                document.document_metadata = {
                    **(document.document_metadata or {}),
                    **document_metadata,
                }
        record.ingest_status = "ingested" if ingested else "skipped"
        await _record(
            session,
            project_id=project.id,
            run_id=run_id,
            workspace_file_id=record.id,
            events=[
                *trace,
                WorkflowTraceEvent(
                    step="workspace_status",
                    status="complete" if ingested else "skipped",
                    message=(
                        "Ingestion complete. File remains in the inbox until Sort Files runs."
                        if ingested
                        else "Ingest skipped because the content is unchanged."
                    ),
                    metadata={
                        "filename": record.filename,
                        "workspace_path": record.workspace_path,
                        "ingest_status": record.ingest_status,
                    },
                ),
            ],
        )
    except Exception as exc:
        record.ingest_status = "failed"
        record.ingest_error = str(exc)
        await _record(
            session,
            project_id=project.id,
            run_id=run_id,
            workspace_file_id=record.id,
            events=[
                *trace,
                WorkflowTraceEvent(
                    step="ingest",
                    status="failed",
                    message="Ingest failed after the file was stored.",
                    metadata={
                        "filename": record.filename,
                        "workspace_path": record.workspace_path,
                        "error": str(exc),
                    },
                ),
            ],
        )
        await session.commit()
        raise

    return DocumentIngestResult(
        workspace_file_id=str(record.id),
        ingest_status=record.ingest_status,
    )
