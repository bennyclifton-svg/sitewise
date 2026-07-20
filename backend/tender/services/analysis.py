from __future__ import annotations

import math
import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import (
    Benchmark,
    ReportLanguageEntry,
    TaxonomyCell,
    TenderAnalysisResult,
    TenderCellStatus,
    TenderComparison,
    TenderFlag,
    TenderJob,
    TenderProjectTrade,
    TenderQuote,
)
from tender.schemas import ProjectContext
from tender.services import jobs
from tender.services.benchmarks import (
    BenchmarkRow,
    PricedBenchmark,
    benchmark_row_from_model,
    inherit_benchmark_key,
    price_benchmark,
    resolve_benchmark,
)

ANALYSIS_VERSION = 1
PRESERVED_FLAG_QA_STATES = {"confirmed", "suppressed"}
QUESTION_SEVERITIES = {"warning", "caution"}


@dataclass(frozen=True)
class AnalysisQuote:
    id: str
    builder_name: str
    stated_total_cents: int | None


@dataclass(frozen=True)
class AnalysisCell:
    code: str
    name: str
    benchmark_key: str | None = None


@dataclass(frozen=True)
class AnalysisCellStatus:
    comparison_id: str
    quote_id: str
    cell_code: str
    status: str
    amount_cents: int | None = None
    bundled_into_cell: str | None = None
    evidence: Mapping[str, Any] | None = None
    confidence: float | None = None
    qa_state: str = "needs_review"


@dataclass(frozen=True)
class LedgerAdjustment:
    adjustment_type: str
    cell_code: str
    cell_name: str
    status: str
    amount_cents: int | None
    amount_range_cents: tuple[int, int] | None
    include_in_headline: bool
    phrase_key: str | None
    benchmark: dict[str, Any]
    evidence: dict[str, Any]


@dataclass(frozen=True)
class LedgerNote:
    severity: str
    note_key: str
    cell_code: str
    benchmark_key: str | None = None
    params: dict[str, Any] | None = None


@dataclass(frozen=True)
class ComparableLedger:
    quote_id: str
    builder_name: str
    stated_total_cents: int | None
    comparable_low_cents: int | None
    comparable_high_cents: int | None
    adjustments: tuple[LedgerAdjustment, ...]
    unquantified_items: tuple[LedgerNote, ...]
    notes: tuple[LedgerNote, ...]


@dataclass(frozen=True)
class AnalysisFlagDraft:
    comparison_id: str
    quote_id: str | None
    cell_code: str | None
    flag_type: str
    severity: str
    headline_key: str
    detail_key: str | None
    evidence: dict[str, Any]
    include_in_report: bool = True
    qa_state: str = "needs_review"


@dataclass(frozen=True)
class FlagMerge:
    preserved: tuple[AnalysisFlagDraft, ...]
    inserted: tuple[AnalysisFlagDraft, ...]
    deleted: tuple[AnalysisFlagDraft, ...]
    current: tuple[AnalysisFlagDraft, ...]


@dataclass(frozen=True)
class QuestionDraft:
    quote_id: str | None
    cell_code: str | None
    flag_type: str
    question: str


@dataclass(frozen=True)
class AnalysisResult:
    version: int
    gap_matrix: tuple[dict[str, Any], ...]
    ledgers: tuple[ComparableLedger, ...]
    questions: tuple[QuestionDraft, ...] = ()


def analyse_comparison(
    *,
    context: ProjectContext,
    quotes: Sequence[AnalysisQuote],
    cells: Sequence[AnalysisCell],
    statuses: Sequence[AnalysisCellStatus],
    benchmarks: Sequence[BenchmarkRow],
) -> AnalysisResult:
    return AnalysisResult(
        version=ANALYSIS_VERSION,
        gap_matrix=tuple(build_gap_matrix(quotes=quotes, cells=cells, statuses=statuses)),
        ledgers=tuple(
            build_comparable_ledgers(
                context=context,
                quotes=quotes,
                cells=cells,
                statuses=statuses,
                benchmarks=benchmarks,
            )
        ),
    )


def build_gap_matrix(
    *,
    quotes: Sequence[AnalysisQuote],
    cells: Sequence[AnalysisCell],
    statuses: Sequence[AnalysisCellStatus],
) -> list[dict[str, Any]]:
    status_by_key = {(status.quote_id, status.cell_code): status for status in statuses}
    rows: list[dict[str, Any]] = []
    for cell in sorted(cells, key=lambda item: item.code):
        rows.append(
            {
                "cell_code": cell.code,
                "cell_name": cell.name,
                "quotes": [
                    _matrix_cell(status_by_key.get((quote.id, cell.code)))
                    for quote in quotes
                ],
            }
        )
    return rows


def build_comparable_ledgers(
    *,
    context: ProjectContext,
    quotes: Sequence[AnalysisQuote],
    cells: Sequence[AnalysisCell],
    statuses: Sequence[AnalysisCellStatus],
    benchmarks: Sequence[BenchmarkRow],
) -> list[ComparableLedger]:
    cell_by_code = {cell.code: cell for cell in cells}
    statuses_by_quote: dict[str, list[AnalysisCellStatus]] = defaultdict(list)
    for status in statuses:
        statuses_by_quote[status.quote_id].append(status)

    ledgers: list[ComparableLedger] = []
    for quote in quotes:
        low_total = quote.stated_total_cents
        high_total = quote.stated_total_cents
        adjustments: list[LedgerAdjustment] = []
        notes: list[LedgerNote] = []
        unquantified: list[LedgerNote] = []

        for status in sorted(statuses_by_quote.get(quote.id, ()), key=lambda item: item.cell_code):
            cell = cell_by_code.get(status.cell_code)
            if cell is None or cell.benchmark_key is None:
                continue
            row = resolve_benchmark(benchmarks, cell.benchmark_key, context)
            if row is None:
                notes.append(
                    LedgerNote(
                        severity="info",
                        note_key="analysis.notes.no_benchmark_available",
                        cell_code=cell.code,
                        benchmark_key=cell.benchmark_key,
                    )
                )
                continue
            priced = price_benchmark(row, context, stated_total_cents=quote.stated_total_cents)
            if priced.skip_reason_key is not None:
                notes.append(
                    LedgerNote(
                        severity="info",
                        note_key=priced.skip_reason_key,
                        cell_code=cell.code,
                        benchmark_key=cell.benchmark_key,
                    )
                )
                continue

            line = _ledger_adjustment(status, cell, priced)
            if line is None:
                continue
            if isinstance(line, LedgerNote):
                unquantified.append(line)
                continue
            adjustments.append(line)
            if line.include_in_headline and low_total is not None and high_total is not None:
                low_delta, high_delta = _adjustment_bounds(line)
                low_total += low_delta
                high_total += high_delta

        ledgers.append(
            ComparableLedger(
                quote_id=quote.id,
                builder_name=quote.builder_name,
                stated_total_cents=quote.stated_total_cents,
                comparable_low_cents=low_total,
                comparable_high_cents=high_total,
                adjustments=tuple(adjustments),
                unquantified_items=tuple(unquantified),
                notes=tuple(notes),
            )
        )
    return ledgers


def generate_analysis_flags(
    *,
    context: ProjectContext,
    quotes: Sequence[AnalysisQuote],
    cells: Sequence[AnalysisCell],
    statuses: Sequence[AnalysisCellStatus],
    benchmarks: Sequence[BenchmarkRow],
) -> list[AnalysisFlagDraft]:
    flags: list[AnalysisFlagDraft] = []
    flags.extend(_gap_flags(cells=cells, statuses=statuses))
    flags.extend(
        _allowance_flags(
            context=context,
            cells=cells,
            statuses=statuses,
            benchmarks=benchmarks,
            quotes=quotes,
        )
    )
    flags.extend(_outlier_flags(cells=cells, statuses=statuses))
    return sorted(
        flags,
        key=lambda flag: (
            flag.flag_type,
            flag.quote_id or "",
            flag.cell_code or "",
            flag.severity,
        ),
    )


def build_question_list(
    flags: Sequence[AnalysisFlagDraft],
    *,
    quotes: Sequence[AnalysisQuote],
    cells: Sequence[AnalysisCell],
    question_templates: Mapping[str, str],
) -> list[QuestionDraft]:
    quote_by_id = {quote.id: quote for quote in quotes}
    cell_by_code = {cell.code: cell for cell in cells}
    questions: list[QuestionDraft] = []
    for flag in flags:
        if flag.severity not in QUESTION_SEVERITIES or not flag.include_in_report:
            continue
        if flag.qa_state == "suppressed":
            continue
        template = question_templates[flag.flag_type]
        quote = quote_by_id.get(flag.quote_id or "")
        cell = cell_by_code.get(flag.cell_code or "")
        questions.append(
            QuestionDraft(
                quote_id=flag.quote_id,
                cell_code=flag.cell_code,
                flag_type=flag.flag_type,
                question=template.format(
                    builder_name=quote.builder_name if quote else "",
                    cell_name=cell.name if cell else "",
                    amount=_format_cents(_question_amount(flag.evidence)),
                ),
            )
        )
    return questions


def merge_generated_flags(
    existing: Sequence[AnalysisFlagDraft],
    drafts: Sequence[AnalysisFlagDraft],
) -> FlagMerge:
    preserved = tuple(
        flag for flag in existing if flag.qa_state in PRESERVED_FLAG_QA_STATES
    )
    deleted = tuple(
        flag for flag in existing if flag.qa_state not in PRESERVED_FLAG_QA_STATES
    )
    protected = {_flag_identity(flag) for flag in preserved}
    inserted = tuple(flag for flag in drafts if _flag_identity(flag) not in protected)
    return FlagMerge(
        preserved=preserved,
        inserted=inserted,
        deleted=deleted,
        current=preserved + inserted,
    )


async def run_analysis(session: AsyncSession, job: TenderJob) -> None:
    if job.comparison_id is None:
        raise ValueError("comparison_id")
    inputs = await _analysis_inputs(session, job.comparison_id)
    result = analyse_comparison(
        context=inputs["context"],
        quotes=inputs["quotes"],
        cells=inputs["cells"],
        statuses=inputs["statuses"],
        benchmarks=inputs["benchmarks"],
    )
    await _upsert_analysis_result(session, job.comparison_id, result)
    await jobs.enqueue(
        session,
        kind="generate_flags",
        comparison_id=job.comparison_id,
        payload={"reason": "analysis_complete"},
    )
    await session.flush()


async def generate_flags(session: AsyncSession, job: TenderJob) -> None:
    if job.comparison_id is None:
        raise ValueError("comparison_id")
    inputs = await _analysis_inputs(session, job.comparison_id)
    result = analyse_comparison(
        context=inputs["context"],
        quotes=inputs["quotes"],
        cells=inputs["cells"],
        statuses=inputs["statuses"],
        benchmarks=inputs["benchmarks"],
    )
    drafts = generate_analysis_flags(
        context=inputs["context"],
        quotes=inputs["quotes"],
        cells=inputs["cells"],
        statuses=inputs["statuses"],
        benchmarks=inputs["benchmarks"],
    )
    current_flags = await _replace_generated_flags(session, job.comparison_id, drafts)
    questions = build_question_list(
        current_flags,
        quotes=inputs["quotes"],
        cells=inputs["cells"],
        question_templates=await _question_templates(session),
    )
    await _upsert_analysis_result(
        session,
        job.comparison_id,
        AnalysisResult(
            version=result.version,
            gap_matrix=result.gap_matrix,
            ledgers=result.ledgers,
            questions=tuple(questions),
        ),
    )
    comparison = await _comparison(session, job.comparison_id)
    from tender.services import qa

    try:
        await qa.assert_no_pending_review(session, comparison_id=job.comparison_id)
    except qa.PendingReviewError:
        comparison.status = "qa"
    else:
        comparison.status = "processing"
        await jobs.enqueue(
            session,
            kind="assemble_report_draft",
            comparison_id=job.comparison_id,
            payload={"reason": "qa_clear"},
        )
    await session.flush()


def analysis_result_to_json(result: AnalysisResult) -> dict[str, Any]:
    return _jsonable(asdict(result))


def _matrix_cell(status: AnalysisCellStatus | None) -> dict[str, Any]:
    if status is None:
        return {
            "status": None,
            "amount_cents": None,
            "qa_state": None,
            "confidence": None,
        }
    return {
        "status": status.status,
        "amount_cents": status.amount_cents,
        "bundled_into_cell": status.bundled_into_cell,
        "qa_state": status.qa_state,
        "confidence": status.confidence,
    }


def _ledger_adjustment(
    status: AnalysisCellStatus,
    cell: AnalysisCell,
    priced: PricedBenchmark,
) -> LedgerAdjustment | LedgerNote | None:
    if _is_gap_fill(status):
        return _fill_adjustment(status, cell, priced)
    if status.status in {"pc", "ps"}:
        return _topup_adjustment(status, cell, priced)
    return None


def _fill_adjustment(
    status: AnalysisCellStatus,
    cell: AnalysisCell,
    priced: PricedBenchmark,
) -> LedgerAdjustment | LedgerNote | None:
    if priced.row.confidence == "low":
        return _unquantified_note(status, cell, priced)
    if priced.row.confidence == "medium":
        if priced.p25_cents is None or priced.p75_cents is None:
            return _incomplete_benchmark_note(cell, priced)
        return _adjustment(
            adjustment_type="fill_at_benchmark",
            status=status,
            cell=cell,
            priced=priced,
            amount_cents=None,
            amount_range_cents=(priced.p25_cents, priced.p75_cents),
            phrase_key="claim_strength_by_benchmark_confidence.medium",
        )
    if priced.p50_cents is None:
        return _incomplete_benchmark_note(cell, priced)
    return _adjustment(
        adjustment_type="fill_at_benchmark",
        status=status,
        cell=cell,
        priced=priced,
        amount_cents=priced.p50_cents,
        amount_range_cents=None,
        phrase_key="claim_strength_by_benchmark_confidence.high",
    )


def _topup_adjustment(
    status: AnalysisCellStatus,
    cell: AnalysisCell,
    priced: PricedBenchmark,
) -> LedgerAdjustment | LedgerNote | None:
    allowance = status.amount_cents
    if allowance is None or priced.p25_cents is None:
        return None
    if allowance >= priced.p25_cents:
        return None
    if priced.row.confidence == "low":
        return _unquantified_note(status, cell, priced)
    if priced.row.confidence == "medium":
        if priced.p75_cents is None:
            return _incomplete_benchmark_note(cell, priced)
        return _adjustment(
            adjustment_type="allowance_topup",
            status=status,
            cell=cell,
            priced=priced,
            amount_cents=None,
            amount_range_cents=(
                max(0, priced.p25_cents - allowance),
                max(0, priced.p75_cents - allowance),
            ),
            phrase_key="claim_strength_by_benchmark_confidence.medium",
        )
    if priced.p50_cents is None:
        return _incomplete_benchmark_note(cell, priced)
    return _adjustment(
        adjustment_type="allowance_topup",
        status=status,
        cell=cell,
        priced=priced,
        amount_cents=max(0, priced.p50_cents - allowance),
        amount_range_cents=None,
        phrase_key="claim_strength_by_benchmark_confidence.high",
    )


def _adjustment(
    *,
    adjustment_type: str,
    status: AnalysisCellStatus,
    cell: AnalysisCell,
    priced: PricedBenchmark,
    amount_cents: int | None,
    amount_range_cents: tuple[int, int] | None,
    phrase_key: str,
) -> LedgerAdjustment:
    return LedgerAdjustment(
        adjustment_type=adjustment_type,
        cell_code=cell.code,
        cell_name=cell.name,
        status=status.status,
        amount_cents=amount_cents,
        amount_range_cents=amount_range_cents,
        include_in_headline=True,
        phrase_key=phrase_key,
        benchmark=_benchmark_evidence(priced),
        evidence=_status_evidence(status),
    )


def _unquantified_note(
    status: AnalysisCellStatus,
    cell: AnalysisCell,
    priced: PricedBenchmark,
) -> LedgerNote:
    return LedgerNote(
        severity="info",
        note_key="analysis.notes.low_confidence_unquantified",
        cell_code=cell.code,
        benchmark_key=priced.row.benchmark_key,
        params={
            "benchmark_id": priced.row.id,
            "status": status.status,
        },
    )


def _incomplete_benchmark_note(cell: AnalysisCell, priced: PricedBenchmark) -> LedgerNote:
    return LedgerNote(
        severity="info",
        note_key="analysis.notes.incomplete_benchmark",
        cell_code=cell.code,
        benchmark_key=priced.row.benchmark_key,
        params={"benchmark_id": priced.row.id},
    )


def _adjustment_bounds(line: LedgerAdjustment) -> tuple[int, int]:
    if line.amount_range_cents is not None:
        return line.amount_range_cents
    assert line.amount_cents is not None
    return line.amount_cents, line.amount_cents


def _is_gap_fill(status: AnalysisCellStatus) -> bool:
    return status.status == "excluded_explicit" or (
        status.status == "silent_ambiguous" and status.qa_state in {"confirmed", "corrected"}
    )


def _gap_flags(
    *,
    cells: Sequence[AnalysisCell],
    statuses: Sequence[AnalysisCellStatus],
) -> list[AnalysisFlagDraft]:
    cell_by_code = {cell.code: cell for cell in cells}
    flags: list[AnalysisFlagDraft] = []
    for status in statuses:
        if status.status == "excluded_explicit":
            flag_type = "exclusion_risk"
            severity = "warning"
        elif status.status == "silent_ambiguous" and status.qa_state in {"confirmed", "corrected"}:
            flag_type = "gap"
            severity = "warning"
        elif status.status == "silent_ambiguous":
            flag_type = "scope_ambiguity"
            severity = "caution"
        else:
            continue
        flags.append(
            _flag(
                comparison_id=status.comparison_id,
                quote_id=status.quote_id,
                cell=cell_by_code.get(status.cell_code),
                cell_code=status.cell_code,
                flag_type=flag_type,
                severity=severity,
                evidence=_status_evidence(status),
            )
        )
    return flags


def _allowance_flags(
    *,
    context: ProjectContext,
    quotes: Sequence[AnalysisQuote],
    cells: Sequence[AnalysisCell],
    statuses: Sequence[AnalysisCellStatus],
    benchmarks: Sequence[BenchmarkRow],
) -> list[AnalysisFlagDraft]:
    quote_by_id = {quote.id: quote for quote in quotes}
    cell_by_code = {cell.code: cell for cell in cells}
    flags: list[AnalysisFlagDraft] = []
    for status in statuses:
        if status.status not in {"pc", "ps"} or status.amount_cents is None:
            continue
        cell = cell_by_code.get(status.cell_code)
        quote = quote_by_id.get(status.quote_id)
        if cell is None or quote is None or cell.benchmark_key is None:
            continue
        row = resolve_benchmark(benchmarks, cell.benchmark_key, context)
        if row is None:
            continue
        priced = price_benchmark(row, context, stated_total_cents=quote.stated_total_cents)
        if not _is_low_allowance(status.amount_cents, priced):
            continue
        flag_type = "low_pc_allowance" if status.status == "pc" else "unrealistic_ps"
        severity = _allowance_severity(status.amount_cents, priced)
        flags.append(
            _flag(
                comparison_id=status.comparison_id,
                quote_id=status.quote_id,
                cell=cell,
                cell_code=status.cell_code,
                flag_type=flag_type,
                severity=severity,
                evidence={
                    **_status_evidence(status),
                    "allowance_cents": status.amount_cents,
                    "benchmark": _benchmark_evidence(priced),
                    "percentile_band": {
                        "p25_cents": priced.p25_cents,
                        "p50_cents": priced.p50_cents,
                        "p75_cents": priced.p75_cents,
                    },
                },
                include_in_report=row.confidence != "low",
                detail_key=None
                if row.confidence == "low"
                else f"claim_strength_by_benchmark_confidence.{row.confidence}",
            )
        )
    return flags


def _is_low_allowance(allowance_cents: int, priced: PricedBenchmark) -> bool:
    return (
        priced.skip_reason_key is None
        and priced.p25_cents is not None
        and allowance_cents < priced.p25_cents
    )


def _allowance_severity(allowance_cents: int, priced: PricedBenchmark) -> str:
    if priced.row.confidence == "low":
        return "info"
    if priced.p50_cents is None:
        return "caution"
    gap = max(0, priced.p50_cents - allowance_cents)
    return "caution" if gap * 4 < priced.p50_cents else "warning"


def _outlier_flags(
    *,
    cells: Sequence[AnalysisCell],
    statuses: Sequence[AnalysisCellStatus],
) -> list[AnalysisFlagDraft]:
    cell_by_code = {cell.code: cell for cell in cells}
    statuses_by_cell: dict[str, list[AnalysisCellStatus]] = defaultdict(list)
    for status in statuses:
        if status.amount_cents is not None:
            statuses_by_cell[status.cell_code].append(status)

    flags: list[AnalysisFlagDraft] = []
    for cell_code, cell_statuses in statuses_by_cell.items():
        if len(cell_statuses) < 3:
            continue
        amounts = [status.amount_cents for status in cell_statuses]
        assert all(amount is not None for amount in amounts)
        mean = sum(amounts) / len(amounts)
        stdev = math.sqrt(sum((amount - mean) ** 2 for amount in amounts) / len(amounts))
        if stdev == 0:
            continue
        for status in cell_statuses:
            assert status.amount_cents is not None
            z_score = (status.amount_cents - mean) / stdev
            if abs(z_score) < 2:
                continue
            flags.append(
                _flag(
                    comparison_id=status.comparison_id,
                    quote_id=status.quote_id,
                    cell=cell_by_code.get(cell_code),
                    cell_code=cell_code,
                    flag_type="price_outlier",
                    severity="info",
                    evidence={
                        **_status_evidence(status),
                        "amount_cents": status.amount_cents,
                        "mean_cents": int(round(mean)),
                        "z_score": round(z_score, 4),
                    },
                )
            )
    return flags


def _flag(
    *,
    comparison_id: str,
    quote_id: str | None,
    cell: AnalysisCell | None,
    cell_code: str | None,
    flag_type: str,
    severity: str,
    evidence: dict[str, Any],
    include_in_report: bool = True,
    detail_key: str | None = None,
) -> AnalysisFlagDraft:
    full_evidence = dict(evidence)
    if cell is not None:
        full_evidence.setdefault("cell", {"code": cell.code, "name": cell.name})
    return AnalysisFlagDraft(
        comparison_id=comparison_id,
        quote_id=quote_id,
        cell_code=cell_code,
        flag_type=flag_type,
        severity=severity,
        headline_key=f"flag_phrases.{flag_type}",
        detail_key=detail_key,
        evidence=full_evidence,
        include_in_report=include_in_report,
    )


def _benchmark_evidence(priced: PricedBenchmark) -> dict[str, Any]:
    return {
        "benchmark_id": priced.row.id,
        "benchmark_key": priced.row.benchmark_key,
        "metric": priced.row.metric,
        "confidence": priced.row.confidence,
        "source": priced.row.source,
        "provenance": priced.row.provenance,
        "effective_date": priced.row.effective_date.isoformat()
        if priced.row.effective_date
        else None,
    }


def _status_evidence(status: AnalysisCellStatus) -> dict[str, Any]:
    evidence = dict(status.evidence or {})
    return {
        "status": status.status,
        "amount_cents": status.amount_cents,
        "qa_state": status.qa_state,
        "page_refs": _page_refs(evidence),
        "source_evidence": evidence,
    }


def _page_refs(evidence: Mapping[str, Any]) -> list[Any]:
    if "page_refs" in evidence and isinstance(evidence["page_refs"], list):
        return list(evidence["page_refs"])
    refs: list[Any] = []
    packet = evidence.get("packet")
    if isinstance(packet, Mapping):
        for key in ("explicit_exclusions", "candidate_ps_lines"):
            values = packet.get(key)
            if isinstance(values, list):
                refs.extend(
                    value.get("page_ref")
                    for value in values
                    if isinstance(value, Mapping) and value.get("page_ref") is not None
                )
    return refs


def _question_amount(evidence: Mapping[str, Any]) -> int | None:
    for key in ("allowance_cents", "amount_cents"):
        amount = evidence.get(key)
        if isinstance(amount, int):
            return amount
    return None


def _format_cents(amount_cents: int | None) -> str:
    if amount_cents is None:
        return ""
    dollars = amount_cents // 100
    cents = abs(amount_cents) % 100
    if cents:
        return f"${dollars:,}.{cents:02d}"
    return f"${dollars:,}"


async def _analysis_inputs(session: AsyncSession, comparison_id: uuid.UUID) -> dict[str, Any]:
    comparison = await _comparison(session, comparison_id)
    context = ProjectContext.model_validate(comparison.context)
    quotes = [
        _quote_from_model(quote)
        for quote in await _scalars(
            session,
            select(TenderQuote)
            .where(TenderQuote.comparison_id == comparison_id)
            .order_by(TenderQuote.created_at),
        )
    ]
    status_rows = await _scalars(
        session,
        select(TenderCellStatus).where(TenderCellStatus.comparison_id == comparison_id),
    )
    trade_rows = await _scalars(
        session,
        select(TenderProjectTrade)
        .where(TenderProjectTrade.comparison_id == comparison_id)
        .order_by(TenderProjectTrade.sort_order, TenderProjectTrade.code),
    )

    if trade_rows:
        cells, statuses, benchmarks = await _trade_analysis_inputs(
            session, trade_rows, status_rows
        )
    else:
        cells, statuses, benchmarks = await _cell_analysis_inputs(session, status_rows)

    return {
        "context": context,
        "quotes": quotes,
        "cells": cells,
        "statuses": statuses,
        "benchmarks": benchmarks,
    }


async def _trade_analysis_inputs(
    session: AsyncSession,
    trade_rows: Sequence[TenderProjectTrade],
    status_rows: Sequence[TenderCellStatus],
) -> tuple[list[AnalysisCell], list[AnalysisCellStatus], list[BenchmarkRow]]:
    anchor_codes = sorted(
        {
            code
            for trade in trade_rows
            for code in (trade.anchor_cell_codes or [])
        }
    )
    taxonomy_cells = [
        cell
        for cell in await _scalars(
            session,
            select(TaxonomyCell).where(TaxonomyCell.code.in_(anchor_codes)),
        )
    ] if anchor_codes else []
    benchmark_key_by_cell = {
        cell.code: cell.benchmark_key for cell in taxonomy_cells
    }
    cells = [
        AnalysisCell(
            code=trade.code,
            name=trade.name,
            benchmark_key=inherit_benchmark_key(
                tuple(trade.anchor_cell_codes or ()),
                benchmark_key_by_cell,
            ),
        )
        for trade in trade_rows
    ]
    trade_code_by_id = {trade.id: trade.code for trade in trade_rows}
    statuses = [
        AnalysisCellStatus(
            comparison_id=str(row.comparison_id),
            quote_id=str(row.quote_id),
            cell_code=trade_code_by_id[row.project_trade_id],
            status=row.status,
            amount_cents=row.amount_cents,
            bundled_into_cell=row.bundled_into_cell,
            evidence=row.evidence,
            confidence=float(row.confidence) if row.confidence is not None else None,
            qa_state=row.qa_state,
        )
        for row in status_rows
        if row.project_trade_id is not None and row.project_trade_id in trade_code_by_id
    ]
    benchmark_keys = sorted({cell.benchmark_key for cell in cells if cell.benchmark_key})
    benchmarks = [
        benchmark_row_from_model(row)
        for row in await _scalars(
            session,
            select(Benchmark).where(Benchmark.benchmark_key.in_(benchmark_keys)),
        )
    ] if benchmark_keys else []
    return cells, statuses, benchmarks


async def _cell_analysis_inputs(
    session: AsyncSession,
    status_rows: Sequence[TenderCellStatus],
) -> tuple[list[AnalysisCell], list[AnalysisCellStatus], list[BenchmarkRow]]:
    statuses = [_status_from_model(row) for row in status_rows if row.cell_code]
    cell_codes = sorted({status.cell_code for status in statuses})
    cells = [
        _cell_from_model(cell)
        for cell in await _scalars(
            session,
            select(TaxonomyCell).where(TaxonomyCell.code.in_(cell_codes)),
        )
    ] if cell_codes else []
    benchmark_keys = sorted({cell.benchmark_key for cell in cells if cell.benchmark_key})
    benchmarks = [
        benchmark_row_from_model(row)
        for row in await _scalars(
            session,
            select(Benchmark).where(Benchmark.benchmark_key.in_(benchmark_keys)),
        )
    ] if benchmark_keys else []
    return cells, statuses, benchmarks


async def _replace_generated_flags(
    session: AsyncSession,
    comparison_id: uuid.UUID,
    drafts: Sequence[AnalysisFlagDraft],
) -> list[AnalysisFlagDraft]:
    existing = await _scalars(
        session,
        select(TenderFlag).where(TenderFlag.comparison_id == comparison_id),
    )
    existing_drafts = [_flag_from_model(flag) for flag in existing]
    merge = merge_generated_flags(existing_drafts, drafts)
    deleted = {_flag_identity(flag) for flag in merge.deleted}

    for flag in existing:
        if _flag_identity(_flag_from_model(flag)) in deleted:
            await session.delete(flag)
    for draft in merge.inserted:
        session.add(_flag_model(draft))
    return list(merge.current)


async def _upsert_analysis_result(
    session: AsyncSession,
    comparison_id: uuid.UUID,
    result: AnalysisResult,
) -> None:
    payload = analysis_result_to_json(result)
    existing = await _analysis_result_row(session, comparison_id)
    if existing is None:
        session.add(
            TenderAnalysisResult(
                comparison_id=comparison_id,
                version=result.version,
                gap_matrix=payload["gap_matrix"],
                ledgers=payload["ledgers"],
                questions=payload["questions"],
            )
        )
        return
    existing.version = result.version
    existing.gap_matrix = payload["gap_matrix"]
    existing.ledgers = payload["ledgers"]
    existing.questions = payload["questions"]


async def _analysis_result_row(
    session: AsyncSession,
    comparison_id: uuid.UUID,
) -> TenderAnalysisResult | None:
    result = await session.execute(
        select(TenderAnalysisResult).where(
            TenderAnalysisResult.comparison_id == comparison_id
        )
    )
    return result.scalar_one_or_none()


async def _question_templates(session: AsyncSession) -> dict[str, str]:
    rows = await _scalars(
        session,
        select(ReportLanguageEntry).where(
            ReportLanguageEntry.key_path.like("question_templates.%")
        ),
    )
    return {
        row.key_path.removeprefix("question_templates."): row.value
        for row in rows
        if isinstance(row.value, str)
    }


async def _comparison(session: AsyncSession, comparison_id: uuid.UUID) -> TenderComparison:
    result = await session.execute(
        select(TenderComparison).where(TenderComparison.id == comparison_id)
    )
    return result.scalar_one()


async def _scalars(session: AsyncSession, statement: Any) -> list[Any]:
    result = await session.execute(statement)
    return list(result.scalars())


def _quote_from_model(quote: TenderQuote) -> AnalysisQuote:
    return AnalysisQuote(
        id=str(quote.id),
        builder_name=quote.builder_name,
        stated_total_cents=quote.stated_total_cents,
    )


def _cell_from_model(cell: TaxonomyCell) -> AnalysisCell:
    return AnalysisCell(
        code=cell.code,
        name=cell.name,
        benchmark_key=cell.benchmark_key,
    )


def _status_from_model(row: TenderCellStatus) -> AnalysisCellStatus:
    return AnalysisCellStatus(
        comparison_id=str(row.comparison_id),
        quote_id=str(row.quote_id),
        cell_code=row.cell_code,
        status=row.status,
        amount_cents=row.amount_cents,
        bundled_into_cell=row.bundled_into_cell,
        evidence=row.evidence,
        confidence=float(row.confidence) if row.confidence is not None else None,
        qa_state=row.qa_state,
    )


def _flag_model(draft: AnalysisFlagDraft) -> TenderFlag:
    return TenderFlag(
        comparison_id=uuid.UUID(draft.comparison_id),
        quote_id=uuid.UUID(draft.quote_id) if draft.quote_id else None,
        cell_code=draft.cell_code,
        flag_type=draft.flag_type,
        severity=draft.severity,
        headline=draft.headline_key,
        detail=draft.detail_key,
        evidence=draft.evidence,
        include_in_report=draft.include_in_report,
        qa_state=draft.qa_state,
    )


def _flag_from_model(flag: TenderFlag) -> AnalysisFlagDraft:
    return AnalysisFlagDraft(
        comparison_id=str(flag.comparison_id),
        quote_id=str(flag.quote_id) if flag.quote_id else None,
        cell_code=flag.cell_code,
        flag_type=flag.flag_type,
        severity=flag.severity,
        headline_key=flag.headline,
        detail_key=flag.detail,
        evidence=flag.evidence or {},
        include_in_report=flag.include_in_report,
        qa_state=flag.qa_state,
    )


def _flag_identity(flag: AnalysisFlagDraft) -> tuple[str, str | None, str | None]:
    return flag.flag_type, flag.quote_id, flag.cell_code


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple | list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(child) for key, child in value.items()}
    return value
