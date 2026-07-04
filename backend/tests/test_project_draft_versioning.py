import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.database.session import get_db
from app.main import fastapi_app as app

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
NOW = datetime(2026, 7, 4, 12, 0, 0, tzinfo=timezone.utc)


def _project(*, owner_user_id: uuid.UUID = USER_ID) -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=owner_user_id,
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


def _draft(*, draft_id: uuid.UUID = DRAFT_ID, version: int, content: str) -> DraftArtifact:
    return DraftArtifact(
        id=draft_id,
        project_id=PROJECT_ID,
        workflow_type="create_pmp",
        version=version,
        status="draft",
        title="Project Management Plan",
        workspace_path="04-projects/demo/00-brief-pmp/PMP.md",
        author_user_id=USER_ID,
        content_markdown=content,
        model="gpt-4.1-mini",
        runtime="clerk-sitewise-create-pmp",
        provenance_metadata={"draft_mode": "evidence_grounded"},
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


def test_patch_project_draft_creates_new_version(
    client: TestClient,
    mock_session: AsyncMock,
) -> None:
    original = _draft(version=1, content="# Original")
    updated = _draft(
        draft_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        version=2,
        content="# Edited",
    )

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.get_draft_artifact", new=AsyncMock(return_value=original)),
        patch(
            "app.api.projects.create_draft_revision",
            new=AsyncMock(return_value=updated),
        ) as create_revision,
        patch("app.api.projects.sync_pmp_draft_workspace", new=AsyncMock()) as sync_pmp,
    ):
        response = client.patch(
            f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}",
            json={"content_markdown": "# Edited"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(updated.id)
    assert payload["version"] == 2
    assert payload["content_markdown"] == "# Edited"
    assert original.content_markdown == "# Original"
    create_revision.assert_awaited_once_with(
        mock_session,
        draft=original,
        author_user_id=USER_ID,
        content_markdown="# Edited",
        edit_source="user",
    )
    sync_pmp.assert_awaited_once()
    assert sync_pmp.await_args.kwargs["draft"] is updated


def test_patch_project_draft_rejects_source_document_id(
    client: TestClient,
) -> None:
    source_document_id = uuid.UUID("55555555-5555-5555-5555-555555555555")

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.get_draft_artifact", new=AsyncMock(return_value=None)),
    ):
        response = client.patch(
            f"/projects/{PROJECT_ID}/drafts/{source_document_id}",
            json={"content_markdown": "# Not a draft"},
        )

    assert response.status_code == 404
