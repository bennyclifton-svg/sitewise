from __future__ import annotations

import hashlib
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.cost_plan.invoice_candidates import InvoiceCandidate, is_invoice_document
from app.cost_plan.invoice_extraction import InvoiceExtractionError, extract_invoice
from app.cost_plan.invoice_mapping import map_invoice_allocations
from app.cost_plan.invoice_service import update_invoice_allocation, update_invoice_fields
from app.cost_plan.schemas import (
    CostItemInput,
    CostPlanState,
    DependencySnapshot,
    ExtractedInvoice,
    InvoiceFieldsUpdate,
    InvoiceLineInput,
)
from tests.conftest import run_async


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "data" / "synthetic-mobilisation-evidence" / "kavanagh-residence-cost-files"


def _candidate(filename: str) -> InvoiceCandidate:
    content = (FIXTURES / filename).read_text(encoding="utf-8")
    return InvoiceCandidate(
        source_document_id=uuid.uuid5(uuid.NAMESPACE_URL, filename),
        workspace_file_id=None,
        filename=filename,
        relative_path=f"projects/kavanagh/_inbox/{filename}",
        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        content=content,
    )


def _item(
    *,
    key: str,
    code: str,
    label: str,
    category: str = "Consultants",
    basis: str = "Fixture",
    source_refs: list[dict[str, object]] | None = None,
) -> CostItemInput:
    return CostItemInput(
        item_key=key,
        cost_code=code,
        category=category,
        item=label,
        budget="100000",
        forecast="100000",
        basis=basis,
        source_refs=source_refs or [],
    )


def _state(items: list[CostItemInput]) -> CostPlanState:
    return CostPlanState(
        project_id=uuid.uuid4(),
        version=5,
        dependency_snapshot=DependencySnapshot(
            profile_revision=1,
            evidence_fingerprint="fixture",
            decision_set_revision=1,
            runtime_version="test",
        ),
        items=items,
    )


def test_quoin_invoice_extracts_reconciled_source_facts() -> None:
    candidate = _candidate("11-tax-invoice-quoin-architecture-01.md")
    invoice = extract_invoice(candidate)

    assert is_invoice_document(filename=candidate.filename, content=candidate.content)
    assert invoice.supplier_name == "Quoin Architecture Pty Ltd"
    assert invoice.supplier_abn == "51000000680"
    assert invoice.invoice_number == "QUA-2601"
    assert invoice.invoice_date == date(2026, 3, 18)
    assert invoice.due_date == date(2026, 4, 1)
    assert invoice.billing_month == date(2026, 3, 1)
    assert invoice.related_reference == "QUA-KAV-2601"
    assert invoice.subtotal_ex_gst == Decimal("24000.00")
    assert invoice.gst == Decimal("2400.00")
    assert invoice.total_including_gst == Decimal("26400.00")
    assert [line.description for line in invoice.lines] == [
        "Stage 1 — Schematic Design, completed"
    ]


def test_mixed_gst_invoice_preserves_disbursement_as_separate_line() -> None:
    invoice = extract_invoice(_candidate("12-tax-invoice-quoin-architecture-02.md"))

    assert invoice.subtotal_ex_gst == Decimal("17760.00")
    assert invoice.gst == Decimal("1728.00")
    assert invoice.total_including_gst == Decimal("19488.00")
    assert [line.gst_treatment for line in invoice.lines] == ["taxable", "gst_free"]
    assert [line.amount_ex_gst for line in invoice.lines] == [
        Decimal("17280.00"),
        Decimal("480.00"),
    ]


def test_full_synthetic_invoice_pack_extracts_and_reconciles() -> None:
    filenames = sorted(path.name for path in FIXTURES.glob("*-tax-invoice-*.md"))

    invoices = [extract_invoice(_candidate(filename)) for filename in filenames]

    assert len(invoices) == 25
    assert len({(invoice.supplier_name, invoice.invoice_number) for invoice in invoices}) == 25
    for invoice in invoices:
        assert sum((line.amount_ex_gst for line in invoice.lines), Decimal("0.00")) == (
            invoice.subtotal_ex_gst
        )
        assert invoice.subtotal_ex_gst + invoice.gst == invoice.total_including_gst


def test_quoin_invoice_maps_fee_by_related_proposal_and_disbursement_by_keyword() -> None:
    state = _state(
        [
            _item(
                key="architect",
                code="3",
                label="Architect / PM",
                source_refs=[
                    {
                        "proposal_reference": "QUA-KAV-2601",
                        "supplier": "Quoin Architecture Pty Ltd",
                    }
                ],
            ),
            _item(
                key="statutory",
                code="2.3",
                label="Statutory and authority fees",
                category="Fees and charges",
            ),
        ]
    )
    invoice = extract_invoice(_candidate("12-tax-invoice-quoin-architecture-02.md"))
    allocations = map_invoice_allocations(invoice, state)

    assert [(row.cost_item_key, row.amount_ex_gst) for row in allocations] == [
        ("architect", Decimal("17280.00")),
        ("statutory", Decimal("480.00")),
    ]
    assert all(row.review_status == "mapped" for row in allocations)


def test_invoice_mapping_withholds_an_ambiguous_allocation() -> None:
    state = _state(
        [
            _item(key="a", code="1", label="Consultant A"),
            _item(key="b", code="2", label="Consultant B"),
        ]
    )
    invoice = extract_invoice(_candidate("11-tax-invoice-quoin-architecture-01.md"))
    allocation = map_invoice_allocations(invoice, state)[0]

    assert allocation.cost_item_key is None
    assert allocation.cost_item_label == "Unidentified"
    assert allocation.review_status == "needs_review"


def test_structural_invoice_prefers_consultant_trade_over_construction_wording() -> None:
    state = _state(
        [
            _item(
                key="structural-engineer",
                code="6",
                label="Structural engineer",
            ),
            _item(
                key="framing-and-roof",
                code="15",
                label="Framing and roof",
                category="Construction",
                basis="Structural steel and timber framing allowance",
            ),
        ]
    )
    invoice = extract_invoice(_candidate("21-tax-invoice-catenary-structures-01.md"))

    allocation = map_invoice_allocations(invoice, state)[0]

    assert allocation.cost_item_key == "structural-engineer"
    assert allocation.cost_item_label == "Structural engineer"
    assert allocation.review_status == "mapped"


def test_structural_invoice_is_not_forced_into_construction_without_trade_row() -> None:
    state = _state(
        [
            _item(
                key="framing-and-roof",
                code="15",
                label="Framing and roof",
                category="Construction",
                basis="Structural steel and timber framing allowance",
            )
        ]
    )
    invoice = extract_invoice(_candidate("21-tax-invoice-catenary-structures-01.md"))

    allocation = map_invoice_allocations(invoice, state)[0]

    assert allocation.cost_item_key is None
    assert allocation.cost_item_label == "Unidentified"
    assert allocation.review_status == "needs_review"


def test_invoice_schema_rejects_model_arithmetic_and_float_inputs() -> None:
    with pytest.raises(ValidationError, match="must not be supplied as float"):
        InvoiceLineInput(
            description="Fee",
            amount_ex_gst=100.0,
        )

    with pytest.raises(ValidationError, match="does not equal subtotal"):
        ExtractedInvoice(
            supplier_name="Supplier",
            invoice_number="INV-1",
            invoice_date=date(2026, 1, 1),
            subtotal_ex_gst="100.00",
            gst="10.00",
            total_including_gst="110.00",
            lines=[InvoiceLineInput(description="Fee", amount_ex_gst="99.00")],
        )

    with pytest.raises(ValidationError, match="does not equal 10% of taxable lines"):
        ExtractedInvoice(
            supplier_name="Supplier",
            invoice_number="INV-2",
            invoice_date=date(2026, 1, 1),
            subtotal_ex_gst="100.00",
            gst="5.00",
            total_including_gst="105.00",
            lines=[InvoiceLineInput(description="Fee", amount_ex_gst="100.00")],
        )


def test_non_invoice_document_is_rejected() -> None:
    candidate = _candidate("01-fee-proposal-quoin-architecture.md")
    assert not is_invoice_document(filename=candidate.filename, content=candidate.content)
    with pytest.raises(InvoiceExtractionError, match="is not an invoice"):
        extract_invoice(candidate)


def test_manual_invoice_controls_increment_revision_and_resolve_review() -> None:
    allocation_id = uuid.uuid4()
    allocation = SimpleNamespace(
        id=allocation_id,
        cost_item_key=None,
        cost_item_label="Unidentified",
        mapping_method="unidentified",
        mapping_confidence=None,
        review_status="needs_review",
    )
    invoice = SimpleNamespace(
        id=uuid.uuid4(),
        revision=3,
        paid=False,
        billing_month=date(2026, 3, 1),
        processing_status="needs_review",
        allocations=[allocation],
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = invoice
    session = AsyncMock()
    session.execute.return_value = result

    updated = run_async(
        update_invoice_allocation(
            session,
            project_id=uuid.uuid4(),
            allocation_id=allocation_id,
            expected_revision=3,
            cost_item_key="structural-engineer",
            cost_item_label="Structural engineer",
        )
    )

    assert updated.revision == 4
    assert updated.processing_status == "booked"
    assert allocation.cost_item_key == "structural-engineer"
    assert allocation.mapping_method == "manual"
    assert allocation.review_status == "mapped"
    session.flush.assert_awaited_once()


def test_paid_and_billing_month_update_is_invoice_level() -> None:
    invoice = SimpleNamespace(
        id=uuid.uuid4(),
        revision=1,
        paid=False,
        billing_month=date(2026, 3, 1),
        allocations=[],
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = invoice
    session = AsyncMock()
    session.execute.return_value = result

    updated = run_async(
        update_invoice_fields(
            session,
            project_id=uuid.uuid4(),
            invoice_id=invoice.id,
            expected_revision=1,
            paid=True,
            billing_month=date(2026, 4, 1),
        )
    )

    assert updated.revision == 2
    assert updated.paid is True
    assert updated.billing_month == date(2026, 4, 1)


def test_invoice_field_update_requires_a_change_and_month_start() -> None:
    with pytest.raises(ValidationError, match="paid or billing_month is required"):
        InvoiceFieldsUpdate(expected_revision=1, expected_cost_plan_version=2)
    with pytest.raises(ValidationError, match="must be the first day"):
        InvoiceFieldsUpdate(
            expected_revision=1,
            expected_cost_plan_version=2,
            billing_month=date(2026, 4, 12),
        )
