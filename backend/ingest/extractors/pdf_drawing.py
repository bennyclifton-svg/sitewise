from pathlib import Path

import fitz

from ingest.drawing_parse import parse_drawing_filename
from ingest.extractors.base import ExtractedDocument


def _title_block_text(path: Path) -> str:
    document = fitz.open(path)
    if document.page_count == 0:
        document.close()
        return ""
    page = document[0]
    rect = page.rect
    # Title blocks are usually along the bottom or right edge of sheet 1.
    regions = [
        fitz.Rect(rect.x0, rect.y1 * 0.75, rect.x1, rect.y1),
        fitz.Rect(rect.x1 * 0.65, rect.y0, rect.x1, rect.y1),
    ]
    chunks: list[str] = []
    for region in regions:
        text = page.get_text("text", clip=region).strip()
        if text:
            chunks.append(text)
    document.close()
    return "\n".join(chunks).strip()


def extract_pdf_drawing(path: Path) -> ExtractedDocument:
    identity = parse_drawing_filename(path.name)
    title_block = _title_block_text(path)
    lines = [
        f"# Drawing register: {path.name}",
        f"Drawing number: {identity.drawing_number or 'unknown'}",
        f"Revision: {identity.revision or 'unknown'}",
        f"Title: {identity.title or path.stem}",
    ]
    if title_block:
        lines.extend(["", "## Title block", "", title_block])
    return ExtractedDocument(
        normalized_content="\n".join(lines).strip(),
        page_count=1,
        drawing_identity=identity,
    )
