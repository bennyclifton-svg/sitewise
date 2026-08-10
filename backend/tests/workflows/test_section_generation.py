from __future__ import annotations

import asyncio

import pytest

from app.workflows.section_generation import (
    SectionGenerationJob,
    run_section_generation,
)


def test_section_generation_is_bounded_and_reports_real_completions() -> None:
    active = 0
    max_active = 0
    events: list[dict] = []

    async def publish(progress: dict) -> None:
        events.append(progress)

    def job(key: str):
        async def run() -> str:
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0)
            active -= 1
            return key

        return run

    results = asyncio.run(
        run_section_generation(
            [
                SectionGenerationJob(key=key, label=key.title(), run=job(key))
                for key in ("one", "two", "three")
            ],
            max_concurrency=2,
            on_progress=publish,
        )
    )

    assert results == {"one": "one", "two": "two", "three": "three"}
    assert max_active == 2
    assert events[-1]["completed_sections"] == 3
    assert all(
        later["completed_sections"] >= earlier["completed_sections"]
        for earlier, later in zip(events, events[1:], strict=False)
    )


def test_section_generation_rejects_duplicate_job_keys() -> None:
    async def run() -> str:
        return "result"

    with pytest.raises(ValueError, match="Duplicate section generation job key: one"):
        asyncio.run(
            run_section_generation(
                (
                    SectionGenerationJob(key="one", label="First", run=run),
                    SectionGenerationJob(key="one", label="Second", run=run),
                )
            )
        )
