from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cost_plan.invoice_candidates import InvoiceCandidate
from app.cost_plan.invoice_extraction import extract_invoice
from app.cost_plan.invoice_issues import (
    InvoiceIssue,
    arithmetic_issues,
    field_reconciliation,
    should_run_secondary,
)
from app.cost_plan.invoice_service import (
    InvoiceDecisionBlocked,
    InvoiceIllegalTransition,
    book_invoice,
    decide_invoice,
    transition_review_state,
)
from app.cost_plan.invoice_snapshot import (
    MachineExtractionImmutable,
    ReviewedLinesNotAllowed,
    apply_reviewed_overlay,
    effective_extraction,
    effective_invoice_number,
    set_machine_extraction,
)
from app.cost_plan.schemas import ExtractedInvoice, InvoiceAllocationInput
from tests.conftest import run_async
from tests.cost_plan.test_invoice_processing import _candidate


def _clean_extracted() -> ExtractedInvoice:
    return extract_invoice(_candidate("11-tax-invoice-quoin-architecture-01.md"))


def test_updating_reviewed_invoice_number_does_not_change_machine_snapshot() -> None:
    invoice = SimpleNamespace(
        machine_extraction={"invoice_number": "INV-1O42", "lines": []},
        reviewed_extraction={},
        reviewed_by_user_id=None,
        reviewed_at=None,
        supplier_name="Acme",
        invoice_number="INV-1O42",
        invoice_date=date(2026, 3, 18),
        due_date=None,
        po_number=None,
        related_reference=None,
        subtotal_ex_gst=None,
        gst=None,
        total_including_gst=None,
        billing_month=date(2026, 3, 1),
    )
    apply_reviewed_overlay(
        invoice,
        {"invoice_number": "INV-1042"},
        actor_id=uuid.uuid4(),
        reviewed_at=datetime.now(timezone.utc),
    )
    assert invoice.machine_extraction["invoice_number"] == "INV-1O42"
    assert effective_invoice_number(invoice) == "INV-1042"


def test_reviewed_overlay_cannot_silently_replace_machine_lines() -> None:
    extracted = _clean_extracted()
    invoice = SimpleNamespace(
        machine_extraction=extracted.model_dump(mode="json"),
        reviewed_extraction={"lines": []},
    )
    with pytest.raises(ReviewedLinesNotAllowed):
        effective_extraction(invoice)


def test_machine_extraction_is_immutable_after_insert() -> None:
    invoice = SimpleNamespace(machine_extraction={"invoice_number": "INV-1"})
    with pytest.raises(MachineExtractionImmutable):
        set_machine_extraction(invoice, {"invoice_number": "INV-2"})


def test_extract_with_total_mismatch_still_inserts_machine_snapshot() -> None:
    source = _candidate("11-tax-invoice-quoin-architecture-01.md")
    dirty = InvoiceCandidate(
        source_document_id=source.source_document_id,
        workspace_file_id=source.workspace_file_id,
        filename=source.filename,
        relative_path=source.relative_path,
        content_hash=source.content_hash,
        content=source.content.replace("$26,400.00", "$30,000.00"),
    )
    extracted = extract_invoice(dirty)
    issues = arithmetic_issues(extracted)
    assert any(issue.code == "GST_MISMATCH" for issue in issues)

    empty = MagicMock()
    empty.scalars.return_value.first.return_value = None
    session = AsyncMock()
    session.execute.return_value = empty
    session.add = MagicMock()
    session.flush = AsyncMock()

    with patch("app.cost_plan.invoice_service.record_project_verb", new=AsyncMock()):
        result = run_async(
            book_invoice(
                session,
                project_id=uuid.uuid4(),
                created_by_user_id=uuid.uuid4(),
                candidate=dirty,
                extracted=extracted,
                allocations=[
                    InvoiceAllocationInput(
                        line_number=1,
                        description="Stage 1 — Schematic Design, completed",
                        amount_ex_gst=extracted.subtotal_ex_gst,
                        gst_treatment="taxable",
                        cost_item_label="Unidentified",
                    )
                ],
            )
        )

    invoice = result.invoice
    assert invoice is not None
    assert invoice.processing_status == "needs_review"
    assert invoice.review_state == "needs_attention"
    assert invoice.machine_extraction["invoice_number"] == "QUA-2601"
    assert invoice.subtotal_ex_gst is None
    assert invoice.review_state != "posted"


def test_book_invoice_without_approval_cannot_reach_posted() -> None:
    extracted = _clean_extracted()
    empty = MagicMock()
    empty.scalars.return_value.first.return_value = None
    session = AsyncMock()
    session.execute.return_value = empty
    session.add = MagicMock()
    session.flush = AsyncMock()
    with patch("app.cost_plan.invoice_service.record_project_verb", new=AsyncMock()):
        result = run_async(
            book_invoice(
                session,
                project_id=uuid.uuid4(),
                created_by_user_id=uuid.uuid4(),
                candidate=_candidate("11-tax-invoice-quoin-architecture-01.md"),
                extracted=extracted,
                allocations=[
                    InvoiceAllocationInput(
                        line_number=1,
                        description=extracted.lines[0].description,
                        amount_ex_gst=extracted.subtotal_ex_gst,
                        gst_treatment="taxable",
                        cost_item_key="architect",
                        cost_item_label="Architect",
                        mapping_method="exact",
                        review_status="mapped",
                    )
                ],
            )
        )
    assert result.invoice is not None
    assert result.invoice.review_state != "posted"
    assert result.invoice.review_state == "ready_for_review"


def test_total_mismatch_emits_coded_issue_not_exception() -> None:
    extracted = ExtractedInvoice.model_validate(
        {
            "supplier_name": "Acme",
            "invoice_number": "INV-1",
            "invoice_date": "2026-03-18",
            "subtotal_ex_gst": "100.00",
            "gst": "10.00",
            "total_including_gst": "200.00",
            "lines": [{"description": "Fee", "amount_ex_gst": "50.00"}],
        },
        context={"strict": False},
    )
    issues = arithmetic_issues(extracted)
    assert {issue.code for issue in issues} >= {"TOTAL_MISMATCH", "GST_MISMATCH"}


def test_reviewed_invoice_number_marks_field_different() -> None:
    invoice = SimpleNamespace(
        machine_extraction={"invoice_number": "INV-1O42", "supplier_name": "Acme"},
        reviewed_extraction={"invoice_number": "INV-1042"},
    )
    status = field_reconciliation(invoice)
    assert status["invoice_number"] == "different"
    assert status["supplier_name"] == "missing_secondary"


def test_clean_invoice_does_not_run_secondary_extraction() -> None:
    extracted = _clean_extracted()
    snapshot = extracted.model_dump(mode="json")
    assert should_run_secondary([], snapshot) is False


def test_should_run_secondary_on_total_mismatch() -> None:
    assert should_run_secondary(
        [InvoiceIssue(code="TOTAL_MISMATCH", severity="error", message="mismatch")],
        {"supplier_name": "Acme", "invoice_number": "1", "invoice_date": "2026-01-01", "subtotal_ex_gst": "1"},
    )


def test_illegal_transition_raises() -> None:
    invoice = SimpleNamespace(review_state="posted")
    with pytest.raises(InvoiceIllegalTransition):
        transition_review_state(invoice, "rejected")


def test_approve_with_open_error_issues_is_blocked() -> None:
    invoice = SimpleNamespace(
        id=uuid.uuid4(),
        issues=[{"code": "TOTAL_MISMATCH", "severity": "error", "message": "bad"}],
        review_state="ready_for_review",
        processing_status="needs_review",
        reviewed_by_user_id=None,
        reviewed_at=None,
        revision=1,
        allocations=[],
    )
    session = AsyncMock()
    session.flush = AsyncMock()
    with (
        patch(
            "app.cost_plan.invoice_service._load_project_invoice",
            new=AsyncMock(return_value=invoice),
        ),
        pytest.raises(InvoiceDecisionBlocked),
    ):
        run_async(
            decide_invoice(
                session,
                project_id=uuid.uuid4(),
                invoice_id=invoice.id,
                actor_id=uuid.uuid4(),
                decision="approve",
                reason=None,
            )
        )
