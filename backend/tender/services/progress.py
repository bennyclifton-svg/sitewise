"""Pipeline progress reporting and one-button processing for a comparison.

The overview UI needs a single, continuously-pollable answer to "where is my
comparison up to?". Progress is derived from ``tender_jobs`` (the queue is the
source of truth for what ran), document ingest statuses (ingest failures are
recorded on the document, not the job), the QA queue, and comparison status.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import TenderDocument, TenderJob, TenderQuote, TenderReport
from tender.schemas import (
    ComparisonProgressResponse,
    ProcessComparisonResponse,
    ProgressDocument,
    ProgressMilestone,
    ProgressQuote,
    StageTimingView,
)
from tender.services import jobs, qa, telemetry

INGEST_KINDS = frozenset({"ingest_document"})
EXTRACT_KINDS = frozenset({"classify_document", "extract_line_items", "embed_items"})
MAP_KINDS = frozenset({"map_items"})
ANALYSE_KINDS = frozenset(
    {
        "run_expectations",
        "infer_silence",
        "infer_silence_batch",
        "run_analysis",
        "generate_flags",
    }
)

MILESTONE_LABELS = {
    "ingest": "Read documents",
    "extract": "Extract line items",
    "map": "Map to cost categories",
    "analyse": "Analyse & compare",
    "review": "Review findings",
    "report": "Report",
}

RUNNING_DETAIL = {
    "ingest": "Reading quote documents",
    "extract": "Extracting priced line items",
    "map": "Mapping items to the cost taxonomy",
    "analyse": "Comparing scope, gaps and allowances",
}

# Documents in these states will never progress without a different file.
DEAD_INGEST_STATUSES = frozenset({"unsupported_format", "duplicate"})


@dataclass(frozen=True, slots=True)
class JobFacts:
    """Latest job per (kind, quote_id) plus terminal error text."""

    kind: str
    quote_id: uuid.UUID | None
    status: str
    last_error: str | None


def _latest_jobs(rows: list[TenderJob]) -> list[JobFacts]:
    latest: dict[tuple[str, uuid.UUID | None], TenderJob] = {}
    for row in rows:
        key = (row.kind, row.quote_id)
        current = latest.get(key)
        if current is None or row.created_at > current.created_at:
            latest[key] = row
    return [
        JobFacts(
            kind=row.kind,
            quote_id=row.quote_id,
            status=row.status,
            last_error=row.last_error,
        )
        for row in latest.values()
    ]


def _error_summary(error: str | None) -> str | None:
    if not error:
        return None
    lines = [line.strip() for line in error.splitlines() if line.strip()]
    return lines[-1][:300] if lines else None


def _group_state(facts: list[JobFacts], kinds: frozenset[str]) -> tuple[str, str | None]:
    """Return (state, detail) for one milestone from its latest jobs."""

    group = [fact for fact in facts if fact.kind in kinds]
    if not group:
        return "pending", None

    failed = [fact for fact in group if fact.status == "failed"]
    if failed:
        return "failed", _error_summary(failed[0].last_error)
    if any(fact.status in {"queued", "running"} for fact in group):
        return "running", None
    if all(fact.status == "done" for fact in group):
        return "done", None
    return "running", None


def compute_milestones(
    *,
    comparison_status: str,
    job_facts: list[JobFacts],
    dead_documents: list[str],
    qa_pending: int,
    has_report: bool,
) -> list[ProgressMilestone]:
    milestones: list[ProgressMilestone] = []

    ingest_state, ingest_detail = _group_state(job_facts, INGEST_KINDS)
    if dead_documents:
        joined = ", ".join(dead_documents[:3])
        ingest_state = "failed"
        ingest_detail = f"Cannot read: {joined}. Attach PDF or DOCX versions."
    milestones.append(_milestone("ingest", ingest_state, ingest_detail))

    for key, kinds in (("extract", EXTRACT_KINDS), ("map", MAP_KINDS), ("analyse", ANALYSE_KINDS)):
        state, detail = _group_state(job_facts, kinds)
        milestones.append(_milestone(key, state, detail))

    analyse_done = milestones[-1].state == "done"
    if not analyse_done:
        review_state, review_detail = "pending", None
    elif qa_pending > 0:
        review_state = "attention"
        review_detail = f"{qa_pending} item{'s' if qa_pending != 1 else ''} need your review"
    else:
        review_state, review_detail = "done", None
    milestones.append(_milestone("review", review_state, review_detail))

    if has_report or comparison_status in {"report_draft", "approved", "delivered"}:
        report_state, report_detail = "done", None
    elif review_state == "done":
        report_state, report_detail = "attention", "Ready to build"
    else:
        report_state, report_detail = "pending", None
    milestones.append(_milestone("report", report_state, report_detail))

    return milestones


def _milestone(key: str, state: str, detail: str | None) -> ProgressMilestone:
    if detail is None and state == "running":
        detail = RUNNING_DETAIL.get(key)
    return ProgressMilestone(
        key=key,
        label=MILESTONE_LABELS[key],
        state=state,
        detail=detail,
    )


def progress_percent(milestones: list[ProgressMilestone]) -> int:
    if not milestones:
        return 0
    score = 0.0
    for milestone in milestones:
        if milestone.state == "done":
            score += 1.0
        elif milestone.state in {"running", "attention"}:
            score += 0.5
    return int(round(100 * score / len(milestones)))


async def comparison_progress(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    comparison_status: str,
) -> ComparisonProgressResponse:
    quotes_result = await session.execute(
        select(TenderQuote)
        .where(TenderQuote.comparison_id == comparison_id)
        .order_by(TenderQuote.created_at)
    )
    quotes = list(quotes_result.scalars().all())

    documents_result = await session.execute(
        select(TenderDocument)
        .join(TenderQuote, TenderQuote.id == TenderDocument.quote_id)
        .where(TenderQuote.comparison_id == comparison_id)
    )
    documents = list(documents_result.scalars().all())

    jobs_result = await session.execute(
        select(TenderJob).where(TenderJob.comparison_id == comparison_id)
    )
    job_facts = _latest_jobs(list(jobs_result.scalars().all()))

    qa_pending = len(
        (await session.execute(qa.review_queue_statement(comparison_id))).all()
    )

    has_report = (
        await session.execute(
            select(func.count())
            .select_from(TenderReport)
            .where(TenderReport.comparison_id == comparison_id)
        )
    ).scalar_one() > 0

    dead_documents = [
        document.original_filename
        for document in documents
        if document.ingest_status in DEAD_INGEST_STATUSES
    ]

    milestones = compute_milestones(
        comparison_status=comparison_status,
        job_facts=job_facts,
        dead_documents=dead_documents,
        qa_pending=qa_pending,
        has_report=has_report,
    )

    documents_by_quote: dict[uuid.UUID, list[ProgressDocument]] = {}
    for document in documents:
        documents_by_quote.setdefault(document.quote_id, []).append(
            ProgressDocument(
                filename=document.original_filename,
                ingest_status=document.ingest_status,
            )
        )

    is_processing = any(milestone.state == "running" for milestone in milestones)
    stage_timings = [
        StageTimingView(
            stage=row.stage,
            duration_ms=row.duration_ms,
            status=row.status,
            llm_calls=row.llm_calls,
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            cache_hits=row.cache_hits,
            metadata=row.metadata or {},
        )
        for row in await telemetry.list_stage_timings(
            session, comparison_id=comparison_id
        )
    ]

    return ComparisonProgressResponse(
        comparison_id=comparison_id,
        status=comparison_status,
        percent=progress_percent(milestones),
        is_processing=is_processing,
        qa_pending=qa_pending,
        milestones=milestones,
        quotes=[
            ProgressQuote(
                quote_id=quote.id,
                builder_name=quote.builder_name,
                stage=quote.stage,
                stated_total_cents=quote.stated_total_cents,
                documents=documents_by_quote.get(quote.id, []),
            )
            for quote in quotes
        ],
        stage_timings=stage_timings,
    )


async def process_comparison(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> ProcessComparisonResponse:
    """Enqueue whatever each quote needs next: retry failures, start ingests.

    Idempotent from the user's point of view: pressing the button while jobs
    are already queued or running enqueues nothing.
    """

    jobs_result = await session.execute(
        select(TenderJob).where(TenderJob.comparison_id == comparison_id)
    )
    job_rows = list(jobs_result.scalars().all())
    job_facts = _latest_jobs(job_rows)

    if any(fact.status in {"queued", "running"} for fact in job_facts):
        return ProcessComparisonResponse(queued=[], notes=["Processing is already running."])

    documents_result = await session.execute(
        select(TenderDocument)
        .join(TenderQuote, TenderQuote.id == TenderDocument.quote_id)
        .where(TenderQuote.comparison_id == comparison_id)
    )
    documents = list(documents_result.scalars().all())

    queued: list[TenderJob] = []
    notes: list[str] = []

    # Retry the most recent failed job of each (kind, quote) with its payload.
    failed_keys = {
        (fact.kind, fact.quote_id) for fact in job_facts if fact.status == "failed"
    }
    if failed_keys:
        latest_rows: dict[tuple[str, uuid.UUID | None], TenderJob] = {}
        for row in job_rows:
            key = (row.kind, row.quote_id)
            if key in failed_keys:
                current = latest_rows.get(key)
                if current is None or row.created_at > current.created_at:
                    latest_rows[key] = row
        for row in latest_rows.values():
            queued.append(
                await jobs.enqueue(
                    session,
                    kind=row.kind,
                    comparison_id=comparison_id,
                    quote_id=row.quote_id,
                    payload=row.payload,
                )
            )

    # Start ingestion for documents that never got a job (or stayed pending).
    ingested_document_ids = {
        str(row.payload.get("document_id"))
        for row in job_rows
        if row.kind == "ingest_document" and row.payload
    }
    for document in documents:
        if document.ingest_status in DEAD_INGEST_STATUSES:
            notes.append(
                f"{document.original_filename}: unsupported format - attach a PDF or DOCX version."
            )
            continue
        if document.ingest_status == "pending" and str(document.id) not in ingested_document_ids:
            queued.append(
                await jobs.enqueue(
                    session,
                    kind="ingest_document",
                    comparison_id=comparison_id,
                    quote_id=document.quote_id,
                    payload={"document_id": str(document.id)},
                )
            )

    if not queued and not notes:
        notes.append("Nothing to do - processing is complete.")

    await session.flush()
    return ProcessComparisonResponse(queued=queued, notes=notes)
