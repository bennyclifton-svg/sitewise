import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.project import Project
from app.database.session import get_db
from app.main import fastapi_app as app

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
NOW = datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc)


def _project() -> Project:
    return Project(
        id=PROJECT_ID, owner_user_id=USER_ID, slug="demo", title="Demo Project",
        workspace_path="04-projects/demo", phase="procurement",
        archetype="small-commercial", user_role="architect-pm", state="NSW",
        status="active", project_metadata={}, created_at=NOW, updated_at=NOW,
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


def test_analyze_endpoint_requires_ownership(client: TestClient) -> None:
    other = _project()
    other.owner_user_id = uuid.uuid4()
    with patch("app.api.projects.get_project", new=AsyncMock(return_value=other)):
        r = client.post(
            f"/projects/{PROJECT_ID}/inbox/analyze",
            files=[("file", ("x.pdf", b"%PDF-1.4", "application/pdf"))],
        )
    assert r.status_code == 403


def test_analyze_endpoint_returns_proposal(client: TestClient) -> None:
    from app.inbox.split_service import AnalyzeResult, SheetProposal

    async def fake_analyze(*, project, filename, content):
        return AnalyzeResult(
            staging_id="s1", storage_key="k", is_drawing_set=True, confidence=0.9,
            page_count=1, scores={},
            pages=[SheetProposal(1, "Site Plan", "x - 01 Site Plan.pdf", True)],
        )

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.ensure_user_exists", new=AsyncMock()),
        patch("app.api.projects.analyze_pdf_upload", side_effect=fake_analyze),
    ):
        r = client.post(
            f"/projects/{PROJECT_ID}/inbox/analyze",
            files=[("file", ("x.pdf", b"%PDF-1.4", "application/pdf"))],
        )
    assert r.status_code == 200
    body = r.json()
    assert body["is_drawing_set"] is True
    assert body["pages"][0]["proposed_title"] == "Site Plan"


def test_split_endpoint_returns_outcomes(client: TestClient) -> None:
    from app.inbox.service import InboxUploadOutcome

    async def fake_split(session, *, project, staging_id, source_filename):
        return [InboxUploadOutcome(
            id=uuid.uuid4(), filename="x - 01 Site Plan.pdf", workspace_path="w",
            content_hash="h", size_bytes=1, ingest_status="ingested", message="ok")]

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.split_staged_pdf", side_effect=fake_split),
    ):
        r = client.post(
            f"/projects/{PROJECT_ID}/inbox/s1/split",
            json={"source_filename": "x.pdf"},
        )
    assert r.status_code == 201
    assert r.json()["files"][0]["ingest_status"] == "ingested"


def test_commit_endpoint_returns_single_outcome(client: TestClient) -> None:
    from app.inbox.service import InboxUploadOutcome

    async def fake_commit(session, *, project, staging_id, source_filename):
        return InboxUploadOutcome(
            id=uuid.uuid4(), filename="x.pdf", workspace_path="w",
            content_hash="h", size_bytes=1, ingest_status="ingested", message="ok")

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.commit_staged_pdf_single", side_effect=fake_commit),
    ):
        r = client.post(
            f"/projects/{PROJECT_ID}/inbox/s1/commit",
            json={"source_filename": "x.pdf"},
        )
    assert r.status_code == 201
    assert r.json()["files"][0]["filename"] == "x.pdf"
