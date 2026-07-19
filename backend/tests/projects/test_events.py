import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.database.project import Project
from app.database.project_event import ProjectEvent
from app.projects.events import (
    UnsafeProjectEventPayload,
    list_project_events,
    publish_project_event,
)


def _project() -> Project:
    return Project(
        id=uuid.uuid4(),
        owner_user_id=uuid.uuid4(),
        slug="demo",
        title="Demo",
        workspace_path="04-projects/demo",
        phase="brief-planning",
        profile_revision=1,
        event_sequence=0,
        status="active",
    )


def test_publish_project_event_assigns_monotonic_project_sequences() -> None:
    project = _project()
    session = AsyncMock()
    session.add = MagicMock()

    first = asyncio.run(
        publish_project_event(
            session,
            project_id=project.id,
            actor_source="worker",
            resource_type="workflow_run",
            resource_id="run-1",
            resource_revision=1,
            action="completed",
            payload={"status": "complete"},
            locked_project=project,
        )
    )
    second = asyncio.run(
        publish_project_event(
            session,
            project_id=project.id,
            actor_source="worker",
            resource_type="workflow_run",
            resource_id="run-2",
            resource_revision=1,
            action="completed",
            locked_project=project,
        )
    )

    assert (first.sequence, second.sequence) == (1, 2)
    assert project.event_sequence == 2
    assert session.add.call_count == 2
    assert session.flush.await_count == 2


def test_publish_project_event_returns_existing_deduplicated_event() -> None:
    project = _project()
    existing = ProjectEvent(
        project_id=project.id,
        sequence=1,
        actor_source="worker",
        resource_type="workflow_run",
        resource_id="run-1",
        resource_revision=1,
        action="completed",
        payload={},
        deduplication_key="workflow:run-1:complete",
    )
    result = SimpleNamespace(scalar_one_or_none=lambda: existing)
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.return_value = result

    event = asyncio.run(
        publish_project_event(
            session,
            project_id=project.id,
            actor_source="worker",
            resource_type="workflow_run",
            resource_id="run-1",
            resource_revision=1,
            action="completed",
            deduplication_key="workflow:run-1:complete",
            locked_project=project,
        )
    )

    assert event is existing
    assert project.event_sequence == 0
    session.add.assert_not_called()
    session.flush.assert_not_awaited()


def test_publish_project_event_rejects_sensitive_payload_keys() -> None:
    project = _project()
    with pytest.raises(UnsafeProjectEventPayload, match="payload.context.token"):
        asyncio.run(
            publish_project_event(
                AsyncMock(),
                project_id=project.id,
                actor_source="agent",
                resource_type="project_profile",
                resource_id=project.id,
                resource_revision=2,
                action="updated",
                payload={"context": {"token": "do-not-store"}},
                locked_project=project,
            )
        )


def test_list_project_events_returns_cursor_order_from_owned_project_scope() -> None:
    project_id = uuid.uuid4()
    events = [SimpleNamespace(sequence=5), SimpleNamespace(sequence=6)]
    scalars = SimpleNamespace(all=lambda: events)
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(scalars=lambda: scalars)

    result = asyncio.run(
        list_project_events(session, project_id=project_id, after=4, limit=2)
    )

    assert result == events
    statement = session.execute.await_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "project_events.project_id" in compiled
    assert "project_events.sequence > 4" in compiled
    assert "ORDER BY project_events.sequence ASC" in compiled
    assert "LIMIT 2" in compiled
