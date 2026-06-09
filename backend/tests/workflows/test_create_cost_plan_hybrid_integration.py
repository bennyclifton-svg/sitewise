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
    from tests.workflows.test_create_cost_plan import _valid_evidence_grounded_cost_plan_markdown

    project = harrison_clarke_cost_project()
    platform_passages = platform_passages_for_cost_plan(project)
    legacy_output = CostPlanDraftOutput(
        title="Project Cost Plan",
        markdown=_valid_evidence_grounded_cost_plan_markdown(),
        seed_consulted=[p.relative_path for p in platform_passages if p.source_type == "reference"],
        evidence_refs=["project_evidence:demo/01-cost/budget.md#chunk=0"],
        context_refs=[f"{p.source_type}:{p.relative_path}#chunk=0" for p in platform_passages],
    )
    draft = mock_cost_plan_draft(runtime=RUNTIME_NAME)

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
