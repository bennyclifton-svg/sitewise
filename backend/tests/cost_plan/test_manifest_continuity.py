"""F9: Cost Plan edits retain the originating generation manifest."""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.cost_plan.calculations import calculate_totals
from app.cost_plan.schemas import CostItemInput, CostPlanState, DependencySnapshot
from app.cost_plan.service import _publish_state
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.projects.artefact_revisions import ArtefactRevisionResult


USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")

ORIGINATING_MANIFEST = {
    "schema_version": 1,
    "artefact_type": "cost_plan",
    "context_version": 4,
    "source_version": "aaaaaaaaaaaaaaaa",
    "seed_version": "bbbbbbbbbbbbbbbb",
    "input_fingerprint": "f" * 64,
    "taxonomy": {"building_class": "commercial"},
    "known_profile": {"identity.title": "Demo"},
    "unknown_relevant_fields": [],
    "explicitly_excluded_fields": ["scope.ffe"],
    "evidence_used": ["brief.pdf"],
    "seed_knowledge": ["seed/cost.md"],
    "constraints": ["Keep PC allowances separate"],
}


def test_publish_state_carries_originating_manifest_and_mutation() -> None:
    project = Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="demo",
        title="Demo",
        workspace_path="04-projects/demo",
    )
    prior = DraftArtifact(
        id=DRAFT_ID,
        project_id=PROJECT_ID,
        workflow_type="create_cost_plan",
        version=1,
        status="draft",
        title="Cost Plan",
        workspace_path="04-projects/demo/01-cost/cost_plan_v01.md",
        author_user_id=USER_ID,
        content_markdown="# Cost Plan",
        model="test",
        runtime="test",
        provenance_metadata={
            "typed_cost_plan": True,
            "generation_manifest": ORIGINATING_MANIFEST,
        },
    )
    published = DraftArtifact(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        workflow_type="create_cost_plan",
        version=2,
        status="draft",
        title="Cost Plan",
        workspace_path="04-projects/demo/01-cost/cost_plan_v02.md",
        author_user_id=USER_ID,
        content_markdown="# Cost Plan",
        model="test",
        runtime="test",
        provenance_metadata={},
    )
    items = [
        CostItemInput(
            item_key="joinery",
            cost_code="C-01",
            category="Construction",
            item="Joinery",
            budget=Decimal("100"),
            forecast=Decimal("100"),
            basis="Manual",
            status="manual",
        )
    ]
    state = CostPlanState(
        project_id=PROJECT_ID,
        version=1,
        dependency_snapshot=DependencySnapshot(
            profile_revision=1,
            evidence_fingerprint="evidence",
            decision_set_revision=1,
            runtime_version="test",
        ),
        items=items,
        totals=calculate_totals(
            items,
            contingency_percent=Decimal("0"),
            escalation_percent=Decimal("0"),
            gst_treatment="exclusive",
        ),
    )

    captured: dict = {}

    async def fake_publish(*_args, provenance: dict, **_kwargs):
        captured["provenance"] = dict(provenance)
        published.provenance_metadata = dict(provenance)
        return ArtefactRevisionResult(revision=published, export_jobs=())

    row = SimpleNamespace(items=[])

    with (
        patch(
            "app.cost_plan.service.get_latest_draft_artifact",
            new=AsyncMock(return_value=prior),
        ),
        patch(
            "app.cost_plan.service.complete_cost_plan_state",
            new=AsyncMock(side_effect=lambda *_args, **kwargs: kwargs["state"]),
        ),
        patch(
            "app.cost_plan.service.publish",
            new=AsyncMock(side_effect=fake_publish),
        ),
        patch(
            "app.cost_plan.service.CostPlanVersion",
            side_effect=lambda **kwargs: row,
        ),
        patch("app.cost_plan.service.CostPlanItem", side_effect=lambda **kwargs: kwargs),
        patch(
            "app.cost_plan.service._state",
            return_value=state.model_copy(update={"version": 2}),
        ),
    ):
        session = AsyncMock()
        asyncio.run(
            _publish_state(
                session,
                project=project,
                author_user_id=USER_ID,
                expected_base_version=1,
                state=state,
                actor_source="cost_plan_tool",
                mutation={
                    "kind": "cost_plan_edit",
                    "operations": [{"operation": "UPDATE"}],
                },
            )
        )

    provenance = captured["provenance"]
    assert provenance["generation_manifest"] == ORIGINATING_MANIFEST
    assert provenance["originating_generation_manifest"] == ORIGINATING_MANIFEST
    assert provenance["mutation"]["kind"] == "cost_plan_edit"
    assert provenance["mutation"]["operations"] == [{"operation": "UPDATE"}]
    assert provenance["typed_cost_plan"] is True
