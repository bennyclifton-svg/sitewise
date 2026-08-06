"""Integration tests for hybrid Create Cost Plan (Harrison Clarke / Test Project 112)."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings
from app.cost_plan.import_legacy import parse_legacy_draft
from app.sitewise.cost_plan_evidence_validation import (
    cost_plan_evidence_grounded_violations,
)
from app.sitewise.cost_plan_sources import (
    required_platform_paths,
    required_section_headings,
)
from app.workflows.create_cost_plan import (
    RUNTIME_HYBRID_NAME,
    RUNTIME_NAME,
    run_create_cost_plan_hybrid,
    run_create_cost_plan_workflow,
    validate_cost_plan_output,
    CostPlanDraftOutput,
    WorkflowValidationError,
)
from tests.conftest import run_async
from tests.sitewise.test_cost_plan_evidence import FIXTURE_DIR
from tests.sitewise.test_cost_plan_renderer import _warehouse_cost_pack, _warehouse_project
from tests.workflows.hybrid_cost_plan_fixtures import (
    USER_ID,
    harrison_clarke_cost_narrative,
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


def _section_headings(markdown: str) -> list[str]:
    return [
        line.strip()[3:].strip()
        for line in markdown.splitlines()
        if line.strip().startswith("## ")
    ]


def assert_hybrid_cost_plan_acceptance_criteria(
    markdown: str, *, project_slug: str
) -> None:
    lower = markdown.lower()
    source_texts = _harrison_clarke_source_texts()
    evidence_refs = [
        f"project_evidence:{project_slug}/02-consultant/architect/"
        "01-engagement-letter-harrison-clarke-studio.md#chunk=0",
        f"project_evidence:{project_slug}/00-brief-pmp/"
        "03-owner-project-brief-chen-residence.md#chunk=0",
    ]

    assert _section_headings(markdown) == list(
        required_section_headings()
    )
    assert (
        cost_plan_evidence_grounded_violations(
            markdown,
            evidence_refs,
            source_texts=source_texts,
        )
        == []
    )

    assert "1,850,000" in markdown
    assert "120,000" in markdown
    assert "148,500" in markdown
    assert "wattle grove" in lower
    assert "michael and sarah chen" in lower
    assert "da + cc" in lower
    assert "geotechnical investigation report on file" in lower
    assert "master programme on file" in lower
    assert "principal certifier appointed" in lower
    assert "1,500,000" not in markdown
    assert "feasibility study" not in lower
    assert "- **assumptions**" in lower
    assert "| cost code | category | cost items | budget | status | basis |" in lower


def test_cost_plan_hybrid_compiler_defaults_to_enabled() -> None:
    assert Settings.model_fields["cost_plan_hybrid_compiler"].default is True


def test_hybrid_harrison_clarke_cost_plan_integration() -> None:
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
            "app.workflows.create_cost_plan.locked_selections",
            new=AsyncMock(return_value={}),
        ),
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
            "app.workflows.cost_plan_narrative.run_cost_plan_narrative_model",
            new=AsyncMock(return_value=harrison_clarke_cost_narrative()),
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
    assert_hybrid_cost_plan_acceptance_criteria(markdown, project_slug=project.slug)

    validate_cost_plan_output(
        CostPlanDraftOutput(
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
        ),
        "evidence_grounded",
        archetype="new-dwelling",        source_texts=_harrison_clarke_source_texts(),
    )

    provenance = create_draft.await_args.kwargs["provenance_metadata"]
    assert provenance["compiler"] == "hybrid"
    assert create_draft.await_args.kwargs["runtime"] == RUNTIME_HYBRID_NAME
    steps = {event.step for event in result.trace}
    assert {"extract", "scaffold", "narrative", "assemble", "validation"}.issubset(
        steps
    )


def test_hybrid_create_cost_plan_maps_received_main_works_proposal_to_typed_rows() -> None:
    """A structured fixed-price proposal must price a newly created Cost Plan."""
    project = harrison_clarke_cost_project()
    passages = [
        *_kavanagh_cost_passages(project),
        *platform_passages_for_cost_plan(project),
    ]

    with patch(
        "app.workflows.cost_plan_narrative.run_cost_plan_narrative_model",
        new=AsyncMock(return_value=harrison_clarke_cost_narrative()),
    ):
        output = run_async(
            run_create_cost_plan_hybrid(
                project=project,
                passages=passages,
                draft_mode="evidence_grounded",
                chat_model="gpt-5.6-terra",
                project_source_texts=[passage.content for passage in passages[:5]],
                trace=[],
            )
        )

    assert "$1,234,000" in output.markdown
    assert "$298,000" in output.markdown
    assert "$96,000" in output.markdown
    assert "$41,800" in output.markdown
    assert "$32,500" in output.markdown
    assert "$45,000" in output.markdown

    draft = mock_cost_plan_draft()
    draft.content_markdown = output.markdown
    typed = parse_legacy_draft(draft)
    assert typed.parsed_budget_total == Decimal("1449300")
    assert any(
        item.item == "Preliminaries" and item.budget == Decimal("136000")
        for item in typed.items
    )


def test_hybrid_cost_plan_adopts_contract_schedule_as_typed_construction_rows() -> None:
    project = harrison_clarke_cost_project()
    schedule = evidence_passage(
        f"{project.slug}/_inbox/ANX V CONTACT PRICE SCHEDULE [B].pdf",
        CONTRACT_PRICE_SCHEDULE_FIXTURE.read_text(encoding="utf-8"),
        project_slug=project.slug,
    ).model_copy(update={"project_id": project.id})
    passages = [schedule, *platform_passages_for_cost_plan(project)]

    with patch(
        "app.workflows.cost_plan_narrative.run_cost_plan_narrative_model",
        new=AsyncMock(return_value=harrison_clarke_cost_narrative()),
    ):
        output = run_async(
            run_create_cost_plan_hybrid(
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
    assert "5,870,686" in output.markdown


def test_hybrid_cost_plan_rejects_an_unreconciled_contract_schedule() -> None:
    project = harrison_clarke_cost_project()
    content = CONTRACT_PRICE_SCHEDULE_FIXTURE.read_text(encoding="utf-8").replace(
        "5,870,686", "5,870,685"
    )
    schedule = evidence_passage(
        f"{project.slug}/_inbox/contract-price-schedule.pdf",
        content,
        project_slug=project.slug,
    ).model_copy(update={"project_id": project.id})
    narrative = AsyncMock(return_value=harrison_clarke_cost_narrative())

    with (
        patch(
            "app.workflows.cost_plan_narrative.run_cost_plan_narrative_model",
            new=narrative,
        ),
        pytest.raises(WorkflowValidationError, match="could not reconcile"),
    ):
        run_async(
            run_create_cost_plan_hybrid(
                project=project,
                passages=[schedule, *platform_passages_for_cost_plan(project)],
                draft_mode="evidence_grounded",
                chat_model="gpt-5.6-terra",
                project_source_texts=[schedule.content],
                trace=[],
            )
        )

    narrative.assert_not_awaited()


def test_legacy_create_cost_plan_when_hybrid_compiler_disabled() -> None:
    from app.sitewise.cost_plan_evidence import extract_cost_plan_evidence_pack
    from app.sitewise.cost_plan_renderer import render_cost_plan_scaffold

    project = harrison_clarke_cost_project()
    platform_passages = platform_passages_for_cost_plan(project)
    evidence_refs = [
        f"project_evidence:{project.slug}/02-consultant/architect/"
        "01-engagement-letter-harrison-clarke-studio.md#chunk=0",
        f"project_evidence:{project.slug}/00-brief-pmp/"
        "03-owner-project-brief-chen-residence.md#chunk=0",
    ]
    legacy_markdown = render_cost_plan_scaffold(
        project,
        extract_cost_plan_evidence_pack(_harrison_clarke_source_texts(), evidence_refs),
        "evidence_grounded",
    )
    legacy_output = CostPlanDraftOutput(
        title="Project Cost Plan",
        markdown=legacy_markdown,
        seed_consulted=[
            p.relative_path for p in platform_passages if p.source_type == "reference"
        ],
        evidence_refs=evidence_refs,
        context_refs=[
            f"{p.source_type}:{p.relative_path}#chunk=0" for p in platform_passages
        ],
    )
    draft = mock_cost_plan_draft(runtime=RUNTIME_NAME)
    workbook_metadata = {
        "file_name": "Cost_Plan_v01.draft.xlsx",
        "workspace_path": "04-projects/test-project-112/01-cost/Cost_Plan_v01.draft.xlsx",
        "version": 1,
        "content_hash": "abc123",
        "size_bytes": 1234,
        "row_count": 8,
        "cost_item_lookup_count": 8,
        "warnings": [],
        "generated_at": "2026-06-08T00:00:00+00:00",
    }

    with (
        patch(
            "app.workflows.create_cost_plan.locked_selections",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "app.workflows.create_cost_plan.settings.cost_plan_hybrid_compiler", False
        ),
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
            new=AsyncMock(
                return_value=harrison_clarke_cost_passages(project_slug=project.slug)
            ),
        ),
        patch(
            "app.workflows.create_cost_plan.load_platform_documents_by_paths",
            new=AsyncMock(return_value=(platform_passages, [])),
        ),
        patch(
            "app.workflows.create_cost_plan.run_create_cost_plan_model",
            new=AsyncMock(return_value=legacy_output),
        ) as run_legacy_model,
        patch(
            "app.workflows.cost_plan_narrative.run_cost_plan_narrative_model",
            new=AsyncMock(),
        ) as run_narrative,
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
    run_legacy_model.assert_awaited_once()
    run_narrative.assert_not_called()
    assert create_draft.await_args.kwargs["provenance_metadata"]["compiler"] == "legacy"
    assert create_draft.await_args.kwargs["runtime"] == RUNTIME_NAME
    assert "model" in {event.step for event in result.trace}


def test_hybrid_cost_plan_retries_on_narrative_validation_failure() -> None:
    from app.workflows.create_pmp import WorkflowValidationError

    project = harrison_clarke_cost_project()
    cost_passages = harrison_clarke_cost_passages(project_slug=project.slug)
    platform_passages = platform_passages_for_cost_plan(project)
    draft = mock_cost_plan_draft()
    narrative = harrison_clarke_cost_narrative()
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
    narrative_mock = AsyncMock(
        side_effect=[
            WorkflowValidationError(
                "Cost plan narrative validation failed: "
                "next_steps item 3 must include an ISO due date (YYYY-MM-DD)"
            ),
            narrative,
        ]
    )

    with (
        patch(
            "app.workflows.create_cost_plan.locked_selections",
            new=AsyncMock(return_value={}),
        ),
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
            "app.workflows.cost_plan_narrative.run_cost_plan_narrative_model",
            new=narrative_mock,
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
    assert narrative_mock.await_count == 2
    retry_events = [
        event
        for event in result.trace
        if event.step == "validation" and event.status == "retry"
    ]
    assert len(retry_events) == 1
    assert "next_steps item 3" in retry_events[0].message


def test_hybrid_industrial_warehouse_cost_plan_smoke_excludes_residential_content() -> None:
    """Segment 4 smoke: an NSW industrial warehouse hybrid run must never leak
    residential-only kitchen/BASIX taxonomy into the assembled Cost Plan.

    Reuses the deterministic warehouse evidence pack from
    tests/sitewise/test_cost_plan_renderer.py (already exercised at the scaffold
    level) instead of building a second warehouse markdown-fixture corpus, since
    extract_cost_plan_evidence_pack is regex-driven off Chen-Residence-shaped
    prose and duplicating that fixture infrastructure for one smoke test isn't
    worth it.
    """
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
            "app.workflows.create_cost_plan.locked_selections",
            new=AsyncMock(return_value={}),
        ),
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
            "app.workflows.cost_plan_narrative.run_cost_plan_narrative_model",
            new=AsyncMock(return_value=harrison_clarke_cost_narrative()),
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
    assert provenance["compiler"] == "hybrid"
    lowered = markdown.lower()
    assert "kitchen" not in lowered
    assert "basix" not in lowered
    assert "structural steel" in lowered
    assert "dock hardstand" in lowered


def test_hybrid_cost_plan_publishes_the_scaffold_before_the_narrative_model() -> None:
    project = harrison_clarke_cost_project()
    cost_passages = [
        passage.model_copy(update={"project_id": project.id})
        for passage in harrison_clarke_cost_passages(project_slug=project.slug)
    ]
    platform_passages = platform_passages_for_cost_plan(project)
    draft = mock_cost_plan_draft()
    published: list[dict] = []
    previews_at_narrative_time: list[int] = []

    async def capture(preview: dict) -> None:
        published.append(preview)

    async def narrative(**kwargs):
        previews_at_narrative_time.append(len(published))
        return harrison_clarke_cost_narrative()

    with (
        patch(
            "app.workflows.create_cost_plan.locked_selections",
            new=AsyncMock(return_value={}),
        ),
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
        patch("app.workflows.cost_plan_narrative.run_cost_plan_narrative_model", new=narrative),
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
    assert previews_at_narrative_time == [1]
    assert published[0]["stage"] == "scaffold"
    assert published[0]["markdown"].strip()
