from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from alembic import command
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.database.project import Project
from app.database.project_event import ProjectEvent
from app.database.user import User
from app.projects.events import publish_project_event
from app.projects.profile import apply_profile_patch
from app.schemas.projects import ProjectProfilePatch
from tests.tender.test_migrations import (
    DESTRUCTIVE_OPT_IN,
    _alembic_config,
    require_destructive_test_database_url,
)

pytestmark = pytest.mark.integration


def _test_url() -> str:
    return require_destructive_test_database_url(
        application_url=settings.database_url,
        test_url=os.environ.get("TEST_DATABASE_URL"),
        opted_in=os.environ.get(DESTRUCTIVE_OPT_IN) == "1",
    )


def _upgrade_head() -> None:
    original = settings.database_url
    settings.database_url = _test_url()
    try:
        command.upgrade(_alembic_config(), "head")
    finally:
        settings.database_url = original


def test_project_event_outbox_is_atomic_ordered_and_deduplicated() -> None:
    _upgrade_head()
    asyncio.run(_exercise_project_event_outbox())


async def _exercise_project_event_outbox() -> None:
    engine = create_async_engine(
        _test_url().replace("postgresql://", "postgresql+psycopg://", 1)
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    try:
        async with factory.begin() as session:
            session.add(User(id=user_id, email=f"events-{user_id}@example.com"))
            session.add(
                Project(
                    id=project_id,
                    owner_user_id=user_id,
                    slug=f"events-{project_id}",
                    title="Event integration fixture",
                    workspace_path=f"04-projects/events-{project_id}",
                    phase="brief-planning",
                    archetype=None,
                    building_class="residential",
                    work_type="new",
                    user_role="architect-pm",
                    state="NSW",
                    profile_revision=1,
                    event_sequence=0,
                    status="active",
                    project_metadata={"taxonomy": {"subclasses": ["house"]}},
                )
            )

        rollback_session = factory()
        await rollback_session.begin()
        project = await rollback_session.get(Project, project_id)
        assert project is not None
        await apply_profile_patch(
            rollback_session,
            project=project,
            patch=ProjectProfilePatch(expected_revision=1, state="VIC"),
            actor_source="user",
        )
        await rollback_session.rollback()
        await rollback_session.close()

        async with factory() as session:
            project = await session.get(Project, project_id)
            assert project is not None
            assert project.state == "NSW"
            assert project.profile_revision == 1
            assert project.event_sequence == 0
            assert await session.scalar(
                select(func.count(ProjectEvent.id)).where(
                    ProjectEvent.project_id == project_id
                )
            ) == 0

        async def produce_duplicate() -> tuple[uuid.UUID, int]:
            async with factory.begin() as session:
                event = await publish_project_event(
                    session,
                    project_id=project_id,
                    actor_source="worker",
                    resource_type="workflow_run",
                    resource_id="run-1",
                    resource_revision=1,
                    action="completed",
                    payload={"status": "complete"},
                    deduplication_key="workflow:run-1:complete",
                )
                return event.id, event.sequence

        duplicate_results = await asyncio.gather(
            produce_duplicate(),
            produce_duplicate(),
        )
        assert duplicate_results[0] == duplicate_results[1]

        async with factory() as session:
            events = list(
                (
                    await session.scalars(
                        select(ProjectEvent)
                        .where(ProjectEvent.project_id == project_id)
                        .order_by(ProjectEvent.sequence)
                    )
                ).all()
            )
            assert [event.sequence for event in events] == [1]
            project = await session.get(Project, project_id)
            assert project is not None
            assert project.event_sequence == 1
    finally:
        async with factory.begin() as session:
            await session.execute(delete(User).where(User.id == user_id))
        await engine.dispose()
