"""ODL extraction eval over the real tender fixtures (slow: invokes the JVM)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from tender.services.pdf import extract_pages

FIXTURES = Path(__file__).parent / "fixtures"
PDFS = ["Enmore.pdf", "Kaposi.pdf", "NexusBuilt.pdf"]


@pytest.mark.integration
@pytest.mark.tender_eval
@pytest.mark.parametrize("name", PDFS)
def test_odl_extracts_real_tender_fixture(name: str) -> None:
    pdf_path = FIXTURES / name
    if not pdf_path.exists():
        pytest.skip(f"fixture {name} not present")

    start = time.perf_counter()
    pages = extract_pages(pdf_path.read_bytes())
    elapsed = time.perf_counter() - start

    assert pages, f"{name}: ODL returned no pages"
    non_empty = [p for p in pages if p.text.strip()]
    assert len(non_empty) >= max(1, len(pages) // 2), (
        f"{name}: {len(non_empty)}/{len(pages)} pages have text"
    )
    total_chars = sum(len(p.text) for p in pages)
    print(f"\n{name}: {len(pages)} pages, {total_chars} chars, {elapsed:.1f}s")
