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
from app.projects.decisions import DecisionValidationError

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
        decision_set_revision=1,
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
        revision=1,
        locked=False,
        evidence_conflict=False,
        agent_suggestion=None,
        provenance={},
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
    updated = _draft(
        f"# PMP\n\n{DECISION_BLOCK.replace('traditional', 'design_construct').replace('agent', 'user')}"
    )
    row = _decision_row()
    row.selected = "design_construct"
    row.source = "user"

    async def latest_draft(session, *, project_id, workflow_type):  # noqa: ANN001
        if workflow_type == "create_pmp":
            return draft
        return None

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.projects.list_project_decisions",
            new=AsyncMock(return_value=([row], 1)),
        ),
        patch(
            "app.api.projects.update_project_decision",
            new=AsyncMock(return_value=(row, 2)),
        ) as update_decision,
        patch("app.api.projects.sync_decisions_from_markdown", new=AsyncMock()),
        patch(
            "app.api.projects.read_project_decision",
            new=AsyncMock(return_value=(row, 3)),
        ),
        patch(
            "app.api.projects.get_latest_draft_artifact",
            new=AsyncMock(side_effect=latest_draft),
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
        patch("app.api.projects.sync_cost_plan_draft_workspace", new=AsyncMock()),
        patch("app.api.projects.record_activity_events", new=AsyncMock()),
    ):
        response = client.put(
            f"/projects/{PROJECT_ID}/decisions/procurement-route",
            json={
                "selected": "design_construct",
                "expected_revision": 1,
                "expected_set_revision": 1,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["selected"] == "design_construct"
    assert payload["draft"]["content_markdown"]
    update_decision.assert_awaited_once()
    update_content.assert_awaited_once()
    rewritten = update_content.await_args.kwargs["content_markdown"]
    assert '"selected": "design_construct"' in rewritten
    assert '"source": "user"' in rewritten


def test_put_project_decision_restamps_cost_plan_and_pmp(
    client: TestClient,
    mock_session: AsyncMock,
) -> None:
    pmp_draft = _draft(f"# PMP\n\n{DECISION_BLOCK}")
    cost_draft = DraftArtifact(
        id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        project_id=PROJECT_ID,
        workflow_type="create_cost_plan",
        version=1,
        status="draft",
        title="Cost Plan",
        workspace_path="04-projects/demo/01-cost/cost-plan.md",
        author_user_id=USER_ID,
        content_markdown=f"# Cost\n\n{DECISION_BLOCK}",
        model="gpt-4.1-mini",
        runtime="clerk-sitewise-create-cost-plan",
        provenance_metadata={},
        created_at=NOW,
        updated_at=NOW,
    )
    row = _decision_row()
    row.selected = "design_construct"
    row.source = "user"
    updates: list[str] = []

    async def latest_draft(session, *, project_id, workflow_type):  # noqa: ANN001
        if workflow_type == "create_pmp":
            return pmp_draft
        if workflow_type == "create_cost_plan":
            return cost_draft
        return None

    async def update_content(session, draft, *, content_markdown):  # noqa: ANN001
        updates.append(draft.workflow_type)
        draft.content_markdown = content_markdown
        return draft

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.projects.list_project_decisions",
            new=AsyncMock(return_value=([row], 1)),
        ),
        patch(
            "app.api.projects.update_project_decision",
            new=AsyncMock(return_value=(row, 2)),
        ),
        patch("app.api.projects.sync_decisions_from_markdown", new=AsyncMock()),
        patch(
            "app.api.projects.read_project_decision",
            new=AsyncMock(return_value=(row, 3)),
        ),
        patch(
            "app.api.projects.get_latest_draft_artifact",
            new=AsyncMock(side_effect=latest_draft),
        ),
        patch(
            "app.api.projects.locked_selections",
            new=AsyncMock(return_value={"procurement-route": "design_construct"}),
        ),
        patch(
            "app.api.projects.update_draft_content",
            new=AsyncMock(side_effect=update_content),
        ),
        patch("app.api.projects.sync_pmp_draft_workspace", new=AsyncMock()) as sync_pmp,
        patch(
            "app.api.projects.sync_cost_plan_draft_workspace", new=AsyncMock()
        ) as sync_cost,
        patch("app.api.projects.record_activity_events", new=AsyncMock()),
    ):
        response = client.put(
            f"/projects/{PROJECT_ID}/decisions/procurement-route",
            json={
                "selected": "design_construct",
                "expected_revision": 1,
                "expected_set_revision": 1,
            },
        )

    assert response.status_code == 200
    assert updates == ["create_pmp", "create_cost_plan"]
    sync_pmp.assert_awaited_once()
    sync_cost.assert_awaited_once()
    assert '"selected": "design_construct"' in pmp_draft.content_markdown
    assert '"selected": "design_construct"' in cost_draft.content_markdown


def test_put_project_decision_rejects_invalid_option(client: TestClient) -> None:
    row = _decision_row()
    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.projects.list_project_decisions",
            new=AsyncMock(return_value=([row], 1)),
        ),
        patch(
            "app.api.projects.update_project_decision",
            new=AsyncMock(side_effect=DecisionValidationError("invalid option")),
        ),
    ):
        response = client.put(
            f"/projects/{PROJECT_ID}/decisions/procurement-route",
            json={
                "selected": "not-valid",
                "expected_revision": 1,
                "expected_set_revision": 1,
            },
        )
    assert response.status_code == 422
