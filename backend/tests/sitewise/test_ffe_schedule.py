"""FFE Schedule shared-knowledge helpers and PMP section rendering."""

from __future__ import annotations

import uuid

from app.database.project import Project
from app.projects.project_knowledge import (
    SharedProjectObjectUpdate,
    upsert_shared_project_object,
)
from app.sitewise.ffe_schedule import ffe_schedule_rows
from app.sitewise.mobilisation_evidence import MobilisationEvidencePack
from app.sitewise.pmp_renderer import render_pmp_scaffold
from app.workflows.create_pmp import markdown_section_headings


def _project() -> Project:
    return Project(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        owner_user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        slug="mosaic",
        title="Mosaic Apartments",
        workspace_path="04-projects/mosaic",
        phase="brief-planning",
        building_class="residential",
        work_type="new",
        state="NSW",
        project_metadata={"taxonomy": {"subclasses": ["apartments"]}},
    )


def test_ffe_schedule_rows_skip_removed_and_sort() -> None:
    project = _project()
    upsert_shared_project_object(
        project,
        kind="ffe_item",
        object_id="vanity",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={"item": "Vanity", "location": "Bathroom", "status": "Selected"},
        ),
        source="user",
    )
    upsert_shared_project_object(
        project,
        kind="ffe_item",
        object_id="freestanding-bath",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={"item": "Freestanding bath", "status": "To be confirmed"},
        ),
        source="user",
    )
    upsert_shared_project_object(
        project,
        kind="ffe_item",
        object_id="old-tap",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={"item": "Old tap", "status": "removed"},
        ),
        source="user",
    )

    rows = ffe_schedule_rows(project)
    assert [row["item"] for row in rows] == ["Freestanding bath", "Vanity"]
    assert rows[0]["location"] == "TBC"
    assert rows[1]["location"] == "Bathroom"


def test_taxonomy_scaffold_renders_shared_ffe_rows_after_brief() -> None:
    project = _project()
    upsert_shared_project_object(
        project,
        kind="ffe_item",
        object_id="freestanding-bath",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={
                "item": "Freestanding bath",
                "location": "Ensuite",
                "quantity": "1",
                "finish": "TBC",
                "status": "To be confirmed",
                "notes": "Owner selection",
            },
        ),
        source="user",
    )

    markdown = render_pmp_scaffold(
        project,
        MobilisationEvidencePack(),
        "platform_seeded",
    )
    headings = markdown_section_headings(markdown)
    assert headings.index("Brief") + 1 == headings.index("FFE Schedule")
    assert "| Freestanding bath | Ensuite | 1 | TBC | To be confirmed | Owner selection |" in (
        markdown
    )
