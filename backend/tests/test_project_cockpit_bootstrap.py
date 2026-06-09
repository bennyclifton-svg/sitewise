import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.project import Project
from app.database.session import get_db
from app.main import fastapi_app as app
from app.schemas.projects import EvidencePreview, PlatformKnowledgeStatus

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
EVIDENCE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
NOW = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)


def _project() -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="demo",
        title="Demo Project",
        workspace_path="04-projects/demo",
        phase="procurement",
        archetype="small-commercial",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata={},
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_session: AsyncMock) -> TestClient:
    current_user = CurrentUser(id=USER_ID, email="user@example.com")

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _draft_summary() -> dict:
    return {
        "id": DRAFT_ID,
        "project_id": PROJECT_ID,
        "workflow_type": "create_pmp",
        "version": 7,
        "status": "draft",
        "title": "PMP Draft",
        "workspace_path": "04-projects/demo/00-brief-pmp/pmp.md",
        "author_user_id": USER_ID,
        "model": "gpt-4o-mini",
        "runtime": "clerk-sitewise",
        "created_at": NOW,
        "updated_at": NOW,
    }


def test_cockpit_bootstrap_returns_lightweight_first_paint_payload(
    client: TestClient,
) -> None:
    evidence = EvidencePreview(
        id=EVIDENCE_ID,
        title="Architect Engagement",
        filename="engagement.md",
        relative_path="04-projects/demo/02-consultant/architect/engagement.md",
        source_type="project_evidence",
        document_class="project_evidence",
        excerpt="Architect engagement excerpt.",
    )

    with (
        patch("app.api.projects.ensure_user_exists", new=AsyncMock()),
        patch("app.api.projects.ensure_default_project_catalog", new=AsyncMock()),
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.list_projects", new=AsyncMock(return_value=[_project()])),
        patch(
            "app.api.projects.list_workspace_files_for_project",
            new=AsyncMock(
                return_value=[
                    SimpleNamespace(
                        workspace_path="04-projects/demo/02-consultant/architect/engagement.md"
                    )
                ]
            ),
        ),
        patch("app.api.projects._list_project_evidence_previews", new=AsyncMock(return_value=[evidence])),
        patch(
            "app.api.projects._platform_knowledge_status",
            new=AsyncMock(return_value=PlatformKnowledgeStatus(available=False, buckets=[])),
        ),
        patch(
            "app.api.projects.get_latest_draft_artifact_summaries",
            new=AsyncMock(return_value={"create_pmp": _draft_summary()}),
        ),
    ):
        response = client.get(f"/projects/{PROJECT_ID}/cockpit-bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"]["id"] == str(PROJECT_ID)
    assert payload["projects"][0]["id"] == str(PROJECT_ID)
    assert payload["workspace_tree"]["tree"]
    assert payload["evidence"][0]["id"] == str(EVIDENCE_ID)
    assert payload["evidence"][0]["content"] is None
    assert payload["latest_drafts"]["create_pmp"]["id"] == str(DRAFT_ID)
    assert "content_markdown" not in payload["latest_drafts"]["create_pmp"]
    assert "provenance_metadata" not in payload["latest_drafts"]["create_pmp"]
    assert payload["latest_drafts"]["create_cost_plan"] is None
    assert payload["latest_drafts"]["sort_files"] is None
    assert "total" in payload["timings_ms"]
