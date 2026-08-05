from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.cost_plan.schemas import CostItemInput
from app.schemas.project_snapshot import ProjectSnapshot
from app.schemas.workflow_runs import WorkflowRunStartRequest
from app.workflows.runs import (
    SUPPORTED_WORKFLOWS,
    canonical_request_hash,
    complete_workflow_run,
    heartbeat_run,
)
from app.workflows.worker import _json_result
from app.workflows.document_ingest import DocumentIngestResult
from app.workflows.consultant_procurement import ConsultantProcurementResult
from app.workflows.contractor_procurement import ContractorEoiResult
from app.workflows.trade_procurement import TradeProcurementResult
from app.workflows import worker as workflow_worker
from tests.conftest import run_async
from unittest.mock import AsyncMock, patch
import uuid
from types import SimpleNamespace


def _request(**overrides) -> WorkflowRunStartRequest:
    values = {
        "idempotency_key": "turn-1:create-project-plan",
        "expected_snapshot_fingerprint": "a" * 64,
        "expected_profile_revision": 2,
        "expected_decision_set_revision": 3,
        "parameters": {"alpha": 1, "nested": {"b": 2, "a": 1}},
    }
    values.update(overrides)
    return WorkflowRunStartRequest.model_validate(values)


def _snapshot() -> ProjectSnapshot:
    return ProjectSnapshot.model_validate(
        {
            "generated_at": datetime.now(UTC),
            "content_fingerprint": "a" * 64,
            "identity": {
                "project_id": "00000000-0000-0000-0000-000000000001",
                "title": "Test",
                "slug": "test",
                "workspace_path": "04-projects/test",
                "phase": "procurement",
                "status": "active",
                "site_address": {"status": "needs_input"},
                "client": {"status": "needs_input"},
            },
            "profile": {
                "project_id": "00000000-0000-0000-0000-000000000001",
                "profile_revision": 2,
                "building_class": "residential",
                "work_type": "refurb",
                "subclasses": ["house"],
                "scale": {},
                "complexity": {},
                "work_scope": [],
                "user_role": "architect-pm",
                "state": "NSW",
            },
            "decisions": {"set_revision": 3, "items": []},
            "evidence": {
                "fingerprint": "b" * 64,
                "active_count": 0,
                "fingerprint_complete": True,
                "ingest_failure_count": 0,
                "ingest_failures": [],
            },
            "confirmed_inputs": {},
            "open_profile_proposals": [],
        }
    )


def test_canonical_request_hash_is_order_independent_and_excludes_key() -> None:
    first = _request()
    reordered = _request(
        idempotency_key="different-key",
        parameters={"nested": {"a": 1, "b": 2}, "alpha": 1},
    )

    assert canonical_request_hash(
        "create_project_plan", first
    ) == canonical_request_hash("create_project_plan", reordered)


def test_canonical_request_hash_changes_with_frozen_input_or_workflow() -> None:
    request = _request()

    assert canonical_request_hash(
        "create_project_plan", request
    ) != canonical_request_hash("create_cost_plan", request)
    assert canonical_request_hash(
        "create_project_plan", request
    ) != canonical_request_hash(
        "create_project_plan", _request(expected_profile_revision=4)
    )


def test_snapshot_fixture_carries_all_frozen_revision_inputs() -> None:
    snapshot = _snapshot()

    assert snapshot.profile.profile_revision == 2
    assert snapshot.decisions.set_revision == 3
    assert snapshot.evidence.fingerprint == "b" * 64


def test_successful_retry_clears_stale_workflow_error_fields() -> None:
    run = SimpleNamespace(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        workflow_type="process_invoices",
        attempt=2,
        state="running",
        result=None,
        result_artefact_id=None,
        result_reference=None,
        progress={},
        stage_durations_ms={},
        error_class="RuntimeError",
        error_message="Unknown workflow type: process_invoices",
        completed_at=None,
        lock_owner="worker-1",
        lease_expires_at=datetime.now(UTC),
    )

    with patch(
        "app.workflows.runs.publish_project_event", new=AsyncMock(return_value=None)
    ):
        run_async(
            complete_workflow_run(
                AsyncMock(),
                run=run,
                result={"status": "complete"},
                duration_ms=125,
            )
        )

    assert run.state == "complete"
    assert run.error_class is None
    assert run.error_message is None


def test_contractor_eoi_is_supported_by_durable_run_boundary() -> None:
    assert "contractor_eoi" in SUPPORTED_WORKFLOWS


def test_trade_procurement_is_supported_by_durable_run_boundary() -> None:
    assert "trade_procurement" in SUPPORTED_WORKFLOWS


def test_document_ingest_is_supported_by_durable_run_boundary() -> None:
    assert "ingest_project_document" in SUPPORTED_WORKFLOWS


def test_consultant_result_serialization_does_not_copy_sqlalchemy_state() -> None:
    draft = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000010",
        project_id="00000000-0000-0000-0000-000000000001",
        workflow_type="consultant_procurement_structural_engineer",
        version=1,
        status="draft",
        title="Structural engineer RFP",
        workspace_path="04-projects/test/02-consultant/structural-rfp.md",
    )

    payload = _json_result(
        ConsultantProcurementResult(
            draft=draft,
            discipline="Structural engineer",
            source_trace={"project_documents": []},
        )
    )

    assert payload["status"] == "complete"
    assert payload["draft"]["id"] == draft.id


def test_dispatches_contractor_eoi_to_durable_draft(monkeypatch) -> None:
    draft = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000010",
        project_id="00000000-0000-0000-0000-000000000001",
        workflow_type="contractor_eoi_main_works",
        version=1,
        status="draft",
        title="Expression of Interest - Main Works",
        workspace_path=(
            "04-projects/test/02-procurement/contractor_eoi_main_works_v01.draft.md"
        ),
    )
    run = SimpleNamespace(
        workflow_type="contractor_eoi",
        requested_by_user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        requested_by_thread_id=None,
        frozen_artefact_version=None,
        run_brief={
            "snapshot": _snapshot().model_dump(mode="json"),
            "project": {
                "id": "00000000-0000-0000-0000-000000000001",
                "owner_user_id": "00000000-0000-0000-0000-000000000002",
                "slug": "test",
                "title": "Test",
                "workspace_path": "04-projects/test",
                "phase": "procurement",
                "status": "active",
            },
            "parameters": {"package": "Main Works", "max_pages": 1},
        },
    )
    draft_eoi = AsyncMock(
        return_value=ContractorEoiResult(
            draft=draft,
            package="Main Works",
            source_trace={"project_documents": []},
        )
    )
    monkeypatch.setattr(workflow_worker, "draft_contractor_eoi_artifact", draft_eoi)
    attach_request = AsyncMock(
        return_value=SimpleNamespace(
            id=uuid.UUID("00000000-0000-0000-0000-000000000020"),
            kind="contractor_eoi",
        )
    )
    monkeypatch.setattr(workflow_worker, "attach_generated_draft", attach_request)

    payload = run_async(workflow_worker._dispatch(AsyncMock(), run))

    assert payload["draft"]["workflow_type"] == "contractor_eoi_main_works"
    assert payload["draft"]["workspace_path"].endswith(
        "/02-procurement/contractor_eoi_main_works_v01.draft.md"
    )
    assert draft_eoi.await_args.kwargs["auto_commit"] is False
    assert payload["procurement_request_id"] == "00000000-0000-0000-0000-000000000020"


def test_dispatches_trade_procurement_to_durable_draft(monkeypatch) -> None:
    draft = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000010",
        project_id="00000000-0000-0000-0000-000000000001",
        workflow_type="trade_rfq_electrical_services",
        version=1,
        status="draft",
        title="Request for Quotation - Electrical Services",
        workspace_path=(
            "04-projects/test/05-procurement/electrical_services/02-tender-pack/"
            "electrical_services_rfq_v01.draft.md"
        ),
    )
    run = SimpleNamespace(
        workflow_type="trade_procurement",
        requested_by_user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        requested_by_thread_id=None,
        frozen_artefact_version=None,
        run_brief={
            "snapshot": _snapshot().model_dump(mode="json"),
            "project": {
                "id": "00000000-0000-0000-0000-000000000001",
                "owner_user_id": "00000000-0000-0000-0000-000000000002",
                "slug": "test",
                "title": "Test",
                "workspace_path": "04-projects/test",
                "phase": "procurement",
                "status": "active",
            },
            "parameters": {"package": "Electrical", "kind": "rfq", "max_pages": 3},
        },
    )
    draft_trade = AsyncMock(
        return_value=TradeProcurementResult(
            draft=draft,
            package="Electrical Services",
            kind="rfq",
            source_trace={"project_documents": []},
        )
    )
    monkeypatch.setattr(
        workflow_worker, "draft_trade_procurement_artifact", draft_trade
    )
    attach_request = AsyncMock(
        return_value=SimpleNamespace(
            id=uuid.UUID("00000000-0000-0000-0000-000000000020"),
            kind="trade_rfq",
        )
    )
    monkeypatch.setattr(workflow_worker, "attach_generated_draft", attach_request)

    payload = run_async(workflow_worker._dispatch(AsyncMock(), run))

    assert payload["draft"]["workflow_type"] == "trade_rfq_electrical_services"
    assert payload["kind"] == "rfq"
    assert payload["procurement_request_id"] == "00000000-0000-0000-0000-000000000020"
    assert draft_trade.await_args.kwargs["auto_commit"] is False


def test_dispatches_document_ingest_to_the_worker(monkeypatch) -> None:
    workspace_file_id = uuid.UUID("00000000-0000-0000-0000-000000000010")
    run = SimpleNamespace(
        id=uuid.UUID("00000000-0000-0000-0000-000000000011"),
        workflow_type="ingest_project_document",
        requested_by_user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        requested_by_thread_id=None,
        frozen_artefact_version=None,
        run_brief={
            "snapshot": _snapshot().model_dump(mode="json"),
            "project": {
                "id": "00000000-0000-0000-0000-000000000001",
                "owner_user_id": "00000000-0000-0000-0000-000000000002",
                "slug": "test",
                "title": "Test",
                "workspace_path": "04-projects/test",
                "phase": "procurement",
                "status": "active",
            },
            "parameters": {"workspace_file_id": str(workspace_file_id)},
        },
    )
    ingest = AsyncMock(
        return_value=DocumentIngestResult(
            workspace_file_id=str(workspace_file_id), ingest_status="ingested"
        )
    )
    monkeypatch.setattr(workflow_worker, "ingest_project_document", ingest)

    payload = run_async(workflow_worker._dispatch(AsyncMock(), run))

    assert payload["ingest_status"] == "ingested"
    assert ingest.await_args.kwargs["workspace_file_id"] == workspace_file_id


def _running_run(progress: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        state="running",
        lock_owner="worker-1",
        cancel_requested=False,
        progress=progress if progress is not None else {},
        heartbeat_at=None,
        lease_expires_at=None,
    )


def _session_returning(run: SimpleNamespace) -> AsyncMock:
    result = SimpleNamespace(scalar_one_or_none=lambda: run)
    session = AsyncMock()
    session.execute.return_value = result
    return session


def test_heartbeat_keeps_a_published_preview_while_advancing_the_stage() -> None:
    run = _running_run(
        {"stage": "starting", "percent": 1, "preview": {"markdown": "# Draft"}}
    )
    session = _session_returning(run)

    run_async(
        heartbeat_run(
            session,
            run_id=run.id,
            worker_id="worker-1",
            progress={"stage": "executing", "percent": 50},
        )
    )

    assert run.progress == {
        "stage": "executing",
        "percent": 50,
        "preview": {"markdown": "# Draft"},
    }


def test_publishing_a_preview_keeps_the_current_stage() -> None:
    run = _running_run({"stage": "executing", "percent": 50})
    session = _session_returning(run)

    run_async(
        heartbeat_run(
            session,
            run_id=run.id,
            worker_id="worker-1",
            progress={"preview": {"markdown": "# Draft"}},
        )
    )

    assert run.progress == {
        "stage": "executing",
        "percent": 50,
        "preview": {"markdown": "# Draft"},
    }


def test_heartbeat_without_progress_leaves_progress_untouched() -> None:
    run = _running_run({"stage": "executing", "percent": 50})
    session = _session_returning(run)

    run_async(heartbeat_run(session, run_id=run.id, worker_id="worker-1"))

    assert run.progress == {"stage": "executing", "percent": 50}


def _plan_run(workflow_type: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.UUID("00000000-0000-0000-0000-000000000011"),
        workflow_type=workflow_type,
        requested_by_user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        requested_by_thread_id=None,
        frozen_artefact_version=None,
        run_brief={
            "snapshot": _snapshot().model_dump(mode="json"),
            "project": {
                "id": "00000000-0000-0000-0000-000000000001",
                "owner_user_id": "00000000-0000-0000-0000-000000000002",
                "slug": "test",
                "title": "Test",
                "workspace_path": "04-projects/test",
                "phase": "procurement",
                "status": "active",
            },
            "parameters": {},
        },
    )


def test_dispatch_hands_the_project_plan_workflow_its_preview_publisher(
    monkeypatch,
) -> None:
    create_pmp = AsyncMock(return_value=SimpleNamespace(status="complete"))
    monkeypatch.setattr(workflow_worker, "run_create_pmp_workflow", create_pmp)
    monkeypatch.setattr(workflow_worker, "_json_result", lambda result: {})

    async def publisher(preview: dict) -> None:
        return None

    run_async(
        workflow_worker._dispatch(
            AsyncMock(), _plan_run("create_project_plan"), on_preview=publisher
        )
    )

    assert create_pmp.await_args.kwargs["on_preview"] is publisher


def test_dispatch_works_without_a_preview_publisher(monkeypatch) -> None:
    create_pmp = AsyncMock(return_value=SimpleNamespace(status="complete"))
    monkeypatch.setattr(workflow_worker, "run_create_pmp_workflow", create_pmp)
    monkeypatch.setattr(workflow_worker, "_json_result", lambda result: {})

    run_async(workflow_worker._dispatch(AsyncMock(), _plan_run("create_project_plan")))

    assert create_pmp.await_args.kwargs["on_preview"] is None


class _FakeSessionFactory:
    """Hands out the same session for every `async with session_factory()`."""

    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *args):
        return False


def test_preview_publisher_writes_the_preview_onto_the_run() -> None:
    run = _running_run({"stage": "executing", "percent": 50})
    session_factory = _FakeSessionFactory(_session_returning(run))

    publish = workflow_worker._preview_publisher(
        session_factory, run_id=run.id, worker_id="worker-1"
    )
    run_async(publish({"stage": "scaffold", "markdown": "# Draft"}))

    assert run.progress["preview"] == {"stage": "scaffold", "markdown": "# Draft"}
    assert run.progress["stage"] == "executing"


def test_run_once_gives_the_workflow_a_publisher_bound_to_this_run(monkeypatch) -> None:
    run = _running_run()
    run.workflow_type = "create_project_plan"
    session_factory = _FakeSessionFactory(_session_returning(run))
    captured: dict = {}

    async def fake_dispatch(session, dispatched_run, on_preview=None):
        captured["run"] = dispatched_run
        await on_preview({"stage": "scaffold", "markdown": "# Draft"})
        return {"status": "complete"}

    monkeypatch.setattr(workflow_worker, "claim_next_run", AsyncMock(return_value=run))
    monkeypatch.setattr(workflow_worker, "_dispatch", fake_dispatch)
    monkeypatch.setattr(
        workflow_worker, "_stamp_result_dependencies", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        workflow_worker, "lock_run_for_publish", AsyncMock(return_value=run)
    )
    monkeypatch.setattr(
        workflow_worker, "complete_workflow_run", AsyncMock(return_value=None)
    )

    assert run_async(workflow_worker.run_once(session_factory, "worker-1")) is True
    assert captured["run"] is run
    assert run.progress["preview"] == {"stage": "scaffold", "markdown": "# Draft"}


def test_dispatch_hands_the_cost_plan_workflow_its_preview_publisher(
    monkeypatch,
) -> None:
    create_cost_plan = AsyncMock(return_value=SimpleNamespace(status="complete"))
    monkeypatch.setattr(
        workflow_worker, "run_create_cost_plan_workflow", create_cost_plan
    )
    monkeypatch.setattr(workflow_worker, "_json_result", lambda result: {})

    async def publisher(preview: dict) -> None:
        return None

    run_async(
        workflow_worker._dispatch(
            AsyncMock(), _plan_run("create_cost_plan"), on_preview=publisher
        )
    )

    assert create_cost_plan.await_args.kwargs["on_preview"] is publisher


def test_dispatch_process_invoices_uses_the_frozen_cost_plan_version(
    monkeypatch,
) -> None:
    run = _plan_run("process_invoices")
    run.frozen_artefact_version = 8
    process = AsyncMock(
        return_value=SimpleNamespace(status="complete", draft_id=None)
    )
    monkeypatch.setattr(workflow_worker, "process_invoices", process)
    monkeypatch.setattr(
        workflow_worker,
        "_json_result",
        lambda result: {"status": result.status},
    )

    payload = run_async(workflow_worker._dispatch(AsyncMock(), run))

    assert payload == {"status": "complete"}
    assert process.await_args.kwargs["workflow_run_id"] == run.id
    assert process.await_args.kwargs["expected_cost_plan_version"] == 8
    assert process.await_args.kwargs["source_document_ids"] is None


def test_refresh_cost_plan_synchronizes_the_published_workbook(monkeypatch) -> None:
    run = _plan_run("refresh_cost_plan")
    run.frozen_artefact_version = 1
    refreshed_draft = SimpleNamespace(
        id=uuid.UUID("00000000-0000-0000-0000-000000000012"),
        project_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        workflow_type="create_cost_plan",
        version=2,
        status="draft",
        title="Cost Plan",
        workspace_path="04-projects/test/01-cost/cost_plan_v02.md",
        author_user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        content_markdown="# Cost Plan v2",
        model="test-model",
        runtime="test-runtime",
        provenance_metadata={
            "workbook": {
                "file_name": "Cost_Plan_v02.draft.xlsx",
                "workspace_path": "04-projects/test/01-cost/Cost_Plan_v02.draft.xlsx",
            }
        },
        created_at=datetime(2026, 8, 2, tzinfo=UTC),
        updated_at=datetime(2026, 8, 2, tzinfo=UTC),
    )
    state = SimpleNamespace(artefact_revision_id=refreshed_draft.id)
    refresh = AsyncMock(return_value=SimpleNamespace(state=state))
    synchronize = AsyncMock()
    session = AsyncMock()
    session.get.return_value = refreshed_draft
    current_item = CostItemInput(
        item_key="architect",
        cost_code="3",
        category="Consultants",
        item="Architect / PM",
        budget=Decimal("12500"),
        forecast=Decimal("12500"),
        basis="Planning allowance",
    )
    received_item = current_item.model_copy(
        update={
            "budget": Decimal("96000"),
            "forecast": Decimal("96000"),
            "basis": "Received fee proposal",
        }
    )
    read_cost_plan = AsyncMock(return_value=SimpleNamespace(items=[current_item]))
    load_documents = AsyncMock(return_value=[SimpleNamespace(filename="fee.md")])
    reconcile = lambda _base, _documents: SimpleNamespace(  # noqa: E731
        proposed_items=(received_item,),
        received_proposals=(),
        issues=(),
    )
    monkeypatch.setattr(workflow_worker, "refresh_cost_plan", refresh)
    monkeypatch.setattr(workflow_worker, "read_typed_cost_plan", read_cost_plan)
    monkeypatch.setattr(workflow_worker, "load_cost_evidence_documents", load_documents)
    monkeypatch.setattr(workflow_worker, "build_cost_evidence_reconciliation", reconcile)
    monkeypatch.setattr(
        workflow_worker,
        "sync_cost_plan_revision_artifacts",
        synchronize,
        raising=False,
    )
    monkeypatch.setattr(workflow_worker, "_json_result", lambda result: {})

    payload = run_async(workflow_worker._dispatch(session, run))

    assert refresh.await_args.kwargs["proposed_items"] == [received_item]
    synchronize.assert_awaited_once_with(
        session,
        project=refresh.await_args.kwargs["project"],
        draft=refreshed_draft,
        typed_state=state,
    )
    assert payload["draft"]["id"] == str(refreshed_draft.id)
    assert payload["draft"]["provenance_metadata"] == refreshed_draft.provenance_metadata


def test_refresh_cost_plan_rejects_an_empty_evidence_reconciliation(monkeypatch) -> None:
    run = _plan_run("refresh_cost_plan")
    run.frozen_artefact_version = 2
    monkeypatch.setattr(
        workflow_worker,
        "read_typed_cost_plan",
        AsyncMock(return_value=SimpleNamespace(items=[])),
    )
    monkeypatch.setattr(
        workflow_worker,
        "load_cost_evidence_documents",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        workflow_worker,
        "build_cost_evidence_reconciliation",
        lambda _base, _documents: SimpleNamespace(
            proposed_items=(), received_proposals=(), issues=()
        ),
    )
    refresh = AsyncMock()
    monkeypatch.setattr(workflow_worker, "refresh_cost_plan", refresh)

    with pytest.raises(RuntimeError, match="no evidence-backed item changes"):
        run_async(workflow_worker._dispatch(AsyncMock(), run))

    refresh.assert_not_awaited()
