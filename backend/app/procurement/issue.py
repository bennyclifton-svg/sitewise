"""Draft and send the cover email that issues a procurement request (D7)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.draft_artifact import DraftArtifact
from app.database.procurement_request import ProcurementRequest
from app.email.models import ProjectEmailDraft
from app.email.providers.base import EmailProvider
from app.email.service import (
    EmailDraftConflict,
    EmailNotFound,
    create_email_draft,
    send_email_draft,
)
from app.procurement.requests import (
    ProcurementRequestDraftConflict,
    ProcurementRequestRevisionConflict,
    ProcurementRequestStateConflict,
    get_procurement_request,
    transition_procurement_request,
)
from app.procurement.submissions import list_request_submissions

_KIND_LABELS = {
    "consultant_rfp": "Request for Proposal",
    "contractor_eoi": "Expression of Interest",
    "trade_rft": "Request for Tender",
    "trade_rfq": "Request for Quotation",
}


async def draft_procurement_issue_email(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    request_id: uuid.UUID,
    actor_id: uuid.UUID,
    to_addresses: Sequence[str],
    body_text: str | None = None,
    provider: EmailProvider | None = None,
) -> ProjectEmailDraft:
    """Create a cover-email draft. Does not transition the request."""
    request = await get_procurement_request(
        session, project_id=project_id, request_id=request_id
    )
    if request.status != "draft":
        raise ProcurementRequestStateConflict(
            f"Cannot draft issue email from {request.status}"
        )
    artefact = await _require_artefact(session, request)
    label = _KIND_LABELS[request.kind]
    subject = f"{label}: {request.target_name}"
    body = body_text or (
        f"Please find the {label} for {request.target_name}.\n\n"
        f"{artefact.workspace_path}\n"
    )
    draft = await create_email_draft(
        session,
        project_id=project_id,
        created_by_user_id=actor_id,
        to_addresses=to_addresses,
        subject=subject,
        body_text=body,
        provider=provider,
        references={
            "kind": "procurement_issue",
            "procurement_request_id": str(request.id),
            "draft_artifact_id": str(artefact.id),
            "workspace_path": artefact.workspace_path,
        },
    )
    request.issue_email_draft_id = draft.id
    return draft


async def _require_artefact(
    session: AsyncSession, request: ProcurementRequest
) -> DraftArtifact:
    if request.current_draft_artifact_id is None:
        raise ProcurementRequestDraftConflict(
            "procurement request has no generated artefact"
        )
    artefact = await session.get(DraftArtifact, request.current_draft_artifact_id)
    if artefact is None:
        raise ProcurementRequestDraftConflict(
            "procurement request has no generated artefact"
        )
    return artefact


async def draft_chase_missing_bidders(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    request_id: uuid.UUID,
    actor_id: uuid.UUID,
    provider: EmailProvider | None = None,
) -> ProjectEmailDraft:
    """Draft a chase email for missing returns. Never sends."""
    request = await get_procurement_request(
        session, project_id=project_id, request_id=request_id
    )
    if request.status != "issued":
        raise ProcurementRequestStateConflict(
            f"Cannot chase bidders from {request.status}"
        )
    if request.issue_email_draft_id is None:
        raise ProcurementRequestDraftConflict("procurement request has no issue email")
    issue_draft = await session.get(ProjectEmailDraft, request.issue_email_draft_id)
    if issue_draft is None:
        raise ProcurementRequestDraftConflict("procurement request has no issue email")
    recipients = list(issue_draft.to_addresses or [])
    submissions = await list_request_submissions(session, request_id=request.id)
    if len(submissions) >= len(recipients):
        raise ProcurementRequestStateConflict("no missing bidders to chase")
    label = _KIND_LABELS[request.kind]
    return await create_email_draft(
        session,
        project_id=project_id,
        created_by_user_id=actor_id,
        to_addresses=recipients,
        subject=f"Reminder: {label}: {request.target_name}",
        body_text=(
            f"We have not yet received your response to the {label} for "
            f"{request.target_name}. Please submit as soon as possible.\n"
        ),
        provider=provider,
        references={
            "kind": "procurement_chase",
            "procurement_request_id": str(request.id),
        },
    )


async def send_procurement_issue_email(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    request_id: uuid.UUID,
    draft_id: uuid.UUID,
    actor_id: uuid.UUID,
    expected_revision: int,
    provider: EmailProvider,
) -> ProcurementRequest:
    """Send the cover email, then issue the request. Never unsends."""
    request = await get_procurement_request(
        session, project_id=project_id, request_id=request_id
    )
    if request.status != "draft":
        raise ProcurementRequestStateConflict(
            f"Cannot issue procurement request from {request.status}"
        )
    if expected_revision != request.revision:
        raise ProcurementRequestRevisionConflict(
            f"Expected request revision {expected_revision}, current revision is {request.revision}"
        )
    draft = await session.get(ProjectEmailDraft, draft_id)
    if draft is None or draft.project_id != project_id:
        raise EmailNotFound(draft_id)
    if request.issue_email_draft_id != draft.id:
        raise ProcurementRequestStateConflict(
            "issue email draft does not belong to this request"
        )
    if draft.status == "draft":
        draft = await send_email_draft(
            session,
            project_id=project_id,
            draft_id=draft.id,
            actor_id=actor_id,
            provider=provider,
        )
    elif draft.status != "sent":
        raise EmailDraftConflict(f"cannot send draft in status {draft.status}")
    if draft.status != "sent":
        return request
    return await transition_procurement_request(
        session,
        request=request,
        status="issued",
        expected_revision=expected_revision,
    )
