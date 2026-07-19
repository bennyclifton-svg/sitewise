"""tender_jobs queue service (PRD §7.3).

The queue is the ``tender_jobs`` table. Claiming uses
``SELECT … FOR UPDATE SKIP LOCKED`` in its own short transaction: the row
lock exists only while flipping the row to ``running``, never for the
duration of the work, so concurrent workers skip claimed rows safely.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import Select, func, inspect as sa_inspect, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.projects.events import publish_project_event
from tender.models import TenderComparison, TenderJob

logger = structlog.get_logger(__name__)


async def enqueue(
    session: AsyncSession,
    *,
    kind: str,
    comparison_id: uuid.UUID | None = None,
    quote_id: uuid.UUID | None = None,
    payload: dict | None = None,
    run_after: datetime | None = None,
) -> TenderJob:
    """Add a queued job; the caller's transaction commits it."""

    job = TenderJob(
        kind=kind,
        comparison_id=comparison_id,
        quote_id=quote_id,
        payload=payload,
        status="queued",
        attempts=0,
        run_after=run_after or datetime.now(timezone.utc),
    )
    session.add(job)
    await session.flush()
    logger.info("tender_job_enqueued", job_id=str(job.id), kind=kind)
    return job


def claim_query() -> Select[tuple[TenderJob]]:
    return (
        select(TenderJob)
        .where(TenderJob.status == "queued", TenderJob.run_after <= func.now())
        .order_by(TenderJob.run_after)
        .limit(1)
        .with_for_update(skip_locked=True)
    )


async def claim_next(session: AsyncSession, *, worker_id: str) -> TenderJob | None:
    """Claim the next runnable job, or return None if the queue is empty.

    The claim commits immediately so the row lock is released as soon as the
    job is marked ``running``.
    """

    result = await session.execute(claim_query())
    job = result.scalars().first()
    if job is None:
        return None

    job.status = "running"
    job.locked_at = datetime.now(timezone.utc)
    job.locked_by = worker_id
    await session.commit()
    logger.info("tender_job_claimed", job_id=str(job.id), kind=job.kind, worker_id=worker_id)
    return job


async def complete(session: AsyncSession, job: TenderJob) -> None:
    job.status = "done"
    job.locked_at = None
    job.locked_by = None
    if job.comparison_id is not None:
        project_id = await session.scalar(
            select(TenderComparison.project_id).where(
                TenderComparison.id == job.comparison_id
            )
        )
        if project_id is not None:
            await publish_project_event(
                session,
                project_id=project_id,
                actor_source="tender_worker",
                resource_type="tender_job",
                resource_id=job.id,
                resource_revision=None,
                action="completed",
                payload={
                    "job_kind": job.kind,
                    "comparison_id": str(job.comparison_id),
                },
                deduplication_key=f"tender_job:{job.id}:completed",
            )
    await session.commit()
    logger.info("tender_job_done", job_id=str(job.id), kind=job.kind)


async def fail(
    session: AsyncSession,
    job: TenderJob,
    error: str,
    *,
    max_attempts: int | None = None,
    backoff_base_seconds: int | None = None,
) -> None:
    """Record a failed attempt: requeue with exponential backoff, or exhaust.

    Backoff is ``base * 2**(attempts - 1)`` — 30s after the first failure,
    60s after the second, ``failed`` with ``last_error`` at the third
    (defaults per config).
    """

    max_attempts = max_attempts if max_attempts is not None else settings.tender_job_max_attempts
    backoff_base_seconds = (
        backoff_base_seconds
        if backoff_base_seconds is not None
        else settings.tender_job_backoff_base_seconds
    )

    job = await _refresh_if_expired(session, job)
    job.attempts += 1
    job.last_error = error
    job.locked_at = None
    job.locked_by = None

    if job.attempts >= max_attempts:
        job.status = "failed"
        logger.warning(
            "tender_job_failed",
            job_id=str(job.id),
            kind=job.kind,
            attempts=job.attempts,
            error=_error_summary(error),
        )
    else:
        backoff_seconds = backoff_base_seconds * 2 ** (job.attempts - 1)
        job.status = "queued"
        job.run_after = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
        logger.warning(
            "tender_job_retry_scheduled",
            job_id=str(job.id),
            kind=job.kind,
            attempts=job.attempts,
            backoff_seconds=backoff_seconds,
            error=_error_summary(error),
        )

    await session.commit()


def _error_summary(error: str) -> str:
    lines = [line.strip() for line in error.splitlines() if line.strip()]
    return (lines[-1] if lines else error.strip())[:500]


async def _refresh_if_expired(session: AsyncSession, job: TenderJob) -> TenderJob:
    state = sa_inspect(job)
    if not state.expired or not state.identity:
        return job

    refreshed = await session.get(TenderJob, state.identity[0])
    if refreshed is None:
        raise ValueError(f"cannot fail missing tender job: {state.identity[0]}")
    return refreshed


async def requeue_stale(session: AsyncSession, *, older_than_minutes: int) -> int:
    """Return jobs stranded ``running`` by a crashed worker to the queue."""

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
    result = await session.execute(
        update(TenderJob)
        .where(TenderJob.status == "running", TenderJob.locked_at < cutoff)
        .values(status="queued", locked_at=None, locked_by=None)
    )
    await session.commit()
    requeued = result.rowcount or 0
    if requeued:
        logger.warning("tender_jobs_stale_requeued", count=requeued)
    return requeued
