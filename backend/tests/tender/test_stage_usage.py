"""Packet A2: stage usage accumulator and OpenAI token capture."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from tender.llm.openai_client import AsyncOpenAITenderClient
from tender.schemas import ProjectContext, TenderDocumentPage
from tender.services import telemetry
from tests.conftest import run_async


def test_stage_usage_accumulates_llm_calls_and_tokens() -> None:
    usage = telemetry.StageUsage()
    usage.add_llm_call(input_tokens=10, output_tokens=4, cache_hits=2)
    usage.add_llm_call(input_tokens=5, output_tokens=1)
    usage.merge_metadata({"tiers": {"t2": 1}})

    assert usage.llm_calls == 2
    assert usage.input_tokens == 15
    assert usage.output_tokens == 5
    assert usage.cache_hits == 2
    assert usage.metadata["tiers"]["t2"] == 1


def test_begin_stage_usage_binds_context_for_record_llm_usage() -> None:
    usage = telemetry.begin_stage_usage()
    telemetry.record_llm_usage(input_tokens=11, output_tokens=3, cache_hits=1)
    telemetry.record_mapping_tier("t0", duration_ms=12)
    telemetry.record_mapping_tier("t2", duration_ms=40)
    telemetry.end_stage_usage()

    assert usage.llm_calls == 1
    assert usage.input_tokens == 11
    assert usage.output_tokens == 3
    assert usage.cache_hits == 1
    assert usage.metadata["tiers"] == {
        "t0": 1,
        "t1": 0,
        "t2": 1,
        "t3": 0,
        "t0_ms": 12,
        "t1_ms": 0,
        "t2_ms": 40,
        "t3_ms": 0,
    }
    assert telemetry.current_stage_usage() is None


def test_openai_extract_records_usage_from_response(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("extract carefully", encoding="utf-8")
    fake_client = _FakeOpenAIClient(
        output={"line_items": [], "page_subtotals": []},
        usage=SimpleNamespace(
            input_tokens=120,
            output_tokens=45,
            input_tokens_details=SimpleNamespace(cached_tokens=8),
        ),
    )
    client = AsyncOpenAITenderClient(
        client=fake_client,  # type: ignore[arg-type]
        model="gpt-test",
        prompt_path=prompt_path,
    )
    usage = telemetry.begin_stage_usage()
    try:
        run_async(
            client.extract(
                [
                    TenderDocumentPage(
                        document_id="doc-1", page_no=1, text_content="Quote text"
                    )
                ],
                {"type": "object", "properties": {"line_items": {"type": "array"}}},
                _context(),
            )
        )
    finally:
        telemetry.end_stage_usage()

    assert usage.llm_calls == 1
    assert usage.input_tokens == 120
    assert usage.output_tokens == 45
    assert usage.cache_hits == 8


def test_usage_from_openai_response_supports_embedding_shape() -> None:
    input_tokens, output_tokens, cache_hits = telemetry.usage_from_openai_response(
        SimpleNamespace(usage=SimpleNamespace(prompt_tokens=64, total_tokens=64))
    )
    assert (input_tokens, output_tokens, cache_hits) == (64, 0, 0)


def test_write_stage_ledger_formats_warm_cold_report(tmp_path: Path) -> None:
    path = tmp_path / "ledger.md"
    rows = [
        telemetry.StageTiming(
            stage="map_items",
            duration_ms=1200,
            status="done",
            llm_calls=3,
            input_tokens=900,
            output_tokens=120,
            metadata={"tiers": {"t0": 2, "t2": 1}},
        )
    ]
    telemetry.write_stage_ledger(
        path,
        title="Three-quote fixture",
        mode="warm",
        rows=rows,
    )
    text = path.read_text(encoding="utf-8")
    assert "Mode: warm" in text
    assert "map_items | done | 1200 | 3 | 900 | 120" in text
    assert '"t0": 2' in text or "t0" in text


def _context() -> ProjectContext:
    return ProjectContext.model_validate(
        {
            "state": "NSW",
            "region": "metro",
            "build_type": "new_build",
            "dwelling_class": "class_1a",
            "storeys": 1,
            "soil_class": "M",
            "slope_class": "flat",
            "bal_rating": "none",
            "spec_level": "builder_base",
        }
    )


class _FakeResponses:
    def __init__(self, output: dict[str, Any], usage: Any) -> None:
        self.output = output
        self.usage = usage
        self.kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp-1",
            output_text=json.dumps(self.output),
            usage=self.usage,
        )


class _FakeOpenAIClient:
    def __init__(self, *, output: dict[str, Any], usage: Any) -> None:
        self.responses = _FakeResponses(output, usage)
