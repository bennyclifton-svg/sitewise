"""Tender job worker: poll loop over tender_jobs (PRD §7.3).

Run as a separate process with ``python -m tender.worker`` (same image as
the API). Claims one job at a time with SKIP LOCKED, dispatches by ``kind``
through the handler registry, and sweeps stale locks each poll cycle so a
crashed worker never strands jobs in ``running``.
"""

from __future__ import annotations

import asyncio
import os
import signal
import socket
import traceback
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.logging import configure_logging, get_logger
from tender.models import TenderJob
from tender.services import jobs
from tender.services.analysis import generate_flags, run_analysis
from tender.services.embedding import embed_items
from tender.services.expectations import run_expectations
from tender.services.ingestion import ingest_document
from tender.services.mapping import map_items
from tender.services.report import assemble_report_draft
from tender.services.silence import infer_silence

log = get_logger(__name__)

Handler = Callable[[AsyncSession, TenderJob], Awaitable[None]]

HANDLERS: dict[str, Handler] = {
    "embed_items": embed_items,
    "ingest_document": ingest_document,
    "infer_silence": infer_silence,
    "map_items": map_items,
    "assemble_report_draft": assemble_report_draft,
    "generate_flags": generate_flags,
    "run_analysis": run_analysis,
    "run_expectations": run_expectations,
}


async def run_once(session_factory, worker_id: str) -> bool:
    """Claim and process at most one job; return whether one was processed."""

    async with session_factory() as session:
        job = await jobs.claim_next(session, worker_id=worker_id)
        if job is None:
            return False

        handler = HANDLERS.get(job.kind)
        if handler is None:
            await jobs.fail(
                session,
                job,
                f"unknown job kind: {job.kind!r} (registered: {sorted(HANDLERS)})",
            )
            return True

        try:
            await handler(session, job)
        except Exception:
            await session.rollback()
            await jobs.fail(session, job, traceback.format_exc())
            return True

        await jobs.complete(session, job)
        return True


async def run_loop(
    session_factory,
    worker_id: str,
    *,
    shutdown_event: asyncio.Event,
) -> None:
    """Poll until shutdown; the in-flight job always finishes before exit."""

    while not shutdown_event.is_set():
        async with session_factory() as session:
            await jobs.requeue_stale(
                session, older_than_minutes=settings.tender_job_stale_lock_minutes
            )

        processed = await run_once(session_factory, worker_id)

        if not processed and not shutdown_event.is_set():
            try:
                await asyncio.wait_for(
                    shutdown_event.wait(), timeout=settings.tender_worker_poll_seconds
                )
            except TimeoutError:
                pass

    log.info("tender_worker_stopped", worker_id=worker_id)


def _install_signal_handlers(shutdown_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown_event.set)
        except NotImplementedError:
            # Windows event loops don't support add_signal_handler.
            signal.signal(sig, lambda signum, frame: shutdown_event.set())


async def main() -> None:
    configure_logging()
    from app.database.session import get_session_factory

    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    shutdown_event = asyncio.Event()
    _install_signal_handlers(shutdown_event)

    log.info(
        "tender_worker_started",
        worker_id=worker_id,
        poll_seconds=settings.tender_worker_poll_seconds,
        handlers=sorted(HANDLERS),
    )
    print(f"Tender worker ready | {worker_id} | handlers={sorted(HANDLERS)}", flush=True)

    await run_loop(get_session_factory(), worker_id, shutdown_event=shutdown_event)


if __name__ == "__main__":
    import sys

    if sys.platform == "win32":
        # psycopg async cannot run on the default ProactorEventLoop.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
