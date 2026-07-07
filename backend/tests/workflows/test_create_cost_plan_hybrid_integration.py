"""Integration tests for hybrid Create Cost Plan (Harrison Clarke / Test Project 112)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.config import Settings
from app.sitewise.cost_plan_evidence_validation import cost_plan_evidence_grounded_violations
from app.sitewise.cost_plan_sources import required_section_headings
from app.workflows.create_cost_plan import (
    RUNTIME_HYBRID_NAME,
    RUNTIME_NAME,
    run_create_cost_plan_workflow,
    validate_cost_plan_output,
    CostPlanDraftOutput,
)
from tests.conftest import run_async
from tests.sitewise.test_cost_plan_evidence import FIXTURE_DIR
from tests.workflows.hybrid_cost_plan_fixtures import (
    USER_ID,
    harrison_clarke_cost_narrative,
    harrison_clarke_cost_passages,
    harrison_clarke_cost_project,
    mock_cost_plan_draft,
    platform_passages_for_cost_plan,
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


def _section_headings(markdown: str) -> list[str]:
    return [
        line.strip()[3:].strip()
        for line in markdown.splitlines()
        if line.strip().startswith("## ")
    ]


def assert_hybrid_cost_plan_acceptance_criteria(markdown: str, *, project_slug: str) -> None:
    lower = markdown.lower()
    source_texts = _harrison_clarke_source_texts()
    evidence_refs = [
        f"project_evidence:{project_slug}/02-consultant/architect/"
        "01-engagement-letter-harrison-clarke-studio.md#chunk=0",
        f"project_evidence:{project_slug}/00-brief-pmp/"
        "03-owner-project-brief-chen-residence.md#chunk=0",
    ]

    assert _section_headings(markdown) == list(required_section_headings("architect-pm"))
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
    assert "- **judgements**" in lower
    assert "| cost code | category | cost items | budget | status | basis |" in lower


def test_cost_plan_hybrid_compiler_defaults_to_enabled() -> None:
    assert Settings.model_fields["cost_plan_hybrid_compiler"].default is True


def test_hybrid_harrison_clarke_cost_plan_integration() -> None:
    project = harrison_clarke_cost_project()
    cost_passages = harrison_clarke_cost_passages(project_slug=project.slug)
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
            seed_consulted=[p.relative_path for p in platform_passages if p.source_type == "reference"],
            evidence_refs=[f"project_evidence:{p.relative_path}#chunk=0" for p in cost_passages],
            context_refs=[
                f"{p.source_type}:{p.relative_path}#chunk={p.chunk_id}" for p in platform_passages
            ],
        ),
        "evidence_grounded",
        archetype="new-dwelling",
        user_role="architect-pm",
        source_texts=_harrison_clarke_source_texts(),
    )

    provenance = create_draft.await_args.kwargs["provenance_metadata"]
    assert provenance["compiler"] == "hybrid"
    assert create_draft.await_args.kwargs["runtime"] == RUNTIME_HYBRID_NAME
    steps = {event.step for event in result.trace}
    assert {"extract", "scaffold", "narrative", "assemble", "validation"}.issubset(steps)


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
        seed_consulted=[p.relative_path for p in platform_passages if p.source_type == "reference"],
        evidence_refs=evidence_refs,
        context_refs=[f"{p.source_type}:{p.relative_path}#chunk=0" for p in platform_passages],
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
        patch("app.workflows.create_cost_plan.settings.cost_plan_hybrid_compiler", False),
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
            new=AsyncMock(return_value=harrison_clarke_cost_passages(project_slug=project.slug)),
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
        event for event in result.trace if event.step == "validation" and event.status == "retry"
    ]
    assert len(retry_events) == 1
    assert "next_steps item 3" in retry_events[0].message
