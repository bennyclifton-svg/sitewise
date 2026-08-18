from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.activity_events import record_activity_events
from app.database.project import Project
from app.database.source_document import SourceDocument
from app.database.workspace_file import WorkspaceFile
from app.intake.sort_service import file_single_document
from app.projects.consultant_facts import upsert_consultant_fact_from_document
from app.projects.identity_bootstrap import safe_bootstrap_identity_from_document
from app.schemas.projects import WorkflowTraceEvent
from app.schemas.project_snapshot import DOCUMENT_INGEST_FAILURE_DETAIL
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
        auto_sort_destination: str | None = None
        if record.ingest_status == "ingested" and record.source_document_id is not None:
            await safe_bootstrap_identity_from_document(
                session,
                project=project,
                source_document_id=record.source_document_id,
            )
            document = await session.get(SourceDocument, record.source_document_id)
            if document is not None:
                upsert_consultant_fact_from_document(project, document)
                auto_sort_destination = await file_single_document(
                    session, project=project, document=document
                )
                if auto_sort_destination:
                    trace.append(
                        WorkflowTraceEvent(
                            step="auto_sort",
                            status="complete",
                            message="Filed inbox document to a confident lifecycle folder.",
                            metadata={
                                "source_path": record.workspace_path,
                                "destination_path": auto_sort_destination,
                            },
                        )
                    )
                    filed_doc_id = await asyncio.to_thread(
                        source_document_id_for_path,
                        auto_sort_destination,
                        project_id=project.id,
                    )
                    if filed_doc_id is not None:
                        filed_document = await session.get(SourceDocument, filed_doc_id)
                        if filed_document is not None:
                            upsert_consultant_fact_from_document(project, filed_document)
                elif record.workspace_path.startswith(
                    f"{project.workspace_path.rstrip('/')}/_inbox/"
                ):
                    trace.append(
                        WorkflowTraceEvent(
                            step="auto_sort",
                            status="skipped",
                            message="No confident lifecycle folder; left in inbox for Sort Files.",
                            metadata={"workspace_path": record.workspace_path},
                        )
                    )
        if ingested:
            status_message = (
                f"Ingestion complete. Auto-filed to {auto_sort_destination}."
                if auto_sort_destination
                else (
                    "Ingestion complete. File remains in the inbox until Sort Files "
                    "finds a confident destination."
                )
            )
        else:
            status_message = "Ingest skipped because the content is unchanged."
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
                    message=status_message,
                    metadata={
                        "filename": record.filename,
                        "workspace_path": record.workspace_path,
                        "ingest_status": record.ingest_status,
                        "auto_sort_destination": auto_sort_destination,
                    },
                ),
            ],
        )
    except Exception as exc:
        record.ingest_status = "failed"
        record.ingest_error = DOCUMENT_INGEST_FAILURE_DETAIL
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
                        "error_type": type(exc).__name__,
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
