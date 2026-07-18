import asyncio
import uuid
from contextlib import asynccontextmanager
from unittest.mock import ANY, AsyncMock, patch

import pytest
from tender import worker
from tender.models import TenderJob
from tests.conftest import run_async


def _job(kind: str = "ingest_document") -> TenderJob:
    return TenderJob(
        id=uuid.uuid4(),
        kind=kind,
        payload={},
        status="running",
        attempts=0,
    )


def _comparison_job(kind: str = "ingest_document") -> TenderJob:
    job = _job(kind)
    job.comparison_id = uuid.uuid4()
    return job


def _session_factory(session: AsyncMock):
    @asynccontextmanager
    async def factory():
        yield session

    return factory


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


def test_run_once_returns_false_when_queue_empty(mock_session: AsyncMock) -> None:
    async def _run() -> None:
        with patch.object(worker.jobs, "claim_next", new=AsyncMock(return_value=None)):
            processed = await worker.run_once(_session_factory(mock_session), "host:1")
        assert processed is False

    run_async(_run())


def test_run_once_dispatches_by_kind_and_completes(mock_session: AsyncMock) -> None:
    job = _comparison_job()
    handler = AsyncMock()

    async def _run() -> None:
        with (
            patch.object(worker.jobs, "claim_next", new=AsyncMock(return_value=job)),
            patch.object(worker.jobs, "complete", new=AsyncMock()) as mock_complete,
            patch.object(
                worker.telemetry, "record_stage_timing", new=AsyncMock()
            ) as mock_timing,
            patch.dict(worker.HANDLERS, {"ingest_document": handler}),
        ):
            processed = await worker.run_once(_session_factory(mock_session), "host:1")

        assert processed is True
        handler.assert_awaited_once_with(mock_session, job)
        mock_timing.assert_awaited_once_with(
            mock_session,
            comparison_id=job.comparison_id,
            job_id=job.id,
            stage="ingest_document",
            duration_ms=ANY,
            status="done",
            llm_calls=0,
            input_tokens=0,
            output_tokens=0,
            cache_hits=0,
            metadata=None,
        )
        mock_complete.assert_awaited_once_with(mock_session, job)

    run_async(_run())


def test_run_once_handler_exception_fails_job_with_traceback(
    mock_session: AsyncMock,
) -> None:
    job = _job()

    async def exploding_handler(session, job):
        raise RuntimeError("kaboom in handler")

    async def _run() -> None:
        with (
            patch.object(worker.jobs, "claim_next", new=AsyncMock(return_value=job)),
            patch.object(worker.jobs, "fail", new=AsyncMock()) as mock_fail,
            patch.object(worker.jobs, "complete", new=AsyncMock()) as mock_complete,
            patch.dict(worker.HANDLERS, {"ingest_document": exploding_handler}),
        ):
            processed = await worker.run_once(_session_factory(mock_session), "host:1")

        assert processed is True
        mock_complete.assert_not_awaited()
        mock_fail.assert_awaited_once()
        error_text = mock_fail.await_args.args[2]
        assert "kaboom in handler" in error_text
        assert "RuntimeError" in error_text

    run_async(_run())


def test_run_once_unknown_kind_fails_without_raising(mock_session: AsyncMock) -> None:
    job = _job(kind="not_a_real_stage")

    async def _run() -> None:
        with (
            patch.object(worker.jobs, "claim_next", new=AsyncMock(return_value=job)),
            patch.object(worker.jobs, "fail", new=AsyncMock()) as mock_fail,
        ):
            processed = await worker.run_once(_session_factory(mock_session), "host:1")

        assert processed is True
        mock_fail.assert_awaited_once()
        assert "not_a_real_stage" in mock_fail.await_args.args[2]

    run_async(_run())


def test_front_half_handlers_registered() -> None:
    from tender.services.classification import classify_document
    from tender.services.extraction_handler import extract_line_items_job
    from tender.services.ingestion import ingest_document

    assert worker.HANDLERS["ingest_document"] is ingest_document
    assert worker.HANDLERS["classify_document"] is classify_document
    assert worker.HANDLERS["extract_line_items"] is extract_line_items_job


def test_run_loop_stops_when_shutdown_event_set(mock_session: AsyncMock) -> None:
    async def _run() -> None:
        shutdown = asyncio.Event()
        shutdown.set()
        with patch.object(worker.jobs, "claim_next", new=AsyncMock()) as mock_claim:
            await worker.run_loop(
                _session_factory(mock_session), "host:1", shutdown_event=shutdown
            )
        mock_claim.assert_not_awaited()

    run_async(_run())


def test_run_loop_processes_then_stops_on_shutdown(mock_session: AsyncMock) -> None:
    job = _job()
    shutdown = asyncio.Event()
    handler_calls: list[TenderJob] = []

    async def handler(session, claimed_job):
        handler_calls.append(claimed_job)
        shutdown.set()

    async def _run() -> None:
        with (
            patch.object(
                worker.jobs, "claim_next", new=AsyncMock(side_effect=[job, None])
            ),
            patch.object(worker.jobs, "complete", new=AsyncMock()),
            patch.object(worker.jobs, "requeue_stale", new=AsyncMock(return_value=0)),
            patch.dict(worker.HANDLERS, {"ingest_document": handler}),
        ):
            await asyncio.wait_for(
                worker.run_loop(
                    _session_factory(mock_session), "host:1", shutdown_event=shutdown
                ),
                timeout=5,
            )

        assert handler_calls == [job]

    run_async(_run())


def test_run_pool_runs_concurrency_lanes_with_distinct_ids(
    mock_session: AsyncMock,
) -> None:
    shutdown = asyncio.Event()
    seen_ids: set[str] = set()

    async def fake_run_once(session_factory, worker_id):
        seen_ids.add(worker_id)
        if len(seen_ids) >= 3:
            shutdown.set()
        return False

    async def _run() -> None:
        with (
            patch.object(worker, "run_once", new=fake_run_once),
            patch.object(worker.jobs, "requeue_stale", new=AsyncMock(return_value=0)),
        ):
            await asyncio.wait_for(
                worker.run_pool(
                    _session_factory(mock_session),
                    "host:1",
                    shutdown_event=shutdown,
                    concurrency=3,
                ),
                timeout=5,
            )

        assert seen_ids == {"host:1#0", "host:1#1", "host:1#2"}

    run_async(_run())


def test_run_lane_continues_after_run_once_raises(mock_session: AsyncMock) -> None:
    shutdown = asyncio.Event()
    calls: list[int] = []

    async def flaky_run_once(session_factory, worker_id):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("transient db blip")
        shutdown.set()
        return False

    async def _run() -> None:
        with (
            patch.object(worker, "run_once", new=flaky_run_once),
            patch.object(worker.settings, "tender_worker_poll_seconds", 0.01),
        ):
            await asyncio.wait_for(
                worker.run_lane(
                    _session_factory(mock_session), "host:1#0", shutdown_event=shutdown
                ),
                timeout=5,
            )

        # First call raised; the lane must self-heal and call run_once again.
        assert len(calls) == 2

    run_async(_run())


def test_run_sweeper_requeues_stale_until_shutdown(mock_session: AsyncMock) -> None:
    shutdown = asyncio.Event()
    calls: list[int] = []

    async def fake_requeue(session, *, older_than_minutes):
        calls.append(older_than_minutes)
        shutdown.set()
        return 0

    async def _run() -> None:
        with patch.object(worker.jobs, "requeue_stale", new=fake_requeue):
            await asyncio.wait_for(
                worker.run_sweeper(
                    _session_factory(mock_session), shutdown_event=shutdown
                ),
                timeout=5,
            )

        assert calls == [worker.settings.tender_job_stale_lock_minutes]

    run_async(_run())
