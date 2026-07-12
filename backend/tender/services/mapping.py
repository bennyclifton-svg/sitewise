from __future__ import annotations

import json
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

PROMPT_DIR = Path(__file__).resolve().parents[1] / "llm" / "prompts"
T2_PROMPT_VERSION = "0.1.0"
T3_PROMPT_VERSION = "0.1.0"
T2_PROMPT_PATH = PROMPT_DIR / f"map_items_t2_v{T2_PROMPT_VERSION}.md"
T3_PROMPT_PATH = PROMPT_DIR / f"map_items_t3_v{T3_PROMPT_VERSION}.md"


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
) -> None:
    if job.quote_id is None:
        raise ValueError("map_items job requires quote_id")
    llm_client = llm_client or _default_llm_client()
    context = await _context_for_quote(session, job.quote_id)
    result = await session.execute(
        select(TenderLineItem)
        .where(TenderLineItem.quote_id == job.quote_id)
        .order_by(TenderLineItem.created_at)
    )
    for line_item in result.scalars():
        existing = await _existing_mappings(session, line_item.id)
        if has_protected_mapping(existing):
            continue
        await session.execute(
            delete(TenderMapping).where(TenderMapping.line_item_id == line_item.id)
        )
        decision = await map_line_item_cascade(
            session,
            _line_item_from_model(line_item),
            context=context,
            llm_client=llm_client,
            frontier_client=frontier_client,
        )
        _add_mapping_rows(session, line_item.id, decision)
        await session.flush()
    quote = await session.get(TenderQuote, job.quote_id)
    if quote is not None:
        quote.stage = "run_expectations"


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
    t0_func = t0_func or t0_match
    t1_func = t1_func or t1_candidates
    t2_func = t2_func or t2_map_item
    t3_func = t3_func or t3_map_item
    cell_loader = cell_loader or load_cell_summaries
    active_cell_loader = active_cell_loader or load_active_cell_summaries

    t0_candidates = await t0_func(session, normalize_phrase(item.description_raw))
    if t0_candidates:
        return _candidate_decision("t0_exact", t0_candidates[0])

    t1 = await t1_func(session, item.embedding or [], 5) if item.embedding else []
    accepted = accept_t1_candidate(t1)
    if accepted is not None:
        return _candidate_decision("t1_embedding", accepted)

    if t1:
        candidate_cells = await cell_loader(session, [candidate.cell_code for candidate in t1])
        t2_decision = await t2_func(
            item=item,
            candidates=t1,
            candidate_cells=candidate_cells,
            context=context,
            llm_client=llm_client,
        )
        if not t2_decision.escalate_to_t3:
            return t2_decision

    active_cells = await active_cell_loader(session)
    return await t3_func(
        item=item,
        active_cells=active_cells,
        context=context,
        frontier_client=frontier_client,
    )


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

    return sorted(by_cell.values(), key=lambda candidate: candidate.similarity, reverse=True)[
        :limit
    ]


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
        .where(TaxonomyCell.active.is_(True))
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
    cells_by_code = {cell.code: cell for cell in candidate_cells}
    ordered_cells = [cells_by_code[candidate.cell_code] for candidate in candidates]
    choices = [candidate.cell_code for candidate in candidates] + ["none_of_these"]
    response = await llm_client.adjudicate(
        _prompt_text(T2_PROMPT_PATH),
        choices,
        {
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
        },
        context,
        prompt_version=T2_PROMPT_VERSION,
        model_key="tender_model_adjudicate_small",
    )
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
