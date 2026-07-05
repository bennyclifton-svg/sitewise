"""Pure PDF helpers for TCM ingestion."""

from __future__ import annotations

import fitz

from app.document_intake.odl_pdf import PageExtract as PageExtract
from app.document_intake.odl_pdf import extract_pages as extract_pages

__all__ = ["PageExtract", "extract_pages", "render_page_png"]


def render_page_png(pdf_bytes: bytes, *, page_no: int, dpi: int) -> bytes:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = document.load_page(page_no - 1)
        pixmap = page.get_pixmap(dpi=dpi)
        return pixmap.tobytes("png")
    finally:
        document.close()
