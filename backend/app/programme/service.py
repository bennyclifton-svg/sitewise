from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.project import Project
from app.programme.models import ProgrammeActivity, ProgrammeVersion
from app.programme.mutate import apply_operations, reschedule
from app.programme.schemas import (
    ProgrammeActivityInput,
    ProgrammeOperation,
    ProgrammeState,
    ProgrammeViewUpdate,
)
from app.programme.seed import default_stage_inputs


class ProgrammeNotFound(LookupError):
    pass


class ProgrammeRevisionConflict(ValueError):
    pass


async def get_programme(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> ProgrammeState:
    row = await _load_current(session, project_id)
    if row is None:
        raise ProgrammeNotFound(str(project_id))
    return _state(row)


async def ensure_programme(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    start: date | None = None,
) -> ProgrammeState:
    current = await _load_current(session, project.id)
    if current is not None:
        return _state(current)
    activities = reschedule(default_stage_inputs(start=start or date.today()))
    row = _new_version(
        project_id=project.id,
        author_user_id=author_user_id,
        version=1,
        view_scale="month",
        pmp_embed_visible=True,
        activities=activities,
    )
    session.add(row)
    await session.flush()
    return _state(row)


async def apply_programme_operations(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    expected_base_version: int,
    operations: list[ProgrammeOperation],
) -> ProgrammeState:
    base = await _require_current(session, project.id, expected_base_version)
    activities = apply_operations(_activities(base), operations)
    return await _publish(
        session,
        base=base,
        project=project,
        author_user_id=author_user_id,
        activities=activities,
        view_scale=base.view_scale,
        pmp_embed_visible=base.pmp_embed_visible,
    )


async def set_programme_view(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    expected_base_version: int,
    update: ProgrammeViewUpdate,
) -> ProgrammeState:
    base = await _require_current(session, project.id, expected_base_version)
    return await _publish(
        session,
        base=base,
        project=project,
        author_user_id=author_user_id,
        activities=_activities(base),
        view_scale=update.view_scale or base.view_scale,
        pmp_embed_visible=(
            base.pmp_embed_visible
            if update.pmp_embed_visible is None
            else update.pmp_embed_visible
        ),
    )


async def _require_current(
    session: AsyncSession,
    project_id: uuid.UUID,
    expected_base_version: int,
) -> ProgrammeVersion:
    current = await _load_current(session, project_id)
    if current is None:
        raise ProgrammeNotFound(str(project_id))
    if current.version != expected_base_version:
        raise ProgrammeRevisionConflict(
            f"Expected Programme v{expected_base_version}, current version is v{current.version}"
        )
    return current


async def _publish(
    session: AsyncSession,
    *,
    base: ProgrammeVersion,
    project: Project,
    author_user_id: uuid.UUID,
    activities: list[ProgrammeActivityInput],
    view_scale: str,
    pmp_embed_visible: bool,
) -> ProgrammeState:
    base.status = "superseded"
    row = _new_version(
        project_id=project.id,
        author_user_id=author_user_id,
        version=base.version + 1,
        view_scale=view_scale,
        pmp_embed_visible=pmp_embed_visible,
        activities=activities,
    )
    session.add(row)
    await session.flush()
    return _state(row)


async def _load_current(
    session: AsyncSession, project_id: uuid.UUID
) -> ProgrammeVersion | None:
    statement = (
        select(ProgrammeVersion)
        .where(ProgrammeVersion.project_id == project_id)
        .options(selectinload(ProgrammeVersion.activities))
        .order_by(ProgrammeVersion.version.desc())
        .limit(1)
    )
    return (await session.execute(statement)).scalar_one_or_none()


def _new_version(
    *,
    project_id: uuid.UUID,
    author_user_id: uuid.UUID,
    version: int,
    view_scale: str,
    pmp_embed_visible: bool,
    activities: list[ProgrammeActivityInput],
) -> ProgrammeVersion:
    row = ProgrammeVersion(
        project_id=project_id,
        version=version,
        created_by_user_id=author_user_id,
        status="proposed",
        view_scale=view_scale,
        pmp_embed_visible=pmp_embed_visible,
    )
    row.activities = [
        ProgrammeActivity(
            activity_key=item.activity_key,
            kind=item.kind,
            parent_key=item.parent_key,
            name=item.name,
            display_order=item.display_order,
            start_date=item.start_date,
            duration_days=item.duration_days,
            finish_date=item.finish_date or item.start_date,
            predecessor_key=item.predecessor_key,
            lag_days=item.lag_days,
            assumption=item.assumption,
            notes=item.notes,
        )
        for item in activities
    ]
    return row


def _activities(row: ProgrammeVersion) -> list[ProgrammeActivityInput]:
    return [
        ProgrammeActivityInput(
            activity_key=item.activity_key,
            kind=item.kind,  # type: ignore[arg-type]
            parent_key=item.parent_key,
            name=item.name,
            display_order=item.display_order,
            start_date=item.start_date,
            duration_days=item.duration_days,
            finish_date=item.finish_date,
            predecessor_key=item.predecessor_key,
            lag_days=item.lag_days,
            assumption=item.assumption,
            notes=item.notes,
        )
        for item in row.activities
    ]


def _state(row: ProgrammeVersion) -> ProgrammeState:
    return ProgrammeState(
        id=row.id,
        project_id=row.project_id,
        version=row.version,
        status=row.status,  # type: ignore[arg-type]
        view_scale=row.view_scale,  # type: ignore[arg-type]
        pmp_embed_visible=row.pmp_embed_visible,
        activities=_activities(row),
    )
