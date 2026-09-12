import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.projects.artefact_revisions import set_export_result_for_path
from tests.conftest import run_async


@pytest.mark.parametrize("error", [None, "Upload failed"])
def test_export_status_write_returns_updated_attempt_for_completion_event(error):
    revision = SimpleNamespace(id=uuid.uuid4())
    job = SimpleNamespace(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        draft_id=revision.id,
        revision=2,
        export_type="workbook",
        attempt_count=3,
        status="failed" if error else "ready",
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = job
    session = AsyncMock()
    session.execute.return_value = result
    with patch(
        "app.projects.artefact_revisions.publish_project_event", new=AsyncMock()
    ) as publish:
        returned = run_async(
            set_export_result_for_path(
                session,
                revision=revision,
                workspace_path="cost-v2.xlsx",
                content_hash="hash",
                error=error,
            )
        )
    assert returned is job
    statement = session.execute.await_args.args[0]
    assert statement.is_update
    assert "RETURNING" in str(statement)
    assert statement.get_execution_options()["populate_existing"]
    assert publish.await_args.kwargs["action"] == f"export_{job.status}"
    assert (
        publish.await_args.kwargs["deduplication_key"]
        == f"artefact-export:{job.id}:3:{job.status}"
    )
    session.execute.assert_awaited_once()
    session.flush.assert_not_awaited()


def test_missing_export_does_not_publish_completion():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    with patch(
        "app.projects.artefact_revisions.publish_project_event", new=AsyncMock()
    ) as publish:
        assert (
            run_async(
                set_export_result_for_path(
                    session,
                    revision=SimpleNamespace(id=uuid.uuid4()),
                    workspace_path="missing.xlsx",
                )
            )
            is None
        )
    publish.assert_not_awaited()
