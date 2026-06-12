import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from tender.models import TenderJob
from tender.services import jobs
from tests.conftest import run_async


def _job(**overrides) -> TenderJob:
    defaults = dict(
        id=uuid.uuid4(),
        kind="ingest_document",
        payload={"document_id": str(uuid.uuid4())},
        status="queued",
        attempts=0,
        locked_at=None,
        locked_by=None,
        last_error=None,
        run_after=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return TenderJob(**defaults)


def _claim_result(job: TenderJob | None) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.first.return_value = job
    return result


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


def test_enqueue_adds_and_flushes(mock_session: AsyncMock) -> None:
    async def _run() -> None:
        job = await jobs.enqueue(
            mock_session, kind="ingest_document", payload={"document_id": "abc"}
        )
        assert job.kind == "ingest_document"
        assert job.payload == {"document_id": "abc"}
        assert job.status == "queued"
        mock_session.add.assert_called_once_with(job)
        mock_session.flush.assert_awaited_once()

    run_async(_run())


def test_claim_next_returns_none_when_queue_empty(mock_session: AsyncMock) -> None:
    mock_session.execute = AsyncMock(return_value=_claim_result(None))

    async def _run() -> None:
        claimed = await jobs.claim_next(mock_session, worker_id="host:1")
        assert claimed is None
        mock_session.commit.assert_not_awaited()

    run_async(_run())


def test_claim_next_locks_job_and_commits(mock_session: AsyncMock) -> None:
    job = _job()
    mock_session.execute = AsyncMock(return_value=_claim_result(job))

    async def _run() -> None:
        claimed = await jobs.claim_next(mock_session, worker_id="host:42")
        assert claimed is job
        assert job.status == "running"
        assert job.locked_by == "host:42"
        assert job.locked_at is not None
        mock_session.commit.assert_awaited_once()

    run_async(_run())


def test_complete_marks_done_and_clears_lock(mock_session: AsyncMock) -> None:
    job = _job(status="running", locked_by="host:1", locked_at=datetime.now(timezone.utc))

    async def _run() -> None:
        await jobs.complete(mock_session, job)
        assert job.status == "done"
        assert job.locked_at is None
        assert job.locked_by is None
        mock_session.commit.assert_awaited_once()

    run_async(_run())


def test_fail_first_attempt_requeues_with_base_backoff(mock_session: AsyncMock) -> None:
    job = _job(status="running", locked_by="host:1", locked_at=datetime.now(timezone.utc))

    async def _run() -> None:
        before = datetime.now(timezone.utc)
        await jobs.fail(
            mock_session, job, "boom", max_attempts=3, backoff_base_seconds=30
        )
        assert job.attempts == 1
        assert job.status == "queued"
        assert job.last_error == "boom"
        assert job.locked_at is None
        assert job.locked_by is None
        delay = (job.run_after - before).total_seconds()
        assert 29 <= delay <= 35
        mock_session.commit.assert_awaited_once()

    run_async(_run())


def test_fail_second_attempt_doubles_backoff(mock_session: AsyncMock) -> None:
    job = _job(status="running", attempts=1)

    async def _run() -> None:
        before = datetime.now(timezone.utc)
        await jobs.fail(
            mock_session, job, "boom again", max_attempts=3, backoff_base_seconds=30
        )
        assert job.attempts == 2
        assert job.status == "queued"
        delay = (job.run_after - before).total_seconds()
        assert 59 <= delay <= 65

    run_async(_run())


def test_fail_exhausts_attempts_and_marks_failed(mock_session: AsyncMock) -> None:
    job = _job(status="running", attempts=2)

    async def _run() -> None:
        await jobs.fail(
            mock_session, job, "final straw", max_attempts=3, backoff_base_seconds=30
        )
        assert job.attempts == 3
        assert job.status == "failed"
        assert job.last_error == "final straw"
        assert job.locked_at is None
        assert job.locked_by is None
        mock_session.commit.assert_awaited_once()

    run_async(_run())


def test_requeue_stale_issues_update_and_commits(mock_session: AsyncMock) -> None:
    result = MagicMock()
    result.rowcount = 2
    mock_session.execute = AsyncMock(return_value=result)

    async def _run() -> None:
        count = await jobs.requeue_stale(mock_session, older_than_minutes=10)
        assert count == 2
        mock_session.execute.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    run_async(_run())


def test_claim_query_uses_skip_locked_and_run_after_order() -> None:
    query = jobs.claim_query()
    sql = str(query.compile(dialect=__import__("sqlalchemy").dialects.postgresql.dialect()))
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "ORDER BY tender_jobs.run_after" in sql
    assert "LIMIT" in sql
