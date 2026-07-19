import uuid
from unittest.mock import AsyncMock, patch

from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import ChunkSearchHit, RetrievalFilters
from tests.conftest import run_async

PROJECT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _hit(
    *,
    chunk_id: uuid.UUID | None = None,
    content: str = "sample content",
    project: str = "procurement-blockb",
    procurement_stage: str | None = "evaluation",
) -> ChunkSearchHit:
    return ChunkSearchHit(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        content=content,
        page_or_section="p.1",
        chunk_metadata=None,
        project=project,
        project_id=PROJECT_ID,
        phase="procurement",
        source_type="project_evidence",
        document_class="evaluation",
        filename="eval.pdf",
        relative_path=f"{project}/06 EVALUATION/eval.pdf",
        document_metadata={"procurement_stage": procurement_stage},
        raw_score=0.9,
    )


def test_retriever_returns_empty_for_blank_query() -> None:
    retriever = DocumentRetriever(AsyncMock())
    assert run_async(retriever.retrieve("   ")) == []


def test_retriever_fuses_semantic_and_lexical_hits() -> None:
    session = AsyncMock()
    shared = _hit(content="evaluation criteria matrix")
    semantic_only = _hit(content="semantic only")
    lexical_only = _hit(content="lexical only")

    with (
        patch(
            "app.retrieval.retriever.embed_query",
            new=AsyncMock(return_value=[0.1] * 1536),
        ),
        patch(
            "app.retrieval.retriever.queries.semantic_search",
            new=AsyncMock(return_value=[shared, semantic_only]),
        ) as semantic_mock,
        patch(
            "app.retrieval.retriever.queries.fulltext_search",
            new=AsyncMock(return_value=[shared, lexical_only]),
        ) as lexical_mock,
        patch(
            "app.retrieval.retriever.queries.fetch_neighbouring_chunks_batch",
            new=AsyncMock(return_value={}),
        ),
    ):
        retriever = DocumentRetriever(session)
        filters = RetrievalFilters(
            project_id=PROJECT_ID,
            procurement_stage="evaluation",
        )
        results = run_async(
            retriever.retrieve(
                "Block B tender evaluation criteria",
                filters=filters,
                include_neighbours=False,
            )
        )

    semantic_mock.assert_awaited_once()
    lexical_mock.assert_awaited_once()
    assert len(results) == 3
    assert results[0].chunk_id == shared.chunk_id
    assert results[0].score >= results[1].score
    assert results[0].project == "procurement-blockb"


def test_retriever_forwards_project_scope_filters() -> None:
    session = AsyncMock()
    hit = _hit(project="procurement-blockb")

    with (
        patch(
            "app.retrieval.retriever.embed_query",
            new=AsyncMock(return_value=[0.1] * 1536),
        ),
        patch(
            "app.retrieval.retriever.queries.semantic_search",
            new=AsyncMock(return_value=[hit]),
        ) as semantic_mock,
        patch(
            "app.retrieval.retriever.queries.fulltext_search",
            new=AsyncMock(return_value=[]),
        ) as lexical_mock,
    ):
        retriever = DocumentRetriever(session)
        filters = RetrievalFilters(
            active_project_id=PROJECT_ID,
            include_platform_knowledge=True,
            cross_project=False,
        )
        run_async(
            retriever.retrieve(
                "project management plan",
                filters=filters,
                include_neighbours=False,
            )
        )

    assert semantic_mock.await_args.kwargs["filters"] == filters
    assert lexical_mock.await_args.kwargs["filters"] == filters


def test_retriever_includes_neighbours_when_requested() -> None:
    session = AsyncMock()
    hit = _hit()
    neighbour = AsyncMock()
    neighbour.id = uuid.uuid4()
    neighbour.chunk_index = 1
    neighbour.content = "neighbour text"
    neighbour.page_or_section = "p.2"

    with (
        patch(
            "app.retrieval.retriever.embed_query",
            new=AsyncMock(return_value=[0.1] * 1536),
        ),
        patch(
            "app.retrieval.retriever.queries.semantic_search",
            new=AsyncMock(return_value=[hit]),
        ),
        patch(
            "app.retrieval.retriever.queries.fulltext_search",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.retrieval.retriever.queries.fetch_neighbouring_chunks_batch",
            new=AsyncMock(return_value={hit.chunk_id: [neighbour]}),
        ) as neighbour_mock,
    ):
        retriever = DocumentRetriever(session)
        results = run_async(retriever.retrieve("criteria", include_neighbours=True))

    neighbour_mock.assert_awaited_once()
    assert len(results) == 1
    assert len(results[0].neighbours) == 1
    assert results[0].neighbours[0].content == "neighbour text"
