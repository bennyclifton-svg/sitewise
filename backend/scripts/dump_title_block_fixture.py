"""Dump a PDF's first-page text blocks to a JSON fixture for title-block tests.

Title-block parsing is geometry-driven, so a fixture only needs the block
rectangles and their text — not the source PDF. That keeps real drawings out of
the repo while making each new problem sheet a one-command regression test.

    python scripts/dump_title_block_fixture.py DRAWING.pdf tests/fixtures/title_blocks/e02.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz

from ingest.title_block import page_title_block_spans


def dump(pdf_path: Path) -> dict:
    document = fitz.open(pdf_path)
    try:
        page = document[0]
        return {
            "source_file_name": pdf_path.name,
            "page_width": round(page.rect.width, 2),
            "page_height": round(page.rect.height, 2),
            "spans": [
                {
                    "x0": round(span.x0, 2),
                    "y0": round(span.y0, 2),
                    "x1": round(span.x1, 2),
                    "y1": round(span.y1, 2),
                    "text": span.text,
                }
                for span in page_title_block_spans(page)
            ],
        }
    finally:
        document.close()


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    pdf_path = Path(argv[1])
    out_path = Path(argv[2])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(dump(pdf_path), indent=2) + "\n", encoding="utf-8")
    print(f"{pdf_path.name}: wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
