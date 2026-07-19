from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.project import Project
from app.database.draft_artifact import DraftArtifact
from app.database.workflow_run import WorkflowRun
from app.projects.events import publish_project_event
from app.schemas.project_snapshot import ProjectSnapshot
from app.schemas.workflow_runs import WorkflowRunStartRequest


TERMINAL_STATES = frozenset({"needs_input", "complete", "failed", "cancelled"})
SUPPORTED_WORKFLOWS = frozenset(
    {
        "create_project_plan",
        "refresh_project_plan",
        "create_cost_plan",
        "sort_project_files",
        "consultant_procurement",
    }
)


class WorkflowRunConflict(RuntimeError):
    pass


class WorkflowRunNotFound(LookupError):
    pass


class WorkflowRunCancelled(RuntimeError):
    pass


class WorkflowRunCapabilityConflict(RuntimeError):
    pass


def canonical_request_hash(
    workflow_type: str, request: WorkflowRunStartRequest
) -> str:
    payload = {
        "schema_version": 1,
        "workflow_type": workflow_type,
        "expected_snapshot_fingerprint": request.expected_snapshot_fingerprint,
        "expected_profile_revision": request.expected_profile_revision,
        "expected_decision_set_revision": request.expected_decision_set_revision,
        "expected_artefact_version": request.expected_artefact_version,
        "chat_model": request.chat_model,
        "parameters": request.parameters,
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


async def start_workflow_run(
    session: AsyncSession,
    *,
    project: Project,
    user_id: uuid.UUID,
    workflow_type: str,
    request: WorkflowRunStartRequest,
    snapshot: ProjectSnapshot,
    max_attempts: int = 3,
) -> tuple[WorkflowRun, bool]:
    if workflow_type not in SUPPORTED_WORKFLOWS:
        raise ValueError(f"Unsupported core workflow: {workflow_type!r}")
    request_hash = canonical_request_hash(workflow_type, request)
    existing = await _find_idempotent_run(
        session,
        project_id=project.id,
        workflow_type=workflow_type,
        idempotency_key=request.idempotency_key,
    )
    if existing is not None:
        _require_matching_request(existing, request_hash)
        return existing, False

    _validate_expected_snapshot(snapshot, request)
    if workflow_type == "refresh_project_plan":
        latest_result = await session.execute(
            select(DraftArtifact)
            .where(
                DraftArtifact.project_id == project.id,
                DraftArtifact.workflow_type == "create_pmp",
            )
            .order_by(DraftArtifact.version.desc())
            .limit(1)
        )
        latest = latest_result.scalar_one_or_none()
        if latest is None or request.expected_artefact_version != latest.version:
            current = latest.version if latest is not None else 0
            raise WorkflowRunCapabilityConflict(
                "Project Plan base changed: "
                f"expected v{request.expected_artefact_version}, current v{current}"
            )
    run = WorkflowRun(
        project_id=project.id,
        requested_by_user_id=user_id,
        requested_by_thread_id=request.thread_id,
        requested_by_turn_id=request.turn_id,
        workflow_type=workflow_type,
        run_brief={
            "schema_version": 1,
            "snapshot": snapshot.model_dump(mode="json"),
            "project": {
                "id": str(project.id),
                "owner_user_id": str(project.owner_user_id),
                "slug": project.slug,
                "title": project.title,
                "workspace_path": project.workspace_path,
                "phase": project.phase,
                "status": project.status,
                "archetype": project.archetype,
                "project_metadata": project.project_metadata,
            },
            "chat_model": request.chat_model,
            "parameters": request.parameters,
        },
        idempotency_key=request.idempotency_key,
        schema_version=1,
        canonical_request_hash=request_hash,
        frozen_profile_revision=snapshot.profile.profile_revision,
        frozen_snapshot_fingerprint=snapshot.content_fingerprint,
        frozen_evidence_fingerprint=snapshot.evidence.fingerprint,
        frozen_decision_set_revision=snapshot.decisions.set_revision,
        frozen_selection_revision=_optional_int(
            snapshot.evidence.selection_metadata.get("revision")
        ),
        frozen_artefact_version=request.expected_artefact_version,
        state="queued",
        max_attempts=max(1, max_attempts),
        progress={"stage": "queued", "percent": 0},
    )
    created = True
    try:
        async with session.begin_nested():
            session.add(run)
            await session.flush()
    except IntegrityError:
        existing = await _find_idempotent_run(
            session,
            project_id=project.id,
            workflow_type=workflow_type,
            idempotency_key=request.idempotency_key,
        )
        if existing is None:
            raise
        _require_matching_request(existing, request_hash)
        run = existing
        created = False

    if created:
        await publish_project_event(
            session,
            project_id=project.id,
            actor_source="workflow_run",
            resource_type="workflow_run",
            resource_id=run.id,
            resource_revision=run.attempt,
            action="queued",
            payload={"workflow_type": workflow_type, "state": "queued"},
            deduplication_key=f"workflow-run:{run.id}:queued",
        )
    return run, created


async def get_workflow_run(
    session: AsyncSession, *, project_id: uuid.UUID, run_id: uuid.UUID
) -> WorkflowRun:
    result = await session.execute(
        select(WorkflowRun).where(
            WorkflowRun.id == run_id, WorkflowRun.project_id == project_id
        )
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise WorkflowRunNotFound(str(run_id))
    return run


async def claim_next_run(
    session: AsyncSession,
    *,
    worker_id: str,
    lease_seconds: int = 90,
) -> WorkflowRun | None:
    await _finalize_one_expired_cancellation(session)
    await _fail_one_exhausted_lease(session)
    now = datetime.now(UTC)
    claimable = or_(
        and_(WorkflowRun.state == "queued", WorkflowRun.run_after <= func.now()),
        and_(
            WorkflowRun.state == "running",
            WorkflowRun.lease_expires_at < func.now(),
        ),
    )
    result = await session.execute(
        select(WorkflowRun)
        .where(
            claimable,
            WorkflowRun.cancel_requested.is_(False),
            WorkflowRun.attempt < WorkflowRun.max_attempts,
        )
        .order_by(WorkflowRun.run_after.asc(), WorkflowRun.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    run = result.scalar_one_or_none()
    if run is None:
        return None
    run.state = "running"
    run.attempt += 1
    run.lock_owner = worker_id
    run.heartbeat_at = now
    run.lease_expires_at = now + timedelta(seconds=max(1, lease_seconds))
    run.started_at = run.started_at or now
    run.progress = {"stage": "starting", "percent": 1}
    await session.commit()
    return run


async def _finalize_one_expired_cancellation(session: AsyncSession) -> None:
    candidate_result = await session.execute(
        select(WorkflowRun.id, WorkflowRun.project_id)
        .where(
            WorkflowRun.state == "running",
            WorkflowRun.cancel_requested.is_(True),
            WorkflowRun.lease_expires_at < func.now(),
        )
        .order_by(WorkflowRun.lease_expires_at.asc())
        .limit(1)
    )
    candidate = candidate_result.first()
    if candidate is None:
        return
    project = await _locked_project(session, candidate.project_id)
    run_result = await session.execute(
        select(WorkflowRun).where(WorkflowRun.id == candidate.id).with_for_update()
    )
    run = run_result.scalar_one_or_none()
    if run is None or run.state != "running" or not run.cancel_requested:
        await session.rollback()
        return
    run.state = "cancelled"
    run.progress = {"stage": "cancelled", "percent": 100}
    run.completed_at = datetime.now(UTC)
    run.lock_owner = None
    run.lease_expires_at = None
    await publish_project_event(
        session,
        project_id=run.project_id,
        actor_source="workflow_worker",
        resource_type="workflow_run",
        resource_id=run.id,
        resource_revision=run.attempt,
        action="cancelled",
        payload={"workflow_type": run.workflow_type, "state": "cancelled"},
        deduplication_key=f"workflow-run:{run.id}:cancelled",
        locked_project=project,
    )
    await session.commit()


async def _fail_one_exhausted_lease(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    candidate_result = await session.execute(
        select(WorkflowRun.id, WorkflowRun.project_id)
        .where(
            WorkflowRun.state == "running",
            WorkflowRun.lease_expires_at < func.now(),
            WorkflowRun.attempt >= WorkflowRun.max_attempts,
        )
        .order_by(WorkflowRun.lease_expires_at.asc())
        .limit(1)
    )
    candidate = candidate_result.first()
    if candidate is None:
        return
    project = await _locked_project(session, candidate.project_id)
    run_result = await session.execute(
        select(WorkflowRun).where(WorkflowRun.id == candidate.id).with_for_update()
    )
    run = run_result.scalar_one_or_none()
    if (
        run is None
        or run.state != "running"
        or run.lease_expires_at is None
        or run.lease_expires_at >= now
        or run.attempt < run.max_attempts
    ):
        await session.rollback()
        return
    run.state = "failed"
    run.error_class = "WorkerLeaseExpired"
    run.error_message = "Worker lease expired after the final permitted attempt"
    run.progress = {"stage": "failed", "percent": 100}
    run.completed_at = now
    run.lock_owner = None
    run.lease_expires_at = None
    await publish_project_event(
        session,
        project_id=run.project_id,
        actor_source="workflow_worker",
        resource_type="workflow_run",
        resource_id=run.id,
        resource_revision=run.attempt,
        action="failed",
        payload={"workflow_type": run.workflow_type, "state": "failed"},
        deduplication_key=f"workflow-run:{run.id}:lease-exhausted",
        locked_project=project,
    )
    await session.commit()


async def heartbeat_run(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    worker_id: str,
    progress: dict[str, Any] | None = None,
    lease_seconds: int = 90,
) -> bool:
    result = await session.execute(
        select(WorkflowRun).where(WorkflowRun.id == run_id).with_for_update()
    )
    run = result.scalar_one_or_none()
    if run is None or run.state != "running" or run.lock_owner != worker_id:
        await session.rollback()
        return False
    now = datetime.now(UTC)
    run.heartbeat_at = now
    run.lease_expires_at = now + timedelta(seconds=max(1, lease_seconds))
    if progress is not None:
        run.progress = progress
    await session.commit()
    return not run.cancel_requested


async def lock_run_for_publish(
    session: AsyncSession, *, run_id: uuid.UUID, worker_id: str
) -> WorkflowRun:
    run = await _lock_project_then_run(session, run_id)
    if run is None or run.state != "running" or run.lock_owner != worker_id:
        raise WorkflowRunConflict("Workflow run lease is no longer owned by this worker")
    if run.cancel_requested:
        raise WorkflowRunCancelled(str(run.id))
    return run


async def complete_workflow_run(
    session: AsyncSession,
    *,
    run: WorkflowRun,
    result: dict[str, Any],
    duration_ms: int,
) -> None:
    result_status = result.get("status")
    terminal_state = {
        "blocked": "needs_input",
        "failed": "failed",
    }.get(result_status, "complete")
    draft = result.get("draft") if isinstance(result.get("draft"), dict) else None
    artefact_id = _optional_uuid(draft.get("id")) if draft else None
    run.state = terminal_state
    run.result = result
    run.result_artefact_id = artefact_id
    run.result_reference = _result_reference(run, result, artefact_id)
    run.progress = {"stage": terminal_state, "percent": 100}
    run.stage_durations_ms = {
        **run.stage_durations_ms,
        **_trace_durations(result),
        "workflow": duration_ms,
    }
    if terminal_state == "failed":
        run.error_class = "WorkflowResultFailed"
        run.error_message = str(result.get("message") or "Workflow failed")[:4000]
    run.completed_at = datetime.now(UTC)
    run.lock_owner = None
    run.lease_expires_at = None
    await publish_project_event(
        session,
        project_id=run.project_id,
        actor_source="workflow_worker",
        resource_type="workflow_run",
        resource_id=run.id,
        resource_revision=run.attempt,
        action=terminal_state,
        payload={
            "workflow_type": run.workflow_type,
            "state": terminal_state,
            "result_artefact_id": str(artefact_id) if artefact_id else None,
            "duration_ms": duration_ms,
        },
        deduplication_key=f"workflow-run:{run.id}:{terminal_state}",
    )


async def fail_workflow_run(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    worker_id: str,
    error: BaseException,
    duration_ms: int,
) -> WorkflowRun:
    run = await _lock_project_then_run(session, run_id)
    if run.lock_owner != worker_id or run.state != "running":
        raise WorkflowRunConflict("Workflow run lease is no longer owned by this worker")
    now = datetime.now(UTC)
    run.error_class = type(error).__name__[:255]
    run.error_message = str(error)[:4000] or type(error).__name__
    run.stage_durations_ms = {**run.stage_durations_ms, "workflow": duration_ms}
    run.lock_owner = None
    run.lease_expires_at = None
    if run.cancel_requested:
        run.state = "cancelled"
        run.progress = {"stage": "cancelled", "percent": 100}
        run.completed_at = now
        action = "cancelled"
    elif run.attempt < run.max_attempts:
        run.state = "queued"
        run.run_after = now + timedelta(seconds=min(60, 2 ** run.attempt))
        run.progress = {"stage": "retry_scheduled", "percent": 0}
        action = "retry_scheduled"
    else:
        run.state = "failed"
        run.progress = {"stage": "failed", "percent": 100}
        run.completed_at = now
        action = "failed"
    await publish_project_event(
        session,
        project_id=run.project_id,
        actor_source="workflow_worker",
        resource_type="workflow_run",
        resource_id=run.id,
        resource_revision=run.attempt,
        action=action,
        payload={"workflow_type": run.workflow_type, "state": run.state},
        deduplication_key=f"workflow-run:{run.id}:{action}:{run.attempt}",
        locked_project=await _locked_project(session, run.project_id),
    )
    await session.commit()
    return run


async def cancel_workflow_run(
    session: AsyncSession, *, project_id: uuid.UUID, run_id: uuid.UUID
) -> WorkflowRun:
    result = await session.execute(
        select(WorkflowRun)
        .where(WorkflowRun.id == run_id, WorkflowRun.project_id == project_id)
        .with_for_update()
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise WorkflowRunNotFound(str(run_id))
    if run.state in TERMINAL_STATES:
        return run
    run.cancel_requested = True
    action = "cancel_requested"
    if run.state == "queued":
        run.state = "cancelled"
        run.completed_at = datetime.now(UTC)
        run.progress = {"stage": "cancelled", "percent": 100}
        action = "cancelled"
    else:
        run.progress = {"stage": "cancelling", "percent": run.progress.get("percent", 1)}
    # Commit the cooperative flag before taking the project-event cursor lock.
    # A workflow may already hold an FK key-share lock while preparing an
    # artefact; reversing that order would make cancellation wait for publish.
    await session.commit()
    if action == "cancel_requested":
        return run
    await publish_project_event(
        session,
        project_id=project_id,
        actor_source="workflow_run",
        resource_type="workflow_run",
        resource_id=run.id,
        resource_revision=run.attempt,
        action=action,
        payload={"workflow_type": run.workflow_type, "state": run.state},
        deduplication_key=f"workflow-run:{run.id}:{action}",
    )
    await session.commit()
    return run


async def mark_cancelled_after_rollback(
    session: AsyncSession, *, run_id: uuid.UUID, worker_id: str
) -> WorkflowRun:
    run = await _lock_project_then_run(session, run_id)
    if run.lock_owner != worker_id or run.state != "running":
        raise WorkflowRunConflict("Workflow run lease is no longer owned by this worker")
    run.state = "cancelled"
    run.cancel_requested = True
    run.progress = {"stage": "cancelled", "percent": 100}
    run.completed_at = datetime.now(UTC)
    run.lock_owner = None
    run.lease_expires_at = None
    project = await _locked_project(session, run.project_id)
    await publish_project_event(
        session,
        project_id=run.project_id,
        actor_source="workflow_worker",
        resource_type="workflow_run",
        resource_id=run.id,
        resource_revision=run.attempt,
        action="cancelled",
        payload={"workflow_type": run.workflow_type, "state": "cancelled"},
        deduplication_key=f"workflow-run:{run.id}:cancelled",
        locked_project=project,
    )
    await session.commit()
    return run


def _validate_expected_snapshot(
    snapshot: ProjectSnapshot, request: WorkflowRunStartRequest
) -> None:
    conflicts: list[str] = []
    if snapshot.content_fingerprint != request.expected_snapshot_fingerprint:
        conflicts.append("snapshot fingerprint")
    if snapshot.profile.profile_revision != request.expected_profile_revision:
        conflicts.append("profile revision")
    if snapshot.decisions.set_revision != request.expected_decision_set_revision:
        conflicts.append("decision set revision")
    if conflicts:
        raise WorkflowRunCapabilityConflict(
            f"Workflow inputs changed: {', '.join(conflicts)}"
        )


async def _find_idempotent_run(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    workflow_type: str,
    idempotency_key: str,
) -> WorkflowRun | None:
    result = await session.execute(
        select(WorkflowRun).where(
            WorkflowRun.project_id == project_id,
            WorkflowRun.workflow_type == workflow_type,
            WorkflowRun.idempotency_key == idempotency_key,
        )
    )
    return result.scalar_one_or_none()


def _require_matching_request(run: WorkflowRun, request_hash: str) -> None:
    if run.canonical_request_hash != request_hash:
        raise WorkflowRunConflict(
            "Idempotency key was already used with different workflow inputs"
        )


async def _locked_project(session: AsyncSession, project_id: uuid.UUID) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id).with_for_update()
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise WorkflowRunNotFound(str(project_id))
    return project


async def _lock_project_then_run(
    session: AsyncSession, run_id: uuid.UUID
) -> WorkflowRun:
    project_id_result = await session.execute(
        select(WorkflowRun.project_id).where(WorkflowRun.id == run_id)
    )
    project_id = project_id_result.scalar_one_or_none()
    if project_id is None:
        raise WorkflowRunNotFound(str(run_id))
    await _locked_project(session, project_id)
    result = await session.execute(
        select(WorkflowRun).where(WorkflowRun.id == run_id).with_for_update()
    )
    run = result.scalar_one()
    return run


def _result_reference(
    run: WorkflowRun, result: dict[str, Any], artefact_id: uuid.UUID | None
) -> dict[str, Any]:
    reference: dict[str, Any] = {
        "run_id": str(run.id),
        "workflow_type": run.workflow_type,
    }
    draft = result.get("draft")
    if artefact_id and isinstance(draft, dict):
        reference.update(
            {
                "resource_type": "draft",
                "resource_id": str(artefact_id),
                "revision": draft.get("version"),
                "workspace_path": draft.get("workspace_path"),
            }
        )
    return reference


def _trace_durations(result: dict[str, Any]) -> dict[str, int]:
    trace = result.get("trace")
    if not isinstance(trace, list):
        return {}
    durations: dict[str, int] = {}
    for item in trace:
        if not isinstance(item, dict):
            continue
        step = item.get("step")
        duration = item.get("duration_ms")
        if isinstance(step, str) and isinstance(duration, int) and duration >= 0:
            durations[step] = duration
    return durations


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_uuid(value: object) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None
