from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from openai import AsyncOpenAI
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from tender.llm.client import LLMAdjudicationResponse, TenderLLMClient
from tender.llm.schema import openai_strict_json_schema
from tender.models import (
    TaxonomyCell,
    TaxonomySynonym,
    TenderJob,
    TenderLineItem,
    TenderMapping,
    TenderQuote,
)
from tender.schemas import ProjectContext
from tender.seeds.load import normalize_phrase
from tender.services.context import context_for_quote
from tender.services.telemetry import note_openai_response, record_mapping_tier

PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"
T2_PROMPT_VERSION = "0.1.0"
T3_PROMPT_VERSION = "0.1.0"
T2_PROMPT_PATH = PROMPT_DIR / f"map_items_t2_v{T2_PROMPT_VERSION}.md"
T3_PROMPT_PATH = PROMPT_DIR / f"map_items_t3_v{T3_PROMPT_VERSION}.md"

# I3 fallback target. Real matrix row; never offered as an LLM/T0/T1 candidate.
UNALLOCATED_CELL_CODE = "99.01"

SessionFactory = Callable[[], Any]


@dataclass(frozen=True)
class CellCandidate:
    cell_code: str
    similarity: float
    via: str


@dataclass(frozen=True)
class TaxonomyCellSummary:
    code: str
    name: str
    description: str | None = None
    sort_order: int = 0


@dataclass(frozen=True)
class LineItemMappingInput:
    description_raw: str
    section_path: tuple[str, ...]
    qty: float | None
    unit: str | None
    amount_cents: int | None
    item_status: str
    embedding: list[float] | None = None


@dataclass(frozen=True)
class CellAllocation:
    cell_code: str
    allocation_fraction: float = 1.0


@dataclass(frozen=True)
class MappingDecision:
    tier: str
    allocations: tuple[CellAllocation, ...]
    confidence: float | None
    qa_state: str
    adjudication: dict[str, Any]
    escalate_to_t3: bool = False


@dataclass(frozen=True)
class FreeTierResult:
    decision: MappingDecision | None = None
    t1_candidates: tuple[CellCandidate, ...] = ()
    candidate_cells: tuple[TaxonomyCellSummary, ...] = ()


@dataclass(frozen=True)
class T2BatchItem:
    item: LineItemMappingInput
    candidates: tuple[CellCandidate, ...]
    candidate_cells: tuple[TaxonomyCellSummary, ...]


@dataclass(frozen=True)
class FrontierMappingResponse:
    allocations: tuple[CellAllocation, ...]
    confidence: float
    rationale: str
    model: str
    prompt_version: str
    request_id: str | None = None
    raw: dict[str, Any] | None = None


class FrontierMappingClient(Protocol):
    async def map_item_open(
        self,
        *,
        line_item: dict[str, Any],
        active_cells: list[TaxonomyCellSummary],
        context: ProjectContext,
        prompt_version: str,
        model_key: str,
    ) -> FrontierMappingResponse:
        ...


class OpenAIFrontierMappingClient:
    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)

    async def map_item_open(
        self,
        *,
        line_item: dict[str, Any],
        active_cells: list[TaxonomyCellSummary],
        context: ProjectContext,
        prompt_version: str,
        model_key: str,
    ) -> FrontierMappingResponse:
        response = await self.client.responses.create(
            model=_model_for_key(model_key),
            instructions=_prompt_text(T3_PROMPT_PATH),
            input=json.dumps(
                {
                    "project_context": context.model_dump(mode="json"),
                    "line_item": line_item,
                    "active_cells": [
                        {"code": cell.code, "name": cell.name} for cell in active_cells
                    ],
                },
                ensure_ascii=True,
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "tender_frontier_mapping",
                    "schema": openai_strict_json_schema(_frontier_mapping_schema()),
                    "strict": True,
                }
            },
            temperature=0,
        )
        note_openai_response(response)
        data = json.loads(_response_text(response))
        return FrontierMappingResponse(
            allocations=tuple(
                CellAllocation(
                    str(item["cell_code"]),
                    float(item["allocation_fraction"]),
                )
                for item in data["mappings"]
            ),
            confidence=float(data["confidence"]),
            rationale=str(data["rationale"]),
            model=_model_for_key(model_key),
            prompt_version=prompt_version,
            request_id=getattr(response, "id", None),
            raw=data,
        )


async def map_items(
    session: AsyncSession,
    job: TenderJob,
    *,
    llm_client: TenderLLMClient | None = None,
    frontier_client: FrontierMappingClient | None = None,
    session_factory: SessionFactory | None = None,
    concurrency: int | None = None,
) -> None:
    if job.quote_id is None:
        raise ValueError("map_items job requires quote_id")
    llm_client = llm_client or _default_llm_client()
    context = await _context_for_quote(session, job.quote_id)
    active_cells = await load_active_cell_summaries(session)

    result = await session.execute(
        select(TenderLineItem)
        .where(TenderLineItem.quote_id == job.quote_id)
        .order_by(TenderLineItem.created_at)
    )
    prepared: list[tuple[uuid.UUID, LineItemMappingInput]] = []
    for line_item in result.scalars():
        existing = await _existing_mappings(session, line_item.id)
        if has_protected_mapping(existing):
            continue
        await session.execute(
            delete(TenderMapping).where(TenderMapping.line_item_id == line_item.id)
        )
        prepared.append((line_item.id, _line_item_from_model(line_item)))

    if prepared:
        await session.flush()
        decisions = await map_prepared_line_items(
            prepared,
            context=context,
            llm_client=llm_client,
            frontier_client=frontier_client,
            session_factory=session_factory,
            concurrency=concurrency,
            active_cells=active_cells,
        )
        for line_item_id, decision in decisions:
            _add_mapping_rows(session, line_item_id, decision)
        await session.flush()

    quote = await session.get(TenderQuote, job.quote_id)
    if quote is not None:
        quote.stage = "run_expectations"


async def map_prepared_line_items(
    prepared: Sequence[tuple[uuid.UUID, LineItemMappingInput]],
    *,
    context: ProjectContext,
    llm_client: TenderLLMClient,
    frontier_client: FrontierMappingClient | None = None,
    session_factory: SessionFactory | None = None,
    concurrency: int | None = None,
    active_cells: Sequence[TaxonomyCellSummary],
) -> list[tuple[uuid.UUID, MappingDecision]]:
    """Map line items: parallel free tiers → batch T2 → parallel scoped T3."""

    limit = max(
        1,
        concurrency if concurrency is not None else settings.tender_map_concurrency,
    )
    factory = session_factory or _default_session_factory()
    semaphore = asyncio.Semaphore(limit)

    async def resolve_one(
        line_item_id: uuid.UUID, item: LineItemMappingInput
    ) -> tuple[uuid.UUID, LineItemMappingInput, FreeTierResult]:
        async with semaphore:
            async with factory() as item_session:
                free = await resolve_free_tier(item_session, item)
                return line_item_id, item, free

    free_results = await asyncio.gather(
        *(resolve_one(line_item_id, item) for line_item_id, item in prepared)
    )

    decisions: dict[uuid.UUID, MappingDecision] = {}
    pending_t2: list[tuple[uuid.UUID, T2BatchItem]] = []
    pending_t3: list[tuple[uuid.UUID, LineItemMappingInput, tuple[CellCandidate, ...]]] = []

    for line_item_id, item, free in free_results:
        if free.decision is not None:
            decisions[line_item_id] = free.decision
            continue
        if free.t1_candidates:
            pending_t2.append(
                (
                    line_item_id,
                    T2BatchItem(
                        item=item,
                        candidates=free.t1_candidates,
                        candidate_cells=free.candidate_cells,
                    ),
                )
            )
            continue
        pending_t3.append((line_item_id, item, ()))

    if pending_t2:
        batch_items = [item for _, item in pending_t2]
        t2_decisions = await t2_map_items_batch(
            batch_items,
            context=context,
            llm_client=llm_client,
        )
        for (line_item_id, batch_item), decision in zip(
            pending_t2, t2_decisions, strict=True
        ):
            if decision.escalate_to_t3:
                pending_t3.append(
                    (line_item_id, batch_item.item, batch_item.candidates)
                )
            else:
                decisions[line_item_id] = decision
                record_mapping_tier(decision.tier, duration_ms=0)

    if pending_t3:
        async def map_t3(
            line_item_id: uuid.UUID,
            item: LineItemMappingInput,
            t1_candidates: tuple[CellCandidate, ...],
        ) -> tuple[uuid.UUID, MappingDecision]:
            started = time.perf_counter()
            async with semaphore:
                scoped = scope_cells_for_t3(
                    active_cells, t1_candidates=t1_candidates
                )
                decision = await t3_map_item(
                    item,
                    active_cells=scoped,
                    context=context,
                    frontier_client=frontier_client,
                )
                _note_mapping_tier(decision.tier, started)
                return line_item_id, decision

        t3_results = await asyncio.gather(
            *(
                map_t3(line_item_id, item, candidates)
                for line_item_id, item, candidates in pending_t3
            )
        )
        for line_item_id, decision in t3_results:
            decisions[line_item_id] = decision

    return [
        (line_item_id, decisions[line_item_id])
        for line_item_id, _item in prepared
        if line_item_id in decisions
    ]


async def resolve_free_tier(
    session: AsyncSession,
    item: LineItemMappingInput,
    *,
    t0_func: Callable[[AsyncSession, str], Awaitable[list[CellCandidate]]] | None = None,
    t1_func: Callable[
        [AsyncSession, list[float], int], Awaitable[list[CellCandidate]]
    ]
    | None = None,
    cell_loader: Callable[
        [AsyncSession, list[str]], Awaitable[list[TaxonomyCellSummary]]
    ]
    | None = None,
) -> FreeTierResult:
    t0_func = t0_func or t0_match
    t1_func = t1_func or t1_candidates
    cell_loader = cell_loader or load_cell_summaries
    started = time.perf_counter()

    t0_candidates = await t0_func(session, normalize_phrase(item.description_raw))
    if t0_candidates:
        decision = _candidate_decision("t0_exact", t0_candidates[0])
        _note_mapping_tier(decision.tier, started)
        return FreeTierResult(decision=decision)

    t1 = await t1_func(session, item.embedding or [], 5) if item.embedding else []
    accepted = accept_t1_candidate(t1)
    if accepted is not None:
        decision = _candidate_decision("t1_embedding", accepted)
        _note_mapping_tier(decision.tier, started)
        return FreeTierResult(decision=decision)

    if not t1:
        return FreeTierResult()

    candidate_cells = await cell_loader(
        session, [candidate.cell_code for candidate in t1]
    )
    return FreeTierResult(
        t1_candidates=tuple(t1),
        candidate_cells=tuple(candidate_cells),
    )


async def map_line_item_cascade(
    session: AsyncSession,
    item: LineItemMappingInput,
    *,
    context: ProjectContext,
    llm_client: TenderLLMClient,
    frontier_client: FrontierMappingClient | None = None,
    t0_func: Callable[[AsyncSession, str], Awaitable[list[CellCandidate]]] | None = None,
    t1_func: Callable[
        [AsyncSession, list[float], int], Awaitable[list[CellCandidate]]
    ]
    | None = None,
    t2_func: Callable[..., Awaitable[MappingDecision]] | None = None,
    t3_func: Callable[..., Awaitable[MappingDecision]] | None = None,
    cell_loader: Callable[
        [AsyncSession, list[str]], Awaitable[list[TaxonomyCellSummary]]
    ]
    | None = None,
    active_cell_loader: Callable[
        [AsyncSession], Awaitable[list[TaxonomyCellSummary]]
    ]
    | None = None,
) -> MappingDecision:
    t2_func = t2_func or t2_map_item
    t3_func = t3_func or t3_map_item
    active_cell_loader = active_cell_loader or load_active_cell_summaries
    started = time.perf_counter()

    free = await resolve_free_tier(
        session,
        item,
        t0_func=t0_func,
        t1_func=t1_func,
        cell_loader=cell_loader,
    )
    if free.decision is not None:
        return free.decision

    t1_candidates = free.t1_candidates
    if t1_candidates:
        t2_decision = await t2_func(
            item=item,
            candidates=list(t1_candidates),
            candidate_cells=list(free.candidate_cells),
            context=context,
            llm_client=llm_client,
        )
        if not t2_decision.escalate_to_t3:
            _note_mapping_tier(t2_decision.tier, started)
            return t2_decision

    active_cells = await active_cell_loader(session)
    scoped_cells = scope_cells_for_t3(active_cells, t1_candidates=t1_candidates)
    t3_decision = await t3_func(
        item=item,
        active_cells=scoped_cells,
        context=context,
        frontier_client=frontier_client,
    )
    _note_mapping_tier(t3_decision.tier, started)
    return t3_decision


def taxonomy_group(cell_code: str) -> str:
    return cell_code.split(".", 1)[0]


def scope_cells_for_t3(
    active_cells: Sequence[TaxonomyCellSummary],
    *,
    t1_candidates: Sequence[CellCandidate],
) -> list[TaxonomyCellSummary]:
    mappable = [
        cell for cell in active_cells if cell.code != UNALLOCATED_CELL_CODE
    ]
    if not t1_candidates:
        return list(mappable)
    groups = {taxonomy_group(candidate.cell_code) for candidate in t1_candidates}
    scoped = [
        cell for cell in mappable if taxonomy_group(cell.code) in groups
    ]
    return scoped or list(mappable)


def has_protected_mapping(mappings: Sequence[Any]) -> bool:
    return any(
        getattr(mapping, "tier") == "human"
        or getattr(mapping, "qa_state") in {"confirmed", "corrected"}
        for mapping in mappings
    )


async def t0_match(session: AsyncSession, phrase_norm: str) -> list[CellCandidate]:
    exact_rows = await _all(
        session,
        select(TaxonomySynonym.cell_code, TaxonomySynonym.phrase)
        .join(TaxonomyCell, TaxonomyCell.code == TaxonomySynonym.cell_code)
        .where(
            TaxonomyCell.active.is_(True),
            TaxonomySynonym.phrase_norm == phrase_norm,
        ),
    )
    exact = _single_cell_candidates(exact_rows, similarity=1.0, via="exact")
    if exact_rows:
        return exact

    similarity = func.similarity(TaxonomySynonym.phrase_norm, phrase_norm).label(
        "similarity"
    )
    trigram_rows = await _all(
        session,
        select(TaxonomySynonym.cell_code, TaxonomySynonym.phrase, similarity)
        .join(TaxonomyCell, TaxonomyCell.code == TaxonomySynonym.cell_code)
        .where(
            TaxonomyCell.active.is_(True),
            similarity >= settings.tender_t0_trgm_threshold,
        )
        .order_by(desc(similarity)),
    )
    return _single_cell_candidates(trigram_rows)


async def t1_candidates(
    session: AsyncSession, embedding: list[float], limit: int = 5
) -> list[CellCandidate]:
    distance = TaxonomySynonym.embedding.cosine_distance(embedding)
    similarity = (1 - distance).label("similarity")
    rows = await _all(
        session,
        select(TaxonomySynonym.cell_code, TaxonomySynonym.phrase, similarity)
        .join(TaxonomyCell, TaxonomyCell.code == TaxonomySynonym.cell_code)
        .where(TaxonomyCell.active.is_(True), TaxonomySynonym.embedding.is_not(None))
        .order_by(distance)
        .limit(max(limit * 5, limit)),
    )
    by_cell: dict[str, CellCandidate] = {}
    for row in rows:
        candidate = CellCandidate(
            cell_code=str(_row_value(row, "cell_code")),
            similarity=float(_row_value(row, "similarity")),
            via=str(_row_value(row, "phrase")),
        )
        existing = by_cell.get(candidate.cell_code)
        if existing is None or candidate.similarity > existing.similarity:
            by_cell[candidate.cell_code] = candidate

    ranked = sorted(
        by_cell.values(), key=lambda candidate: candidate.similarity, reverse=True
    )
    return [
        candidate
        for candidate in ranked
        if candidate.cell_code != UNALLOCATED_CELL_CODE
    ][:limit]


def accept_t1_candidate(candidates: Sequence[CellCandidate]) -> CellCandidate | None:
    if not candidates:
        return None
    top = candidates[0]
    runner_up = candidates[1].similarity if len(candidates) > 1 else 0.0
    if top.similarity < settings.tender_t1_accept_sim:
        return None
    if top.similarity - runner_up < settings.tender_t1_accept_margin:
        return None
    return top


async def load_cell_summaries(
    session: AsyncSession, codes: list[str]
) -> list[TaxonomyCellSummary]:
    result = await session.execute(select(TaxonomyCell).where(TaxonomyCell.code.in_(codes)))
    cells_by_code = {
        cell.code: TaxonomyCellSummary(
            code=cell.code,
            name=cell.name,
            description=cell.description,
            sort_order=cell.sort_order,
        )
        for cell in result.scalars()
    }
    return [cells_by_code[code] for code in codes if code in cells_by_code]


async def load_active_cell_summaries(session: AsyncSession) -> list[TaxonomyCellSummary]:
    result = await session.execute(
        select(TaxonomyCell)
        .where(
            TaxonomyCell.active.is_(True),
            TaxonomyCell.code != UNALLOCATED_CELL_CODE,
        )
        .order_by(TaxonomyCell.sort_order, TaxonomyCell.code)
    )
    return [
        TaxonomyCellSummary(
            code=cell.code,
            name=cell.name,
            description=cell.description,
            sort_order=cell.sort_order,
        )
        for cell in result.scalars()
    ]


async def t2_map_item(
    item: LineItemMappingInput,
    *,
    candidates: Sequence[CellCandidate],
    candidate_cells: Sequence[TaxonomyCellSummary],
    context: ProjectContext,
    llm_client: TenderLLMClient,
) -> MappingDecision:
    ordered_cells = _ordered_candidate_cells(candidates, candidate_cells)
    choices = _t2_choices(candidates)
    response = await llm_client.adjudicate(
        _prompt_text(T2_PROMPT_PATH),
        choices,
        _t2_evidence(item, candidates, ordered_cells),
        context,
        prompt_version=T2_PROMPT_VERSION,
        model_key="tender_model_adjudicate_small",
    )
    return _decision_from_t2_response(response, candidates, ordered_cells)


async def t2_map_items_batch(
    items: Sequence[T2BatchItem],
    *,
    context: ProjectContext,
    llm_client: TenderLLMClient,
) -> list[MappingDecision]:
    if not items:
        return []

    batch_size = max(1, settings.tender_map_t2_batch_size)
    decisions: list[MappingDecision] = []
    for offset in range(0, len(items), batch_size):
        chunk = list(items[offset : offset + batch_size])
        decisions.extend(
            await _t2_map_items_batch_chunk(
                chunk, context=context, llm_client=llm_client
            )
        )
    return decisions


async def _t2_map_items_batch_chunk(
    items: Sequence[T2BatchItem],
    *,
    context: ProjectContext,
    llm_client: TenderLLMClient,
) -> list[MappingDecision]:
    prepared = [
        (
            item,
            item.candidates,
            _ordered_candidate_cells(item.candidates, item.candidate_cells),
        )
        for item in items
    ]
    choice_union: list[str] = []
    seen_choices: set[str] = set()
    for _item, candidates, _cells in prepared:
        for choice in _t2_choices(candidates):
            if choice not in seen_choices:
                seen_choices.add(choice)
                choice_union.append(choice)

    evidence_items = [
        {
            **_t2_evidence(item.item, candidates, ordered_cells),
            "allowed_choices": _t2_choices(candidates),
        }
        for item, candidates, ordered_cells in prepared
    ]

    adjudicate_many = getattr(llm_client, "adjudicate_many", None)
    if adjudicate_many is not None:
        responses = await adjudicate_many(
            _prompt_text(T2_PROMPT_PATH),
            choice_union,
            evidence_items,
            context,
            prompt_version=T2_PROMPT_VERSION,
            model_key="tender_model_adjudicate_small",
        )
    else:
        responses = [
            await llm_client.adjudicate(
                _prompt_text(T2_PROMPT_PATH),
                _t2_choices(candidates),
                evidence,
                context,
                prompt_version=T2_PROMPT_VERSION,
                model_key="tender_model_adjudicate_small",
            )
            for (_item, candidates, _cells), evidence in zip(
                prepared, evidence_items, strict=True
            )
        ]

    if len(responses) != len(prepared):
        raise ValueError(
            f"T2 batch returned {len(responses)} decisions for {len(prepared)} items"
        )

    decisions: list[MappingDecision] = []
    for response, (_item, candidates, ordered_cells) in zip(
        responses, prepared, strict=True
    ):
        allowed = set(_t2_choices(candidates))
        if response.choice not in allowed:
            adjudication = _adjudication_payload(response, candidates, ordered_cells)
            adjudication["error"] = "choice_outside_item_candidates"
            decisions.append(
                MappingDecision(
                    tier="t2_small_llm",
                    allocations=(),
                    confidence=response.confidence,
                    qa_state="needs_review",
                    adjudication=adjudication,
                    escalate_to_t3=True,
                )
            )
            continue
        decisions.append(
            _decision_from_t2_response(response, candidates, ordered_cells)
        )
    return decisions


def _t2_choices(candidates: Sequence[CellCandidate]) -> list[str]:
    return [candidate.cell_code for candidate in candidates] + ["none_of_these"]


def _ordered_candidate_cells(
    candidates: Sequence[CellCandidate],
    candidate_cells: Sequence[TaxonomyCellSummary],
) -> list[TaxonomyCellSummary]:
    cells_by_code = {cell.code: cell for cell in candidate_cells}
    return [cells_by_code[candidate.cell_code] for candidate in candidates]


def _t2_evidence(
    item: LineItemMappingInput,
    candidates: Sequence[CellCandidate],
    ordered_cells: Sequence[TaxonomyCellSummary],
) -> dict[str, Any]:
    return {
        "line_item": _line_item_payload(item),
        "candidate_cells": [
            {
                "code": cell.code,
                "name": cell.name,
                "description": cell.description,
                "similarity": candidates[index].similarity,
                "via": candidates[index].via,
            }
            for index, cell in enumerate(ordered_cells)
        ],
        "taxonomy_block": _taxonomy_block(ordered_cells, include_description=True),
    }


def _decision_from_t2_response(
    response: LLMAdjudicationResponse,
    candidates: Sequence[CellCandidate],
    ordered_cells: Sequence[TaxonomyCellSummary],
) -> MappingDecision:
    adjudication = _adjudication_payload(response, candidates, ordered_cells)
    if response.choice == "none_of_these":
        return MappingDecision(
            tier="t2_small_llm",
            allocations=(),
            confidence=response.confidence,
            qa_state="needs_review",
            adjudication=adjudication,
            escalate_to_t3=True,
        )
    qa_state = (
        "auto_pass"
        if response.confidence >= settings.tender_t2_accept_conf
        else "needs_review"
    )
    return MappingDecision(
        tier="t2_small_llm",
        allocations=(CellAllocation(response.choice, 1.0),),
        confidence=response.confidence,
        qa_state=qa_state,
        adjudication=adjudication,
    )


async def t3_map_item(
    item: LineItemMappingInput,
    *,
    active_cells: Sequence[TaxonomyCellSummary],
    context: ProjectContext,
    frontier_client: FrontierMappingClient | None = None,
) -> MappingDecision:
    frontier_client = frontier_client or OpenAIFrontierMappingClient()
    ordered_cells = sorted(active_cells, key=lambda cell: (cell.sort_order, cell.code))
    if not ordered_cells:
        raise ValueError("tender taxonomy seed data has no active cells")
    response = await frontier_client.map_item_open(
        line_item=_line_item_payload(item),
        active_cells=list(ordered_cells),
        context=context,
        prompt_version=T3_PROMPT_VERSION,
        model_key="tender_model_adjudicate_frontier",
    )
    return _decision_from_frontier_response(response, ordered_cells)


async def _all(session: AsyncSession, statement: Any) -> list[Any]:
    result = await session.execute(statement)
    return list(result.all())


def _single_cell_candidates(
    rows: Sequence[Any], *, similarity: float | None = None, via: str | None = None
) -> list[CellCandidate]:
    if not rows:
        return []
    cell_codes = {str(_row_value(row, "cell_code")) for row in rows}
    if len(cell_codes) != 1:
        return []
    best = max(rows, key=lambda row: float(similarity or _row_value(row, "similarity")))
    return [
        CellCandidate(
            cell_code=str(_row_value(best, "cell_code")),
            similarity=float(similarity or _row_value(best, "similarity")),
            via=via or str(_row_value(best, "phrase")),
        )
    ]


def _row_value(row: Any, key: str) -> Any:
    if hasattr(row, key):
        return getattr(row, key)
    if hasattr(row, "_mapping"):
        return row._mapping[key]
    return row[key]


def _decision_from_frontier_response(
    response: FrontierMappingResponse, active_cells: Sequence[TaxonomyCellSummary]
) -> MappingDecision:
    known_codes = {cell.code for cell in active_cells}
    adjudication = {
        "model": response.model,
        "prompt_version": response.prompt_version,
        "request_id": response.request_id,
        "rationale": response.rationale,
        "raw_response": response.raw or _frontier_raw(response),
    }
    unknown = [item.cell_code for item in response.allocations if item.cell_code not in known_codes]
    if unknown:
        adjudication["error"] = "unknown_cell_code"
        adjudication["unknown_cell_codes"] = unknown
        return MappingDecision(
            tier="t3_frontier",
            allocations=(),
            confidence=response.confidence,
            qa_state="needs_review",
            adjudication=adjudication,
        )

    normalized = _validated_allocations(response.allocations, adjudication)
    qa_state = (
        "auto_pass"
        if normalized is not None and response.confidence >= settings.tender_t3_review_conf
        else "needs_review"
    )
    return MappingDecision(
        tier="t3_frontier",
        allocations=normalized or (),
        confidence=response.confidence,
        qa_state=qa_state,
        adjudication=adjudication,
    )


def _validated_allocations(
    allocations: Sequence[CellAllocation], adjudication: dict[str, Any]
) -> tuple[CellAllocation, ...] | None:
    if not 1 <= len(allocations) <= 4:
        adjudication["error"] = "invalid_mapping_count"
        return None
    total = sum(allocation.allocation_fraction for allocation in allocations)
    if abs(total - 1.0) <= 0.001:
        return tuple(allocations)
    if all(allocation.allocation_fraction > 0 for allocation in allocations):
        return tuple(
            CellAllocation(
                allocation.cell_code,
                allocation.allocation_fraction / total,
            )
            for allocation in allocations
        )
    adjudication["error"] = "invalid_allocation_fraction"
    return None


def _adjudication_payload(
    response: LLMAdjudicationResponse,
    candidates: Sequence[CellCandidate],
    candidate_cells: Sequence[TaxonomyCellSummary] = (),
) -> dict[str, Any]:
    cells_by_code = {cell.code: cell for cell in candidate_cells}
    payload = {
        "candidates": [
            {
                "cell_code": candidate.cell_code,
                "name": cells_by_code[candidate.cell_code].name
                if candidate.cell_code in cells_by_code
                else None,
                "similarity": candidate.similarity,
                "via": candidate.via,
            }
            for candidate in candidates
        ],
        "model": response.model,
        "prompt_version": response.prompt_version,
        "request_id": response.request_id,
        "rationale": response.rationale,
    }
    selected = {"cell_code": response.choice}
    selected_cell = cells_by_code.get(response.choice)
    if selected_cell is not None:
        selected["name"] = selected_cell.name
    payload["choice"] = selected
    return payload


def has_multi_candidate_adjudication(adjudication: Any) -> bool:
    if not isinstance(adjudication, dict):
        return False
    candidates = adjudication.get("candidates")
    return isinstance(candidates, list) and len(candidates) >= 2


def _line_item_payload(item: LineItemMappingInput) -> dict[str, Any]:
    return {
        "description_raw": item.description_raw,
        "section_path": list(item.section_path),
        "qty": item.qty,
        "unit": item.unit,
        "amount_cents": item.amount_cents,
        "item_status": item.item_status,
    }


def _taxonomy_block(
    cells: Sequence[TaxonomyCellSummary], *, include_description: bool
) -> str:
    lines = []
    for cell in cells:
        parts = [cell.code, cell.name]
        if include_description:
            parts.append(cell.description or "")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _frontier_raw(response: FrontierMappingResponse) -> dict[str, Any]:
    return {
        "mappings": [
            {
                "cell_code": allocation.cell_code,
                "allocation_fraction": allocation.allocation_fraction,
            }
            for allocation in response.allocations
        ],
        "confidence": response.confidence,
        "rationale": response.rationale,
    }


def _prompt_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _model_for_key(model_key: str) -> str:
    model = getattr(settings, model_key, None)
    if not isinstance(model, str) or not model:
        raise ValueError(f"unknown tender model config key: {model_key}")
    return model


def _frontier_mapping_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "mappings": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "properties": {
                        "cell_code": {"type": "string"},
                        "allocation_fraction": {
                            "type": "number",
                            "exclusiveMinimum": 0,
                        },
                    },
                    "required": ["cell_code", "allocation_fraction"],
                    "additionalProperties": False,
                },
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "rationale": {"type": "string"},
        },
        "required": ["mappings", "confidence", "rationale"],
        "additionalProperties": False,
    }


def _response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    for output in getattr(response, "output", []):
        for content in getattr(output, "content", []):
            text = getattr(content, "text", None)
            if text:
                return str(text)
    raise ValueError("OpenAI structured mapping response did not contain text")


def _candidate_decision(tier: str, candidate: CellCandidate) -> MappingDecision:
    return MappingDecision(
        tier=tier,
        allocations=(CellAllocation(candidate.cell_code, 1.0),),
        confidence=candidate.similarity,
        qa_state="auto_pass",
        adjudication={
            "candidates": [
                {
                    "cell_code": candidate.cell_code,
                    "similarity": candidate.similarity,
                    "via": candidate.via,
                }
            ]
        },
    )


async def _context_for_quote(session: AsyncSession, quote_id: uuid.UUID) -> ProjectContext:
    return await context_for_quote(session, quote_id)


async def _existing_mappings(
    session: AsyncSession, line_item_id: uuid.UUID
) -> list[TenderMapping]:
    result = await session.execute(
        select(TenderMapping).where(TenderMapping.line_item_id == line_item_id)
    )
    return list(result.scalars())


def _line_item_from_model(line_item: TenderLineItem) -> LineItemMappingInput:
    return LineItemMappingInput(
        description_raw=line_item.description_raw,
        section_path=tuple(line_item.section_path or ()),
        qty=float(line_item.qty) if line_item.qty is not None else None,
        unit=line_item.unit,
        amount_cents=line_item.amount_cents,
        item_status=line_item.item_status,
        embedding=list(line_item.embedding) if line_item.embedding is not None else None,
    )


def _add_mapping_rows(
    session: AsyncSession, line_item_id: uuid.UUID, decision: MappingDecision
) -> None:
    for allocation in decision.allocations:
        session.add(
            TenderMapping(
                line_item_id=line_item_id,
                cell_code=allocation.cell_code,
                allocation_fraction=allocation.allocation_fraction,
                tier=decision.tier,
                confidence=decision.confidence,
                adjudication=decision.adjudication,
                qa_state=decision.qa_state,
            )
        )


def _default_llm_client() -> TenderLLMClient:
    from tender.llm.openai_client import AsyncOpenAITenderClient

    return AsyncOpenAITenderClient()


def _default_session_factory() -> SessionFactory:
    from app.database.session import get_session_factory

    return get_session_factory()


def _note_mapping_tier(tier: str, started: float) -> None:
    record_mapping_tier(
        tier,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
