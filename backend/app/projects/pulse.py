"""Pulse feed: synthesised attention from Stage 13 verbs and canonical rows.

Signals are derived at read time. There is no pulse_* table. Detectors are
pure readers — they never call decide_invoice, set_document_classification,
file_single_document, or ingest.

Dismissing a grouped card dismisses `{signal_type}:group`, not the members.
A new member (created_at after the dismiss) re-raises the group.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, get_args

from pydantic import BaseModel
from sqlalchemy import Float, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import Delete, Insert, Update

from app.cost_plan.models import CostInvoice
from app.database.activity_event import ActivityEvent
from app.database.source_document import SourceDocument
from app.projects.event_spine import list_project_verbs
from ingest.router import REVIEW_CONFIDENCE_MIN

PulseSignalType = Literal[
    "drawing_revision",
    "approval_received",
    "invoice_review_required",
    "potential_cost_change",
    "document_needs_classification",
]

PulseAttentionKind = Literal["attention", "other"]
PulseAction = Literal[
    "review_invoice",
    "classify_document",
    "view_evidence",
    "dismiss",
]

PULSE_SIGNAL_TYPES: frozenset[str] = frozenset(get_args(PulseSignalType))
PULSE_ACTIONS: frozenset[str] = frozenset(get_args(PulseAction))

MAX_ATTENTION_ITEMS = 7
MIN_GROUPED = 3
PULSE_QUERY_COUNT = 4
_GROUPED_EVIDENCE = 3
_REVIEW_STATES = ("ready_for_review", "needs_attention")
_COST_CHANGE_CODES = frozenset(
    {
        "UNAPPROVED_VARIATION",
        "COST_PLAN_OVERRUN",
        "AMOUNT_EXCEEDS_COMMITMENT",
    }
)
_DETERMINATION_MARKERS = (
    "notice of determination",
    "nod ",
    "determination received",
)


class PulseEvidenceRef(BaseModel):
    reference_type: str
    reference_id: uuid.UUID
    label: str


class PulseItem(BaseModel):
    id: str
    kind: PulseAttentionKind
    signal_type: PulseSignalType | None = None
    title: str
    body: str
    domain: str
    evidence: list[PulseEvidenceRef]
    actions: list[str]
    confidence: float | None = None
    created_at: datetime


class PulseFeed(BaseModel):
    attention: list[PulseItem]
    other: list[PulseItem]
    attention_count: int
    generated_at: datetime


@dataclass(frozen=True)
class PulseSnapshot:
    verbs: tuple[ActivityEvent, ...]
    invoices: tuple[CostInvoice, ...]
    documents: tuple[SourceDocument, ...]
    dismissed: tuple[ActivityEvent, ...]


def subject_key(
    signal_type: str,
    reference_type: str,
    reference_id: uuid.UUID,
    state: str = "",
) -> str:
    """Stable dismiss key. Mutable rows append a state discriminator."""
    base = f"{signal_type}:{reference_type}:{reference_id}"
    return f"{base}:{state}" if state else base


def grouped_subject_key(signal_type: str) -> str:
    return f"{signal_type}:group"


def parse_signal_type(key: str) -> str | None:
    prefix = key.split(":", 1)[0]
    return prefix if prefix in PULSE_SIGNAL_TYPES else None


def _meta(event: ActivityEvent) -> dict[str, Any]:
    payload = event.event_metadata or {}
    return payload if isinstance(payload, dict) else {}


def _doc_meta(document: SourceDocument) -> dict[str, Any]:
    payload = document.document_metadata or {}
    return payload if isinstance(payload, dict) else {}


def _as_datetime(value: datetime | None) -> datetime:
    if value is not None:
        return value
    return datetime.now(UTC)


def _confidence_of(document: SourceDocument) -> float | None:
    raw = _doc_meta(document).get("confidence")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _issue_codes(invoice: CostInvoice) -> set[str]:
    codes: set[str] = set()
    for issue in invoice.issues or []:
        if isinstance(issue, dict):
            code = issue.get("code")
            if isinstance(code, str):
                codes.add(code)
    return codes


def _money(amount: Decimal | None) -> str:
    if amount is None:
        return "an amount"
    quantized = amount.quantize(Decimal("0.01"))
    if quantized == quantized.to_integral():
        return f"${int(quantized):,}"
    return f"${quantized:,.2f}"


def _filename_supports_determination(*parts: str | None) -> bool:
    haystack = " ".join(part for part in parts if part).casefold()
    return any(marker in haystack for marker in _DETERMINATION_MARKERS)


def detect_drawing_revision(verbs: Sequence[ActivityEvent]) -> list[PulseItem]:
    items: list[PulseItem] = []
    for event in verbs:
        if event.source != "document.revised" or event.reference_id is None:
            continue
        meta = _meta(event)
        drawing = str(meta.get("drawing_number") or "Drawing")
        revision = str(meta.get("revision") or "?")
        previous = str(meta.get("previous_revision") or "?")
        title = f"{drawing} Rev {revision} supersedes Rev {previous}"
        items.append(
            PulseItem(
                id=subject_key(
                    "drawing_revision",
                    event.reference_type or "source_document",
                    event.reference_id,
                ),
                kind="attention",
                signal_type="drawing_revision",
                title=title,
                body=title,
                domain="STRUCTURE",
                evidence=[
                    PulseEvidenceRef(
                        reference_type=event.reference_type or "source_document",
                        reference_id=event.reference_id,
                        label=str(meta.get("filename") or drawing),
                    )
                ],
                actions=["view_evidence", "dismiss"],
                created_at=_as_datetime(event.created_at),
            )
        )
    return items


def detect_approval_received(verbs: Sequence[ActivityEvent]) -> list[PulseItem]:
    items: list[PulseItem] = []
    for event in verbs:
        if event.source not in {"document.classified", "document.reclassified"}:
            continue
        if event.reference_id is None:
            continue
        meta = _meta(event)
        if str(meta.get("document_class") or "") != "certificate":
            continue
        filename = str(meta.get("filename") or "")
        subject = str(meta.get("document_subject") or meta.get("subject") or "")
        if subject and subject != "planning" and subject != "town_planner":
            # Prefer planning certificates; still surface any certificate.
            pass
        if _filename_supports_determination(filename, event.message):
            title = "Notice of Determination received"
        else:
            title = "Planning certificate received"
        items.append(
            PulseItem(
                id=subject_key(
                    "approval_received",
                    event.reference_type or "source_document",
                    event.reference_id,
                ),
                kind="attention",
                signal_type="approval_received",
                title=title,
                body=title,
                domain="PLANNING",
                evidence=[
                    PulseEvidenceRef(
                        reference_type=event.reference_type or "source_document",
                        reference_id=event.reference_id,
                        label=filename or title,
                    )
                ],
                actions=["view_evidence", "dismiss"],
                created_at=_as_datetime(event.created_at),
            )
        )
    return items


def detect_invoice_review(invoices: Sequence[CostInvoice]) -> list[PulseItem]:
    items: list[PulseItem] = []
    for invoice in invoices:
        if invoice.review_state not in _REVIEW_STATES:
            continue
        number = invoice.invoice_number or "invoice"
        supplier = invoice.supplier_name or "Supplier"
        title = f"{supplier} invoice {number} needs review"
        items.append(
            PulseItem(
                id=subject_key(
                    "invoice_review_required",
                    "cost_invoice",
                    invoice.id,
                    invoice.review_state,
                ),
                kind="attention",
                signal_type="invoice_review_required",
                title=title,
                body=title,
                domain="COMMERCIAL",
                evidence=[
                    PulseEvidenceRef(
                        reference_type="cost_invoice",
                        reference_id=invoice.id,
                        label=f"{supplier} {number}",
                    )
                ],
                actions=["review_invoice", "dismiss"],
                created_at=_as_datetime(invoice.updated_at or invoice.created_at),
            )
        )
    return items


def detect_cost_change(invoices: Sequence[CostInvoice]) -> list[PulseItem]:
    items: list[PulseItem] = []
    for invoice in invoices:
        if invoice.review_state not in _REVIEW_STATES:
            continue
        codes = _issue_codes(invoice)
        if not codes.intersection(_COST_CHANGE_CODES):
            continue
        number = invoice.invoice_number or "invoice"
        supplier = invoice.supplier_name or "Supplier"
        amount = _money(invoice.total_including_gst)
        if "UNAPPROVED_VARIATION" in codes:
            title = (
                f"{supplier} Invoice {number} includes {amount} "
                "against an unapproved variation"
            )
        elif "COST_PLAN_OVERRUN" in codes:
            title = f"{supplier} Invoice {number} would overrun the cost plan"
        else:
            title = f"{supplier} Invoice {number} exceeds the committed amount"
        items.append(
            PulseItem(
                id=subject_key(
                    "potential_cost_change",
                    "cost_invoice",
                    invoice.id,
                    invoice.review_state,
                ),
                kind="attention",
                signal_type="potential_cost_change",
                title=title,
                body=title,
                domain="COMMERCIAL",
                evidence=[
                    PulseEvidenceRef(
                        reference_type="cost_invoice",
                        reference_id=invoice.id,
                        label=f"{supplier} {number}",
                    )
                ],
                actions=["review_invoice", "dismiss"],
                created_at=_as_datetime(invoice.updated_at or invoice.created_at),
            )
        )
    return items


def detect_needs_classification(documents: Sequence[SourceDocument]) -> list[PulseItem]:
    items: list[PulseItem] = []
    for document in documents:
        confidence = _confidence_of(document)
        unknown = document.document_class == "unknown"
        low = confidence is not None and confidence < REVIEW_CONFIDENCE_MIN
        if not unknown and not low:
            continue
        filename = document.filename or "Document"
        title = f"{filename} needs classification"
        items.append(
            PulseItem(
                id=subject_key(
                    "document_needs_classification",
                    "source_document",
                    document.id,
                    document.document_class,
                ),
                kind="attention",
                signal_type="document_needs_classification",
                title=title,
                body=title,
                domain="REVIEW",
                evidence=[
                    PulseEvidenceRef(
                        reference_type="source_document",
                        reference_id=document.id,
                        label=filename,
                    )
                ],
                actions=["classify_document", "dismiss"],
                confidence=confidence,
                created_at=_as_datetime(document.updated_at or document.created_at),
            )
        )
    return items


def merge_invoice_cards(
    review_items: Sequence[PulseItem],
    cost_items: Sequence[PulseItem],
) -> list[PulseItem]:
    """One invoice → one attention card. Cost-change wins the title."""
    cost_by_invoice = {
        ref.reference_id: item
        for item in cost_items
        for ref in item.evidence
        if ref.reference_type == "cost_invoice"
    }
    merged: list[PulseItem] = list(cost_items)
    claimed = set(cost_by_invoice)
    for item in review_items:
        invoice_ids = [
            ref.reference_id
            for ref in item.evidence
            if ref.reference_type == "cost_invoice"
        ]
        if invoice_ids and invoice_ids[0] in claimed:
            continue
        merged.append(item)
    return merged


def _group_title(signal_type: str, count: int) -> str:
    labels = {
        "drawing_revision": f"{count} revised drawings received",
        "approval_received": f"{count} certificates received",
        "invoice_review_required": f"{count} invoices need review",
        "potential_cost_change": f"{count} invoices may change project cost",
        "document_needs_classification": f"{count} documents need classification",
    }
    return labels.get(signal_type, f"{count} items")


def _group_body(signal_type: str, count: int) -> str:
    if signal_type == "document_needs_classification":
        return f"{count} documents need classification"
    return _group_title(signal_type, count)


def _group_actions(signal_type: str) -> list[str]:
    if signal_type in {"invoice_review_required", "potential_cost_change"}:
        return ["review_invoice", "dismiss"]
    if signal_type == "document_needs_classification":
        return ["classify_document", "dismiss"]
    return ["view_evidence", "dismiss"]


def _collapse_group(signal_type: str, members: Sequence[PulseItem]) -> PulseItem:
    ordered = sorted(members, key=lambda item: item.created_at, reverse=True)
    evidence: list[PulseEvidenceRef] = []
    seen: set[uuid.UUID] = set()
    for item in ordered:
        for ref in item.evidence:
            if ref.reference_id in seen:
                continue
            seen.add(ref.reference_id)
            evidence.append(ref)
            if len(evidence) >= _GROUPED_EVIDENCE:
                break
        if len(evidence) >= _GROUPED_EVIDENCE:
            break
    return PulseItem(
        id=grouped_subject_key(signal_type),
        kind="attention",
        signal_type=signal_type,  # type: ignore[arg-type]
        title=_group_title(signal_type, len(ordered)),
        body=_group_body(signal_type, len(ordered)),
        domain=ordered[0].domain,
        evidence=evidence,
        actions=_group_actions(signal_type),
        created_at=ordered[0].created_at,
    )


def group_attention(
    items: Sequence[PulseItem],
    dismissed_at: dict[str, datetime],
) -> list[PulseItem]:
    buckets: dict[str, list[PulseItem]] = {}
    for item in items:
        if item.signal_type is None:
            continue
        buckets.setdefault(item.signal_type, []).append(item)
    result: list[PulseItem] = []
    for signal_type, members in buckets.items():
        group_key = grouped_subject_key(signal_type)
        cutoff = dismissed_at.get(group_key)
        if cutoff is not None:
            members = [item for item in members if item.created_at > cutoff]
        if len(members) >= MIN_GROUPED:
            result.append(_collapse_group(signal_type, members))
        else:
            result.extend(members)
    return result


def _dismissed_map(events: Sequence[ActivityEvent]) -> dict[str, datetime]:
    dismissed: dict[str, datetime] = {}
    for event in events:
        key = _meta(event).get("subject_key")
        if not isinstance(key, str) or not key:
            continue
        stamp = _as_datetime(event.created_at)
        previous = dismissed.get(key)
        if previous is None or stamp > previous:
            dismissed[key] = stamp
    return dismissed


def _other_rollup(
    snapshot: PulseSnapshot,
    attention: Sequence[PulseItem],
    truncated: Sequence[PulseItem],
    generated_at: datetime,
) -> list[PulseItem]:
    attention_invoice_ids = {
        ref.reference_id
        for item in (*attention, *truncated)
        for ref in item.evidence
        if ref.reference_type == "cost_invoice"
    }
    filed = sum(1 for event in snapshot.verbs if event.source == "document.filed")
    leftover_invoices = sum(
        1 for invoice in snapshot.invoices if invoice.id not in attention_invoice_ids
    )
    parts: list[str] = []
    if filed:
        noun = "document" if filed == 1 else "documents"
        parts.append(f"{filed} {noun} filed")
    if leftover_invoices:
        noun = "invoice" if leftover_invoices == 1 else "invoices"
        parts.append(f"{leftover_invoices} {noun} ready for review")
    if truncated:
        extra = "item" if len(truncated) == 1 else "items"
        parts.append(f"{len(truncated)} more {extra}")
        parts.append("; ".join(item.title for item in truncated))
    if not parts:
        return []
    return [
        PulseItem(
            id="other:rollup",
            kind="other",
            signal_type=None,
            title="Other activity",
            body=" · ".join(parts),
            domain="ACTIVITY",
            evidence=[],
            actions=[],
            created_at=generated_at,
        )
    ]


def synthesize_pulse_feed(
    snapshot: PulseSnapshot,
    *,
    now: datetime | None = None,
) -> PulseFeed:
    generated_at = now or datetime.now(UTC)
    dismissed_at = _dismissed_map(snapshot.dismissed)
    items: list[PulseItem] = []
    items.extend(detect_drawing_revision(snapshot.verbs))
    items.extend(detect_approval_received(snapshot.verbs))
    items.extend(
        merge_invoice_cards(
            detect_invoice_review(snapshot.invoices),
            detect_cost_change(snapshot.invoices),
        )
    )
    items.extend(detect_needs_classification(snapshot.documents))
    visible = [item for item in items if item.id not in dismissed_at]
    grouped = group_attention(visible, dismissed_at)
    grouped.sort(key=lambda item: item.created_at, reverse=True)
    attention_count = len(grouped)
    attention = grouped[:MAX_ATTENTION_ITEMS]
    truncated = grouped[MAX_ATTENTION_ITEMS:]
    return PulseFeed(
        attention=attention,
        other=_other_rollup(snapshot, attention, truncated, generated_at),
        attention_count=attention_count,
        generated_at=generated_at,
    )


def _is_mutating(statement: object) -> bool:
    if isinstance(statement, (Insert, Update, Delete)):
        return True
    compiled = str(statement).lstrip().split(None, 1)
    return bool(compiled) and compiled[0].upper() in {
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
    }


def assert_read_only(statement: object) -> None:
    """Raise if a detector issued DML. Used by tests; also a load-path guard."""
    if _is_mutating(statement):
        raise RuntimeError("Pulse detectors must not write canonical rows")


async def load_pulse_snapshot(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> PulseSnapshot:
    verbs = await list_project_verbs(session, project_id=project_id, limit=200)
    invoice_result = await session.execute(
        select(CostInvoice).where(
            CostInvoice.project_id == project_id,
            CostInvoice.review_state.in_(_REVIEW_STATES),
        )
    )
    document_result = await session.execute(
        select(SourceDocument).where(
            SourceDocument.project_id == project_id,
            or_(
                SourceDocument.document_class == "unknown",
                cast(
                    SourceDocument.document_metadata["confidence"].astext,
                    Float,
                )
                < REVIEW_CONFIDENCE_MIN,
            ),
        )
    )
    dismissed_result = await session.execute(
        select(ActivityEvent).where(
            ActivityEvent.project_id == project_id,
            ActivityEvent.source == "project_signal.dismissed",
        )
    )
    return PulseSnapshot(
        verbs=tuple(verbs),
        invoices=tuple(invoice_result.scalars().all()),
        documents=tuple(document_result.scalars().all()),
        dismissed=tuple(dismissed_result.scalars().all()),
    )


async def build_pulse_feed(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> PulseFeed:
    snapshot = await load_pulse_snapshot(session, project_id)
    return synthesize_pulse_feed(snapshot)
