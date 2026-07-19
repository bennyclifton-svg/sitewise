"""Per-comparison project trade taxonomy (Phase 4).

Trades replace the fixed seed matrix rows when present. Legacy comparisons
without trades keep the canonical cell_code path.
"""

from __future__ import annotations

import itertools
import json
import math
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from tender.llm.schema import openai_strict_json_schema
from tender.models import (
    TaxonomyCell,
    TenderComparison,
    TenderJob,
    TenderLineItem,
    TenderProjectTrade,
    TenderQuote,
    UNALLOCATED_TRADE_CODE,
)
from tender.schemas import ProjectContext, ProjectTradesResponse, ProjectTradeView
from tender.services import jobs
from tender.services.embedding import (
    EmbeddingClient,
    EmbeddingTarget,
    OpenAIEmbeddingClient,
    embed_targets,
)
from tender.services.telemetry import note_openai_response

UNALLOCATED_TRADE_NAME = "Unallocated / uncategorised"
PROMPT_VERSION = "0.1.0"
PROMPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "llm"
    / "prompts"
    / f"generate_project_taxonomy_v{PROMPT_VERSION}.md"
)
LABEL_COSINE_THRESHOLD = 0.75
AMOUNT_BAND_RATIO = 0.15


@dataclass(frozen=True)
class CountedSection:
    section_label: str
    amount_ex_gst_cents: int | None
    figure_key: str


@dataclass(frozen=True)
class AlignmentHint:
    left_quote_id: str
    left_figure_keys: tuple[str, ...]
    right_quote_id: str
    right_figure_keys: tuple[str, ...]
    reason: Literal["label_cosine", "amount_band"]
    score: float


@dataclass(frozen=True)
class TradeDraft:
    code: str
    name: str
    description: str | None
    group_label: str | None
    sort_order: int
    seed_assignments: list[dict[str, str]]
    anchor_cell_codes: list[str]
    anchor_confidence: float | None
    source: str = "generated"


class ProjectTaxonomyLLMClient(Protocol):
    async def generate_project_taxonomy(
        self,
        *,
        context: ProjectContext,
        sections_by_quote: Mapping[str, Sequence[dict[str, Any]]],
        hints: Sequence[dict[str, Any]],
        cell_catalog: Sequence[dict[str, str]],
    ) -> dict[str, Any]:
        ...


class PerQuoteSections(BaseModel):
    quote_id: str
    figure_keys: list[str] = Field(default_factory=list)


class GeneratedTrade(BaseModel):
    code: str
    name: str
    description: str | None = None
    group_label: str | None = None
    sort_order: int = 0
    per_quote_sections: list[PerQuoteSections] = Field(default_factory=list)
    anchor_cell_codes: list[str] | None = None
    confidence: float = 0.0


class GenerateProjectTaxonomyOutput(BaseModel):
    trades: list[GeneratedTrade] = Field(default_factory=list)


class OpenAIProjectTaxonomyClient:
    def __init__(
        self,
        client: AsyncOpenAI | None = None,
        *,
        model: str | None = None,
        prompt_path: Path = PROMPT_PATH,
    ) -> None:
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = model or settings.tender_model_adjudicate_frontier
        self.prompt_path = prompt_path

    async def generate_project_taxonomy(
        self,
        *,
        context: ProjectContext,
        sections_by_quote: Mapping[str, Sequence[dict[str, Any]]],
        hints: Sequence[dict[str, Any]],
        cell_catalog: Sequence[dict[str, str]],
    ) -> dict[str, Any]:
        schema = GenerateProjectTaxonomyOutput.model_json_schema()
        response = await self.client.responses.create(
            model=self.model,
            instructions=self.prompt_path.read_text(encoding="utf-8"),
            input=json.dumps(
                {
                    "project_context": context.model_dump(mode="json"),
                    "sections_by_quote": dict(sections_by_quote),
                    "alignment_hints": list(hints),
                    "cell_catalog": list(cell_catalog),
                },
                ensure_ascii=True,
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "generate_project_taxonomy",
                    "schema": openai_strict_json_schema(schema),
                    "strict": True,
                }
            },
            temperature=0,
        )
        note_openai_response(response)
        return json.loads(_response_text(response))


def select_counted_sections(items: Sequence[Any]) -> list[CountedSection]:
    """Pick counting-frontier rollups; fall back when a quote has no rollups."""
    live = [
        item
        for item in items
        if getattr(item, "duplicate_of_id", None) is None
        and getattr(item, "figure_key", None)
    ]
    counted = [item for item in live if bool(getattr(item, "counted_in_total", False))]
    rollups = [item for item in counted if bool(getattr(item, "is_rollup", False))]
    if rollups:
        return [_to_section(item) for item in rollups]

    # No counted rollups (e.g. Montique lump + PS children): use children of
    # counted roots when present; else top-level counted / top-level items.
    counted_ids = {item.id for item in counted}
    children = [item for item in live if item.parent_id in counted_ids]
    if children:
        return [_to_section(item) for item in children]

    if counted:
        return [_to_section(item) for item in counted]

    top_level = [item for item in live if item.parent_id is None]
    return [_to_section(item) for item in top_level]


async def counted_sections(
    session: AsyncSession,
    quote_id: uuid.UUID,
) -> list[CountedSection]:
    result = await session.execute(
        select(TenderLineItem).where(TenderLineItem.quote_id == quote_id)
    )
    return select_counted_sections(list(result.scalars()))


async def alignment_hints(
    sections_by_quote: Mapping[uuid.UUID | str, Sequence[CountedSection]],
    *,
    embedder: EmbeddingClient | None = None,
    label_embeddings: Mapping[str, Sequence[float]] | None = None,
) -> list[AlignmentHint]:
    normalized = {
        str(quote_id): list(sections)
        for quote_id, sections in sections_by_quote.items()
    }
    embeddings = dict(label_embeddings or {})
    if label_embeddings is None:
        labels = sorted(
            {
                section.section_label
                for sections in normalized.values()
                for section in sections
                if section.section_label
            }
        )
        if labels:
            client = embedder or OpenAIEmbeddingClient()
            vectors = await client.embed_texts(
                labels, model=settings.tender_embed_model
            )
            embeddings = {
                label: vector for label, vector in zip(labels, vectors, strict=True)
            }

    hints: list[AlignmentHint] = []
    quote_ids = list(normalized)
    for left_id, right_id in itertools.combinations(quote_ids, 2):
        left_sections = normalized[left_id]
        right_sections = normalized[right_id]
        hints.extend(
            _label_cosine_hints(left_id, left_sections, right_id, right_sections, embeddings)
        )
        hints.extend(
            _amount_band_hints(left_id, left_sections, right_id, right_sections)
        )
    return hints


def post_validate_trades(
    llm_trades: Sequence[Mapping[str, Any] | GeneratedTrade],
    *,
    sections_by_quote: Mapping[str, Sequence[CountedSection]],
    known_cell_codes: set[str],
) -> list[TradeDraft]:
    """Drop unknown anchors, auto-trade unassigned sections, always add UNALLOC."""
    known_sections = {
        (str(quote_id), section.figure_key)
        for quote_id, sections in sections_by_quote.items()
        for section in sections
    }
    assigned: set[tuple[str, str]] = set()
    drafts: list[TradeDraft] = []
    used_codes: set[str] = set()

    for raw in llm_trades:
        trade = (
            raw
            if isinstance(raw, GeneratedTrade)
            else _coerce_generated_trade(raw)
        )
        if trade.code == UNALLOCATED_TRADE_CODE:
            continue
        code = trade.code.strip() or _next_auto_code(used_codes)
        used_codes.add(code)
        per_quote = _normalize_per_quote_sections(trade.per_quote_sections)
        seed: list[dict[str, str]] = []
        for quote_id, figure_keys in per_quote.items():
            for figure_key in figure_keys:
                key = (str(quote_id), str(figure_key))
                if key not in known_sections or key in assigned:
                    continue
                assigned.add(key)
                seed.append({"quote_id": str(quote_id), "figure_key": str(figure_key)})

        anchors = [
            code_
            for code_ in (trade.anchor_cell_codes or [])
            if code_ in known_cell_codes
        ]
        drafts.append(
            TradeDraft(
                code=code,
                name=trade.name,
                description=trade.description,
                group_label=trade.group_label,
                sort_order=int(trade.sort_order),
                seed_assignments=seed,
                anchor_cell_codes=anchors,
                anchor_confidence=(
                    float(trade.confidence) if trade.confidence is not None else None
                ),
            )
        )

    auto_index = 1
    for quote_id, sections in sections_by_quote.items():
        for section in sections:
            key = (str(quote_id), section.figure_key)
            if key in assigned:
                continue
            assigned.add(key)
            code = _next_auto_code(used_codes, start=auto_index)
            used_codes.add(code)
            auto_index += 1
            drafts.append(
                TradeDraft(
                    code=code,
                    name=section.section_label,
                    description=None,
                    group_label=None,
                    sort_order=10_000 - auto_index,
                    seed_assignments=[
                        {"quote_id": str(quote_id), "figure_key": section.figure_key}
                    ],
                    anchor_cell_codes=[],
                    anchor_confidence=None,
                )
            )

    drafts.append(
        TradeDraft(
            code=UNALLOCATED_TRADE_CODE,
            name=UNALLOCATED_TRADE_NAME,
            description="Fallback row for items that could not be assigned a trade",
            group_label="Unallocated",
            sort_order=10_000,
            seed_assignments=[],
            anchor_cell_codes=[],
            anchor_confidence=None,
        )
    )
    return drafts


async def generate_project_taxonomy(
    session: AsyncSession,
    job: TenderJob,
    *,
    llm_client: ProjectTaxonomyLLMClient | None = None,
    embedder: EmbeddingClient | None = None,
) -> None:
    """Fan-in stage: build trades then enqueue map_items per quote."""
    if job.comparison_id is None:
        return

    comparison_id = job.comparison_id
    payload = job.payload if isinstance(job.payload, dict) else {}
    regenerate = bool(payload.get("regenerate"))

    existing = await session.execute(
        select(TenderProjectTrade.id).where(
            TenderProjectTrade.comparison_id == comparison_id
        )
    )
    existing_ids = list(existing.scalars())
    if existing_ids and not regenerate:
        await _enqueue_map_items_for_quotes(session, comparison_id=comparison_id)
        return

    if existing_ids and regenerate:
        await session.execute(
            delete(TenderProjectTrade).where(
                TenderProjectTrade.comparison_id == comparison_id
            )
        )
        await session.flush()

    quote_result = await session.execute(
        select(TenderQuote.id).where(TenderQuote.comparison_id == comparison_id)
    )
    quote_ids = list(quote_result.scalars())

    sections_by_quote: dict[str, list[CountedSection]] = {}
    for quote_id in quote_ids:
        sections_by_quote[str(quote_id)] = await counted_sections(session, quote_id)

    hints = await alignment_hints(sections_by_quote, embedder=embedder)

    comparison = await session.get(TenderComparison, comparison_id)
    if comparison is None:
        await _enqueue_map_items_for_quotes(session, comparison_id=comparison_id)
        return
    context = ProjectContext.model_validate(comparison.context)

    cell_result = await session.execute(
        select(TaxonomyCell)
        .where(TaxonomyCell.active.is_(True))
        .order_by(TaxonomyCell.sort_order, TaxonomyCell.code)
    )
    cell_catalog: list[dict[str, str]] = []
    known_codes: set[str] = set()
    for cell in cell_result.scalars():
        code = str(cell.code)
        cell_catalog.append({"code": code, "name": str(cell.name)})
        known_codes.add(code)

    client = llm_client or OpenAIProjectTaxonomyClient()
    llm_payload = await client.generate_project_taxonomy(
        context=context,
        sections_by_quote={
            quote_id: [
                {
                    "section_label": section.section_label,
                    "amount_ex_gst_cents": section.amount_ex_gst_cents,
                    "figure_key": section.figure_key,
                }
                for section in sections
            ]
            for quote_id, sections in sections_by_quote.items()
        },
        hints=[
            {
                "left_quote_id": hint.left_quote_id,
                "left_figure_keys": list(hint.left_figure_keys),
                "right_quote_id": hint.right_quote_id,
                "right_figure_keys": list(hint.right_figure_keys),
                "reason": hint.reason,
                "score": hint.score,
            }
            for hint in hints
        ],
        cell_catalog=cell_catalog,
    )

    raw_trades = llm_payload.get("trades", []) if isinstance(llm_payload, dict) else []
    drafts = post_validate_trades(
        raw_trades,
        sections_by_quote=sections_by_quote,
        known_cell_codes=known_codes,
    )

    embedder = embedder or OpenAIEmbeddingClient()
    trade_rows: list[TenderProjectTrade] = []
    for draft in drafts:
        row = TenderProjectTrade(
            id=uuid.uuid4(),
            comparison_id=comparison_id,
            code=draft.code,
            name=draft.name,
            description=draft.description,
            group_label=draft.group_label,
            sort_order=draft.sort_order,
            source=draft.source,
            anchor_cell_codes=list(draft.anchor_cell_codes) or None,
            anchor_confidence=draft.anchor_confidence,
            seed_assignments=list(draft.seed_assignments),
        )
        session.add(row)
        trade_rows.append(row)

    await session.flush()

    by_id = {row.id: row for row in trade_rows}
    await embed_targets(
        [
            EmbeddingTarget(
                id=row.id,
                text=_embed_text(row.name, row.description),
                embedding=None,
            )
            for row in trade_rows
        ],
        embedder=embedder,
        write_embedding=lambda trade_id, vector: setattr(
            by_id[trade_id], "embedding", vector
        ),
        model=settings.tender_embed_model,
        dimensions=settings.tender_embedding_dimensions,
    )
    await session.flush()

    await _enqueue_map_items_for_quotes(session, comparison_id=comparison_id)


async def _enqueue_map_items_for_quotes(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> None:
    result = await session.execute(
        select(TenderQuote.id).where(TenderQuote.comparison_id == comparison_id)
    )
    quote_ids = list(result.scalars())
    for quote_id in quote_ids:
        await jobs.enqueue(
            session,
            kind="map_items",
            comparison_id=comparison_id,
            quote_id=quote_id,
            payload={"reason": "project_taxonomy_ready"},
        )


async def list_project_trades(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> ProjectTradesResponse:
    result = await session.execute(
        select(TenderProjectTrade)
        .where(TenderProjectTrade.comparison_id == comparison_id)
        .order_by(TenderProjectTrade.sort_order, TenderProjectTrade.code)
    )
    rows = list(result.scalars())
    trades = [_trade_view(row) for row in rows]
    if not any(trade.code == UNALLOCATED_TRADE_CODE for trade in trades):
        trades.append(
            ProjectTradeView(
                id=None,
                code=UNALLOCATED_TRADE_CODE,
                name=UNALLOCATED_TRADE_NAME,
                description="Fallback row for items that could not be assigned a trade",
                group_label="Unallocated",
                sort_order=10_000,
                source="reserved",
                anchor_cell_codes=[],
                anchor_confidence=None,
            )
        )
    return ProjectTradesResponse(comparison_id=comparison_id, trades=trades)


def _trade_view(row: TenderProjectTrade) -> ProjectTradeView:
    return ProjectTradeView(
        id=row.id,
        code=row.code,
        name=row.name,
        description=row.description,
        group_label=row.group_label,
        sort_order=row.sort_order,
        source=row.source if row.source in ("generated", "manual") else "generated",
        anchor_cell_codes=list(row.anchor_cell_codes or []),
        anchor_confidence=(
            float(row.anchor_confidence) if row.anchor_confidence is not None else None
        ),
    )


def _to_section(item: Any) -> CountedSection:
    label = str(getattr(item, "description_raw", "") or "")
    path = getattr(item, "section_path", None)
    if not label and isinstance(path, list) and path:
        label = str(path[-1])
    amount = getattr(item, "amount_ex_gst_cents", None)
    if amount is not None:
        amount = int(amount)
    return CountedSection(
        section_label=label,
        amount_ex_gst_cents=amount,
        figure_key=str(item.figure_key),
    )


def _label_cosine_hints(
    left_id: str,
    left_sections: Sequence[CountedSection],
    right_id: str,
    right_sections: Sequence[CountedSection],
    embeddings: Mapping[str, Sequence[float]],
) -> list[AlignmentHint]:
    hints: list[AlignmentHint] = []
    for left in left_sections:
        left_vec = embeddings.get(left.section_label)
        if left_vec is None:
            continue
        for right in right_sections:
            right_vec = embeddings.get(right.section_label)
            if right_vec is None:
                continue
            score = _cosine_similarity(left_vec, right_vec)
            if score >= LABEL_COSINE_THRESHOLD:
                hints.append(
                    AlignmentHint(
                        left_quote_id=left_id,
                        left_figure_keys=(left.figure_key,),
                        right_quote_id=right_id,
                        right_figure_keys=(right.figure_key,),
                        reason="label_cosine",
                        score=score,
                    )
                )
    return hints


def _amount_band_hints(
    left_id: str,
    left_sections: Sequence[CountedSection],
    right_id: str,
    right_sections: Sequence[CountedSection],
) -> list[AlignmentHint]:
    """Emit one amount-band hint per left candidate.

    Among right candidates inside the band, prefer the match that involves more
    figure keys (so Cabinetry ≈ Joinery+benchtops beats Cabinetry ≈ Joinery),
    then the tighter relative delta.
    """
    hints: list[AlignmentHint] = []
    left_candidates = _amount_candidates(left_sections)
    right_candidates = _amount_candidates(right_sections)
    for left_keys, left_amount in left_candidates:
        matches: list[tuple[tuple[str, ...], float]] = []
        for right_keys, right_amount in right_candidates:
            ratio = _amount_band_ratio(left_amount, right_amount)
            if ratio is None or ratio > AMOUNT_BAND_RATIO:
                continue
            matches.append((right_keys, ratio))
        if not matches:
            continue
        right_keys, ratio = max(
            matches,
            key=lambda item: (len(left_keys) + len(item[0]), -item[1]),
        )
        hints.append(
            AlignmentHint(
                left_quote_id=left_id,
                left_figure_keys=left_keys,
                right_quote_id=right_id,
                right_figure_keys=right_keys,
                reason="amount_band",
                score=ratio,
            )
        )
    return hints


def _amount_candidates(
    sections: Sequence[CountedSection],
) -> list[tuple[tuple[str, ...], int]]:
    priced = [
        section
        for section in sections
        if section.amount_ex_gst_cents is not None and section.amount_ex_gst_cents > 0
    ]
    candidates: list[tuple[tuple[str, ...], int]] = []
    for section in priced:
        candidates.append(((section.figure_key,), int(section.amount_ex_gst_cents)))
    for a, b in itertools.combinations(priced, 2):
        candidates.append(
            (
                (a.figure_key, b.figure_key),
                int(a.amount_ex_gst_cents) + int(b.amount_ex_gst_cents),
            )
        )
    return candidates


def _amount_band_ratio(left: int, right: int) -> float | None:
    denom = max(left, right)
    if denom <= 0:
        return None
    return abs(left - right) / denom


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _coerce_generated_trade(raw: Mapping[str, Any]) -> GeneratedTrade:
    per_quote = raw.get("per_quote_sections")
    if isinstance(per_quote, dict):
        normalized = [
            {"quote_id": str(quote_id), "figure_keys": list(keys or [])}
            for quote_id, keys in per_quote.items()
        ]
        payload = {**dict(raw), "per_quote_sections": normalized}
        return GeneratedTrade.model_validate(payload)
    return GeneratedTrade.model_validate(dict(raw))


def _normalize_per_quote_sections(
    per_quote_sections: Sequence[PerQuoteSections] | Mapping[str, Sequence[str]],
) -> dict[str, list[str]]:
    if isinstance(per_quote_sections, Mapping):
        return {
            str(quote_id): [str(key) for key in keys]
            for quote_id, keys in per_quote_sections.items()
        }
    out: dict[str, list[str]] = {}
    for entry in per_quote_sections:
        out[str(entry.quote_id)] = [str(key) for key in entry.figure_keys]
    return out


def _next_auto_code(used: set[str], *, start: int = 1) -> str:
    index = start
    while True:
        code = f"PT.A{index:02d}"
        if code not in used:
            return code
        index += 1


def _embed_text(name: str, description: str | None) -> str:
    if description:
        return f"{name}\n{description}"
    return name


def _response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)
    for output in getattr(response, "output", []):
        for content in getattr(output, "content", []):
            text = getattr(content, "text", None)
            if text:
                return str(text)
    raise ValueError("OpenAI structured taxonomy response did not contain text")
