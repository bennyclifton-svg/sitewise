from __future__ import annotations

from datetime import UTC, datetime

from app.projects.workflow_capabilities import workflow_capabilities
from app.schemas.project_snapshot import ProjectSnapshot


def _snapshot(**profile_overrides: object) -> ProjectSnapshot:
    profile = {
        "project_id": "00000000-0000-0000-0000-000000000001",
        "profile_revision": 1,
        "building_class": "residential",
        "work_type": "refurb",
        "subclasses": ["house"],
        "scale": {},
        "complexity": {},
        "work_scope": [],
        "user_role": "architect-pm",
        "state": "NSW",
    }
    profile.update(profile_overrides)
    return ProjectSnapshot.model_validate(
        {
            "generated_at": datetime.now(UTC),
            "content_fingerprint": "snapshot-fingerprint",
            "identity": {
                "project_id": profile["project_id"],
                "title": "Test",
                "slug": "test",
                "workspace_path": "04-projects/test",
                "phase": "brief-planning",
                "status": "active",
                "site_address": {"status": "needs_input"},
                "client": {"status": "needs_input"},
            },
            "profile": profile,
            "decisions": {"set_revision": 1, "items": []},
            "evidence": {
                "fingerprint": "evidence-fingerprint",
                "active_count": 0,
                "fingerprint_complete": True,
                "ingest_failure_count": 0,
                "ingest_failures": [],
            },
            "confirmed_inputs": {},
            "open_profile_proposals": [],
            "source_type": None,
            "document_class": "unknown",
            "excerpt": "",
        }
    )


def test_complete_residential_snapshot_publishes_supported_capabilities() -> None:
    matrix = workflow_capabilities(_snapshot())

    assert matrix.snapshot_content_fingerprint == "snapshot-fingerprint"
    assert matrix.capabilities["create_pmp"].status == "supported"
    assert matrix.capabilities["tender_comparison"].status == "supported"
    assert matrix.capabilities["create_cost_plan"].status == "supported"
    assert matrix.capabilities["consultant_procurement"].status == "supported"


def test_missing_profile_context_reports_needs_input_and_fields() -> None:
    matrix = workflow_capabilities(_snapshot(work_type=None, state=None))

    plan = matrix.capabilities["create_pmp"]
    assert plan.status == "needs_input"
    assert plan.required_fields == ["work_type", "state"]


def test_tender_rejects_non_class_1a_residential_work() -> None:
    tender = workflow_capabilities(_snapshot(subclasses=["apartments"])).capabilities[
        "tender_comparison"
    ]

    assert tender.status == "unsupported"
    assert "Class 1a" in tender.reasons[0]


def test_cost_plan_does_not_claim_six_class_or_interstate_coverage() -> None:
    matrix = workflow_capabilities(
        _snapshot(building_class="commercial", subclasses=["office"], state="VIC")
    )
    cost_plan = matrix.capabilities["create_cost_plan"]

    assert cost_plan.status == "unsupported"
    assert cost_plan.reasons == [
        "Cost Plan reference-data coverage is currently residential only.",
        "Cost Plan reference-data coverage is currently NSW only.",
    ]
    assert matrix.capabilities["create_pmp"].status == "supported"


def test_consultant_procurement_requires_role_and_taxonomy_context() -> None:
    capability = workflow_capabilities(
        _snapshot(building_class=None, user_role=None)
    ).capabilities["consultant_procurement"]

    assert capability.status == "needs_input"
    assert capability.required_fields == ["building_class", "user_role"]
