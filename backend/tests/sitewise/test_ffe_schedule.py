"""FFE Schedule shared-knowledge helpers and PMP section rendering."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.database.project import Project
from app.projects.project_knowledge import (
    SharedProjectObjectUpdate,
    upsert_shared_project_object,
)
from app.sitewise.ffe_schedule import ffe_schedule_rows
from app.sitewise.mobilisation_evidence import MobilisationEvidencePack
from app.sitewise.pmp_renderer import render_pmp_scaffold
from app.workflows.create_pmp import markdown_section_headings

_EMPTY_STUB = "TBC — record finishes, fixtures and equipment selections"
_UNIFIED_HEADER = "| Item | Location | Qty | Finish | Status | Notes |"


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
    assert headings.index("Consultants") + 1 == headings.index("FFE Schedule")
    assert "| Freestanding bath | Ensuite | 1 | TBC | To be confirmed | Owner selection |" in (
        markdown
    )
    assert _UNIFIED_HEADER in markdown
    assert "Make / capacity" not in markdown


def _taxonomy_project(
    *,
    title: str,
    building_class: str,
    work_type: str,
    subclasses: list[str],
    work_scope: list[str] | None = None,
    assets: list[dict] | None = None,
) -> SimpleNamespace:
    taxonomy: dict = {
        "subclasses": subclasses,
        "work_scope": work_scope or [],
    }
    if assets is not None:
        taxonomy["assets"] = assets
    return SimpleNamespace(
        slug=title.lower().replace(" ", "-"),
        title=title,
        workspace_path=f"04-projects/{title.lower().replace(' ', '-')}",
        phase="brief-planning",
        building_class=building_class,
        work_type=work_type,
        state="NSW",
        project_metadata={"taxonomy": taxonomy},
    )


def _ffe_body(markdown: str) -> str:
    headings = markdown_section_headings(markdown)
    start = markdown.index("## FFE Schedule")
    next_heading = None
    for heading in headings:
        marker = f"## {heading}"
        at = markdown.index(marker)
        if at > start:
            next_heading = at
            break
    return markdown[start:next_heading]


def test_new_house_prepopulates_wet_area_and_envelope_items() -> None:
    markdown = render_pmp_scaffold(
        _taxonomy_project(
            title="Knock-down rebuild",
            building_class="residential",
            work_type="new",
            subclasses=["house"],
        ),
        MobilisationEvidencePack(),
        "platform_seeded",
    )
    body = _ffe_body(markdown)

    assert _EMPTY_STUB not in body
    assert _UNIFIED_HEADER in body
    for item in (
        "Wall and floor tiles",
        "Basin",
        "WC",
        "Shower screen",
        "Facade cladding",
        "Roof sheeting / covering",
        "Paving",
    ):
        assert item in body, item
    assert "interior and exterior" in body.lower()


def test_rail_station_prepopulates_exterior_finishes_not_an_empty_stub() -> None:
    markdown = render_pmp_scaffold(
        _taxonomy_project(
            title="Rail station upgrade",
            building_class="infrastructure",
            work_type="refurb",
            subclasses=["rail_metro"],
            work_scope=["facade_system", "roofing"],
        ),
        MobilisationEvidencePack(),
        "platform_seeded",
    )
    body = _ffe_body(markdown)

    assert _EMPTY_STUB not in body
    assert _UNIFIED_HEADER in body
    assert "Facade cladding" in body
    assert "Roof sheeting / covering" in body
    assert "Paving" in body
    assert "Make / capacity" not in markdown


def test_fire_services_refurb_prepopulates_equipment_on_the_unified_schedule() -> None:
    markdown = render_pmp_scaffold(
        _taxonomy_project(
            title="Fire upgrade",
            building_class="industrial",
            work_type="refurb",
            subclasses=["warehouse"],
            work_scope=["fire_services"],
        ),
        MobilisationEvidencePack(),
        "platform_seeded",
    )
    body = _ffe_body(markdown)

    assert _EMPTY_STUB not in body
    assert "Fire pumpset" in body
    assert "Sprinkler heads / valves" in body
    assert _UNIFIED_HEADER in body


def test_assets_and_typical_finishes_share_one_table() -> None:
    markdown = render_pmp_scaffold(
        _taxonomy_project(
            title="Plant replacement",
            building_class="commercial",
            work_type="refurb",
            subclasses=["office"],
            work_scope=["mechanical_hvac", "roofing"],
            assets=[
                {
                    "type": "Split ducted air conditioning system",
                    "count": 2,
                    "location": "Service centre",
                    "capacity": "30kW",
                    "action": "replace",
                }
            ],
        ),
        MobilisationEvidencePack(),
        "platform_seeded",
    )
    body = _ffe_body(markdown)

    assert "Split ducted air conditioning system" in body
    assert "30kW" in body
    assert "Roof sheeting / covering" in body
    assert "Kitchen joinery" not in body
    assert _UNIFIED_HEADER in body
    assert "Make / capacity" not in markdown
    assert "Equipment schedule derived" not in markdown
    assert _EMPTY_STUB not in body


def test_office_refurb_prepopulates_interior_finishes() -> None:
    markdown = render_pmp_scaffold(
        _taxonomy_project(
            title="Tenancy refresh",
            building_class="commercial",
            work_type="refurb",
            subclasses=["office"],
        ),
        MobilisationEvidencePack(),
        "platform_seeded",
    )
    body = _ffe_body(markdown)

    assert _EMPTY_STUB not in body
    for item in (
        "Floor finish",
        "Wall finish / paint",
        "Ceiling finish",
        "Joinery",
        "Kitchen joinery",
    ):
        assert item in body, item
