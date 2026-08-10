from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cost_plan.dependencies import dependency_snapshot
from app.cost_plan.invoice_candidates import (
    count_pending_invoice_ingests,
    discover_invoice_candidates,
)
from app.cost_plan.invoice_extraction import InvoiceExtractionError, extract_invoice
from app.cost_plan.invoice_mapping import map_invoice_allocations
from app.cost_plan.models import CostInvoiceMappingMemory
from app.cost_plan.invoice_service import book_invoice
from app.cost_plan.service import republish_cost_plan_for_ledger
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.schemas.project_snapshot import ProjectSnapshot
from app.workflows.create_cost_plan import sync_cost_plan_revision_artifacts


ProgressCallback = Callable[[str, int], Awaitable[None]]


class ProcessInvoicesResult(BaseModel):
    candidate_count: int = 0
    pending_ingest_count: int = 0
    booked_invoice_count: int = 0
    register_row_count: int = 0
    duplicate_count: int = 0
    conflict_count: int = 0
    review_count: int = 0
    extraction_error_count: int = 0
    conflicts: list[str] = Field(default_factory=list)
    review_items: list[str] = Field(default_factory=list)
    extraction_errors: list[str] = Field(default_factory=list)
    cost_plan_version: int
    workbook_path: str | None = None
    draft_id: uuid.UUID | None = None


async def process_invoices(
    session: AsyncSession,
    *,
    project: Project,
    user_id: uuid.UUID,
    workflow_run_id: uuid.UUID,
    expected_cost_plan_version: int,
    snapshot: ProjectSnapshot,
    source_document_ids: list[uuid.UUID] | None = None,
    progress: ProgressCallback | None = None,
) -> ProcessInvoicesResult:
    await _progress(progress, "discovering_invoices", 10)
    pending_ingest_count = await count_pending_invoice_ingests(
        session,
        project_id=project.id,
    )
    candidates = await discover_invoice_candidates(
        session,
        project_id=project.id,
        source_document_ids=source_document_ids,
    )

    booked = []
    duplicate_count = 0
    conflicts: list[str] = []
    review_items: list[str] = []
    extraction_errors: list[str] = []
    next_version = expected_cost_plan_version + 1
    mapping_plan = (
        await _cost_plan_for_mapping(
            session,
            project=project,
            user_id=user_id,
            version=expected_cost_plan_version,
        )
        if candidates
        else None
    )
    remembered_mappings: dict[tuple[str, str], tuple[str, str]] = {}
    if candidates:
        memories = (
            (
                await session.execute(
                    select(CostInvoiceMappingMemory).where(
                        CostInvoiceMappingMemory.project_id == project.id
                    )
                )
            )
            .scalars()
            .all()
        )
        remembered_mappings = {
            (memory.supplier_key, memory.description_key): (
                memory.cost_item_key,
                memory.cost_item_label,
            )
            for memory in memories
        }

    for index, candidate in enumerate(candidates, start=1):
        if mapping_plan is None:
            raise RuntimeError("invoice candidates require a current Cost Plan")
        percent = 15 + int((index / max(len(candidates), 1)) * 50)
        await _progress(progress, "extracting_and_mapping", percent)
        try:
            extracted = extract_invoice(candidate)
        except InvoiceExtractionError as exc:
            extraction_errors.append(str(exc))
            continue
        allocations = map_invoice_allocations(
            extracted,
            mapping_plan,
            remembered_mappings=remembered_mappings,
        )
        booking = await book_invoice(
            session,
            project_id=project.id,
            created_by_user_id=user_id,
            candidate=candidate,
            extracted=extracted,
            allocations=allocations,
            workflow_run_id=workflow_run_id,
            first_published_cost_plan_version=next_version,
        )
        if booking.status == "duplicate":
            duplicate_count += 1
            continue
        if booking.status == "conflict":
            conflicts.append(booking.message or candidate.relative_path)
            continue
        if booking.invoice is None:
            raise RuntimeError("booked invoice result has no invoice")
        booked.append(booking.invoice)
        review_items.extend(
            f"{extracted.invoice_number}: {allocation.description}"
            for allocation in allocations
            if allocation.review_status == "needs_review"
        )

    if not booked:
        await _progress(progress, "complete", 100)
        return ProcessInvoicesResult(
            candidate_count=len(candidates),
            pending_ingest_count=pending_ingest_count,
            duplicate_count=duplicate_count,
            conflict_count=len(conflicts),
            review_count=len(review_items),
            extraction_error_count=len(extraction_errors),
            conflicts=conflicts,
            review_items=review_items,
            extraction_errors=extraction_errors,
            cost_plan_version=expected_cost_plan_version,
        )

    await _progress(progress, "publishing_cost_plan", 75)
    state = await republish_cost_plan_for_ledger(
        session,
        project=project,
        author_user_id=user_id,
        expected_base_version=expected_cost_plan_version,
        dependency_snapshot=dependency_snapshot(
            snapshot,
            model_version=None,
            prompt_version="invoice-processing-v1",
            runtime_version="clerk-cost-plan-invoices-v1",
        ),
        external_idempotency_key=f"process-invoices:{workflow_run_id}",
    )
    if state.artefact_revision_id is None:
        raise RuntimeError("published Cost Plan has no artefact revision")
    draft = await session.get(DraftArtifact, state.artefact_revision_id)
    if draft is None:
        raise RuntimeError("published Cost Plan artefact revision was not found")
    workbook = await sync_cost_plan_revision_artifacts(
        session,
        project=project,
        draft=draft,
        typed_state=state,
        provenance_updates={
            "invoice_processing": {
                "workflow_run_id": str(workflow_run_id),
                "booked_invoice_ids": [str(invoice.id) for invoice in booked],
                "changed_allocation_ids": [
                    str(allocation.id)
                    for invoice in booked
                    for allocation in invoice.allocations
                ],
            }
        },
    )
    await _progress(progress, "verifying_workbook", 95)
    register_row_count = sum(len(invoice.allocations) for invoice in booked)
    await _progress(progress, "complete", 100)
    return ProcessInvoicesResult(
        candidate_count=len(candidates),
        pending_ingest_count=pending_ingest_count,
        booked_invoice_count=len(booked),
        register_row_count=register_row_count,
        duplicate_count=duplicate_count,
        conflict_count=len(conflicts),
        review_count=len(review_items),
        extraction_error_count=len(extraction_errors),
        conflicts=conflicts,
        review_items=review_items,
        extraction_errors=extraction_errors,
        cost_plan_version=state.version,
        workbook_path=str(workbook["workspace_path"]),
        draft_id=draft.id,
    )


async def _cost_plan_for_mapping(
    session: AsyncSession,
    *,
    project: Project,
    user_id: uuid.UUID,
    version: int,
):
    from app.cost_plan.service import complete_cost_plan_state, get_cost_plan

    state = await get_cost_plan(
        session,
        project_id=project.id,
        owner_user_id=user_id,
        version=version,
    )
    return await complete_cost_plan_state(
        session,
        project=project,
        state=state,
    )


async def _progress(
    callback: ProgressCallback | None,
    stage: str,
    percent: int,
) -> None:
    if callback is not None:
        await callback(stage, percent)
