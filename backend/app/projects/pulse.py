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
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal, get_args

from pydantic import BaseModel, Field
from sqlalchemy import Float, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import Delete, Insert, Update

from app.cost_plan.models import CostInvoice
from app.database.activity_event import ActivityEvent
from app.database.procurement_request import ProcurementRequest
from app.database.procurement_request_submission import ProcurementRequestSubmission
from app.database.source_document import SourceDocument
from app.email.models import (
    ProjectEmail,
    ProjectEmailAttachment,
    ProjectEmailDraft,
    ProjectEmailInterpretation,
)
from app.email.project_matching import thread_key
from app.projects.event_spine import PROJECT_VERBS
from ingest.router import REVIEW_CONFIDENCE_MIN

PulseSignalType = Literal[
    "drawing_revision",
    "approval_received",
    "invoice_review_required",
    "potential_cost_change",
    "document_needs_classification",
    "tender_received",
    "unanswered_correspondence",
]

PulseAttentionKind = Literal["attention", "other"]
PulseAction = Literal[
    "review_invoice",
    "classify_document",
    "view_evidence",
    "dismiss",
    "draft_reply",
    "view_thread",
]

PULSE_SIGNAL_TYPES: frozenset[str] = frozenset(get_args(PulseSignalType))
PULSE_ACTIONS: frozenset[str] = frozenset(get_args(PulseAction))

MAX_ATTENTION_ITEMS = 7
MIN_GROUPED = 3
PULSE_QUERY_COUNT = 9
DEFAULT_SINCE_DAYS = 7
UNANSWERED_AFTER = timedelta(days=5)
_UNANSWERED_CATEGORIES = frozenset({"rfi", "action_required"})
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
    since: datetime = Field(
        description=(
            "Inclusive window start. Verbs and canonical rows are considered "
            "when the triggering event is >= since. Omitted query defaults to "
            f"{DEFAULT_SINCE_DAYS} days before generated_at, not all time."
        ),
    )


@dataclass(frozen=True)
class PulseSnapshot:
    verbs: tuple[ActivityEvent, ...]
    invoices: tuple[CostInvoice, ...]
    documents: tuple[SourceDocument, ...]
    dismissed: tuple[ActivityEvent, ...]
    emails: tuple[ProjectEmail, ...] = ()
    drafts: tuple[ProjectEmailDraft, ...] = ()
    attachments: tuple[ProjectEmailAttachment, ...] = ()
    submissions: tuple[ProcurementRequestSubmission, ...] = ()


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


def resolve_pulse_since(
    *,
    now: datetime,
    since: datetime | None,
) -> datetime:
    if since is not None:
        return since
    return now - timedelta(days=DEFAULT_SINCE_DAYS)


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


def _email_category(email: ProjectEmail) -> str | None:
    interpretation = getattr(email, "interpretation", None)
    if interpretation is None:
        return None
    category = interpretation.message_category
    return category if isinstance(category, str) else None


def _drawing_number_of(item: PulseItem, documents_by_id: dict[uuid.UUID, SourceDocument]) -> str | None:
    for ref in item.evidence:
        document = documents_by_id.get(ref.reference_id)
        if document is not None:
            number = _doc_meta(document).get("drawing_number")
            if isinstance(number, str) and number.strip():
                return number.strip()
    token = item.title.split(" ", 1)[0].strip()
    return token or None


def _email_has_drawing(
    email: ProjectEmail,
    drawing: str,
    attachments: Sequence[ProjectEmailAttachment],
    documents_by_id: dict[uuid.UUID, SourceDocument],
) -> bool:
    needle = drawing.casefold()
    parts = [email.subject or "", email.body_text or ""]
    for attachment in attachments:
        if attachment.email_id != email.id:
            continue
        parts.append(attachment.filename or "")
        document = (
            documents_by_id.get(attachment.source_document_id)
            if attachment.source_document_id is not None
            else None
        )
        if document is not None:
            number = _doc_meta(document).get("drawing_number")
            if isinstance(number, str) and number.casefold() == needle:
                return True
            parts.append(document.filename or "")
    return needle in " ".join(parts).casefold()


def _answered_thread_keys(
    drafts: Sequence[ProjectEmailDraft],
    emails_by_id: dict[uuid.UUID, ProjectEmail],
) -> set[str]:
    keys: set[str] = set()
    for draft in drafts:
        if draft.status != "sent":
            continue
        if draft.in_reply_to_email_id is None:
            continue
        email = emails_by_id.get(draft.in_reply_to_email_id)
        if email is None:
            continue
        keys.add(thread_key(email))
    return keys


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


def merge_drawing_and_transmittal(
    items: Sequence[PulseItem],
    emails: Sequence[ProjectEmail],
    attachments: Sequence[ProjectEmailAttachment],
    documents: Sequence[SourceDocument],
) -> list[PulseItem]:
    documents_by_id = {document.id: document for document in documents}
    transmittals = [
        email for email in emails if _email_category(email) == "document_transmittal"
    ]
    used: set[uuid.UUID] = set()
    merged: list[PulseItem] = []
    for item in items:
        if item.signal_type != "drawing_revision":
            merged.append(item)
            continue
        drawing = _drawing_number_of(item, documents_by_id)
        match = None
        if drawing:
            for email in transmittals:
                if email.id in used:
                    continue
                if _email_has_drawing(email, drawing, attachments, documents_by_id):
                    match = email
                    break
        if match is None:
            merged.append(item)
            continue
        used.add(match.id)
        evidence = list(item.evidence) + [
            PulseEvidenceRef(
                reference_type="email",
                reference_id=match.id,
                label=match.subject or "Transmittal",
            )
        ]
        title = (
            f"Structural drawing {drawing} revised; issued on transmittal"
            if drawing
            else "Structural drawing revised; issued on transmittal"
        )
        merged.append(
            item.model_copy(
                update={
                    "title": title,
                    "body": f"{item.title}. Issued on transmittal.",
                    "evidence": evidence,
                    "actions": ["view_evidence", "view_thread", "dismiss"],
                }
            )
        )
    return merged


def merge_invoice_and_email(
    items: Sequence[PulseItem],
    invoices: Sequence[CostInvoice],
    emails: Sequence[ProjectEmail],
    attachments: Sequence[ProjectEmailAttachment],
) -> list[PulseItem]:
    emails_by_id = {email.id: email for email in emails}
    email_by_document = {
        attachment.source_document_id: emails_by_id[attachment.email_id]
        for attachment in attachments
        if attachment.source_document_id is not None
        and attachment.email_id in emails_by_id
    }
    invoices_by_id = {invoice.id: invoice for invoice in invoices}
    merged: list[PulseItem] = []
    for item in items:
        if item.signal_type not in {
            "invoice_review_required",
            "potential_cost_change",
        }:
            merged.append(item)
            continue
        parent = None
        for ref in item.evidence:
            if ref.reference_type != "cost_invoice":
                continue
            invoice = invoices_by_id.get(ref.reference_id)
            if invoice is None or invoice.source_document_id is None:
                continue
            parent = email_by_document.get(invoice.source_document_id)
            if parent is not None:
                break
        if parent is None:
            merged.append(item)
            continue
        evidence = list(item.evidence) + [
            PulseEvidenceRef(
                reference_type="email",
                reference_id=parent.id,
                label=parent.subject or "Invoice email",
            )
        ]
        actions = list(item.actions)
        if "view_thread" not in actions:
            actions.insert(-1 if "dismiss" in actions else len(actions), "view_thread")
        title = item.title
        if item.signal_type != "potential_cost_change":
            title = "Invoice arrived by email"
        merged.append(
            item.model_copy(
                update={
                    "title": title,
                    "body": title,
                    "evidence": evidence,
                    "actions": actions,
                }
            )
        )
    return merged


def detect_unanswered_correspondence(
    emails: Sequence[ProjectEmail],
    drafts: Sequence[ProjectEmailDraft],
    *,
    now: datetime,
) -> list[PulseItem]:
    emails_by_id = {email.id: email for email in emails}
    answered = _answered_thread_keys(drafts, emails_by_id)
    items: list[PulseItem] = []
    seen_threads: set[str] = set()
    for email in emails:
        category = _email_category(email)
        if category not in _UNANSWERED_CATEGORIES:
            continue
        stamp = _as_datetime(email.sent_at or email.created_at)
        if now - stamp < UNANSWERED_AFTER:
            continue
        key = thread_key(email)
        if key in answered or key in seen_threads:
            continue
        seen_threads.add(key)
        label = "RFI" if category == "rfi" else "action required"
        title = f"Unanswered {label}: {email.subject or 'correspondence'}"
        items.append(
            PulseItem(
                id=subject_key("unanswered_correspondence", "email", email.id),
                kind="attention",
                signal_type="unanswered_correspondence",
                title=title,
                body=title,
                domain="CORRESPONDENCE",
                evidence=[
                    PulseEvidenceRef(
                        reference_type="email",
                        reference_id=email.id,
                        label=email.subject or label,
                    )
                ],
                actions=["draft_reply", "view_thread", "dismiss"],
                created_at=stamp,
            )
        )
    return items


def detect_tender_received(
    submissions: Sequence[ProcurementRequestSubmission],
    documents: Sequence[SourceDocument],
) -> list[PulseItem]:
    documents_by_id = {document.id: document for document in documents}
    grouped: dict[uuid.UUID, list[ProcurementRequestSubmission]] = {}
    for submission in submissions:
        grouped.setdefault(submission.request_id, []).append(submission)
    items: list[PulseItem] = []
    for request_id, members in grouped.items():
        latest = max(members, key=lambda row: _as_datetime(row.created_at))
        document = documents_by_id.get(latest.source_document_id)
        filename = document.filename if document is not None else "submission"
        items.append(
            PulseItem(
                id=subject_key("tender_received", "procurement_request", request_id),
                kind="attention",
                signal_type="tender_received",
                title=f"Submission received from {filename}",
                body=f"Submission received from {filename}",
                domain="COMMERCIAL",
                evidence=[
                    PulseEvidenceRef(
                        reference_type="source_document",
                        reference_id=latest.source_document_id,
                        label=filename,
                    )
                ],
                actions=["view_evidence", "dismiss"],
                created_at=_as_datetime(latest.created_at),
            )
        )
    return items


def _group_title(signal_type: str, count: int) -> str:
    labels = {
        "drawing_revision": f"{count} revised drawings received",
        "approval_received": f"{count} certificates received",
        "invoice_review_required": f"{count} invoices need review",
        "potential_cost_change": f"{count} invoices may change project cost",
        "document_needs_classification": f"{count} documents need classification",
        "tender_received": f"{count} tender submissions received",
        "unanswered_correspondence": f"{count} unanswered items",
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
    if signal_type == "unanswered_correspondence":
        return ["draft_reply", "view_thread", "dismiss"]
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
    window_start: datetime,
) -> list[PulseItem]:
    attention_invoice_ids = {
        ref.reference_id
        for item in (*attention, *truncated)
        for ref in item.evidence
        if ref.reference_type == "cost_invoice"
    }
    attention_email_ids = {
        ref.reference_id
        for item in (*attention, *truncated)
        for ref in item.evidence
        if ref.reference_type == "email"
    }
    filed = sum(
        1
        for event in snapshot.verbs
        if event.source == "document.filed"
        and _as_datetime(event.created_at) >= window_start
    )
    leftover_invoices = sum(
        1
        for invoice in snapshot.invoices
        if invoice.id not in attention_invoice_ids
        and _as_datetime(invoice.updated_at or invoice.created_at) >= window_start
    )
    leftover_emails = sum(
        1
        for event in snapshot.verbs
        if event.source == "email.received"
        and (event.reference_id is None or event.reference_id not in attention_email_ids)
        and _as_datetime(event.created_at) >= window_start
    )
    parts: list[str] = []
    if filed:
        noun = "document" if filed == 1 else "documents"
        parts.append(f"{filed} {noun} filed")
    if leftover_emails:
        noun = "consultant reply" if leftover_emails == 1 else "consultant replies"
        parts.append(f"{leftover_emails} {noun}")
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
    since: datetime | None = None,
) -> PulseFeed:
    generated_at = now or datetime.now(UTC)
    window_start = resolve_pulse_since(now=generated_at, since=since)
    dismissed_at = _dismissed_map(snapshot.dismissed)
    items: list[PulseItem] = []
    items.extend(
        merge_drawing_and_transmittal(
            detect_drawing_revision(snapshot.verbs),
            snapshot.emails,
            snapshot.attachments,
            snapshot.documents,
        )
    )
    items.extend(detect_approval_received(snapshot.verbs))
    items.extend(
        merge_invoice_and_email(
            merge_invoice_cards(
                detect_invoice_review(snapshot.invoices),
                detect_cost_change(snapshot.invoices),
            ),
            snapshot.invoices,
            snapshot.emails,
            snapshot.attachments,
        )
    )
    items.extend(detect_needs_classification(snapshot.documents))
    items.extend(
        detect_unanswered_correspondence(
            snapshot.emails,
            snapshot.drafts,
            now=generated_at,
        )
    )
    items.extend(detect_tender_received(snapshot.submissions, snapshot.documents))
    in_window = [item for item in items if item.created_at >= window_start]
    visible = [item for item in in_window if item.id not in dismissed_at]
    grouped = group_attention(visible, dismissed_at)
    grouped.sort(key=lambda item: item.created_at, reverse=True)
    attention_count = len(grouped)
    attention = grouped[:MAX_ATTENTION_ITEMS]
    truncated = grouped[MAX_ATTENTION_ITEMS:]
    return PulseFeed(
        attention=attention,
        other=_other_rollup(
            snapshot, attention, truncated, generated_at, window_start
        ),
        attention_count=attention_count,
        generated_at=generated_at,
        since=window_start,
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
    *,
    since: datetime,
) -> PulseSnapshot:
    verb_result = await session.execute(
        select(ActivityEvent)
        .where(
            ActivityEvent.project_id == project_id,
            ActivityEvent.source.in_(PROJECT_VERBS),
            ActivityEvent.created_at >= since,
        )
        .order_by(ActivityEvent.created_at.desc())
        .limit(200)
    )
    verbs = tuple(verb_result.scalars().all())
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
    interp_result = await session.execute(
        select(ProjectEmailInterpretation).where(
            ProjectEmailInterpretation.project_id == project_id
        )
    )
    interpretations = tuple(interp_result.scalars().all())
    email_result = await session.execute(
        select(ProjectEmail).where(
            ProjectEmail.id.in_(
                select(ProjectEmailInterpretation.email_id).where(
                    ProjectEmailInterpretation.project_id == project_id
                )
            )
        )
    )
    emails = tuple(email_result.scalars().all())
    interp_by_id = {row.email_id: row for row in interpretations}
    for email in emails:
        email.interpretation = interp_by_id.get(email.id)
    draft_result = await session.execute(
        select(ProjectEmailDraft).where(ProjectEmailDraft.project_id == project_id)
    )
    attachment_result = await session.execute(
        select(ProjectEmailAttachment).where(
            ProjectEmailAttachment.email_id.in_(
                select(ProjectEmailInterpretation.email_id).where(
                    ProjectEmailInterpretation.project_id == project_id
                )
            )
        )
    )
    submission_result = await session.execute(
        select(ProcurementRequestSubmission).join(
            ProcurementRequest,
            ProcurementRequest.id == ProcurementRequestSubmission.request_id,
        ).where(ProcurementRequest.project_id == project_id)
    )
    return PulseSnapshot(
        verbs=verbs,
        invoices=tuple(invoice_result.scalars().all()),
        documents=tuple(document_result.scalars().all()),
        dismissed=tuple(dismissed_result.scalars().all()),
        emails=emails,
        drafts=tuple(draft_result.scalars().all()),
        attachments=tuple(attachment_result.scalars().all()),
        submissions=tuple(submission_result.scalars().all()),
    )


async def build_pulse_feed(
    session: AsyncSession,
    project_id: uuid.UUID,
    *,
    since: datetime | None = None,
    now: datetime | None = None,
) -> PulseFeed:
    generated_at = now or datetime.now(UTC)
    window_start = resolve_pulse_since(now=generated_at, since=since)
    snapshot = await load_pulse_snapshot(session, project_id, since=window_start)
    return synthesize_pulse_feed(snapshot, now=generated_at, since=window_start)
