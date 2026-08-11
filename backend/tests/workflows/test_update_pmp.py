import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.sitewise.gate import overlay_status
from app.workflows.create_pmp import PmpDraftOutput, markdown_section_headings
from app.workflows import update_pmp as workflow
from app.workflows.update_pmp import run_update_pmp_workflow, validate_update_pmp_output
from app.schemas.projects import WorkflowTraceEvent
from tests.conftest import run_async
from tests.workflows.test_create_pmp import (
    _valid_evidence_grounded_pmp_markdown,
    _valid_pmp_markdown,
    _valid_seed_consulted,
)

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
BASELINE_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture(autouse=True)
def _no_consultant_fact_reconcile(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tests pass bare AsyncMock sessions that don't model chained
    # session.execute(...).scalars().all() calls; skip the reconcile side
    # effect so those mocks don't have to.
    monkeypatch.setattr(
        "app.workflows.update_pmp._reconcile_consultant_facts_for_pmp",
        AsyncMock(return_value=0),
    )


def _project(**overrides) -> Project:
    values = {
        "id": PROJECT_ID,
        "owner_user_id": USER_ID,
        "slug": "test-project",
        "title": "Test Project",
        "workspace_path": "04-projects/test-project",
        "phase": "brief-planning",
        "archetype": "new-dwelling",
        "user_role": "architect-pm",
        "state": "NSW",
        "status": "active",
        "project_metadata": None,
        "created_at": datetime(2026, 6, 7, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 6, 7, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return Project(**values)


def _baseline_draft() -> DraftArtifact:
    return DraftArtifact(
        id=BASELINE_ID,
        project_id=PROJECT_ID,
        workflow_type="create_pmp",
        version=1,
        status="draft",
        title="Project Management Plan",
        workspace_path="04-projects/test-project/00-brief-pmp/PMP.md",
        author_user_id=USER_ID,
        content_markdown=_valid_pmp_markdown(),
        model="gpt-5.6-terra",
        runtime="clerk-sitewise-create-pmp",
        provenance_metadata={},
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )


def test_validate_update_pmp_output_preserves_baseline_headings() -> None:
    baseline = _valid_pmp_markdown()
    output = PmpDraftOutput(
        title="Project Management Plan",
        markdown=(
            "## Project overview\n\n"
            + "Updated only. " * 30
        ),
        seed_consulted=_valid_seed_consulted(),
        evidence_refs=["project_evidence:test/brief.md"],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    full_seeds = _valid_seed_consulted() + ["seed/new-dwelling-guide.md", "seed/role-architect-pm.md"]
    output.seed_consulted = full_seeds
    try:
        validate_update_pmp_output(
            output,
            baseline_markdown=baseline,
            archetype="new-dwelling",            has_evidence_delta=True,
        )
    except Exception as exc:
        assert "removed baseline sections" in str(exc)
    else:
        raise AssertionError("Expected validation to fail when baseline headings removed")


def test_validate_update_pmp_output_rejects_evidence_contradictions() -> None:
    baseline = _valid_evidence_grounded_pmp_markdown()
    full_seeds = _valid_seed_consulted() + ["seed/new-dwelling-guide.md"]
    output = PmpDraftOutput(
        title="Project Management Plan",
        markdown=baseline.replace(
            "Evidence on file:",
            "Source hierarchy: project evidence (none yet). Evidence on file:",
        ),
        seed_consulted=full_seeds,
        evidence_refs=[
            "project_evidence:test/02-consultant/architect/"
            "01-engagement-letter-harrison-clarke-studio.md#chunk=abc",
        ],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    try:
        validate_update_pmp_output(
            output,
            baseline_markdown=baseline,
            archetype="new-dwelling",            has_evidence_delta=True,
        )
    except Exception as exc:
        assert "evidence_grounded fidelity" in str(exc)
    else:
        raise AssertionError("Expected validation to fail for evidence contradictions")


def test_validate_update_pmp_output_accepts_valid_output_without_coverage_refs() -> None:
    baseline = _valid_evidence_grounded_pmp_markdown()
    full_seeds = _valid_seed_consulted() + ["seed/new-dwelling-guide.md"]
    output = PmpDraftOutput(
        title="Project Management Plan",
        markdown=baseline,
        seed_consulted=full_seeds,
        evidence_refs=[
            "project_evidence:test/02-consultant/architect/"
            "01-engagement-letter-harrison-clarke-studio.md#chunk=abc",
        ],
        context_refs=["doctrine:docs/clerk-brief.md"],
    )
    validate_update_pmp_output(
        output,
        baseline_markdown=baseline,
        archetype="new-dwelling",        has_evidence_delta=True,
    )


def test_markdown_section_headings_extracts_custom_sections() -> None:
    markdown = "## Project overview\n\n## Custom client section\n\nBody\n"
    assert markdown_section_headings(markdown) == [
        "Project overview",
        "Custom client section",
    ]


def test_update_pmp_emits_lifecycle_progress_events() -> None:
    published: list[dict] = []
    baseline = _baseline_draft()
    baseline.content_markdown = _valid_evidence_grounded_pmp_markdown()

    async def capture(progress: dict) -> None:
        published.append(progress)

    with (
        patch(
            "app.workflows.update_pmp.overlay_status",
            return_value=overlay_status(
                archetype="new-dwelling",
                state="NSW",
            ),
        ),
        patch(
            "app.workflows.update_pmp.locked_selections",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "app.workflows.update_pmp.get_latest_draft_artifact",
            new=AsyncMock(return_value=baseline),
        ),
        patch(
            "app.workflows.update_pmp.retrieve_create_pmp_sources",
            new=AsyncMock(return_value=([], 0, 0, "platform_seeded", [])),
        ),
        patch(
            "app.workflows.update_pmp.retrieve_generation_evidence",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    category=lambda key: []  # noqa: ARG005
                )
            ),
        ),
        patch(
            "app.workflows.update_pmp.project_has_taxonomy",
            return_value=False,
        ),
        patch(
            "app.workflows.create_pmp.retrieve_project_evidence_delta",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.workflows.update_pmp.run_update_pmp_model",
            new=AsyncMock(
                return_value=PmpDraftOutput(
                    title="Project Management Plan",
                    markdown=baseline.content_markdown,
                    seed_consulted=_valid_seed_consulted(),
                    evidence_refs=[],
                    context_refs=[],
                )
            ),
        ),
        patch(
            "app.workflows.update_pmp.validate_update_pmp_output",
            return_value=None,
        ),
        patch(
            "app.workflows.update_pmp.create_draft_artifact",
            new=AsyncMock(return_value=baseline),
        ),
        patch("app.workflows.update_pmp.sync_decisions_from_markdown", new=AsyncMock()),
        patch("app.workflows.update_pmp._persist_trace_message", new=AsyncMock()),
        patch(
            "app.workflows.create_pmp._next_version_hint",
            new=AsyncMock(return_value=2),
        ),
        patch(
            "app.workflows.create_pmp.sync_pmp_draft_workspace",
            new=AsyncMock(return_value="path"),
        ),
        patch(
            "app.workflows.update_pmp.apply_document_refresh",
            side_effect=lambda baseline_md, _meta, regenerated, **_kwargs: SimpleNamespace(
                markdown=regenerated,
                metadata={},
                updated=(),
                preserved=(),
                conflicts=(),
            ),
        ),
    ):
        result = run_async(
            run_update_pmp_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=_project(),
                thread_id=None,
                on_preview=capture,
            )
        )

    assert result.status == "complete"
    stages = [item.get("stage") for item in published]
    assert "context_ready" in stages
    assert "retrieval_complete" in stages
    assert "section_started" in stages
    assert "validation_started" in stages
    assert "artefact_ready" in stages
    scaffold = next(item for item in published if item.get("markdown"))
    assert scaffold["markdown"].strip()


def test_update_pmp_skips_retrieval_and_model_when_inputs_unchanged() -> None:
    from app.projects.selective_refresh import compute_refresh_input_hash
    from app.sitewise.seed_routing import select_seed_knowledge_for_project

    baseline = _baseline_draft()
    seed_version = (
        "|".join(select_seed_knowledge_for_project("pmp", _project()).applicable_paths)
        or "no-seed-guidance"
    )
    refresh_hash = compute_refresh_input_hash(
        context_version=1,
        source_version="no-project-evidence",
        seed_version=seed_version,
        artefact_type="pmp",
    )
    baseline.provenance_metadata = {
        "incremental_update": {"input_hash": refresh_hash},
    }
    retrieve = AsyncMock(side_effect=AssertionError("retrieval must be skipped"))
    model = AsyncMock(side_effect=AssertionError("model must be skipped"))

    with (
        patch(
            "app.workflows.update_pmp.overlay_status",
            return_value=overlay_status(archetype="new-dwelling", state="NSW"),
        ),
        patch(
            "app.workflows.update_pmp.locked_selections",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "app.workflows.update_pmp.get_latest_draft_artifact",
            new=AsyncMock(return_value=baseline),
        ),
        patch("app.workflows.update_pmp.retrieve_create_pmp_sources", new=retrieve),
        patch("app.workflows.update_pmp.run_update_pmp_model", new=model),
        patch("app.workflows.update_pmp._persist_trace_message", new=AsyncMock()),
    ):
        result = run_async(
            run_update_pmp_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=_project(project_context_version=1),
                thread_id=None,
            )
        )

    assert result.status == "complete"
    assert result.draft is not None
    assert result.draft.version == baseline.version
    assert any(event.step == "selective_refresh" for event in result.trace)
    retrieve.assert_not_awaited()
    model.assert_not_awaited()


def test_update_pmp_fails_without_baseline() -> None:
    with (
        patch(
            "app.workflows.update_pmp.overlay_status",
            return_value=overlay_status(
                archetype="new-dwelling",                state="NSW",
            ),
        ),
        patch(
            "app.workflows.update_pmp.locked_selections",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "app.workflows.update_pmp.get_latest_draft_artifact",
            new=AsyncMock(return_value=None),
        ),
    ):
        result = run_async(
            run_update_pmp_workflow(
                AsyncMock(),
                user_id=USER_ID,
                project=_project(),
                thread_id=None,
            )
        )
    assert result.status == "failed"
    assert "Create PMP first" in (result.message or "")


def test_update_pmp_trace_persists_project_activity_without_thread() -> None:
    session = AsyncMock()
    trace = [
        WorkflowTraceEvent(
            step="validation",
            status="passed",
            message="Update PMP output passed validation.",
            metadata={},
        )
    ]
    run_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    with (
        patch("app.workflows.update_pmp.record_activity_events", new=AsyncMock()) as record,
        patch("app.workflows.update_pmp.create_message", new=AsyncMock()) as create_message,
    ):
        run_async(
            workflow._persist_trace_message(
                session,
                project_id=PROJECT_ID,
                run_id=run_id,
                thread_id=None,
                content="Update PMP completed.",
                trace=trace,
                status="complete",
                draft_id=BASELINE_ID,
            )
        )

    record.assert_awaited_once_with(
        session,
        project_id=PROJECT_ID,
        source=workflow.UPDATE_WORKFLOW_TYPE,
        run_id=run_id,
        reference_type="draft_artifact",
        reference_id=BASELINE_ID,
        events=trace,
    )
    create_message.assert_not_awaited()
