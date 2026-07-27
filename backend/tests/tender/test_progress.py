from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

from tender.schemas import ComparisonProgressResponse
from tender.services import telemetry
from tender.services.progress import (
    JobFacts,
    comparison_progress,
    compute_milestones,
    progress_percent,
)
from tests.conftest import run_async

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


def test_comparison_progress_includes_stage_timings(monkeypatch) -> None:
    comparison_id = uuid.uuid4()

    class _EmptyScalars:
        def all(self):
            return []

    class _EmptyResult:
        def scalars(self):
            return _EmptyScalars()

        def all(self):
            return []

        def scalar_one(self):
            return 0

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_EmptyResult())
    monkeypatch.setattr(
        telemetry,
        "list_stage_timings",
        AsyncMock(
            return_value=[
                telemetry.StageTiming(
                    stage="map_items",
                    duration_ms=1200,
                    status="done",
                    llm_calls=3,
                    input_tokens=900,
                    output_tokens=120,
                    metadata={"tier_counts": {"t2": 3}},
                )
            ]
        ),
    )

    response = run_async(
        comparison_progress(
            session,
            comparison_id=comparison_id,
            comparison_status="processing",
        )
    )

    assert isinstance(response, ComparisonProgressResponse)
    assert len(response.stage_timings) == 1
    timing = response.stage_timings[0]
    assert timing.stage == "map_items"
    assert timing.duration_ms == 1200
    assert timing.llm_calls == 3
    assert timing.input_tokens == 900
    assert timing.output_tokens == 120
    assert timing.metadata == {"tier_counts": {"t2": 3}}
