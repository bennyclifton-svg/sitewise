"""SKIP LOCKED concurrency proof against a real PostgreSQL database."""

import asyncio
import uuid

import pytest
from sqlalchemy import delete

from app.database.session import get_session_factory
from tender.models import TenderJob
from tender.services import jobs
from tests.conftest import run_async

pytestmark = pytest.mark.integration

TEST_KIND = "integration_test_claim"


async def _cleanup(factory) -> None:
    async with factory() as session:
        await session.execute(delete(TenderJob).where(TenderJob.kind == TEST_KIND))
        await session.commit()


def test_locked_row_is_skipped_by_second_claimer() -> None:
    """While one transaction holds the claim lock, a second claimer skips the row."""

    async def _run() -> None:
        factory = get_session_factory()
        await _cleanup(factory)

        async with factory() as session:
            job = await jobs.enqueue(session, kind=TEST_KIND)
            await session.commit()
            job_id = job.id

        try:
            async with factory() as first, factory() as second:
                first_result = await first.execute(jobs.claim_query())
                first_job = first_result.scalars().first()
                assert first_job is not None
                assert first_job.id == job_id

                # The first transaction still holds the row lock here.
                second_result = await second.execute(jobs.claim_query())
                second_job = second_result.scalars().first()
                assert second_job is None or second_job.id != job_id

                await first.rollback()
                await second.rollback()
        finally:
            await _cleanup(factory)

    run_async(_run())


def test_exactly_one_concurrent_claimer_wins() -> None:
    async def _run() -> None:
        factory = get_session_factory()
        await _cleanup(factory)

        async with factory() as session:
            job = await jobs.enqueue(session, kind=TEST_KIND)
            await session.commit()
            job_id = job.id

        try:
            async with factory() as first, factory() as second:
                results = await asyncio.gather(
                    jobs.claim_next(first, worker_id=f"w1:{uuid.uuid4()}"),
                    jobs.claim_next(second, worker_id=f"w2:{uuid.uuid4()}"),
                )
            winners = [job for job in results if job is not None and job.id == job_id]
            assert len(winners) == 1
            assert winners[0].status == "running"
        finally:
            await _cleanup(factory)

    run_async(_run())
