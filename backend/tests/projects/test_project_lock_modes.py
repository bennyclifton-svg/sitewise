import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects.postgresql import dialect

from app.projects.events import publish_project_event
from app.projects.locks import lock_project
from tests.conftest import run_async


@pytest.mark.parametrize("publisher", [False, True], ids=["project-mutation", "event-publication"])
def test_project_writers_remain_exclusive_without_blocking_child_foreign_keys(publisher):
    project = SimpleNamespace(id=uuid.uuid4(), event_sequence=4, project_context_version=2)
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: project)
    if publisher:
        event = run_async(publish_project_event(session, project_id=project.id,
            actor_source="test", resource_type="workspace_file", resource_id="new-file",
            resource_revision=1, action="received"))
        assert event.sequence == 5
    else:
        assert run_async(lock_project(session, project_id=project.id)) is project
    statement = session.execute.await_args_list[0].args[0]
    sql = str(statement.compile(dialect=dialect()))
    assert "FOR NO KEY UPDATE" in sql
    assert statement.get_execution_options()["populate_existing"]
