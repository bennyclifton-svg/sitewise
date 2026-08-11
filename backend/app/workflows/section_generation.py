"""Bounded concurrent execution and truthful progress for narrative sections."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any


SectionRunner = Callable[[], Awaitable[Any]]
SectionProgressPublisher = Callable[[dict[str, Any]], Awaitable[None]]
SectionCompletePublisher = Callable[[str, Any, dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class SectionGenerationJob:
    key: str
    label: str
    run: SectionRunner


async def run_section_generation(
    jobs: Sequence[SectionGenerationJob],
    *,
    max_concurrency: int = 4,
    on_progress: SectionProgressPublisher | None = None,
    on_section_complete: SectionCompletePublisher | None = None,
) -> dict[str, Any]:
    """Run independent jobs concurrently and emit state derived from real completions."""
    if not jobs:
        return {}
    seen_keys: set[str] = set()
    for job in jobs:
        if job.key in seen_keys:
            raise ValueError(f"Duplicate section generation job key: {job.key}")
        seen_keys.add(job.key)
    semaphore = asyncio.Semaphore(max(1, max_concurrency))
    statuses = {job.key: "queued" for job in jobs}
    labels = {job.key: job.label for job in jobs}
    completed_results: dict[str, Any] = {}
    publish_lock = asyncio.Lock()

    async def publish(stage: str, active_key: str) -> None:
        if on_progress is None:
            return
        async with publish_lock:
            completed = sum(status == "complete" for status in statuses.values())
            await on_progress(
                {
                    "stage": stage,
                    "active_section": active_key,
                    "completed_sections": completed,
                    "total_sections": len(jobs),
                    "sections": [
                        {
                            "id": job.key,
                            "label": labels[job.key],
                            "status": statuses[job.key],
                        }
                        for job in jobs
                    ],
                }
            )

    async def run_one(job: SectionGenerationJob) -> tuple[str, Any]:
        async with semaphore:
            statuses[job.key] = "generating"
            await publish("section_started", job.key)
            try:
                result = await job.run()
            except BaseException:
                statuses[job.key] = "failed"
                await publish("section_failed", job.key)
                raise
            async with publish_lock:
                completed_results[job.key] = result
                snapshot = dict(completed_results)
            statuses[job.key] = "complete"
            await publish("section_completed", job.key)
            if on_section_complete is not None:
                await on_section_complete(job.key, result, snapshot)
            return job.key, result

    results = await asyncio.gather(*(run_one(job) for job in jobs))
    return dict(results)
