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
from app.database.project_decision import ProjectDecision
from app.database.project_event import ProjectEvent
from app.database.user import User
from app.projects.events import publish_project_event
from app.projects.profile import apply_profile_patch
from app.projects.project_knowledge import (
    SharedProjectObjectUpdate,
    write_shared_project_object,
)
from app.projects.snapshot import get_project_snapshot
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


def test_project_event_sequence_refreshes_after_concurrent_preload() -> None:
    _upgrade_head()
    asyncio.run(_exercise_concurrent_distinct_event_writes())


def test_project_context_version_serializes_only_context_changes() -> None:
    _upgrade_head()
    asyncio.run(_exercise_concurrent_mixed_event_writes())


def test_shared_project_object_writes_preserve_concurrent_changes() -> None:
    _upgrade_head()
    asyncio.run(_exercise_concurrent_shared_object_writes())


def test_snapshot_retry_refreshes_preloaded_decisions() -> None:
    _upgrade_head()
    asyncio.run(_exercise_snapshot_retry_with_preloaded_decision())


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
                    project_context_version=1,
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
            assert project.project_context_version == 1
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
            assert project.project_context_version == 1
    finally:
        async with factory.begin() as session:
            await session.execute(delete(User).where(User.id == user_id))
        await engine.dispose()


async def _exercise_concurrent_distinct_event_writes() -> None:
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
                    title="Concurrent event fixture",
                    workspace_path=f"04-projects/events-{project_id}",
                    phase="brief-planning",
                    archetype=None,
                    building_class="residential",
                    work_type="new",
                    user_role="architect-pm",
                    state="NSW",
                    profile_revision=1,
                    project_context_version=1,
                    event_sequence=0,
                    status="active",
                    project_metadata={"taxonomy": {"subclasses": ["house"]}},
                )
            )

        barrier = asyncio.Barrier(4)

        async def produce_distinct(index: int) -> int:
            async with factory.begin() as session:
                project = await session.get(Project, project_id)
                assert project is not None
                await barrier.wait()
                event = await publish_project_event(
                    session,
                    project_id=project_id,
                    actor_source="workflow_run",
                    resource_type="workflow_run",
                    resource_id=f"run-{index}",
                    resource_revision=1,
                    action="queued",
                    payload={"index": index},
                    deduplication_key=f"workflow:run-{index}:queued",
                )
                return event.sequence

        sequences = await asyncio.gather(*(produce_distinct(index) for index in range(4)))
        assert sorted(sequences) == [1, 2, 3, 4]

        async with factory() as session:
            project = await session.get(Project, project_id)
            assert project is not None
            assert project.event_sequence == 4
            assert project.project_context_version == 1
    finally:
        async with factory.begin() as session:
            await session.execute(delete(User).where(User.id == user_id))
        await engine.dispose()


async def _exercise_concurrent_mixed_event_writes() -> None:
    engine = create_async_engine(
        _test_url().replace("postgresql://", "postgresql+psycopg://", 1)
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    try:
        async with factory.begin() as session:
            session.add(User(id=user_id, email=f"context-{user_id}@example.com"))
            session.add(
                Project(
                    id=project_id,
                    owner_user_id=user_id,
                    slug=f"context-{project_id}",
                    title="Concurrent context fixture",
                    workspace_path=f"04-projects/context-{project_id}",
                    phase="brief-planning",
                    profile_revision=1,
                    project_context_version=1,
                    event_sequence=0,
                    status="active",
                )
            )

        barrier = asyncio.Barrier(4)

        async def publish(index: int, *, changes_context: bool) -> tuple[int, int]:
            async with factory.begin() as session:
                await barrier.wait()
                event = await publish_project_event(
                    session,
                    project_id=project_id,
                    actor_source="test",
                    resource_type="project_profile"
                    if changes_context
                    else "workflow_run",
                    resource_id=f"resource-{index}",
                    resource_revision=index + 1,
                    action="updated" if changes_context else "queued",
                    changes_context=changes_context,
                )
                project = await session.get(Project, project_id)
                assert project is not None
                return event.sequence, project.project_context_version

        results = await asyncio.gather(
            publish(0, changes_context=True),
            publish(1, changes_context=False),
            publish(2, changes_context=True),
            publish(3, changes_context=False),
        )
        assert sorted(sequence for sequence, _version in results) == [1, 2, 3, 4]

        async with factory() as session:
            project = await session.get(Project, project_id)
            assert project is not None
            assert project.event_sequence == 4
            assert project.project_context_version == 3
    finally:
        async with factory.begin() as session:
            await session.execute(delete(User).where(User.id == user_id))
        await engine.dispose()


async def _exercise_concurrent_shared_object_writes() -> None:
    engine = create_async_engine(
        _test_url().replace("postgresql://", "postgresql+psycopg://", 1)
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    try:
        async with factory.begin() as session:
            session.add(User(id=user_id, email=f"knowledge-{user_id}@example.com"))
            session.add(
                Project(
                    id=project_id,
                    owner_user_id=user_id,
                    slug=f"knowledge-{project_id}",
                    title="Concurrent knowledge fixture",
                    workspace_path=f"04-projects/knowledge-{project_id}",
                    phase="brief-planning",
                    project_context_version=1,
                    event_sequence=0,
                    status="active",
                    project_metadata={},
                )
            )

        barrier = asyncio.Barrier(2)

        async def write(object_id: str) -> None:
            async with factory.begin() as session:
                project = await session.get(Project, project_id)
                assert project is not None
                await barrier.wait()
                await write_shared_project_object(
                    session,
                    project=project,
                    kind="consultant",
                    object_id=object_id,
                    update=SharedProjectObjectUpdate(
                        expected_revision=0,
                        value={"name": object_id.title()},
                    ),
                    source="user",
                )

        await asyncio.gather(write("architect"), write("engineer"))

        async with factory() as session:
            project = await session.get(Project, project_id)
            assert project is not None
            knowledge = project.project_metadata["shared_knowledge"]
            assert set(knowledge) == {
                "consultant:architect",
                "consultant:engineer",
            }
            assert project.event_sequence == 2
            assert project.project_context_version == 3
    finally:
        async with factory.begin() as session:
            await session.execute(delete(User).where(User.id == user_id))
        await engine.dispose()


async def _exercise_snapshot_retry_with_preloaded_decision() -> None:
    engine = create_async_engine(
        _test_url().replace("postgresql://", "postgresql+psycopg://", 1)
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    decision_id = uuid.uuid4()
    try:
        async with factory.begin() as session:
            session.add(User(id=user_id, email=f"snapshot-{user_id}@example.com"))
            session.add(
                Project(
                    id=project_id,
                    owner_user_id=user_id,
                    slug=f"snapshot-{project_id}",
                    title="Snapshot retry fixture",
                    workspace_path=f"04-projects/snapshot-{project_id}",
                    phase="brief-planning",
                    project_context_version=1,
                    event_sequence=0,
                    status="active",
                )
            )
            await session.flush()
            session.add(
                ProjectDecision(
                    id=decision_id,
                    project_id=project_id,
                    decision_id="procurement-route",
                    section="Procurement",
                    label="Procurement route",
                    options=[
                        {"value": "traditional", "label": "Traditional"},
                        {
                            "value": "design_construct",
                            "label": "Design & Construct",
                        },
                    ],
                    selected="traditional",
                    source="agent",
                    revision=1,
                    locked=False,
                    evidence_conflict=False,
                    provenance={},
                    workflow_type="create_pmp",
                )
            )

        async with factory() as reader:
            stale_project = await reader.get(Project, project_id)
            stale_decision = await reader.get(ProjectDecision, decision_id)
            assert stale_project is not None
            assert stale_decision is not None

            async with factory.begin() as writer:
                project = await writer.get(Project, project_id, with_for_update=True)
                decision = await writer.get(
                    ProjectDecision, decision_id, with_for_update=True
                )
                assert project is not None
                assert decision is not None
                decision.selected = "design_construct"
                decision.source = "user"
                decision.revision = 2
                await publish_project_event(
                    writer,
                    locked_project=project,
                    project_id=project_id,
                    actor_source="user",
                    resource_type="project_decision",
                    resource_id="procurement-route",
                    resource_revision=2,
                    action="updated",
                    changes_context=True,
                )

            snapshot = await get_project_snapshot(
                reader,
                project_id=project_id,
                owner_user_id=user_id,
            )

            assert snapshot.context_version == 2
            assert snapshot.decisions.items[0].selected == "design_construct"
            assert snapshot.decisions.items[0].revision == 2
    finally:
        async with factory.begin() as session:
            await session.execute(delete(User).where(User.id == user_id))
        await engine.dispose()
