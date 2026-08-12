"""`scope_narrative` gives prose scope somewhere to land.

Wave 2 measured fact retention of 2/9, 2/10 and 2/7 on prompts whose scope was
described in words: "concrete cancer in the basement carpark", "second storey
addition to a semi in a heritage conservation area", "new lifts, footbridge,
accessible platforms and canopies". `work_scope` is an enum and could hold none
of it, so the chat turn acknowledged each fact in prose and the generator never
saw it.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.projects.profile import (
    MAX_SCOPE_NARRATIVE_ITEM_CHARS,
    MAX_SCOPE_NARRATIVE_ITEMS,
    PROFILE_FIELDS,
    ProfileValidationError,
    project_scope_narrative,
    read_profile,
    validate_profile_patch,
)
from app.projects.profile_proposals import SETUP_PROPOSAL_FIELDS
from app.schemas.projects import ProjectProfilePatch


def _project(taxonomy: dict | None = None, *, revision: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        profile_revision=revision,
        building_class="residential",
        work_type="remediation",
        user_role="architect-pm",
        state="NSW",
        project_metadata={"taxonomy": taxonomy or {"subclasses": ["apartments"]}},
    )


def test_scope_narrative_is_a_profile_field_and_a_setup_proposal_field() -> None:
    """It has to be in both, or the agent cannot write it without a round-trip."""
    assert "scope_narrative" in PROFILE_FIELDS
    assert "scope_narrative" in SETUP_PROPOSAL_FIELDS


def test_read_profile_returns_the_stored_narrative() -> None:
    project = _project(
        {
            "subclasses": ["apartments"],
            "scope_narrative": [
                "Concrete cancer remediation to basement carpark",
                "Spalling repair to eastern facade",
            ],
        }
    )

    assert read_profile(project).scope_narrative == [
        "Concrete cancer remediation to basement carpark",
        "Spalling repair to eastern facade",
    ]


def test_read_profile_skips_non_string_and_blank_entries() -> None:
    """A stored row that no longer parses must not break the whole profile."""
    project = _project(
        {
            "subclasses": ["apartments"],
            "scope_narrative": ["Kept", "   ", None, 42, {"nested": True}],
        }
    )

    assert project_scope_narrative(project) == ["Kept"]


def test_patch_persists_the_narrative_into_taxonomy_metadata() -> None:
    project = _project()
    plan = validate_profile_patch(
        project,
        ProjectProfilePatch(
            expected_revision=1,
            scope_narrative=[
                "  Concrete cancer remediation to basement carpark  ",
                "",
                "Spalling repair to eastern facade",
            ],
        ),
    )

    # Blank entries are dropped and surrounding whitespace stripped at the
    # schema boundary, so the rendered scope line is not " Concrete cancer…".
    assert plan.after.scope_narrative == [
        "Concrete cancer remediation to basement carpark",
        "Spalling repair to eastern facade",
    ]
    assert "scope_narrative" in plan.changed_fields


def test_narrative_and_enum_are_independent() -> None:
    """The enum routes doctrine; the narrative describes. Setting one keeps the other."""
    project = _project(
        {
            "subclasses": ["apartments"],
            "work_scope": ["facade_cladding"],
        }
    )
    plan = validate_profile_patch(
        project,
        ProjectProfilePatch(
            expected_revision=1,
            scope_narrative=["Spalling repair to eastern facade"],
        ),
    )

    assert plan.after.work_scope == ["facade_cladding"]
    assert plan.after.scope_narrative == ["Spalling repair to eastern facade"]


def test_too_many_items_is_rejected_so_it_stays_a_scope_list() -> None:
    """Without a cap this becomes the place an agent pastes the whole prompt."""
    project = _project()
    with pytest.raises(ProfileValidationError) as excinfo:
        validate_profile_patch(
            project,
            ProjectProfilePatch(
                expected_revision=1,
                scope_narrative=[
                    f"Scope item {index}"
                    for index in range(MAX_SCOPE_NARRATIVE_ITEMS + 1)
                ],
            ),
        )
    assert "at most" in str(excinfo.value)


def test_an_overlong_item_is_rejected() -> None:
    project = _project()
    with pytest.raises(ProfileValidationError) as excinfo:
        validate_profile_patch(
            project,
            ProjectProfilePatch(
                expected_revision=1,
                scope_narrative=["x" * (MAX_SCOPE_NARRATIVE_ITEM_CHARS + 1)],
            ),
        )
    assert "characters" in str(excinfo.value)


def test_the_cap_boundary_is_accepted() -> None:
    project = _project()
    plan = validate_profile_patch(
        project,
        ProjectProfilePatch(
            expected_revision=1,
            scope_narrative=[
                "y" * MAX_SCOPE_NARRATIVE_ITEM_CHARS
                for _ in range(MAX_SCOPE_NARRATIVE_ITEMS)
            ],
        ),
    )
    assert len(plan.after.scope_narrative) == MAX_SCOPE_NARRATIVE_ITEMS
