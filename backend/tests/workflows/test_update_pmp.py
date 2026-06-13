import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.workflows.create_pmp import PmpDraftOutput, markdown_section_headings
from app.workflows.update_pmp import (
    run_update_pmp_workflow,
    validate_update_pmp_output,
)
from tests.conftest import run_async
from tests.workflows.test_create_pmp import (
    _valid_evidence_grounded_pmp_markdown,
    _valid_pmp_markdown,
    _valid_seed_consulted,
)

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
BASELINE_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


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
        model="gpt-4o-mini",
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
            archetype="new-dwelling",
            user_role="architect-pm",
            has_evidence_delta=True,
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
            archetype="new-dwelling",
            user_role="architect-pm",
            has_evidence_delta=True,
        )
    except Exception as exc:
        assert "evidence_grounded fidelity" in str(exc)
    else:
        raise AssertionError("Expected validation to fail for evidence contradictions")


def test_markdown_section_headings_extracts_custom_sections() -> None:
    markdown = "## Project overview\n\n## Custom client section\n\nBody\n"
    assert markdown_section_headings(markdown) == [
        "Project overview",
        "Custom client section",
    ]


def test_update_pmp_fails_without_baseline() -> None:
    with patch(
        "app.workflows.update_pmp.get_latest_draft_artifact",
        new=AsyncMock(return_value=None),
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
