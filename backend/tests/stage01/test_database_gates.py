from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.projects import _list_project_evidence_previews
from app.billing.usage import (
    require_active_mutation_turn,
    reserve_agent_turn,
    revoke_agent_turn,
)
from app.config import settings
from app.database.agent_turn import AgentTurn
from app.database.source_document import SourceDocument
from app.mcp_bridge.server import _load_project_source_document
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters
from app.retrieval.queries import apply_document_filters
from app.workflows.create_cost_plan import load_cost_project_evidence_documents
from app.workflows.create_pmp import load_project_evidence_whole_documents
from ingest.ids import document_id
from ingest.extractors.base import ExtractedDocument
from ingest.persist import upsert_document
from ingest.types import Classification, IngestPlan, ManifestEntry, ProjectContext
from scripts.audit_evidence_identity import audit_evidence_identity
from scripts.repair_evidence_identity import repair_evidence_identity
from tests.tender.test_migrations import (
    DESTRUCTIVE_OPT_IN,
    _alembic_config,
    require_destructive_test_database_url,
)

pytestmark = pytest.mark.integration

P1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
P2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
U1 = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
U2 = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
T1 = uuid.UUID("31111111-1111-1111-1111-111111111111")
T2 = uuid.UUID("32222222-2222-2222-2222-222222222222")
SHARED_DOCUMENT = uuid.UUID("41111111-1111-1111-1111-111111111111")
SINGLE_DOCUMENT = uuid.UUID("42222222-2222-2222-2222-222222222222")
PLATFORM_DOCUMENT = uuid.UUID("43333333-3333-3333-3333-333333333333")
PROJECTLESS_REFERENCE = uuid.UUID("44444444-4444-4444-4444-444444444444")
SHARED_CHUNK = uuid.UUID("51111111-1111-1111-1111-111111111111")
SHARED_PATH = "04-projects/shared/quote.pdf"


def _test_url() -> str:
    return require_destructive_test_database_url(
        application_url=settings.database_url,
        test_url=os.environ.get("TEST_DATABASE_URL"),
        opted_in=os.environ.get(DESTRUCTIVE_OPT_IN) == "1",
    )


def _sync_url(url: str) -> str:
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


def _async_url(url: str) -> str:
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


def _run_migration(revision: str, *, downgrade: bool = False) -> None:
    original = settings.database_url
    settings.database_url = _test_url()
    try:
        operation = command.downgrade if downgrade else command.upgrade
        operation(_alembic_config(), revision)
    finally:
        settings.database_url = original


def _reset_to_pre_expand(engine: sa.Engine) -> None:
    tables = sa.inspect(engine).get_table_names()
    if "alembic_version" not in tables:
        _run_migration("020_tender_extract_cache")
    else:
        with engine.connect() as connection:
            current = connection.scalar(text("SELECT version_num FROM alembic_version"))
        if current != "020_tender_extract_cache":
            _clear_fixture_rows(engine)
            _run_migration("020_tender_extract_cache", downgrade=True)

    _clear_fixture_rows(engine)


def _clear_fixture_rows(engine: sa.Engine) -> None:
    existing = set(sa.inspect(engine).get_table_names())
    with engine.begin() as connection:
        for table in (
            "agent_turns",
            "message_citations",
            "chat_messages",
            "chat_threads",
            "workspace_files",
            "document_chunks",
            "source_documents",
            "projects",
            "users",
        ):
            if table in existing:
                connection.execute(text(f"DELETE FROM {table}"))


def _seed_legacy_identity_fixture(engine: sa.Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO users (id, email) VALUES (:u1, 'one@example.test'), (:u2, 'two@example.test')"),
            {"u1": U1, "u2": U2},
        )
        connection.execute(
            text(
                """
                INSERT INTO projects (id, owner_user_id, slug, title, workspace_path, phase, status)
                VALUES
                  (:p1, :u1, 'same-slug', 'One', '04-projects/same-slug', 'procurement', 'active'),
                  (:p2, :u2, 'same-slug', 'Two', '04-projects/same-slug', 'procurement', 'active')
                """
            ),
            {"p1": P1, "p2": P2, "u1": U1, "u2": U2},
        )
        connection.execute(
            text(
                """
                INSERT INTO source_documents
                  (id, project, phase, document_type, document_class, ingest_mode,
                   document_metadata, content_hash, source_type, filename,
                   relative_path, normalized_content)
                VALUES
                  (:shared, 'same-slug', 'procurement', 'quote', 'commercial', 'hosted',
                   '{}'::jsonb, 'shared-hash', 'project_evidence', 'quote.pdf',
                   :shared_path, 'shared historical evidence'),
                  (:single, 'same-slug', 'procurement', 'report', 'commercial', 'hosted',
                   '{}'::jsonb, 'single-hash', 'project_evidence', 'report.pdf',
                   '04-projects/same-slug/report.pdf', 'single owner evidence'),
                  (:platform, 'sitewise-platform', 'reference', 'guide', 'guidance', 'seed',
                   '{"knowledge_scope":"platform"}'::jsonb, 'platform-hash', 'reference',
                   'guide.md', 'sitewise-platform/guide.md', 'platform guidance'),
                  (:projectless, 'legacy-reference', 'reference', 'guide', 'guidance', 'seed',
                   '{}'::jsonb, 'legacy-reference-hash', 'reference', 'legacy.md',
                   'legacy-reference/legacy.md', 'projectless nonplatform reference')
                """
            ),
            {
                "shared": SHARED_DOCUMENT,
                "single": SINGLE_DOCUMENT,
                "platform": PLATFORM_DOCUMENT,
                "projectless": PROJECTLESS_REFERENCE,
                "shared_path": SHARED_PATH,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO document_chunks
                  (id, document_id, chunk_index, page_or_section, content, token_count, chunk_metadata)
                VALUES (:chunk, :document, 0, '1', 'shared historical evidence', 3, '{}'::jsonb)
                """
            ),
            {"chunk": SHARED_CHUNK, "document": SHARED_DOCUMENT},
        )
        connection.execute(
            text(
                """
                INSERT INTO workspace_files
                  (id, project_id, workspace_path, filename, storage_bucket, storage_key,
                   content_hash, size_bytes, ingest_status, source_document_id)
                VALUES
                  (gen_random_uuid(), :p1, :path, 'quote.pdf', 'test', 'one/quote.pdf',
                   'shared-hash', 10, 'ready', :shared),
                  (gen_random_uuid(), :p2, :path, 'quote.pdf', 'test', 'two/quote.pdf',
                   'shared-hash', 10, 'ready', :shared),
                  (gen_random_uuid(), :p1, '04-projects/same-slug/report.pdf', 'report.pdf',
                   'test', 'one/report.pdf', 'single-hash', 10, 'ready', :single)
                """
            ),
            {"p1": P1, "p2": P2, "path": SHARED_PATH, "shared": SHARED_DOCUMENT, "single": SINGLE_DOCUMENT},
        )
        connection.execute(
            text(
                """
                INSERT INTO chat_threads (id, user_id, project_id, title)
                VALUES (:t1, :u1, :p1, 'One'), (:t2, :u2, :p2, 'Two')
                """
            ),
            {"t1": T1, "t2": T2, "u1": U1, "u2": U2, "p1": P1, "p2": P2},
        )
        connection.execute(
            text(
                """
                INSERT INTO chat_messages (id, thread_id, role, content)
                VALUES
                  ('61111111-1111-1111-1111-111111111111', :t1, 'assistant', 'one'),
                  ('62222222-2222-2222-2222-222222222222', :t2, 'assistant', 'two')
                """
            ),
            {"t1": T1, "t2": T2},
        )
        connection.execute(
            text(
                """
                INSERT INTO message_citations (id, message_id, chunk_id, document_id, excerpt)
                VALUES
                  (gen_random_uuid(), '61111111-1111-1111-1111-111111111111', :chunk, :document, 'one'),
                  (gen_random_uuid(), '62222222-2222-2222-2222-222222222222', :chunk, :document, 'two')
                """
            ),
            {"chunk": SHARED_CHUNK, "document": SHARED_DOCUMENT},
        )


async def _exercise_async_gates(url: str) -> None:
    engine = create_async_engine(_async_url(url), pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            expanded_audit = await audit_evidence_identity(session)
            assert expanded_audit.ambiguous_owner_rows == 1
            assert expanded_audit.platform_owner_violations == 0
            dry_run = await repair_evidence_identity(session, apply=False)
            assert dry_run == {
                "shared_documents": 1,
                "project_copies": 1,
                "workspace_files_repointed": 0,
                "citations_repointed": 0,
            }
            await session.rollback()

        async with factory() as session:
            applied = await repair_evidence_identity(session, apply=True)
            assert applied["project_copies"] == 1
            assert applied["workspace_files_repointed"] == 1
            assert applied["citations_repointed"] == 1
            await session.commit()

        async with factory() as session:
            assert (await repair_evidence_identity(session, apply=True))["shared_documents"] == 0
            await session.commit()
    finally:
        await engine.dispose()


async def _assert_read_isolation_and_races(url: str) -> None:
    engine = create_async_engine(_async_url(url), pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    p2_document = document_id(SHARED_PATH, project_id=P2)
    try:
        async with factory() as session:
            previews = await _list_project_evidence_previews(
                session, project_id=P1, workspace_paths={SHARED_PATH}
            )
            assert {row.id for row in previews} == {SHARED_DOCUMENT, SINGLE_DOCUMENT}
            assert p2_document not in {row.id for row in previews}
            assert await _load_project_source_document(
                session, project_id=P1, document_id=p2_document
            ) is None
            assert (
                await _load_project_source_document(
                    session, project_id=P1, document_id=SHARED_DOCUMENT
                )
            ).project_id == P1

            retriever = DocumentRetriever(session)
            passages = await retriever.retrieve(
                "shared historical evidence",
                filters=RetrievalFilters(active_project_id=P1),
                include_neighbours=False,
            )
            assert passages and {row.project_id for row in passages} == {P1}

            platform_ids = set(
                (
                    await session.scalars(
                        apply_document_filters(
                            select(SourceDocument.id),
                            RetrievalFilters(platform_knowledge_only=True),
                        )
                    )
                ).all()
            )
            assert PLATFORM_DOCUMENT in platform_ids
            assert PROJECTLESS_REFERENCE not in platform_ids

            pmp_documents = await load_project_evidence_whole_documents(
                session, project_id=P1, relative_paths=[SHARED_PATH]
            )
            cost_documents = await load_cost_project_evidence_documents(
                session,
                project_id=P1,
                semantic_relative_paths=[SHARED_PATH],
                marker_paths=[],
            )
            assert {row.document_id for row in pmp_documents} == {SHARED_DOCUMENT}
            assert {row.document_id for row in cost_documents} == {SHARED_DOCUMENT}

            citation_projects = (
                await session.execute(
                    text(
                        """
                        SELECT thread.project_id, citation.document_id, chunk.document_id
                        FROM message_citations citation
                        JOIN chat_messages message ON message.id = citation.message_id
                        JOIN chat_threads thread ON thread.id = message.thread_id
                        JOIN document_chunks chunk ON chunk.id = citation.chunk_id
                        ORDER BY thread.project_id
                        """
                    )
                )
            ).all()
            assert citation_projects == [
                (P1, SHARED_DOCUMENT, SHARED_DOCUMENT),
                (P2, p2_document, p2_document),
            ]

        original_quota = settings.agent_monthly_turn_quota
        settings.agent_monthly_turn_quota = 1
        try:
            async def reserve(message_id: str) -> bool:
                async with factory() as session:
                    try:
                        await reserve_agent_turn(
                            session,
                            turn_id=uuid.uuid4(),
                            project_id=P1,
                            user_id=U1,
                            thread_id=T1,
                            user_message_id=message_id,
                            runtime="pi",
                            model="test",
                        )
                        await session.commit()
                        return True
                    except Exception:
                        await session.rollback()
                        return False

            assert sum(await asyncio.gather(reserve("race-a"), reserve("race-b"))) == 1
        finally:
            settings.agent_monthly_turn_quota = original_quota

        turn_id = uuid.uuid4()
        async with factory() as session:
            turn = AgentTurn(
                id=turn_id,
                project_id=P1,
                user_id=U1,
                thread_id=T1,
                user_message_id="revoke-race",
                state="active",
                runtime="pi",
                model="test",
                status="reserved",
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
            session.add(turn)
            await session.commit()

        revoked = asyncio.Event()

        async def revoke_first() -> None:
            async with factory() as session:
                assert await revoke_agent_turn(session, turn_id)
                revoked.set()
                await asyncio.sleep(0.1)
                await session.commit()

        async def mutation_after_revoke_started() -> bool:
            await revoked.wait()
            async with factory() as session:
                try:
                    await require_active_mutation_turn(
                        session, turn_id=turn_id, project_id=P1, user_id=U1
                    )
                except PermissionError:
                    return False
                return True

        _, mutation_allowed = await asyncio.gather(
            revoke_first(), mutation_after_revoke_started()
        )
        assert mutation_allowed is False

        # A fresh session represents a restarted API or worker process.
        async with factory() as restarted_session:
            with pytest.raises(PermissionError):
                await require_active_mutation_turn(
                    restarted_session, turn_id=turn_id, project_id=P1, user_id=U1
                )
    finally:
        await engine.dispose()


def test_stage_0_and_stage_1_database_acceptance() -> None:
    url = _test_url()
    engine = sa.create_engine(_sync_url(url))
    try:
        _reset_to_pre_expand(engine)
        _seed_legacy_identity_fixture(engine)

        async def pre_expand_audit() -> None:
            async_engine = create_async_engine(_async_url(url))
            try:
                async with async_sessionmaker(async_engine)() as session:
                    audit = await audit_evidence_identity(session)
                    assert audit.ambiguous_owner_rows == 1
                    assert audit.single_owner_rows == 1
                    assert audit.platform_rows == 1
            finally:
                await async_engine.dispose()

        asyncio.run(pre_expand_audit())
        _run_migration("021_source_document_uuid_expand")

        with engine.connect() as connection:
            rows = dict(
                connection.execute(
                    text("SELECT id, project_id FROM source_documents")
                ).all()
            )
            assert rows[SHARED_DOCUMENT] is None
            assert rows[SINGLE_DOCUMENT] == P1
            assert rows[PLATFORM_DOCUMENT] is None
            assert rows[PROJECTLESS_REFERENCE] is None

        _run_migration("021b_source_doc_path_contract")
        asyncio.run(_exercise_async_gates(url))
        _run_migration("head")

        plan = IngestPlan(
            entry=ManifestEntry(
                absolute_path=Path("quote.pdf"),
                relative_path=SHARED_PATH,
                project="same-slug",
                filename="quote.pdf",
                extension=".pdf",
                size_bytes=10,
            ),
            context=ProjectContext(
                project="same-slug",
                phase="procurement",
                source_type="project_evidence",
                project_id=P1,
            ),
            classification=Classification(
                document_class="tender_submission",
                ingest_mode="full_text",
            ),
            extractor="test",
            chunker="test",
        )
        extracted = ExtractedDocument(normalized_content="reingested evidence")
        with sa.orm.Session(engine) as session:
            first_id = upsert_document(session, plan, extracted, "reingested-hash")
            second_id = upsert_document(session, plan, extracted, "reingested-hash")
            session.commit()
        assert first_id == second_id == SHARED_DOCUMENT

        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO source_documents
                          (id, project_id, project, phase, document_type, document_class,
                           ingest_mode, document_metadata, content_hash, source_type,
                           filename, relative_path, normalized_content)
                        VALUES
                          (:id, :project_id, 'same-slug', 'procurement', 'quote', 'commercial',
                           'hosted', '{}'::jsonb, 'duplicate', 'project_evidence',
                           'quote.pdf', :path, 'duplicate')
                        """
                    ),
                    {"id": uuid.uuid4(), "project_id": P1, "path": SHARED_PATH},
                )

        # Contract and durable-turn schema can roll back while the expanded UUID
        # schema and project-scoped path contract remain. The path-contract
        # downgrade must refuse once repaired projects legitimately share a path.
        _run_migration("021b_source_doc_path_contract", downgrade=True)
        with pytest.raises(Exception, match="global relative_path uniqueness"):
            _run_migration("021_source_document_uuid_expand", downgrade=True)
        _run_migration("head")
    finally:
        engine.dispose()

    asyncio.run(_assert_read_isolation_and_races(url))
