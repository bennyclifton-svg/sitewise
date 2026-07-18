from __future__ import annotations

import json
import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import TenderTelemetryEvent

_EMPTY_TIERS: dict[str, int] = {
    "t0": 0,
    "t1": 0,
    "t2": 0,
    "t3": 0,
    "t0_ms": 0,
    "t1_ms": 0,
    "t2_ms": 0,
    "t3_ms": 0,
}

_stage_usage: ContextVar["StageUsage | None"] = ContextVar(
    "tender_stage_usage", default=None
)
_stage_usage_token: ContextVar[Token["StageUsage | None"] | None] = ContextVar(
    "tender_stage_usage_token", default=None
)


@dataclass
class StageUsage:
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hits: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_llm_call(
        self,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_hits: int = 0,
    ) -> None:
        self.llm_calls += 1
        self.input_tokens += max(0, input_tokens)
        self.output_tokens += max(0, output_tokens)
        self.cache_hits += max(0, cache_hits)

    def merge_metadata(self, values: dict[str, Any]) -> None:
        self.metadata.update(values)

    def record_mapping_tier(self, tier: str, *, duration_ms: int) -> None:
        key = _normalize_tier_key(tier)
        tiers = self.metadata.setdefault("tiers", dict(_EMPTY_TIERS))
        tiers[key] = int(tiers.get(key, 0)) + 1
        ms_key = f"{key}_ms"
        tiers[ms_key] = int(tiers.get(ms_key, 0)) + max(0, duration_ms)


@dataclass(frozen=True, slots=True)
class StageTiming:
    stage: str
    duration_ms: int
    status: str
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hits: int = 0
    metadata: dict[str, Any] | None = None


def begin_stage_usage() -> StageUsage:
    usage = StageUsage()
    token = _stage_usage.set(usage)
    _stage_usage_token.set(token)
    return usage


def current_stage_usage() -> StageUsage | None:
    return _stage_usage.get()


def end_stage_usage() -> StageUsage | None:
    usage = _stage_usage.get()
    token = _stage_usage_token.get()
    if token is not None:
        _stage_usage.reset(token)
        _stage_usage_token.set(None)
    else:
        _stage_usage.set(None)
    return usage


def record_llm_usage(
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_hits: int = 0,
) -> None:
    usage = current_stage_usage()
    if usage is None:
        return
    usage.add_llm_call(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_hits=cache_hits,
    )


def record_mapping_tier(tier: str, *, duration_ms: int) -> None:
    usage = current_stage_usage()
    if usage is None:
        return
    usage.record_mapping_tier(tier, duration_ms=duration_ms)


def usage_from_openai_response(response: Any) -> tuple[int, int, int]:
    """Return ``(input_tokens, output_tokens, cache_hits)`` from an OpenAI response."""

    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0, 0

    input_tokens = _usage_int(usage, "input_tokens", "prompt_tokens")
    output_tokens = _usage_int(usage, "output_tokens", "completion_tokens")
    details = _usage_value(usage, "input_tokens_details")
    cache_hits = 0
    if details is not None:
        cache_hits = _usage_int(details, "cached_tokens")
    return input_tokens, output_tokens, cache_hits


def note_openai_response(response: Any) -> None:
    input_tokens, output_tokens, cache_hits = usage_from_openai_response(response)
    record_llm_usage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_hits=cache_hits,
    )


async def record_stage_timing(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID | None,
    stage: str,
    duration_ms: int,
    status: str,
    job_id: uuid.UUID | None = None,
    llm_calls: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_hits: int = 0,
    metadata: dict[str, Any] | None = None,
) -> TenderTelemetryEvent | None:
    if comparison_id is None:
        return None

    event = TenderTelemetryEvent(
        comparison_id=comparison_id,
        job_id=job_id,
        stage=stage,
        duration_ms=max(0, duration_ms),
        status=status,
        llm_calls=max(0, llm_calls),
        input_tokens=max(0, input_tokens),
        output_tokens=max(0, output_tokens),
        cache_hits=max(0, cache_hits),
        event_metadata=metadata or {},
    )
    session.add(event)
    await session.flush()
    return event


async def list_stage_timings(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> list[StageTiming]:
    result = await session.execute(
        select(TenderTelemetryEvent)
        .where(TenderTelemetryEvent.comparison_id == comparison_id)
        .order_by(TenderTelemetryEvent.created_at.asc(), TenderTelemetryEvent.id.asc())
    )
    return [
        StageTiming(
            stage=event.stage,
            duration_ms=event.duration_ms,
            status=event.status,
            llm_calls=event.llm_calls,
            input_tokens=event.input_tokens,
            output_tokens=event.output_tokens,
            cache_hits=event.cache_hits,
            metadata=event.event_metadata,
        )
        for event in result.scalars().all()
    ]


def timing_table(rows: list[StageTiming]) -> str:
    lines = [
        "stage | status | duration_ms | llm_calls | input_tokens | output_tokens | cache_hits",
        "--- | --- | ---: | ---: | ---: | ---: | ---:",
    ]
    for row in rows:
        lines.append(
            " | ".join(
                [
                    row.stage,
                    row.status,
                    str(row.duration_ms),
                    str(row.llm_calls),
                    str(row.input_tokens),
                    str(row.output_tokens),
                    str(row.cache_hits),
                ]
            )
        )
    return "\n".join(lines)


def write_stage_ledger(
    path: Path,
    *,
    title: str,
    mode: str,
    rows: list[StageTiming],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total_ms = sum(row.duration_ms for row in rows)
    total_llm = sum(row.llm_calls for row in rows)
    total_in = sum(row.input_tokens for row in rows)
    total_out = sum(row.output_tokens for row in rows)
    metadata_blocks = [
        f"- `{row.stage}`: {json.dumps(row.metadata, sort_keys=True)}"
        for row in rows
        if row.metadata
    ]
    sections = [
        f"# {title}",
        "",
        f"Mode: {mode}",
        "",
        "## Stage ledger",
        "",
        timing_table(rows),
        "",
        "## Totals",
        "",
        f"- duration_ms: {total_ms}",
        f"- llm_calls: {total_llm}",
        f"- input_tokens: {total_in}",
        f"- output_tokens: {total_out}",
    ]
    if metadata_blocks:
        sections.extend(["", "## Metadata", "", *metadata_blocks])
    sections.append("")
    path.write_text("\n".join(sections), encoding="utf-8")


def _normalize_tier_key(tier: str) -> str:
    mapping = {
        "t0": "t0",
        "t0_exact": "t0",
        "t1": "t1",
        "t1_embedding": "t1",
        "t2": "t2",
        "t2_small_llm": "t2",
        "t3": "t3",
        "t3_frontier": "t3",
    }
    return mapping.get(tier, tier)


def _usage_value(usage: Any, key: str) -> Any:
    if isinstance(usage, dict):
        return usage.get(key)
    return getattr(usage, key, None)


def _usage_int(usage: Any, *keys: str) -> int:
    for key in keys:
        value = _usage_value(usage, key)
        if value is None:
            continue
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            continue
    return 0
