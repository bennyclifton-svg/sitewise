"""Shared fixtures for hybrid Create Cost Plan workflow tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

from app.database.project import Project
from app.retrieval.schemas import SourcePassage
from app.sitewise.cost_plan_sources import required_platform_paths
from app.workflows.cost_plan_narrative import CostPlanNarrativeOutput
from app.workflows.pmp_narrative import RiskRow
from tests.workflows.hybrid_pmp_fixtures import (
    FIXTURE_DIR,
    PROJECT_ID,
    USER_ID,
    evidence_passage,
    platform_passage,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def harrison_clarke_cost_project(**overrides: Any) -> Project:
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


def platform_passages_for_cost_plan(project: Project) -> list[SourcePassage]:
    paths = required_platform_paths(
        archetype=project.archetype or "",
        user_role=project.user_role or "",
    )
    passages: list[SourcePassage] = []
    for path in paths:
        source_type = "doctrine" if path.startswith("docs/") else "reference"
        passages.append(platform_passage(path, source_type))
    return passages


def harrison_clarke_cost_passages(*, project_slug: str) -> list[SourcePassage]:
    base = f"{project_slug}/02-consultant/architect"
    brief_base = f"{project_slug}/00-brief-pmp"
    due_diligence = f"{project_slug}/03-design/01-due-diligence"
    authority = f"{project_slug}/04-authority"
    fixtures: list[tuple[str, str]] = [
        (f"{base}/01-engagement-letter-harrison-clarke-studio.md", "01-engagement-letter-harrison-clarke-studio.md"),
        (f"{base}/02-fee-proposal-harrison-clarke-studio.md", "02-fee-proposal-harrison-clarke-studio.md"),
        (f"{brief_base}/03-owner-project-brief-chen-residence.md", "03-owner-project-brief-chen-residence.md"),
        (
            f"{brief_base}/09-planning-pathway-memo-harrison-clarke.md",
            "09-planning-pathway-memo-harrison-clarke.md",
        ),
        (f"{due_diligence}/06-geotechnical-report-terratech.md", "06-geotechnical-report-terratech.md"),
        (f"{brief_base}/11-master-programme-chen-residence.md", "11-master-programme-chen-residence.md"),
        (f"{authority}/12-certifier-appointment-chen-residence.md", "12-certifier-appointment-chen-residence.md"),
    ]
    return [
        evidence_passage(
            relative_path,
            (FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"),
            project_slug=project_slug,
        )
        for relative_path, fixture_name in fixtures
    ]


def harrison_clarke_cost_narrative() -> CostPlanNarrativeOutput:
    return CostPlanNarrativeOutput(
        judgements=[
            "Owner brief construction ceiling $1,850,000 ex GST is the cost-control reference; "
            "architect fee sits outside that ceiling.",
            "DA + CC pathway adopted; construction breakdown remains TBC until head-builder tender.",
        ],
        recommendations=[
            "Owner to confirm owner-supplied allowances remain at stated levels by 2026-06-28.",
            "Architect-PM to issue tender comparison against $1,850,000 ceiling by 2026-07-05.",
            "Architect-PM to declare Linden Constructions conflict before tender list lock by 2026-06-28.",
        ],
        risk_rows=[
            RiskRow(
                risk="Tender pricing exceeds owner brief ceiling",
                owner="Owner",
                status="Open",
                next_action="Review tender against $1,850,000 ceiling",
                due_date="2026-07-05",
            ),
            RiskRow(
                risk="Footing class / reactive soil allowance",
                owner="Architect-PM",
                status="Open",
                next_action="Adopt geotechnical H1 parameters in tender package",
                due_date="2026-06-28",
            ),
            RiskRow(
                risk="DA programme slip vs September 2026 target",
                owner="Owner",
                status="Partial",
                next_action="Confirm schematic programme",
                due_date="2026-06-28",
            ),
            RiskRow(
                risk="Builder conflict / related-party tender",
                owner="Architect-PM",
                status="Partial",
                next_action="Declare Linden conflict",
                due_date="2026-06-28",
            ),
            RiskRow(
                risk="Consultant fee drift before tender",
                owner="Architect-PM",
                status="Assumption",
                next_action="Lock consultant appointments",
                due_date="2026-07-05",
            ),
        ],
        next_steps=[
            "Owner to confirm owner-supplied allowances by 2026-06-28.",
            "Architect-PM to prepare head-builder tender package by 2026-07-05.",
            "Architect-PM to reconcile tender pricing to owner brief ceiling by 2026-07-12.",
        ],
    )


def mock_cost_plan_draft(**overrides: Any) -> AsyncMock:
    draft = AsyncMock()
    draft.id = uuid.uuid4()
    draft.project_id = PROJECT_ID
    draft.workflow_type = "create_cost_plan"
    draft.version = 1
    draft.status = "draft"
    draft.title = "Project Cost Plan"
    draft.workspace_path = "04-projects/test-project-112/01-cost/cost_plan_v01.md"
    draft.author_user_id = USER_ID
    draft.content_markdown = "# Project Cost Plan"
    draft.model = "gpt-4o-mini"
    draft.runtime = "clerk-sitewise-create-cost-plan-hybrid"
    draft.provenance_metadata = {}
    draft.created_at = datetime(2026, 6, 8, tzinfo=timezone.utc)
    draft.updated_at = datetime(2026, 6, 8, tzinfo=timezone.utc)
    for key, value in overrides.items():
        setattr(draft, key, value)
    return draft
