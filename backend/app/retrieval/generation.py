"""Bounded retrieval plans and reusable evidence pools for artefact generation."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from enum import IntEnum
from typing import Protocol

from app.retrieval.schemas import RetrievalFilters, SourcePassage


_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


class RetrievalLevel(IntEnum):
    STRUCTURED_FACTS = 0
    CURRENT_ARTEFACT = 1
    TARGETED_PROJECT = 2
    BROAD_CORPUS = 3


@dataclass(frozen=True, slots=True)
class RetrievalBudget:
    max_searches: int = 8
    max_chunks: int = 24
    max_documents: int = 12
    max_chars: int = 48_000
    max_concurrency: int = 4
    max_tokens: int = 12_000

    def __post_init__(self) -> None:
        for name, value in (
            ("max_searches", self.max_searches),
            ("max_chunks", self.max_chunks),
            ("max_documents", self.max_documents),
            ("max_chars", self.max_chars),
            ("max_concurrency", self.max_concurrency),
            ("max_tokens", self.max_tokens),
        ):
            if value < 1:
                raise ValueError(f"{name} must be at least 1")


@dataclass(frozen=True, slots=True)
class GenerationRetrievalRequest:
    key: str
    category: str
    query: str
    filters: RetrievalFilters
    limit: int
    level: RetrievalLevel = RetrievalLevel.TARGETED_PROJECT
    include_neighbours: bool = False


@dataclass(frozen=True, slots=True)
class GenerationEvidenceInput:
    """Already-loaded evidence that participates in the same global budgets."""

    key: str
    category: str
    passages: tuple[SourcePassage, ...]


@dataclass(frozen=True, slots=True)
class EvidencePoolStats:
    level: RetrievalLevel
    requested_searches: int
    executed_searches: int
    selected_chunks: int
    selected_documents: int
    selected_chars: int
    selected_tokens: int = 0


@dataclass(slots=True)
class GenerationEvidencePool:
    by_request: dict[str, list[SourcePassage]] = field(default_factory=dict)
    by_category: dict[str, list[SourcePassage]] = field(default_factory=dict)
    stats: EvidencePoolStats | None = None

    def passages_for(self, key: str) -> list[SourcePassage]:
        return list(self.by_request.get(key, ()))

    def category(self, key: str) -> list[SourcePassage]:
        return list(self.by_category.get(key, ()))


@dataclass(slots=True)
class _LogicalRequestGroup:
    request: GenerationRetrievalRequest
    consumers: list[GenerationRetrievalRequest]


class GenerationRetriever(Protocol):
    async def retrieve(
        self,
        query: str,
        *,
        filters: RetrievalFilters | None = None,
        limit: int | None = None,
        include_neighbours: bool = True,
    ) -> list[SourcePassage]: ...


async def retrieve_generation_evidence(
    retriever: GenerationRetriever,
    requests: Sequence[GenerationRetrievalRequest],
    *,
    preloaded: Sequence[GenerationEvidenceInput] = (),
    level: RetrievalLevel,
    budget: RetrievalBudget,
) -> GenerationEvidencePool:
    """Execute one bounded retrieval plan and return reusable evidence buckets."""
    eligible = [request for request in requests if request.level <= level]
    logical_requests = _group_logical_requests(eligible)
    selected_groups = (
        logical_requests[: budget.max_searches]
        if level >= RetrievalLevel.TARGETED_PROJECT
        else []
    )
    raw = await _execute_requests(
        retriever,
        [group.request for group in selected_groups],
        budget=budget,
    )
    pool = GenerationEvidencePool()
    selected_by_chunk: dict[str, SourcePassage] = {}
    rejected_chunks: set[str] = set()
    seen_documents: set[str] = set()
    seen_by_category: dict[str, set[str]] = {}
    selected_chars = 0
    selected_tokens = 0

    def select_passages(passages: Sequence[SourcePassage]) -> list[SourcePassage]:
        nonlocal selected_chars, selected_tokens
        group_passages: list[SourcePassage] = []
        group_chunks: set[str] = set()
        for passage in passages:
            chunk_key = str(passage.chunk_id)
            if chunk_key in group_chunks or chunk_key in rejected_chunks:
                continue
            group_chunks.add(chunk_key)
            previously_selected = selected_by_chunk.get(chunk_key)
            if previously_selected is not None:
                group_passages.append(previously_selected)
                continue
            document_key = str(passage.document_id)
            if (
                document_key not in seen_documents
                and len(seen_documents) >= budget.max_documents
            ):
                rejected_chunks.add(chunk_key)
                continue
            if len(selected_by_chunk) >= budget.max_chunks:
                rejected_chunks.add(chunk_key)
                continue
            remaining_chars = budget.max_chars - selected_chars
            remaining_tokens = budget.max_tokens - selected_tokens
            if remaining_chars <= 0 or remaining_tokens <= 0:
                rejected_chunks.add(chunk_key)
                continue
            bounded_content, bounded_tokens = _truncate_content(
                passage.content,
                max_chars=remaining_chars,
                max_tokens=remaining_tokens,
            )
            bounded = passage
            if bounded_content != passage.content:
                bounded = passage.model_copy(update={"content": bounded_content})
            selected_by_chunk[chunk_key] = bounded
            seen_documents.add(document_key)
            selected_chars += len(bounded.content)
            selected_tokens += bounded_tokens
            group_passages.append(bounded)
        return group_passages

    def add_to_category(category: str, passages: Sequence[SourcePassage]) -> None:
        category_passages = pool.by_category.setdefault(category, [])
        category_chunks = seen_by_category.setdefault(category, set())
        for passage in passages:
            chunk_key = str(passage.chunk_id)
            if chunk_key in category_chunks:
                continue
            category_chunks.add(chunk_key)
            category_passages.append(passage)

    for evidence_input in preloaded:
        input_passages = select_passages(evidence_input.passages)
        pool.by_request[evidence_input.key] = list(input_passages)
        add_to_category(evidence_input.category, input_passages)

    for group in selected_groups:
        group_passages = select_passages(raw.get(group.request.key, ()))

        for request in group.consumers:
            request_passages = group_passages[: request.limit]
            pool.by_request[request.key] = list(request_passages)
            add_to_category(request.category, request_passages)

    pool.stats = EvidencePoolStats(
        level=level,
        requested_searches=len(eligible),
        executed_searches=len(selected_groups),
        selected_chunks=len(selected_by_chunk),
        selected_documents=len(seen_documents),
        selected_chars=selected_chars,
        selected_tokens=selected_tokens,
    )
    return pool


def _group_logical_requests(
    requests: Sequence[GenerationRetrievalRequest],
) -> list[_LogicalRequestGroup]:
    groups: list[_LogicalRequestGroup] = []
    indexes: dict[tuple[str, str, bool], int] = {}
    for request in requests:
        identity = _logical_request_identity(request)
        existing_index = indexes.get(identity)
        if existing_index is None:
            indexes[identity] = len(groups)
            groups.append(_LogicalRequestGroup(request=request, consumers=[request]))
            continue
        group = groups[existing_index]
        group.consumers.append(request)
        if request.limit > group.request.limit:
            group.request = replace(group.request, limit=request.limit)
    return groups


def _logical_request_identity(
    request: GenerationRetrievalRequest,
) -> tuple[str, str, bool]:
    query = " ".join(request.query.split()).casefold()
    filters = json.dumps(
        request.filters.model_dump(mode="json", exclude_none=True),
        sort_keys=True,
        separators=(",", ":"),
    )
    return query, filters, request.include_neighbours


def _truncate_content(
    content: str,
    *,
    max_chars: int,
    max_tokens: int,
) -> tuple[str, int]:
    """Apply deterministic word/punctuation token and character bounds."""
    if max_chars <= 0 or max_tokens <= 0:
        return "", 0
    bounded = content[:max_chars]
    matches = list(_TOKEN_PATTERN.finditer(bounded))
    if len(matches) <= max_tokens:
        return bounded, len(matches)
    return bounded[: matches[max_tokens - 1].end()], max_tokens


def select_retrieval_level(
    *,
    structured_context_available: bool,
    current_artefact_available: bool,
    project_evidence_required: bool,
    broad_corpus_required: bool = False,
) -> RetrievalLevel:
    """Choose the lowest retrieval level capable of satisfying the request."""
    if broad_corpus_required:
        return RetrievalLevel.BROAD_CORPUS
    if project_evidence_required:
        return RetrievalLevel.TARGETED_PROJECT
    if current_artefact_available:
        return RetrievalLevel.CURRENT_ARTEFACT
    if structured_context_available:
        return RetrievalLevel.STRUCTURED_FACTS
    return RetrievalLevel.TARGETED_PROJECT


async def _execute_requests(
    retriever: GenerationRetriever,
    requests: list[GenerationRetrievalRequest],
    *,
    budget: RetrievalBudget,
) -> dict[str, list[SourcePassage]]:
    retrieve_many = getattr(retriever, "retrieve_many", None)
    if callable(retrieve_many) and requests:
        return await retrieve_many(
            requests,
            max_concurrency=budget.max_concurrency,
        )

    results: dict[str, list[SourcePassage]] = {}
    for request in requests:
        results[request.key] = await retriever.retrieve(
            request.query,
            filters=request.filters,
            limit=request.limit,
            include_neighbours=request.include_neighbours,
        )
    return results
