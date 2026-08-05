from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.cost_plan.models import CostInvoice
from app.database.project import Project
from app.database.draft_artifact import DraftArtifact
from app.database.user import User
from app.database.workflow_run import WorkflowRun
from app.schemas.project_snapshot import ProjectSnapshot
from app.schemas.workflow_runs import WorkflowRunStartRequest
from app.workflows.runs import (
    WorkflowRunConflict,
    WorkflowRunNotFound,
    cancel_workflow_run,
    claim_next_run,
    get_workflow_run,
    heartbeat_run,
    start_workflow_run,
)
from app.workflows import worker as workflow_worker
from tests.conftest import run_async


def _snapshot(project_id: uuid.UUID, revision: int = 1) -> ProjectSnapshot:
    return ProjectSnapshot.model_validate(
        {
            "generated_at": datetime.now(UTC),
            "content_fingerprint": f"{revision:064x}",
            "identity": {
                "project_id": project_id,
                "title": "Stage 5",
                "slug": f"stage5-{project_id}",
                "workspace_path": f"projects/{project_id}",
                "phase": "procurement",
                "status": "active",
                "site_address": {"status": "needs_input"},
                "client": {"status": "needs_input"},
            },
            "profile": {
                "project_id": project_id,
                "profile_revision": revision,
                "building_class": "residential",
                "work_type": "refurb",
                "subclasses": ["house"],
                "scale": {},
                "complexity": {},
                "work_scope": [],
                "user_role": "architect-pm",
                "state": "NSW",
            },
            "decisions": {"set_revision": revision, "items": []},
            "evidence": {
                "fingerprint": f"{revision + 100:064x}",
                "active_count": 0,
                "fingerprint_complete": True,
                "ingest_failure_count": 0,
                "ingest_failures": [],
            },
            "confirmed_inputs": {},
            "open_profile_proposals": [],
        }
    )


def _request(snapshot: ProjectSnapshot, key: str, **parameters) -> WorkflowRunStartRequest:
    return WorkflowRunStartRequest(
        idempotency_key=key,
        expected_snapshot_fingerprint=snapshot.content_fingerprint,
        expected_profile_revision=snapshot.profile.profile_revision,
        expected_decision_set_revision=snapshot.decisions.set_revision,
        parameters=parameters,
    )


@pytest.mark.integration
def test_workflow_run_idempotency_claim_recovery_cancellation_and_tenancy() -> None:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if os.environ.get("ALLOW_DESTRUCTIVE_TEST_DATABASE") != "1" or not database_url:
        pytest.skip("requires an explicitly opted-in disposable PostgreSQL database")
    async_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    async def exercise() -> None:
        engine = create_async_engine(async_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid.uuid4()
        project_ids = [uuid.uuid4(), uuid.uuid4()]
        async with factory() as session, session.begin():
            await session.execute(delete(WorkflowRun))
            session.add(User(id=user_id, email=f"stage5-{user_id}@example.com"))
            for project_id in project_ids:
                session.add(
                    Project(
                        id=project_id,
                        owner_user_id=user_id,
                        slug=f"stage5-{project_id}",
                        title="Stage 5",
                        workspace_path=f"projects/{project_id}",
                        phase="procurement",
                        building_class="residential",
                        work_type="refurb",
                        user_role="architect-pm",
                        state="NSW",
                        status="active",
                        project_metadata={},
                    )
                )

        snapshot = _snapshot(project_ids[0])
        async with factory() as session, session.begin():
            project = await session.get(Project, project_ids[0])
            assert project is not None
            first, created = await start_workflow_run(
                session,
                project=project,
                user_id=user_id,
                workflow_type="create_project_plan",
                request=_request(snapshot, "same-key"),
                snapshot=snapshot,
            )
            replay, replay_created = await start_workflow_run(
                session,
                project=project,
                user_id=user_id,
                workflow_type="create_project_plan",
                request=_request(snapshot, "same-key"),
                snapshot=snapshot,
            )
            assert created is True
            assert replay_created is False
            assert replay.id == first.id
            with pytest.raises(WorkflowRunConflict):
                await start_workflow_run(
                    session,
                    project=project,
                    user_id=user_id,
                    workflow_type="create_project_plan",
                    request=_request(snapshot, "same-key", changed=True),
                    snapshot=snapshot,
                )
            second, _ = await start_workflow_run(
                session,
                project=project,
                user_id=user_id,
                workflow_type="sort_project_files",
                request=_request(snapshot, "second-key"),
                snapshot=snapshot,
            )

        async def claim(worker: str):
            async with factory() as session:
                return await claim_next_run(session, worker_id=worker, lease_seconds=1)

        claimed = await asyncio.gather(claim("worker-a"), claim("worker-b"))
        assert {run.id for run in claimed if run is not None} == {first.id, second.id}

        async with factory() as session, session.begin():
            abandoned = await session.get(WorkflowRun, first.id)
            other = await session.get(WorkflowRun, second.id)
            assert abandoned is not None
            assert other is not None
            abandoned.state = "running"
            abandoned.cancel_requested = False
            abandoned.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            other.lease_expires_at = datetime.now(UTC) + timedelta(minutes=5)
            previous_attempt = abandoned.attempt
        recovered = await claim("worker-recovery")
        assert recovered is not None
        assert recovered.id == first.id
        assert recovered.attempt == previous_attempt + 1

        async with factory() as session:
            queued = await session.get(WorkflowRun, second.id)
            assert queued is not None
            queued.state = "queued"
            queued.lock_owner = None
            queued.lease_expires_at = None
            cancelled = await cancel_workflow_run(
                session, project_id=project_ids[0], run_id=second.id
            )
            assert cancelled.state == "cancelled"

        async with factory() as session:
            with pytest.raises(WorkflowRunNotFound):
                await get_workflow_run(
                    session, project_id=project_ids[1], run_id=first.id
                )

        await engine.dispose()

    run_async(exercise())


@pytest.mark.integration
def test_heartbeat_does_not_block_on_uncommitted_invoice_booking() -> None:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if os.environ.get("ALLOW_DESTRUCTIVE_TEST_DATABASE") != "1" or not database_url:
        pytest.skip("requires an explicitly opted-in disposable PostgreSQL database")
    async_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    async def exercise() -> None:
        engine = create_async_engine(async_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        user_id, project_id = uuid.uuid4(), uuid.uuid4()
        worker_id = "invoice-lock-worker"
        try:
            async with factory() as session, session.begin():
                session.add(User(id=user_id, email=f"invoice-lock-{user_id}@example.com"))
                project = Project(
                    id=project_id,
                    owner_user_id=user_id,
                    slug=f"invoice-lock-{project_id}",
                    title="Invoice lock regression",
                    workspace_path=f"projects/{project_id}",
                    phase="construction",
                    building_class="residential",
                    work_type="new",
                    user_role="architect-pm",
                    state="NSW",
                    status="active",
                    project_metadata={},
                )
                session.add(project)
                await session.flush()
                session.add(
                    DraftArtifact(
                        project_id=project_id,
                        workflow_type="create_cost_plan",
                        version=1,
                        status="draft",
                        title="Cost Plan",
                        workspace_path=f"projects/{project_id}/cost-plan-v1.md",
                        author_user_id=user_id,
                        content_markdown="# Cost Plan",
                        runtime="test",
                        provenance_metadata={},
                    )
                )
                snapshot = _snapshot(project_id)
                run, _ = await start_workflow_run(
                    session,
                    project=project,
                    user_id=user_id,
                    workflow_type="process_invoices",
                    request=_request(snapshot, "invoice-lock").model_copy(
                        update={"expected_artefact_version": 1}
                    ),
                    snapshot=snapshot,
                )

            async with factory() as claim_session:
                claimed = await claim_next_run(
                    claim_session,
                    worker_id=worker_id,
                    lease_seconds=90,
                )
            assert claimed is not None
            assert claimed.id == run.id

            async with factory() as invoice_session:
                invoice_session.add(
                    CostInvoice(
                        project_id=project_id,
                        source_content_hash="a" * 64,
                        source_locator="projects/invoice-lock/_inbox/invoice.pdf",
                        supplier_name="Example Supplier",
                        supplier_key="examplesupplier",
                        invoice_number="INV-001",
                        invoice_key="inv001",
                        invoice_date=date(2026, 8, 1),
                        billing_month=date(2026, 8, 1),
                        subtotal_ex_gst=Decimal("100.00"),
                        gst=Decimal("10.00"),
                        total_including_gst=Decimal("110.00"),
                        processed_by_workflow_run_id=run.id,
                        created_by_user_id=user_id,
                    )
                )
                await invoice_session.flush()

                async with factory() as heartbeat_session:
                    await heartbeat_session.execute(
                        text("SET LOCAL statement_timeout = '1s'")
                    )
                    alive = await heartbeat_run(
                        heartbeat_session,
                        run_id=run.id,
                        worker_id=worker_id,
                        progress={"stage": "extracting_and_mapping", "percent": 50},
                        lease_seconds=90,
                    )
                assert alive is True

                await invoice_session.rollback()
        finally:
            await engine.dispose()

    run_async(exercise())


@pytest.mark.integration
def test_worker_cancellation_rolls_back_unpublished_artefact(monkeypatch) -> None:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if os.environ.get("ALLOW_DESTRUCTIVE_TEST_DATABASE") != "1" or not database_url:
        pytest.skip("requires an explicitly opted-in disposable PostgreSQL database")
    async_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    async def exercise() -> None:
        engine = create_async_engine(async_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        user_id, project_id = uuid.uuid4(), uuid.uuid4()
        async with factory() as session, session.begin():
            await session.execute(delete(WorkflowRun))
            session.add(User(id=user_id, email=f"stage5-cancel-{user_id}@example.com"))
            project = Project(
                id=project_id,
                owner_user_id=user_id,
                slug=f"stage5-cancel-{project_id}",
                title="Stage 5 cancellation",
                workspace_path=f"projects/{project_id}",
                phase="procurement",
                building_class="residential",
                work_type="refurb",
                user_role="architect-pm",
                state="NSW",
                status="active",
                project_metadata={},
            )
            session.add(project)
            await session.flush()
            snapshot = _snapshot(project_id)
            run, _ = await start_workflow_run(
                session,
                project=project,
                user_id=user_id,
                workflow_type="create_project_plan",
                request=_request(snapshot, "cancel-key"),
                snapshot=snapshot,
            )

        dispatch_started = asyncio.Event()
        release_dispatch = asyncio.Event()
        draft_id = uuid.uuid4()

        async def fake_dispatch(session, claimed_run, on_preview=None):
            session.add(
                DraftArtifact(
                    id=draft_id,
                    project_id=project_id,
                    workflow_type="create_pmp",
                    version=1,
                    status="draft",
                    title="Must roll back",
                    workspace_path=f"projects/{project_id}/pmp-v1.md",
                    author_user_id=user_id,
                    content_markdown="# Must roll back",
                    runtime="test",
                    provenance_metadata={},
                )
            )
            await session.flush()
            dispatch_started.set()
            await release_dispatch.wait()
            return {"status": "complete", "draft": {"id": str(draft_id), "version": 1}}

        monkeypatch.setattr(workflow_worker, "_dispatch", fake_dispatch)
        worker_task = asyncio.create_task(
            workflow_worker.run_once(factory, "cancellation-worker")
        )
        await asyncio.wait_for(dispatch_started.wait(), timeout=5)
        async with factory() as session:
            await cancel_workflow_run(session, project_id=project_id, run_id=run.id)
        release_dispatch.set()
        assert await asyncio.wait_for(worker_task, timeout=5) is True

        async with factory() as session:
            persisted = await session.get(WorkflowRun, run.id)
            assert persisted is not None
            assert persisted.state == "cancelled"
            assert await session.get(DraftArtifact, draft_id) is None
        await engine.dispose()

    run_async(exercise())
