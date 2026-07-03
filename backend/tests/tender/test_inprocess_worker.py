import asyncio

from app.config import settings
from app.tender_worker import (
    start_inprocess_tender_worker,
    stop_inprocess_tender_worker,
)
from tests.conftest import run_async


def test_inprocess_tender_worker_default_off(monkeypatch) -> None:
    monkeypatch.setattr(settings, "tender_worker_inproc_enabled", False)

    async def _run() -> None:
        handle = await start_inprocess_tender_worker(session_factory=object())
        assert handle is None

    run_async(_run())


def test_inprocess_tender_worker_starts_and_stops(monkeypatch) -> None:
    monkeypatch.setattr(settings, "tender_worker_inproc_enabled", True)
    monkeypatch.setattr(settings, "tender_worker_concurrency", 2)
    calls: dict[str, object] = {}

    async def fake_run_pool(
        session_factory,
        worker_id,
        *,
        shutdown_event,
        concurrency,
    ) -> None:
        calls["session_factory"] = session_factory
        calls["worker_id"] = worker_id
        calls["concurrency"] = concurrency
        calls["started"] = True
        await shutdown_event.wait()
        calls["stopped"] = True

    monkeypatch.setattr("app.tender_worker.tender_worker.run_pool", fake_run_pool)

    async def _run() -> None:
        session_factory = object()
        handle = await start_inprocess_tender_worker(
            session_factory=session_factory,
        )
        assert handle is not None
        await asyncio.sleep(0)
        assert calls["session_factory"] is session_factory
        assert str(calls["worker_id"]).startswith("inproc:")
        assert calls["concurrency"] == 2

        await stop_inprocess_tender_worker(handle)
        assert calls["stopped"] is True
        assert handle.task.done()

    run_async(_run())
