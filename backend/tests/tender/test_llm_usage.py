"""Stage LLM usage collector used by the tender worker telemetry path."""

from __future__ import annotations

from types import SimpleNamespace

from tender.llm import usage
from tests.conftest import run_async


def test_begin_stage_usage_isolates_collectors_per_context() -> None:
    first = usage.begin_stage_usage()
    usage.record_llm_call(input_tokens=10, output_tokens=4)
    assert first.snapshot() == usage.LlmUsageSnapshot(
        llm_calls=1,
        input_tokens=10,
        output_tokens=4,
    )

    second = usage.begin_stage_usage()
    usage.record_llm_call(input_tokens=3, output_tokens=1)
    assert second.snapshot().llm_calls == 1
    assert second.snapshot().input_tokens == 3
    assert first.snapshot().llm_calls == 1
    assert first.snapshot().input_tokens == 10

    usage.reset_stage_usage()
    usage.record_llm_call(input_tokens=99, output_tokens=99)
    assert usage.current_stage_usage() is None


def test_tokens_from_response_reads_responses_api_usage() -> None:
    response = SimpleNamespace(
        usage=SimpleNamespace(input_tokens=120, output_tokens=45)
    )
    assert usage.tokens_from_response(response) == (120, 45)


def test_tokens_from_embedding_response_reads_prompt_tokens() -> None:
    response = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=80, total_tokens=80))
    assert usage.tokens_from_embedding_response(response) == (80, 0)


def test_merge_metadata_is_available_on_collector() -> None:
    collector = usage.begin_stage_usage()
    collector.merge_metadata({"tier_counts": {"t0": 2, "t2": 1}})
    assert collector.snapshot().metadata == {"tier_counts": {"t0": 2, "t2": 1}}
    usage.reset_stage_usage()


def test_record_llm_call_is_noop_without_active_collector() -> None:
    usage.reset_stage_usage()
    usage.record_llm_call(input_tokens=5, output_tokens=1)
