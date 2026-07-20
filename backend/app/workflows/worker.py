from __future__ import annotations

import asyncio
import os
import signal
import socket
import sys
import time
import traceback
import uuid
from contextlib import suppress
from dataclasses import fields, is_dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import app.database.models  # noqa: F401
from app.config import settings
from app.database.project import Project
from app.database.draft_artifact import DraftArtifact
from app.database.session import get_session_factory
from app.logging import configure_logging, get_logger
from app.schemas.project_snapshot import ProjectSnapshot
from app.workflows.consultant_procurement import draft_consultant_procurement_artifact
from app.workflows.create_cost_plan import run_create_cost_plan_workflow
from app.cost_plan.dependencies import dependency_snapshot
from app.cost_plan.schemas import CostItemInput
from app.cost_plan.service import refresh_cost_plan
from app.workflows.create_pmp import run_create_pmp_workflow
from app.workflows.runs import (
    WorkflowRunCancelled,
    claim_next_run,
    complete_workflow_run,
    fail_workflow_run,
    heartbeat_run,
    lock_run_for_publish,
    mark_cancelled_after_rollback,
)
from app.workflows.sort_files import run_sort_files_workflow
from app.workflows.update_pmp import run_update_pmp_workflow

log = get_logger(__name__)


def _frozen_project(run) -> Project:
    raw = run.run_brief["project"]
    snapshot = ProjectSnapshot.model_validate(run.run_brief["snapshot"])
    return Project(
        id=uuid.UUID(raw["id"]),
        owner_user_id=uuid.UUID(raw["owner_user_id"]),
        slug=raw["slug"],
        title=raw["title"],
        workspace_path=raw["workspace_path"],
        phase=raw["phase"],
        status=raw["status"],
        archetype=raw.get("archetype"),
        building_class=snapshot.profile.building_class,
        work_type=snapshot.profile.work_type,
        user_role=snapshot.profile.user_role,
        state=snapshot.profile.state,
        profile_revision=snapshot.profile.profile_revision,
        decision_set_revision=snapshot.decisions.set_revision,
        project_metadata=raw.get("project_metadata"),
    )


async def _dispatch(session: AsyncSession, run) -> dict[str, Any]:
    snapshot = ProjectSnapshot.model_validate(run.run_brief["snapshot"])
    project = _frozen_project(run)
    chat_model = run.run_brief.get("chat_model")
    parameters = run.run_brief.get("parameters") or {}
    common = {
        "session": session,
        "user_id": run.requested_by_user_id,
        "project": project,
        "thread_id": run.requested_by_thread_id,
    }
    if run.workflow_type == "create_project_plan":
        result = await run_create_pmp_workflow(
            **common, chat_model=chat_model, snapshot=snapshot
        )
    elif run.workflow_type == "refresh_project_plan":
        result = await run_update_pmp_workflow(
            **common, chat_model=chat_model, snapshot=snapshot
        )
    elif run.workflow_type == "create_cost_plan":
        result = await run_create_cost_plan_workflow(
            **common, chat_model=chat_model, snapshot=snapshot
        )
    elif run.workflow_type == "refresh_cost_plan":
        result = await refresh_cost_plan(
            session,
            project=project,
            author_user_id=run.requested_by_user_id,
            expected_base_version=run.frozen_artefact_version,
            current_snapshot=snapshot,
            proposed_items=[
                CostItemInput.model_validate(item)
                for item in parameters.get("proposed_items", [])
            ],
            dependency_snapshot=dependency_snapshot(
                snapshot,
                model_version=chat_model,
                prompt_version="typed-refresh-v1",
                runtime_version="clerk-typed-cost-plan-refresh-v1",
            ),
        )
    elif run.workflow_type == "sort_project_files":
        result = await run_sort_files_workflow(**common, auto_commit=False)
    elif run.workflow_type == "consultant_procurement":
        result = await draft_consultant_procurement_artifact(
            session,
            project=project,
            user_id=run.requested_by_user_id,
            discipline=str(parameters["discipline"]),
            max_pages=int(parameters.get("max_pages", 1)),
            instructions=parameters.get("instructions"),
            auto_commit=False,
        )
    else:
        raise ValueError(f"Unknown workflow type: {run.workflow_type}")
    return _json_result(result)


async def _stamp_result_dependencies(
    session: AsyncSession, run, result: dict[str, Any]
) -> None:
    draft_value = result.get("draft")
    if not isinstance(draft_value, dict) or not draft_value.get("id"):
        return
    draft = await session.get(DraftArtifact, uuid.UUID(str(draft_value["id"])))
    if draft is None:
        return
    metadata = dict(draft.provenance_metadata or {})
    if isinstance(metadata.get("dependency_snapshot"), dict):
        return
    upstream: list[dict[str, Any]] = []
    if run.frozen_artefact_version is not None:
        upstream.append(
            {
                "type": "base_revision",
                "workflow_type": draft.workflow_type,
                "version": run.frozen_artefact_version,
            }
        )
    metadata["dependency_snapshot"] = {
        "profile_revision": run.frozen_profile_revision,
        "evidence_fingerprint": run.frozen_evidence_fingerprint,
        "decision_set_revision": run.frozen_decision_set_revision,
        "upstream_artefacts": upstream,
        "model_version": draft.model,
        "prompt_version": metadata.get("prompt_version"),
        "runtime_version": draft.runtime,
    }
    draft.provenance_metadata = metadata
    await session.flush()


def _json_result(result: Any) -> dict[str, Any]:
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if is_dataclass(result):
        raw = {
            field.name: getattr(result, field.name)
            for field in fields(result)
            if field.name != "draft"
        }
        draft = getattr(result, "draft", None)
        if draft is not None:
            raw["draft"] = {
                "id": str(draft.id),
                "project_id": str(draft.project_id),
                "workflow_type": draft.workflow_type,
                "version": draft.version,
                "status": draft.status,
                "title": draft.title,
                "workspace_path": draft.workspace_path,
            }
        raw.setdefault("status", "complete")
        return raw
    raise TypeError(
        f"Workflow returned unsupported result type: {type(result).__name__}"
    )


async def _heartbeat_loop(
    session_factory, run_id: uuid.UUID, worker_id: str, stop: asyncio.Event
) -> None:
    interval = max(1.0, settings.workflow_worker_lease_seconds / 3)
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
            return
        except TimeoutError:
            pass
        async with session_factory() as session:
            alive = await heartbeat_run(
                session,
                run_id=run_id,
                worker_id=worker_id,
                progress={"stage": "executing", "percent": 50},
                lease_seconds=settings.workflow_worker_lease_seconds,
            )
        if not alive:
            return


async def run_once(session_factory, worker_id: str) -> bool:
    async with session_factory() as claim_session:
        run = await claim_next_run(
            claim_session,
            worker_id=worker_id,
            lease_seconds=settings.workflow_worker_lease_seconds,
        )
    if run is None:
        return False

    stop_heartbeat = asyncio.Event()
    heartbeat_task = asyncio.create_task(
        _heartbeat_loop(session_factory, run.id, worker_id, stop_heartbeat),
        name=f"workflow-heartbeat:{run.id}",
    )
    started = time.perf_counter()
    try:
        async with session_factory() as work_session:
            result = await _dispatch(work_session, run)
            await _stamp_result_dependencies(work_session, run, result)
            owned_run = await lock_run_for_publish(
                work_session, run_id=run.id, worker_id=worker_id
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            await complete_workflow_run(
                work_session, run=owned_run, result=result, duration_ms=duration_ms
            )
            await work_session.commit()
    except WorkflowRunCancelled:
        async with session_factory() as cancel_session:
            await mark_cancelled_after_rollback(
                cancel_session, run_id=run.id, worker_id=worker_id
            )
    except Exception as exc:
        log.error(
            "workflow_run_failed",
            run_id=str(run.id),
            workflow_type=run.workflow_type,
            error=traceback.format_exc(),
        )
        async with session_factory() as failure_session:
            await fail_workflow_run(
                failure_session,
                run_id=run.id,
                worker_id=worker_id,
                error=exc,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
    finally:
        stop_heartbeat.set()
        with suppress(asyncio.CancelledError):
            await heartbeat_task
    return True


async def _idle_wait(shutdown_event: asyncio.Event) -> None:
    try:
        await asyncio.wait_for(
            shutdown_event.wait(), timeout=settings.workflow_worker_poll_seconds
        )
    except TimeoutError:
        pass


async def run_lane(
    session_factory, worker_id: str, shutdown_event: asyncio.Event
) -> None:
    while not shutdown_event.is_set():
        try:
            processed = await run_once(session_factory, worker_id)
        except Exception:
            log.error("workflow_worker_lane_error", error=traceback.format_exc())
            processed = False
        if not processed:
            await _idle_wait(shutdown_event)


async def run_pool(
    session_factory, worker_id: str, *, shutdown_event: asyncio.Event, concurrency: int
) -> None:
    await asyncio.gather(
        *(
            run_lane(session_factory, f"{worker_id}#{index}", shutdown_event)
            for index in range(max(1, concurrency))
        )
    )


async def _main() -> None:
    configure_logging()
    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(signum, shutdown_event.set)
    worker_id = f"core:{socket.gethostname()}:{os.getpid()}"
    log.info("workflow_worker_started", worker_id=worker_id)
    await run_pool(
        get_session_factory(),
        worker_id,
        shutdown_event=shutdown_event,
        concurrency=settings.workflow_worker_concurrency,
    )
    log.info("workflow_worker_stopped", worker_id=worker_id)


async def _healthcheck() -> None:
    async with get_session_factory()() as session:
        await session.execute(text("SELECT 1"))


if __name__ == "__main__":
    asyncio.run(_healthcheck() if "--healthcheck" in sys.argv else _main())
