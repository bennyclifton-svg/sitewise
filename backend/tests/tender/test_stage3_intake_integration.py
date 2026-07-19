import os
import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.project import Project
from app.database.user import User
from app.database.workspace_file import WorkspaceFile
from app.projects.document_selections import replace_selection
from app.schemas.document_selections import QuoteCandidateInput
from tender.models import TenderComparison, TenderDocument, TenderJob, TenderQuote
from tender.schemas import TenderIntakeRequest
from tender.services.intake import TenderIdempotencyConflict, TenderIntakeNotReady, create_immutable_intake
from tests.conftest import run_async


@pytest.mark.integration
def test_atomic_intake_rollback_idempotency_and_frozen_inputs() -> None:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if os.environ.get("ALLOW_DESTRUCTIVE_TEST_DATABASE") != "1" or not database_url:
        pytest.skip("requires an explicitly opted-in disposable PostgreSQL database")
    async_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    async def exercise() -> None:
        engine = create_async_engine(async_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        user_id, project_id = uuid.uuid4(), uuid.uuid4()
        file_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        async with factory() as session, session.begin():
            session.add(User(id=user_id, email=f"stage3-{user_id}@example.com"))
            session.add(Project(
                id=project_id, owner_user_id=user_id, slug=f"stage3-{project_id}", title="Stage 3",
                workspace_path=f"projects/{project_id}", phase="procurement", building_class="residential",
                work_type="refurb", state="NSW", status="active",
                project_metadata={"taxonomy": {"subclasses": ["house"], "scale": {"storeys": 2, "gfa_sqm": 240}}},
            ))
            for position, file_id in enumerate(file_ids):
                session.add(WorkspaceFile(
                    id=file_id, project_id=project_id, workspace_path=f"quotes/{position}.pdf",
                    filename=f"{position}.pdf", storage_bucket="project-files",
                    storage_key=f"{project_id}/quotes/{position}.pdf", content_hash=str(position) * 64,
                    size_bytes=100 + position, ingest_status="complete",
                ))
        async with factory() as session, session.begin():
            selection = await replace_selection(
                session, project_id=project_id, selected_by=user_id, expected_revision=0,
                quote_candidates=[
                    QuoteCandidateInput(builder_name="Builder A", ordered_workspace_file_ids=file_ids[:2]),
                    QuoteCandidateInput(builder_name="Builder B", ordered_workspace_file_ids=file_ids[2:]),
                ], actor_source="user",
            )

        base = dict(project_id=project_id, expected_profile_revision=1, expected_selection_revision=selection.revision, turn_id=str(uuid.uuid4()))
        async with factory() as session:
            with pytest.raises(TenderIntakeNotReady):
                async with session.begin():
                    await create_immutable_intake(
                        session, request=TenderIntakeRequest(**base, context_overrides={"region": "metro"}), owner_user_id=user_id,
                    )
        async with factory() as session:
            assert await session.scalar(select(func.count()).select_from(TenderComparison).where(TenderComparison.project_id == project_id)) == 0

        request = TenderIntakeRequest(**base, context_overrides={"region": "metro", "spec_level": "mid"})
        async with factory() as session, session.begin():
            created = await create_immutable_intake(session, request=request, owner_user_id=user_id)
            comparison_id = created.comparison.id
        async with factory() as session, session.begin():
            advanced = await replace_selection(
                session, project_id=project_id, selected_by=user_id,
                expected_revision=selection.revision,
                quote_candidates=[
                    QuoteCandidateInput(builder_name="Builder B", ordered_workspace_file_ids=file_ids[2:]),
                    QuoteCandidateInput(builder_name="Builder A", ordered_workspace_file_ids=file_ids[:2]),
                ], actor_source="user",
            )
            assert advanced.revision == selection.revision + 1
        async with factory() as session, session.begin():
            replay = await create_immutable_intake(session, request=request, owner_user_id=user_id)
            assert replay.idempotent_replay is True
            assert replay.comparison.id == comparison_id
        async with factory() as session:
            assert await session.scalar(select(func.count()).select_from(TenderQuote).where(TenderQuote.comparison_id == comparison_id)) == 2
            assert await session.scalar(select(func.count()).select_from(TenderDocument).join(TenderQuote).where(TenderQuote.comparison_id == comparison_id)) == 3
            assert await session.scalar(select(func.count()).select_from(TenderJob).where(TenderJob.comparison_id == comparison_id)) == 3
            frozen = (await session.execute(select(TenderDocument).join(TenderQuote).where(TenderQuote.comparison_id == comparison_id).order_by(TenderDocument.quote_group_position, TenderDocument.input_position))).scalars().all()
            assert [row.content_hash for row in frozen] == ["0" * 64, "1" * 64, "2" * 64]
            assert all(row.storage_version == row.content_hash for row in frozen)
        async with factory() as session:
            with pytest.raises(TenderIdempotencyConflict):
                async with session.begin():
                    await create_immutable_intake(
                        session,
                        request=request.model_copy(update={"context_overrides": {"region": "regional", "spec_level": "mid"}}),
                        owner_user_id=user_id,
                    )
        await engine.dispose()

    run_async(exercise())
