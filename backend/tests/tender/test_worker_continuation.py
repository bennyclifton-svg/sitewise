import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from tender.models import TenderJob
from tender.services import analysis, embedding, qa
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
