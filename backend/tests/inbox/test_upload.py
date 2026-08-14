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
from tests.conftest import run_async

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

def test_upload_inbox_files_stores_and_queues_ingest_without_sorting(
    mock_session: AsyncMock,
) -> None:
    project = _project()
    content = b"# Procurement matrix\n\nEvaluation content."
    snapshot = type(
        "Snapshot",
        (),
        {
            "content_fingerprint": "a" * 64,
            "profile": type("Profile", (), {"profile_revision": 1})(),
            "decisions": type("Decisions", (), {"set_revision": 1})(),
        },
    )()

    async def _run() -> None:
        with (
            patch("app.inbox.service.get_workspace_file_by_path", new=AsyncMock(return_value=None)),
            patch("app.inbox.service.upload_project_file") as mock_upload,
            patch(
                "app.inbox.service.lock_project",
                new=AsyncMock(return_value=project),
            ) as mock_lock_project,
            patch(
                "app.inbox.service.sort_inbox_files",
                new=AsyncMock(),
                create=True,
            ) as mock_sort,
            patch("app.inbox.service.ingest_hosted_file", create=True) as mock_ingest,
            patch(
                "app.inbox.service.start_workflow_run",
                new=AsyncMock(return_value=(type("Run", (), {"id": uuid.uuid4()})(), True)),
                create=True,
            ) as mock_start,
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
                user_id=USER_ID,
                snapshot=snapshot,
            )

        mock_upload.assert_called_once()
        mock_lock_project.assert_awaited_once_with(mock_session, project_id=project.id)
        mock_ingest.assert_not_called()
        mock_sort.assert_not_called()
        mock_start.assert_awaited_once()
        assert mock_start.await_args.kwargs["workflow_type"] == "ingest_project_document"
        assert mock_start.await_args.kwargs["request"].parameters == {
            "workspace_file_id": str(outcomes[0].id),
            "document_metadata": {},
        }
        assert mock_start.await_args.kwargs["request"].idempotency_key.endswith(
            outcomes[0].content_hash
        )
        assert len(outcomes) == 1
        assert outcomes[0].workspace_path == "04-projects/demo/_inbox/EVALUATION/matrix.md"
        assert outcomes[0].ingest_status == "queued"
        assert outcomes[0].message == "Uploaded; ingestion queued"
        assert outcomes[0].workflow_run_id is not None
        mock_session.commit.assert_called_once()

    run_async(_run())


def test_upload_inbox_files_hides_storage_provider_error(
    mock_session: AsyncMock,
) -> None:
    project = _project()
    provider_detail = "provider-secret-" + ("x" * 24)
    snapshot = type("Snapshot", (), {})()

    async def _run() -> None:
        with (
            patch(
                "app.inbox.service.get_workspace_file_by_path",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.inbox.service.upload_project_file",
                side_effect=RuntimeError(provider_detail),
            ),
            patch(
                "app.inbox.service.record_activity_events", new=AsyncMock()
            ) as record_events,
            patch("app.inbox.service.logger.error") as log_error,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await upload_inbox_files(
                    mock_session,
                    project=project,
                    items=[InboxUploadItem(filename="report.md", content=b"body")],
                    user_id=USER_ID,
                    snapshot=snapshot,
                )

        assert exc_info.value.status_code == 502
        assert exc_info.value.detail == (
            "Could not store the file in project storage. Please try again."
        )
        assert provider_detail not in str(exc_info.value.detail)
        event = record_events.await_args.kwargs["events"][0]
        assert event.metadata["error_type"] == "RuntimeError"
        assert provider_detail not in str(event)
        assert log_error.call_args.kwargs["error_type"] == "RuntimeError"
        assert "error" not in log_error.call_args.kwargs
        assert "exc_info" not in log_error.call_args.kwargs

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
    async def fake_upload_inbox_files(session, *, project, items, user_id, snapshot):
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
        patch("app.api.projects.get_project_snapshot", new=AsyncMock(return_value=object())),
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
    assert payload["files"][0]["workflow_run_id"] is None


def test_post_document_repair_preview_is_read_only_and_returns_proposals(
    client: TestClient,
    mock_session: AsyncMock,
) -> None:
    from app.intake.repair_service import FileRepairPreview, FileRepairPreviewResult

    preview = FileRepairPreviewResult(
        inspected=1,
        changes=1,
        rows=[
            FileRepairPreview(
                status="change",
                current_path="04-projects/demo/03-design/architect/HY-SK~1.PDF",
                current_filename="HY-SK~1.PDF",
                proposed_path=(
                    "04-projects/demo/03-design/hydraulic/"
                    "HY-SK-06 - ROOF DRAINAGE PLAN Rev P1.PDF"
                ),
                proposed_filename="HY-SK-06 - ROOF DRAINAGE PLAN Rev P1.PDF",
                document_number="HY-SK-06",
                title="ROOF DRAINAGE PLAN",
                revision="P1",
                category="Hydraulic",
                confidence="high",
                changes=("folder", "filename", "metadata"),
            )
        ],
    )

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.projects.preview_existing_file_repairs",
            new=AsyncMock(return_value=preview),
            create=True,
        ),
    ):
        response = client.post(f"/projects/{PROJECT_ID}/document-repairs/preview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["inspected"] == 1
    assert payload["changes"] == 1
    assert payload["rows"][0]["document_number"] == "HY-SK-06"
    mock_session.commit.assert_not_awaited()


def test_post_document_repair_apply_requires_explicit_paths(
    client: TestClient,
    mock_session: AsyncMock,
) -> None:
    from app.intake.repair_service import FileRepairApplyResult, FileRepairApplyRow

    current_path = "04-projects/demo/03-design/architect/HY-SK~1.PDF"
    applied = FileRepairApplyResult(
        applied=1,
        rows=[
            FileRepairApplyRow(
                current_path=current_path,
                proposed_path=(
                    "04-projects/demo/03-design/hydraulic/"
                    "HY-SK-06 - ROOF DRAINAGE PLAN Rev P1.PDF"
                ),
                status="applied",
            )
        ],
    )
    apply_repairs = AsyncMock(return_value=applied)

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.projects.apply_existing_file_repairs",
            new=apply_repairs,
            create=True,
        ),
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/document-repairs/apply",
            json={"workspace_paths": [current_path]},
        )

    assert response.status_code == 200
    assert response.json()["applied"] == 1
    assert apply_repairs.await_args.kwargs["workspace_paths"] == {current_path}
