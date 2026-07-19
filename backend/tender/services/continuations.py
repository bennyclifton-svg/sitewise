from __future__ import annotations

import hashlib
import inspect
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import TenderJob, TenderQuote
from tender.services import jobs


async def after_job_complete(
    session: AsyncSession,
    *,
    job_id: uuid.UUID,
    job_kind: str,
    comparison_id: uuid.UUID | None,
) -> None:
    if comparison_id is None:
        return
    try:
        if job_kind == "embed_items":
            await _enqueue_taxonomy_if_ready(session, comparison_id=comparison_id)
        elif job_kind == "map_items":
            await _enqueue_expectations_if_ready(session, comparison_id=comparison_id)
        elif job_kind in {"infer_silence", "infer_silence_batch"}:
            await _enqueue_analysis_if_ready(session, comparison_id=comparison_id)
    finally:
        in_transaction = session.in_transaction()
        if inspect.isawaitable(in_transaction):
            in_transaction = await in_transaction
        if in_transaction:
            await session.rollback()


async def _enqueue_taxonomy_if_ready(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> None:
    await _lock_continuation(
        session,
        comparison_id=comparison_id,
        stage="generate_project_taxonomy",
    )
    if await _has_active_jobs(
        session,
        comparison_id=comparison_id,
        kind="embed_items",
    ) or await _has_active_jobs(
        session,
        comparison_id=comparison_id,
        kind="extract_line_items",
    ):
        return
    if not await _all_quotes_ready_for_taxonomy(
        session,
        comparison_id=comparison_id,
    ):
        return
    if await _has_existing_job(
        session,
        comparison_id=comparison_id,
        kind="generate_project_taxonomy",
    ):
        return
    await jobs.enqueue(
        session,
        kind="generate_project_taxonomy",
        comparison_id=comparison_id,
        payload={"reason": "all_quotes_embedded"},
    )
    await session.commit()


async def _all_quotes_ready_for_taxonomy(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> bool:
    result = await session.execute(
        select(TenderQuote.stage).where(TenderQuote.comparison_id == comparison_id)
    )
    stages = list(result.scalars())
    return bool(stages) and all(stage == "map_items" for stage in stages)


async def _enqueue_expectations_if_ready(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> None:
    await _lock_continuation(
        session,
        comparison_id=comparison_id,
        stage="run_expectations",
    )
    if await _has_active_jobs(
        session,
        comparison_id=comparison_id,
        kind="map_items",
    ):
        return
    if not await _all_quotes_ready_for_expectations(
        session,
        comparison_id=comparison_id,
    ):
        return
    if await _has_existing_job(
        session,
        comparison_id=comparison_id,
        kind="run_expectations",
    ):
        return
    await jobs.enqueue(
        session,
        kind="run_expectations",
        comparison_id=comparison_id,
        payload={"reason": "all_quotes_mapped"},
    )
    await session.commit()


async def _enqueue_analysis_if_ready(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> None:
    await _lock_continuation(
        session,
        comparison_id=comparison_id,
        stage="run_analysis",
    )
    if await _has_active_jobs(
        session,
        comparison_id=comparison_id,
        kind="infer_silence",
    ) or await _has_active_jobs(
        session,
        comparison_id=comparison_id,
        kind="infer_silence_batch",
    ):
        return
    if await _has_existing_job(
        session,
        comparison_id=comparison_id,
        kind="run_analysis",
    ):
        return
    await jobs.enqueue(
        session,
        kind="run_analysis",
        comparison_id=comparison_id,
        payload={"reason": "all_silence_complete"},
    )
    await session.commit()


async def _has_active_jobs(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    kind: str,
) -> bool:
    result = await session.execute(
        select(TenderJob.id)
        .where(
            TenderJob.comparison_id == comparison_id,
            TenderJob.kind == kind,
            TenderJob.status.in_(("queued", "running")),
        )
        .limit(1)
    )
    return result.scalars().first() is not None


async def _has_existing_job(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    kind: str,
) -> bool:
    result = await session.execute(
        select(TenderJob.id)
        .where(
            TenderJob.comparison_id == comparison_id,
            TenderJob.kind == kind,
            TenderJob.status.in_(("queued", "running", "done")),
        )
        .limit(1)
    )
    return result.scalars().first() is not None


async def _all_quotes_ready_for_expectations(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> bool:
    result = await session.execute(
        select(TenderQuote.stage).where(TenderQuote.comparison_id == comparison_id)
    )
    stages = list(result.scalars())
    return bool(stages) and all(stage == "run_expectations" for stage in stages)


async def _lock_continuation(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    stage: str,
) -> None:
    await session.execute(
        select(func.pg_advisory_xact_lock(_continuation_lock_key(comparison_id, stage)))
    )


def _continuation_lock_key(comparison_id: uuid.UUID, stage: str) -> int:
    digest = hashlib.blake2b(
        f"{comparison_id}:{stage}".encode("ascii"),
        digest_size=8,
    ).digest()
    return int.from_bytes(digest, "big") & ((1 << 63) - 1)
