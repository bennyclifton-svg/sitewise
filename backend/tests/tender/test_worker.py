import asyncio
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

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
    job = _job()
    handler = AsyncMock()

    async def _run() -> None:
        with (
            patch.object(worker.jobs, "claim_next", new=AsyncMock(return_value=job)),
            patch.object(worker.jobs, "complete", new=AsyncMock()) as mock_complete,
            patch.dict(worker.HANDLERS, {"ingest_document": handler}),
        ):
            processed = await worker.run_once(_session_factory(mock_session), "host:1")

        assert processed is True
        handler.assert_awaited_once_with(mock_session, job)
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
