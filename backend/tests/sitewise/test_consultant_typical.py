"""Typical house consultant roster — starter rows, not appointments."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.database.project import Project
from app.projects.project_knowledge import (
    SharedProjectObjectUpdate,
    upsert_shared_project_object,
)
from app.sitewise.consultant_typical import typical_consultant_labels
from app.sitewise.pmp_renderer import _render_taxonomy_consultants


def _house(
    *,
    work_type: str = "extend",
    work_scope: list[str] | None = None,
    subclasses: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        title="New Town Extension",
        building_class="residential",
        work_type=work_type,
        state="NSW",
        project_metadata={
            "taxonomy": {
                "subclasses": ["house"] if subclasses is None else subclasses,
                "work_scope": work_scope or [],
            }
        },
    )


def _project() -> Project:
    return Project(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        owner_user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        slug="new-town-extension",
        title="New Town Extension",
        workspace_path="04-projects/new-town-extension",
        phase="brief-planning",
        building_class="residential",
        work_type="extend",
        state="NSW",
        project_metadata={"taxonomy": {"subclasses": ["house"], "work_scope": []}},
    )


def _disciplines(markdown: str) -> list[str]:
    rows = [line for line in markdown.splitlines() if line.startswith("| ")]
    return [row.split("|")[1].strip() for row in rows[2:]]


def test_house_construction_gets_the_four_starter_disciplines() -> None:
    expected = (
        "Architect",
        "Structural Engineer",
        "Town Planner",
        "Civil / stormwater",
    )
    for work_type in ("new", "extend", "refurb"):
        assert typical_consultant_labels(
            work_type=work_type, subclasses=["house"]
        ) == expected


def test_typical_roster_skips_office_and_non_construction_houses() -> None:
    assert typical_consultant_labels(work_type="refurb", subclasses=["office"]) == ()
    assert typical_consultant_labels(work_type="extend", subclasses=["townhouses"]) == ()
    assert typical_consultant_labels(work_type="remediation", subclasses=["house"]) == ()
    assert typical_consultant_labels(work_type="advisory", subclasses=["house"]) == ()


def test_house_extension_register_lists_starter_rows_not_the_stub() -> None:
    markdown = _render_taxonomy_consultants(_house())
    assert _disciplines(markdown) == [
        "Architect",
        "Structural Engineer",
        "Town Planner",
        "Civil / stormwater",
    ]
    assert "Discipline roster" not in markdown
    assert "The Architect row is the design lead" not in markdown
    assert "Design lead — to be confirmed" in markdown
    assert "| Architect | TBC | | Not evidenced | — |" in markdown


def test_scope_and_appointment_rows_are_not_duplicated() -> None:
    markdown = _render_taxonomy_consultants(
        _house(work_scope=["structural_tie_in", "partitions_walls"])
    )
    disciplines = _disciplines(markdown)
    assert disciplines[0] == "Structural Engineer"
    assert disciplines.count("Architect") == 1
    assert disciplines.count("Structural Engineer") == 1
    assert "Town Planner" in disciplines
    assert "Civil / stormwater" in disciplines


def test_removed_typical_discipline_stays_gone() -> None:
    project = _project()
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="town-planner",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={"discipline": "Town Planner", "firm": "TBC", "status": "removed"},
        ),
        source="user",
    )

    markdown = _render_taxonomy_consultants(project)
    assert "Town Planner" not in _disciplines(markdown)
    assert "Architect" in _disciplines(markdown)
