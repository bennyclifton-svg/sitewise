from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import TenderTelemetryEvent


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
