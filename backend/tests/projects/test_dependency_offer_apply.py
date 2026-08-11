"""F6: apply accepted dependency offers without overwriting protected facts."""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.database.project import Project
from app.projects.dependencies import (
    mark_project_dirty_from_change,
    resolve_concrete_affected,
    list_dependency_offers,
)
from app.projects.dependency_offers import accept_dependency_offer


class _Session:
    def __init__(self) -> None:
        self.drafts: dict[uuid.UUID, SimpleNamespace] = {}
        self.cost_items: list[dict] = []
        self.requests: list[dict] = []
        self.flushed = False

    async def flush(self) -> None:
        self.flushed = True


def test_accept_applies_deterministic_reference_to_selected_only() -> None:
    project = Project(
        id=uuid.uuid4(),
        owner_user_id=uuid.uuid4(),
        slug="demo",
        title="Demo",
        workspace_path="04-projects/demo",
        phase="brief-planning",
        project_metadata={},
    )
    draft_id = uuid.uuid4()
    markdown = (
        "## Consultants\n\n"
        "| Discipline | Firm |\n"
        "| --- | --- |\n"
        "| Hydraulic engineer | ABC Engineering | "
        "<!-- clerk:block id=blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -->\n"
    )
    session = _Session()
    session.drafts[draft_id] = SimpleNamespace(
        id=draft_id,
        project_id=project.id,
        version=1,
        content_markdown=markdown,
        provenance_metadata={
            "blocks": {
                "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": {
                    "id": "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "type": "table_row",
                    "user_protected": False,
                    "created_by": "ai",
                    "last_modified_by": "ai",
                    "created_at": "2026-08-10T00:00:00+00:00",
                    "updated_at": "2026-08-10T00:00:00+00:00",
                    "baseline_content_hash": "x",
                }
            }
        },
        workflow_type="create_pmp",
    )
    artefacts = resolve_concrete_affected(
        ["consultants_dirty"],
        source_kind="consultant",
        object_id="hydraulic",
        previous_value={"name": "ABC Engineering"},
        new_value={"name": "Fluid Design"},
        procurement_requests=(
            {
                "id": str(uuid.uuid4()),
                "kind": "consultant_rfp",
                "target_slug": "hydraulic_engineer",
                "current_draft_artifact_id": str(draft_id),
            },
        ),
        cost_items=(
            {
                "item_key": "received-proposal:hydraulic_engineer",
                "category": "Consultants",
                "item": "Hydraulic engineer — ABC Engineering",
            },
        ),
        pmp_blocks=(
            {
                "id": "blk_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "section_id": "consultants",
                "content": "| Hydraulic engineer | ABC Engineering |",
            },
        ),
    )
    # Point pmp/consultant_register at the same draft for the accept path.
    enriched = []
    for item in artefacts:
        if item.artefact_type in {"pmp", "consultant_register"}:
            enriched.append(
                item.model_copy(
                    update={
                        "selector": item.selector.model_copy(
                            update={"draft_id": str(draft_id)}
                        )
                    }
                )
            )
        else:
            enriched.append(item)
    mark_project_dirty_from_change(
        project,
        categories=("consultants_dirty",),
        source_kind="consultant",
        object_id="hydraulic",
        previous_value={"name": "ABC Engineering"},
        new_value={"name": "Fluid Design"},
        artefacts=tuple(enriched),
    )
    offer = list_dependency_offers(project)[0]

    async def _get_draft(session_obj, draft_uuid):
        return session_obj.drafts.get(draft_uuid)

    async def _revise(**kwargs):
        draft = kwargs["draft"]
        draft.content_markdown = kwargs["content_markdown"]
        draft.version += 1
        return draft

    result = asyncio.run(
        accept_dependency_offer(
            session,
            project=project,
            offer_id=offer.id,
            artefact_types=["pmp"],
            author_user_id=project.owner_user_id,
            get_draft=_get_draft,
            revise_draft=_revise,
            update_cost_item_labels=lambda *_a, **_k: [
                "received-proposal:hydraulic_engineer"
            ],
        )
    )

    assert "Fluid Design" in session.drafts[draft_id].content_markdown
    assert result.updated_artefact_types == ("pmp",)
    remaining = list_dependency_offers(project)[0]
    assert {item.artefact_type for item in remaining.artefacts} == {
        "rfp",
        "consultant_register",
        "cost_plan",
    }
