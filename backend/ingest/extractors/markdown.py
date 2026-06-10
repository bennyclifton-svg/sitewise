from pathlib import Path

from ingest.extractors.base import ExtractedDocument


def extract_markdown(path: Path) -> ExtractedDocument:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return ExtractedDocument(normalized_content="", page_count=0)
    return ExtractedDocument(normalized_content=text, page_count=1)
