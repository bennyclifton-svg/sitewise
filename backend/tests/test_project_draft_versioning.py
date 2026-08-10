import uuid
from datetime import datetime, timezone
from unittest.mock import ANY, AsyncMock, MagicMock, patch

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


def _draft(
    *, draft_id: uuid.UUID = DRAFT_ID, version: int, content: str
) -> DraftArtifact:
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
        model="gpt-5.6-luna",
        runtime="clerk-sitewise-create-pmp",
        provenance_metadata={"draft_mode": "evidence_grounded"},
        created_at=NOW,
        updated_at=NOW,
    )


def _cost_plan_draft(
    *,
    draft_id: uuid.UUID = DRAFT_ID,
    version: int,
    content: str,
) -> DraftArtifact:
    return DraftArtifact(
        id=draft_id,
        project_id=PROJECT_ID,
        workflow_type="create_cost_plan",
        version=version,
        status="draft",
        title="Cost Plan",
        workspace_path="04-projects/demo/01-cost/cost_plan_v01.md",
        author_user_id=USER_ID,
        content_markdown=content,
        model="gpt-5.6-luna",
        runtime="clerk-sitewise-create-cost-plan",
        provenance_metadata={"workbook": {"file_name": "Cost_Plan_v01.draft.xlsx"}},
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
        patch(
            "app.api.projects.get_draft_artifact", new=AsyncMock(return_value=original)
        ),
        patch(
            "app.api.projects.revise_workflow_artefact",
            new=AsyncMock(return_value=updated),
        ) as revise_artefact,
    ):
        response = client.patch(
            f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}",
            json={"content_markdown": "# Edited", "expected_base_version": 1},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(updated.id)
    assert payload["version"] == 2
    assert payload["content_markdown"] == "# Edited"
    assert original.content_markdown == "# Original"
    revise_artefact.assert_awaited_once_with(
        mock_session,
        project=ANY,
        draft=original,
        expected_base_version=1,
        author_user_id=USER_ID,
        content_markdown="# Edited",
        actor_source="user",
    )


def test_patch_cost_plan_draft_regenerates_workbook(
    client: TestClient,
    mock_session: AsyncMock,
) -> None:
    original = _cost_plan_draft(version=1, content="# Cost Plan\n\nOld")
    updated = _cost_plan_draft(
        draft_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        version=2,
        content="# Cost Plan\n\nEdited",
    )

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.projects.get_draft_artifact", new=AsyncMock(return_value=original)
        ),
        patch(
            "app.api.projects.revise_workflow_artefact",
            new=AsyncMock(return_value=updated),
        ) as revise_artefact,
    ):
        response = client.patch(
            f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}",
            json={
                "content_markdown": "# Cost Plan\n\nEdited",
                "expected_base_version": 1,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == 2
    assert payload["content_markdown"] == "# Cost Plan\n\nEdited"
    revise_artefact.assert_awaited_once_with(
        mock_session,
        project=ANY,
        draft=original,
        expected_base_version=1,
        author_user_id=USER_ID,
        content_markdown="# Cost Plan\n\nEdited",
        actor_source="user",
    )


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
            json={"content_markdown": "# Not a draft", "expected_base_version": 1},
        )

    assert response.status_code == 404


def test_get_project_draft_by_workspace_path_returns_historical_revision(
    client: TestClient,
) -> None:
    historical = _draft(version=1, content="# Historical")

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch(
            "app.api.projects.get_latest_draft_artifact_by_workspace_path",
            new=AsyncMock(return_value=historical),
        ) as get_by_path,
    ):
        response = client.get(
            f"/projects/{PROJECT_ID}/drafts/by-workspace-path",
            params={"workspace_path": historical.workspace_path},
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(historical.id)
    get_by_path.assert_awaited_once_with(
        ANY,
        project_id=PROJECT_ID,
        workspace_path=historical.workspace_path,
    )


def test_export_project_draft_renders_and_caches_pdf(
    client: TestClient,
) -> None:
    draft = _draft(
        version=3,
        content="# Project Management Plan\n\n## Citation key\n\n[1] `brief.pdf`",
    )
    render_export = MagicMock(return_value=b"%PDF-1.7 issue")
    upload = MagicMock(return_value="storage-key")
    upsert = AsyncMock()

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.get_draft_artifact", new=AsyncMock(return_value=draft)),
        patch(
            "app.api.projects.get_artefact_export",
            new=AsyncMock(return_value=None),
        ),
        patch("app.api.projects.render_artifact_export", new=render_export),
        patch("app.api.projects.upload_project_file", new=upload),
        patch("app.api.projects.cache_ready_artefact_export", new=upsert),
    ):
        response = client.get(
            f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}/export",
            params={"format": "pdf"},
        )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "private, no-cache"
    assert (
        'filename="Project_Management_Plan_v03.pdf"'
        in response.headers["content-disposition"]
    )
    render_export.assert_called_once_with(
        draft.content_markdown,
        export_format="pdf",
        project_title="Demo Project",
        artifact_title="Project Management Plan",
        version=3,
        workflow_type="create_pmp",
    )
    upload.assert_called_once()
    upsert.assert_awaited_once()


def test_export_project_draft_reuses_cached_bytes(client: TestClient) -> None:
    draft = _draft(version=3, content="# Project Management Plan")
    cached = MagicMock(
        storage_key="cached/export.pdf",
        status="ready",
        workspace_path=ANY,
    )
    render_export = MagicMock()
    download = MagicMock(return_value=b"%PDF-1.7 cached")

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.get_draft_artifact", new=AsyncMock(return_value=draft)),
        patch(
            "app.api.projects.get_artefact_export",
            new=AsyncMock(return_value=cached),
        ),
        patch("app.api.projects.render_artifact_export", new=render_export),
        patch("app.api.projects.download_project_file", new=download),
    ):
        response = client.get(
            f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}/export",
            params={"format": "pdf"},
        )

    assert response.status_code == 200
    assert response.content == b"%PDF-1.7 cached"
    download.assert_called_once_with(storage_key="cached/export.pdf")
    render_export.assert_not_called()
