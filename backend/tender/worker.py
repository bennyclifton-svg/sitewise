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
import time
import traceback
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

import app.database.models  # noqa: F401 — register all SQLAlchemy mappers before any query
from app.config import settings
from app.logging import configure_logging, get_logger
from tender.models import TenderJob
from tender.services import continuations, jobs, telemetry
from tender.services.analysis import generate_flags, run_analysis
from tender.services.classification import classify_document
from tender.services.embedding import embed_items
from tender.services.expectations import run_expectations
from tender.services.extraction_handler import extract_line_items_job
from tender.services.ingestion import ingest_document
from tender.services.mapping import map_items
from tender.services.report import assemble_report_draft
from tender.services.silence import infer_silence, infer_silence_batch

log = get_logger(__name__)

Handler = Callable[[AsyncSession, TenderJob], Awaitable[None]]

HANDLERS: dict[str, Handler] = {
    "ingest_document": ingest_document,
    "classify_document": classify_document,
    "extract_line_items": extract_line_items_job,
    "embed_items": embed_items,
    "map_items": map_items,
    "infer_silence": infer_silence,
    "infer_silence_batch": infer_silence_batch,
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
            await telemetry.record_stage_timing(
                session,
                comparison_id=job.comparison_id,
                job_id=job.id,
                stage=job.kind,
                duration_ms=0,
                status="failed",
                metadata={"error": "unknown job kind"},
            )
            await jobs.fail(
                session,
                job,
                f"unknown job kind: {job.kind!r} (registered: {sorted(HANDLERS)})",
            )
            return True

        job_id = job.id
        job_kind = job.kind
        comparison_id = job.comparison_id
        started = time.perf_counter()
        usage = telemetry.begin_stage_usage()
        try:
            await handler(session, job)
        except Exception:
            error_text = traceback.format_exc()
            duration_ms = int((time.perf_counter() - started) * 1000)
            await session.rollback()
            failed_meta = dict(usage.metadata)
            failed_meta["error"] = (
                error_text.splitlines()[-1] if error_text else ""
            )
            await telemetry.record_stage_timing(
                session,
                comparison_id=comparison_id,
                job_id=job_id,
                stage=job_kind,
                duration_ms=duration_ms,
                status="failed",
                llm_calls=usage.llm_calls,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_hits=usage.cache_hits,
                metadata=failed_meta,
            )
            await jobs.fail(session, job, error_text)
            return True
        finally:
            telemetry.end_stage_usage()

        duration_ms = int((time.perf_counter() - started) * 1000)
        await telemetry.record_stage_timing(
            session,
            comparison_id=comparison_id,
            job_id=job_id,
            stage=job_kind,
            duration_ms=duration_ms,
            status="done",
            llm_calls=usage.llm_calls,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_hits=usage.cache_hits,
            metadata=usage.metadata or None,
        )
        await jobs.complete(session, job)
        await continuations.after_job_complete(
            session,
            job_id=job_id,
            job_kind=job_kind,
            comparison_id=comparison_id,
        )
        return True


async def _idle_wait(shutdown_event: asyncio.Event) -> None:
    """Sleep one poll interval, but wake immediately on shutdown."""

    try:
        await asyncio.wait_for(
            shutdown_event.wait(), timeout=settings.tender_worker_poll_seconds
        )
    except TimeoutError:
        pass


async def run_lane(
    session_factory,
    worker_id: str,
    *,
    shutdown_event: asyncio.Event,
) -> None:
    """One processing lane: claim and run jobs until shutdown.

    The lane is self-healing — a transient error from claiming or completing
    a job (a DB blip, say) is logged and the lane backs off one poll interval
    rather than dying, so a single hiccup never drains the pool. Per-job
    handler failures are already absorbed by ``run_once``/``jobs.fail``.
    """

    while not shutdown_event.is_set():
        try:
            processed = await run_once(session_factory, worker_id)
        except Exception:
            log.error(
                "tender_worker_lane_error",
                worker_id=worker_id,
                error=traceback.format_exc(),
            )
            await _idle_wait(shutdown_event)
            continue

        if not processed and not shutdown_event.is_set():
            await _idle_wait(shutdown_event)

    log.info("tender_worker_lane_stopped", worker_id=worker_id)


async def run_sweeper(
    session_factory,
    *,
    shutdown_event: asyncio.Event,
) -> None:
    """Periodically return jobs stranded ``running`` by a crashed worker."""

    while not shutdown_event.is_set():
        try:
            async with session_factory() as session:
                await jobs.requeue_stale(
                    session, older_than_minutes=settings.tender_job_stale_lock_minutes
                )
        except Exception:
            log.error("tender_worker_sweeper_error", error=traceback.format_exc())

        if not shutdown_event.is_set():
            await _idle_wait(shutdown_event)

    log.info("tender_worker_sweeper_stopped")


async def run_pool(
    session_factory,
    worker_id: str,
    *,
    shutdown_event: asyncio.Event,
    concurrency: int,
) -> None:
    """Run ``concurrency`` lanes plus one stale-lock sweeper concurrently.

    Lanes pull distinct jobs via ``SELECT … FOR UPDATE SKIP LOCKED`` so the
    only speedup limit is the OpenAI rate ceiling, not local CPU. All tasks
    share the shutdown event and drain together on SIGINT/SIGTERM.
    """

    lanes = max(1, concurrency)
    tasks = [
        asyncio.create_task(
            run_sweeper(session_factory, shutdown_event=shutdown_event)
        ),
        *(
            asyncio.create_task(
                run_lane(
                    session_factory,
                    f"{worker_id}#{index}",
                    shutdown_event=shutdown_event,
                )
            )
            for index in range(lanes)
        ),
    ]
    await asyncio.gather(*tasks)


async def run_loop(
    session_factory,
    worker_id: str,
    *,
    shutdown_event: asyncio.Event,
) -> None:
    """Single-lane loop with an inline stale-lock sweep (used by tests).

    ``run_pool`` is the production entrypoint; this remains the simplest
    serial driver for one worker.
    """

    while not shutdown_event.is_set():
        async with session_factory() as session:
            await jobs.requeue_stale(
                session, older_than_minutes=settings.tender_job_stale_lock_minutes
            )

        processed = await run_once(session_factory, worker_id)

        if not processed and not shutdown_event.is_set():
            await _idle_wait(shutdown_event)

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

    concurrency = max(1, settings.tender_worker_concurrency)
    log.info(
        "tender_worker_started",
        worker_id=worker_id,
        poll_seconds=settings.tender_worker_poll_seconds,
        concurrency=concurrency,
        handlers=sorted(HANDLERS),
    )
    print(
        f"Tender worker ready | {worker_id} | lanes={concurrency} | "
        f"handlers={sorted(HANDLERS)}",
        flush=True,
    )

    await run_pool(
        get_session_factory(),
        worker_id,
        shutdown_event=shutdown_event,
        concurrency=concurrency,
    )


if __name__ == "__main__":
    import sys

    if sys.platform == "win32":
        # psycopg async cannot run on the default ProactorEventLoop.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
