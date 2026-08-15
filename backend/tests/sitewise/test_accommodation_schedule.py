"""Accommodation Schedule shared-knowledge helpers."""

from __future__ import annotations

import uuid

from app.database.project import Project
from app.projects.project_knowledge import (
    SharedProjectObjectUpdate,
    upsert_shared_project_object,
)
from app.sitewise.accommodation_schedule import (
    accommodation_schedule_rows,
    parse_area_m2,
    scheduled_area_total,
)


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
