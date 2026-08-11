"""Integration tests for hybrid Create PMP (Harrison Clarke / Test Project 112)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.config import Settings
from app.projects.generation_brief import build_generation_brief
from app.projects.generation_context import (
    ContextField,
    FieldState,
    ProjectGenerationContext,
)
from app.sitewise.pmp_evidence_validation import (
    evidence_grounded_violations,
    sync_document_control_version,
)
from app.sitewise.pmp_greenfield_brief import greenfield_structure_violations
from app.sitewise.pmp_sources import required_section_headings
from app.workflows.create_pmp import (
    PmpDraftOutput,
    RUNTIME_HYBRID_NAME,
    RUNTIME_NAME,
    markdown_section_headings,
    validate_pmp_output,
    run_create_pmp_workflow,
)
from tests.conftest import run_async
from tests.workflows.hybrid_pmp_fixtures import (
    FIXTURE_DIR,
    USER_ID,
    harrison_clarke_mobilisation_passages,
    harrison_clarke_narrative,
    harrison_clarke_project,
    mock_draft_artifact,
    platform_passages_for_project,
)


@pytest.fixture(autouse=True)
def _no_locked_create_pmp_decisions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.workflows.create_pmp.locked_selections",
        AsyncMock(return_value={}),
    )


@pytest.fixture(autouse=True)
def _no_consultant_fact_reconcile(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tests pass bare AsyncMock sessions that don't model chained
    # session.execute(...).scalars().all() calls; skip the reconcile side
    # effect so those mocks don't have to.
    monkeypatch.setattr(
        "app.workflows.create_pmp._reconcile_consultant_facts_for_pmp",
        AsyncMock(return_value=0),
    )


def _harrison_clarke_source_texts() -> list[str]:
    return [
        (FIXTURE_DIR / "01-engagement-letter-harrison-clarke-studio.md").read_text(
            encoding="utf-8"
        ),
        (FIXTURE_DIR / "02-fee-proposal-harrison-clarke-studio.md").read_text(
            encoding="utf-8"
        ),
    ]


def _harrison_clarke_evidence_refs(project_slug: str) -> list[str]:
    return [
        f"project_evidence:{project_slug}/02-consultant/architect/"
        "01-engagement-letter-harrison-clarke-studio.md#chunk=abc",
        f"project_evidence:{project_slug}/02-consultant/architect/"
        "02-fee-proposal-harrison-clarke-studio.md#chunk=def",
    ]


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


def assert_hybrid_pmp_acceptance_criteria(markdown: str, *, project_slug: str) -> None:
    """PRD quality bar checks for Harrison Clarke hybrid output."""
    lower = markdown.lower()
    source_texts = _harrison_clarke_source_texts()
    evidence_refs = _harrison_clarke_evidence_refs(project_slug)

    expected_headings = [
        "Trace & QA" if heading == "Internal audit layer" else heading
        for heading in required_section_headings()
    ]
    assert markdown_section_headings(markdown) == expected_headings
    assert (
        evidence_grounded_violations(
            markdown,
            evidence_refs,
            source_texts=source_texts,
        )
        == []
    )
    assert (
        greenfield_structure_violations(
            markdown,
            archetype="new-dwelling",
        )
        == []
    )

    assert "michael and sarah chen" in lower
    assert "wattle grove" in lower
    assert "knockdown" in lower
    assert "16/05/2026" in lower
    assert "148,500" in lower
    assert "$22,000" in lower
    assert "qbe" in lower
    assert "cdc not assumed" in lower
    assert "september 2026" in lower
    assert "linden" in lower
    assert "invited builders: 3" in lower
    assert "pending owner formal sign-off" not in lower
    assert "- judgements:" in lower
    assert "| r-001 | master programme |" in lower
    assert "basix" in lower
    assert "executed" in lower


def test_pmp_hybrid_compiler_defaults_to_enabled() -> None:
    assert Settings.model_fields["pmp_hybrid_compiler"].default is True


def test_hybrid_harrison_clarke_integration_acceptance_criteria() -> None:
    project = harrison_clarke_project()
    mobilisation_passages = harrison_clarke_mobilisation_passages(
        project_slug=project.slug
    )
    platform_passages = platform_passages_for_project(project)
    draft = mock_draft_artifact()
    narrative = AsyncMock(return_value=harrison_clarke_narrative())

    with (
        patch(
            "app.workflows.create_pmp.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.load_mobilisation_project_evidence_documents",
            new=AsyncMock(return_value=mobilisation_passages),
        ),
        patch(
            "app.workflows.create_pmp.load_platform_documents_by_paths",
            new=AsyncMock(return_value=(platform_passages, [])),
        ),
        patch(
            "app.workflows.create_pmp.load_seed_knowledge",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    passages=[],
                    missing_required_refs=[],
                )
            ),
        ),
        patch(
            "app.workflows.pmp_narrative.run_pmp_narrative_model",
            new=narrative,
        ),
        patch(
            "app.workflows.create_pmp.build_generation_brief",
            wraps=build_generation_brief,
        ) as build_brief,
        patch(
            "app.workflows.create_pmp._next_version_hint",
            new=AsyncMock(return_value=1),
        ),
        patch(
            "app.workflows.create_pmp.create_draft_artifact",
            new=AsyncMock(return_value=draft),
        ) as create_draft,
    ):
        result = run_async(
            run_create_pmp_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=project,
                thread_id=None,
                generation_context=_generation_context(project.id),
            )
        )

    assert result.status == "complete", result.message
    markdown = create_draft.await_args.kwargs["content_markdown"]
    synced = sync_document_control_version(markdown, 1)
    assert "Version v01" in synced
    assert_hybrid_pmp_acceptance_criteria(synced, project_slug=project.slug)

    validate_pmp_output(
        PmpDraftOutput(
            title="Project Management Plan",
            markdown=synced,
            seed_consulted=[
                p.relative_path
                for p in platform_passages
                if p.source_type == "reference"
            ],
            evidence_refs=_harrison_clarke_evidence_refs(project.slug),
            context_refs=[
                f"{p.source_type}:{p.relative_path}#chunk={p.chunk_id}"
                for p in platform_passages
            ],
        ),
        "evidence_grounded",
        archetype="new-dwelling",
        source_texts=_harrison_clarke_source_texts(),
    )

    provenance = create_draft.await_args.kwargs["provenance_metadata"]
    assert provenance["compiler"] == "hybrid"
    generated_brief = narrative.await_args.kwargs["generation_brief"]
    assert build_brief.call_count == 1
    assert provenance["generation_brief"] == generated_brief.model_dump(mode="json")
    assert (
        provenance["generation_manifest"]["input_fingerprint"]
        == generated_brief.input_fingerprint
    )
    assert provenance["generation_manifest"][
        "generation_brief"
    ] == generated_brief.model_dump(mode="json")
    assert create_draft.await_args.kwargs["runtime"] == RUNTIME_HYBRID_NAME
    steps = {event.step for event in result.trace}
    assert {"extract", "scaffold", "narrative", "assemble", "validation"}.issubset(
        steps
    )


def test_legacy_create_pmp_path_when_hybrid_compiler_disabled() -> None:
    from tests.workflows.test_create_pmp import _valid_evidence_grounded_pmp_markdown

    project = harrison_clarke_project()
    platform_passages = platform_passages_for_project(project)
    legacy_output = PmpDraftOutput(
        title="Project Management Plan",
        markdown=_valid_evidence_grounded_pmp_markdown(),
        seed_consulted=[
            p.relative_path for p in platform_passages if p.source_type == "reference"
        ],
        evidence_refs=_harrison_clarke_evidence_refs(project.slug),
        context_refs=[
            f"{p.source_type}:{p.relative_path}#chunk={p.chunk_id}"
            for p in platform_passages
        ],
    )
    draft = mock_draft_artifact(runtime=RUNTIME_NAME)

    with (
        patch("app.workflows.create_pmp.settings.pmp_hybrid_compiler", False),
        patch(
            "app.workflows.create_pmp.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.load_mobilisation_project_evidence_documents",
            new=AsyncMock(
                return_value=harrison_clarke_mobilisation_passages(
                    project_slug=project.slug
                )
            ),
        ),
        patch(
            "app.workflows.create_pmp.load_platform_documents_by_paths",
            new=AsyncMock(return_value=(platform_passages_for_project(project), [])),
        ),
        patch(
            "app.workflows.create_pmp.run_create_pmp_model",
            new=AsyncMock(return_value=legacy_output),
        ) as run_legacy_model,
        patch(
            "app.workflows.pmp_narrative.run_pmp_narrative_model",
            new=AsyncMock(),
        ) as run_narrative,
        patch(
            "app.workflows.create_pmp._next_version_hint",
            new=AsyncMock(return_value=1),
        ),
        patch(
            "app.workflows.create_pmp.create_draft_artifact",
            new=AsyncMock(return_value=draft),
        ) as create_draft,
    ):
        result = run_async(
            run_create_pmp_workflow(
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


def _run_hybrid_with_preview(on_preview, narrative_hook=None):
    """Run the hybrid Create PMP path, capturing previews it publishes."""
    project = harrison_clarke_project()
    mobilisation_passages = harrison_clarke_mobilisation_passages(
        project_slug=project.slug
    )
    platform_passages = platform_passages_for_project(project)

    async def narrative(**kwargs):
        if narrative_hook is not None:
            narrative_hook()
        return harrison_clarke_narrative()

    with (
        patch(
            "app.workflows.create_pmp.DocumentRetriever.retrieve",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.create_pmp.load_mobilisation_project_evidence_documents",
            new=AsyncMock(return_value=mobilisation_passages),
        ),
        patch(
            "app.workflows.create_pmp.load_platform_documents_by_paths",
            new=AsyncMock(return_value=(platform_passages, [])),
        ),
        patch("app.workflows.pmp_narrative.run_pmp_narrative_model", new=narrative),
        patch(
            "app.workflows.create_pmp._next_version_hint",
            new=AsyncMock(return_value=1),
        ),
        patch(
            "app.workflows.create_pmp.create_draft_artifact",
            new=AsyncMock(return_value=mock_draft_artifact()),
        ),
    ):
        return run_async(
            run_create_pmp_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=project,
                thread_id=None,
                on_preview=on_preview,
            )
        )


def test_hybrid_publishes_the_scaffold_before_the_narrative_model_runs() -> None:
    published: list[dict] = []
    previews_at_narrative_time: list[int] = []

    async def capture(preview: dict) -> None:
        published.append(preview)

    result = _run_hybrid_with_preview(
        capture,
        narrative_hook=lambda: previews_at_narrative_time.append(len(published)),
    )

    assert result.status == "complete"
    # The scaffold reaches the user before the multi-minute model call starts.
    assert previews_at_narrative_time[0] > 0
    scaffold = next(item for item in published if item.get("markdown"))
    assert scaffold["stage"] == "scaffold_ready"
    assert scaffold["markdown"].strip()


def test_hybrid_persists_consistency_ai_calls_from_rejected_attempts() -> None:
    from app.workflows.create_pmp import WorkflowValidationError

    attempts = 0

    def fail_first_attempt() -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise WorkflowValidationError(
                "PMP narrative consistency failed: duplicate scope",
                consistency_ai_call_count=1,
            )

    result = _run_hybrid_with_preview(None, narrative_hook=fail_first_attempt)

    assert result.status == "complete"
    assert attempts == 2
    retry_event = next(
        event
        for event in result.trace
        if event.step == "validation" and event.status == "retry"
    )
    assert retry_event.metadata["consistency_ai_call_count"] == 1
    narrative_event = next(event for event in result.trace if event.step == "narrative")
    assert narrative_event.metadata["consistency_ai_call_count"] == 1


def test_published_scaffold_carries_the_document_headings() -> None:
    published: list[dict] = []

    async def capture(preview: dict) -> None:
        published.append(preview)

    _run_hybrid_with_preview(capture)

    scaffold = next(item for item in published if item.get("markdown"))
    headings = markdown_section_headings(scaffold["markdown"])
    assert headings == list(required_section_headings())


def test_a_failing_preview_publisher_does_not_fail_the_run() -> None:
    async def explode(preview: dict) -> None:
        raise RuntimeError("preview channel is down")

    result = _run_hybrid_with_preview(explode)

    assert result.status == "complete"


def test_hybrid_runs_without_a_preview_publisher() -> None:
    result = _run_hybrid_with_preview(None)

    assert result.status == "complete"
