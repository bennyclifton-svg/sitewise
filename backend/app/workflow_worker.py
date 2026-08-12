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
from app.workflows.worker import run_pool

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class InProcessWorkflowWorker:
    shutdown_event: asyncio.Event
    task: asyncio.Task[None]
    worker_id: str


async def start_inprocess_workflow_worker(
    *, session_factory: Any | None = None
) -> InProcessWorkflowWorker | None:
    if not settings.workflow_worker_inproc_enabled:
        return None
    shutdown_event = asyncio.Event()
    # The scope leads the worker id so `lock_owner` shows which environment
    # claimed a run without joining back to the queue scope column.
    worker_id = (
        f"{settings.workflow_queue_scope}:inproc-core:"
        f"{socket.gethostname()}:{os.getpid()}"
    )
    log.info(
        "workflow_worker_inproc_started",
        worker_id=worker_id,
        queue_scope=settings.workflow_queue_scope,
    )
    task = asyncio.create_task(
        run_pool(
            session_factory or get_session_factory(),
            worker_id,
            shutdown_event=shutdown_event,
            concurrency=settings.workflow_worker_concurrency,
        ),
        name="core-workflow-worker-inproc",
    )
    return InProcessWorkflowWorker(shutdown_event, task, worker_id)


async def stop_inprocess_workflow_worker(
    handle: InProcessWorkflowWorker | None, *, timeout_seconds: float = 15.0
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
    log.info("workflow_worker_inproc_stopped", worker_id=handle.worker_id)
