from __future__ import annotations

import asyncio
import os
import socket
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.database.session import get_session_factory
from app.logging import get_logger
from tender import worker as tender_worker

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class InProcessTenderWorker:
    shutdown_event: asyncio.Event
    task: asyncio.Task[None]
    worker_id: str


async def start_inprocess_tender_worker(
    *,
    session_factory: Any | None = None,
) -> InProcessTenderWorker | None:
    if not settings.tender_worker_inproc_enabled:
        return None

    shutdown_event = asyncio.Event()
    worker_id = f"inproc:{socket.gethostname()}:{os.getpid()}"
    task = asyncio.create_task(
        tender_worker.run_pool(
            session_factory or get_session_factory(),
            worker_id,
            shutdown_event=shutdown_event,
            concurrency=max(1, settings.tender_worker_concurrency),
        ),
        name="tender-worker-inproc",
    )
    log.info(
        "tender_worker_inproc_started",
        worker_id=worker_id,
        concurrency=max(1, settings.tender_worker_concurrency),
    )
    return InProcessTenderWorker(
        shutdown_event=shutdown_event,
        task=task,
        worker_id=worker_id,
    )


async def stop_inprocess_tender_worker(
    handle: InProcessTenderWorker | None,
    *,
    timeout_seconds: float = 10.0,
) -> None:
    if handle is None:
        return

    handle.shutdown_event.set()
    try:
        await asyncio.wait_for(handle.task, timeout=timeout_seconds)
    except TimeoutError:
        handle.task.cancel()
        with suppress(asyncio.CancelledError):
            await handle.task
    log.info("tender_worker_inproc_stopped", worker_id=handle.worker_id)
