"""Phase 5 speed gate over the simple three-tender fixture package."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from tender.services.pdf import extract_pages
from tender.services.telemetry import StageTiming, timing_table

FIXTURES = Path(__file__).parent / "fixtures"
PDFS = ["Enmore.pdf", "Kaposi.pdf", "NexusBuilt.pdf"]
SPEED_GATE_SECONDS = 90


@pytest.mark.integration
@pytest.mark.tender_eval
def test_simple_three_tender_fixture_package_cold_speed_gate() -> None:
    missing = [name for name in PDFS if not (FIXTURES / name).exists()]
    if missing:
        pytest.skip(f"fixture PDFs not present: {', '.join(missing)}")

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
                metadata={"pages": len(pages), "chars": total_chars},
            )
        )
        assert pages, f"{name}: ODL returned no pages"
        assert total_chars > 0, f"{name}: ODL returned no text"

    total_elapsed = time.perf_counter() - package_started
    rows.append(
        StageTiming(
            stage="package_total",
            duration_ms=int(total_elapsed * 1000),
            status="done",
        )
    )
    print("\n" + timing_table(rows))
    assert total_elapsed < SPEED_GATE_SECONDS
