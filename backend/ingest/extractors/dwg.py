from pathlib import Path

from ingest.drawing_parse import parse_drawing_filename
from ingest.extractors.base import ExtractedDocument


def extract_dwg(path: Path) -> ExtractedDocument:
    identity = parse_drawing_filename(path.name)
    lines = [
        f"# Drawing register: {path.name}",
        f"Drawing number: {identity.drawing_number or 'unknown'}",
        f"Revision: {identity.revision or 'unknown'}",
        f"Title: {identity.title or path.stem}",
        "Format: dwg",
        "Note: Geometry not indexed; register metadata only.",
    ]
    return ExtractedDocument(
        normalized_content="\n".join(lines),
        page_count=1,
        drawing_identity=identity,
    )
