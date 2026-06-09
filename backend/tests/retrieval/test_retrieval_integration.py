import uuid

import pytest

from app.database.session import get_session_factory
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters
from tests.conftest import run_async


@pytest.fixture
def session_factory():
    return get_session_factory()


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
            retriever = DocumentRetriever(session)
            results = await retriever.retrieve(
                "What are the Block B tender evaluation criteria?",
                filters=RetrievalFilters(
                    project="procurement-blockb",
                    procurement_stage="evaluation",
                ),
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
            retriever = DocumentRetriever(session)
            results = await retriever.retrieve(
                "What does the Block B TRR recommend and why?",
                filters=RetrievalFilters(
                    project="procurement-blockb",
                    procurement_stage="trr",
                ),
                include_neighbours=False,
            )
            assert results, "Expected TRR chunks for procurement-blockb"
            assert any("trr" in r.relative_path.lower() for r in results)

    run_async(_run_query())


@pytest.mark.integration
def test_seed_defects_dlp(session_factory) -> None:
    async def _run_query() -> None:
        async with session_factory() as session:
            retriever = DocumentRetriever(session)
            results = await retriever.retrieve(
                "What does the seed guide say about defects during DLP?",
                filters=RetrievalFilters(source_type="reference"),
                include_neighbours=False,
            )
            assert results, "Expected seed reference chunks"
            assert all(r.source_type == "reference" for r in results)

    run_async(_run_query())


@pytest.mark.integration
def test_doctrine_progress_certification(session_factory) -> None:
    async def _run_query() -> None:
        async with session_factory() as session:
            retriever = DocumentRetriever(session)
            results = await retriever.retrieve(
                "What does doctrine say about certifying progress without inspection?",
                filters=RetrievalFilters(source_type="doctrine"),
                include_neighbours=False,
            )
            assert results, "Expected doctrine chunks"
            assert all(r.source_type == "doctrine" for r in results)

    run_async(_run_query())


@pytest.mark.integration
def test_read_chunk_by_id(session_factory) -> None:
    async def _run_query() -> None:
        async with session_factory() as session:
            retriever = DocumentRetriever(session)
            sample = await retriever.retrieve(
                "tender evaluation",
                filters=RetrievalFilters(project="procurement-blockb"),
                limit=1,
                include_neighbours=False,
            )
            assert sample
            loaded = await retriever.read_chunk(sample[0].chunk_id)
            assert loaded is not None
            assert loaded.chunk_id == sample[0].chunk_id
            assert loaded.content == sample[0].content

    run_async(_run_query())
