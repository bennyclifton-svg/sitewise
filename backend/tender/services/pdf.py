"""Pure PDF helpers for TCM ingestion."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

import fitz
import opendataloader_pdf


@dataclass(frozen=True)
class PageExtract:
    page_no: int
    text: str


def extract_pages(pdf_bytes: bytes, *, hybrid: bool = False) -> list[PageExtract]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "doc.pdf"
        src.write_bytes(pdf_bytes)

        convert_kwargs: dict = dict(
            input_path=[str(src)],
            output_dir=str(tmp_path),
            format="json",
        )
        if hybrid:
            convert_kwargs["hybrid"] = "docling-fast"

        opendataloader_pdf.convert(**convert_kwargs)

        json_file = tmp_path / "doc.json"
        raw = json.loads(json_file.read_text(encoding="utf-8"))

    elements: list[dict] = raw.get("kids", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    pages: dict[int, list[str]] = {}
    for el in elements:
        pg = int(el.get("page number", 1))
        content = el.get("content", "").strip()
        if content:
            pages.setdefault(pg, []).append(content)

    return [
        PageExtract(page_no=pg, text="\n".join(texts))
        for pg, texts in sorted(pages.items())
    ]


def render_page_png(pdf_bytes: bytes, *, page_no: int, dpi: int) -> bytes:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = document.load_page(page_no - 1)
        pixmap = page.get_pixmap(dpi=dpi)
        return pixmap.tobytes("png")
    finally:
        document.close()
