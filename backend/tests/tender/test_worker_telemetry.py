"""Packet A2: worker records LLM usage from stage context."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from unittest.mock import ANY, AsyncMock, patch

from tender import worker
from tender.models import TenderJob
from tender.services import telemetry
from tests.conftest import run_async


def test_run_once_records_llm_usage_from_handler() -> None:
    mock_session = AsyncMock()
    job = TenderJob(
        id=uuid.uuid4(),
        kind="extract_line_items",
        comparison_id=uuid.uuid4(),
        payload={},
        status="running",
        attempts=0,
    )

    async def handler(session, job_arg) -> None:
        telemetry.record_llm_usage(input_tokens=40, output_tokens=12, cache_hits=2)
        telemetry.record_mapping_tier("t2", duration_ms=25)

    async def _run() -> None:
        with (
            patch.object(worker.jobs, "claim_next", new=AsyncMock(return_value=job)),
            patch.object(worker.jobs, "complete", new=AsyncMock()),
            patch.object(
                worker.telemetry, "record_stage_timing", new=AsyncMock()
            ) as mock_timing,
            patch.object(
                worker, "continuations", new=AsyncMock(after_job_complete=AsyncMock())
            ),
            patch.dict(worker.HANDLERS, {"extract_line_items": handler}),
        ):
            processed = await worker.run_once(_session_factory(mock_session), "host:1")

        assert processed is True
        mock_timing.assert_awaited_once_with(
            mock_session,
            comparison_id=job.comparison_id,
            job_id=job.id,
            stage="extract_line_items",
            duration_ms=ANY,
            status="done",
            llm_calls=1,
            input_tokens=40,
            output_tokens=12,
            cache_hits=2,
            metadata={
                "tiers": {
                    "t0": 0,
                    "t1": 0,
                    "t2": 1,
                    "t3": 0,
                    "t0_ms": 0,
                    "t1_ms": 0,
                    "t2_ms": 25,
                    "t3_ms": 0,
                }
            },
        )

    run_async(_run())


def _session_factory(session: AsyncMock):
    @asynccontextmanager
    async def factory():
        yield session

    return factory
