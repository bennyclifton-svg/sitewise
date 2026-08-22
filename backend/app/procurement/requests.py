from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.draft_artifact import DraftArtifact
from app.database.procurement_request import ProcurementRequest
from app.procurement.strategy import (
    advance_strategy_status,
    link_request_to_strategy_row,
)

ProcurementRequestKind = Literal[
    "consultant_rfp", "contractor_eoi", "trade_rft", "trade_rfq"
]
ProcurementRequestStatus = Literal["draft", "issued", "closed", "cancelled"]

REQUEST_KINDS = frozenset(
    {"consultant_rfp", "contractor_eoi", "trade_rft", "trade_rfq"}
)
REQUEST_STATUSES = frozenset({"draft", "issued", "closed", "cancelled"})
_WORKFLOW_PREFIXES = {
    "consultant_rfp": "consultant_procurement_",
    "contractor_eoi": "contractor_eoi_",
    "trade_rft": "trade_rft_",
    "trade_rfq": "trade_rfq_",
}
_STATUS_TRANSITIONS = {
    "draft": frozenset({"issued", "cancelled"}),
    "issued": frozenset({"closed", "cancelled"}),
    "closed": frozenset(),
    "cancelled": frozenset(),
}


class ProcurementRequestNotFound(LookupError):
    pass


class ProcurementRequestRevisionConflict(RuntimeError):
    pass


class ProcurementRequestStateConflict(RuntimeError):
    pass


class ProcurementRequestDraftConflict(RuntimeError):
    pass


def normalise_target_name(value: str) -> tuple[str, str]:
    name = " ".join(value.strip().split())
    if not name:
        raise ValueError("target_name is required")
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return name, slug or "procurement_request"


def request_kind_for_workflow(
    workflow_type: str, *, trade_kind: str | None = None
) -> str:
    if workflow_type.startswith("consultant_procurement_"):
        return "consultant_rfp"
    if workflow_type.startswith("contractor_eoi_"):
        return "contractor_eoi"
    if workflow_type.startswith("trade_rft_") or trade_kind == "rft":
        return "trade_rft"
    if workflow_type.startswith("trade_rfq_") or trade_kind == "rfq":
        return "trade_rfq"
    raise ValueError(f"Unsupported procurement workflow: {workflow_type}")


async def create_procurement_request(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    kind: ProcurementRequestKind,
    target_name: str,
    discipline_code: str | None = None,
    strategy_row_id: uuid.UUID | None = None,
) -> ProcurementRequest:
    if kind not in REQUEST_KINDS:
        raise ValueError("invalid procurement request kind")
    name, slug = normalise_target_name(target_name)
    request = ProcurementRequest(
        project_id=project_id,
        created_by_user_id=created_by_user_id,
        kind=kind,
        target_name=name,
        target_slug=slug,
        status="draft",
        revision=1,
    )
    session.add(request)
    if discipline_code is not None or strategy_row_id is not None:
        await link_request_to_strategy_row(
            session,
            request=request,
            discipline_code=discipline_code,
            strategy_row_id=strategy_row_id,
        )
    await session.flush()
    await session.refresh(request)
    return request


async def get_procurement_request(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    request_id: uuid.UUID,
) -> ProcurementRequest:
    result = await session.execute(
        select(ProcurementRequest).where(
            ProcurementRequest.id == request_id,
            ProcurementRequest.project_id == project_id,
        )
    )
    request = result.scalar_one_or_none()
    if request is None:
        raise ProcurementRequestNotFound(str(request_id))
    return request


async def list_procurement_requests(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> list[ProcurementRequest]:
    result = await session.execute(
        select(ProcurementRequest)
        .where(ProcurementRequest.project_id == project_id)
        .order_by(
            ProcurementRequest.updated_at.desc(), ProcurementRequest.created_at.desc()
        )
    )
    return list(result.scalars())


async def transition_procurement_request(
    session: AsyncSession,
    *,
    request: ProcurementRequest,
    status: ProcurementRequestStatus,
    expected_revision: int,
) -> ProcurementRequest:
    if expected_revision != request.revision:
        raise ProcurementRequestRevisionConflict(
            f"Expected request revision {expected_revision}, current revision is {request.revision}"
        )
    if status not in REQUEST_STATUSES:
        raise ValueError("invalid procurement request status")
    if status == request.status:
        return request
    if status not in _STATUS_TRANSITIONS[request.status]:
        raise ProcurementRequestStateConflict(
            f"Cannot transition procurement request from {request.status} to {status}"
        )
    request.status = status
    if status == "issued":
        request.issued_at = datetime.now(UTC)
    elif status == "closed":
        request.closed_at = datetime.now(UTC)
    request.revision += 1
    if status == "issued":
        await advance_strategy_status(session, request=request, status="issued")
    elif status == "cancelled":
        await advance_strategy_status(session, request=request, status="cancelled")
    await session.flush()
    await session.refresh(request)
    return request


async def attach_current_draft(
    session: AsyncSession,
    *,
    request: ProcurementRequest,
    draft: DraftArtifact,
) -> ProcurementRequest:
    if request.project_id != draft.project_id:
        raise ProcurementRequestDraftConflict(
            "draft artefact does not belong to this procurement request project"
        )
    prefix = _WORKFLOW_PREFIXES[request.kind]
    if not draft.workflow_type.startswith(prefix):
        raise ProcurementRequestDraftConflict(
            "draft workflow type does not match procurement request kind"
        )
    request.current_draft_artifact_id = draft.id
    request.revision += 1
    await advance_strategy_status(
        session, request=request, status="request_drafted"
    )
    await session.flush()
    await session.refresh(request)
    return request


async def attach_generated_draft(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    draft: DraftArtifact,
    target_name: str,
    kind: ProcurementRequestKind,
    request_id: uuid.UUID | None = None,
    discipline_code: str | None = None,
    strategy_row_id: uuid.UUID | None = None,
) -> ProcurementRequest:
    """Attach a workflow result, reusing an open matching draft request when possible."""
    if request_id is not None:
        request = await get_procurement_request(
            session, project_id=project_id, request_id=request_id
        )
        if request.kind != kind:
            raise ProcurementRequestDraftConflict(
                "request kind does not match workflow"
            )
    else:
        _name, slug = normalise_target_name(target_name)
        result = await session.execute(
            select(ProcurementRequest)
            .where(
                ProcurementRequest.project_id == project_id,
                ProcurementRequest.kind == kind,
                ProcurementRequest.target_slug == slug,
                ProcurementRequest.status == "draft",
            )
            .order_by(ProcurementRequest.updated_at.desc())
            .limit(1)
        )
        request = result.scalar_one_or_none()
        if request is None:
            request = await create_procurement_request(
                session,
                project_id=project_id,
                created_by_user_id=created_by_user_id,
                kind=kind,
                target_name=target_name,
                discipline_code=discipline_code,
                strategy_row_id=strategy_row_id,
            )
    if request.strategy_row_id is None:
        await link_request_to_strategy_row(
            session,
            request=request,
            discipline_code=discipline_code,
            strategy_row_id=strategy_row_id,
        )
    return await attach_current_draft(session, request=request, draft=draft)
