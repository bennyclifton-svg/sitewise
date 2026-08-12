"""Budget capture, and the scale band it unlocks.

The R2 verification runs captured scope, complexity and the asset register but
showed `budget=None` on both projects: budget lived in taxonomy metadata and was
never a profile field, so the agent had nowhere to put "$180k". D5 was built and
inert — every document fell back to the 1300-word default regardless of size.
"""

import uuid
from types import SimpleNamespace

import pytest

from app.projects.profile import ProfileValidationError, read_profile, validate_profile_patch
from app.projects.profile_proposals import should_auto_apply_proposal
from app.schemas.projects import ProjectProfilePatch
from app.sitewise.taxonomy import parse_budget_amount, scale_band_for


def _project(**taxonomy) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        profile_revision=1,
        building_class="commercial",
        work_type="refurb",
        state="NSW",
        user_role="architect-pm",
        project_metadata={"taxonomy": taxonomy},
    )


@pytest.mark.parametrize(
    "text,band",
    [
        ("Budget around $180k", "xs"),
        ("$95k", "xs"),
        ("roughly $850k", "s"),
        ("$1.4m approved", "s"),
        ("Budget not fixed yet, maybe $1.2m", "s"),
        ("about $12m", "m"),
        ("$28m", "l"),
        ("circa $140m", "l"),
    ],
)
def test_the_budgets_a_pm_actually_types_resolve_to_bands(text, band) -> None:
    assert scale_band_for(text) == band


def test_no_budget_means_no_band_rather_than_a_guess() -> None:
    assert parse_budget_amount("budget not stated") is None
    assert scale_band_for(None) is None
    assert scale_band_for("") is None


def test_budget_round_trips_as_the_users_own_words() -> None:
    """Storing "around $180k" keeps what was said; the band is derived from it."""
    profile = read_profile(_project(budget="Budget around $180k"))

    assert profile.budget == "Budget around $180k"
    assert scale_band_for(profile.budget) == "xs"


def test_a_budget_without_a_figure_is_rejected() -> None:
    project = _project()
    patch = ProjectProfilePatch(expected_revision=1, budget="to be confirmed")

    with pytest.raises(ProfileValidationError) as excinfo:
        validate_profile_patch(project, patch)

    assert "amount" in str(excinfo.value)


def test_a_budget_with_a_figure_passes_validation() -> None:
    plan = validate_profile_patch(
        _project(), ProjectProfilePatch(expected_revision=1, budget="around $180k")
    )

    assert "budget" in plan.changed_fields


def test_budget_auto_applies_into_a_blank_profile() -> None:
    proposal = SimpleNamespace(
        proposed_values={"budget": "around $180k"}, evidence_references=[]
    )

    assert should_auto_apply_proposal(proposal, _project()) is True


def test_a_stated_budget_is_never_overwritten() -> None:
    proposal = SimpleNamespace(
        proposed_values={"budget": "$250k"}, evidence_references=[]
    )

    assert should_auto_apply_proposal(proposal, _project(budget="$180k")) is False
