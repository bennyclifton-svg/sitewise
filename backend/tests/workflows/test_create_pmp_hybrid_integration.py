"""Integration tests for hybrid Create PMP (Harrison Clarke / Test Project 112)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.config import Settings
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


def _harrison_clarke_source_texts() -> list[str]:
    return [
        (FIXTURE_DIR / "01-engagement-letter-harrison-clarke-studio.md").read_text(
            encoding="utf-8"
        ),
        (FIXTURE_DIR / "02-fee-proposal-harrison-clarke-studio.md").read_text(encoding="utf-8"),
    ]


def _harrison_clarke_evidence_refs(project_slug: str) -> list[str]:
    return [
        f"project_evidence:{project_slug}/02-consultant/architect/"
        "01-engagement-letter-harrison-clarke-studio.md#chunk=abc",
        f"project_evidence:{project_slug}/02-consultant/architect/"
        "02-fee-proposal-harrison-clarke-studio.md#chunk=def",
    ]


def assert_hybrid_pmp_acceptance_criteria(markdown: str, *, project_slug: str) -> None:
    """PRD quality bar checks for Harrison Clarke hybrid output."""
    lower = markdown.lower()
    source_texts = _harrison_clarke_source_texts()
    evidence_refs = _harrison_clarke_evidence_refs(project_slug)

    assert markdown_section_headings(markdown) == list(required_section_headings("architect-pm"))
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
            user_role="architect-pm",
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
    assert "pending owner formal sign-off" in lower
    assert "- **judgements**" in lower
    assert "| r-001 | master programme |" in lower
    assert "basix" in lower
    assert "executed" in lower


def test_pmp_hybrid_compiler_defaults_to_enabled() -> None:
    assert Settings.model_fields["pmp_hybrid_compiler"].default is True


def test_hybrid_harrison_clarke_integration_acceptance_criteria() -> None:
    project = harrison_clarke_project()
    mobilisation_passages = harrison_clarke_mobilisation_passages(project_slug=project.slug)
    platform_passages = platform_passages_for_project(project)
    draft = mock_draft_artifact()

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
            "app.workflows.pmp_narrative.run_pmp_narrative_model",
            new=AsyncMock(return_value=harrison_clarke_narrative()),
        ),
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
    markdown = create_draft.await_args.kwargs["content_markdown"]
    synced = sync_document_control_version(markdown, 1)
    assert "Version v01" in synced
    assert_hybrid_pmp_acceptance_criteria(synced, project_slug=project.slug)

    validate_pmp_output(
        PmpDraftOutput(
            title="Project Management Plan",
            markdown=synced,
            seed_consulted=[p.relative_path for p in platform_passages if p.source_type == "reference"],
            evidence_refs=_harrison_clarke_evidence_refs(project.slug),
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


def test_legacy_create_pmp_path_when_hybrid_compiler_disabled() -> None:
    from tests.workflows.test_create_pmp import _valid_evidence_grounded_pmp_markdown

    project = harrison_clarke_project()
    platform_passages = platform_passages_for_project(project)
    legacy_output = PmpDraftOutput(
        title="Project Management Plan",
        markdown=_valid_evidence_grounded_pmp_markdown(),
        seed_consulted=[p.relative_path for p in platform_passages if p.source_type == "reference"],
        evidence_refs=_harrison_clarke_evidence_refs(project.slug),
        context_refs=[f"{p.source_type}:{p.relative_path}#chunk={p.chunk_id}" for p in platform_passages],
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
            new=AsyncMock(return_value=harrison_clarke_mobilisation_passages(project_slug=project.slug)),
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
