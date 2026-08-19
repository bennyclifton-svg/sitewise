from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cost_plan.invoice_candidates import InvoiceCandidate
from app.cost_plan.invoice_extraction import extract_invoice_secondary
from app.cost_plan.invoice_issues import (
    InvoiceIssue,
    allocation_issues,
    arithmetic_issues,
    field_reconciliation,
    has_error_issues,
    should_run_secondary,
)
from app.cost_plan.invoice_mapping import normalize_description_key
from app.cost_plan.invoice_snapshot import (
    apply_reviewed_overlay,
    machine_snapshot_payload,
    set_machine_extraction,
)
from app.cost_plan.models import (
    CostInvoice,
    CostInvoiceAllocation,
    CostInvoiceMappingMemory,
)
from app.cost_plan.normalization import normalize_business_key
from app.cost_plan.schemas import (
    CostPlanState,
    ExtractedInvoice,
    InvoiceAllocationInput,
    InvoiceCostItemOption,
    InvoiceLedgerResponse,
    InvoiceLedgerRow,
    InvoiceRegisterRow,
    InvoiceReviewAllocation,
    InvoiceReviewFieldValues,
    InvoiceReviewResponse,
)
from app.projects.event_spine import PROJECT_VERBS, record_project_verb, verb_dedup_key


BookingStatus = Literal["booked", "duplicate", "conflict"]
InvoiceDecision = Literal["hold", "reject", "approve"]

REVIEW_TRANSITIONS: dict[str, frozenset[str]] = {
    "received": frozenset(
        {
            "extracting",
            "ready_for_review",
            "needs_attention",
            "duplicate",
            "conflict",
            "rejected",
        }
    ),
    "extracting": frozenset({"ready_for_review", "needs_attention", "rejected"}),
    "ready_for_review": frozenset({"needs_attention", "approved", "rejected"}),
    "needs_attention": frozenset({"ready_for_review", "approved", "rejected"}),
    "approved": frozenset({"posted"}),
    "rejected": frozenset(),
    "posted": frozenset(),
    "duplicate": frozenset(),
    "conflict": frozenset({"needs_attention", "rejected"}),
}

_DECISION_TARGET: dict[InvoiceDecision, str] = {
    "hold": "needs_attention",
    "reject": "rejected",
    "approve": "approved",
}


class InvoiceNotFound(LookupError):
    pass


class InvoiceRevisionConflict(RuntimeError):
    pass


class InvoiceIllegalTransition(RuntimeError):
    pass


class InvoiceDecisionBlocked(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class InvoiceBookingResult:
    status: BookingStatus
    invoice: CostInvoice | None
    message: str | None = None


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
    issues = [
        *arithmetic_issues(extracted),
        *allocation_issues(extracted, allocations),
    ]
    snapshot = machine_snapshot_payload(extracted)
    if should_run_secondary(issues, snapshot):
        snapshot["secondary"] = extract_invoice_secondary(candidate)

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
            existing.issues = [
                InvoiceIssue(
                    code="DUPLICATE_INVOICE",
                    severity="info",
                    field=None,
                    message="Invoice is already booked with the same financial facts",
                ).model_dump()
            ]
            existing.review_state = "duplicate"
            await _record_invoice_event(
                session,
                project_id=project_id,
                invoice_id=existing.id,
                source="invoice.duplicate",
                message="Duplicate invoice skipped",
            )
            return InvoiceBookingResult(status="duplicate", invoice=existing)
        existing.issues = [
            InvoiceIssue(
                code="CONFLICTING_DUPLICATE",
                severity="error",
                field=None,
                message=(
                    f"{extracted.supplier_name} invoice {extracted.invoice_number} "
                    "is already booked with different financial facts"
                ),
            ).model_dump()
        ]
        existing.review_state = "conflict"
        await _record_invoice_event(
            session,
            project_id=project_id,
            invoice_id=existing.id,
            source="invoice.conflict",
            message="Conflicting duplicate invoice",
        )
        return InvoiceBookingResult(
            status="conflict",
            invoice=existing,
            message=(
                f"{extracted.supplier_name} invoice {extracted.invoice_number} "
                "is already booked with different financial facts"
            ),
        )

    dirty = has_error_issues(issues)
    mapping_review = any(
        allocation.review_status == "needs_review" for allocation in allocations
    )
    bookable = not dirty
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
        subtotal_ex_gst=extracted.subtotal_ex_gst if bookable else None,
        gst=extracted.gst if bookable else None,
        total_including_gst=extracted.total_including_gst if bookable else None,
        currency=extracted.currency,
        paid=False,
        processing_status="needs_review" if dirty or mapping_review else "booked",
        review_state="needs_attention" if dirty else "ready_for_review",
        extraction_provenance=extracted.provenance,
        machine_extraction={},
        reviewed_extraction={},
        issues=[issue.model_dump() for issue in issues],
        processed_by_workflow_run_id=workflow_run_id,
        created_by_user_id=created_by_user_id,
        first_published_cost_plan_version=first_published_cost_plan_version,
    )
    set_machine_extraction(invoice, snapshot)
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
    await _record_invoice_event(
        session,
        project_id=project_id,
        invoice_id=invoice.id,
        source="invoice.received",
        message="Invoice extracted",
    )
    if invoice.review_state == "needs_attention":
        await _record_invoice_event(
            session,
            project_id=project_id,
            invoice_id=invoice.id,
            source="invoice.needs_review",
            message="Invoice needs attention",
        )
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
    invoice_number: str | None = None,
    supplier_name: str | None = None,
    actor_id: uuid.UUID | None = None,
) -> CostInvoice:
    invoice = await _load_project_invoice(
        session, project_id=project_id, invoice_id=invoice_id
    )
    if invoice.revision != expected_revision:
        raise InvoiceRevisionConflict(
            f"Expected invoice revision {expected_revision}, current revision is {invoice.revision}"
        )
    if paid is not None:
        invoice.paid = paid
    if billing_month is not None:
        invoice.billing_month = billing_month
    overlay = {
        key: value
        for key, value in {
            "invoice_number": invoice_number,
            "supplier_name": supplier_name,
        }.items()
        if value is not None
    }
    if overlay:
        apply_reviewed_overlay(
            invoice,
            overlay,
            actor_id=actor_id,
            reviewed_at=datetime.now(UTC),
        )
    invoice.revision += 1
    await session.flush()
    return invoice


async def update_invoice_allocation(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
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
    if allocation.mapping_method == "manual":
        statement = insert(CostInvoiceMappingMemory).values(
            project_id=invoice.project_id,
            supplier_key=invoice.supplier_key,
            description_key=normalize_description_key(allocation.description),
            cost_item_key=cost_item_key,
            cost_item_label=cost_item_label,
            updated_by_user_id=user_id,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[
                CostInvoiceMappingMemory.project_id,
                CostInvoiceMappingMemory.supplier_key,
                CostInvoiceMappingMemory.description_key,
            ],
            set_={
                "cost_item_key": cost_item_key,
                "cost_item_label": cost_item_label,
                "updated_by_user_id": user_id,
                "updated_at": func.now(),
            },
        )
        await session.execute(statement)
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


def transition_review_state(invoice: CostInvoice, target: str) -> None:
    allowed = REVIEW_TRANSITIONS.get(invoice.review_state, frozenset())
    if target not in allowed:
        raise InvoiceIllegalTransition(
            f"Cannot move invoice from {invoice.review_state} to {target}"
        )
    invoice.review_state = target


async def decide_invoice(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    invoice_id: uuid.UUID,
    actor_id: uuid.UUID,
    decision: InvoiceDecision,
    reason: str | None,
) -> CostInvoice:
    invoice = await _load_project_invoice(
        session, project_id=project_id, invoice_id=invoice_id
    )
    target = _DECISION_TARGET[decision]
    if decision == "approve" and has_error_issues(invoice.issues or []):
        raise InvoiceDecisionBlocked("Open error issues block approval")
    transition_review_state(invoice, target)
    if decision == "approve":
        transition_review_state(invoice, "posted")
        invoice.processing_status = "booked"
        source = "invoice.approved"
        posted_source = "invoice.posted"
    elif decision == "reject":
        invoice.processing_status = "void"
        source = "invoice.rejected"
        posted_source = None
    else:
        invoice.processing_status = "needs_review"
        source = "invoice.needs_review"
        posted_source = None
    invoice.reviewed_by_user_id = actor_id
    invoice.reviewed_at = datetime.now(UTC)
    invoice.revision += 1
    await session.flush()
    await _record_invoice_event(
        session,
        project_id=project_id,
        invoice_id=invoice.id,
        source=source,
        message=reason or f"Invoice {decision}",
    )
    if posted_source is not None:
        await _record_invoice_event(
            session,
            project_id=project_id,
            invoice_id=invoice.id,
            source=posted_source,
            message="Invoice posted in SiteWise",
        )
    return invoice


async def invoice_review_payload(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> InvoiceReviewResponse:
    invoice = await _load_project_invoice(
        session, project_id=project_id, invoice_id=invoice_id
    )
    machine = invoice.machine_extraction or {}
    secondary = machine.get("secondary") if isinstance(machine.get("secondary"), dict) else {}
    reviewed = invoice.reviewed_extraction or {}
    return InvoiceReviewResponse(
        invoice_id=invoice.id,
        invoice_number=invoice.invoice_number,
        original_excerpt="",
        machine=_review_fields(machine),
        secondary=_review_fields(secondary if isinstance(secondary, dict) else {}),
        reviewed=_review_fields(reviewed),
        reconciliation=field_reconciliation(invoice),
        issues=list(invoice.issues or []),
        allocations=[
            InvoiceReviewAllocation(
                description=allocation.description,
                amount_ex_gst=str(allocation.amount_ex_gst),
                cost_item_label=allocation.cost_item_label,
                mapping_method=allocation.mapping_method,
            )
            for allocation in invoice.allocations
        ],
        review_state=invoice.review_state,
        processing_status=invoice.processing_status,
        revision=invoice.revision,
    )


def _review_fields(payload: dict) -> InvoiceReviewFieldValues:
    return InvoiceReviewFieldValues(
        invoice_number=_optional_str(payload.get("invoice_number")),
        supplier_name=_optional_str(payload.get("supplier_name")),
        supplier_abn=_optional_str(payload.get("supplier_abn")),
        invoice_date=_optional_str(payload.get("invoice_date")),
        subtotal_ex_gst=_optional_str(payload.get("subtotal_ex_gst")),
        gst=_optional_str(payload.get("gst")),
        total_including_gst=_optional_str(payload.get("total_including_gst")),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


async def _load_project_invoice(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    invoice_id: uuid.UUID,
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
    return invoice


async def _record_invoice_event(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    invoice_id: uuid.UUID,
    source: str,
    message: str,
) -> None:
    if source not in PROJECT_VERBS:
        raise ValueError(f"unknown project verb: {source}")
    invoice = await session.get(CostInvoice, invoice_id)
    invoice_number = invoice.invoice_number if invoice is not None else None
    await record_project_verb(
        session,
        project_id=project_id,
        verb=source,  # type: ignore[arg-type]
        reference_type="cost_invoice",
        reference_id=invoice_id,
        message=message,
        deduplication_key=verb_dedup_key(
            source,
            reference_type="cost_invoice",
            reference_id=invoice_id,
        ),
        metadata={"invoice_number": invoice_number} if invoice_number else None,
    )
