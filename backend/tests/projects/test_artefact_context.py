from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.projects.artefact_context import (
    build_cost_plan_context,
    build_pmp_context,
    build_rfp_context,
    build_rft_context,
    format_artefact_context,
)
from app.projects.generation_context import (
    FieldState,
    resolve_project_generation_context,
)
from app.schemas.project_snapshot import ProjectSnapshot


PROJECT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def test_pmp_lens_keeps_governance_context_and_computes_emphasis() -> None:
    context = resolve_project_generation_context(_snapshot())

    lens = build_pmp_context(context)

    assert lens.project_id == PROJECT_ID
    assert lens.context_version == 9
    assert lens.identity["client"].value == "Example Developments"
    assert lens.stakeholders["consultants"].state == FieldState.KNOWN
    assert lens.user_provided_fields["budget"] == "$12,000,000"
    assert "planning" not in lens.complexity
    assert "procurement_route" not in lens.complexity
    assert sum(lens.section_weights.values()) == pytest.approx(1.0)
    assert "timeframe" in {field.key for field in lens.critical_unknowns}


def test_cost_plan_lens_excludes_governance_only_context() -> None:
    context = resolve_project_generation_context(_snapshot())

    lens = build_cost_plan_context(context)
    rendered = format_artefact_context(lens)

    assert set(lens.identity) == {"title", "site_address"}
    assert lens.commercial["budget"].value == "$12,000,000"
    assert lens.procurement["procurement_route"].value == "traditional"
    assert "procurement_route" not in lens.complexity
    assert lens.known_exclusions["stripout"].state == (
        FieldState.EXPLICITLY_EXCLUDED
    )
    assert not hasattr(lens, "stakeholders")
    assert "Cost Plan project context lens" in rendered
    assert "client: Example Developments" not in rendered


def test_rfp_lens_is_discipline_specific_without_cost_plan_budget() -> None:
    context = resolve_project_generation_context(_snapshot())

    lens = build_rfp_context(context, "  Structural Engineer  ")
    rendered = format_artefact_context(lens)

    assert lens.discipline == "Structural Engineer"
    assert lens.identity["client"].value == "Example Developments"
    assert lens.programme["phase"].value == "design"
    assert not hasattr(lens, "commercial")
    assert "consultant_discipline: Structural Engineer" in rendered
    assert "$12,000,000" not in rendered


def test_rft_lens_focuses_package_delivery_and_exclusions() -> None:
    context = resolve_project_generation_context(_snapshot())

    lens = build_rft_context(context, "Mechanical Services")
    rendered = format_artefact_context(lens)

    assert lens.package == "Mechanical Services"
    assert lens.complexity["access_constraints"].value == "urban_constrained"
    assert lens.complexity["operational_constraints"].value == "live_environment"
    assert lens.known_exclusions["stripout"].state == (
        FieldState.EXPLICITLY_EXCLUDED
    )
    assert not hasattr(lens, "stakeholders")
    assert "trade_package: Mechanical Services" in rendered
    assert "Example Developments" not in rendered
    assert "$12,000,000" not in rendered


@pytest.mark.parametrize("builder", [build_rfp_context, build_rft_context])
def test_targeted_lenses_reject_blank_targets(builder) -> None:
    context = resolve_project_generation_context(_snapshot())

    with pytest.raises(ValueError, match="required"):
        builder(context, "   ")


def _snapshot() -> ProjectSnapshot:
    return ProjectSnapshot.model_validate(
        {
            "generated_at": datetime(2026, 8, 10, tzinfo=UTC),
            "content_fingerprint": "c" * 64,
            "context_version": 9,
            "field_states": {
                "scope.stripout": "explicitly_excluded",
            },
            "identity": {
                "project_id": str(PROJECT_ID),
                "title": "City Office Upgrade",
                "slug": "city-office-upgrade",
                "workspace_path": "04-projects/city-office-upgrade",
                "phase": "design",
                "status": "active",
                "site_address": {
                    "status": "confirmed",
                    "value": "10 Test Street, Sydney",
                    "source": "project_setup",
                },
                "client": {
                    "status": "confirmed",
                    "value": "Example Developments",
                    "source": "project_setup",
                },
            },
            "profile": {
                "project_id": str(PROJECT_ID),
                "profile_revision": 4,
                "building_class": "commercial",
                "work_type": "refurb",
                "subclasses": ["office"],
                "scale": {
                    "storeys": 8,
                    "nla_sqm": 4200,
                    "tenancies": 6,
                    "grade": "A",
                },
                "complexity": {
                    "planning": "da",
                    "procurement_route": "traditional",
                    "access_constraints": "urban_constrained",
                    "operational_constraints": "live_environment",
                    "stakeholder_complexity": "single_owner",
                },
                "work_scope": [
                    "live_environment_fitout",
                    "services_upgrade",
                ],
                "user_role": "architect-pm",
                "state": "NSW",
            },
            "decisions": {"set_revision": 3, "items": []},
            "evidence": {
                "fingerprint": "d" * 64,
                "active_count": 0,
                "fingerprint_complete": True,
                "ingest_failure_count": 0,
                "ingest_failures": [],
            },
            "confirmed_inputs": {
                "budget": {
                    "status": "confirmed",
                    "value": "$12,000,000",
                    "source": "project_setup",
                },
                "timeframe": {"status": "needs_input"},
                "procurement_route": {
                    "status": "confirmed",
                    "value": "traditional",
                    "source": "project_decision",
                },
            },
            "open_profile_proposals": [],
        }
    )
