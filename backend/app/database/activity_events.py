from __future__ import annotations

import inspect
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.activity_event import ActivityEvent
from app.logging import get_logger
from app.schemas.projects import WorkflowTraceEvent

log = get_logger(__name__)

TERMINAL_ACTIVITY_STATUSES = frozenset(
    {
        "blocked",
        "cancelled",
        "canceled",
        "complete",
        "completed",
        "done",
        "failed",
        "refused",
        "skipped",
    }
)


@dataclass(frozen=True, slots=True)
class ActivityRun:
    run_id: uuid.UUID
    source: str
    reference_type: str | None
    reference_id: uuid.UUID | None
    status: str
    created_at: datetime
    updated_at: datetime
    events: list[ActivityEvent]


def activity_run_status(events: Sequence[ActivityEvent]) -> str:
    if not events:
        return "running"
    latest_status = events[-1].status
    if latest_status in TERMINAL_ACTIVITY_STATUSES:
        return latest_status
    return "running"


async def record_activity_events(
    session,
    *,
    project_id: uuid.UUID,
    source: str,
    run_id: uuid.UUID,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    events: Sequence[WorkflowTraceEvent | Mapping[str, Any]],
) -> None:
    if not events:
        return

    created_at = datetime.now(UTC)
    rows = []
    for index, event in enumerate(events):
        rows.append(
            ActivityEvent(
                project_id=project_id,
                run_id=run_id,
                source=source,
                reference_type=reference_type,
                reference_id=reference_id,
                step=event.step
                if isinstance(event, WorkflowTraceEvent)
                else str(event["step"]),
                status=event.status
                if isinstance(event, WorkflowTraceEvent)
                else str(event["status"]),
                message=event.message
                if isinstance(event, WorkflowTraceEvent)
                else str(event["message"]),
                event_metadata=(
                    dict(event.metadata)
                    if isinstance(event, WorkflowTraceEvent)
                    else dict(event.get("metadata") or {})
                ),
                created_at=created_at + timedelta(microseconds=index),
            )
        )

    try:
        if isinstance(session, AsyncSession):
            async with session.begin_nested():
                session.add_all(rows)
                await session.flush()
            return

        add_result = session.add_all(rows)
        if inspect.isawaitable(add_result):
            await add_result
        flush_result = session.flush()
        if inspect.isawaitable(flush_result):
            await flush_result
    except Exception:
        log.exception(
            "activity_events_record_failed",
            project_id=str(project_id),
            source=source,
            run_id=str(run_id),
        )


async def list_project_activity_runs(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    since: datetime | None = None,
    limit: int = 50,
) -> list[ActivityRun]:
    latest_created_at = func.max(ActivityEvent.created_at).label("updated_at")
    grouped = (
        select(ActivityEvent.run_id, latest_created_at)
        .where(ActivityEvent.project_id == project_id)
        .group_by(ActivityEvent.run_id)
    )
    if since is not None:
        grouped = grouped.having(latest_created_at > since)
    grouped = grouped.order_by(desc("updated_at")).limit(limit)

    grouped_rows = (await session.execute(grouped)).all()
    if not grouped_rows:
        return []

    run_ids = [row.run_id for row in grouped_rows]
    order = {row.run_id: index for index, row in enumerate(grouped_rows)}
    updated_at_by_run = {row.run_id: row.updated_at for row in grouped_rows}

    events_result = await session.execute(
        select(ActivityEvent)
        .where(
            ActivityEvent.project_id == project_id,
            ActivityEvent.run_id.in_(run_ids),
        )
        .order_by(ActivityEvent.run_id.asc(), ActivityEvent.created_at.asc())
    )
    events_by_run: dict[uuid.UUID, list[ActivityEvent]] = {
        run_id: [] for run_id in run_ids
    }
    for event in events_result.scalars().all():
        events_by_run.setdefault(event.run_id, []).append(event)

    runs: list[ActivityRun] = []
    for run_id in run_ids:
        events = events_by_run.get(run_id, [])
        if not events:
            continue
        first = events[0]
        runs.append(
            ActivityRun(
                run_id=run_id,
                source=first.source,
                reference_type=first.reference_type,
                reference_id=first.reference_id,
                status=activity_run_status(events),
                created_at=first.created_at,
                updated_at=updated_at_by_run[run_id],
                events=events,
            )
        )

    return sorted(runs, key=lambda run: order[run.run_id])


async def delete_project_activity_runs(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    run_ids: Sequence[uuid.UUID],
) -> int:
    if not run_ids:
        return 0

    result = await session.execute(
        delete(ActivityEvent).where(
            ActivityEvent.project_id == project_id,
            ActivityEvent.run_id.in_(list(run_ids)),
        )
    )
    return int(result.rowcount or 0)
