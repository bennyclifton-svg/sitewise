"""Full-pipeline speed ledger for the three-quote fixture package (Sprint S0).

Cold/warm reports live under ``docs/performance/tender/``. The default path
asserts telemetry wiring and committed ledger format (no live OpenAI). Set
``TENDER_FULL_PIPELINE_LIVE=1`` later when a live warm/cold runner is available.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tender.llm import usage
from tender.services.telemetry import StageTiming, timing_table, write_stage_ledger

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PDFS = ["Enmore.pdf", "Kaposi.pdf", "NexusBuilt.pdf"]
LEDGER_DIR = Path(__file__).resolve().parents[4] / "docs" / "performance" / "tender"


def test_stage_ledger_includes_nonzero_llm_stats(tmp_path: Path) -> None:
    collector = usage.begin_stage_usage()
    try:
        usage.record_llm_call(input_tokens=240, output_tokens=60)
        usage.record_llm_call(input_tokens=80, output_tokens=20)
        snapshot = collector.snapshot()
        collector.merge_metadata(
            {
                "tier_counts": {"t0": 12, "t1": 8, "t2": 30, "t3": 4},
                "tier_durations_ms": {"t0": 40, "t1": 80, "t2": 90000, "t3": 32000},
                "mode": "warm",
            }
        )
        metadata = collector.snapshot().metadata
    finally:
        usage.reset_stage_usage()

    rows = [
        StageTiming(
            stage="extract_line_items",
            duration_ms=18000,
            status="done",
            llm_calls=1,
            input_tokens=240,
            output_tokens=60,
        ),
        StageTiming(
            stage="map_items",
            duration_ms=122000,
            status="done",
            llm_calls=snapshot.llm_calls,
            input_tokens=snapshot.input_tokens,
            output_tokens=snapshot.output_tokens,
            metadata=metadata,
        ),
        StageTiming(
            stage="package_total",
            duration_ms=140000,
            status="done",
            llm_calls=snapshot.llm_calls + 1,
            input_tokens=snapshot.input_tokens + 240,
            output_tokens=snapshot.output_tokens + 60,
            metadata={"quotes": 3, "mode": "warm"},
        ),
    ]

    out = tmp_path / "warm-three-quote.md"
    write_stage_ledger(
        out,
        rows,
        header={
            "fixture": "simple-three-tender",
            "mode": "warm",
            "quotes": PDFS,
            "generated_at": "test",
        },
    )
    text = out.read_text(encoding="utf-8")
    assert "llm_calls" in text
    assert "map_items | done | 122000 | 2 | 320 | 80 |" in text
    assert "tier_counts" in text
    assert rows[-1].llm_calls > 0
    assert rows[-1].input_tokens > 0
    print("\n" + timing_table(rows))


def test_committed_cold_and_warm_ledgers_have_nonzero_llm_stats() -> None:
    missing = [name for name in PDFS if not (FIXTURES / name).exists()]
    if missing:
        pytest.skip(f"fixture PDFs not present: {', '.join(missing)}")

    if os.environ.get("TENDER_FULL_PIPELINE_LIVE") == "1":
        pytest.skip("live full-pipeline runner not wired in S0; telemetry gate covered above")

    cold_path = LEDGER_DIR / "three-quote-cold.md"
    warm_path = LEDGER_DIR / "three-quote-warm.md"
    for path in (cold_path, warm_path):
        assert path.exists(), f"missing stage ledger: {path}"
        text = path.read_text(encoding="utf-8")
        assert "map_items" in text
        assert "llm_calls" in text
        # Non-zero LLM stats somewhere in the table body.
        assert any(
            line.split("|")[3].strip().isdigit() and int(line.split("|")[3].strip()) > 0
            for line in text.splitlines()
            if "|" in line and "llm_calls" not in line and "---" not in line
        ), f"{path.name} has no non-zero llm_calls"


def test_ledger_header_is_json_front_matter(tmp_path: Path) -> None:
    path = tmp_path / "sample.md"
    write_stage_ledger(
        path,
        [
            StageTiming(
                stage="map_items",
                duration_ms=10,
                status="done",
                llm_calls=1,
                input_tokens=2,
                output_tokens=3,
            )
        ],
        header={"mode": "warm"},
    )
    text = path.read_text(encoding="utf-8")
    assert text.startswith("```json\n")
    block = text.split("```json\n", 1)[1].split("\n```", 1)[0]
    assert json.loads(block)["mode"] == "warm"
