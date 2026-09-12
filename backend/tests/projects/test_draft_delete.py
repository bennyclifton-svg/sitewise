import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.database.project import Project
from app.projects.draft_delete import delete_project_draft
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
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


def _scalars(items: list) -> MagicMock:
    result = MagicMock()
    result.all.return_value = items
    return result


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


def test_delete_project_draft_clears_procurement_and_returns_storage_keys(
    mock_session: AsyncMock,
) -> None:
    draft = SimpleNamespace(
        id=DRAFT_ID,
        project_id=PROJECT_ID,
        workflow_type="consultant_procurement_quantity_surveyor",
        workspace_path="04-projects/demo/05-procurement/qs/qs_rfp_v01.draft.md",
    )
    export = SimpleNamespace(
        workspace_path=draft.workspace_path,
        storage_key="demo/qs_rfp_v01.draft.md",
    )
    workspace_file = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_path=draft.workspace_path,
        storage_key="demo/qs_rfp_v01.draft.md",
    )
    request = SimpleNamespace(
        current_draft_artifact_id=DRAFT_ID,
        status="draft",
    )
    previous = SimpleNamespace(id=uuid.uuid4(), workflow_type=draft.workflow_type)

    mock_session.get = AsyncMock(return_value=draft)
    mock_session.scalars = AsyncMock(
        side_effect=[
            _scalars([export]),
            _scalars([workspace_file]),
            _scalars([request]),
        ]
    )
    mock_session.execute = AsyncMock(return_value=MagicMock())

    async def _run() -> None:
        with patch(
            "app.projects.draft_delete.get_latest_draft_artifact",
            new=AsyncMock(return_value=previous),
        ):
            storage_keys, latest = await delete_project_draft(
                mock_session, project=_project(), draft_id=DRAFT_ID
            )

        assert storage_keys == ["demo/qs_rfp_v01.draft.md"]
        assert latest is previous
        assert request.current_draft_artifact_id is None
        mock_session.delete.assert_any_await(request)
        mock_session.delete.assert_any_await(draft)
        mock_session.commit.assert_awaited_once()

    run_async(_run())


def test_delete_project_draft_missing_raises_404(mock_session: AsyncMock) -> None:
    mock_session.get = AsyncMock(return_value=None)

    async def _run() -> None:
        with pytest.raises(HTTPException) as exc:
            await delete_project_draft(
                mock_session, project=_project(), draft_id=DRAFT_ID
            )
        assert exc.value.status_code == 404

    run_async(_run())


def test_delete_create_pmp_removes_all_plan_versions(mock_session: AsyncMock) -> None:
    current = SimpleNamespace(
        id=DRAFT_ID,
        project_id=PROJECT_ID,
        workflow_type="create_pmp",
        workspace_path="04-projects/demo/00-brief-pmp/PMP.md",
    )
    previous = SimpleNamespace(
        id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        project_id=PROJECT_ID,
        workflow_type="create_pmp",
        workspace_path="04-projects/demo/00-brief-pmp/PMP_v01.md",
    )
    workspace_file = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_path=current.workspace_path,
        storage_key="demo/PMP.md",
    )

    mock_session.get = AsyncMock(return_value=current)
    mock_session.scalars = AsyncMock(
        side_effect=[
            _scalars([current, previous]),
            _scalars([]),
            _scalars([workspace_file]),
            _scalars([]),
        ]
    )
    mock_session.execute = AsyncMock(return_value=MagicMock())

    async def _run() -> None:
        with patch(
            "app.projects.draft_delete.get_latest_draft_artifact",
            new=AsyncMock(return_value=None),
        ):
            storage_keys, latest = await delete_project_draft(
                mock_session, project=_project(), draft_id=DRAFT_ID
            )

        assert storage_keys == ["demo/PMP.md"]
        assert latest is None
        mock_session.delete.assert_any_await(current)
        mock_session.delete.assert_any_await(previous)
        mock_session.commit.assert_awaited_once()

    run_async(_run())


def test_delete_project_draft_clears_workspace_file_locks(
    mock_session: AsyncMock,
) -> None:
    draft = SimpleNamespace(
        id=DRAFT_ID,
        project_id=PROJECT_ID,
        workflow_type="create_pmp",
        workspace_path="04-projects/demo/00-brief-pmp/PMP.md",
    )
    workspace_file = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_path=draft.workspace_path,
        storage_key="demo/PMP.md",
    )

    mock_session.get = AsyncMock(return_value=draft)
    mock_session.scalars = AsyncMock(
        side_effect=[
            _scalars([draft]),
            _scalars([]),
            _scalars([workspace_file]),
            _scalars([]),
        ]
    )
    mock_session.execute = AsyncMock(return_value=MagicMock())

    async def _run() -> None:
        with patch(
            "app.projects.draft_delete.get_latest_draft_artifact",
            new=AsyncMock(return_value=None),
        ):
            await delete_project_draft(
                mock_session, project=_project(), draft_id=DRAFT_ID
            )

        executed = [str(call.args[0]) for call in mock_session.execute.await_args_list]
        assert any("project_document_selection_items" in sql for sql in executed)
        assert any("workflow_input_retention_locks" in sql for sql in executed)

    run_async(_run())
