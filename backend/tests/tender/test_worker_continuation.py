import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from tender.models import TenderJob
from tender.services import analysis, continuations, embedding, mapping, qa
from tender.services.analysis import AnalysisResult
from tests.conftest import run_async


def test_embed_items_queues_mapping_stage(monkeypatch) -> None:
    quote_id = uuid.uuid4()
    comparison_id = uuid.uuid4()
    quote = SimpleNamespace(stage="embed_items")
    session = AsyncMock()
    session.get = AsyncMock(return_value=quote)
    enqueue = AsyncMock()

    monkeypatch.setattr(embedding, "embed_line_items", AsyncMock(return_value=0))
    monkeypatch.setattr(embedding.jobs, "enqueue", enqueue)

    async def _run() -> None:
        await embedding.embed_items(
            session,
            TenderJob(
                kind="embed_items",
                comparison_id=comparison_id,
                quote_id=quote_id,
                payload={},
            ),
        )

    run_async(_run())

    assert quote.stage == "map_items"
    enqueue.assert_awaited_once_with(
        session,
        kind="map_items",
        comparison_id=comparison_id,
        quote_id=quote_id,
        payload={"reason": "embedding_complete"},
    )


def test_map_items_marks_quote_ready_for_expectations(monkeypatch) -> None:
    quote_id = uuid.uuid4()
    comparison_id = uuid.uuid4()
    quote = SimpleNamespace(stage="map_items", comparison_id=comparison_id)
    session = AsyncMock()
    session.get = AsyncMock(return_value=quote)

    class _Result:
        def scalars(self):
            return iter(())

    session.execute = AsyncMock(return_value=_Result())
    monkeypatch.setattr(
        mapping,
        "_context_for_quote",
        AsyncMock(return_value=object()),
    )

    async def _run() -> None:
        await mapping.map_items(
            session,
            TenderJob(
                kind="map_items",
                comparison_id=comparison_id,
                quote_id=quote_id,
                payload={},
            ),
        )

    run_async(_run())

    assert quote.stage == "run_expectations"


def test_completed_map_items_queues_expectations_after_barrier(monkeypatch) -> None:
    comparison_id = uuid.uuid4()
    session = AsyncMock()
    enqueue = AsyncMock()

    monkeypatch.setattr(
        continuations,
        "_has_active_jobs",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        continuations,
        "_all_quotes_ready_for_expectations",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        continuations,
        "_has_existing_job",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(continuations.jobs, "enqueue", enqueue)

    async def _run() -> None:
        await continuations.after_job_complete(
            session,
            job_id=uuid.uuid4(),
            job_kind="map_items",
            comparison_id=comparison_id,
        )

    run_async(_run())

    enqueue.assert_awaited_once_with(
        session,
        kind="run_expectations",
        comparison_id=comparison_id,
        payload={"reason": "all_quotes_mapped"},
    )
    session.commit.assert_awaited_once()


def test_completed_map_items_waits_for_remaining_mapping_jobs(monkeypatch) -> None:
    comparison_id = uuid.uuid4()
    session = AsyncMock()
    enqueue = AsyncMock()

    monkeypatch.setattr(
        continuations,
        "_has_active_jobs",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(continuations.jobs, "enqueue", enqueue)

    async def _run() -> None:
        await continuations.after_job_complete(
            session,
            job_id=uuid.uuid4(),
            job_kind="map_items",
            comparison_id=comparison_id,
        )

    run_async(_run())

    enqueue.assert_not_awaited()


def test_completed_infer_silence_queues_analysis_after_barrier(monkeypatch) -> None:
    comparison_id = uuid.uuid4()
    session = AsyncMock()
    enqueue = AsyncMock()

    monkeypatch.setattr(
        continuations,
        "_has_active_jobs",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        continuations,
        "_has_existing_job",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(continuations.jobs, "enqueue", enqueue)

    async def _run() -> None:
        await continuations.after_job_complete(
            session,
            job_id=uuid.uuid4(),
            job_kind="infer_silence",
            comparison_id=comparison_id,
        )

    run_async(_run())

    enqueue.assert_awaited_once_with(
        session,
        kind="run_analysis",
        comparison_id=comparison_id,
        payload={"reason": "all_silence_complete"},
    )
    session.commit.assert_awaited_once()


def test_generate_flags_queues_report_when_qa_is_clear(monkeypatch) -> None:
    comparison_id = uuid.uuid4()
    comparison = SimpleNamespace(status="processing")
    session = AsyncMock()
    enqueue = AsyncMock()

    monkeypatch.setattr(
        analysis,
        "_analysis_inputs",
        AsyncMock(
            return_value={
                "context": object(),
                "quotes": [],
                "cells": [],
                "statuses": [],
                "benchmarks": [],
            }
        ),
    )
    monkeypatch.setattr(
        analysis,
        "analyse_comparison",
        lambda **_kwargs: AnalysisResult(version=1, gap_matrix=(), ledgers=()),
    )
    monkeypatch.setattr(analysis, "generate_analysis_flags", lambda **_kwargs: [])
    monkeypatch.setattr(analysis, "_replace_generated_flags", AsyncMock(return_value=[]))
    monkeypatch.setattr(analysis, "_question_templates", AsyncMock(return_value={}))
    monkeypatch.setattr(analysis, "_upsert_analysis_result", AsyncMock())
    monkeypatch.setattr(analysis, "_comparison", AsyncMock(return_value=comparison))
    monkeypatch.setattr(qa, "assert_no_pending_review", AsyncMock())
    monkeypatch.setattr(analysis.jobs, "enqueue", enqueue)

    async def _run() -> None:
        await analysis.generate_flags(
            session,
            TenderJob(
                kind="generate_flags",
                comparison_id=comparison_id,
                payload={},
            ),
        )

    run_async(_run())

    assert comparison.status == "processing"
    enqueue.assert_awaited_once_with(
        session,
        kind="assemble_report_draft",
        comparison_id=comparison_id,
        payload={"reason": "qa_clear"},
    )
