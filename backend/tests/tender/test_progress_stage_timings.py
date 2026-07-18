"""Packet A2: progress API includes stage timing ledger."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock

from tender.schemas import ComparisonProgressResponse
from tender.services import progress, telemetry
from tests.conftest import run_async


class _Result:
    def scalars(self) -> "_Result":
        return self

    def all(self) -> list[Any]:
        return []

    def scalar_one(self) -> int:
        return 0


def test_comparison_progress_includes_stage_timings(monkeypatch) -> None:
    comparison_id = uuid.uuid4()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_Result())

    monkeypatch.setattr(
        progress.qa,
        "review_queue_statement",
        lambda _comparison_id: object(),
    )
    monkeypatch.setattr(
        telemetry,
        "list_stage_timings",
        AsyncMock(
            return_value=[
                telemetry.StageTiming(
                    stage="map_items",
                    duration_ms=1500,
                    status="done",
                    llm_calls=4,
                    input_tokens=800,
                    output_tokens=90,
                    metadata={"tiers": {"t0": 3, "t2": 1}},
                )
            ]
        ),
    )

    response = run_async(
        progress.comparison_progress(
            session,
            comparison_id=comparison_id,
            comparison_status="processing",
        )
    )

    assert isinstance(response, ComparisonProgressResponse)
    assert len(response.stage_timings) == 1
    timing = response.stage_timings[0]
    assert timing.stage == "map_items"
    assert timing.llm_calls == 4
    assert timing.input_tokens == 800
    assert timing.output_tokens == 90
    assert timing.metadata["tiers"]["t0"] == 3
