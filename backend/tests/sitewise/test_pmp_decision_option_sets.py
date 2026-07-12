from types import SimpleNamespace

from app.sitewise.pmp_decisions import (
    PMP_CORE_DECISIONS,
    SPARSE_BRIEF_DECISION_BAND,
    decision_option_sets_for_project,
    format_decision_option_sets,
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


def test_required_decision_ids_stay_within_sparse_band() -> None:
    project = SimpleNamespace(
        archetype="new-dwelling",
        building_class="residential",
        work_type="new",
        project_metadata={},
    )
    required = required_decision_ids_for_project(project)
    assert required[:3] == list(PMP_CORE_DECISIONS)
    assert len(required) <= SPARSE_BRIEF_DECISION_BAND
    assert len(required) >= 8
    assert "flooring-finish" in required


def test_format_decision_option_sets_lists_required_ids() -> None:
    project = SimpleNamespace(
        archetype="new-dwelling",
        building_class="residential",
        work_type="new",
        project_metadata={},
    )
    text = format_decision_option_sets(project)
    assert "Required decision ids for this project" in text
    assert "flooring-finish" in text
