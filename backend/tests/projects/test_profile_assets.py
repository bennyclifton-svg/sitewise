"""The asset register: where a services job's actual scope lands.

Wave 1 measured 0/7 fact retention on the mechanical prompt. `R22`, `Pioneer`,
`Actron`, `30kW`, the two named zones — none reached the document, because the
profile modelled buildings (GFA, storeys, NLA) and nothing modelled the plant
being replaced. `work_scope` could only ever compress that prompt to a coarse
services enum before discipline-level items (e.g. `mechanical_hvac`) existed.
"""

import uuid
from types import SimpleNamespace

import pytest

from app.projects.profile import read_profile, validate_profile_patch
from app.projects.profile_proposals import should_auto_apply_proposal
from app.schemas.projects import ProjectAsset, ProjectProfilePatch
from app.sitewise.taxonomy import (
    asset_option_label,
    asset_option_values,
    asset_register_applies_to,
)

AC_UNITS = {
    "type": "Split ducted air conditioning system",
    "count": 2,
    "location": "Service centre; western office",
    "make_model": "Pioneer",
    "capacity": "30kW",
    "age_years": 30,
    "condition": "beyond_economical_repair",
    "action": "replace",
    "replacement_spec": "Actron 30kW split ducted",
    "notes": "R22 refrigerant; phase-out obligations apply",
}


def _project(**taxonomy) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        profile_revision=1,
        building_class=taxonomy.pop("building_class", "commercial"),
        work_type=taxonomy.pop("work_type", "refurb"),
        state=taxonomy.pop("state", "NSW"),
        user_role="architect-pm",
        project_metadata={"taxonomy": taxonomy},
    )


def test_the_mechanical_prompt_survives_a_round_trip() -> None:
    """Every fact Wave 1 dropped is now addressable on the profile."""
    profile = read_profile(_project(assets=[AC_UNITS]))

    assert len(profile.assets) == 1
    asset = profile.assets[0]
    assert asset.count == 2
    assert asset.make_model == "Pioneer"
    assert asset.capacity == "30kW"
    assert asset.age_years == 30
    assert "R22" in (asset.notes or "")
    assert "Actron" in (asset.replacement_spec or "")
    assert "western office" in (asset.location or "")


def test_unparsable_asset_rows_are_skipped_not_fatal() -> None:
    """A stored row that no longer matches the schema must not break the profile."""
    profile = read_profile(
        _project(assets=[AC_UNITS, {"count": 3}, "not-an-asset", {"type": "  "}])
    )

    assert [asset.type for asset in profile.assets] == [AC_UNITS["type"]]


def test_asset_condition_and_action_are_validated() -> None:
    project = _project()
    patch = ProjectProfilePatch(
        expected_revision=1,
        assets=[ProjectAsset(type="Lift", condition="haunted", action="replace")],
    )

    with pytest.raises(Exception) as excinfo:
        validate_profile_patch(project, patch)

    assert "condition" in str(excinfo.value)


def test_a_valid_asset_patch_passes_validation() -> None:
    project = _project()
    patch = ProjectProfilePatch(
        expected_revision=1, assets=[ProjectAsset.model_validate(AC_UNITS)]
    )

    plan = validate_profile_patch(project, patch)

    assert "assets" in plan.changed_fields


def test_assets_auto_apply_into_a_blank_profile() -> None:
    """Captured from the user's own description, so it fills a blank directly."""
    proposal = SimpleNamespace(
        proposed_values={"assets": [AC_UNITS]}, evidence_references=[]
    )

    assert should_auto_apply_proposal(proposal, _project()) is True


def test_assets_are_not_overwritten_once_recorded() -> None:
    proposal = SimpleNamespace(
        proposed_values={"assets": [AC_UNITS]}, evidence_references=[]
    )
    existing = _project(assets=[{"type": "Chiller"}])

    assert should_auto_apply_proposal(proposal, existing) is False


def test_asset_register_does_not_apply_to_new_builds() -> None:
    """A new build has no existing asset to register."""
    assert asset_register_applies_to("refurb") is True
    assert asset_register_applies_to("remediation") is True
    assert asset_register_applies_to("new") is False
    assert asset_register_applies_to(None) is False


def test_option_groups_resolve_labels() -> None:
    assert asset_option_values("condition")
    assert asset_option_label("action", "replace") == "Replace"
    assert asset_option_label("condition", None) is None
