from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.billing.entitlements import require_active_entitlement
from app.database.projects import get_project
from app.database.session import get_db
from app.projects.event_spine import record_project_verb
from app.projects.pulse import PulseFeed, build_pulse_feed, parse_signal_type
from app.schemas.pulse import PulseDismissRequest

router = APIRouter(prefix="/projects", tags=["pulse"])


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


@router.get("/{project_id}/pulse", response_model=PulseFeed)
async def get_project_pulse(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PulseFeed:
    await require_active_entitlement(session, user)
    await _owned_project(session, project_id=project_id, user_id=user.id)
    return await build_pulse_feed(session, project_id)


@router.post("/{project_id}/pulse/dismiss", response_model=PulseFeed)
async def dismiss_project_pulse(
    project_id: uuid.UUID,
    body: PulseDismissRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PulseFeed:
    await require_active_entitlement(session, user)
    project = await _owned_project(session, project_id=project_id, user_id=user.id)
    signal_type = parse_signal_type(body.subject_key)
    if signal_type is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unknown Pulse signal type",
        )
    await record_project_verb(
        session,
        project_id=project.id,
        verb="project_signal.dismissed",
        reference_type="pulse",
        reference_id=uuid.uuid5(uuid.NAMESPACE_URL, body.subject_key),
        message=f"Dismissed {body.subject_key}",
        deduplication_key=f"project_signal.dismissed:pulse:{body.subject_key}",
        metadata={
            "signal_type": signal_type,
            "subject_key": body.subject_key,
        },
    )
    await session.commit()
    return await build_pulse_feed(session, project.id)
