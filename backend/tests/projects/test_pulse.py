"""Pulse synthesizer (X1 Stage 14). Fast unit tests; no live database."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import get_args
from unittest.mock import AsyncMock, patch

from sqlalchemy.sql.dml import Insert, Update
from sqlalchemy.sql.selectable import Select

from app.cost_plan.models import CostInvoice
from app.database.activity_event import ActivityEvent
from app.database.procurement_request_submission import ProcurementRequestSubmission
from app.database.source_document import SourceDocument
from app.email.models import (
    ProjectEmail,
    ProjectEmailAttachment,
    ProjectEmailDraft,
    ProjectEmailInterpretation,
)
from app.projects.pulse import (
    MAX_ATTENTION_ITEMS,
    MIN_GROUPED,
    PULSE_QUERY_COUNT,
    PULSE_SIGNAL_TYPES,
    PulseSignalType,
    PulseSnapshot,
    assert_read_only,
    build_pulse_feed,
    synthesize_pulse_feed,
)
from ingest.router import REVIEW_CONFIDENCE_MIN
from tests.conftest import run_async

PROJECT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
NOW = datetime(2026, 8, 19, 10, 0, tzinfo=UTC)


def _stamp(offset_seconds: int = 0) -> datetime:
    return NOW + timedelta(seconds=offset_seconds)


def _verb(
    source: str,
    *,
    reference_id: uuid.UUID | None = None,
    metadata: dict | None = None,
    created_at: datetime | None = None,
    message: str = "",
    reference_type: str = "source_document",
) -> ActivityEvent:
    return ActivityEvent(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        run_id=uuid.uuid4(),
        source=source,
        reference_type=reference_type,
        reference_id=reference_id or uuid.uuid4(),
        step=source,
        status="complete",
        message=message,
        event_metadata=metadata or {},
        created_at=created_at or NOW,
    )


def _document(
    *,
    document_class: str = "unknown",
    filename: str = "Note.pdf",
    confidence: str | None = None,
    created_at: datetime | None = None,
    document_id: uuid.UUID | None = None,
    drawing_number: str | None = None,
) -> SourceDocument:
    metadata: dict = {}
    if confidence is not None:
        metadata["confidence"] = confidence
    if drawing_number is not None:
        metadata["drawing_number"] = drawing_number
    return SourceDocument(
        id=document_id or uuid.uuid4(),
        project_id=PROJECT_ID,
        project="demo",
        phase="delivery",
        document_class=document_class,
        filename=filename,
        relative_path=f"04-projects/demo/{filename}",
        normalized_content="x" * 200,
        document_metadata=metadata,
        created_at=created_at or NOW,
        updated_at=created_at or NOW,
    )


def _invoice(
    *,
    review_state: str = "ready_for_review",
    issues: list | None = None,
    supplier_name: str = "Builder",
    invoice_number: str = "009",
    total: str = "8400.00",
    created_at: datetime | None = None,
    invoice_id: uuid.UUID | None = None,
    source_document_id: uuid.UUID | None = None,
) -> CostInvoice:
    return CostInvoice(
        id=invoice_id or uuid.uuid4(),
        project_id=PROJECT_ID,
        source_document_id=source_document_id,
        source_content_hash="a" * 64,
        source_locator="inbox/invoice.pdf",
        supplier_name=supplier_name,
        supplier_key=supplier_name.casefold(),
        invoice_number=invoice_number,
        invoice_key=invoice_number.casefold(),
        invoice_date=NOW.date(),
        billing_month=NOW.date().replace(day=1),
        total_including_gst=Decimal(total),
        subtotal_ex_gst=Decimal("7636.36"),
        gst=Decimal("763.64"),
        review_state=review_state,
        issues=issues or [],
        created_by_user_id=uuid.uuid4(),
        created_at=created_at or NOW,
        updated_at=created_at or NOW,
    )


def _snapshot(
    *,
    verbs: list[ActivityEvent] | None = None,
    invoices: list[CostInvoice] | None = None,
    documents: list[SourceDocument] | None = None,
    dismissed: list[ActivityEvent] | None = None,
    emails: list | None = None,
    drafts: list | None = None,
    attachments: list | None = None,
    submissions: list | None = None,
) -> PulseSnapshot:
    return PulseSnapshot(
        verbs=tuple(verbs or ()),
        invoices=tuple(invoices or ()),
        documents=tuple(documents or ()),
        dismissed=tuple(dismissed or ()),
        emails=tuple(emails or ()),
        drafts=tuple(drafts or ()),
        attachments=tuple(attachments or ()),
        submissions=tuple(submissions or ()),
    )


def _email(
    *,
    email_id: uuid.UUID | None = None,
    subject: str = "Hello",
    body_text: str = "",
    from_address: str = "qs@consultant.com",
    provider_thread_id: str | None = None,
    internet_message_id: str | None = None,
    headers: dict | None = None,
    created_at: datetime | None = None,
    message_category: str | None = None,
    provider_message_id: str | None = None,
) -> ProjectEmail:
    stamp = created_at or NOW
    eid = email_id or uuid.uuid4()
    email = ProjectEmail(
        id=eid,
        provider="fake",
        provider_message_id=provider_message_id or f"msg-{eid}",
        provider_thread_id=provider_thread_id,
        internet_message_id=internet_message_id or f"<{eid}@example.com>",
        from_address=from_address,
        to_addresses=["pm@owner.com"],
        cc_addresses=[],
        subject=subject,
        sent_at=stamp,
        body_text=body_text,
        headers=headers or {},
        content_hash="b" * 64,
        created_at=stamp,
    )
    email.interpretation = ProjectEmailInterpretation(
        email_id=eid,
        project_id=PROJECT_ID,
        message_category=message_category,
        actions=[],
        updated_at=stamp,
    )
    return email


def _draft(
    *,
    in_reply_to_email_id: uuid.UUID | None = None,
    status: str = "draft",
    sent_at: datetime | None = None,
    created_at: datetime | None = None,
) -> ProjectEmailDraft:
    return ProjectEmailDraft(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        created_by_user_id=uuid.uuid4(),
        in_reply_to_email_id=in_reply_to_email_id,
        to_addresses=["qs@consultant.com"],
        cc_addresses=[],
        subject="Re: Hello",
        body_text="Thanks",
        status=status,
        sent_at=sent_at,
        references={},
    )


def _attachment(
    *,
    email_id: uuid.UUID,
    source_document_id: uuid.UUID | None = None,
    filename: str = "file.pdf",
) -> ProjectEmailAttachment:
    return ProjectEmailAttachment(
        id=uuid.uuid4(),
        email_id=email_id,
        provider_attachment_id=f"att-{uuid.uuid4()}",
        filename=filename,
        content_type="application/pdf",
        size_bytes=100,
        source_document_id=source_document_id,
    )


def _submission(
    *,
    request_id: uuid.UUID | None = None,
    source_document_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
) -> ProcurementRequestSubmission:
    return ProcurementRequestSubmission(
        request_id=request_id or uuid.uuid4(),
        source_document_id=source_document_id or uuid.uuid4(),
        created_at=created_at or NOW,
    )


def _feed(**kwargs) -> object:
    since = kwargs.pop("since", None)
    return synthesize_pulse_feed(_snapshot(**kwargs), now=NOW, since=since)


class CountingSession:
    def __init__(
        self,
        *,
        documents: list[SourceDocument] | None = None,
        invoices: list[CostInvoice] | None = None,
        verbs: list[ActivityEvent] | None = None,
        dismissed: list[ActivityEvent] | None = None,
        emails: list | None = None,
        drafts: list | None = None,
        attachments: list | None = None,
        submissions: list | None = None,
        interpretations: list | None = None,
    ) -> None:
        self.calls: list = []
        self.documents = documents or []
        self.invoices = invoices or []
        self.verbs = verbs or []
        self.dismissed = dismissed or []
        self.emails = emails or []
        self.drafts = drafts or []
        self.attachments = attachments or []
        self.submissions = submissions or []
        self.interpretations = interpretations or []

    async def execute(self, statement):
        assert_read_only(statement)
        self.calls.append(statement)
        sql = str(statement.compile()).upper()
        if "PROCUREMENT_REQUEST_SUBMISSIONS" in sql:
            rows = self.submissions
        elif "PROJECT_EMAIL_DRAFTS" in sql:
            rows = self.drafts
        elif "PROJECT_EMAIL_ATTACHMENTS" in sql:
            rows = self.attachments
        elif "PROJECT_EMAILS" in sql:
            rows = self.emails
        elif "PROJECT_EMAIL_INTERPRETATIONS" in sql:
            rows = self.interpretations
        elif "COST_INVOICES" in sql:
            rows = self.invoices
        elif "SOURCE_DOCUMENTS" in sql:
            rows = self.documents
        elif "ACTIVITY_EVENTS" in sql and "IN " not in sql.replace("NOT IN", ""):
            rows = self.dismissed
        else:
            rows = self.verbs
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: list(rows)))


class WriteGuardSession:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, statement):
        self.calls += 1
        assert_read_only(statement)
        if isinstance(statement, (Insert, Update)):
            raise AssertionError("write reached execute")
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))


def test_pulse_signal_types_are_closed() -> None:
    assert set(get_args(PulseSignalType)) == {
        "drawing_revision",
        "approval_received",
        "invoice_review_required",
        "potential_cost_change",
        "document_needs_classification",
        "tender_received",
        "unanswered_correspondence",
    }
    assert "programme_risk" not in PULSE_SIGNAL_TYPES
    assert "decision_required" not in PULSE_SIGNAL_TYPES
    assert "consultant_action_due" not in PULSE_SIGNAL_TYPES


def test_dismissed_subject_key_is_excluded() -> None:
    doc_id = uuid.uuid4()
    item_key = (
        f"document_needs_classification:source_document:{doc_id}:unknown"
    )
    feed = _feed(
        documents=[_document(document_id=doc_id, filename="Keep.pdf")],
        dismissed=[
            _verb(
                "project_signal.dismissed",
                metadata={
                    "signal_type": "document_needs_classification",
                    "subject_key": item_key,
                },
            )
        ],
    )
    assert feed.attention == []
    assert feed.attention_count == 0


def test_synthesizer_does_not_write_canonical_rows() -> None:
    session = WriteGuardSession()
    feed = run_async(build_pulse_feed(session, PROJECT_ID))
    assert feed.attention_count == 0
    assert session.calls == PULSE_QUERY_COUNT


def test_forty_unclassified_documents_produce_one_grouped_card() -> None:
    documents = [
        _document(filename=f"Unknown {index}.pdf", created_at=_stamp(index))
        for index in range(40)
    ]
    feed = _feed(documents=documents)
    assert len(feed.attention) == 1
    card = feed.attention[0]
    assert card.id == "document_needs_classification:group"
    assert card.body == "40 documents need classification"
    assert feed.attention_count == 1
    assert len(card.evidence) <= MIN_GROUPED


def test_attention_never_exceeds_max_attention_items() -> None:
    documents = [
        _document(
            document_class="report",
            filename=f"Low {index}.pdf",
            confidence="0.40",
            created_at=_stamp(index),
        )
        for index in range(2)
    ]
    invoices = [
        _invoice(invoice_number=f"R{index}", created_at=_stamp(10 + index))
        for index in range(2)
    ]
    cost = [
        _invoice(
            invoice_number=f"C{index}",
            issues=[{"code": "COST_PLAN_OVERRUN", "severity": "error", "message": "x"}],
            created_at=_stamp(20 + index),
        )
        for index in range(2)
    ]
    verbs = [
        _verb(
            "document.revised",
            metadata={
                "drawing_number": f"S20{index}",
                "revision": "C",
                "previous_revision": "B",
            },
            created_at=_stamp(30 + index),
        )
        for index in range(2)
    ] + [
        _verb(
            "document.classified",
            metadata={
                "document_class": "certificate",
                "document_subject": "planning",
                "filename": f"Cert {index}.pdf",
            },
            created_at=_stamp(40 + index),
        )
        for index in range(2)
    ]
    feed = _feed(documents=documents, invoices=invoices + cost, verbs=verbs)
    assert len(feed.attention) <= MAX_ATTENTION_ITEMS
    assert feed.attention_count == 10
    assert len(feed.attention) == MAX_ATTENTION_ITEMS


def test_truncated_items_appear_in_other_rollup() -> None:
    verbs = [
        _verb(
            "document.revised",
            metadata={
                "drawing_number": f"S{index}",
                "revision": "C",
                "previous_revision": "B",
            },
            created_at=_stamp(index),
        )
        for index in range(2)
    ]
    invoices = [
        _invoice(invoice_number=f"I{index}", created_at=_stamp(10 + index))
        for index in range(2)
    ]
    cost = [
        _invoice(
            invoice_number=f"V{index}",
            issues=[{"code": "UNAPPROVED_VARIATION", "severity": "error", "message": "x"}],
            created_at=_stamp(20 + index),
        )
        for index in range(2)
    ]
    certs = [
        _verb(
            "document.classified",
            metadata={"document_class": "certificate", "filename": f"C{index}.pdf"},
            created_at=_stamp(30 + index),
        )
        for index in range(2)
    ]
    docs = [
        _document(filename=f"U{index}.pdf", created_at=_stamp(40 + index))
        for index in range(2)
    ]
    feed = _feed(verbs=verbs + certs, invoices=invoices + cost, documents=docs)
    assert feed.attention_count == 10
    assert len(feed.attention) == MAX_ATTENTION_ITEMS
    assert feed.other
    other_body = " ".join(item.body for item in feed.other)
    assert "3 more items" in other_body
    kept_titles = {item.title for item in feed.attention}
    named = [
        title
        for title in other_body.split("; ")
        if title and title not in kept_titles
    ]
    assert named


def test_attention_count_reflects_pre_truncation_total() -> None:
    docs = [_document(filename=f"U{index}.pdf", created_at=_stamp(index)) for index in range(2)]
    invoices = [_invoice(invoice_number=f"I{index}", created_at=_stamp(10 + index)) for index in range(2)]
    cost = [
        _invoice(
            invoice_number=f"V{index}",
            issues=[{"code": "AMOUNT_EXCEEDS_COMMITMENT", "severity": "error", "message": "x"}],
            created_at=_stamp(20 + index),
        )
        for index in range(2)
    ]
    verbs = [
        _verb(
            "document.revised",
            metadata={"drawing_number": f"S{index}", "revision": "C", "previous_revision": "B"},
            created_at=_stamp(30 + index),
        )
        for index in range(2)
    ] + [
        _verb(
            "document.classified",
            metadata={"document_class": "certificate", "filename": f"Cert{index}.pdf"},
            created_at=_stamp(40 + index),
        )
        for index in range(2)
    ]
    feed = _feed(documents=docs, invoices=invoices + cost, verbs=verbs)
    assert feed.attention_count == 10
    assert len(feed.attention) == MAX_ATTENTION_ITEMS
    assert feed.attention_count > len(feed.attention)


def test_build_pulse_feed_issues_a_fixed_number_of_queries() -> None:
    empty = CountingSession()
    run_async(build_pulse_feed(empty, PROJECT_ID))
    crowded = CountingSession(
        documents=[_document(filename=f"U{index}.pdf") for index in range(50)]
    )
    run_async(build_pulse_feed(crowded, PROJECT_ID))
    assert len(empty.calls) == PULSE_QUERY_COUNT
    assert len(crowded.calls) == PULSE_QUERY_COUNT
    assert len(crowded.calls) == len(empty.calls)


def test_drawing_revision_detector_uses_document_revised_verb() -> None:
    doc_id = uuid.uuid4()
    feed = _feed(
        verbs=[
            _verb(
                "document.revised",
                reference_id=doc_id,
                metadata={
                    "drawing_number": "S203",
                    "revision": "C",
                    "previous_revision": "B",
                    "filename": "S203.pdf",
                },
            )
        ]
    )
    assert len(feed.attention) == 1
    card = feed.attention[0]
    assert card.signal_type == "drawing_revision"
    assert card.title == "S203 Rev C supersedes Rev B"
    assert card.evidence[0].reference_id == doc_id


def test_invoice_with_unapproved_variation_is_potential_cost_change() -> None:
    invoice = _invoice(
        issues=[{"code": "UNAPPROVED_VARIATION", "severity": "error", "message": "var"}],
    )
    feed = _feed(invoices=[invoice])
    assert len(feed.attention) == 1
    card = feed.attention[0]
    assert card.signal_type == "potential_cost_change"
    assert "unapproved variation" in card.title
    assert "$8,400" in card.title
    assert "review_invoice" in card.actions


def test_low_confidence_document_needs_classification() -> None:
    assert REVIEW_CONFIDENCE_MIN == 0.65
    feed = _feed(
        documents=[
            _document(
                document_class="report",
                filename="Heritage.pdf",
                confidence="0.55",
            )
        ]
    )
    assert len(feed.attention) == 1
    assert feed.attention[0].signal_type == "document_needs_classification"
    assert feed.attention[0].title == "Heritage.pdf needs classification"


def test_certificate_classified_is_approval_received() -> None:
    nod = _verb(
        "document.classified",
        metadata={
            "document_class": "certificate",
            "document_subject": "planning",
            "filename": "Notice of Determination - DA.pdf",
        },
    )
    other = _verb(
        "document.classified",
        metadata={
            "document_class": "certificate",
            "document_subject": "planning",
            "filename": "Occupation Certificate.pdf",
        },
        created_at=_stamp(-10),
    )
    feed = _feed(verbs=[nod, other])
    titles = {item.title for item in feed.attention}
    assert "Notice of Determination received" in titles
    assert "Planning certificate received" in titles
    assert all(item.signal_type == "approval_received" for item in feed.attention)


def test_one_invoice_does_not_produce_two_attention_cards() -> None:
    invoice = _invoice(
        issues=[{"code": "UNAPPROVED_VARIATION", "severity": "error", "message": "var"}],
    )
    feed = _feed(invoices=[invoice])
    assert len(feed.attention) == 1
    assert feed.attention[0].signal_type == "potential_cost_change"
    assert "review_invoice" in feed.attention[0].actions


def test_detectors_do_not_call_decide_invoice() -> None:
    with patch(
        "app.cost_plan.invoice_service.decide_invoice",
        new=AsyncMock(side_effect=AssertionError("decide_invoice must not run")),
    ) as decide:
        feed = _feed(
            invoices=[
                _invoice(
                    issues=[
                        {
                            "code": "UNAPPROVED_VARIATION",
                            "severity": "error",
                            "message": "var",
                        }
                    ]
                )
            ]
        )
        assert feed.attention
        decide.assert_not_called()


def test_detectors_do_not_call_send_email_draft() -> None:
    received = NOW - timedelta(days=5)
    email = _email(
        subject="RFI-12: slab thickness",
        message_category="rfi",
        created_at=received,
    )
    with patch(
        "app.email.service.send_email_draft",
        new=AsyncMock(side_effect=AssertionError("send_email_draft must not run")),
    ) as send:
        feed = _feed(
            emails=[email],
            verbs=[
                _verb(
                    "email.received",
                    reference_id=email.id,
                    reference_type="email",
                    created_at=received,
                )
            ],
        )
        assert feed.attention
        assert "draft_reply" in feed.attention[0].actions
        send.assert_not_called()


def test_dismissed_invoice_card_returns_when_review_state_changes() -> None:
    invoice_id = uuid.uuid4()
    first = _invoice(invoice_id=invoice_id, review_state="ready_for_review")
    key = f"invoice_review_required:cost_invoice:{invoice_id}:ready_for_review"
    dismissed_feed = _feed(
        invoices=[first],
        dismissed=[
            _verb(
                "project_signal.dismissed",
                metadata={"signal_type": "invoice_review_required", "subject_key": key},
            )
        ],
    )
    assert dismissed_feed.attention == []
    changed = _invoice(invoice_id=invoice_id, review_state="needs_attention")
    returned = _feed(
        invoices=[changed],
        dismissed=[
            _verb(
                "project_signal.dismissed",
                metadata={"signal_type": "invoice_review_required", "subject_key": key},
            )
        ],
    )
    assert len(returned.attention) == 1
    assert returned.attention[0].id.endswith(":needs_attention")


def test_acceptance_g_unapproved_variation_pulse_attention() -> None:
    invoice = _invoice(
        supplier_name="Builder",
        invoice_number="009",
        total="8400.00",
        issues=[{"code": "UNAPPROVED_VARIATION", "severity": "error", "message": "var"}],
    )
    feed = run_async(
        build_pulse_feed(
            CountingSession(invoices=[invoice]),
            PROJECT_ID,
        )
    )
    assert len(feed.attention) == 1
    card = feed.attention[0]
    assert card.signal_type == "potential_cost_change"
    assert "review_invoice" in card.actions
    assert "unapproved variation" in card.title


def test_acceptance_i_drawing_revision_pulse_attention() -> None:
    feed = run_async(
        build_pulse_feed(
            CountingSession(
                verbs=[
                    _verb(
                        "document.revised",
                        metadata={
                            "drawing_number": "S203",
                            "revision": "C",
                            "previous_revision": "B",
                        },
                    )
                ]
            ),
            PROJECT_ID,
        )
    )
    assert len(feed.attention) == 1
    assert feed.attention[0].signal_type == "drawing_revision"
    assert "S203 Rev C supersedes Rev B" in feed.attention[0].title


def test_grouped_card_reappears_after_new_member() -> None:
    early = [_document(filename=f"Old {index}.pdf", created_at=_stamp(index)) for index in range(5)]
    dismissed = [
        _verb(
            "project_signal.dismissed",
            metadata={
                "signal_type": "document_needs_classification",
                "subject_key": "document_needs_classification:group",
            },
            created_at=_stamp(10),
        )
    ]
    hidden = _feed(documents=early, dismissed=dismissed)
    assert hidden.attention == []
    later = early + [
        _document(filename=f"New {index}.pdf", created_at=_stamp(20 + index))
        for index in range(3)
    ]
    raised = _feed(documents=later, dismissed=dismissed)
    assert len(raised.attention) == 1
    assert raised.attention[0].id == "document_needs_classification:group"
    assert "3 documents" in raised.attention[0].body


def test_select_statements_are_not_treated_as_writes() -> None:
    from sqlalchemy import select as sa_select

    stmt = sa_select(ActivityEvent.id)
    assert isinstance(stmt, Select)
    assert_read_only(stmt)


def test_since_yesterday_hides_older_drawing_revision() -> None:
    yesterday = NOW - timedelta(days=1)
    older_id = uuid.uuid4()
    newer_id = uuid.uuid4()
    feed = _feed(
        since=yesterday,
        verbs=[
            _verb(
                "document.revised",
                reference_id=older_id,
                metadata={
                    "drawing_number": "S201",
                    "revision": "C",
                    "previous_revision": "B",
                },
                created_at=NOW - timedelta(days=3),
            ),
            _verb(
                "document.revised",
                reference_id=newer_id,
                metadata={
                    "drawing_number": "S203",
                    "revision": "C",
                    "previous_revision": "B",
                },
                created_at=NOW - timedelta(hours=2),
            ),
        ],
    )
    assert feed.since == yesterday
    assert [item.evidence[0].reference_id for item in feed.attention] == [newer_id]


def test_omitted_since_is_seven_days_not_unbounded() -> None:
    from app.projects.pulse import DEFAULT_SINCE_DAYS

    older_id = uuid.uuid4()
    newer_id = uuid.uuid4()
    feed = _feed(
        verbs=[
            _verb(
                "document.revised",
                reference_id=older_id,
                metadata={
                    "drawing_number": "S199",
                    "revision": "C",
                    "previous_revision": "B",
                },
                created_at=NOW - timedelta(days=8),
            ),
            _verb(
                "document.revised",
                reference_id=newer_id,
                metadata={
                    "drawing_number": "S203",
                    "revision": "C",
                    "previous_revision": "B",
                },
                created_at=NOW - timedelta(days=2),
            ),
        ]
    )
    assert DEFAULT_SINCE_DAYS == 7
    assert feed.since == NOW - timedelta(days=7)
    assert [item.evidence[0].reference_id for item in feed.attention] == [newer_id]


def test_drawing_revision_and_transmittal_email_are_one_card() -> None:
    doc_id = uuid.uuid4()
    email = _email(
        subject="Transmittal S203 Rev C",
        message_category="document_transmittal",
        body_text="Please find S203 attached.",
    )
    feed = _feed(
        verbs=[
            _verb(
                "document.revised",
                reference_id=doc_id,
                metadata={
                    "drawing_number": "S203",
                    "revision": "C",
                    "previous_revision": "B",
                    "filename": "S203.pdf",
                },
            ),
            _verb(
                "email.received",
                reference_id=email.id,
                reference_type="email",
                metadata={"subject_key": str(email.id)},
            ),
        ],
        emails=[email],
        attachments=[
            _attachment(email_id=email.id, source_document_id=doc_id, filename="S203.pdf")
        ],
        documents=[
            _document(
                document_id=doc_id,
                document_class="drawing",
                filename="S203.pdf",
                confidence="0.95",
                drawing_number="S203",
            )
        ],
    )
    assert len(feed.attention) == 1
    card = feed.attention[0]
    assert "transmittal" in card.title.lower()
    assert "S203" in card.title
    evidence_types = {ref.reference_type for ref in card.evidence}
    assert "source_document" in evidence_types
    assert "email" in evidence_types


def test_email_invoice_is_one_card_not_email_plus_invoice() -> None:
    doc_id = uuid.uuid4()
    invoice = _invoice(source_document_id=doc_id)
    email = _email(
        subject="Invoice 009 attached",
        message_category="invoice_notice",
    )
    feed = _feed(
        invoices=[invoice],
        emails=[email],
        attachments=[
            _attachment(
                email_id=email.id,
                source_document_id=doc_id,
                filename="Invoice 009.pdf",
            )
        ],
        verbs=[
            _verb(
                "email.received",
                reference_id=email.id,
                reference_type="email",
                metadata={"subject_key": str(email.id)},
            ),
            _verb(
                "invoice.needs_review",
                reference_id=invoice.id,
                reference_type="cost_invoice",
            ),
        ],
    )
    assert len(feed.attention) == 1
    card = feed.attention[0]
    assert "email" in card.title.lower()
    assert "review_invoice" in card.actions
    evidence_types = {ref.reference_type for ref in card.evidence}
    assert "cost_invoice" in evidence_types
    assert "email" in evidence_types


def test_unanswered_rfi_is_attention_after_five_days() -> None:
    received = NOW - timedelta(days=5)
    email = _email(
        subject="RFI-12: slab thickness",
        message_category="rfi",
        created_at=received,
    )
    feed = _feed(
        emails=[email],
        verbs=[
            _verb(
                "email.received",
                reference_id=email.id,
                reference_type="email",
                metadata={"subject_key": str(email.id)},
                created_at=received,
            )
        ],
    )
    assert len(feed.attention) == 1
    card = feed.attention[0]
    assert card.signal_type == "unanswered_correspondence"
    assert "draft_reply" in card.actions
    assert "view_thread" in card.actions
    assert "dismiss" in card.actions


def test_failed_send_does_not_clear_unanswered_correspondence() -> None:
    received = NOW - timedelta(days=5)
    email = _email(
        subject="RFI-12: slab thickness",
        message_category="rfi",
        created_at=received,
    )
    feed = _feed(
        emails=[email],
        drafts=[
            _draft(in_reply_to_email_id=email.id, status="send_failed"),
            _draft(in_reply_to_email_id=None, status="sent", sent_at=NOW),
        ],
        verbs=[
            _verb(
                "email.received",
                reference_id=email.id,
                reference_type="email",
                metadata={"subject_key": str(email.id)},
                created_at=received,
            )
        ],
    )
    assert len(feed.attention) == 1
    assert feed.attention[0].signal_type == "unanswered_correspondence"


def test_sent_reply_on_thread_key_clears_unanswered_correspondence() -> None:
    received = NOW - timedelta(days=6)
    original = _email(
        subject="RFI-12: slab thickness",
        message_category="rfi",
        internet_message_id="<rfi-12@example.com>",
        created_at=received,
    )
    follow_up = _email(
        subject="Re: RFI-12: slab thickness",
        message_category="rfi",
        internet_message_id="<rfi-12-follow@example.com>",
        headers={"In-Reply-To": "<rfi-12@example.com>"},
        created_at=received + timedelta(days=1),
    )
    feed = _feed(
        emails=[original, follow_up],
        drafts=[
            _draft(
                in_reply_to_email_id=follow_up.id,
                status="sent",
                sent_at=NOW - timedelta(days=1),
            )
        ],
        verbs=[
            _verb(
                "email.received",
                reference_id=original.id,
                reference_type="email",
                created_at=received,
            )
        ],
    )
    assert feed.attention == []


def test_tender_received_from_linked_submission() -> None:
    doc_id = uuid.uuid4()
    request_id = uuid.uuid4()
    document = _document(
        document_id=doc_id,
        document_class="commercial",
        filename="Builder B final.pdf",
        confidence="0.90",
    )
    feed = _feed(
        documents=[document],
        submissions=[_submission(request_id=request_id, source_document_id=doc_id)],
    )
    assert len(feed.attention) == 1
    card = feed.attention[0]
    assert card.signal_type == "tender_received"
    assert card.title == "Submission received from Builder B final.pdf"
    assert all(item.id != card.id or item is card for item in feed.attention)


def test_other_activity_rollup_mentions_emails() -> None:
    emails = [
        _email(
            subject=f"Consultant note {index}",
            message_category="information_only",
            created_at=NOW - timedelta(hours=index + 1),
        )
        for index in range(2)
    ]
    feed = _feed(
        emails=emails,
        verbs=[
            _verb("document.filed", created_at=NOW - timedelta(hours=1)),
            *[
                _verb(
                    "email.received",
                    reference_id=email.id,
                    reference_type="email",
                    created_at=email.created_at,
                )
                for email in emails
            ],
        ],
    )
    assert feed.attention == []
    assert feed.other
    body = feed.other[0].body
    assert "1 document filed" in body
    assert "2 consultant replies" in body
