"""Progress comes only from saved page coverage and live queue state."""

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any

from tender.models import TenderJob


def _live(job: TenderJob, now: datetime) -> bool:
    # Workers renew at least every 30 seconds. A missing heartbeat is waiting,
    # not evidence that reading continues or that the entire review has failed.
    return bool(
        job.status == "running"
        and job.locked_at
        and job.locked_at > now - timedelta(seconds=90)
    )


def review_activity(jobs: Sequence[TenderJob], *, now: datetime) -> str:
    if any(_live(job, now) for job in jobs):
        return "running"
    if any(job.status == "queued" and job.attempts for job in jobs):
        return "retrying"
    if any(job.status == "queued" for job in jobs):
        return "queued"
    return "waiting"


def document_progress(
    document: Mapping[str, Any], jobs: Sequence[TenderJob], *, now: datetime
) -> dict[str, Any]:
    related = [
        job
        for job in jobs
        if str((job.payload or {}).get("document_id")) == str(document["id"])
    ]
    complete = bool(document["complete"])
    pages = document["pages"]
    read = {
        page
        for page in document["read_pages"] or []
        if isinstance(page, int) and 0 < page <= (pages or 0)
    }
    running = next((job for job in related if _live(job, now)), None)
    state = (
        "complete"
        if complete
        else "failed"
        if any(job.status == "failed" for job in related)
        else "opening"
        if running and running.kind == "ingest_document"
        else "reading"
        if running
        else review_activity(related, now=now)
    )
    return {
        "id": str(document["id"]),
        "filename": document["filename"],
        "firm_name": document["firm_name"],
        "pages": pages,
        "pages_read": len(read),
        "complete": complete,
        "state": state,
    }
