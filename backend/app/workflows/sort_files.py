import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.activity_events import record_activity_events
from app.database.chats import create_message
from app.database.draft_artifacts import create_draft_artifact, next_draft_version
from app.database.project import Project
from app.intake.sort_service import SortFilesResult, sort_inbox_files
from app.schemas.projects import (
    DraftArtifactResponse,
    SortFilesResponse,
    SortFileRow,
    SortFilesSummary,
    WorkflowTraceEvent,
)
from app.sitewise.gate import format_overlay_failure, overlay_status
from ingest.hashing import bytes_content_hash

WORKFLOW_TYPE = "sort_files"
RUNTIME_NAME = "clerk-sitewise-sort-files"


def _trace(step: str, status: str, message: str, **metadata) -> WorkflowTraceEvent:
    duration_ms = metadata.pop("duration_ms", None)
    return WorkflowTraceEvent(
        step=step,
        status=status,
        message=message,
        duration_ms=duration_ms,
        metadata={key: value for key, value in metadata.items() if value is not None},
    )


def _summary(result: SortFilesResult) -> SortFilesSummary:
    return SortFilesSummary(
        inspected=result.counts.inspected,
        moved=result.counts.moved,
        already_filed=result.counts.already_filed,
        unresolved=result.counts.unresolved,
        skipped=result.counts.skipped,
        refused=result.counts.refused,
    )


def _rows(result: SortFilesResult) -> list[SortFileRow]:
    return [
        SortFileRow(
            source_path=record.source_path,
            filename=record.filename,
            outcome=record.outcome,
            destination_path=record.destination_path,
            destination_filename=record.destination_filename,
            reason=record.reason,
            document_number=record.document_number,
            title=record.title,
            revision=record.revision,
            category=record.category,
        )
        for record in result.records
    ]


def _record_status(outcome: str) -> str:
    if outcome in {"moved", "already-filed"}:
        return "complete"
    if outcome == "unresolved":
        return "blocked"
    if outcome in {"refused", "skipped"}:
        return outcome
    return "complete"


def _record_message(record) -> str:
    if record.destination_path:
        return f"{record.filename}: {record.outcome} to {record.destination_path}."
    return f"{record.filename}: {record.reason or record.outcome}."


def _record_trace_events(result: SortFilesResult) -> list[WorkflowTraceEvent]:
    return [
        _trace(
            "file",
            _record_status(record.outcome),
            _record_message(record),
            source_path=record.source_path,
            destination_path=record.destination_path,
            outcome=record.outcome,
            reason=record.reason,
            document_number=record.document_number,
            title=record.title,
            revision=record.revision,
            category=record.category,
        )
        for record in result.records
    ]


async def run_sort_files_workflow(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    project: Project,
    thread_id: uuid.UUID | None,
    auto_commit: bool = True,
) -> SortFilesResponse:
    trace: list[WorkflowTraceEvent] = []
    run_id = uuid.uuid4()

    gate = overlay_status(
        archetype=project.archetype,
        user_role=project.user_role,
        state=project.state,
        building_class=project.building_class,
        work_type=project.work_type,
    )
    if not gate.ready:
        message = format_overlay_failure(gate, workflow="Sort Files")
        trace.append(_trace("gate", "blocked", message))
        await _persist_trace_message(
            session,
            project_id=project.id,
            run_id=run_id,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="blocked",
        )
        return SortFilesResponse(
            status="blocked",
            gate=gate,
            trace=trace,
            message=message,
        )

    trace.append(_trace("gate", "passed", "SiteWise three-overlay gate passed."))

    inspection_started = time.perf_counter()
    manifest_hint = await next_draft_version(
        session,
        project_id=project.id,
        workflow_type=WORKFLOW_TYPE,
    )
    result = await sort_inbox_files(
        session,
        project=project,
        manifest_version_hint=manifest_hint - 1,
    )

    trace.append(
        _trace(
            "inspect",
            "complete",
            f"Inspected {result.counts.inspected} inbox file(s).",
            inspected=result.counts.inspected,
            moved=result.counts.moved,
            unresolved=result.counts.unresolved,
            refused=result.counts.refused,
            skipped=result.counts.skipped,
            already_filed=result.counts.already_filed,
            duration_ms=int((time.perf_counter() - inspection_started) * 1000),
        )
    )
    trace.extend(_record_trace_events(result))

    persistence_started = time.perf_counter()
    draft = await create_draft_artifact(
        session,
        project_id=project.id,
        workflow_type=WORKFLOW_TYPE,
        title=f"Intake manifest v{result.manifest_version:02d}",
        workspace_path=result.manifest_workspace_path,
        author_user_id=user_id,
        content_markdown=result.manifest_markdown,
        model=None,
        runtime=RUNTIME_NAME,
        expected_base_version=result.manifest_version - 1,
        actor_source="sort_files_workflow",
        provenance_metadata={
            "summary": _summary(result).model_dump(),
            "rows": [row.model_dump() for row in _rows(result)],
            "warnings": result.warnings,
            "trace": [event.model_dump() for event in trace],
        },
    )
    from app.projects.artefact_revisions import set_export_result_for_path

    await set_export_result_for_path(
        session,
        revision=draft,
        workspace_path=result.manifest_workspace_path,
        content_hash=bytes_content_hash(result.manifest_markdown.encode("utf-8")),
    )
    trace.append(
        _trace(
            "manifest_save",
            "complete",
            "Saved intake manifest as a versioned draft artefact.",
            draft_id=str(draft.id),
            version=draft.version,
            manifest_path=result.manifest_workspace_path,
            duration_ms=int((time.perf_counter() - persistence_started) * 1000),
        )
    )

    if auto_commit:
        await session.commit()

    message = (
        f"Sort Files completed. {result.counts.moved} moved, "
        f"{result.counts.unresolved} unresolved, {result.counts.refused} refused."
    )
    await _persist_trace_message(
        session,
        project_id=project.id,
        run_id=run_id,
        thread_id=thread_id,
        content=message,
        trace=trace,
        status="complete",
        draft_id=draft.id,
    )

    return SortFilesResponse(
        status="complete",
        gate=gate,
        trace=trace,
        summary=_summary(result),
        rows=_rows(result),
        warnings=result.warnings,
        draft=DraftArtifactResponse.model_validate(draft),
        message=message,
    )


async def _persist_trace_message(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    thread_id: uuid.UUID | None,
    content: str,
    trace: list[WorkflowTraceEvent],
    status: str,
    draft_id: uuid.UUID | None = None,
) -> None:
    await record_activity_events(
        session,
        project_id=project_id,
        source=WORKFLOW_TYPE,
        run_id=run_id,
        reference_type="draft_artifact" if draft_id else None,
        reference_id=draft_id,
        events=trace,
    )
    if thread_id is None:
        return
    await create_message(
        session,
        thread_id=thread_id,
        role="assistant",
        content=content,
        message_data={
            "workflowType": WORKFLOW_TYPE,
            "workflowStatus": status,
            "workflowTrace": [event.model_dump() for event in trace],
            "draftId": str(draft_id) if draft_id else None,
        },
    )
