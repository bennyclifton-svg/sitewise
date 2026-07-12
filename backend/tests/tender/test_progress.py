from __future__ import annotations

import uuid

from tender.services.progress import (
    JobFacts,
    compute_milestones,
    progress_percent,
)

QUOTE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _facts(*specs: tuple[str, str]) -> list[JobFacts]:
    return [
        JobFacts(kind=kind, quote_id=QUOTE_ID, status=status, last_error=None)
        for kind, status in specs
    ]


def _states(milestones) -> dict[str, str]:
    return {m.key: m.state for m in milestones}


def test_fresh_comparison_is_all_pending() -> None:
    milestones = compute_milestones(
        comparison_status="intake",
        job_facts=[],
        dead_documents=[],
        qa_pending=0,
        has_report=False,
    )
    assert _states(milestones) == {
        "ingest": "pending",
        "extract": "pending",
        "map": "pending",
        "analyse": "pending",
        "review": "pending",
        "report": "pending",
    }
    assert progress_percent(milestones) == 0


def test_running_ingest_shows_running() -> None:
    milestones = compute_milestones(
        comparison_status="processing",
        job_facts=_facts(("ingest_document", "running")),
        dead_documents=[],
        qa_pending=0,
        has_report=False,
    )
    assert _states(milestones)["ingest"] == "running"


def test_unsupported_document_fails_ingest_even_when_job_done() -> None:
    milestones = compute_milestones(
        comparison_status="intake",
        job_facts=_facts(("ingest_document", "done")),
        dead_documents=["quote.md"],
        qa_pending=0,
        has_report=False,
    )
    ingest = milestones[0]
    assert ingest.state == "failed"
    assert "quote.md" in (ingest.detail or "")


def test_failed_map_job_marks_map_failed() -> None:
    milestones = compute_milestones(
        comparison_status="processing",
        job_facts=_facts(
            ("ingest_document", "done"),
            ("classify_document", "done"),
            ("extract_line_items", "done"),
            ("embed_items", "done"),
            ("map_items", "failed"),
        ),
        dead_documents=[],
        qa_pending=0,
        has_report=False,
    )
    states = _states(milestones)
    assert states["ingest"] == "done"
    assert states["extract"] == "done"
    assert states["map"] == "failed"
    assert states["analyse"] == "pending"


def test_complete_pipeline_with_qa_pending_needs_attention() -> None:
    milestones = compute_milestones(
        comparison_status="qa",
        job_facts=_facts(
            ("ingest_document", "done"),
            ("classify_document", "done"),
            ("extract_line_items", "done"),
            ("embed_items", "done"),
            ("map_items", "done"),
            ("run_expectations", "done"),
            ("infer_silence_batch", "done"),
            ("run_analysis", "done"),
            ("generate_flags", "done"),
        ),
        dead_documents=[],
        qa_pending=103,
        has_report=False,
    )
    states = _states(milestones)
    assert states["analyse"] == "done"
    assert states["review"] == "attention"
    assert states["report"] == "pending"
    review = next(m for m in milestones if m.key == "review")
    assert "103" in (review.detail or "")


def test_qa_clear_marks_review_done_and_report_ready() -> None:
    milestones = compute_milestones(
        comparison_status="processing",
        job_facts=_facts(
            ("ingest_document", "done"),
            ("classify_document", "done"),
            ("extract_line_items", "done"),
            ("embed_items", "done"),
            ("map_items", "done"),
            ("run_expectations", "done"),
            ("infer_silence_batch", "done"),
            ("run_analysis", "done"),
            ("generate_flags", "done"),
        ),
        dead_documents=[],
        qa_pending=0,
        has_report=False,
    )
    states = _states(milestones)
    assert states["review"] == "done"
    assert states["report"] == "attention"


def test_report_built_is_fully_done() -> None:
    milestones = compute_milestones(
        comparison_status="report_draft",
        job_facts=_facts(
            ("ingest_document", "done"),
            ("classify_document", "done"),
            ("extract_line_items", "done"),
            ("embed_items", "done"),
            ("map_items", "done"),
            ("run_expectations", "done"),
            ("infer_silence_batch", "done"),
            ("run_analysis", "done"),
            ("generate_flags", "done"),
        ),
        dead_documents=[],
        qa_pending=0,
        has_report=True,
    )
    assert all(m.state == "done" for m in milestones), _states(milestones)
    assert progress_percent(milestones) == 100
