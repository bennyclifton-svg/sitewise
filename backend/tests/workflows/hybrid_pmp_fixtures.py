"""Shared fixtures for hybrid Create PMP workflow tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

from app.database.project import Project
from app.retrieval.schemas import SourcePassage
from app.sitewise.pmp_sources import required_platform_paths
from app.workflows.pmp_narrative import PmpNarrativeOutput, RegisterRow

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_ROOT = REPO_ROOT / "data" / "synthetic-mobilisation-evidence"
FIXTURE_DIR = EVIDENCE_ROOT / "chen-residence"

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def harrison_clarke_project(**overrides: Any) -> Project:
    values = {
        "id": PROJECT_ID,
        "owner_user_id": USER_ID,
        "slug": "test-project-112",
        "title": "Chen Residence",
        "workspace_path": "04-projects/test-project-112",
        "phase": "brief-planning",
        "archetype": "new-dwelling",
        "user_role": "architect-pm",
        "state": "NSW",
        "status": "active",
        "project_metadata": None,
        "created_at": datetime(2026, 6, 8, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 6, 8, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return Project(**values)


def evidence_passage(relative_path: str, content: str, *, project_slug: str) -> SourcePassage:
    return SourcePassage(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        content=content,
        project=project_slug,
        phase="reference",
        source_type="project_evidence",
        document_class="project_evidence",
        filename=relative_path.split("/")[-1],
        relative_path=relative_path,
        document_metadata=None,
        chunk_metadata={"whole_document": True},
        score=1.0,
    )


def platform_passage(relative_path: str, source_type: str) -> SourcePassage:
    return SourcePassage(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        content=f"Platform source: {relative_path}",
        project="seed",
        phase="reference",
        source_type=source_type,
        document_class="reference_guide" if source_type == "reference" else source_type,
        filename=relative_path.split("/")[-1],
        relative_path=relative_path,
        document_metadata={"knowledge_scope": "platform"},
        chunk_metadata={"whole_document": True},
        score=1.0,
    )


def platform_passages_for_project(project: Project) -> list[SourcePassage]:
    paths = required_platform_paths(
        archetype=project.archetype or "",
        user_role=project.user_role or "",
    )
    passages: list[SourcePassage] = []
    for path in paths:
        source_type = "doctrine" if path.startswith("docs/") else "reference"
        passages.append(platform_passage(path, source_type))
    return passages


def harrison_clarke_mobilisation_passages(*, project_slug: str) -> list[SourcePassage]:
    engagement_path = (
        f"{project_slug}/02-consultant/architect/"
        "01-engagement-letter-harrison-clarke-studio.md"
    )
    fee_path = f"{project_slug}/02-consultant/architect/02-fee-proposal-harrison-clarke-studio.md"
    return [
        evidence_passage(
            engagement_path,
            (FIXTURE_DIR / "01-engagement-letter-harrison-clarke-studio.md").read_text(
                encoding="utf-8"
            ),
            project_slug=project_slug,
        ),
        evidence_passage(
            fee_path,
            (FIXTURE_DIR / "02-fee-proposal-harrison-clarke-studio.md").read_text(
                encoding="utf-8"
            ),
            project_slug=project_slug,
        ),
    ]


def harrison_clarke_narrative() -> PmpNarrativeOutput:
    return PmpNarrativeOutput(
        judgements=[
            "Post-engagement mobilisation posture; master programme required before September 2026 DA target.",
            "DA pathway assumed (not CDC) per fee proposal — programme contingent on due diligence completion.",
        ],
        recommendations=[
            "Owner to confirm working budget ceiling by 2026-06-28.",
            "Architect-PM to issue master programme aligned to September 2026 DA target by 2026-06-28.",
            "Architect-PM to declare Linden Constructions conflict before tender list lock by 2026-06-28.",
        ],
        register_rows=[
            RegisterRow(
                id="R-001",
                description="Master programme",
                owner="Architect-PM",
                status="Open",
                due_date="2026-06-28",
                source="engagement letter",
                next_action="Issue programme aligned to September 2026 DA target",
            ),
            RegisterRow(
                id="R-002",
                description="Linden conflict declaration",
                owner="Architect-PM",
                status="Open",
                due_date="2026-06-28",
                source="fee proposal",
                next_action="Declare evaluation involvement before tender list lock",
            ),
            RegisterRow(
                id="R-003",
                description="Working budget ceiling",
                owner="Owner",
                status="Open",
                due_date="2026-06-28",
                source="gap: construction budget",
                next_action="Confirm construction budget allowance",
            ),
        ],
        risk_rows=[],
        workflow_warnings=[
            "Geotechnical report not on file.",
            "Certifier not yet appointed.",
        ],
    )


def mock_draft_artifact(**overrides: Any) -> AsyncMock:
    draft = AsyncMock()
    draft.id = uuid.uuid4()
    draft.project_id = PROJECT_ID
    draft.workflow_type = "create_pmp"
    draft.version = 1
    draft.status = "draft"
    draft.title = "Project Management Plan"
    draft.workspace_path = "04-projects/test-project-112/00-brief-pmp/PMP-draft-v01.md"
    draft.author_user_id = USER_ID
    draft.content_markdown = "# Project Management Plan"
    draft.model = "gpt-4o-mini"
    draft.runtime = "clerk-sitewise-create-pmp-hybrid"
    draft.provenance_metadata = {}
    draft.created_at = datetime(2026, 6, 8, tzinfo=timezone.utc)
    draft.updated_at = datetime(2026, 6, 8, tzinfo=timezone.utc)
    for key, value in overrides.items():
        setattr(draft, key, value)
    return draft
