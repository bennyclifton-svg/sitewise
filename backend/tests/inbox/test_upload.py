import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.project import Project
from app.database.session import get_db
from app.inbox.service import InboxUploadItem, InboxUploadOutcome, upload_inbox_files
from app.main import fastapi_app as app

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
NOW = datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc)


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


def test_validate_upload_batch_rejects_empty_file() -> None:
    from app.inbox.service import validate_upload_batch

    with pytest.raises(HTTPException) as exc_info:
        validate_upload_batch([InboxUploadItem(filename="empty.pdf", content=b"")])
    assert exc_info.value.status_code == 400


def test_validate_upload_batch_rejects_unsupported_extension() -> None:
    from app.inbox.service import validate_upload_batch

    with pytest.raises(HTTPException) as exc_info:
        validate_upload_batch([InboxUploadItem(filename="notes.txt", content=b"hello")])
    assert exc_info.value.status_code == 400


from tests.conftest import run_async


def test_upload_inbox_files_stores_and_ingests(mock_session: AsyncMock) -> None:
    project = _project()
    content = b"# Procurement matrix\n\nEvaluation content."

    async def _run() -> None:
        with (
            patch("app.inbox.service.get_workspace_file_by_path", new=AsyncMock(return_value=None)),
            patch("app.inbox.service.upload_project_file") as mock_upload,
            patch("app.inbox.service.ingest_hosted_file", return_value=True) as mock_ingest,
            patch("app.inbox.service.source_document_id_for_path", return_value=uuid.uuid4()),
            patch(
                "app.inbox.service.upsert_workspace_file",
                new=AsyncMock(
                    side_effect=lambda session, **kwargs: type(
                        "Record",
                        (),
                        {
                            "id": uuid.uuid4(),
                            **kwargs,
                        },
                    )()
                ),
            ),
        ):
            outcomes = await upload_inbox_files(
                mock_session,
                project=project,
                items=[InboxUploadItem(filename="matrix.md", content=content, relative_path="EVALUATION")],
            )

        mock_upload.assert_called_once()
        mock_ingest.assert_called_once()
        assert len(outcomes) == 1
        assert outcomes[0].workspace_path == "04-projects/demo/_inbox/EVALUATION/matrix.md"
        assert outcomes[0].ingest_status == "ingested"
        mock_session.commit.assert_called_once()

    run_async(_run())


def test_post_inbox_upload_requires_project_ownership(client: TestClient, mock_session: AsyncMock) -> None:
    other_project = _project()
    other_project.owner_user_id = uuid.uuid4()

    with patch("app.api.projects.get_project", new=AsyncMock(return_value=other_project)):
        response = client.post(
            f"/projects/{PROJECT_ID}/inbox/upload",
            files=[("files", ("report.md", b"# Title\n\nBody", "text/markdown"))],
        )

    assert response.status_code == 403


def test_post_inbox_upload_returns_upload_results(client: TestClient, mock_session: AsyncMock) -> None:
    async def fake_upload_inbox_files(session, *, project, items):
        return [
            InboxUploadOutcome(
                id=uuid.uuid4(),
                filename="report.md",
                workspace_path=f"{project.workspace_path}/_inbox/report.md",
                content_hash="abc123",
                size_bytes=12,
                ingest_status="ingested",
                message="Uploaded and ingested",
            )
        ]

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.ensure_user_exists", new=AsyncMock()),
        patch("app.api.projects.upload_inbox_files", side_effect=fake_upload_inbox_files),
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/inbox/upload",
            files=[("files", ("report.md", b"# Title\n\nBody", "text/markdown"))],
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["files"][0]["ingest_status"] == "ingested"
    assert payload["files"][0]["workspace_path"].endswith("/_inbox/report.md")
