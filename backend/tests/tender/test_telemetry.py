import uuid
from types import SimpleNamespace
from typing import Any

from tender.models import TenderTelemetryEvent
from tender.services import telemetry
from tests.conftest import run_async


class _ScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        return self._values


class _ExecuteResult:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._values)


class _Session:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, item: Any) -> None:
        self.added.append(item)

    async def flush(self) -> None:
        return None

    async def execute(self, statement: Any) -> _ExecuteResult:
        return _ExecuteResult(self.added)


def test_record_stage_timing_clamps_counters_and_formats_table() -> None:
    session = _Session()
    comparison_id = uuid.uuid4()
    job_id = uuid.uuid4()

    async def _run() -> None:
        event = await telemetry.record_stage_timing(
            session,
            comparison_id=comparison_id,
            job_id=job_id,
            stage="map_items",
            duration_ms=-10,
            status="done",
            llm_calls=1,
            input_tokens=-5,
            output_tokens=22,
            cache_hits=3,
            metadata={"cache": "warm"},
        )
        assert isinstance(event, TenderTelemetryEvent)
        rows = await telemetry.list_stage_timings(
            session,
            comparison_id=comparison_id,
        )
        table = telemetry.timing_table(rows)
        assert "map_items | done | 0 | 1 | 0 | 22 | 3" in table

    run_async(_run())


def test_record_stage_timing_skips_jobs_without_comparison() -> None:
    session = SimpleNamespace(add=lambda _item: None)

    async def _run() -> None:
        event = await telemetry.record_stage_timing(
            session,
            comparison_id=None,
            stage="orphan",
            duration_ms=1,
            status="done",
        )
        assert event is None

    run_async(_run())
