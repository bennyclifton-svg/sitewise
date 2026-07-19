import uuid

import pytest
from sqlalchemy import func, select

from app.database.document_chunk import DocumentChunk
from app.database.session import get_session_factory
from app.database.source_document import SourceDocument
from app.retrieval import queries
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters
from tests.conftest import run_async


@pytest.fixture
def session_factory():
    return get_session_factory()


async def _has_seeded_chunks(session, filters: RetrievalFilters) -> bool:
    stmt = (
        select(func.count(DocumentChunk.id))
        .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
    )
    stmt = queries.apply_document_filters(stmt, filters)
    return (await session.scalar(stmt)) > 0


async def _skip_if_corpus_missing(
    session,
    filters: RetrievalFilters,
    corpus_name: str,
) -> None:
    if not await _has_seeded_chunks(session, filters):
        pytest.skip(f"{corpus_name} chunks are not seeded in this database")


async def _project_id_for_slug(session, slug: str) -> uuid.UUID:
    result = await session.scalars(
        select(SourceDocument.project_id)
        .where(SourceDocument.project == slug, SourceDocument.project_id.is_not(None))
        .distinct()
    )
    project_ids = list(result.all())
    if len(project_ids) != 1:
        pytest.skip(f"{slug} does not resolve to one UUID-scoped corpus project")
    return project_ids[0]


@pytest.mark.integration
def test_pure_catalog_question(session_factory) -> None:
    async def _run_query() -> None:
        async with session_factory() as session:
            from app.chat.orchestrator import run_chat_turn

            answer = await run_chat_turn(
                session,
                user_id=uuid.uuid4(),
                thread_id=uuid.uuid4(),
                user_text="hello, what projects are you aware of?",
            )
            assert answer.evidence_sufficient
            assert answer.citations
            assert "procurement-blockb" in answer.answer or "delivery-house" in answer.answer

    run_async(_run_query())


@pytest.mark.integration
def test_blockb_evaluation_criteria(session_factory) -> None:
    async def _run_query() -> None:
        async with session_factory() as session:
            filters = RetrievalFilters(
                project_id=await _project_id_for_slug(session, "procurement-blockb"),
                procurement_stage="evaluation",
            )
            await _skip_if_corpus_missing(
                session,
                filters,
                "procurement-blockb evaluation",
            )
            retriever = DocumentRetriever(session)
            results = await retriever.retrieve(
                "What are the Block B tender evaluation criteria?",
                filters=filters,
                include_neighbours=False,
            )
            assert results, "Expected evaluation chunks for procurement-blockb"
            assert all(r.project == "procurement-blockb" for r in results)
            assert all(
                (r.document_metadata or {}).get("procurement_stage") == "evaluation"
                for r in results
            )

    run_async(_run_query())


@pytest.mark.integration
def test_blockb_trr_recommendation(session_factory) -> None:
    async def _run_query() -> None:
        async with session_factory() as session:
            filters = RetrievalFilters(
                project_id=await _project_id_for_slug(session, "procurement-blockb"),
                procurement_stage="trr",
            )
            await _skip_if_corpus_missing(
                session,
                filters,
                "procurement-blockb TRR",
            )
            retriever = DocumentRetriever(session)
            results = await retriever.retrieve(
                "What does the Block B TRR recommend and why?",
                filters=filters,
                include_neighbours=False,
            )
            assert results, "Expected TRR chunks for procurement-blockb"
            assert any("trr" in r.relative_path.lower() for r in results)

    run_async(_run_query())


@pytest.mark.integration
def test_seed_defects_dlp(session_factory) -> None:
    async def _run_query() -> None:
        async with session_factory() as session:
            filters = RetrievalFilters(source_type="reference")
            await _skip_if_corpus_missing(session, filters, "reference")
            retriever = DocumentRetriever(session)
            results = await retriever.retrieve(
                "What does the seed guide say about defects during DLP?",
                filters=filters,
                include_neighbours=False,
            )
            assert results, "Expected seed reference chunks"
            assert all(r.source_type == "reference" for r in results)

    run_async(_run_query())


@pytest.mark.integration
def test_doctrine_progress_certification(session_factory) -> None:
    async def _run_query() -> None:
        async with session_factory() as session:
            filters = RetrievalFilters(source_type="doctrine")
            await _skip_if_corpus_missing(session, filters, "doctrine")
            retriever = DocumentRetriever(session)
            results = await retriever.retrieve(
                "What does doctrine say about certifying progress without inspection?",
                filters=filters,
                include_neighbours=False,
            )
            assert results, "Expected doctrine chunks"
            assert all(r.source_type == "doctrine" for r in results)

    run_async(_run_query())


@pytest.mark.integration
def test_read_chunk_by_id(session_factory) -> None:
    async def _run_query() -> None:
        async with session_factory() as session:
            filters = RetrievalFilters(
                project_id=await _project_id_for_slug(session, "procurement-blockb")
            )
            await _skip_if_corpus_missing(
                session,
                filters,
                "procurement-blockb",
            )
            retriever = DocumentRetriever(session)
            sample = await retriever.retrieve(
                "tender evaluation",
                filters=filters,
                limit=1,
                include_neighbours=False,
            )
            assert sample
            loaded = await retriever.read_chunk(sample[0].chunk_id, filters=filters)
            assert loaded is not None
            assert loaded.chunk_id == sample[0].chunk_id
            assert loaded.content == sample[0].content

    run_async(_run_query())
