from __future__ import annotations

import fitz

DEFAULT_MAX_PAGES = 200


class PdfSplitError(ValueError):
    pass


def split_pdf_pages(data: bytes, *, max_pages: int = DEFAULT_MAX_PAGES) -> list[bytes]:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        if doc.needs_pass:
            raise PdfSplitError("PDF is encrypted")
        if doc.page_count > max_pages:
            raise PdfSplitError(
                f"PDF has {doc.page_count} pages, exceeding the limit of {max_pages}"
            )
        parts: list[bytes] = []
        for i in range(doc.page_count):
            out = fitz.open()
            out.insert_pdf(doc, from_page=i, to_page=i)
            parts.append(out.tobytes(garbage=4, deflate=True))
            out.close()
        return parts
    finally:
        doc.close()
