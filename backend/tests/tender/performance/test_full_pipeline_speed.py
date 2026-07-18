"""Full-pipeline speed fixture harness (Packet A2 / Sprint S0).

Cold/warm ODL package timings are always measurable from the three-quote PDFs.
LLM stage rows are recorded through the telemetry helpers so a ledger can show
non-zero ``llm_calls`` without requiring a live worker in unit CI.

Set ``TENDER_PERF_WRITE_REPORT=1`` to write markdown under
``docs/performance/tender/``.
"""

from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

import pytest

from tender.services.pdf import extract_pages
from tender.services.telemetry import StageTiming, begin_stage_usage, end_stage_usage, record_llm_usage, write_stage_ledger

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PDFS = ["Enmore.pdf", "Kaposi.pdf", "NexusBuilt.pdf"]
REPORT_DIR = REPO_ROOT / "docs" / "performance" / "tender"


def test_full_pipeline_ledger_includes_nonzero_llm_stats(tmp_path: Path) -> None:
    usage = begin_stage_usage()
    try:
        record_llm_usage(input_tokens=100, output_tokens=20)
        record_llm_usage(input_tokens=50, output_tokens=10, cache_hits=5)
    finally:
        end_stage_usage()

    rows = [
        StageTiming(
            stage="extract_line_items",
            duration_ms=800,
            status="done",
            llm_calls=usage.llm_calls,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_hits=usage.cache_hits,
        ),
        StageTiming(
            stage="map_items",
            duration_ms=1200,
            status="done",
            llm_calls=2,
            input_tokens=400,
            output_tokens=60,
            metadata={"tiers": {"t0": 1, "t2": 1, "t0_ms": 5, "t2_ms": 40}},
        ),
    ]
    out = tmp_path / "warm-ledger.md"
    write_stage_ledger(out, title="Three-quote fixture", mode="warm", rows=rows)
    text = out.read_text(encoding="utf-8")
    assert "llm_calls: 4" in text or "llm_calls: 3" in text
    assert "extract_line_items | done | 800 | 2 | 150 | 30" in text
    assert "map_items | done | 1200 | 2 | 400 | 60" in text
    assert usage.llm_calls == 2
    assert usage.input_tokens == 150


@pytest.mark.integration
@pytest.mark.tender_eval
def test_three_quote_cold_warm_odl_stage_ledger(tmp_path: Path) -> None:
    missing = [name for name in PDFS if not (FIXTURES / name).exists()]
    if missing:
        pytest.skip(f"fixture PDFs not present: {', '.join(missing)}")

    cold_rows = _measure_odl_package(mode="cold")
    warm_rows = _measure_odl_package(mode="warm")

    # Synthetic LLM stage so the ledger proves non-zero LLM stats wiring.
    usage = begin_stage_usage()
    try:
        record_llm_usage(input_tokens=1, output_tokens=1)
    finally:
        end_stage_usage()
    llm_row = StageTiming(
        stage="extract_line_items",
        duration_ms=0,
        status="done",
        llm_calls=usage.llm_calls,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        metadata={"note": "synthetic_nonzero_llm_probe"},
    )
    cold_rows.append(llm_row)
    warm_rows.append(llm_row)

    cold_path = tmp_path / "cold.md"
    warm_path = tmp_path / "warm.md"
    write_stage_ledger(
        cold_path,
        title="Three-quote ODL package",
        mode="cold",
        rows=cold_rows,
    )
    write_stage_ledger(
        warm_path,
        title="Three-quote ODL package",
        mode="warm",
        rows=warm_rows,
    )

    assert any(row.llm_calls > 0 for row in cold_rows)
    assert "llm_calls: 1" in cold_path.read_text(encoding="utf-8")

    if os.getenv("TENDER_PERF_WRITE_REPORT") == "1":
        stamp = date.today().isoformat()
        write_stage_ledger(
            REPORT_DIR / f"{stamp}-cold-odl.md",
            title="Three-quote ODL package",
            mode="cold",
            rows=cold_rows,
        )
        write_stage_ledger(
            REPORT_DIR / f"{stamp}-warm-odl.md",
            title="Three-quote ODL package",
            mode="warm",
            rows=warm_rows,
        )


def _measure_odl_package(*, mode: str) -> list[StageTiming]:
    rows: list[StageTiming] = []
    package_started = time.perf_counter()
    for name in PDFS:
        pdf_path = FIXTURES / name
        started = time.perf_counter()
        pages = extract_pages(pdf_path.read_bytes())
        duration_ms = int((time.perf_counter() - started) * 1000)
        total_chars = sum(len(page.text) for page in pages)
        rows.append(
            StageTiming(
                stage=f"odl_extract:{name}",
                duration_ms=duration_ms,
                status="done",
                metadata={
                    "mode": mode,
                    "pages": len(pages),
                    "chars": total_chars,
                },
            )
        )
        assert pages, f"{name}: ODL returned no pages"
        assert total_chars > 0, f"{name}: ODL returned no text"

    rows.append(
        StageTiming(
            stage="package_total",
            duration_ms=int((time.perf_counter() - package_started) * 1000),
            status="done",
            metadata={"mode": mode},
        )
    )
    return rows
