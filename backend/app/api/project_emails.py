"""Project-scoped email register, drafts, and match corrections."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.billing.entitlements import require_active_entitlement
from app.config import settings
from app.database.projects import get_project
from app.database.session import get_db
from app.email.providers import email_provider_from_settings
from app.email.schemas import (
    EmailDraftView,
    EmailMatchView,
    EmailRegisterRow,
    LinkEmailRequest,
    ReplyEmailDraftRequest,
)
from app.email.service import (
    EmailDraftConflict,
    EmailNotFound,
    link_email_to_project,
    list_project_email_register,
    read_email_thread,
    reply_email_draft,
    send_email_draft,
)

router = APIRouter(prefix="/projects", tags=["project-emails"])


async def _owned_project(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
):
    project = await get_project(session, project_id)
    if project is None or project.owner_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def _draft_view(draft) -> EmailDraftView:
    return EmailDraftView(
        id=draft.id,
        project_id=draft.project_id,
        status=draft.status,
        to_addresses=list(draft.to_addresses or []),
        cc_addresses=list(draft.cc_addresses or []),
        subject=draft.subject,
        body_text=draft.body_text,
        in_reply_to_email_id=draft.in_reply_to_email_id,
        provider_draft_id=draft.provider_draft_id,
        provider_message_id=draft.provider_message_id,
        send_error=draft.send_error,
        sent_at=draft.sent_at,
        sent_by_user_id=draft.sent_by_user_id,
    )


@router.get("/{project_id}/emails", response_model=list[EmailRegisterRow])
async def get_project_email_register(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[EmailRegisterRow]:
    await require_active_entitlement(session, user)
    await _owned_project(session, project_id=project_id, user_id=user.id)
    rows = await list_project_email_register(session, project_id=project_id)
    return [EmailRegisterRow.model_validate(row) for row in rows]


@router.post(
    "/{project_id}/emails/drafts/{draft_id}/send",
    response_model=EmailDraftView,
)
async def post_send_project_email_draft(
    project_id: uuid.UUID,
    draft_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailDraftView:
    await require_active_entitlement(session, user)
    project = await _owned_project(session, project_id=project_id, user_id=user.id)
    try:
        draft = await send_email_draft(
            session,
            project_id=project.id,
            draft_id=draft_id,
            actor_id=user.id,
            provider=email_provider_from_settings(settings),
        )
    except EmailNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        ) from exc
    except EmailDraftConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return _draft_view(draft)


@router.post(
    "/{project_id}/emails/{email_id}/reply-draft",
    response_model=EmailDraftView,
)
async def post_reply_project_email_draft(
    project_id: uuid.UUID,
    email_id: uuid.UUID,
    body: ReplyEmailDraftRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailDraftView:
    await require_active_entitlement(session, user)
    project = await _owned_project(session, project_id=project_id, user_id=user.id)
    payload = body or ReplyEmailDraftRequest()
    try:
        draft = await reply_email_draft(
            session,
            project_id=project.id,
            created_by_user_id=user.id,
            email_id=email_id,
            body_text=payload.body_text,
            to_addresses=payload.to_addresses,
            cc_addresses=payload.cc_addresses,
            provider=email_provider_from_settings(settings),
        )
    except EmailNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        ) from exc
    await session.commit()
    return _draft_view(draft)


@router.get("/{project_id}/emails/{email_id}/thread")
async def get_project_email_thread(
    project_id: uuid.UUID,
    email_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    await require_active_entitlement(session, user)
    project = await _owned_project(session, project_id=project_id, user_id=user.id)
    try:
        return await read_email_thread(
            session, project_id=project.id, email_id=email_id
        )
    except EmailNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        ) from exc


@router.post("/{project_id}/emails/{email_id}/link", response_model=EmailMatchView)
async def post_link_project_email(
    project_id: uuid.UUID,
    email_id: uuid.UUID,
    body: LinkEmailRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailMatchView:
    await require_active_entitlement(session, user)
    project = await _owned_project(session, project_id=project_id, user_id=user.id)
    try:
        interpretation = await link_email_to_project(
            session,
            email_id=email_id,
            project_id=project.id,
            actor_id=user.id,
            reason=body.reason,
        )
    except EmailNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        ) from exc
    await session.commit()
    confidence = interpretation.match_confidence
    return EmailMatchView(
        email_id=interpretation.email_id,
        project_id=interpretation.project_id,
        match_basis=interpretation.match_basis,
        match_confidence=None if confidence is None else float(confidence),
    )
