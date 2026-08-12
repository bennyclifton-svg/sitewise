"""Integration tests for typed Create Cost Plan (Harrison Clarke / Test Project 112)."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings
from app.cost_plan.import_legacy import parse_legacy_draft
from app.projects.generation_brief import build_generation_brief
from app.projects.generation_context import (
    ContextField,
    FieldState,
    ProjectGenerationContext,
)
from app.sitewise.cost_plan_sources import required_platform_paths
from app.workflows.create_cost_plan import (
    RUNTIME_TYPED_NAME,
    run_create_cost_plan_typed,
    run_create_cost_plan_workflow,
    validate_cost_plan_output,
    CostPlanDraftOutput,
    WorkflowValidationError,
)
from tests.conftest import run_async
from tests.sitewise.test_cost_plan_evidence import FIXTURE_DIR
from tests.sitewise.test_cost_plan_renderer import (
    _warehouse_cost_pack,
    _warehouse_project,
)
from tests.workflows.hybrid_cost_plan_fixtures import (
    USER_ID,
    harrison_clarke_cost_passages,
    harrison_clarke_cost_project,
    mock_cost_plan_draft,
    platform_passages_for_cost_plan,
)
from tests.workflows.hybrid_pmp_fixtures import evidence_passage, platform_passage


KAVANAGH_COST_FIXTURE_DIR = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "synthetic-mobilisation-evidence"
    / "kavanagh-residence-cost-files"
)
CONTRACT_PRICE_SCHEDULE_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "cost_plan"
    / "fixtures"
    / "large_contract_price_schedule.md"
)


def _typed_import(draft):
    return replace(parse_legacy_draft(draft), typed_version_id=draft.id)


def _generation_context(project_id) -> ProjectGenerationContext:
    def known(key: str, value: object) -> ContextField:
        return ContextField(
            key=key,
            label=key.replace("_", " ").title(),
            value=value,
            state=FieldState.KNOWN,
            source="project",
        )

    return ProjectGenerationContext(
        project_id=project_id,
        context_version=7,
        identity={"title": known("title", "Chen Residence")},
        taxonomy={
            "building_class": known("building_class", "residential"),
            "work_type": known("work_type", "new"),
            "subclasses": known("subclasses", ["house"]),
            "state": known("state", "NSW"),
            "user_role": known("user_role", "architect-pm"),
        },
        scale={},
        complexity={},
        scope={},
        commercial={},
        programme={},
        approvals={},
        stakeholders={},
        derived_risks=[],
    )


def _harrison_clarke_source_texts() -> list[str]:
    fixture_names = [
        "01-engagement-letter-harrison-clarke-studio.md",
        "02-fee-proposal-harrison-clarke-studio.md",
        "03-owner-project-brief-chen-residence.md",
        "09-planning-pathway-memo-harrison-clarke.md",
        "06-geotechnical-report-terratech.md",
        "11-master-programme-chen-residence.md",
        "12-certifier-appointment-chen-residence.md",
    ]
    return [(FIXTURE_DIR / name).read_text(encoding="utf-8") for name in fixture_names]


def _kavanagh_cost_passages(project) -> list:
    fixture_names = [
        "01-fee-proposal-quoin-architecture.md",
        "02-fee-proposal-catenary-structures.md",
        "03-fee-proposal-flowline-hydraulics.md",
        "04-fee-proposal-vertex-cost-advisory.md",
        "05-building-proposal-ironbark-main-works.md",
    ]
    return [
        evidence_passage(
            f"{project.slug}/01-cost/received/{name}",
            (KAVANAGH_COST_FIXTURE_DIR / name).read_text(encoding="utf-8"),
            project_slug=project.slug,
        ).model_copy(update={"project_id": project.id})
        for name in fixture_names
    ]


def assert_typed_cost_plan_acceptance_criteria(
    output: CostPlanDraftOutput,
) -> None:
    markdown = output.markdown.lower()
    assert "| cost code | category | cost items | budget | status | basis |" in markdown
    assert "1,850,000" in output.markdown or any(
        item.budget == Decimal("1850000")
        or (
            item.category.lower() == "construction"
            and item.budget is not None
        )
        for item in output._cost_items
    )
    assert any(
        item.budget == Decimal("148500") or item.budget == Decimal("148500.00")
        for item in output._cost_items
    )
    assert any(
        item.budget == Decimal("120000") or item.budget == Decimal("120000.00")
        for item in output._cost_items
    )
    assert "cost plan summary and control decision" not in markdown
    assert "source evidence and audit trail" not in markdown
    assert len(output._cost_items) >= 10


def test_cost_plan_hybrid_compiler_defaults_to_enabled() -> None:
    assert Settings.model_fields["cost_plan_hybrid_compiler"].default is True


def test_typed_harrison_clarke_cost_plan_integration() -> None:
    project = harrison_clarke_cost_project()
    cost_passages = [
        passage.model_copy(update={"project_id": project.id})
        for passage in harrison_clarke_cost_passages(project_slug=project.slug)
    ]
    platform_passages = platform_passages_for_cost_plan(project)
    draft = mock_cost_plan_draft()
    workbook_metadata = {
        "file_name": "Cost_Plan_v01.draft.xlsx",
        "workspace_path": "04-projects/test-project-112/01-cost/Cost_Plan_v01.draft.xlsx",
        "version": 1,
        "content_hash": "abc123",
        "size_bytes": 1234,
        "row_count": 10,
        "cost_item_lookup_count": 10,
        "warnings": [],
        "generated_at": "2026-06-08T00:00:00+00:00",
    }

    with (
        patch(
            "app.workflows.create_cost_plan.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.list_cost_evidence_paths",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.load_cost_project_evidence_documents",
            new=AsyncMock(return_value=cost_passages),
        ),
        patch(
            "app.workflows.create_cost_plan.load_platform_documents_by_paths",
            new=AsyncMock(return_value=(platform_passages, [])),
        ),
        patch(
            "app.workflows.create_cost_plan.build_generation_brief",
            wraps=build_generation_brief,
        ) as build_brief,
        patch(
            "app.workflows.create_cost_plan._next_version_hint",
            new=AsyncMock(return_value=1),
        ),
        patch(
            "app.workflows.create_cost_plan.create_draft_artifact",
            new=AsyncMock(return_value=draft),
        ) as create_draft,
        patch(
            "app.workflows.create_cost_plan.import_legacy_draft",
            new=AsyncMock(return_value=_typed_import(draft)),
        ),
        patch(
            "app.workflows.create_cost_plan.sync_cost_plan_draft_workspace",
            new=AsyncMock(return_value=draft.workspace_path),
        ),
        patch(
            "app.workflows.create_cost_plan.save_cost_plan_workbook_artifact",
            new=AsyncMock(return_value=workbook_metadata),
        ),
    ):
        result = run_async(
            run_create_cost_plan_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=project,
                thread_id=None,
                generation_context=_generation_context(project.id),
            )
        )

    assert result.status == "complete", result.message
    markdown = create_draft.await_args.kwargs["content_markdown"]
    output = CostPlanDraftOutput(
        title="Project Cost Plan",
        markdown=markdown,
        seed_consulted=[
            p.relative_path
            for p in platform_passages
            if p.source_type == "reference"
        ],
        evidence_refs=[
            f"project_evidence:{p.relative_path}#chunk=0" for p in cost_passages
        ],
        context_refs=[
            f"{p.source_type}:{p.relative_path}#chunk={p.chunk_id}"
            for p in platform_passages
        ],
    )
    # Reconstruct typed items from the create path by re-running typed compiler.
    typed = run_async(
        run_create_cost_plan_typed(
            project=project,
            passages=[*cost_passages, *platform_passages],
            draft_mode="evidence_grounded",
            chat_model="gpt-5.6-terra",
            project_source_texts=_harrison_clarke_source_texts(),
            trace=[],
        )
    )
    output._cost_items = typed._cost_items
    assert_typed_cost_plan_acceptance_criteria(output)

    validate_cost_plan_output(
        output,
        "evidence_grounded",
        archetype="new-dwelling",
        source_texts=_harrison_clarke_source_texts(),
    )

    provenance = create_draft.await_args.kwargs["provenance_metadata"]
    assert provenance["compiler"] == "typed"
    assert build_brief.call_count == 1
    assert create_draft.await_args.kwargs["runtime"] == RUNTIME_TYPED_NAME
    steps = {event.step for event in result.trace}
    assert {"extract", "typed_rows", "validation"}.issubset(steps)
    assert "narrative" not in steps
    assert "assemble" not in steps


def test_typed_create_cost_plan_maps_received_main_works_proposal_to_typed_rows() -> (
    None
):
    """A structured fixed-price proposal must price a newly created Cost Plan."""
    project = harrison_clarke_cost_project()
    passages = [
        *_kavanagh_cost_passages(project),
        *platform_passages_for_cost_plan(project),
    ]

    output = run_async(
        run_create_cost_plan_typed(
            project=project,
            passages=passages,
            draft_mode="evidence_grounded",
            chat_model="gpt-5.6-terra",
            project_source_texts=[passage.content for passage in passages[:5]],
            trace=[],
        )
    )

    construction_total = sum(
        (item.budget or Decimal("0"))
        for item in output._cost_items
        if item.category == "Construction"
    )
    assert construction_total == Decimal("1234000")
    assert any(
        item.item == "Preliminaries" and item.budget == Decimal("136000")
        for item in output._cost_items
    )

    draft = mock_cost_plan_draft()
    draft.content_markdown = output.markdown
    typed = parse_legacy_draft(draft)
    assert typed.parsed_budget_total > Decimal("0")
    assert any(item.category == "Construction" for item in typed.items)


def test_typed_cost_plan_adopts_contract_schedule_as_typed_construction_rows() -> None:
    project = harrison_clarke_cost_project()
    schedule = evidence_passage(
        f"{project.slug}/_inbox/ANX V CONTACT PRICE SCHEDULE [B].pdf",
        CONTRACT_PRICE_SCHEDULE_FIXTURE.read_text(encoding="utf-8"),
        project_slug=project.slug,
    ).model_copy(update={"project_id": project.id})
    passages = [schedule, *platform_passages_for_cost_plan(project)]

    output = run_async(
        run_create_cost_plan_typed(
            project=project,
            passages=passages,
            draft_mode="evidence_grounded",
            chat_model="gpt-5.6-terra",
            project_source_texts=[schedule.content],
            trace=[],
        )
    )

    construction = [
        item for item in output._cost_items if item.category == "Construction"
    ]
    assert len(construction) == 37
    assert sum((item.budget or Decimal("0")) for item in construction) == Decimal(
        "5870686.00"
    )
    assert construction[0].cost_code == "1.01"
    assert construction[0].item == "Preliminaries"
    assert all(item.source_refs for item in construction)
    assert any(item.budget is not None for item in construction)


def test_typed_cost_plan_rejects_an_unreconciled_contract_schedule() -> None:
    project = harrison_clarke_cost_project()
    content = CONTRACT_PRICE_SCHEDULE_FIXTURE.read_text(encoding="utf-8").replace(
        "5,870,686", "5,870,685"
    )
    schedule = evidence_passage(
        f"{project.slug}/_inbox/contract-price-schedule.pdf",
        content,
        project_slug=project.slug,
    ).model_copy(update={"project_id": project.id})

    with pytest.raises(WorkflowValidationError, match="could not reconcile"):
        run_async(
            run_create_cost_plan_typed(
                project=project,
                passages=[schedule, *platform_passages_for_cost_plan(project)],
                draft_mode="evidence_grounded",
                chat_model="gpt-5.6-terra",
                project_source_texts=[schedule.content],
                trace=[],
            )
        )


def test_typed_industrial_warehouse_cost_plan_smoke_excludes_residential_content() -> (
    None
):
    project = _warehouse_project()
    warehouse_pack = _warehouse_cost_pack()
    platform_paths = required_platform_paths(
        archetype=project.archetype or "",
        project=project,
    )
    platform_passages = [
        platform_passage(path, "doctrine" if path.startswith("docs/") else "reference")
        for path in platform_paths
    ]
    cost_passages = [
        evidence_passage(
            f"{project.slug}/00-brief-pmp/00-owner-project-brief-placeholder.md",
            "Owner project brief placeholder for Eastern Creek Distribution Centre.",
            project_slug=project.slug,
        )
    ]
    draft = mock_cost_plan_draft(
        project_id=project.id,
        workspace_path=f"{project.workspace_path}/01-cost/cost_plan_v01.md",
    )
    workbook_metadata = {
        "file_name": "Cost_Plan_v01.draft.xlsx",
        "workspace_path": f"{project.workspace_path}/01-cost/Cost_Plan_v01.draft.xlsx",
        "version": 1,
        "content_hash": "abc123",
        "size_bytes": 1234,
        "row_count": 9,
        "cost_item_lookup_count": 9,
        "warnings": [],
        "generated_at": "2026-07-01T00:00:00+00:00",
    }

    with (
        patch(
            "app.workflows.create_cost_plan.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.list_cost_evidence_paths",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.load_cost_project_evidence_documents",
            new=AsyncMock(return_value=cost_passages),
        ),
        patch(
            "app.workflows.create_cost_plan.load_platform_documents_by_paths",
            new=AsyncMock(return_value=(platform_passages, [])),
        ),
        patch(
            "app.sitewise.cost_plan_evidence.extract_cost_plan_evidence_pack",
            return_value=warehouse_pack,
        ),
        patch(
            "app.workflows.create_cost_plan._next_version_hint",
            new=AsyncMock(return_value=1),
        ),
        patch(
            "app.workflows.create_cost_plan.create_draft_artifact",
            new=AsyncMock(return_value=draft),
        ) as create_draft,
        patch(
            "app.workflows.create_cost_plan.import_legacy_draft",
            new=AsyncMock(return_value=_typed_import(draft)),
        ),
        patch(
            "app.workflows.create_cost_plan.sync_cost_plan_draft_workspace",
            new=AsyncMock(return_value=draft.workspace_path),
        ),
        patch(
            "app.workflows.create_cost_plan.save_cost_plan_workbook_artifact",
            new=AsyncMock(return_value=workbook_metadata),
        ),
    ):
        result = run_async(
            run_create_cost_plan_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=project,
                thread_id=None,
            )
        )

    assert result.status == "complete"
    markdown = create_draft.await_args.kwargs["content_markdown"]
    provenance = create_draft.await_args.kwargs["provenance_metadata"]
    assert provenance["compiler"] == "typed"
    lowered = markdown.lower()
    assert "kitchen" not in lowered
    assert "basix" not in lowered
    assert "structural steel" in lowered
    assert "dock hardstand" in lowered


def test_typed_cost_plan_publishes_progressive_row_batches_without_markdown_preview() -> (
    None
):
    project = harrison_clarke_cost_project()
    cost_passages = [
        passage.model_copy(update={"project_id": project.id})
        for passage in harrison_clarke_cost_passages(project_slug=project.slug)
    ]
    platform_passages = platform_passages_for_cost_plan(project)
    draft = mock_cost_plan_draft()
    published: list[dict] = []

    async def capture(preview: dict) -> None:
        published.append(preview)

    with (
        patch(
            "app.workflows.create_cost_plan.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.list_cost_evidence_paths",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_cost_plan.load_cost_project_evidence_documents",
            new=AsyncMock(return_value=cost_passages),
        ),
        patch(
            "app.workflows.create_cost_plan.load_platform_documents_by_paths",
            new=AsyncMock(return_value=(platform_passages, [])),
        ),
        patch(
            "app.workflows.create_cost_plan._next_version_hint",
            new=AsyncMock(return_value=1),
        ),
        patch(
            "app.workflows.create_cost_plan.create_draft_artifact",
            new=AsyncMock(return_value=draft),
        ),
        patch(
            "app.workflows.create_cost_plan.import_legacy_draft",
            new=AsyncMock(return_value=_typed_import(draft)),
        ),
        patch(
            "app.workflows.create_cost_plan.sync_cost_plan_draft_workspace",
            new=AsyncMock(return_value=draft.workspace_path),
        ),
        patch(
            "app.workflows.create_cost_plan.save_cost_plan_workbook_artifact",
            new=AsyncMock(
                return_value={
                    "file_name": "Cost_Plan_v01.draft.xlsx",
                    "workspace_path": (
                        "04-projects/test-project-112/01-cost/Cost_Plan_v01.draft.xlsx"
                    ),
                    "version": 1,
                    "content_hash": "abc123",
                    "size_bytes": 1234,
                    "row_count": 10,
                    "cost_item_lookup_count": 10,
                    "warnings": [],
                    "generated_at": "2026-06-08T00:00:00+00:00",
                }
            ),
        ),
    ):
        result = run_async(
            run_create_cost_plan_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=project,
                thread_id=None,
                on_preview=capture,
            )
        )

    assert result.status == "complete"
    assert not any(item.get("markdown") for item in published)
    typed_batches = [item for item in published if item.get("typed_cost_plan")]
    assert len(typed_batches) >= 2
    counts = [batch["typed_cost_plan"]["item_count"] for batch in typed_batches]
    assert counts == sorted(counts)
    assert counts[-1] > counts[0]
    first_items = typed_batches[0]["typed_cost_plan"]["items"]
    assert first_items[0]["cost_code"]
    assert "basis" in first_items[0]
