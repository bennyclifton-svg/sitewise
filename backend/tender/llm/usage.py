"""Per-job LLM usage accumulator for tender worker stage telemetry.

Handlers and OpenAI wrappers record into a ContextVar collector that the worker
snapshots when writing ``tender_telemetry_events``.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class LlmUsageSnapshot:
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StageUsageCollector:
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_llm_call(self, *, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self.llm_calls += 1
        self.input_tokens += max(0, int(input_tokens))
        self.output_tokens += max(0, int(output_tokens))

    def merge_metadata(self, data: dict[str, Any]) -> None:
        self.metadata.update(data)

    def snapshot(self) -> LlmUsageSnapshot:
        return LlmUsageSnapshot(
            llm_calls=self.llm_calls,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            metadata=dict(self.metadata),
        )


_collector: ContextVar[StageUsageCollector | None] = ContextVar(
    "tender_stage_usage",
    default=None,
)


def begin_stage_usage() -> StageUsageCollector:
    collector = StageUsageCollector()
    _collector.set(collector)
    return collector


def reset_stage_usage() -> None:
    _collector.set(None)


def current_stage_usage() -> StageUsageCollector | None:
    return _collector.get()


def record_llm_call(*, input_tokens: int = 0, output_tokens: int = 0) -> None:
    collector = _collector.get()
    if collector is None:
        return
    collector.record_llm_call(input_tokens=input_tokens, output_tokens=output_tokens)


def tokens_from_response(response: Any) -> tuple[int, int]:
    usage_obj = getattr(response, "usage", None)
    if usage_obj is None:
        return 0, 0
    input_tokens = getattr(usage_obj, "input_tokens", None)
    output_tokens = getattr(usage_obj, "output_tokens", None)
    if input_tokens is None and output_tokens is None:
        # Chat Completions-shaped fallback.
        input_tokens = getattr(usage_obj, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage_obj, "completion_tokens", 0) or 0
    return max(0, int(input_tokens or 0)), max(0, int(output_tokens or 0))


def tokens_from_embedding_response(response: Any) -> tuple[int, int]:
    usage_obj = getattr(response, "usage", None)
    if usage_obj is None:
        return 0, 0
    prompt_tokens = getattr(usage_obj, "prompt_tokens", None)
    if prompt_tokens is None:
        prompt_tokens = getattr(usage_obj, "total_tokens", 0) or 0
    return max(0, int(prompt_tokens or 0)), 0
