from __future__ import annotations

import asyncio
import time
import uuid

from app.retrieval.generation import (
    GenerationEvidenceInput,
    GenerationRetrievalRequest,
    RetrievalBudget,
    RetrievalLevel,
    retrieve_generation_evidence,
    select_retrieval_level,
)
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters, SourcePassage
from tests.conftest import run_async


def test_generation_evidence_pool_uses_parallel_batch_and_enforces_budget() -> None:
    first = _passage("brief.md", "A" * 60)
    duplicate = first.model_copy()
    second = _passage("programme.md", "B" * 60)
    retriever = _BatchRetriever(
        {
            "scope": [first],
            "programme": [duplicate, second],
        }
    )
    requests = (
        _request("scope", "scope"),
        _request("programme", "programme"),
    )

    pool = run_async(
        retrieve_generation_evidence(
            retriever,
            requests,
            level=RetrievalLevel.TARGETED_PROJECT,
            budget=RetrievalBudget(
                max_searches=2,
                max_chunks=2,
                max_documents=2,
                max_chars=90,
                max_concurrency=2,
            ),
        )
    )

    assert retriever.max_concurrency == 2
    assert pool.passages_for("scope") == [first]
    assert pool.passages_for("programme")[0] == first
    assert len(pool.passages_for("programme")) == 2
    assert len(pool.passages_for("programme")[1].content) == 30
    assert pool.stats is not None
    assert pool.stats.selected_chunks == 2
    assert pool.stats.selected_chars == 90


def test_retrieval_levels_skip_broader_requests() -> None:
    retriever = _SequentialRetriever()
    requests = (
        _request("current", "current", level=RetrievalLevel.CURRENT_ARTEFACT),
        _request("targeted", "targeted"),
        _request("broad", "broad", level=RetrievalLevel.BROAD_CORPUS),
    )

    pool = run_async(
        retrieve_generation_evidence(
            retriever,
            requests,
            level=RetrievalLevel.TARGETED_PROJECT,
            budget=RetrievalBudget(max_searches=3),
        )
    )

    assert retriever.queries == ["current", "targeted"]
    assert pool.stats is not None
    assert pool.stats.executed_searches == 2
    assert "broad" not in pool.by_request


def test_levels_below_targeted_project_never_execute_semantic_searches() -> None:
    for level in (
        RetrievalLevel.STRUCTURED_FACTS,
        RetrievalLevel.CURRENT_ARTEFACT,
    ):
        retriever = _SequentialRetriever()

        pool = run_async(
            retrieve_generation_evidence(
                retriever,
                (_request("scope", "scope", level=level),),
                level=level,
                budget=RetrievalBudget(),
            )
        )

        assert retriever.queries == []
        assert pool.stats is not None
        assert pool.stats.executed_searches == 0


def test_preloaded_evidence_is_selected_without_semantic_search() -> None:
    passage = _passage("brief.md", "structured project brief")
    retriever = _SequentialRetriever()

    pool = run_async(
        retrieve_generation_evidence(
            retriever,
            (_request("scope", "scope"),),
            preloaded=(
                GenerationEvidenceInput(
                    key="structured",
                    category="project_evidence",
                    passages=(passage,),
                ),
            ),
            level=RetrievalLevel.STRUCTURED_FACTS,
            budget=RetrievalBudget(),
        )
    )

    assert retriever.queries == []
    assert pool.passages_for("structured") == [passage]
    assert pool.category("project_evidence") == [passage]
    assert pool.stats is not None
    assert pool.stats.selected_chunks == 1
    assert pool.stats.selected_tokens == 3


def test_preloaded_and_searched_evidence_share_global_budgets() -> None:
    preloaded = _passage("brief.md", "one two")
    searched = _passage("programme.md", "three four five")
    retriever = _BatchRetriever({"programme": [searched]})

    pool = run_async(
        retrieve_generation_evidence(
            retriever,
            (_request("programme", "programme"),),
            preloaded=(
                GenerationEvidenceInput(
                    key="brief",
                    category="project_evidence",
                    passages=(preloaded,),
                ),
            ),
            level=RetrievalLevel.TARGETED_PROJECT,
            budget=RetrievalBudget(max_tokens=4, max_chunks=2, max_documents=2),
        )
    )

    assert pool.passages_for("brief") == [preloaded]
    assert pool.passages_for("programme")[0].content == "three four"
    assert pool.stats is not None
    assert pool.stats.selected_tokens == 4


def test_generation_evidence_pool_enforces_token_budget() -> None:
    retriever = _SequentialRetriever()
    request = _request("alpha beta gamma delta", "scope")

    pool = run_async(
        retrieve_generation_evidence(
            retriever,
            (request,),
            level=RetrievalLevel.TARGETED_PROJECT,
            budget=RetrievalBudget(max_tokens=3),
        )
    )

    assert pool.passages_for(request.key)[0].content == "alpha beta gamma"
    assert pool.stats is not None
    assert pool.stats.selected_tokens == 3


def test_logical_query_executes_once_at_largest_limit_and_fans_out() -> None:
    first = _passage("brief.md", "Project brief")
    second = _passage("programme.md", "Project programme")
    retriever = _BatchRetriever(
        {
            "scope": [first, second],
            "programme": [first, second],
        }
    )
    requests = (
        _request("scope", "scope", query="project evidence", limit=1),
        _request(
            "programme",
            "programme",
            query="  PROJECT   evidence ",
            limit=2,
        ),
    )

    pool = run_async(
        retrieve_generation_evidence(
            retriever,
            requests,
            level=RetrievalLevel.TARGETED_PROJECT,
            budget=RetrievalBudget(max_searches=1),
        )
    )

    assert len(retriever.requests) == 1
    assert retriever.requests[0].limit == 2
    assert pool.passages_for("scope") == [first]
    assert pool.passages_for("programme") == [first, second]
    assert pool.category("scope") == [first]
    assert pool.category("programme") == [first, second]
    assert pool.stats is not None
    assert pool.stats.requested_searches == 2
    assert pool.stats.executed_searches == 1


def test_chunk_document_and_token_budgets_are_global_across_queries() -> None:
    first_document_id = uuid.uuid4()
    first = _passage("brief-1.md", "one two", document_id=first_document_id)
    second = _passage("brief-2.md", "three four", document_id=first_document_id)
    third = _passage("programme.md", "five six")
    over_document_budget = _passage("risk.md", "seven")
    retriever = _BatchRetriever(
        {
            "scope": [first, second],
            "programme": [third, over_document_budget],
        }
    )

    pool = run_async(
        retrieve_generation_evidence(
            retriever,
            (
                _request("scope", "scope"),
                _request("programme", "programme"),
            ),
            level=RetrievalLevel.TARGETED_PROJECT,
            budget=RetrievalBudget(
                max_searches=2,
                max_chunks=3,
                max_documents=2,
                max_tokens=5,
            ),
        )
    )

    assert pool.passages_for("scope") == [first, second]
    assert pool.passages_for("programme")[0].content == "five"
    assert all(
        passage.chunk_id != over_document_budget.chunk_id
        for passage in pool.passages_for("programme")
    )
    assert pool.stats is not None
    assert pool.stats.selected_chunks == 3
    assert pool.stats.selected_documents == 2
    assert pool.stats.selected_tokens == 5


def test_document_retriever_batches_with_isolated_bounded_sessions(monkeypatch) -> None:
    in_flight = 0
    max_in_flight = 0

    async def fake_retrieve(self, query, **kwargs):
        nonlocal in_flight, max_in_flight
        del self, kwargs
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return [_passage(f"{query}.md", query)]

    monkeypatch.setattr(DocumentRetriever, "retrieve", fake_retrieve)
    factory = _SessionFactory()
    retriever = DocumentRetriever(object(), session_factory=factory)

    result = run_async(
        retriever.retrieve_many(
            tuple(_request(str(index), str(index)) for index in range(5)),
            max_concurrency=2,
        )
    )

    assert max_in_flight == 2
    assert factory.opened == 5
    assert list(result) == ["0", "1", "2", "3", "4"]


def test_bounded_parallel_retrieval_is_faster_with_identical_evidence(
    monkeypatch,
) -> None:
    passages = {
        str(index): _passage(f"{index}.md", f"evidence {index}") for index in range(6)
    }

    async def fake_retrieve(self, query, **kwargs):
        del self, kwargs
        await asyncio.sleep(0.04)
        return [passages[query]]

    monkeypatch.setattr(DocumentRetriever, "retrieve", fake_retrieve)
    requests = tuple(_request(str(index), str(index)) for index in range(6))

    async def compare():
        sequential_started = time.perf_counter()
        sequential = await retrieve_generation_evidence(
            DocumentRetriever(object(), session_factory=_SessionFactory()),
            requests,
            level=RetrievalLevel.TARGETED_PROJECT,
            budget=RetrievalBudget(max_searches=6, max_concurrency=1),
        )
        sequential_seconds = time.perf_counter() - sequential_started

        parallel_started = time.perf_counter()
        parallel = await retrieve_generation_evidence(
            DocumentRetriever(object(), session_factory=_SessionFactory()),
            requests,
            level=RetrievalLevel.TARGETED_PROJECT,
            budget=RetrievalBudget(max_searches=6, max_concurrency=3),
        )
        parallel_seconds = time.perf_counter() - parallel_started
        return sequential_seconds, sequential, parallel_seconds, parallel

    sequential_seconds, sequential, parallel_seconds, parallel = asyncio.run(compare())

    sequential_evidence = {
        request.key: sequential.passages_for(request.key) for request in requests
    }
    parallel_evidence = {
        request.key: parallel.passages_for(request.key) for request in requests
    }
    assert parallel_evidence == sequential_evidence
    assert parallel_seconds < sequential_seconds * 0.7


def test_select_retrieval_level_uses_lowest_sufficient_level() -> None:
    assert (
        select_retrieval_level(
            structured_context_available=True,
            current_artefact_available=False,
            project_evidence_required=False,
        )
        == RetrievalLevel.STRUCTURED_FACTS
    )
    assert (
        select_retrieval_level(
            structured_context_available=True,
            current_artefact_available=True,
            project_evidence_required=False,
        )
        == RetrievalLevel.CURRENT_ARTEFACT
    )
    assert (
        select_retrieval_level(
            structured_context_available=True,
            current_artefact_available=True,
            project_evidence_required=True,
        )
        == RetrievalLevel.TARGETED_PROJECT
    )


class _BatchRetriever:
    def __init__(self, results: dict[str, list[SourcePassage]]) -> None:
        self.results = results
        self.max_concurrency: int | None = None
        self.requests = []

    async def retrieve_many(self, requests, *, max_concurrency):
        self.max_concurrency = max_concurrency
        self.requests = list(requests)
        return {request.key: self.results[request.key] for request in requests}


class _SequentialRetriever:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def retrieve(self, query, **kwargs):
        del kwargs
        self.queries.append(query)
        return [_passage(f"{query}.md", query)]


class _SessionFactory:
    def __init__(self) -> None:
        self.opened = 0

    def __call__(self):
        factory = self

        class _Context:
            async def __aenter__(self):
                factory.opened += 1
                return object()

            async def __aexit__(self, exc_type, exc, traceback):
                return False

        return _Context()


def _request(
    key: str,
    category: str,
    *,
    query: str | None = None,
    limit: int = 3,
    level: RetrievalLevel = RetrievalLevel.TARGETED_PROJECT,
) -> GenerationRetrievalRequest:
    return GenerationRetrievalRequest(
        key=key,
        category=category,
        query=query or key,
        filters=RetrievalFilters(),
        limit=limit,
        level=level,
    )


def _passage(
    path: str,
    content: str,
    *,
    document_id: uuid.UUID | None = None,
) -> SourcePassage:
    return SourcePassage(
        chunk_id=uuid.uuid4(),
        document_id=document_id or uuid.uuid4(),
        chunk_index=0,
        content=content,
        project="test",
        phase="reference",
        document_class="project_evidence",
        filename=path,
        relative_path=path,
        score=1.0,
    )
