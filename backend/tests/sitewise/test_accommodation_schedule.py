"""Accommodation Schedule shared-knowledge helpers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.database.project import Project
from app.projects.project_knowledge import (
    SharedProjectObjectUpdate,
    upsert_shared_project_object,
)
from app.sitewise.accommodation_schedule import (
    accommodation_schedule_display_rows,
    accommodation_schedule_rows,
    brief_accommodation_rows,
    parse_area_m2,
    scheduled_area_total,
)
from app.sitewise.mobilisation_evidence import MobilisationEvidencePack
from app.sitewise.pmp_renderer import render_pmp_scaffold
from app.sitewise.taxonomy import applicable_sections
from app.workflows.create_pmp import markdown_section_headings


def _project() -> Project:
    return Project(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        owner_user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        slug="harbour-house",
        title="Harbour House",
        workspace_path="04-projects/harbour-house",
        phase="brief-planning",
        building_class="residential",
        work_type="new",
        state="NSW",
        project_metadata={"taxonomy": {"subclasses": ["house"]}},
    )


def _add(project: Project, object_id: str, value: dict) -> None:
    upsert_shared_project_object(
        project,
        kind="accommodation_space",
        object_id=object_id,
        update=SharedProjectObjectUpdate(expected_revision=0, value=value),
        source="user",
    )


def test_parse_area_m2_reads_loose_text() -> None:
    assert parse_area_m2(24) == 24.0
    assert parse_area_m2("24") == 24.0
    assert parse_area_m2("24 m²") == 24.0
    assert parse_area_m2("approx 24") == 24.0
    assert parse_area_m2("24–28") == 24.0
    assert parse_area_m2("TBC") is None
    assert parse_area_m2("") is None
    assert parse_area_m2("pending survey") is None


def test_rows_skip_removed_and_sort_by_level() -> None:
    project = _project()
    _add(project, "courtyard", {
        "space": "Courtyard",
        "level": "External",
        "area": "40",
        "status": "New",
    })
    _add(project, "kitchen", {
        "space": "Kitchen",
        "level": "Ground",
        "area": "18 m²",
        "characteristics": "north-facing",
        "status": "New",
    })
    _add(project, "basement-store", {
        "space": "Store",
        "level": "Basement",
        "area": "8",
        "status": "Existing",
    })
    _add(project, "old-laundry", {
        "space": "Laundry",
        "level": "Ground",
        "status": "removed",
    })
    _add(project, "fake-total", {
        "space": "Scheduled area",
        "area": "999",
        "status": "TBC",
    })

    rows = accommodation_schedule_rows(project)
    assert [row["space"] for row in rows] == ["Store", "Kitchen", "Courtyard"]
    assert rows[1]["characteristics"] == "north-facing"
    assert rows[0]["characteristics"] == "TBC"


def test_scheduled_area_total_skips_demolished_and_unparseable() -> None:
    project = _project()
    _add(project, "kitchen", {"space": "Kitchen", "level": "Ground", "area": "18 m²", "status": "New"})
    _add(project, "deck", {"space": "Covered deck", "level": "External", "area": "approx 24", "status": "New"})
    _add(project, "old-bath", {"space": "Bathroom", "level": "Ground", "area": "6", "status": "Demolished"})
    _add(project, "study", {"space": "Study", "level": "First", "area": "TBC", "status": "New"})

    rows = accommodation_schedule_rows(project)
    assert scheduled_area_total(rows) == 42.0


_NEWTOWN_BRIEF = (
    "four bedrooms, a rear extension, second story addition to a semi "
    "master bedroom and parents retreat upstairs, new kitchen opening, "
    "open plan living dining"
)


def _project_with_brief(*lines: str) -> Project:
    project = _project()
    metadata = dict(project.project_metadata or {})
    taxonomy = dict(metadata.get("taxonomy") or {})
    taxonomy["scope_narrative"] = list(lines)
    metadata["taxonomy"] = taxonomy
    project.project_metadata = metadata
    return project


def test_brief_names_spaces_without_inventing_typical_rooms() -> None:
    rows = brief_accommodation_rows(_project_with_brief(_NEWTOWN_BRIEF))
    names = [row["space"] for row in rows]
    assert "Master bedroom" in names
    assert "Parents retreat" in names
    assert "Kitchen" in names
    assert "Living / dining" in names
    assert "Bedroom 2" not in names
    assert "Bedroom" not in names
    assert "Laundry" not in names
    assert "Garage" not in names
    assert "Extension" not in names
    assert "Addition" not in names
    master = next(row for row in rows if row["space"] == "Master bedroom")
    retreat = next(row for row in rows if row["space"] == "Parents retreat")
    kitchen = next(row for row in rows if row["space"] == "Kitchen")
    living = next(row for row in rows if row["space"] == "Living / dining")
    assert master["level"] == "First"
    assert retreat["level"] == "First"
    assert kitchen["status"] == "New"
    assert "open plan" in living["characteristics"].casefold()


def test_display_rows_keep_explicit_and_skip_removed_brief_spaces() -> None:
    project = _project_with_brief(
        "new kitchen, laundry, and a covered deck"
    )
    _add(project, "kitchen", {
        "space": "Kitchen",
        "level": "Ground",
        "area": "16 m²",
        "characteristics": "owner-selected",
        "status": "New",
    })
    _add(project, "laundry", {
        "space": "Laundry",
        "level": "Ground",
        "status": "removed",
    })

    rows = accommodation_schedule_display_rows(project)
    by_name = {row["space"]: row for row in rows}
    assert by_name["Kitchen"]["area"] == "16 m²"
    assert by_name["Kitchen"]["characteristics"] == "owner-selected"
    assert "Laundry" not in by_name
    assert "Covered deck" in by_name


def test_taxonomy_scaffold_renders_named_brief_spaces() -> None:
    project = _project_with_brief(_NEWTOWN_BRIEF)
    markdown = render_pmp_scaffold(
        project, MobilisationEvidencePack(), "platform_seeded"
    )
    assert "| Master bedroom |" in markdown
    assert "| Parents retreat |" in markdown
    assert "| Kitchen |" in markdown
    assert "| Living / dining |" in markdown
    assert "| — | — | TBC | TBC | To be confirmed |" not in markdown


def test_applicable_for_new_absent_for_remediation() -> None:
    assert "accommodation-schedule" in applicable_sections(
        work_type="new", work_scope=[]
    )
    assert "accommodation-schedule" not in applicable_sections(
        work_type="remediation", work_scope=[]
    )
    assert "accommodation-schedule" not in applicable_sections(
        work_type="advisory", work_scope=["building_condition"]
    )
    assert "accommodation-schedule" in applicable_sections(
        work_type="advisory", work_scope=["massing_study"]
    )


def test_taxonomy_scaffold_renders_spaces_and_scheduled_area() -> None:
    project = _project()
    _add(project, "kitchen", {
        "space": "Kitchen",
        "level": "Ground",
        "area": "18 m²",
        "characteristics": "4.2 × 3.6 m, north-facing",
        "status": "New",
    })
    _add(project, "deck", {
        "space": "Covered deck",
        "level": "External",
        "area": "24",
        "status": "New",
    })

    markdown = render_pmp_scaffold(
        project, MobilisationEvidencePack(), "platform_seeded"
    )
    headings = markdown_section_headings(markdown)
    assert headings.index("Consultants") + 1 == headings.index(
        "Accommodation Schedule"
    )
    assert headings.index("Accommodation Schedule") + 1 == headings.index(
        "FFE Schedule"
    )
    assert "| Space | Level | Area | Characteristics | Status |" in markdown
    assert "| Kitchen | Ground | 18 m² | 4.2 × 3.6 m, north-facing | New |" in markdown
    assert "| **Scheduled area** |  | 42 m² |  |  |" in markdown


def test_remediation_project_omits_the_section() -> None:
    project = SimpleNamespace(
        slug="plant-swap",
        title="Plant swap",
        workspace_path="04-projects/plant-swap",
        phase="brief-planning",
        building_class="industrial",
        work_type="remediation",
        state="NSW",
        project_metadata={"taxonomy": {"subclasses": ["warehouse"]}},
    )
    markdown = render_pmp_scaffold(
        project, MobilisationEvidencePack(), "platform_seeded"
    )
    assert "Accommodation Schedule" not in markdown_section_headings(markdown)
