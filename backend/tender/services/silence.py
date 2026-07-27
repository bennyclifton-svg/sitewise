from __future__ import annotations

import math
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from tender.llm.client import LLMAdjudicationResponse, TenderLLMClient
from tender.models import (
    Benchmark,
    TaxonomyCell,
    TaxonomySynonym,
    TenderCellStatus,
    TenderLineItem,
    TenderJob,
    TenderProjectTrade,
)
from tender.schemas import ProjectContext
from tender.seeds.load import normalize_phrase
from tender.services.context import context_for_quote
from tender.services.expectations import ConceptMap, predicate_matches

ALLOWED_OUTCOMES = ["excluded", "bundled", "ps_covered", "not_required", "ambiguous"]
DEFAULT_PS_SIMILARITY_THRESHOLD = 0.60
DEFAULT_EXCLUSION_TRIGRAM_THRESHOLD = 0.92
PROMPT_VERSION = "0.1.0"
PROMPT_PATH = Path(__file__).resolve().parents[1] / "llm" / "prompts" / (
    f"infer_silence_v{PROMPT_VERSION}.md"
)


@dataclass(frozen=True)
class SilenceSynonym:
    phrase: str
    embedding: Sequence[float] | None = None


@dataclass(frozen=True)
class SilenceCell:
    code: str
    name: str
    expected_because: Sequence[str]
    synonyms: Sequence[SilenceSynonym] = ()
    bundling_parents: Sequence[str] = ()
    benchmark_key: str | None = None
    applicability: Mapping[str, Any] | None = None
    anchor_cell_codes: Sequence[str] = ()


@dataclass(frozen=True)
class SilenceLineItem:
    id: str
    description: str
    item_status: str
    amount_cents: int | None = None
    allowance_cents: int | None = None
    embedding: Sequence[float] | None = None
    page_ref: dict[str, Any] | None = None


@dataclass(frozen=True)
class SilenceMappedCell:
    cell_code: str
    amount_cents: int | None


@dataclass(frozen=True)
class SilenceBenchmark:
    benchmark_key: str
    state: str
    region: str
    build_type: str
    spec_level: str
    p50_cents: int | None


@dataclass(frozen=True)
class EvidencePacket:
    packet: dict[str, Any]
    explicit_exclusion: dict[str, Any] | None = None


@dataclass(frozen=True)
class SilenceDecision:
    status: str
    qa_state: str
    confidence: float | None
    bundled_into_cell: str | None
    evidence: dict[str, Any]


@dataclass(frozen=True)
class AnchorCellParts:
    """One taxonomy cell contribution to a trade's silence evidence union."""

    code: str
    name: str
    synonyms: Sequence[SilenceSynonym] = ()
    bundling_parents: Sequence[str] = ()
    benchmark_key: str | None = None
    applicability: Mapping[str, Any] | None = None


def silence_cell_from_anchors(
    *,
    trade_code: str,
    trade_name: str,
    expected_because: Sequence[str],
    anchors: Sequence[AnchorCellParts],
) -> SilenceCell:
    """Build a SilenceCell whose synonyms/parents are the union of anchor cells."""
    synonym_by_phrase: dict[str, SilenceSynonym] = {}
    parents: list[str] = []
    seen_parents: set[str] = set()
    for anchor in anchors:
        for synonym in anchor.synonyms:
            key = normalize_phrase(synonym.phrase)
            if key and key not in synonym_by_phrase:
                synonym_by_phrase[key] = synonym
        for parent in anchor.bundling_parents:
            if parent not in seen_parents:
                parents.append(parent)
                seen_parents.add(parent)

    benchmark_key: str | None = None
    applicability: Mapping[str, Any] | None = None
    if len(anchors) == 1:
        benchmark_key = anchors[0].benchmark_key
        applicability = anchors[0].applicability

    return SilenceCell(
        code=trade_code,
        name=trade_name,
        expected_because=tuple(expected_because),
        synonyms=tuple(synonym_by_phrase.values()),
        bundling_parents=tuple(parents),
        benchmark_key=benchmark_key,
        applicability=applicability,
        anchor_cell_codes=tuple(anchor.code for anchor in anchors),
    )


def unanchored_silence_decision(
    row: TenderCellStatus,
) -> SilenceDecision:
    """Keep silent_ambiguous; unanchored trades skip LLM (Phase 6)."""
    prior = dict(row.evidence or {})
    prior.setdefault("cross_quote_presence", True)
    prior.setdefault(
        "cross_quote_note",
        "Trade is priced in at least one other quote but absent here.",
    )
    prior["silence_skip"] = "unanchored_trade"
    return SilenceDecision(
        status="silent_ambiguous",
        qa_state="needs_review",
        confidence=None,
        bundled_into_cell=None,
        evidence={
            **prior,
            "adjudication": {
                "outcome": "ambiguous",
                "stored_status": "silent_ambiguous",
                "confidence": None,
                "rationale": (
                    "Unanchored trade skipped LLM silence; cross-quote presence "
                    "remains the only expectation signal."
                ),
                "model": None,
                "prompt_version": None,
                "request_id": None,
                "cites": [],
                "downgraded": False,
                "source": "unanchored_trade_skip",
                "review_reason": "unanchored_trade",
            },
        },
    )


def assemble_evidence_packet(
    *,
    cell: SilenceCell,
    context: ProjectContext,
    line_items: Sequence[SilenceLineItem],
    mapped_cells: Sequence[SilenceMappedCell] = (),
    cells_by_code: Mapping[str, SilenceCell] | None = None,
    benchmarks: Sequence[SilenceBenchmark] = (),
    concepts: ConceptMap | None = None,
    ps_similarity_threshold: float = DEFAULT_PS_SIMILARITY_THRESHOLD,
    exclusion_trigram_threshold: float = DEFAULT_EXCLUSION_TRIGRAM_THRESHOLD,
) -> EvidencePacket:
    explicit_exclusions = _explicit_exclusions(
        cell,
        line_items,
        trigram_threshold=exclusion_trigram_threshold,
    )
    packet = {
        "cell": {
            "code": cell.code,
            "name": cell.name,
            "expected_because": list(cell.expected_because),
        },
        "explicit_exclusions": explicit_exclusions,
        "candidate_ps_lines": _candidate_ps_lines(
            cell,
            line_items,
            similarity_threshold=ps_similarity_threshold,
        ),
        "bundling_parents_present": _bundling_parents_present(
            cell,
            context,
            mapped_cells,
            cells_by_code or {},
            benchmarks,
        ),
        "context_signals": _context_signals(context),
        "not_required_candidate": _not_required_candidate(cell, context, concepts or {}),
        "allowed_outcomes": list(ALLOWED_OUTCOMES),
    }
    return EvidencePacket(
        packet=packet,
        explicit_exclusion=explicit_exclusions[0] if explicit_exclusions else None,
    )


async def adjudicate_silence_packet(
    packet: EvidencePacket,
    context: ProjectContext,
    *,
    llm_client: TenderLLMClient,
) -> SilenceDecision:
    response = await llm_client.adjudicate(
        _prompt_text(),
        ALLOWED_OUTCOMES,
        packet.packet,
        context,
        prompt_version=PROMPT_VERSION,
        model_key="tender_model_adjudicate_small",
    )
    return _decision_from_adjudication(packet, response)


async def infer_silence_from_packet(
    row: TenderCellStatus,
    packet: EvidencePacket,
    context: ProjectContext,
    *,
    llm_client: TenderLLMClient | None = None,
) -> SilenceDecision:
    if packet.explicit_exclusion is not None:
        decision = _explicit_exclusion_decision(packet)
    elif (decision := deterministic_silence_decision(packet)) is not None:
        pass
    else:
        decision = await adjudicate_silence_packet(
            packet,
            context,
            llm_client=llm_client or _default_llm_client(),
        )
    apply_silence_decision(row, decision)
    return decision


def apply_silence_decision(row: TenderCellStatus, decision: SilenceDecision) -> None:
    row.status = decision.status
    row.amount_cents = None
    row.bundled_into_cell = decision.bundled_into_cell
    row.evidence = decision.evidence
    row.confidence = decision.confidence
    row.qa_state = decision.qa_state


async def infer_silence(
    session: AsyncSession,
    job: TenderJob,
    *,
    llm_client: TenderLLMClient | None = None,
) -> None:
    if job.comparison_id is None or job.quote_id is None:
        raise ValueError("infer_silence job requires comparison_id and quote_id")
    payload = job.payload or {}
    cell_code = payload.get("cell_code")
    project_trade_id = _parse_optional_uuid(payload.get("project_trade_id"))

    if project_trade_id is not None:
        row = await _cell_status_row_by_trade(
            session, job.comparison_id, job.quote_id, project_trade_id
        )
    elif isinstance(cell_code, str) and cell_code:
        row = await _cell_status_row(session, job.comparison_id, job.quote_id, cell_code)
    else:
        raise ValueError(
            "infer_silence job payload requires cell_code or project_trade_id"
        )

    if row.project_trade_id is not None:
        trade = await _project_trade(session, row.project_trade_id)
        if not (trade.anchor_cell_codes or []):
            apply_silence_decision(row, unanchored_silence_decision(row))
            await session.flush()
            return

    context = await _context_for_quote(session, job.quote_id)
    packet = await _packet_from_db(session, row, context)
    await infer_silence_from_packet(
        row,
        packet,
        context,
        llm_client=llm_client,
    )
    await session.flush()


async def infer_silence_batch(
    session: AsyncSession,
    job: TenderJob,
    *,
    llm_client: TenderLLMClient | None = None,
) -> None:
    if job.comparison_id is None or job.quote_id is None:
        raise ValueError("infer_silence_batch job requires comparison_id and quote_id")
    payload = job.payload or {}
    cell_codes = payload.get("cell_codes")
    project_trade_ids = payload.get("project_trade_ids")

    has_cells = (
        isinstance(cell_codes, list)
        and cell_codes
        and all(isinstance(code, str) and code for code in cell_codes)
    )
    has_trades = (
        isinstance(project_trade_ids, list)
        and project_trade_ids
        and all(isinstance(value, str) and value for value in project_trade_ids)
    )
    if not has_cells and not has_trades:
        raise ValueError(
            "infer_silence_batch job payload requires cell_codes or project_trade_ids"
        )

    context = await _context_for_quote(session, job.quote_id)
    line_items = await _line_items(session, job.quote_id)
    mapped_cells = await _mapped_cells(session, job.comparison_id, job.quote_id)
    pending: list[tuple[TenderCellStatus, EvidencePacket]] = []

    if has_trades:
        trade_uuids = tuple(
            dict.fromkeys(uuid.UUID(value) for value in project_trade_ids)
        )
        rows_by_trade = await _cell_status_rows_by_trade(
            session,
            job.comparison_id,
            job.quote_id,
            trade_uuids,
        )
        trades_by_id = await _project_trades(session, trade_uuids)
        for trade_id in trade_uuids:
            row = rows_by_trade[trade_id]
            trade = trades_by_id[trade_id]
            if not (trade.anchor_cell_codes or []):
                apply_silence_decision(row, unanchored_silence_decision(row))
                continue
            packet = await _packet_from_db(
                session,
                row,
                context,
                line_items=line_items,
                mapped_cells=mapped_cells,
                trade=trade,
            )
            if packet.explicit_exclusion is not None:
                apply_silence_decision(row, _explicit_exclusion_decision(packet))
                continue
            deterministic = deterministic_silence_decision(packet)
            if deterministic is not None:
                apply_silence_decision(row, deterministic)
                continue
            pending.append((row, packet))

    if has_cells:
        unique_cell_codes = tuple(dict.fromkeys(cell_codes))
        rows_by_code = await _cell_status_rows(
            session,
            job.comparison_id,
            job.quote_id,
            unique_cell_codes,
        )
        for cell_code in unique_cell_codes:
            row = rows_by_code[cell_code]
            packet = await _packet_from_db(
                session,
                row,
                context,
                line_items=line_items,
                mapped_cells=mapped_cells,
            )
            if packet.explicit_exclusion is not None:
                apply_silence_decision(row, _explicit_exclusion_decision(packet))
                continue
            deterministic = deterministic_silence_decision(packet)
            if deterministic is not None:
                apply_silence_decision(row, deterministic)
                continue
            pending.append((row, packet))

    if pending:
        decisions = await adjudicate_silence_packets(
            [packet for _, packet in pending],
            context,
            llm_client=llm_client or _default_llm_client(),
        )
        for (row, _packet), decision in zip(pending, decisions, strict=True):
            apply_silence_decision(row, decision)

    await session.flush()


def deterministic_silence_decision(packet: EvidencePacket) -> SilenceDecision | None:
    if packet.explicit_exclusion is not None:
        return _explicit_exclusion_decision(packet)
    evidence = packet.packet
    if evidence.get("not_required_candidate") is True:
        return _deterministic_not_required_decision(packet)
    if (
        not evidence.get("explicit_exclusions")
        and not evidence.get("candidate_ps_lines")
        and not evidence.get("bundling_parents_present")
    ):
        return _deterministic_ambiguous_decision(packet)
    return None


async def adjudicate_silence_packets(
    packets: Sequence[EvidencePacket],
    context: ProjectContext,
    *,
    llm_client: TenderLLMClient,
) -> tuple[SilenceDecision, ...]:
    if not packets:
        return ()

    adjudicate_many = getattr(llm_client, "adjudicate_many", None)
    if adjudicate_many is not None:
        responses = await adjudicate_many(
            _prompt_text(),
            ALLOWED_OUTCOMES,
            [packet.packet for packet in packets],
            context,
            prompt_version=PROMPT_VERSION,
            model_key="tender_model_adjudicate_small",
        )
    else:
        responses = [
            await llm_client.adjudicate(
                _prompt_text(),
                ALLOWED_OUTCOMES,
                packet.packet,
                context,
                prompt_version=PROMPT_VERSION,
                model_key="tender_model_adjudicate_small",
            )
            for packet in packets
        ]
    if len(responses) != len(packets):
        raise ValueError(
            f"silence batch returned {len(responses)} decisions for {len(packets)} packets"
        )
    return tuple(
        _decision_from_adjudication(packet, response)
        for packet, response in zip(packets, responses, strict=True)
    )


def _explicit_exclusions(
    cell: SilenceCell,
    line_items: Sequence[SilenceLineItem],
    *,
    trigram_threshold: float,
) -> list[dict[str, Any]]:
    synonyms = [normalize_phrase(synonym.phrase) for synonym in cell.synonyms]
    matches: list[dict[str, Any]] = []
    for item in line_items:
        if item.item_status != "excluded":
            continue
        description_norm = normalize_phrase(item.description)
        best = max(
            (_phrase_similarity(synonym, description_norm) for synonym in synonyms),
            default=0.0,
        )
        if best < trigram_threshold:
            continue
        matches.append(
            {
                "line_item_id": item.id,
                "description": item.description,
                "similarity": round(best, 4),
                "page_ref": item.page_ref,
            }
        )
    return sorted(matches, key=lambda match: (-match["similarity"], match["line_item_id"]))


def _candidate_ps_lines(
    cell: SilenceCell,
    line_items: Sequence[SilenceLineItem],
    *,
    similarity_threshold: float,
) -> list[dict[str, Any]]:
    synonym_embeddings = [
        synonym.embedding for synonym in cell.synonyms if synonym.embedding is not None
    ]
    candidates: list[dict[str, Any]] = []
    for item in line_items:
        if item.item_status != "ps_allowance" or item.embedding is None:
            continue
        similarity = max(
            (_cosine_similarity(item.embedding, synonym) for synonym in synonym_embeddings),
            default=0.0,
        )
        if similarity < similarity_threshold:
            continue
        candidates.append(
            {
                "line_item_id": item.id,
                "description": item.description,
                "allowance_cents": item.allowance_cents,
                "similarity": round(similarity, 4),
                "page_ref": item.page_ref,
            }
        )
    return sorted(candidates, key=lambda candidate: (-candidate["similarity"], candidate["line_item_id"]))


def _bundling_parents_present(
    cell: SilenceCell,
    context: ProjectContext,
    mapped_cells: Sequence[SilenceMappedCell],
    cells_by_code: Mapping[str, SilenceCell],
    benchmarks: Sequence[SilenceBenchmark],
) -> list[dict[str, Any]]:
    mapped_by_cell = {mapped.cell_code: mapped for mapped in mapped_cells}
    rows: list[dict[str, Any]] = []
    for parent_code in cell.bundling_parents:
        mapped_parent = mapped_by_cell.get(parent_code)
        if mapped_parent is None or mapped_parent.amount_cents is None:
            continue
        parent = cells_by_code.get(parent_code)
        parent_p50 = _benchmark_p50(parent.benchmark_key if parent else None, context, benchmarks)
        cell_p50 = _benchmark_p50(cell.benchmark_key, context, benchmarks)
        rows.append(
            {
                "cell": parent_code,
                "quote_amount_cents": mapped_parent.amount_cents,
                "benchmark_p50_parent_cents": parent_p50,
                "benchmark_p50_this_cell_cents": cell_p50,
                "headroom_assessment": _headroom_assessment(
                    mapped_parent.amount_cents,
                    parent_p50,
                    cell_p50,
                ),
            }
        )
    return rows


def _benchmark_p50(
    benchmark_key: str | None,
    context: ProjectContext,
    benchmarks: Sequence[SilenceBenchmark],
) -> int | None:
    if benchmark_key is None:
        return None
    for benchmark in benchmarks:
        if (
            benchmark.benchmark_key == benchmark_key
            and benchmark.state == context.state
            and benchmark.region == context.region
            and benchmark.build_type == context.build_type
            and benchmark.spec_level == context.spec_level
        ):
            return benchmark.p50_cents
    return None


def _headroom_assessment(
    parent_amount_cents: int,
    parent_p50: int | None,
    cell_p50: int | None,
) -> str:
    if parent_p50 is None or cell_p50 is None:
        return "unknown headroom"
    combined = parent_p50 + cell_p50
    delta = parent_amount_cents - combined
    if abs(delta) <= combined * 0.10:
        return "parent ~= p50(parent)+p50(cell)"
    if delta > 0:
        return "parent > p50(parent)+p50(cell)"
    return "parent < p50(parent)+p50(cell)"


def _not_required_candidate(
    cell: SilenceCell,
    context: ProjectContext,
    concepts: ConceptMap,
) -> bool:
    if cell.applicability is None:
        return False
    return not predicate_matches(cell.applicability, context, concepts=concepts)


def _context_signals(context: ProjectContext) -> dict[str, Any]:
    return {
        key: value
        for key, value in context.model_dump(mode="json").items()
        if value is not None
    }


def _phrase_similarity(synonym_norm: str, description_norm: str) -> float:
    if synonym_norm == description_norm or synonym_norm in description_norm:
        return 1.0
    left = _trigrams(synonym_norm)
    right = _trigrams(description_norm)
    if not left or not right:
        return 0.0
    return (2 * len(left & right)) / (len(left) + len(right))


def _trigrams(value: str) -> set[str]:
    padded = f"  {value} "
    return {padded[index : index + 3] for index in range(len(padded) - 2)}


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _decision_from_adjudication(
    packet: EvidencePacket,
    response: LLMAdjudicationResponse,
) -> SilenceDecision:
    stored_status = _status_for_outcome(response.choice)
    downgraded = response.choice == "excluded"
    return SilenceDecision(
        status=stored_status,
        qa_state="needs_review",
        confidence=response.confidence,
        bundled_into_cell=_bundled_parent(packet) if stored_status == "bundled" else None,
        evidence={
            "packet": packet.packet,
            "adjudication": {
                "outcome": response.choice,
                "stored_status": stored_status,
                "confidence": response.confidence,
                "rationale": response.rationale,
                "model": response.model,
                "prompt_version": response.prompt_version,
                "request_id": response.request_id,
                "cites": [],
                "downgraded": downgraded,
                "review_reason": _review_reason(response),
            },
        },
    )


def _explicit_exclusion_decision(packet: EvidencePacket) -> SilenceDecision:
    assert packet.explicit_exclusion is not None
    line_item_id = packet.explicit_exclusion["line_item_id"]
    return SilenceDecision(
        status="excluded_explicit",
        qa_state="needs_review",
        confidence=packet.explicit_exclusion.get("similarity"),
        bundled_into_cell=None,
        evidence={
            "packet": packet.packet,
            "adjudication": {
                "outcome": "excluded_explicit",
                "stored_status": "excluded_explicit",
                "confidence": packet.explicit_exclusion.get("similarity"),
                "rationale": "Explicit exclusion matched the expected cell synonyms.",
                "model": None,
                "prompt_version": None,
                "request_id": None,
                "cites": [line_item_id],
                "downgraded": False,
                "source": "explicit_exclusion_match",
                "review_reason": "silence_never_auto_pass_v1",
            },
        },
    )


def _deterministic_not_required_decision(packet: EvidencePacket) -> SilenceDecision:
    return SilenceDecision(
        status="not_required",
        qa_state="needs_review",
        confidence=1.0,
        bundled_into_cell=None,
        evidence={
            "packet": packet.packet,
            "adjudication": {
                "outcome": "not_required",
                "stored_status": "not_required",
                "confidence": 1.0,
                "rationale": "The taxonomy cell applicability predicate does not match the project context.",
                "model": None,
                "prompt_version": None,
                "request_id": None,
                "cites": [],
                "downgraded": False,
                "source": "deterministic_not_required",
                "review_reason": "silence_never_auto_pass_v1",
            },
        },
    )


def _deterministic_ambiguous_decision(packet: EvidencePacket) -> SilenceDecision:
    return SilenceDecision(
        status="silent_ambiguous",
        qa_state="needs_review",
        confidence=None,
        bundled_into_cell=None,
        evidence={
            "packet": packet.packet,
            "adjudication": {
                "outcome": "ambiguous",
                "stored_status": "silent_ambiguous",
                "confidence": None,
                "rationale": "No explicit exclusion, likely provisional sum, likely bundled parent, or not-required signal was found.",
                "model": None,
                "prompt_version": None,
                "request_id": None,
                "cites": [],
                "downgraded": False,
                "source": "deterministic_low_evidence_default",
                "review_reason": "ambiguous",
            },
        },
    )


def _status_for_outcome(outcome: str) -> str:
    return {
        "excluded": "silent_ambiguous",
        "bundled": "bundled",
        "ps_covered": "ps",
        "not_required": "not_required",
        "ambiguous": "silent_ambiguous",
    }[outcome]


def _review_reason(response: LLMAdjudicationResponse) -> str:
    if response.choice == "ambiguous":
        return "ambiguous"
    if response.confidence < _silence_review_confidence():
        return "low_confidence"
    return "silence_never_auto_pass_v1"


def _bundled_parent(packet: EvidencePacket) -> str | None:
    parents = packet.packet.get("bundling_parents_present", [])
    if not parents:
        return None
    return parents[0].get("cell")


async def _cell_status_row(
    session: AsyncSession,
    comparison_id: Any,
    quote_id: Any,
    cell_code: str,
) -> TenderCellStatus:
    result = await session.execute(
        select(TenderCellStatus).where(
            TenderCellStatus.comparison_id == comparison_id,
            TenderCellStatus.quote_id == quote_id,
            TenderCellStatus.cell_code == cell_code,
        )
    )
    return result.scalar_one()


async def _cell_status_row_by_trade(
    session: AsyncSession,
    comparison_id: Any,
    quote_id: Any,
    project_trade_id: uuid.UUID,
) -> TenderCellStatus:
    result = await session.execute(
        select(TenderCellStatus).where(
            TenderCellStatus.comparison_id == comparison_id,
            TenderCellStatus.quote_id == quote_id,
            TenderCellStatus.project_trade_id == project_trade_id,
        )
    )
    return result.scalar_one()


async def _cell_status_rows(
    session: AsyncSession,
    comparison_id: Any,
    quote_id: Any,
    cell_codes: Sequence[str],
) -> dict[str, TenderCellStatus]:
    result = await session.execute(
        select(TenderCellStatus).where(
            TenderCellStatus.comparison_id == comparison_id,
            TenderCellStatus.quote_id == quote_id,
            TenderCellStatus.cell_code.in_(list(cell_codes)),
        )
    )
    rows = {row.cell_code: row for row in result.scalars()}
    missing = [cell_code for cell_code in cell_codes if cell_code not in rows]
    if missing:
        raise ValueError(f"missing tender cell statuses: {', '.join(missing)}")
    return rows


async def _cell_status_rows_by_trade(
    session: AsyncSession,
    comparison_id: Any,
    quote_id: Any,
    trade_ids: Sequence[uuid.UUID],
) -> dict[uuid.UUID, TenderCellStatus]:
    result = await session.execute(
        select(TenderCellStatus).where(
            TenderCellStatus.comparison_id == comparison_id,
            TenderCellStatus.quote_id == quote_id,
            TenderCellStatus.project_trade_id.in_(list(trade_ids)),
        )
    )
    rows = {
        row.project_trade_id: row
        for row in result.scalars()
        if row.project_trade_id is not None
    }
    missing = [str(trade_id) for trade_id in trade_ids if trade_id not in rows]
    if missing:
        raise ValueError(f"missing tender trade statuses: {', '.join(missing)}")
    return rows


async def _context_for_quote(session: AsyncSession, quote_id: Any) -> ProjectContext:
    return await context_for_quote(session, quote_id)


async def _packet_from_db(
    session: AsyncSession,
    row: TenderCellStatus,
    context: ProjectContext,
    *,
    line_items: Sequence[SilenceLineItem] | None = None,
    mapped_cells: Sequence[SilenceMappedCell] | None = None,
    trade: TenderProjectTrade | None = None,
) -> EvidencePacket:
    if line_items is None:
        line_items = await _line_items(session, row.quote_id)
    else:
        line_items = tuple(line_items)
    if mapped_cells is None:
        mapped_cells = await _mapped_cells(session, row.comparison_id, row.quote_id)
    else:
        mapped_cells = tuple(mapped_cells)

    expected_because = tuple((row.evidence or {}).get("expected_because", ()))

    if row.project_trade_id is not None:
        if trade is None:
            trade = await _project_trade(session, row.project_trade_id)
        cell = await _silence_cell_for_trade(
            session,
            trade,
            expected_because=expected_because,
        )
        parent_cells = await _parent_cells(session, cell.bundling_parents)
        cells_by_code = {cell.code: cell, **parent_cells}
        # Also index anchor cells for parent benchmark lookups.
        for anchor_code in cell.anchor_cell_codes:
            if anchor_code not in cells_by_code:
                anchor_model = await _taxonomy_cell(session, anchor_code)
                cells_by_code[anchor_code] = _silence_cell_from_model(
                    anchor_model,
                    expected_because=(),
                    synonyms=(),
                )
    else:
        cell_model = await _taxonomy_cell(session, row.cell_code)
        synonyms = await _synonyms(session, row.cell_code)
        cell = _silence_cell_from_model(
            cell_model,
            expected_because=expected_because,
            synonyms=synonyms,
        )
        parent_cells = await _parent_cells(session, cell_model.bundling_parents or ())
        cells_by_code = {row.cell_code: cell, **parent_cells}

    benchmark_keys = [
        item.benchmark_key for item in cells_by_code.values() if item.benchmark_key
    ]
    return assemble_evidence_packet(
        cell=cell,
        context=context,
        line_items=line_items,
        mapped_cells=mapped_cells,
        cells_by_code=cells_by_code,
        benchmarks=await _benchmarks(session, benchmark_keys),
        ps_similarity_threshold=_silence_ps_similarity(),
    )


async def _silence_cell_for_trade(
    session: AsyncSession,
    trade: TenderProjectTrade,
    *,
    expected_because: Sequence[str],
) -> SilenceCell:
    anchor_codes = list(trade.anchor_cell_codes or [])
    if not anchor_codes:
        return SilenceCell(
            code=trade.code,
            name=trade.name,
            expected_because=tuple(expected_because),
            anchor_cell_codes=(),
        )
    anchors: list[AnchorCellParts] = []
    for code in anchor_codes:
        cell = await _taxonomy_cell(session, code)
        synonyms = await _synonyms(session, code)
        anchors.append(
            AnchorCellParts(
                code=cell.code,
                name=cell.name,
                synonyms=synonyms,
                bundling_parents=tuple(cell.bundling_parents or ()),
                benchmark_key=cell.benchmark_key,
                applicability=cell.applicability,
            )
        )
    return silence_cell_from_anchors(
        trade_code=trade.code,
        trade_name=trade.name,
        expected_because=expected_because,
        anchors=anchors,
    )


async def _project_trade(
    session: AsyncSession, project_trade_id: uuid.UUID
) -> TenderProjectTrade:
    result = await session.execute(
        select(TenderProjectTrade).where(TenderProjectTrade.id == project_trade_id)
    )
    return result.scalar_one()


async def _project_trades(
    session: AsyncSession, trade_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, TenderProjectTrade]:
    result = await session.execute(
        select(TenderProjectTrade).where(TenderProjectTrade.id.in_(list(trade_ids)))
    )
    trades = {trade.id: trade for trade in result.scalars()}
    missing = [str(trade_id) for trade_id in trade_ids if trade_id not in trades]
    if missing:
        raise ValueError(f"missing project trades: {', '.join(missing)}")
    return trades


async def _taxonomy_cell(session: AsyncSession, cell_code: str) -> TaxonomyCell:
    result = await session.execute(select(TaxonomyCell).where(TaxonomyCell.code == cell_code))
    return result.scalar_one()


async def _synonyms(session: AsyncSession, cell_code: str) -> tuple[SilenceSynonym, ...]:
    result = await session.execute(
        select(TaxonomySynonym).where(TaxonomySynonym.cell_code == cell_code)
    )
    return tuple(
        SilenceSynonym(
            phrase=synonym.phrase,
            embedding=tuple(synonym.embedding) if synonym.embedding is not None else None,
        )
        for synonym in result.scalars()
    )


async def _line_items(session: AsyncSession, quote_id: Any) -> tuple[SilenceLineItem, ...]:
    result = await session.execute(
        select(TenderLineItem)
        .where(TenderLineItem.quote_id == quote_id)
        .order_by(TenderLineItem.created_at)
    )
    return tuple(
        SilenceLineItem(
            id=str(item.id),
            description=item.description_raw,
            item_status=item.item_status,
            amount_cents=item.amount_cents,
            allowance_cents=item.allowance_cents,
            embedding=tuple(item.embedding) if item.embedding is not None else None,
            page_ref={"doc": str(item.document_id), "page": item.page_no},
        )
        for item in result.scalars()
    )


async def _mapped_cells(
    session: AsyncSession,
    comparison_id: Any,
    quote_id: Any,
) -> tuple[SilenceMappedCell, ...]:
    result = await session.execute(
        select(TenderCellStatus).where(
            TenderCellStatus.comparison_id == comparison_id,
            TenderCellStatus.quote_id == quote_id,
        )
    )
    statuses = list(result.scalars())
    mapped: list[SilenceMappedCell] = []
    trade_ids = list(
        dict.fromkeys(
            status.project_trade_id
            for status in statuses
            if status.project_trade_id is not None and status.amount_cents is not None
        )
    )
    trades_by_id: dict[uuid.UUID, TenderProjectTrade] = {}
    if trade_ids:
        trade_result = await session.execute(
            select(TenderProjectTrade).where(TenderProjectTrade.id.in_(trade_ids))
        )
        trades_by_id = {trade.id: trade for trade in trade_result.scalars()}

    for status in statuses:
        if status.cell_code:
            mapped.append(
                SilenceMappedCell(
                    cell_code=status.cell_code, amount_cents=status.amount_cents
                )
            )
            continue
        if status.project_trade_id is None or status.amount_cents is None:
            continue
        trade = trades_by_id.get(status.project_trade_id)
        if trade is None:
            continue
        for anchor in trade.anchor_cell_codes or []:
            mapped.append(
                SilenceMappedCell(cell_code=anchor, amount_cents=status.amount_cents)
            )
    return tuple(mapped)


async def _parent_cells(
    session: AsyncSession,
    parent_codes: Sequence[str],
) -> dict[str, SilenceCell]:
    if not parent_codes:
        return {}
    result = await session.execute(
        select(TaxonomyCell).where(TaxonomyCell.code.in_(list(parent_codes)))
    )
    return {
        cell.code: _silence_cell_from_model(cell, expected_because=(), synonyms=())
        for cell in result.scalars()
    }


async def _benchmarks(
    session: AsyncSession,
    benchmark_keys: Sequence[str],
) -> tuple[SilenceBenchmark, ...]:
    if not benchmark_keys:
        return ()
    result = await session.execute(
        select(Benchmark).where(Benchmark.benchmark_key.in_(list(benchmark_keys)))
    )
    return tuple(
        SilenceBenchmark(
            benchmark_key=benchmark.benchmark_key,
            state=benchmark.state,
            region=benchmark.region,
            build_type=benchmark.build_type,
            spec_level=benchmark.spec_level,
            p50_cents=int(benchmark.p50) if benchmark.p50 is not None else None,
        )
        for benchmark in result.scalars()
    )


def _silence_cell_from_model(
    cell: TaxonomyCell,
    *,
    expected_because: Sequence[str],
    synonyms: Sequence[SilenceSynonym],
) -> SilenceCell:
    return SilenceCell(
        code=cell.code,
        name=cell.name,
        expected_because=tuple(expected_because),
        synonyms=tuple(synonyms),
        bundling_parents=tuple(cell.bundling_parents or ()),
        benchmark_key=cell.benchmark_key,
        applicability=cell.applicability,
        anchor_cell_codes=(cell.code,),
    )


def _parse_optional_uuid(value: Any) -> uuid.UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        return uuid.UUID(value)
    raise ValueError(f"expected UUID, got {type(value).__name__}")


def _prompt_text() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _silence_ps_similarity() -> float:
    return float(
        getattr(settings, "tender_silence_ps_sim", DEFAULT_PS_SIMILARITY_THRESHOLD)
    )


def _silence_review_confidence() -> float:
    return float(getattr(settings, "tender_silence_review_conf", 0.75))


def _default_llm_client() -> TenderLLMClient:
    from tender.llm.openai_client import AsyncOpenAITenderClient

    return AsyncOpenAITenderClient()
