import uuid
import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.projects.project_intelligence import (
    enrich_project_snapshot,
    project_next_actions,
)
from app.schemas.project_snapshot import ProjectSnapshot, ProjectSnapshotSelection


PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _snapshot(**updates: object) -> ProjectSnapshot:
    snapshot = ProjectSnapshot.model_validate(
        {
            "generated_at": datetime(2026, 7, 20, tzinfo=UTC),
            "content_fingerprint": "fingerprint",
            "identity": {
                "project_id": PROJECT_ID,
                "title": "Demo",
                "slug": "demo",
                "workspace_path": "04-projects/demo",
                "phase": "procurement",
                "status": "active",
                "site_address": {"status": "confirmed", "value": "10 Test St"},
                "client": {"status": "confirmed", "value": "Example"},
            },
            "profile": {
                "project_id": PROJECT_ID,
                "profile_revision": 2,
                "building_class": "residential",
                "subclasses": [{"value": "house", "source": "user"}],
                "work_type": "refurb",
                "user_role": "architect-pm",
                "state": "NSW",
                "scale": {},
                "complexity": {},
                "work_scope": [],
            },
            "decisions": {"set_revision": 1, "items": []},
            "evidence": {
                "fingerprint": "evidence",
                "active_count": 2,
                "fingerprint_complete": True,
                "ingest_failure_count": 0,
                "ingest_failures": [],
            },
            "confirmed_inputs": {},
            "open_profile_proposals": [],
        }
    )
    return snapshot.model_copy(update=updates)


def test_next_actions_name_blocking_fact_route_and_tool() -> None:
    actions = project_next_actions(_snapshot())

    assert [item.code for item in actions] == [
        "create_project_plan",
        "create_cost_plan",
        "select_tender_quotes",
    ]
    assert all(item.blocking_fact and item.route and item.tool for item in actions)


def test_unsupported_workflows_are_not_recommended() -> None:
    snapshot = _snapshot()
    snapshot.profile.state = "SA"
    snapshot.profile.building_class = "commercial"

    action_codes = {item.code for item in project_next_actions(snapshot)}

    assert "create_cost_plan" not in action_codes
    assert "select_tender_quotes" not in action_codes
    assert "create_project_plan" in action_codes


def test_selected_quotes_advance_to_comparison_action() -> None:
    snapshot = _snapshot(
        purpose_selections=[
            ProjectSnapshotSelection(purpose="tender_comparison", revision=3)
        ]
    )

    actions = project_next_actions(snapshot)

    action = next(item for item in actions if item.code == "start_tender_comparison")
    assert action.blocking_fact == "tender_report:none"
    assert action.route == f"/projects/{PROJECT_ID}/tender"


class _Result:
    def __init__(self, *, rows=None, value=None):
        self.rows = rows or []
        self.value = value

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.value


def test_enrichment_rolls_up_shared_state_without_tender_table_reads() -> None:
    report_id = uuid.uuid4()
    run_id = uuid.uuid4()
    report = SimpleNamespace(
        id=report_id,
        workflow_type="tender_report",
        title="Tender recommendation report",
        version=4,
        status="accepted",
        is_stale=False,
        stale_reason=None,
        provenance_metadata={
            "frozen": True,
            "quality": {"open_qa_count": 0, "qs_gate_passed": True},
        },
    )
    run = SimpleNamespace(
        id=run_id,
        workflow_type="create_project_plan",
        state="running",
        error_class=None,
    )
    cost = SimpleNamespace(
        status="accepted",
        version=2,
        deterministic_totals={"total_including_gst": "550000.00"},
        gst_treatment="exclusive",
    )
    session = AsyncMock()
    session.execute.side_effect = [
        _Result(rows=[SimpleNamespace(purpose="tender_comparison", revision=2)]),
        _Result(rows=[report]),
        _Result(rows=[run]),
        _Result(value=cost),
    ]

    enriched = asyncio.run(enrich_project_snapshot(session, _snapshot()))

    assert enriched.tender.status == "approved"
    assert enriched.tender.qs_gate_passed is True
    assert enriched.budget.total == "550000.00"
    assert enriched.active_workflow_runs[0].run_id == run_id
    assert enriched.latest_artefacts[0].artefact_id == report_id
    assert all("tender_" not in str(call) for call in session.execute.await_args_list)
