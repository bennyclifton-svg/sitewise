from __future__ import annotations

from datetime import UTC, datetime

from app.projects.workflow_capabilities import workflow_capabilities
from app.schemas.project_snapshot import ProjectSnapshot

_WAREHOUSE_SUBCLASSES = ("warehouse", "logistics_ecommerce")
_COMMERCIAL_FITOUT_SUBCLASSES = ("office", "serviced_office_coworking")


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
        "Cost Plan reference-data coverage is currently NSW only."
    ]
    assert matrix.capabilities["create_pmp"].status == "supported"


def test_cost_plan_supports_nsw_warehouse_and_logistics() -> None:
    for subclass in _WAREHOUSE_SUBCLASSES:
        cost_plan = workflow_capabilities(
            _snapshot(
                building_class="industrial",
                subclasses=[subclass],
                state="NSW",
            )
        ).capabilities["create_cost_plan"]
        assert cost_plan.status == "supported"
        assert any(
            "warehouse/logistics" in item for item in cost_plan.reference_coverage
        )


def test_cost_plan_supports_new_industrial_reference_families() -> None:
    for subclass in (
        "manufacturing",
        "heavy_manufacturing",
        "cold_storage",
        "food_processing",
        "data_centre",
    ):
        cost_plan = workflow_capabilities(
            _snapshot(
                building_class="industrial",
                subclasses=[subclass],
                state="NSW",
            )
        ).capabilities["create_cost_plan"]
        assert cost_plan.status == "supported"


def test_cost_plan_rejects_uncovered_specialist_industrial_subclasses() -> None:
    for subclass in (
        "dangerous_goods",
        "pharmaceutical_gmp",
        "cleanroom",
        "battery_manufacturing",
        "waste_to_energy",
    ):
        cost_plan = workflow_capabilities(
            _snapshot(
                building_class="industrial",
                subclasses=[subclass],
                state="NSW",
            )
        ).capabilities["create_cost_plan"]
        assert cost_plan.status == "unsupported"


def test_cost_plan_still_rejects_interstate_industrial() -> None:
    cost_plan = workflow_capabilities(
        _snapshot(
            building_class="industrial",
            subclasses=["warehouse"],
            state="VIC",
        )
    ).capabilities["create_cost_plan"]
    assert cost_plan.status == "unsupported"
    assert any("NSW" in reason for reason in cost_plan.reasons)


def test_cost_plan_supports_nsw_class_5_commercial_fitout() -> None:
    for subclass in _COMMERCIAL_FITOUT_SUBCLASSES:
        cost_plan = workflow_capabilities(
            _snapshot(
                building_class="commercial",
                work_type="refurb",
                subclasses=[subclass],
                state="NSW",
            )
        ).capabilities["create_cost_plan"]
        assert cost_plan.status == "supported"
        assert any("commercial fit-out" in item for item in cost_plan.reference_coverage)


def test_cost_plan_rejects_specialist_commercial_fitout_without_reference_coverage() -> None:
    cost_plan = workflow_capabilities(
        _snapshot(
            building_class="commercial",
            work_type="refurb",
            subclasses=["food_beverage"],
            state="NSW",
        )
    ).capabilities["create_cost_plan"]

    assert cost_plan.status == "unsupported"
    assert any("office/coworking" in reason for reason in cost_plan.reasons)


def test_cost_plan_supports_commercial_base_building_new_work() -> None:
    for subclass in ("office", "retail_shopping_centre", "retail_standalone"):
        cost_plan = workflow_capabilities(
            _snapshot(
                building_class="commercial",
                work_type="new",
                subclasses=[subclass],
                state="NSW",
            )
        ).capabilities["create_cost_plan"]
        assert cost_plan.status == "supported"
        assert any("base-building" in item for item in cost_plan.reference_coverage)


def test_cost_plan_supports_selected_multi_residential_new_work() -> None:
    for subclass in (
        "apartments",
        "btr",
        "student_housing",
        "social_affordable_housing",
    ):
        cost_plan = workflow_capabilities(
            _snapshot(
                building_class="residential",
                work_type="new",
                subclasses=[subclass],
                state="NSW",
            )
        ).capabilities["create_cost_plan"]
        assert cost_plan.status == "supported"


def test_cost_plan_remediation_requires_supported_work_scope() -> None:
    needs_scope = workflow_capabilities(
        _snapshot(
            building_class="commercial",
            work_type="remediation",
            subclasses=["office"],
            work_scope=[],
        )
    ).capabilities["create_cost_plan"]
    assert needs_scope.status == "needs_input"
    assert needs_scope.required_fields == ["work_scope"]

    supported = workflow_capabilities(
        _snapshot(
            building_class="commercial",
            work_type="remediation",
            subclasses=["office"],
            work_scope=["facade_cladding"],
        )
    ).capabilities["create_cost_plan"]
    assert supported.status == "supported"

    contamination = workflow_capabilities(
        _snapshot(
            building_class="commercial",
            work_type="remediation",
            subclasses=["office"],
            work_scope=["contamination_remediation"],
        )
    ).capabilities["create_cost_plan"]
    assert contamination.status == "unsupported"


def test_cost_plan_advisory_is_intentionally_not_a_construction_cost_plan() -> None:
    capability = workflow_capabilities(
        _snapshot(work_type="advisory")
    ).capabilities["create_cost_plan"]

    assert capability.status == "unsupported"
    assert "fee and deliverable planning" in capability.reasons[0]


def test_consultant_procurement_requires_taxonomy_context() -> None:
    capability = workflow_capabilities(
        _snapshot(building_class=None)
    ).capabilities["consultant_procurement"]

    assert capability.status == "needs_input"
    assert capability.required_fields == ["building_class"]


def test_contractor_eoi_capability() -> None:
    capability = workflow_capabilities(_snapshot()).capabilities["contractor_eoi"]

    assert capability.status == "supported"
    assert set(capability.required_fields) == set()


def test_trade_procurement_uses_general_project_coverage() -> None:
    capability = workflow_capabilities(_snapshot(subclasses=["apartments"])).capabilities[
        "trade_procurement"
    ]

    assert capability.status == "supported"
    assert capability.required_fields == []


def test_contractor_eoi_requires_project_and_jurisdiction_context() -> None:
    capability = workflow_capabilities(
        _snapshot(building_class=None, work_type=None, state=None)
    ).capabilities["contractor_eoi"]

    assert capability.status == "needs_input"
    assert set(capability.required_fields) == {"building_class", "work_type", "state"}


def test_trade_procurement_requires_project_and_jurisdiction_context() -> None:
    capability = workflow_capabilities(
        _snapshot(building_class=None, work_type=None, state=None)
    ).capabilities["trade_procurement"]

    assert capability.status == "needs_input"
    assert set(capability.required_fields) == {"building_class", "work_type", "state"}


def test_contractor_eoi_supports_class_2_apartment_projects() -> None:
    capability = workflow_capabilities(
        _snapshot(subclasses=["apartments"])
    ).capabilities["contractor_eoi"]

    assert capability.status == "supported"
