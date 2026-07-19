from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from alembic import command
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.database.project import Project
from app.database.user import User
from app.projects.profile import apply_profile_patch
from app.projects.profile_proposals import (
    ProfileProposalRevisionConflict,
    accept_profile_proposal,
    list_profile_proposals,
    propose_project_profile_change,
    reject_profile_proposal,
)
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


def test_profile_proposals_survive_reload_and_enforce_profile_revision() -> None:
    original = settings.database_url
    settings.database_url = _test_url()
    try:
        command.upgrade(_alembic_config(), "head")
    finally:
        settings.database_url = original
    asyncio.run(_exercise_profile_proposals())


async def _exercise_profile_proposals() -> None:
    engine = create_async_engine(
        _test_url().replace("postgresql://", "postgresql+psycopg://", 1)
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    evidence_id = uuid.uuid4()
    try:
        async with factory.begin() as session:
            session.add(User(id=user_id, email=f"proposals-{user_id}@example.com"))
            session.add(
                Project(
                    id=project_id,
                    owner_user_id=user_id,
                    slug=f"proposals-{project_id}",
                    title="Proposal integration fixture",
                    workspace_path=f"04-projects/proposals-{project_id}",
                    phase="brief-planning",
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

        async with factory.begin() as session:
            project = await session.get(Project, project_id)
            assert project is not None
            pending = await propose_project_profile_change(
                session,
                project=project,
                proposed_values={"state": "VIC"},
                evidence_references=[
                    {
                        "source_document_id": evidence_id,
                        "locator": "page 2",
                        "claim": "Victorian site address",
                    }
                ],
                confidence=0.92,
                proposer="agent",
            )

        async with factory.begin() as session:
            reloaded = await list_profile_proposals(
                session, project_id=project_id, state="pending"
            )
            assert reloaded[0].id == pending.id
            assert reloaded[0].evidence_references[0].source_document_id == evidence_id
            project = await session.get(Project, project_id)
            assert project is not None
            accepted = await accept_profile_proposal(
                session,
                project=project,
                proposal_id=pending.id,
                expected_profile_revision=1,
                actor_source="user",
            )
            assert accepted.profile_change is not None
            assert accepted.profile_change.new_revision == 2

        async with factory.begin() as session:
            project = await session.get(Project, project_id)
            assert project is not None
            assert project.state == "VIC"
            stale = await propose_project_profile_change(
                session,
                project=project,
                proposed_values={"state": "QLD"},
                evidence_references=[],
                confidence=0.5,
                proposer="agent",
            )
            await apply_profile_patch(
                session,
                project=project,
                patch=ProjectProfilePatch(expected_revision=2, state="SA"),
                actor_source="user",
            )

        async with factory() as session:
            project = await session.get(Project, project_id)
            assert project is not None
            with pytest.raises(ProfileProposalRevisionConflict):
                await accept_profile_proposal(
                    session,
                    project=project,
                    proposal_id=stale.id,
                    expected_profile_revision=3,
                    actor_source="user",
                )
            await session.rollback()

        async with factory.begin() as session:
            project = await session.get(Project, project_id)
            assert project is not None
            rejected = await propose_project_profile_change(
                session,
                project=project,
                proposed_values={"state": "WA"},
                evidence_references=[],
                confidence=None,
                proposer="agent",
            )
            await reject_profile_proposal(
                session,
                project=project,
                proposal_id=rejected.id,
                expected_profile_revision=3,
                actor_source="user",
            )

        async with factory() as session:
            rejected_rows = await list_profile_proposals(
                session, project_id=project_id, state="rejected"
            )
            assert [row.id for row in rejected_rows] == [rejected.id]
    finally:
        async with factory.begin() as session:
            await session.execute(delete(User).where(User.id == user_id))
        await engine.dispose()
