import uuid

import pytest
from pydantic import ValidationError

from app.database.project import Project
from app.schemas.projects import (
    ProjectProfileChange,
    ProjectProfilePatch,
    ProjectProfileView,
)


def test_profile_patch_distinguishes_omission_from_explicit_clear() -> None:
    omitted = ProjectProfilePatch(expected_revision=3)
    explicit_clear = ProjectProfilePatch(expected_revision=3, building_class=None)

    assert "building_class" not in omitted.model_fields_set
    assert "building_class" in explicit_clear.model_fields_set

    with pytest.raises(ValidationError):
        ProjectProfilePatch()


def test_profile_patch_exposes_only_submitted_normalized_changes() -> None:
    patch = ProjectProfilePatch(
        expected_revision=4,
        state=" NSW ",
        subclasses=[" house "],
        work_scope=[" fire_services "],
        clear_incompatible=True,
    )

    assert patch.model_dump(exclude_unset=True) == {
        "expected_revision": 4,
        "state": "NSW",
        "subclasses": ["house"],
        "work_scope": ["fire_services"],
        "clear_incompatible": True,
    }


def test_profile_patch_rejects_fields_outside_the_profile_contract() -> None:
    with pytest.raises(ValidationError):
        ProjectProfilePatch(expected_revision=1, title="Silent generic mutation")


def test_profile_change_contains_complete_profile_and_derived_state() -> None:
    project_id = uuid.uuid4()
    profile = ProjectProfileView(
        project_id=project_id,
        profile_revision=5,
        building_class="commercial",
        work_type="refurb",
        subclasses=["office"],
        scale={"nla_sqm": 1200},
        complexity={"operational_constraints": "live_environment"},
        work_scope=["fire_services"],
        user_role="architect-pm",
        state="NSW",
    )

    change = ProjectProfileChange(
        profile=profile,
        previous_revision=4,
        new_revision=5,
        changed_fields=["building_class", "work_type"],
        cleared_fields=[],
        overlay_status={"ready": True},
        risk_flags=[
            {
                "value": "live_operations",
                "severity": "warning",
                "title": "Live operations",
                "description": "Works occur in an operating facility.",
            }
        ],
    )

    assert change.profile.project_id == project_id
    assert change.profile.profile_revision == change.new_revision
    assert change.overlay_status.ready is True
    assert change.risk_flags[0].value == "live_operations"


def test_profile_change_encodes_single_increment_and_no_op_revisions() -> None:
    project_id = uuid.uuid4()
    no_op = ProjectProfileChange(
        profile=ProjectProfileView(project_id=project_id, profile_revision=4),
        previous_revision=4,
        new_revision=4,
        changed_fields=[],
        cleared_fields=[],
        overlay_status={"ready": False},
        risk_flags=[],
    )
    assert no_op.new_revision == no_op.previous_revision

    with pytest.raises(ValidationError):
        ProjectProfileChange(
            profile=ProjectProfileView(project_id=project_id, profile_revision=4),
            previous_revision=4,
            new_revision=4,
            changed_fields=["state"],
            cleared_fields=[],
            overlay_status={"ready": False},
            risk_flags=[],
        )

    with pytest.raises(ValidationError):
        ProjectProfileChange(
            profile=ProjectProfileView(project_id=project_id, profile_revision=5),
            previous_revision=4,
            new_revision=5,
            changed_fields=[],
            cleared_fields=[],
            overlay_status={"ready": False},
            risk_flags=[],
        )


def test_project_profile_revision_starts_at_one_and_is_required() -> None:
    column = Project.__table__.c.profile_revision

    assert column.nullable is False
    assert column.default.arg == 1
    assert str(column.server_default.arg) == "1"
