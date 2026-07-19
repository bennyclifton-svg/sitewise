from __future__ import annotations

import re
import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import (
    ExpectationRule,
    TenderCellStatus,
    TenderComparison,
    TenderJob,
    TenderLineItem,
    TenderMapping,
    TenderQuote,
)
from tender.schemas import ProjectContext
from tender.services import jobs
from tender.services.reconciliation import COUNTABLE_ROLES

ConceptMap = Mapping[str, Sequence[str]]

# Display status for a uniform role. Money never follows this map (I4).
_ROLE_TO_CELL_STATUS = {
    "contract_component": "included",
    "pc_allowance": "pc",
    "ps_allowance": "ps",
    "optional_upgrade": "included",
    "informational": "included",
    "excluded": "excluded_explicit",
}
_ITEM_STATUS_TO_ROLE = {
    "included": "contract_component",
    "excluded": "excluded",
    "pc_allowance": "pc_allowance",
    "ps_allowance": "ps_allowance",
    "note": "informational",
}

_MISSING = object()
_COMPARATORS = {"eq", "in", "gte", "lte", "before", "exists", "contains_concept"}
_YEAR_RE = re.compile(r"\b(18|19|20)\d{2}\b")


class PredicateValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ExpectationRuleInput:
    rule_code: str
    cell_code: str
    predicate: Mapping[str, Any]
    severity: str
    rationale: str | None = None
    region_tags: Sequence[str] = ()
    build_type_tags: Sequence[str] = ()


@dataclass(frozen=True)
class FiredRule:
    rule_code: str
    cell_code: str
    severity: str
    rationale: str | None


@dataclass(frozen=True)
class MappedCellItem:
    line_item_id: uuid.UUID
    quote_id: uuid.UUID
    cell_code: str
    item_status: str
    amount_cents: int | None = None
    allowance_cents: int | None = None
    allocation_fraction: float = 1.0
    role: str | None = None
    counted_in_total: bool = True
    amount_ex_gst_cents: int | None = None


@dataclass(frozen=True)
class CellStatusDraft:
    comparison_id: uuid.UUID
    quote_id: uuid.UUID
    cell_code: str
    status: str
    amount_cents: int | None
    bundled_into_cell: str | None
    evidence: dict[str, Any]
    confidence: float | None
    qa_state: str
    queue_silence: bool = False
    amount_breakdown: dict[str, Any] | None = None

    def as_row_state(self) -> "CellStatusRowState":
        return CellStatusRowState(
            comparison_id=self.comparison_id,
            quote_id=self.quote_id,
            cell_code=self.cell_code,
            status=self.status,
            amount_cents=self.amount_cents,
            bundled_into_cell=self.bundled_into_cell,
            evidence=self.evidence,
            confidence=self.confidence,
            qa_state=self.qa_state,
            amount_breakdown=self.amount_breakdown,
        )


@dataclass(frozen=True)
class CellStatusRowState:
    comparison_id: uuid.UUID
    quote_id: uuid.UUID
    cell_code: str
    status: str
    amount_cents: int | None
    bundled_into_cell: str | None
    evidence: dict[str, Any] | None
    confidence: float | None
    qa_state: str
    amount_breakdown: dict[str, Any] | None = None


@dataclass(frozen=True)
class CellStatusMerge:
    inserts: list[CellStatusDraft]
    updates: list[tuple[CellStatusRowState, CellStatusDraft]]
    silence_jobs: list[CellStatusDraft]


def evaluate_rules(
    rules: Sequence[ExpectationRuleInput],
    context: ProjectContext,
    *,
    concepts: ConceptMap | None = None,
) -> list[FiredRule]:
    concepts = concepts or {}
    fired: list[FiredRule] = []
    for rule in rules:
        validate_predicate(rule.predicate, concepts=concepts)
        if not _tags_match(rule.region_tags, _context_region_tags(context)):
            continue
        if rule.build_type_tags and context.build_type not in rule.build_type_tags:
            continue
        if _evaluate_predicate(rule.predicate, context, concepts):
            fired.append(
                FiredRule(
                    rule_code=rule.rule_code,
                    cell_code=rule.cell_code,
                    severity=rule.severity,
                    rationale=rule.rationale,
                )
            )
    return fired


def build_cell_status_grid(
    *,
    comparison_id: uuid.UUID,
    quote_ids: Sequence[uuid.UUID],
    fired_rules: Sequence[FiredRule],
    mapped_items: Sequence[MappedCellItem] = (),
) -> list[CellStatusDraft]:
    expected_by_cell: dict[str, list[FiredRule]] = defaultdict(list)
    for rule in fired_rules:
        expected_by_cell[rule.cell_code].append(rule)

    mapped_by_key: dict[tuple[uuid.UUID, str], list[MappedCellItem]] = defaultdict(list)
    for item in mapped_items:
        mapped_by_key[(item.quote_id, item.cell_code)].append(item)

    drafts: list[CellStatusDraft] = []
    expected_cells = set(expected_by_cell)
    for quote_id in quote_ids:
        mapped_cells = {cell_code for item_quote_id, cell_code in mapped_by_key if item_quote_id == quote_id}
        for cell_code in sorted(expected_cells | mapped_cells):
            mapped = mapped_by_key.get((quote_id, cell_code), [])
            if mapped:
                # I4: money and status from counted frontier items; fall back if none flagged.
                active = [item for item in mapped if item.counted_in_total] or list(mapped)
                drafts.append(
                    _mapped_status_draft(comparison_id, quote_id, cell_code, active)
                )
            else:
                drafts.append(
                    _silent_status_draft(
                        comparison_id,
                        quote_id,
                        cell_code,
                        expected_by_cell[cell_code],
                    )
                )
    return drafts


def merge_cell_status_drafts(
    existing_rows: Sequence[CellStatusRowState],
    drafts: Sequence[CellStatusDraft],
) -> CellStatusMerge:
    existing = {
        (row.comparison_id, row.quote_id, row.cell_code): row for row in existing_rows
    }
    inserts: list[CellStatusDraft] = []
    updates: list[tuple[CellStatusRowState, CellStatusDraft]] = []
    silence_jobs: list[CellStatusDraft] = []

    for draft in drafts:
        row = existing.get((draft.comparison_id, draft.quote_id, draft.cell_code))
        if row is None:
            inserts.append(draft)
            if draft.queue_silence:
                silence_jobs.append(draft)
            continue
        if row.qa_state in {"confirmed", "corrected"}:
            continue
        if _row_matches_draft(row, draft):
            continue
        updates.append((row, draft))
        if draft.queue_silence:
            silence_jobs.append(draft)

    return CellStatusMerge(inserts=inserts, updates=updates, silence_jobs=silence_jobs)


async def run_expectations(session: AsyncSession, job: TenderJob) -> None:
    if job.comparison_id is None:
        raise ValueError("run_expectations job requires comparison_id")

    comparison = await _comparison(session, job.comparison_id)
    context = ProjectContext.model_validate(comparison.context)
    rules = [
        _rule_input_from_model(rule)
        for rule in await _scalars(
            session,
            select(ExpectationRule).order_by(ExpectationRule.rule_code),
        )
    ]
    fired = evaluate_rules(rules, context)
    quote_ids = [
        quote.id
        for quote in await _scalars(
            session,
            select(TenderQuote)
            .where(TenderQuote.comparison_id == job.comparison_id)
            .order_by(TenderQuote.created_at),
        )
    ]
    mapped_items = await _mapped_items_for_comparison(session, job.comparison_id)
    existing_models = await _scalars(
        session,
        select(TenderCellStatus).where(
            TenderCellStatus.comparison_id == job.comparison_id
        ),
    )
    existing_states = [_row_state_from_model(row) for row in existing_models]
    models_by_key = {
        (row.comparison_id, row.quote_id, row.cell_code): row for row in existing_models
    }
    merge = merge_cell_status_drafts(
        existing_states,
        build_cell_status_grid(
            comparison_id=job.comparison_id,
            quote_ids=quote_ids,
            fired_rules=fired,
            mapped_items=mapped_items,
        ),
    )

    for draft in merge.inserts:
        session.add(_cell_status_model(draft))
    for row_state, draft in merge.updates:
        _apply_draft(models_by_key[(row_state.comparison_id, row_state.quote_id, row_state.cell_code)], draft)
    silence_jobs_by_quote: dict[uuid.UUID, list[CellStatusDraft]] = defaultdict(list)
    for draft in merge.silence_jobs:
        silence_jobs_by_quote[draft.quote_id].append(draft)

    for quote_id, drafts in silence_jobs_by_quote.items():
        session.add(
            TenderJob(
                kind="infer_silence_batch",
                comparison_id=job.comparison_id,
                quote_id=quote_id,
                payload={
                    "cell_codes": sorted(draft.cell_code for draft in drafts),
                },
            )
        )
    comparison.status = "processing"
    if not merge.silence_jobs:
        await jobs.enqueue(
            session,
            kind="run_analysis",
            comparison_id=job.comparison_id,
            payload={"reason": "expectations_complete"},
        )
    await session.flush()


def validate_predicate(
    predicate: Mapping[str, Any],
    *,
    concepts: ConceptMap | None = None,
) -> None:
    _validate_node(predicate, concepts or {})


def predicate_matches(
    predicate: Mapping[str, Any],
    context: ProjectContext,
    *,
    concepts: ConceptMap | None = None,
) -> bool:
    concepts = concepts or {}
    validate_predicate(predicate, concepts=concepts)
    return _evaluate_predicate(predicate, context, concepts)


def _validate_node(node: Any, concepts: ConceptMap) -> None:
    if not isinstance(node, Mapping):
        raise PredicateValidationError("predicate must be a mapping")

    combinators = [key for key in ("all", "any", "not") if key in node]
    if combinators:
        if len(combinators) != 1 or len(node) != 1:
            raise PredicateValidationError("predicate must contain one combinator")
        operator = combinators[0]
        value = node[operator]
        if operator in {"all", "any"}:
            if not isinstance(value, list) or not value:
                raise PredicateValidationError(f"{operator} must be a non-empty list")
            for child in value:
                _validate_node(child, concepts)
            return
        _validate_node(value, concepts)
        return

    field = node.get("field")
    if not isinstance(field, str) or not field:
        raise PredicateValidationError("field predicate requires a field")

    comparators = [key for key in node if key != "field"]
    if len(comparators) != 1:
        raise PredicateValidationError("field predicate requires exactly one comparator")
    comparator = comparators[0]
    if comparator not in _COMPARATORS:
        raise PredicateValidationError(f"unknown comparator: {comparator}")
    if comparator == "in" and not isinstance(node[comparator], list):
        raise PredicateValidationError("in comparator requires a list")
    if comparator == "exists" and not isinstance(node[comparator], bool):
        raise PredicateValidationError("exists comparator requires a boolean")
    if comparator == "contains_concept":
        concept = node[comparator]
        if not isinstance(concept, str) or not concept:
            raise PredicateValidationError("contains_concept requires a concept key")
        if concepts and concept not in concepts:
            raise PredicateValidationError(f"unknown concept: {concept}")


def _evaluate_predicate(
    predicate: Mapping[str, Any],
    context: ProjectContext,
    concepts: ConceptMap,
) -> bool:
    if "all" in predicate:
        return all(_evaluate_predicate(child, context, concepts) for child in predicate["all"])
    if "any" in predicate:
        return any(_evaluate_predicate(child, context, concepts) for child in predicate["any"])
    if "not" in predicate:
        return not _evaluate_predicate(predicate["not"], context, concepts)

    field = str(predicate["field"])
    comparator = next(key for key in predicate if key != "field")
    expected = predicate[comparator]
    actual = _field_value(context, field)
    return _compare(actual, comparator, expected, concepts)


def _compare(actual: Any, comparator: str, expected: Any, concepts: ConceptMap) -> bool:
    if comparator == "exists":
        return _exists(actual) is bool(expected)
    if actual is _MISSING or actual is None:
        return False
    if comparator == "eq":
        return actual == expected
    if comparator == "in":
        return actual in expected
    if comparator == "gte":
        return _decimal(actual) >= _decimal(expected)
    if comparator == "lte":
        return _decimal(actual) <= _decimal(expected)
    if comparator == "before":
        actual_year = _year(actual)
        expected_year = _year(expected)
        return actual_year is not None and expected_year is not None and actual_year < expected_year
    if comparator == "contains_concept":
        text = str(actual).casefold()
        return any(phrase.casefold() in text for phrase in concepts.get(str(expected), ()))
    raise PredicateValidationError(f"unknown comparator: {comparator}")


def _field_value(context: ProjectContext, field: str) -> Any:
    parts = field.split(".")
    if parts and parts[0] == "context":
        parts = parts[1:]

    value: Any = context.model_dump()
    for part in parts:
        if isinstance(value, Mapping) and part in value:
            value = value[part]
        else:
            return _MISSING
    return value


def _exists(value: Any) -> bool:
    return value is not _MISSING and value is not None and value != ""


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise PredicateValidationError(f"cannot compare non-numeric value: {value}") from exc


def _year(value: Any) -> int | None:
    match = _YEAR_RE.search(str(value))
    return int(match.group(0)) if match else None


def _context_region_tags(context: ProjectContext) -> set[str]:
    tags: set[str] = set()
    if context.state:
        tags.add(context.state)
    if context.state and context.region:
        tags.add(f"{context.state}:{context.region}")
    return tags


def _tags_match(rule_tags: Sequence[str], context_tags: set[str]) -> bool:
    return not rule_tags or any(tag in context_tags for tag in rule_tags)


def _mapped_status_draft(
    comparison_id: uuid.UUID,
    quote_id: uuid.UUID,
    cell_code: str,
    items: Sequence[MappedCellItem],
) -> CellStatusDraft:
    breakdown = _role_amount_breakdown(items)
    statuses = {_cell_status_for_mapped_item(item) for item in items}
    status = next(iter(statuses)) if len(statuses) == 1 else "mixed"
    countable = sum(breakdown.get(role, 0) for role in COUNTABLE_ROLES)
    amount_breakdown: dict[str, Any] | None = None
    if items:
        amount_breakdown = {**breakdown, "item_count": len(items)}
    return CellStatusDraft(
        comparison_id=comparison_id,
        quote_id=quote_id,
        cell_code=cell_code,
        status=status,
        amount_cents=countable if items else None,
        amount_breakdown=amount_breakdown,
        bundled_into_cell=None,
        evidence={
            "mapped_line_items": [
                {
                    "line_item_id": str(item.line_item_id),
                    "item_status": item.item_status,
                    "role": item.role or _role_for_item_status(item.item_status),
                    "allocation_fraction": item.allocation_fraction,
                }
                for item in items
            ]
        },
        confidence=None,
        qa_state="auto_pass",
    )


def _silent_status_draft(
    comparison_id: uuid.UUID,
    quote_id: uuid.UUID,
    cell_code: str,
    rules: Sequence[FiredRule],
) -> CellStatusDraft:
    return CellStatusDraft(
        comparison_id=comparison_id,
        quote_id=quote_id,
        cell_code=cell_code,
        status="silent_ambiguous",
        amount_cents=None,
        bundled_into_cell=None,
        evidence={
            "expected_because": [rule.rule_code for rule in rules],
            "expectation_rules": [
                {
                    "rule_code": rule.rule_code,
                    "severity": rule.severity,
                    "rationale": rule.rationale,
                }
                for rule in rules
            ],
        },
        confidence=None,
        qa_state="needs_review",
        queue_silence=True,
    )


def _cell_status_for_item(item_status: str) -> str:
    return {
        "included": "included",
        "excluded": "excluded_explicit",
        "pc_allowance": "pc",
        "ps_allowance": "ps",
        "note": "included",
    }[item_status]


def _role_for_item_status(item_status: str) -> str:
    return _ITEM_STATUS_TO_ROLE.get(item_status, "contract_component")


def _cell_status_for_mapped_item(item: MappedCellItem) -> str:
    role = item.role or _role_for_item_status(item.item_status)
    if role in _ROLE_TO_CELL_STATUS:
        return _ROLE_TO_CELL_STATUS[role]
    return _cell_status_for_item(item.item_status)


def _item_native_amount_cents(item: MappedCellItem) -> int | None:
    if item.amount_ex_gst_cents is not None:
        return item.amount_ex_gst_cents
    if item.item_status in {"pc_allowance", "ps_allowance"}:
        return item.allowance_cents
    return item.amount_cents


def _role_amount_breakdown(items: Sequence[MappedCellItem]) -> dict[str, int]:
    breakdown: dict[str, int] = defaultdict(int)
    for item in items:
        amount = _item_native_amount_cents(item)
        if amount is None:
            continue
        role = item.role or _role_for_item_status(item.item_status)
        breakdown[role] += round(amount * item.allocation_fraction)
    return dict(breakdown)


def _row_matches_draft(row: CellStatusRowState, draft: CellStatusDraft) -> bool:
    return (
        row.status == draft.status
        and row.amount_cents == draft.amount_cents
        and row.amount_breakdown == draft.amount_breakdown
        and row.bundled_into_cell == draft.bundled_into_cell
        and (row.evidence or {}) == draft.evidence
        and row.confidence == draft.confidence
        and row.qa_state == draft.qa_state
    )


async def _comparison(session: AsyncSession, comparison_id: uuid.UUID) -> TenderComparison:
    result = await session.execute(
        select(TenderComparison).where(TenderComparison.id == comparison_id)
    )
    return result.scalar_one()


async def _scalars(session: AsyncSession, statement: Any) -> list[Any]:
    result = await session.execute(statement)
    return list(result.scalars())


async def _mapped_items_for_comparison(
    session: AsyncSession, comparison_id: uuid.UUID
) -> list[MappedCellItem]:
    result = await session.execute(
        select(TenderMapping, TenderLineItem)
        .join(TenderLineItem, TenderLineItem.id == TenderMapping.line_item_id)
        .join(TenderQuote, TenderQuote.id == TenderLineItem.quote_id)
        .where(
            TenderQuote.comparison_id == comparison_id,
            TenderLineItem.duplicate_of_id.is_(None),
        )
    )
    items: list[MappedCellItem] = []
    for mapping, line_item in result.all():
        items.append(
            MappedCellItem(
                line_item_id=line_item.id,
                quote_id=line_item.quote_id,
                cell_code=mapping.cell_code,
                item_status=line_item.item_status,
                amount_cents=line_item.amount_cents,
                allowance_cents=line_item.allowance_cents,
                allocation_fraction=float(mapping.allocation_fraction),
                role=line_item.role,
                counted_in_total=bool(line_item.counted_in_total),
                amount_ex_gst_cents=line_item.amount_ex_gst_cents,
            )
        )
    return items


def _rule_input_from_model(rule: ExpectationRule) -> ExpectationRuleInput:
    return ExpectationRuleInput(
        rule_code=rule.rule_code,
        cell_code=rule.cell_code,
        predicate=rule.predicate,
        severity=rule.severity,
        rationale=rule.rationale,
        region_tags=tuple(rule.region_tags or ()),
        build_type_tags=tuple(rule.build_type_tags or ()),
    )


def _row_state_from_model(row: TenderCellStatus) -> CellStatusRowState:
    return CellStatusRowState(
        comparison_id=row.comparison_id,
        quote_id=row.quote_id,
        cell_code=row.cell_code,
        status=row.status,
        amount_cents=row.amount_cents,
        amount_breakdown=row.amount_breakdown,
        bundled_into_cell=row.bundled_into_cell,
        evidence=row.evidence,
        confidence=float(row.confidence) if row.confidence is not None else None,
        qa_state=row.qa_state,
    )


def _cell_status_model(draft: CellStatusDraft) -> TenderCellStatus:
    return TenderCellStatus(
        comparison_id=draft.comparison_id,
        quote_id=draft.quote_id,
        cell_code=draft.cell_code,
        status=draft.status,
        amount_cents=draft.amount_cents,
        amount_breakdown=draft.amount_breakdown,
        bundled_into_cell=draft.bundled_into_cell,
        evidence=draft.evidence,
        confidence=draft.confidence,
        qa_state=draft.qa_state,
    )


def _apply_draft(row: TenderCellStatus, draft: CellStatusDraft) -> None:
    row.status = draft.status
    row.amount_cents = draft.amount_cents
    row.amount_breakdown = draft.amount_breakdown
    row.bundled_into_cell = draft.bundled_into_cell
    row.evidence = draft.evidence
    row.confidence = draft.confidence
    row.qa_state = draft.qa_state
