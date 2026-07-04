"""Run the Phase 5 Hermes -> TCM acceptance flow.

This is a local gate script, not production app code. It creates a disposable
project in the configured database/storage, drives the real Hermes agent endpoint,
drains the real tender worker, and verifies the report artefact SSE event.

Usage from WSL:

    cd backend
    AGENT_TURN_TOKEN_SECRET=phase5-acceptance \
    AGENT_RUNTIME_ENABLED=true \
    HERMES_BINARY_PATH=/home/bennyclifton/.local/bin/hermes \
    UV_PROJECT_ENVIRONMENT=/home/bennyclifton/.cache/clerk-phase5-wsl-venv \
    uv run python scripts/phase5_acceptance.py
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.database.models  # noqa: F401
from app.api import chat as chat_api
from app.auth.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.database.chat_thread import ChatThread
from app.database.project import Project
from app.database.session import get_session_factory
from app.database.user import User
from app.database.workspace_file import WorkspaceFile
from app.main import fastapi_app
from app.storage.project_files import upload_project_file
from tender.models import (
    TenderComparison,
    TenderJob,
    TenderReport,
    TenderTelemetryEvent,
)
from tender.schemas import QAResolveRequest
from tender.seeds.load import DatabaseSeedStore, load_tender_seeds
from tender.services import continuations, jobs, matrix, qa, telemetry
from tender.worker import HANDLERS

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "tender" / "fixtures"
PILOT_PDFS = {
    "Enmore": FIXTURES / "Enmore.pdf",
    "Kaposi": FIXTURES / "Kaposi.pdf",
    "NexusBuilt": FIXTURES / "NexusBuilt.pdf",
}
PORT = 8765
BASE_URL = f"http://127.0.0.1:{PORT}"
JOB_TIMEOUT_S = 180


@dataclass(frozen=True)
class AcceptanceSeed:
    user_id: uuid.UUID
    project_id: uuid.UUID
    thread_id: uuid.UUID
    run_id: str
    workspace_paths: dict[str, str]


async def main() -> None:
    _configure_runtime()
    seed = await _seed_acceptance_project()
    _install_acceptance_auth(seed.user_id)

    server = uvicorn.Server(
        uvicorn.Config(
            fastapi_app,
            host="127.0.0.1",
            port=PORT,
            log_level="warning",
            lifespan="on",
        )
    )
    server_task = asyncio.create_task(server.serve())
    try:
        await _wait_for_backend()
        first_turn = await _agent_turn(seed, _start_prompt(seed), timeout_s=360)
        _assert_tool_event(first_turn, "list_selected_documents")
        _assert_tool_event(first_turn, "start_tender_comparison")

        comparison = await _latest_comparison(seed.project_id)
        if comparison is None:
            raise RuntimeError("Hermes completed without creating a tender comparison")

        await _drain_worker(comparison.id, timeout_s=1500)
        await _clear_qa_if_needed(comparison.id, seed.user_id)
        await _ensure_report_job(comparison.id)
        await _drain_worker(comparison.id, timeout_s=300)

        report = await _latest_report(comparison.id)
        if report is None:
            raise RuntimeError("TCM completed without creating a tender report")

        matrix_payload = await _matrix_payload(comparison.id)
        if not matrix_payload.get("groups"):
            raise RuntimeError("TCM completed with an empty comparison matrix")
        second_turn = await _agent_turn(seed, _result_prompt(comparison.id), timeout_s=240)
        artefact = _artefact_event(second_turn)
        if artefact is None:
            raise RuntimeError("get_comparison_result did not emit an artefact event")

        ledger = await _timing_ledger(comparison.id)
        _assert_pipeline_stages(ledger)
        _print_result(
            comparison_id=comparison.id,
            report=report,
            artefact=artefact,
            matrix_payload=matrix_payload,
            ledger=ledger,
        )
    finally:
        server.should_exit = True
        await server_task


def _configure_runtime() -> None:
    hermes = shutil.which("hermes") or settings.hermes_binary_path
    settings.agent_runtime_enabled = True
    settings.agent_turn_token_secret = (
        settings.agent_turn_token_secret or "phase5-acceptance-secret"
    )
    settings.agent_mcp_url = f"{BASE_URL}/mcp"
    settings.hermes_binary_path = hermes
    settings.agent_turn_timeout_seconds = max(settings.agent_turn_timeout_seconds, 360)
    settings.tender_worker_inproc_enabled = False
    settings.tender_odl_hybrid_enabled = False


async def _seed_acceptance_project() -> AcceptanceSeed:
    run_id = uuid.uuid4().hex[:12]
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    workspace_paths: dict[str, str] = {}

    async with get_session_factory()() as session:
        await load_tender_seeds(DatabaseSeedStore(session), settings.data_dir / "tender")
        session.add(
            User(
                id=user_id,
                email=f"phase5-{run_id}@example.invalid",
            )
        )
        session.add(
            Project(
                id=project_id,
                owner_user_id=user_id,
                slug=f"phase5-{run_id}",
                title=f"Phase 5 Acceptance {run_id}",
                workspace_path=f"projects/phase5-{run_id}",
                phase="procurement",
                archetype="single_dwelling",
                user_role="client",
                state="NSW",
                status="active",
                project_metadata={"acceptance": "phase5", "run_id": run_id},
            )
        )
        session.add(
            ChatThread(
                id=thread_id,
                user_id=user_id,
                project_id=project_id,
                title="Phase 5 acceptance chat",
            )
        )
        for builder, path in PILOT_PDFS.items():
            content = path.read_bytes()
            workspace_path = f"quotes/{builder}.pdf"
            storage_key = (
                f"acceptance/phase5/{run_id}/{project_id}/quotes/{builder}.pdf"
            )
            await asyncio.to_thread(
                upload_project_file,
                storage_key=storage_key,
                content=content,
                filename=path.name,
            )
            workspace_paths[builder] = workspace_path
            session.add(
                WorkspaceFile(
                    project_id=project_id,
                    workspace_path=workspace_path,
                    filename=path.name,
                    storage_bucket=settings.supabase_storage_bucket,
                    storage_key=storage_key,
                    content_hash=hashlib.sha256(content).hexdigest(),
                    size_bytes=len(content),
                    ingest_status="uploaded",
                )
            )
        await session.commit()

    return AcceptanceSeed(
        user_id=user_id,
        project_id=project_id,
        thread_id=thread_id,
        run_id=run_id,
        workspace_paths=workspace_paths,
    )


def _install_acceptance_auth(user_id: uuid.UUID) -> None:
    current_user = CurrentUser(id=user_id, email=f"{user_id}@example.invalid")
    fastapi_app.dependency_overrides[get_current_user] = lambda: current_user

    async def _allow_entitlement(*_args: Any, **_kwargs: Any) -> None:
        return None

    chat_api.require_active_entitlement = _allow_entitlement


async def _wait_for_backend() -> None:
    async with httpx.AsyncClient(timeout=5) as client:
        for _ in range(80):
            try:
                response = await client.get(f"{BASE_URL}/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.25)
    raise RuntimeError("acceptance backend did not start")


async def _agent_turn(
    seed: AcceptanceSeed,
    prompt: str,
    *,
    timeout_s: int,
) -> list[dict[str, Any]]:
    payload = {
        "threadId": str(seed.thread_id),
        "messages": [{"role": "user", "parts": [{"type": "text", "text": prompt}]}],
    }
    events: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        async with client.stream(
            "POST",
            f"{BASE_URL}/chat/agent/stream",
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line.removeprefix("data: ").strip()
                if raw == "[DONE]":
                    events.append({"type": "done"})
                    continue
                try:
                    events.append(json.loads(raw))
                except json.JSONDecodeError:
                    events.append({"type": "raw", "text": raw})
    return events


def _start_prompt(seed: AcceptanceSeed) -> str:
    quote_lines = "\n".join(
        f"- {builder}: {path}" for builder, path in seed.workspace_paths.items()
    )
    return f"""
Phase 5 acceptance run. Use Clerk MCP tools only.

Project id: {seed.project_id}

First call list_selected_documents for the project. Then call
start_tender_comparison with exactly these quotes:
{quote_lines}

Use this context:
{{"context_version": 1, "state": "NSW", "region": "metro",
"build_type": "new_build", "dwelling_class": "class_1a", "storeys": 2,
"floor_area_m2": 240, "soil_class": "M", "slope_class": "flat",
"bal_rating": "none", "spec_level": "mid",
"notes": "Phase 5 automated acceptance run"}}

After the tool returns, reply only with the comparison id.
""".strip()


def _result_prompt(comparison_id: uuid.UUID) -> str:
    return f"""
Phase 5 acceptance run. Use Clerk MCP tools only.

Call get_comparison_result for comparison id {comparison_id}. After the tool
returns, reply only with RESULT_READY.
""".strip()


def _assert_tool_event(events: list[dict[str, Any]], tool: str) -> None:
    for event in events:
        if event.get("type") != "data-clerk-status":
            continue
        data = event.get("data") or {}
        if data.get("kind") == "tool" and data.get("tool") == tool:
            return
    raise RuntimeError(f"Hermes did not call expected tool: {tool}")


def _artefact_event(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for event in events:
        if event.get("type") != "data-clerk-status":
            continue
        data = event.get("data") or {}
        if data.get("kind") == "artefact" and data.get("workflowType") == "tender_report":
            return data
    return None


async def _latest_comparison(project_id: uuid.UUID) -> TenderComparison | None:
    async with get_session_factory()() as session:
        result = await session.execute(
            select(TenderComparison)
            .where(TenderComparison.project_id == project_id)
            .order_by(TenderComparison.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def _latest_report(comparison_id: uuid.UUID) -> TenderReport | None:
    async with get_session_factory()() as session:
        result = await session.execute(
            select(TenderReport)
            .where(TenderReport.comparison_id == comparison_id)
            .order_by(TenderReport.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def _drain_worker(comparison_id: uuid.UUID, *, timeout_s: int) -> None:
    deadline = time.monotonic() + timeout_s
    worker_count = max(1, settings.tender_worker_concurrency)
    stop_event = asyncio.Event()
    ingest_lock = asyncio.Lock()
    active_lanes: set[str] = set()
    lanes = [
        asyncio.create_task(
            _drain_worker_lane(
                comparison_id,
                worker_id=f"phase5-acceptance-{index + 1}",
                stop_event=stop_event,
                deadline=deadline,
                ingest_lock=ingest_lock,
                active_lanes=active_lanes,
            )
        )
        for index in range(worker_count)
    ]
    try:
        while time.monotonic() < deadline:
            counts = await _job_counts(comparison_id)
            if counts.get("failed", 0):
                raise RuntimeError(
                    f"tender job failed: {await _failed_jobs(comparison_id)}"
                )
            if (
                not counts.get("queued", 0)
                and not counts.get("running", 0)
                and not active_lanes
            ):
                await asyncio.sleep(1.0)
                counts = await _job_counts(comparison_id)
                if (
                    not counts.get("queued", 0)
                    and not counts.get("running", 0)
                    and not active_lanes
                ):
                    return
            await asyncio.sleep(0.5)
        raise RuntimeError(f"tender worker did not drain within {timeout_s}s")
    finally:
        stop_event.set()
        for lane in lanes:
            lane.cancel()
        await asyncio.gather(*lanes, return_exceptions=True)


async def _drain_worker_lane(
    comparison_id: uuid.UUID,
    *,
    worker_id: str,
    stop_event: asyncio.Event,
    deadline: float,
    ingest_lock: asyncio.Lock,
    active_lanes: set[str],
) -> None:
    idle_rounds = 0
    while not stop_event.is_set() and time.monotonic() < deadline:
        ready_kinds = await _ready_job_kinds(comparison_id)
        if not ready_kinds:
            idle_rounds += 1
            await asyncio.sleep(0.25)
            continue

        idle_rounds = 0
        if "ingest_document" in ready_kinds:
            if ingest_lock.locked():
                await asyncio.sleep(0.25)
                continue
            async with ingest_lock:
                await _run_or_idle(
                    comparison_id,
                    worker_id=worker_id,
                    active_lanes=active_lanes,
                )
        else:
            await _run_or_idle(
                comparison_id,
                worker_id=worker_id,
                active_lanes=active_lanes,
            )


async def _run_or_idle(
    comparison_id: uuid.UUID,
    *,
    worker_id: str,
    active_lanes: set[str],
) -> None:
    active_lanes.add(worker_id)
    try:
        processed = await _run_once_for_comparison(comparison_id, worker_id=worker_id)
    finally:
        active_lanes.discard(worker_id)
    if not processed:
        await asyncio.sleep(0.25)


async def _run_once_for_comparison(
    comparison_id: uuid.UUID,
    *,
    worker_id: str,
) -> bool:
    async with get_session_factory()() as session:
        result = await session.execute(
            select(TenderJob)
            .where(
                TenderJob.comparison_id == comparison_id,
                TenderJob.status == "queued",
                TenderJob.run_after <= func.now(),
            )
            .order_by(TenderJob.run_after)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = result.scalars().first()
        if job is None:
            return False

        job.status = "running"
        job.locked_at = datetime.now(timezone.utc)
        job.locked_by = worker_id
        await session.commit()

        handler = HANDLERS.get(job.kind)
        job_id = job.id
        job_kind = job.kind
        if handler is None:
            await telemetry.record_stage_timing(
                session,
                comparison_id=comparison_id,
                job_id=job_id,
                stage=job_kind,
                duration_ms=0,
                status="failed",
                metadata={"error": "unknown job kind"},
            )
            await jobs.fail(session, job, f"unknown job kind: {job_kind!r}")
            return True

        started = time.perf_counter()
        try:
            await asyncio.wait_for(handler(session, job), timeout=JOB_TIMEOUT_S)
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            await session.rollback()
            await telemetry.record_stage_timing(
                session,
                comparison_id=comparison_id,
                job_id=job_id,
                stage=job_kind,
                duration_ms=duration_ms,
                status="failed",
                metadata={"error": str(exc)},
            )
            await jobs.fail(session, job, str(exc))
            return True

        duration_ms = int((time.perf_counter() - started) * 1000)
        await telemetry.record_stage_timing(
            session,
            comparison_id=comparison_id,
            job_id=job_id,
            stage=job_kind,
            duration_ms=duration_ms,
            status="done",
        )
        await jobs.complete(session, job)
        await continuations.after_job_complete(
            session,
            job_id=job_id,
            job_kind=job_kind,
            comparison_id=comparison_id,
        )
        return True


async def _job_counts(comparison_id: uuid.UUID) -> dict[str, int]:
    async with get_session_factory()() as session:
        result = await session.execute(
            select(TenderJob.status, func.count())
            .where(TenderJob.comparison_id == comparison_id)
            .group_by(TenderJob.status)
        )
        return {status: count for status, count in result.all()}


async def _ready_job_kinds(comparison_id: uuid.UUID) -> list[str]:
    async with get_session_factory()() as session:
        result = await session.execute(
            select(TenderJob.kind)
            .where(
                TenderJob.comparison_id == comparison_id,
                TenderJob.status == "queued",
                TenderJob.run_after <= func.now(),
            )
            .order_by(TenderJob.run_after)
        )
        return list(result.scalars())


async def _failed_jobs(comparison_id: uuid.UUID) -> list[dict[str, Any]]:
    async with get_session_factory()() as session:
        result = await session.execute(
            select(TenderJob).where(
                TenderJob.comparison_id == comparison_id,
                TenderJob.status == "failed",
            )
        )
        return [
            {"kind": job.kind, "attempts": job.attempts, "last_error": job.last_error}
            for job in result.scalars()
        ]


async def _clear_qa_if_needed(comparison_id: uuid.UUID, user_id: uuid.UUID) -> None:
    async with get_session_factory()() as session:
        pending = await qa.list_review_items(session, comparison_id=comparison_id)
        for item in pending:
            if item.entity_type == "document_classification":
                request = QAResolveRequest(
                    action="correct",
                    corrected_value={"doc_type": "quote_letter"},
                    reason="Phase 5 acceptance auto-clear",
                )
            else:
                request = QAResolveRequest(
                    action="accept",
                    reason="Phase 5 acceptance auto-clear",
                )
            await qa.resolve_qa_item(
                session,
                item_id=item.id,
                reviewer_id=user_id,
                request=request,
            )
        await session.commit()


async def _ensure_report_job(comparison_id: uuid.UUID) -> None:
    if await _latest_report(comparison_id) is not None:
        return
    async with get_session_factory()() as session:
        await jobs.enqueue(
            session,
            kind="assemble_report_draft",
            comparison_id=comparison_id,
            payload={"phase5_acceptance": True},
        )
        await session.commit()


async def _matrix_payload(comparison_id: uuid.UUID) -> dict[str, Any]:
    async with get_session_factory()() as session:
        payload = await matrix.build_matrix(session, comparison_id=comparison_id)
        return payload.model_dump(mode="json")


async def _timing_ledger(comparison_id: uuid.UUID) -> list[dict[str, Any]]:
    async with get_session_factory()() as session:
        result = await session.execute(
            select(TenderTelemetryEvent)
            .where(TenderTelemetryEvent.comparison_id == comparison_id)
            .order_by(TenderTelemetryEvent.created_at.asc())
        )
        return [
            {
                "stage": row.stage,
                "status": row.status,
                "duration_ms": row.duration_ms,
                "llm_calls": row.llm_calls,
                "input_tokens": row.input_tokens,
                "output_tokens": row.output_tokens,
                "cache_hits": row.cache_hits,
            }
            for row in result.scalars()
        ]


def _assert_pipeline_stages(ledger: list[dict[str, Any]]) -> None:
    required = {
        "run_expectations",
        "infer_silence",
        "run_analysis",
        "generate_flags",
        "assemble_report_draft",
    }
    seen = {row["stage"] for row in ledger if row["status"] == "done"}
    missing = sorted(required - seen)
    if missing:
        raise RuntimeError(f"TCM pipeline skipped required stages: {missing}")


def _print_result(
    *,
    comparison_id: uuid.UUID,
    report: TenderReport,
    artefact: dict[str, Any],
    matrix_payload: dict[str, Any],
    ledger: list[dict[str, Any]],
) -> None:
    print("\nPHASE 5 ACCEPTANCE: GREEN")
    print(f"comparison_id={comparison_id}")
    print(f"report_id={report.id}")
    print(f"draft_id={report.draft_id}")
    print(f"artefact_title={artefact.get('title')}")
    print(f"matrix_groups={len(matrix_payload.get('groups', []))}")
    print("\nstage | status | duration_ms | llm_calls | input_tokens | output_tokens | cache_hits")
    print("--- | --- | ---: | ---: | ---: | ---: | ---:")
    for row in ledger:
        print(
            f"{row['stage']} | {row['status']} | {row['duration_ms']} | "
            f"{row['llm_calls']} | {row['input_tokens']} | "
            f"{row['output_tokens']} | {row['cache_hits']}"
        )


if __name__ == "__main__":
    asyncio.run(main())
