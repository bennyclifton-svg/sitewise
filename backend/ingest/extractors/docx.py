import re
from pathlib import Path

import mammoth

from ingest.extractors.base import ExtractedDocument


def _html_to_text(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</h[1-6]>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_docx(path: Path) -> ExtractedDocument:
    with path.open("rb") as handle:
        result = mammoth.convert_to_html(handle)
    text = _html_to_text(result.value)
    return ExtractedDocument(normalized_content=text, page_count=1)
