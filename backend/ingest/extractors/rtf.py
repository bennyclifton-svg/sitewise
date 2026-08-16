from pathlib import Path

from striprtf.striprtf import rtf_to_text

from ingest.extractors.base import ExtractedDocument


def extract_rtf(path: Path) -> ExtractedDocument:
    raw = path.read_bytes()
    if not raw.strip():
        return ExtractedDocument(normalized_content="", page_count=0)
    text = rtf_to_text(raw.decode("latin-1"), errors="ignore").strip()
    if not text:
        return ExtractedDocument(normalized_content="", page_count=0)
    return ExtractedDocument(normalized_content=text, page_count=1)
