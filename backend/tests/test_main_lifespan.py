from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI

from app import main
from tests.conftest import run_async


def test_lifespan_starts_and_stops_inprocess_tender_worker(monkeypatch) -> None:
    events: list[str] = []

    @asynccontextmanager
    async def fake_mcp_lifespan(_app):
        events.append("mcp-start")
        yield
        events.append("mcp-stop")

    async def fake_start():
        events.append("worker-start")
        return "worker-handle"

    async def fake_stop(handle):
        events.append(f"worker-stop:{handle}")

    engine = AsyncMock()

    monkeypatch.setattr(main, "mcp_app", SimpleNamespace(lifespan=fake_mcp_lifespan))
    monkeypatch.setattr(main, "start_inprocess_tender_worker", fake_start)
    monkeypatch.setattr(main, "stop_inprocess_tender_worker", fake_stop)
    monkeypatch.setattr(main, "get_engine", lambda: engine)

    async def _run() -> None:
        async with main.lifespan(FastAPI()):
            events.append("inside")

    run_async(_run())

    assert events == [
        "worker-start",
        "mcp-start",
        "inside",
        "mcp-stop",
        "worker-stop:worker-handle",
    ]
    engine.dispose.assert_awaited_once()
