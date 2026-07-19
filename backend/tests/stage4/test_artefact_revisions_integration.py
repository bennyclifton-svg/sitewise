from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.artefact_export import ArtefactExport
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.database.user import User
from app.projects.artefact_revisions import (
    ArtefactRevisionConflict,
    ExportSpec,
    publish,
    regenerate_exports,
    revise,
    set_export_result,
)
from tests.conftest import run_async


@pytest.mark.integration
def test_concurrent_revision_conflict_and_idempotent_export_retry() -> None:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if os.environ.get("ALLOW_DESTRUCTIVE_TEST_DATABASE") != "1" or not database_url:
        pytest.skip("requires an explicitly opted-in disposable PostgreSQL database")
    async_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    async def exercise() -> None:
        engine = create_async_engine(async_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        user_id, project_id = uuid.uuid4(), uuid.uuid4()
        async with factory() as session, session.begin():
            session.add(User(id=user_id, email=f"stage4-{user_id}@example.com"))
            session.add(
                Project(
                    id=project_id,
                    owner_user_id=user_id,
                    slug=f"stage4-{project_id}",
                    title="Stage 4",
                    workspace_path=f"projects/{project_id}",
                    phase="procurement",
                    state="NSW",
                    status="active",
                    project_metadata={},
                )
            )

        async def first_publish(label: str):
            async with factory() as session:
                async with session.begin():
                    return await publish(
                        session,
                        project_id=project_id,
                        workflow_type="create_pmp",
                        expected_base_version=0,
                        title=label,
                        workspace_path=f"projects/{project_id}/pmp-v1.md",
                        author_user_id=user_id,
                        content_markdown=f"# {label}",
                        model=None,
                        runtime="test",
                        provenance={"fixture": True},
                        actor_source="test",
                        exports=[
                            ExportSpec(
                                "markdown",
                                f"projects/{project_id}/pmp-v1.md",
                                f"{project_id}/pmp-v1.md",
                            )
                        ],
                    )

        results = await asyncio.gather(
            first_publish("one"), first_publish("two"), return_exceptions=True
        )
        successes = [item for item in results if not isinstance(item, Exception)]
        conflicts = [item for item in results if isinstance(item, ArtefactRevisionConflict)]
        assert len(successes) == 1
        assert len(conflicts) == 1
        first = successes[0]
        assert first.revision.version == 1

        async with factory() as session, session.begin():
            persisted_first = await session.get(DraftArtifact, first.revision.id)
            assert persisted_first is not None
            first_job = (
                await session.execute(
                    select(ArtefactExport).where(
                        ArtefactExport.draft_id == persisted_first.id
                    )
                )
            ).scalar_one()
            await set_export_result(session, job=first_job, content_hash="a" * 64)

        async with factory() as session, session.begin():
            persisted_first = await session.get(DraftArtifact, first.revision.id)
            assert persisted_first is not None
            second = await revise(
                session,
                base_revision=persisted_first,
                expected_base_version=1,
                author_user_id=user_id,
                content_markdown="# revised",
                actor_source="test",
                exports=[
                    ExportSpec(
                        "markdown",
                        f"projects/{project_id}/pmp-v2.md",
                        f"{project_id}/pmp-v2.md",
                    )
                ],
            )
            assert second.revision.version == 2
            second_job = second.export_jobs[0]
            await set_export_result(session, job=second_job, error="storage unavailable")

        async with factory() as session, session.begin():
            second_revision = await session.get(DraftArtifact, second.revision.id)
            assert second_revision is not None
            retried = await regenerate_exports(session, revision=second_revision)
            assert len(retried) == 1
            await set_export_result(session, job=retried[0], content_hash="b" * 64)

        async with factory() as session:
            revisions = await session.scalar(
                select(func.count()).select_from(DraftArtifact).where(
                    DraftArtifact.project_id == project_id,
                    DraftArtifact.workflow_type == "create_pmp",
                )
            )
            jobs = (
                await session.execute(
                    select(ArtefactExport)
                    .where(ArtefactExport.project_id == project_id)
                    .order_by(ArtefactExport.revision)
                )
            ).scalars().all()
            assert revisions == 2
            assert [(job.revision, job.status) for job in jobs] == [
                (1, "ready"),
                (2, "ready"),
            ]
            assert jobs[1].attempt_count == 2
        await engine.dispose()

    run_async(exercise())
