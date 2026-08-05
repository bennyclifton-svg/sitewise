from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cost_plan.invoice_candidates import InvoiceCandidate
from app.cost_plan.models import CostInvoice, CostInvoiceAllocation
from app.cost_plan.schemas import (
    CostPlanState,
    ExtractedInvoice,
    InvoiceAllocationInput,
    InvoiceCostItemOption,
    InvoiceLedgerResponse,
    InvoiceLedgerRow,
    InvoiceRegisterRow,
)


BookingStatus = Literal["booked", "duplicate", "conflict"]


class InvoiceNotFound(LookupError):
    pass


class InvoiceRevisionConflict(RuntimeError):
    pass


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


async def invoice_ledger_response(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    state: CostPlanState,
    workbook_path: str,
) -> InvoiceLedgerResponse:
    invoices = (
        await session.execute(
            select(CostInvoice)
            .where(
                CostInvoice.project_id == project_id,
                CostInvoice.processing_status != "void",
            )
            .options(selectinload(CostInvoice.allocations))
            .order_by(
                CostInvoice.invoice_date,
                CostInvoice.supplier_key,
                CostInvoice.invoice_key,
            )
        )
    ).scalars().all()
    return InvoiceLedgerResponse(
        cost_plan_version=state.version,
        workbook_path=workbook_path,
        rows=[
            InvoiceLedgerRow(
                allocation_id=allocation.id,
                invoice_id=invoice.id,
                invoice_revision=invoice.revision,
                invoice_date=invoice.invoice_date,
                company=invoice.supplier_name,
                po_number=invoice.po_number,
                invoice_number=invoice.invoice_number,
                description=allocation.description,
                cost_item_key=allocation.cost_item_key,
                cost_item_label=allocation.cost_item_label,
                amount_ex_gst=allocation.amount_ex_gst,
                billing_month=invoice.billing_month,
                paid=invoice.paid,
                review_status=allocation.review_status,
                mapping_method=allocation.mapping_method,
            )
            for invoice in invoices
            for allocation in invoice.allocations
        ],
        cost_items=[
            InvoiceCostItemOption(
                item_key=item.item_key,
                cost_code=item.cost_code,
                category=item.category,
                item=item.item,
                budget=item.budget,
            )
            for item in state.items
        ],
    )


async def update_invoice_fields(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    invoice_id: uuid.UUID,
    expected_revision: int,
    paid: bool | None,
    billing_month: date | None,
) -> CostInvoice:
    invoice = (
        await session.execute(
            select(CostInvoice)
            .where(
                CostInvoice.id == invoice_id,
                CostInvoice.project_id == project_id,
            )
            .options(selectinload(CostInvoice.allocations))
            .with_for_update()
        )
    ).scalar_one_or_none()
    if invoice is None:
        raise InvoiceNotFound(str(invoice_id))
    if invoice.revision != expected_revision:
        raise InvoiceRevisionConflict(
            f"Expected invoice revision {expected_revision}, current revision is {invoice.revision}"
        )
    if paid is not None:
        invoice.paid = paid
    if billing_month is not None:
        invoice.billing_month = billing_month
    invoice.revision += 1
    await session.flush()
    return invoice


async def update_invoice_allocation(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    allocation_id: uuid.UUID,
    expected_revision: int,
    cost_item_key: str,
    cost_item_label: str,
) -> CostInvoice:
    invoice = (
        await session.execute(
            select(CostInvoice)
            .join(CostInvoiceAllocation)
            .where(
                CostInvoice.project_id == project_id,
                CostInvoiceAllocation.id == allocation_id,
            )
            .options(selectinload(CostInvoice.allocations))
            .with_for_update()
        )
    ).scalar_one_or_none()
    if invoice is None:
        raise InvoiceNotFound(str(allocation_id))
    if invoice.revision != expected_revision:
        raise InvoiceRevisionConflict(
            f"Expected invoice revision {expected_revision}, current revision is {invoice.revision}"
        )
    allocation = next(
        item for item in invoice.allocations if item.id == allocation_id
    )
    allocation.cost_item_key = cost_item_key
    allocation.cost_item_label = cost_item_label
    allocation.mapping_method = "manual"
    allocation.mapping_confidence = None
    allocation.review_status = "mapped"
    invoice.processing_status = (
        "needs_review"
        if any(item.review_status == "needs_review" for item in invoice.allocations)
        else "booked"
    )
    invoice.revision += 1
    await session.flush()
    return invoice


def _same_financial_facts(existing: CostInvoice, extracted: ExtractedInvoice) -> bool:
    return (
        existing.supplier_key == normalize_business_key(extracted.supplier_name)
        and existing.invoice_key == normalize_business_key(extracted.invoice_number)
        and existing.invoice_date == extracted.invoice_date
        and existing.subtotal_ex_gst == extracted.subtotal_ex_gst
        and existing.gst == extracted.gst
        and existing.total_including_gst == extracted.total_including_gst
    )
