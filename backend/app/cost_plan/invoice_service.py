from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cost_plan.invoice_candidates import InvoiceCandidate
from app.cost_plan.models import CostInvoice, CostInvoiceAllocation
from app.cost_plan.schemas import (
    ExtractedInvoice,
    InvoiceAllocationInput,
    InvoiceRegisterRow,
)


BookingStatus = Literal["booked", "duplicate", "conflict"]


@dataclass(frozen=True, slots=True)
class InvoiceBookingResult:
    status: BookingStatus
    invoice: CostInvoice | None
    message: str | None = None


def normalize_business_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


async def book_invoice(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    candidate: InvoiceCandidate,
    extracted: ExtractedInvoice,
    allocations: list[InvoiceAllocationInput],
    workflow_run_id: uuid.UUID | None = None,
    first_published_cost_plan_version: int | None = None,
) -> InvoiceBookingResult:
    allocation_total = sum(
        (allocation.amount_ex_gst for allocation in allocations), Decimal("0")
    ).quantize(Decimal("0.01"))
    subtotal = extracted.subtotal_ex_gst.quantize(Decimal("0.01"))
    if allocation_total != subtotal:
        raise ValueError(
            f"invoice allocation total {allocation_total} does not equal subtotal {subtotal}"
        )

    supplier_key = normalize_business_key(extracted.supplier_name)
    invoice_key = normalize_business_key(extracted.invoice_number)
    existing = (
        await session.execute(
            select(CostInvoice)
            .where(
                CostInvoice.project_id == project_id,
                or_(
                    CostInvoice.source_content_hash == candidate.content_hash,
                    (
                        (CostInvoice.supplier_key == supplier_key)
                        & (CostInvoice.invoice_key == invoice_key)
                    ),
                ),
            )
            .options(selectinload(CostInvoice.allocations))
        )
    ).scalars().first()
    if existing is not None:
        if _same_financial_facts(existing, extracted):
            return InvoiceBookingResult(status="duplicate", invoice=existing)
        return InvoiceBookingResult(
            status="conflict",
            invoice=existing,
            message=(
                f"{extracted.supplier_name} invoice {extracted.invoice_number} "
                "is already booked with different financial facts"
            ),
        )

    needs_review = any(
        allocation.review_status == "needs_review" for allocation in allocations
    )
    invoice = CostInvoice(
        project_id=project_id,
        workspace_file_id=candidate.workspace_file_id,
        source_document_id=candidate.source_document_id,
        source_content_hash=candidate.content_hash,
        source_locator=candidate.relative_path,
        supplier_name=extracted.supplier_name,
        supplier_key=supplier_key,
        supplier_abn=extracted.supplier_abn,
        invoice_number=extracted.invoice_number,
        invoice_key=invoice_key,
        invoice_date=extracted.invoice_date,
        due_date=extracted.due_date,
        billing_month=extracted.billing_month,
        po_number=extracted.po_number,
        related_reference=extracted.related_reference,
        subtotal_ex_gst=extracted.subtotal_ex_gst,
        gst=extracted.gst,
        total_including_gst=extracted.total_including_gst,
        currency=extracted.currency,
        paid=False,
        processing_status="needs_review" if needs_review else "booked",
        extraction_provenance=extracted.provenance,
        processed_by_workflow_run_id=workflow_run_id,
        created_by_user_id=created_by_user_id,
        first_published_cost_plan_version=first_published_cost_plan_version,
    )
    invoice.allocations = [
        CostInvoiceAllocation(
            project_id=project_id,
            line_number=allocation.line_number,
            description=allocation.description,
            amount_ex_gst=allocation.amount_ex_gst,
            gst_treatment=allocation.gst_treatment,
            cost_item_key=allocation.cost_item_key,
            cost_item_label=allocation.cost_item_label,
            mapping_method=allocation.mapping_method,
            mapping_confidence=allocation.mapping_confidence,
            review_status=allocation.review_status,
            source_locators=allocation.source_locators,
        )
        for allocation in allocations
    ]
    session.add(invoice)
    await session.flush()
    return InvoiceBookingResult(status="booked", invoice=invoice)


async def list_invoice_register_rows(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    through_cost_plan_version: int | None = None,
) -> list[InvoiceRegisterRow]:
    statement = (
        select(CostInvoice)
        .where(
            CostInvoice.project_id == project_id,
            CostInvoice.processing_status != "void",
        )
        .options(selectinload(CostInvoice.allocations))
        .order_by(CostInvoice.invoice_date, CostInvoice.supplier_key, CostInvoice.invoice_key)
    )
    if through_cost_plan_version is not None:
        statement = statement.where(
            CostInvoice.first_published_cost_plan_version.is_not(None),
            CostInvoice.first_published_cost_plan_version <= through_cost_plan_version,
        )
    invoices = (await session.execute(statement)).scalars().all()
    return [
        InvoiceRegisterRow(
            allocation_id=allocation.id,
            invoice_date=invoice.invoice_date,
            company=invoice.supplier_name,
            po_number=invoice.po_number,
            invoice_number=invoice.invoice_number,
            description=allocation.description,
            cost_item=allocation.cost_item_label,
            amount_ex_gst=allocation.amount_ex_gst,
            billing_month=invoice.billing_month,
            paid=invoice.paid,
        )
        for invoice in invoices
        for allocation in invoice.allocations
    ]


def _same_financial_facts(existing: CostInvoice, extracted: ExtractedInvoice) -> bool:
    return (
        existing.supplier_key == normalize_business_key(extracted.supplier_name)
        and existing.invoice_key == normalize_business_key(extracted.invoice_number)
        and existing.invoice_date == extracted.invoice_date
        and existing.subtotal_ex_gst == extracted.subtotal_ex_gst
        and existing.gst == extracted.gst
        and existing.total_including_gst == extracted.total_including_gst
    )
