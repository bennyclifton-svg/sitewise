from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.project_snapshot import ProjectSnapshot
from app.schemas.workflow_runs import WorkflowRunStartRequest
from app.workflows.runs import canonical_request_hash
from app.workflows.worker import _json_result
from app.workflows.consultant_procurement import ConsultantProcurementResult
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

    assert canonical_request_hash("create_project_plan", first) == canonical_request_hash(
        "create_project_plan", reordered
    )


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
