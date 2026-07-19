import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.project import Project
from app.database.session import get_db
from app.evidence.service import delete_project_evidence
from app.main import fastapi_app as app
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
EVIDENCE_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
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


def _execute_result(scalars_all: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = scalars_all
    return result


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


def test_delete_project_evidence_removes_records_and_returns_storage_keys(
    mock_session: AsyncMock,
) -> None:
    document = SimpleNamespace(
        id=EVIDENCE_ID,
        relative_path="04-projects/demo/_inbox/report.md",
    )
    workspace_file = SimpleNamespace(
        id=uuid.uuid4(),
        storage_key="demo/_inbox/report.md",
        workspace_path="04-projects/demo/_inbox/report.md",
    )
    mock_session.scalar = AsyncMock(return_value=document)
    mock_session.execute = AsyncMock(
        side_effect=[
            _execute_result([workspace_file]),
            _retention_result(None),
            MagicMock(),
            MagicMock(),
        ]
    )

    async def _run() -> None:
        storage_keys = await delete_project_evidence(
            mock_session, project=_project(), evidence_id=EVIDENCE_ID
        )

        # Storage removal is deferred to the caller: the service returns the keys
        # rather than performing the slow object-storage round-trip itself.
        assert storage_keys == ["demo/_inbox/report.md"]
        # select workspace files + delete workspace files + delete source document
        assert mock_session.execute.await_count == 4
        mock_session.commit.assert_awaited_once()

    run_async(_run())


def test_delete_project_evidence_missing_document_raises_404(mock_session: AsyncMock) -> None:
    mock_session.scalar = AsyncMock(return_value=None)

    async def _run() -> None:
        with pytest.raises(HTTPException) as exc_info:
            await delete_project_evidence(
                mock_session, project=_project(), evidence_id=EVIDENCE_ID
            )
        assert exc_info.value.status_code == 404

    run_async(_run())


def test_delete_project_evidence_removes_unindexed_inbox_workspace_file(
    mock_session: AsyncMock,
) -> None:
    workspace_file = SimpleNamespace(
        id=EVIDENCE_ID,
        storage_key="demo/_inbox/cover.pdf",
        workspace_path="04-projects/demo/_inbox/cover.pdf",
    )
    mock_session.scalar = AsyncMock(side_effect=[None, workspace_file])
    mock_session.execute = AsyncMock(
        side_effect=[_retention_result(None), MagicMock()]
    )

    async def _run() -> None:
        storage_keys = await delete_project_evidence(
            mock_session, project=_project(), evidence_id=EVIDENCE_ID
        )

        assert storage_keys == ["demo/_inbox/cover.pdf"]
        assert mock_session.execute.await_count == 2
        mock_session.commit.assert_awaited_once()

    run_async(_run())


def _retention_result(value) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def test_delete_project_evidence_refuses_retained_workspace_file(
    mock_session: AsyncMock,
) -> None:
    document = SimpleNamespace(id=EVIDENCE_ID, relative_path="04-projects/demo/_inbox/report.md")
    workspace_file = SimpleNamespace(id=uuid.uuid4(), storage_key="demo/report.md", workspace_path=document.relative_path)
    mock_session.scalar = AsyncMock(return_value=document)
    mock_session.execute = AsyncMock(
        side_effect=[_execute_result([workspace_file]), _retention_result(uuid.uuid4())]
    )

    async def _run() -> None:
        with pytest.raises(HTTPException) as exc_info:
            await delete_project_evidence(mock_session, project=_project(), evidence_id=EVIDENCE_ID)
        assert exc_info.value.status_code == 409
        mock_session.commit.assert_not_awaited()

    run_async(_run())


def test_delete_evidence_endpoint_requires_project_ownership(
    client: TestClient, mock_session: AsyncMock
) -> None:
    other_project = _project()
    other_project.owner_user_id = uuid.uuid4()

    with patch("app.api.projects.get_project", new=AsyncMock(return_value=other_project)):
        response = client.delete(f"/projects/{PROJECT_ID}/evidence/{EVIDENCE_ID}")

    assert response.status_code == 403


def test_delete_evidence_endpoint_returns_204(
    client: TestClient, mock_session: AsyncMock
) -> None:
    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch(
            "app.api.projects.delete_project_evidence",
            new=AsyncMock(return_value=[]),
        ) as mock_delete,
    ):
        response = client.delete(f"/projects/{PROJECT_ID}/evidence/{EVIDENCE_ID}")

    assert response.status_code == 204
    mock_delete.assert_awaited_once()


def test_delete_evidence_endpoint_schedules_background_storage_cleanup(
    client: TestClient, mock_session: AsyncMock
) -> None:
    storage_keys = ["demo/_inbox/report.md"]
    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch(
            "app.api.projects.delete_project_evidence",
            new=AsyncMock(return_value=storage_keys),
        ),
        patch("app.api.projects.delete_project_files") as mock_delete_files,
    ):
        response = client.delete(f"/projects/{PROJECT_ID}/evidence/{EVIDENCE_ID}")

    assert response.status_code == 204
    # The storage cleanup runs as a background task after the response is sent.
    mock_delete_files.assert_called_once_with(storage_keys=storage_keys)
