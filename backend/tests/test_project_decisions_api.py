import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.database.project_decision import ProjectDecision
from app.database.session import get_db
from app.main import fastapi_app as app

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
DECISION_ROW_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
NOW = datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)

DECISION_BLOCK = """\
```pmp-decision
{
  "id": "procurement-route",
  "section": "Procurement",
  "label": "Procurement route",
  "options": [
    {"value": "traditional", "label": "Traditional (Lump Sum)"},
    {"value": "design_construct", "label": "Design & Construct"}
  ],
  "selected": "traditional",
  "source": "agent"
}
```
"""


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


def _draft(content: str) -> DraftArtifact:
    return DraftArtifact(
        id=DRAFT_ID,
        project_id=PROJECT_ID,
        workflow_type="create_pmp",
        version=1,
        status="draft",
        title="Project Management Plan",
        workspace_path="04-projects/demo/00-brief-pmp/PMP.md",
        author_user_id=USER_ID,
        content_markdown=content,
        model="gpt-4.1-mini",
        runtime="clerk-sitewise-create-pmp",
        provenance_metadata={},
        created_at=NOW,
        updated_at=NOW,
    )


def _decision_row() -> ProjectDecision:
    return ProjectDecision(
        id=DECISION_ROW_ID,
        project_id=PROJECT_ID,
        decision_id="procurement-route",
        section="Procurement",
        label="Procurement route",
        options=[
            {"value": "traditional", "label": "Traditional (Lump Sum)"},
            {"value": "design_construct", "label": "Design & Construct"},
        ],
        selected="traditional",
        source="agent",
        workflow_type="create_pmp",
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


def test_put_project_decision_rewrites_draft_markdown(
    client: TestClient,
    mock_session: AsyncMock,
) -> None:
    draft = _draft(f"# PMP\n\n{DECISION_BLOCK}")
    updated = _draft(f"# PMP\n\n{DECISION_BLOCK.replace('traditional', 'design_construct').replace('agent', 'user')}")
    row = _decision_row()
    row.selected = "design_construct"
    row.source = "user"

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.list_decisions", new=AsyncMock(return_value=[row])),
        patch("app.api.projects.upsert_decision", new=AsyncMock(return_value=row)) as upsert,
        patch(
            "app.api.projects.get_latest_draft_artifact",
            new=AsyncMock(return_value=draft),
        ),
        patch(
            "app.api.projects.locked_selections",
            new=AsyncMock(return_value={"procurement-route": "design_construct"}),
        ),
        patch(
            "app.api.projects.update_draft_content",
            new=AsyncMock(return_value=updated),
        ) as update_content,
        patch("app.api.projects.sync_pmp_draft_workspace", new=AsyncMock()),
        patch("app.api.projects.record_activity_events", new=AsyncMock()),
    ):
        response = client.put(
            f"/projects/{PROJECT_ID}/decisions/procurement-route",
            json={"selected": "design_construct"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["selected"] == "design_construct"
    assert payload["draft"]["content_markdown"]
    upsert.assert_awaited_once()
    update_content.assert_awaited_once()
    rewritten = update_content.await_args.kwargs["content_markdown"]
    assert '"selected": "design_construct"' in rewritten
    assert '"source": "user"' in rewritten


def test_put_project_decision_rejects_invalid_option(client: TestClient) -> None:
    row = _decision_row()
    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.list_decisions", new=AsyncMock(return_value=[row])),
    ):
        response = client.put(
            f"/projects/{PROJECT_ID}/decisions/procurement-route",
            json={"selected": "not-valid"},
        )
    assert response.status_code == 422
