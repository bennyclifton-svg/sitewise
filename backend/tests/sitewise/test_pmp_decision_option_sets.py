from types import SimpleNamespace

from app.sitewise.pmp_decisions import (
    PMP_CORE_DECISIONS,
    SPARSE_BRIEF_DECISION_BAND,
    decision_option_sets_for_project,
    required_decision_ids_for_project,
)


def test_new_dwelling_merges_seed_catalogs_into_option_sets() -> None:
    project = SimpleNamespace(
        archetype="new-dwelling",
        building_class="residential",
        work_type="new",
        project_metadata={},
    )
    sets = decision_option_sets_for_project(project)
    assert "approval-pathway" in sets
    assert "flooring-finish" in sets
    assert "kitchen-benchtop" in sets
    assert "dwelling-storeys" in sets
    assert sets["flooring-finish"]["default_hint"] == "engineered"
    assert sets["flooring-finish"]["section"] == "FFE Schedule"


def test_required_decision_ids_stay_within_sparse_band() -> None:
    project = SimpleNamespace(
        archetype="new-dwelling",
        building_class="residential",
        work_type="new",
        project_metadata={},
    )
    required = required_decision_ids_for_project(project)
    assert required[:2] == list(PMP_CORE_DECISIONS)
    assert "staging-strategy" not in required
    assert len(required) <= SPARSE_BRIEF_DECISION_BAND
    assert len(required) >= 6
    assert "flooring-finish" not in required
    assert "external-cladding" not in required


def test_format_includes_cost_only_when_requested() -> None:
    project = SimpleNamespace(
        archetype="new-dwelling",
        building_class="residential",
        work_type="new",
        project_metadata={},
    )
    without = decision_option_sets_for_project(project, include_cost_only=False)
    with_cost = decision_option_sets_for_project(project, include_cost_only=True)
    assert "contingency-band" not in without
    assert "contingency-band" in with_cost
    assert with_cost["contingency-band"].get("cost_only") is True
