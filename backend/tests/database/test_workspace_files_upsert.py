import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database import workspace_files as workspace_files_module
from tests.conftest import run_async


PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
RECORD_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def test_upsert_workspace_file_uses_atomic_on_conflict() -> None:
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one.return_value = RECORD_ID
    session.execute = AsyncMock(return_value=execute_result)
    record = MagicMock()
    record.id = RECORD_ID
    session.get = AsyncMock(return_value=record)

    result = run_async(
        workspace_files_module.upsert_workspace_file(
            session,
            project_id=PROJECT_ID,
            workspace_path="04-projects/demo/01-cost/Cost_Plan_v01.draft.xlsx",
            filename="Cost_Plan_v01.draft.xlsx",
            storage_bucket="project-files",
            storage_key="22222222/04-projects/demo/01-cost/Cost_Plan_v01.draft.xlsx",
            content_hash="abc",
            size_bytes=12,
            ingest_status="generated",
        )
    )

    assert result is record
    statement = session.execute.await_args.args[0]
    compiled = str(statement)
    assert "ON CONFLICT" in compiled.upper()
    assert "uq_workspace_files_project_workspace_path" in compiled
    session.get.assert_awaited_once_with(
        workspace_files_module.WorkspaceFile, RECORD_ID
    )


def test_upsert_workspace_file_raises_when_row_missing_after_write() -> None:
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one.return_value = RECORD_ID
    session.execute = AsyncMock(return_value=execute_result)
    session.get = AsyncMock(return_value=None)

    with pytest.raises(RuntimeError, match="did not return a row"):
        run_async(
            workspace_files_module.upsert_workspace_file(
                session,
                project_id=PROJECT_ID,
                workspace_path="04-projects/demo/01-cost/Cost_Plan_v01.draft.xlsx",
                filename="Cost_Plan_v01.draft.xlsx",
                storage_bucket="project-files",
                storage_key="22222222/04-projects/demo/01-cost/Cost_Plan_v01.draft.xlsx",
                content_hash="abc",
                size_bytes=12,
                ingest_status="generated",
            )
        )
