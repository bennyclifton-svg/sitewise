from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.billing.entitlements import require_active_entitlement
from app.cost_plan.invoice_service import (
    InvoiceNotFound,
    InvoiceRevisionConflict,
    invoice_ledger_response,
    update_invoice_allocation,
    update_invoice_fields,
)
from app.cost_plan.schemas import (
    CostPlanState,
    InvoiceAllocationUpdate,
    InvoiceFieldsUpdate,
    InvoiceLedgerResponse,
)
from app.cost_plan.service import (
    CostPlanNotFound,
    complete_cost_plan_state,
    get_cost_plan,
)
from app.cost_plan.workbook_rebuild import schedule_cost_plan_workbook_rebuild
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.database.projects import get_project
from app.database.session import get_db
from app.workflows.create_cost_plan import workbook_workspace_path


router = APIRouter(prefix="/projects", tags=["cost-invoices"])


async def _project_and_state(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[Project, CostPlanState]:
    project = await get_project(session, project_id)
    if project is None or project.owner_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    try:
        state = await get_cost_plan(
            session,
            project_id=project.id,
            owner_user_id=user_id,
        )
    except CostPlanNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Create a Cost Plan before editing invoices",
        ) from exc
    state = await complete_cost_plan_state(session, project=project, state=state)
    return project, state


async def _publish_edit(
    session: AsyncSession,
    *,
    project: Project,
    state: CostPlanState,
    edit_kind: str,
    invoice_id: uuid.UUID,
    allocation_id: uuid.UUID | None = None,
    details: dict[str, object] | None = None,
) -> InvoiceLedgerResponse:
    """Commit the ledger mutation without republishing the Cost Plan.

    A dropdown change is already canonical on cost_invoices. Republishing a
    new Cost Plan revision in the same transaction made the save take tens of
    seconds and rolled the mapping back if the user left the page.
    """
    edit_id = uuid.uuid4()
    if state.artefact_revision_id is not None:
        draft = await session.get(DraftArtifact, state.artefact_revision_id)
        if draft is not None:
            draft.provenance_metadata = {
                **(draft.provenance_metadata or {}),
                "invoice_operator_edit": {
                    "edit_id": str(edit_id),
                    "kind": edit_kind,
                    "invoice_id": str(invoice_id),
                    "allocation_id": str(allocation_id) if allocation_id else None,
                    "details": details or {},
                },
                "workbook": {"status": "pending", "version": state.version},
            }
    await session.flush()
    await session.commit()
    schedule_cost_plan_workbook_rebuild(project.id, state.version)
    return await invoice_ledger_response(
        session,
        project_id=project.id,
        state=state,
        workbook_path=workbook_workspace_path(project, state.version),
    )


@router.get("/{project_id}/invoices", response_model=InvoiceLedgerResponse)
async def get_invoice_ledger(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvoiceLedgerResponse:
    project, state = await _project_and_state(
        session, project_id=project_id, user_id=user.id
    )
    return await invoice_ledger_response(
        session,
        project_id=project.id,
        state=state,
        workbook_path=workbook_workspace_path(project, state.version),
    )


@router.patch("/{project_id}/invoices/{invoice_id}", response_model=InvoiceLedgerResponse)
async def patch_invoice(
    project_id: uuid.UUID,
    invoice_id: uuid.UUID,
    body: InvoiceFieldsUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvoiceLedgerResponse:
    project, state = await _project_and_state(
        session, project_id=project_id, user_id=user.id
    )
    await require_active_entitlement(session, user)
    if state.version != body.expected_cost_plan_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Expected Cost Plan v{body.expected_cost_plan_version}, "
                f"current version is v{state.version}"
            ),
        )
    try:
        invoice = await update_invoice_fields(
            session,
            project_id=project.id,
            invoice_id=invoice_id,
            expected_revision=body.expected_revision,
            paid=body.paid,
            billing_month=body.billing_month,
        )
    except InvoiceNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        ) from exc
    except InvoiceRevisionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return await _publish_edit(
        session,
        project=project,
        state=state,
        edit_kind="invoice_fields",
        invoice_id=invoice.id,
        details={
            "paid": body.paid,
            "billing_month": (
                body.billing_month.isoformat() if body.billing_month else None
            ),
        },
    )


@router.patch(
    "/{project_id}/invoice-allocations/{allocation_id}",
    response_model=InvoiceLedgerResponse,
)
async def patch_invoice_allocation(
    project_id: uuid.UUID,
    allocation_id: uuid.UUID,
    body: InvoiceAllocationUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvoiceLedgerResponse:
    project, state = await _project_and_state(
        session, project_id=project_id, user_id=user.id
    )
    await require_active_entitlement(session, user)
    if state.version != body.expected_cost_plan_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Expected Cost Plan v{body.expected_cost_plan_version}, "
                f"current version is v{state.version}"
            ),
        )
    target = next(
        (item for item in state.items if item.item_key == body.cost_item_key),
        None,
    )
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selected cost item does not exist in the current Cost Plan",
        )
    try:
        invoice = await update_invoice_allocation(
            session,
            project_id=project.id,
            user_id=user.id,
            allocation_id=allocation_id,
            expected_revision=body.expected_revision,
            cost_item_key=target.item_key,
            cost_item_label=target.item,
        )
    except InvoiceNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice allocation not found",
        ) from exc
    except InvoiceRevisionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return await _publish_edit(
        session,
        project=project,
        state=state,
        edit_kind="allocation_mapping",
        invoice_id=invoice.id,
        allocation_id=allocation_id,
        details={
            "cost_item_key": target.item_key,
            "cost_item_label": target.item,
        },
    )
