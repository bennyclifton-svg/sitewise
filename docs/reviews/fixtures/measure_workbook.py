"""Offline exporter measurement; run with backend's pinned uv environment.

From backend: uv run --frozen python ../docs/reviews/fixtures/measure_workbook.py
No database, object storage or model is used. This is not an end-to-end SLA test.
"""
from __future__ import annotations

import asyncio
import ctypes
import json
import sys
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
import tests.offline_network  # noqa: E402, F401 — contain settings/network before app imports
from app.cost_plan.schemas import CostItemInput, CostPlanState, DependencySnapshot  # noqa: E402
from app.cost_plan.workbook_rebuild import WorkbookRebuildCoordinator  # noqa: E402
from app.sitewise.cost_plan_workbook import build_typed_cost_plan_workbook  # noqa: E402

STATE = CostPlanState(
    project_id=uuid.UUID(int=1), version=1,
    dependency_snapshot=DependencySnapshot(
        profile_revision=1, evidence_fingerprint="synthetic-100-rows-v1",
        decision_set_revision=1, runtime_version="review-fixture",
    ),
    items=[CostItemInput(
        item_key=f"item-{i}", cost_code=f"C{i:03}", category="Construction",
        item=f"Synthetic construction package {i}", display_order=i,
        budget=Decimal("10000"), committed=Decimal("8000"),
        basis="Synthetic performance fixture, not project evidence",
    ) for i in range(100)],
)


def build() -> int:
    result = build_typed_cost_plan_workbook(
        project_title="Isolated review fixture", state=STATE, invoice_rows=[],
        generated_at=datetime(2026, 9, 13, tzinfo=UTC),
    )
    assert result.row_count == 100
    return len(result.content)


def peak_working_set_bytes() -> int | None:
    if sys.platform != "win32":
        return None

    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in (
                "peak", "working", "quota_peak_paged", "quota_paged",
                "quota_peak_nonpaged", "quota_nonpaged", "pagefile", "peak_pagefile",
            )
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    get_process = ctypes.windll.kernel32.GetCurrentProcess
    get_process.restype = ctypes.c_void_p
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    if not query(get_process(), ctypes.byref(counters), counters.cb):
        return None
    return counters.peak


async def measure() -> dict:
    build()  # same warm interpreter/import/template state for every measured batch
    samples = []
    for concurrency in (1, 2, 4):
        for sample in range(7):
            wall = time.perf_counter()
            cpu = time.process_time()
            sizes = await asyncio.gather(*[asyncio.to_thread(build) for _ in range(concurrency)])
            samples.append(dict(
                concurrency=concurrency, sample=sample,
                wall_ms=(time.perf_counter() - wall) * 1000,
                cpu_ms=(time.process_time() - cpu) * 1000,
                output_bytes=sizes, peak_process_working_set=peak_working_set_bytes(),
            ))

    builds = 0

    async def export() -> None:
        nonlocal builds
        builds += 1
        await asyncio.to_thread(build)

    # Independent coordinators model the isolation of API and worker memory.
    # This proves lack of shared exclusion, not PostgreSQL race correctness.
    api, worker = WorkbookRebuildCoordinator(quiet_seconds=60), WorkbookRebuildCoordinator(quiet_seconds=60)
    api.schedule("same-project", export)
    worker.schedule("same-project", export)
    await asyncio.gather(api.flush("same-project"), worker.flush("same-project"))
    return {"samples": samples, "independent_coordinator_exports": builds}


if __name__ == "__main__":
    result = asyncio.run(measure())
    output = ROOT / ".tmp/architecture-review/workbook-measurements.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    for concurrency in (1, 2, 4):
        rows = [row for row in result["samples"] if row["concurrency"] == concurrency]
        print(json.dumps({"concurrency": concurrency, "n": len(rows), **{
            field: {"median": median(row[field] for row in rows),
                    "min": min(row[field] for row in rows), "max": max(row[field] for row in rows)}
            for field in ("wall_ms", "cpu_ms")
        }}))
    print("Independent coordinator exports:", result["independent_coordinator_exports"])
