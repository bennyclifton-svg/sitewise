import asyncio
import uuid
from types import SimpleNamespace

import pytest

from app.database.project import Project
from app.projects.profile import (
    ProfileDependencyConflict,
    ProfileRevisionConflict,
    ProfileValidationError,
    apply_profile_patch,
    profile_options,
    read_profile,
    validate_profile_patch,
)
from app.schemas.projects import ProjectProfilePatch


def test_read_profile_normalizes_columns_and_taxonomy_metadata() -> None:
    project_id = uuid.uuid4()
    project = SimpleNamespace(
        id=project_id,
        profile_revision=3,
        building_class="commercial",
        work_type="refurb",
        user_role="architect-pm",
        state="NSW",
        project_metadata={
            "source": "hosted-create-project",
            "taxonomy": {
                "subclasses": ["office"],
                "scale": {"nla_sqm": 1200},
                "complexity": {"operational_constraints": "live_environment"},
                "work_scope": ["fire_services"],
            },
        },
    )

    profile = read_profile(project)

    assert profile.model_dump() == {
        "project_id": project_id,
        "profile_revision": 3,
        "building_class": "commercial",
        "work_type": "refurb",
        "subclasses": ["office"],
        "scale": {"nla_sqm": 1200},
        "complexity": {"operational_constraints": "live_environment"},
        "work_scope": ["fire_services"],
        "user_role": "architect-pm",
        "state": "NSW",
    }


def test_profile_options_uses_the_backend_taxonomy_source_of_truth() -> None:
    options = profile_options()

    assert [item["value"] for item in options["building_classes"]] == [
        "residential",
        "commercial",
        "industrial",
        "institution",
        "mixed",
        "infrastructure",
    ]
    assert "refurb" in options["work_scopes"]


def test_validate_profile_patch_rejects_invalid_class_work_type_combination() -> None:
    project = _project(profile_revision=2)
    patch = ProjectProfilePatch(
        expected_revision=2,
        building_class="residential",
        work_type="teleportation",
    )

    with pytest.raises(ProfileValidationError, match="Unknown work_type"):
        validate_profile_patch(project, patch)


def test_validate_profile_patch_rejects_stale_revision() -> None:
    project = _project(profile_revision=5)

    with pytest.raises(ProfileRevisionConflict) as raised:
        validate_profile_patch(project, ProjectProfilePatch(expected_revision=4))

    assert raised.value.expected_revision == 4
    assert raised.value.current_revision == 5


def test_validate_profile_patch_rejects_unknown_and_wrong_scale_values() -> None:
    project = _project(
        profile_revision=2,
        building_class="commercial",
        work_type="refurb",
        project_metadata={"taxonomy": {"subclasses": ["office"]}},
    )
    patch = ProjectProfilePatch(
        expected_revision=2,
        scale={"storeys": 1.5, "mystery": 2},
    )

    with pytest.raises(ProfileValidationError) as raised:
        validate_profile_patch(project, patch)

    assert "Unknown scale field: 'mystery'" in raised.value.errors
    assert "scale 'storeys' must be an integer" in raised.value.errors


def test_validate_profile_patch_rejects_unknown_complexity_keys_and_options() -> None:
    project = _project(
        profile_revision=2,
        building_class="commercial",
        work_type="refurb",
        project_metadata={"taxonomy": {"subclasses": ["office"]}},
    )
    patch = ProjectProfilePatch(
        expected_revision=2,
        complexity={"contamination_level": "impossible", "mystery": "value"},
    )

    with pytest.raises(ProfileValidationError) as raised:
        validate_profile_patch(project, patch)

    assert "Unknown complexity dimension: 'mystery'" in raised.value.errors
    assert (
        "Unknown option for complexity 'contamination_level': 'impossible'"
        in raised.value.errors
    )


def test_validate_profile_patch_rejects_work_scope_from_another_work_type() -> None:
    project = _project(
        profile_revision=2,
        building_class="commercial",
        work_type="refurb",
        project_metadata={"taxonomy": {"subclasses": ["office"]}},
    )

    with pytest.raises(ProfileValidationError) as raised:
        validate_profile_patch(
            project,
            ProjectProfilePatch(expected_revision=2, work_scope=["demolition"]),
        )

    assert "Unknown work_scope for 'refurb': 'demolition'" in raised.value.errors


def test_validate_profile_patch_rejects_unknown_role_and_state() -> None:
    project = _project(profile_revision=2)

    with pytest.raises(ProfileValidationError) as raised:
        validate_profile_patch(
            project,
            ProjectProfilePatch(
                expected_revision=2,
                user_role="wizard",
                state="XX",
            ),
        )

    assert "Unknown user_role: 'wizard'" in raised.value.errors
    assert "Unknown state: 'XX'" in raised.value.errors


def test_parent_change_requires_explicit_incompatible_dependent_clear() -> None:
    project = _project(
        profile_revision=2,
        building_class="residential",
        work_type="new",
        project_metadata={
            "taxonomy": {
                "subclasses": ["house"],
                "scale": {"gfa_sqm": 240},
            }
        },
    )
    patch = ProjectProfilePatch(expected_revision=2, building_class="commercial")

    with pytest.raises(ProfileDependencyConflict) as raised:
        validate_profile_patch(project, patch)

    assert raised.value.fields == ("subclasses", "scale")

    cleared = validate_profile_patch(
        project,
        patch.model_copy(update={"clear_incompatible": True}),
    )
    assert cleared.after.building_class == "commercial"
    assert cleared.after.subclasses == []
    assert cleared.after.scale == {}
    assert cleared.cleared_fields == ("subclasses", "scale")


def test_apply_profile_patch_keeps_revision_and_audit_unchanged_for_no_op() -> None:
    project = _orm_project(profile_revision=3)
    session = _Session()

    change = asyncio.run(
        apply_profile_patch(
            session,
            project=project,
            patch=ProjectProfilePatch(expected_revision=3, state="NSW"),
            actor_source="user",
        )
    )

    assert change.previous_revision == change.new_revision == 3
    assert change.changed_fields == []
    assert change.cleared_fields == []
    assert session.added == []
    assert session.flush_count == 0


def test_apply_profile_patch_updates_once_and_records_one_audit_run() -> None:
    project = _orm_project(profile_revision=3)
    session = _Session()

    change = asyncio.run(
        apply_profile_patch(
            session,
            project=project,
            patch=ProjectProfilePatch(expected_revision=3, state="VIC"),
            actor_source="user",
        )
    )

    assert project.state == "VIC"
    assert project.profile_revision == 4
    assert change.previous_revision == 3
    assert change.new_revision == 4
    assert change.changed_fields == ["state"]
    assert change.cleared_fields == []
    assert session.flush_count == 1
    assert len(session.added) == 2
    activity = session.added[0]
    assert activity.project_id == project.id
    assert activity.source == "user"
    assert activity.reference_type == "project_profile"
    assert activity.event_metadata["changed_fields"] == ["state"]
    assert activity.event_metadata["before"]["state"] == "NSW"
    assert activity.event_metadata["after"]["state"] == "VIC"
    event = session.added[1]
    assert event.project_id == project.id
    assert event.sequence == 1
    assert event.resource_type == "project_profile"
    assert event.resource_revision == 4
    assert event.action == "updated"
    assert event.payload["changed_fields"] == ["state"]


def test_apply_profile_patch_rechecks_revision_under_row_lock() -> None:
    project = _orm_project(profile_revision=3)
    session = _Session(refreshed_revision=4)

    with pytest.raises(ProfileRevisionConflict):
        asyncio.run(
            apply_profile_patch(
                session,
                project=project,
                patch=ProjectProfilePatch(expected_revision=3, state="VIC"),
                actor_source="user",
            )
        )

    assert session.added == []
    assert session.flush_count == 0


def test_apply_profile_patch_reports_explicit_clears_separately() -> None:
    project = _orm_project(profile_revision=1, state="NSW")
    session = _Session()

    change = asyncio.run(
        apply_profile_patch(
            session,
            project=project,
            patch=ProjectProfilePatch(expected_revision=1, state=None),
            actor_source="user",
        )
    )

    assert project.state is None
    assert change.changed_fields == []
    assert change.cleared_fields == ["state"]
    assert change.new_revision == 2


def _project(**overrides):
    values = {
        "id": uuid.uuid4(),
        "profile_revision": 1,
        "event_sequence": 0,
        "building_class": None,
        "work_type": None,
        "user_role": None,
        "state": None,
        "project_metadata": {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _orm_project(**overrides) -> Project:
    values = {
        "id": uuid.uuid4(),
        "owner_user_id": uuid.uuid4(),
        "slug": "demo",
        "title": "Demo",
        "workspace_path": "04-projects/demo",
        "phase": "brief-planning",
        "archetype": None,
        "building_class": "residential",
        "work_type": "new",
        "user_role": "architect-pm",
        "state": "NSW",
        "profile_revision": 1,
        "status": "active",
        "project_metadata": {},
    }
    values.update(overrides)
    return Project(**values)


class _Session:
    def __init__(self, *, refreshed_revision: int | None = None) -> None:
        self.added = []
        self.flush_count = 0
        self.refreshed_revision = refreshed_revision

    async def refresh(self, project, **_kwargs) -> None:
        if self.refreshed_revision is not None:
            project.profile_revision = self.refreshed_revision

    def add(self, row) -> None:
        self.added.append(row)

    async def flush(self) -> None:
        self.flush_count += 1
