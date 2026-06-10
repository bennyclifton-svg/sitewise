from pathlib import Path

import fitz

from ingest.extractors.base import ExtractedDocument, PageText


def extract_pdf_text(path: Path) -> ExtractedDocument:
    document = fitz.open(path)
    pages: list[PageText] = []
    parts: list[str] = []

    for index, page in enumerate(document, start=1):
        text = page.get_text("text").strip()
        if not text:
            continue
        pages.append(PageText(page_number=index, text=text))
        parts.append(f"## Page {index}\n\n{text}")

    document.close()
    normalized = "\n\n".join(parts).strip()
    return ExtractedDocument(
        normalized_content=normalized,
        page_count=len(pages),
        pages=pages,
    )
