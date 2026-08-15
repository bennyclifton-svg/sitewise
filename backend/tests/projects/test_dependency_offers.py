"""F6: actionable dependency offers and concrete cross-artefact selectors."""

from __future__ import annotations

import uuid

from app.database.project import Project
from app.projects.dependencies import (
    apply_deterministic_reference_update,
    clear_consumed_dependency_entries,
    list_dependency_offers,
    mark_project_dirty_from_change,
    reject_dependency_offer,
    resolve_concrete_affected,
)
from app.projects.project_knowledge import (
    SharedProjectObjectUpdate,
    list_shared_project_objects,
    get_shared_project_object,
    upsert_shared_project_object,
)


def _project(**overrides) -> Project:
    values = {
        "id": uuid.uuid4(),
        "owner_user_id": uuid.uuid4(),
        "slug": "demo",
        "title": "Demo",
        "workspace_path": "04-projects/demo",
        "phase": "brief-planning",
        "project_metadata": {},
    }
    values.update(overrides)
    return Project(**values)


def test_hydraulic_consultant_change_identifies_exact_dependants() -> None:
    affected = resolve_concrete_affected(
        ["consultants_dirty"],
        source_kind="consultant",
        object_id="hydraulic",
        previous_value={"name": "ABC Engineering"},
        new_value={"name": "Fluid Design"},
        procurement_requests=(
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "kind": "consultant_rfp",
                "target_slug": "hydraulic_engineer",
                "current_draft_artifact_id": "22222222-2222-2222-2222-222222222222",
            },
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "kind": "consultant_rfp",
                "target_slug": "structural_engineer",
                "current_draft_artifact_id": "44444444-4444-4444-4444-444444444444",
            },
        ),
        cost_items=(
            {
                "item_key": "received-proposal:hydraulic_engineer",
                "category": "Consultants",
                "item": "Hydraulic engineer — ABC Engineering",
            },
            {
                "item_key": "received-proposal:architect",
                "category": "Consultants",
                "item": "Architect — Studio A",
            },
            {
                "item_key": "scaffold:finishes",
                "category": "Finishes and external works",
                "item": "Finishes",
            },
        ),
        pmp_blocks=(
            {
                "id": "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "section_id": "consultants",
                "content": "| Hydraulic engineer | ABC Engineering |",
            },
            {
                "id": "blk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "section_id": "programme",
                "content": "Programme milestone",
            },
        ),
    )

    by_type = {item.artefact_type: item for item in affected}
    assert set(by_type) == {
        "consultant_register",
        "pmp",
        "rfp",
        "cost_plan",
    }
    assert by_type["rfp"].selector.discipline_slug == "hydraulic_engineer"
    assert by_type["rfp"].selector.procurement_request_id == (
        "11111111-1111-1111-1111-111111111111"
    )
    assert by_type["rfp"].selector.draft_id == (
        "22222222-2222-2222-2222-222222222222"
    )
    assert by_type["pmp"].selector.block_ids == (
        "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    assert by_type["pmp"].selector.section_ids == ("consultants",)
    assert by_type["consultant_register"].selector.section_ids == ("consultants",)
    assert by_type["cost_plan"].selector.cost_item_keys == (
        "received-proposal:hydraulic_engineer",
    )
    assert "structural" not in (
        by_type["rfp"].selector.discipline_slug or ""
    )


def test_ffe_change_identifies_only_package_dependants() -> None:
    affected = resolve_concrete_affected(
        ["ffe_dirty", "cost_dirty"],
        source_kind="ffe_item",
        object_id="bathroom-finish",
        previous_value={"name": "Matte white tile", "package": "bathroom"},
        new_value={"name": "Honed limestone", "package": "bathroom"},
        procurement_requests=(
            {
                "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "kind": "trade_rft",
                "target_slug": "bathroom",
                "current_draft_artifact_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            },
            {
                "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "kind": "trade_rft",
                "target_slug": "structural_steel",
                "current_draft_artifact_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
            },
        ),
        cost_items=(
            {
                "item_key": "finishes:bathroom",
                "category": "Finishes and external works",
                "item": "Bathroom finishes — Matte white tile",
            },
            {
                "item_key": "received-proposal:architect",
                "category": "Consultants",
                "item": "Architect",
            },
        ),
        pmp_blocks=(
            {
                "id": "blk_ffffffffffffffffffffffffffffffff",
                "section_id": "ffe-schedule",
                "content": "| Matte white tile | Bathroom | 1 | Matte white | Selected | — |",
            },
            {
                "id": "blk_eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
                "section_id": "procurement-delivery",
                "content": "Procurement route",
            },
        ),
    )

    by_type = {item.artefact_type: item for item in affected}
    assert set(by_type) == {"pmp", "rft", "cost_plan"}
    assert "consultant_register" not in by_type
    assert by_type["rft"].selector.package_slug == "bathroom"
    assert by_type["rft"].selector.procurement_request_id == (
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    )
    assert by_type["cost_plan"].selector.cost_item_keys == ("finishes:bathroom",)
    assert by_type["pmp"].selector.block_ids == (
        "blk_ffffffffffffffffffffffffffffffff",
    )
    assert by_type["pmp"].selector.section_ids == ("ffe-schedule",)
    assert "programme" not in by_type["pmp"].selector.section_ids


def test_accommodation_change_identifies_only_the_schedule_section() -> None:
    affected = resolve_concrete_affected(
        ["accommodation_dirty"],
        source_kind="accommodation_space",
        object_id="kitchen",
        previous_value={"space": "Kitchen", "level": "Ground", "area": "16"},
        new_value={"space": "Kitchen", "level": "Ground", "area": "18"},
        pmp_blocks=(
            {
                "id": "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "section_id": "accommodation-schedule",
                "content": "| Kitchen | Ground | 16 m² | TBC | New |",
            },
            {
                "id": "blk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "section_id": "scope-client-requirements",
                "content": "Brief prose",
            },
            {
                "id": "blk_cccccccccccccccccccccccccccccccc",
                "section_id": "ffe-schedule",
                "content": "| Basin | Ensuite | 1 | TBC | Selected | — |",
            },
        ),
    )

    by_type = {item.artefact_type: item for item in affected}
    assert set(by_type) == {"pmp"}
    assert by_type["pmp"].selector.section_ids == ("accommodation-schedule",)
    assert by_type["pmp"].selector.block_ids == (
        "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    assert "cost_plan" not in by_type
    assert "rft" not in by_type


def test_upsert_consultant_records_pending_offer_with_concrete_selectors() -> None:
    project = _project()
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="hydraulic",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={"name": "ABC Engineering"},
        ),
        source="user",
    )
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="hydraulic",
        update=SharedProjectObjectUpdate(
            expected_revision=1,
            value={"name": "Fluid Design"},
        ),
        source="user",
    )

    offers = list_dependency_offers(project)
    assert len(offers) == 1
    offer = offers[0]
    assert offer.category == "consultants_dirty"
    assert offer.source.kind == "consultant"
    assert offer.source.object_id == "hydraulic"
    assert offer.reference_patch == {
        "from": "ABC Engineering",
        "to": "Fluid Design",
    }
    types = {item.artefact_type for item in offer.artefacts}
    assert types == {"pmp", "rfp", "consultant_register", "cost_plan"}
    rfp = next(item for item in offer.artefacts if item.artefact_type == "rfp")
    assert rfp.selector.discipline_slug == "hydraulic_engineer"


def test_accept_updates_only_selected_artefacts_and_clears_consumed() -> None:
    project = _project()
    mark_project_dirty_from_change(
        project,
        categories=("consultants_dirty",),
        source_kind="consultant",
        object_id="hydraulic",
        previous_value={"name": "ABC Engineering"},
        new_value={"name": "Fluid Design"},
        artefacts=resolve_concrete_affected(
            ["consultants_dirty"],
            source_kind="consultant",
            object_id="hydraulic",
            previous_value={"name": "ABC Engineering"},
            new_value={"name": "Fluid Design"},
            procurement_requests=(
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "kind": "consultant_rfp",
                    "target_slug": "hydraulic_engineer",
                    "current_draft_artifact_id": None,
                },
            ),
            cost_items=(
                {
                    "item_key": "received-proposal:hydraulic_engineer",
                    "category": "Consultants",
                    "item": "Hydraulic engineer — ABC Engineering",
                },
            ),
            pmp_blocks=(),
        ),
    )
    offer = list_dependency_offers(project)[0]
    selected = ["rfp", "cost_plan"]

    remaining = clear_consumed_dependency_entries(
        project,
        offer_id=offer.id,
        artefact_types=selected,
    )

    assert {item.artefact_type for item in remaining.artefacts} == {
        "pmp",
        "consultant_register",
    }
    assert project.project_metadata["dirty_categories"] == ["consultants_dirty"]
    assert len(list_dependency_offers(project)) == 1


def test_reject_changes_none_and_clears_dismissed_entries() -> None:
    project = _project()
    mark_project_dirty_from_change(
        project,
        categories=("consultants_dirty",),
        source_kind="consultant",
        object_id="hydraulic",
        previous_value={"name": "ABC"},
        new_value={"name": "Fluid Design"},
        artefacts=resolve_concrete_affected(
            ["consultants_dirty"],
            source_kind="consultant",
            object_id="hydraulic",
            previous_value={"name": "ABC"},
            new_value={"name": "Fluid Design"},
            procurement_requests=(),
            cost_items=(),
            pmp_blocks=(),
        ),
    )
    offer = list_dependency_offers(project)[0]

    reject_dependency_offer(project, offer_id=offer.id)

    assert list_dependency_offers(project) == []
    assert "dirty_categories" not in project.project_metadata
    assert "dependency_offers" not in project.project_metadata


def test_deterministic_reference_update_skips_protected_blocks() -> None:
    markdown = (
        "## Consultants\n\n"
        "| Discipline | Firm |\n"
        "| --- | --- |\n"
        "| Hydraulic engineer | ABC Engineering | "
        "<!-- clerk:block id=blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -->\n\n"
        "| Structural engineer | ABC Engineering | "
        "<!-- clerk:block id=blk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -->\n"
    )
    metadata = {
        "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": {
            "id": "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "type": "table_row",
            "user_protected": False,
            "created_by": "ai",
            "last_modified_by": "ai",
            "created_at": "2026-08-10T00:00:00+00:00",
            "updated_at": "2026-08-10T00:00:00+00:00",
            "baseline_content_hash": "x",
        },
        "blk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb": {
            "id": "blk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "type": "table_row",
            "user_protected": True,
            "created_by": "user",
            "last_modified_by": "user",
            "created_at": "2026-08-10T00:00:00+00:00",
            "updated_at": "2026-08-10T00:00:00+00:00",
            "baseline_content_hash": "y",
        },
    }

    updated, changed = apply_deterministic_reference_update(
        markdown,
        metadata=metadata,
        block_ids=("blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                   "blk_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"),
        old_text="ABC Engineering",
        new_text="Fluid Design",
    )

    assert "Fluid Design" in updated
    assert changed == ("blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",)
    assert (
        "| Structural engineer | ABC Engineering |" in updated
    )


def test_list_and_get_shared_project_objects() -> None:
    project = _project()
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="hydraulic",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={"name": "Fluid Design"},
        ),
        source="user",
    )
    upsert_shared_project_object(
        project,
        kind="ffe_item",
        object_id="bathroom-finish",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={"name": "Tile", "package": "bathroom"},
        ),
        source="user",
    )

    listed = list_shared_project_objects(project)
    assert {item.kind for item in listed} == {"consultant", "ffe_item"}
    fetched = get_shared_project_object(
        project, kind="consultant", object_id="hydraulic"
    )
    assert fetched is not None
    assert fetched.value["name"] == "Fluid Design"
    assert (
        get_shared_project_object(project, kind="consultant", object_id="missing")
        is None
    )
