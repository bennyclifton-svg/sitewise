"""OpenDataLoader-backed PDF extraction shared by Clerk and TCM ingestion."""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import opendataloader_pdf

_DEFAULT_HYBRID_URL = "http://localhost:5002"
_MARKDOWN_PAGE_SEPARATOR = "\n\n<!-- page %page-number% -->\n\n"
_TEXT_PAGE_SEPARATOR = "\n\n=== page %page-number% ===\n\n"
_MARKDOWN_PAGE_RE = re.compile(r"^\s*<!-- page (?P<page>\d+) -->\s*$")
_TEXT_PAGE_RE = re.compile(r"^\s*=== page (?P<page>\d+) ===\s*$")
_HYBRID_HEALTH_TIMEOUT_SECONDS = 0.75


@dataclass(frozen=True, slots=True)
class PageExtract:
    page_no: int
    text: str


@dataclass(frozen=True, slots=True)
class PdfDocumentExtract:
    pages: list[PageExtract]
    markdown: str
    html: str
    text: str
    raw_json: dict | list | None
    hybrid_requested: bool
    hybrid_backend_available: bool | None
    hybrid_mode: str | None


def extract_pages(
    pdf_bytes: bytes,
    *,
    hybrid: bool = False,
    hybrid_url: str | None = None,
    hybrid_mode: str = "full",
    hybrid_fallback: bool = True,
) -> list[PageExtract]:
    return extract_pdf_document(
        pdf_bytes,
        hybrid=hybrid,
        hybrid_url=hybrid_url,
        hybrid_mode=hybrid_mode,
        hybrid_fallback=hybrid_fallback,
    ).pages


def extract_pdf_document(
    pdf_bytes: bytes,
    *,
    hybrid: bool = False,
    hybrid_url: str | None = None,
    hybrid_mode: str = "full",
    hybrid_fallback: bool = True,
) -> PdfDocumentExtract:
    hybrid_backend_available = (
        _hybrid_backend_available(hybrid_url or _DEFAULT_HYBRID_URL)
        if hybrid
        else None
    )
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "doc.pdf"
        src.write_bytes(pdf_bytes)

        convert_kwargs: dict = {
            "input_path": [str(src)],
            "output_dir": str(tmp_path),
            "format": "json,markdown,html,text",
            "image_output": "off",
            "markdown_page_separator": _MARKDOWN_PAGE_SEPARATOR,
            "text_page_separator": _TEXT_PAGE_SEPARATOR,
            "quiet": True,
        }
        if hybrid:
            convert_kwargs["hybrid"] = "docling-fast"
            convert_kwargs["hybrid_mode"] = hybrid_mode
            convert_kwargs["hybrid_fallback"] = hybrid_fallback
            if hybrid_url:
                convert_kwargs["hybrid_url"] = hybrid_url

        opendataloader_pdf.convert(**convert_kwargs)

        json_file = tmp_path / "doc.json"
        raw = json.loads(json_file.read_text(encoding="utf-8"))
        markdown = _read_optional_text(tmp_path / "doc.md")
        html = _read_optional_text(tmp_path / "doc.html")
        text = _read_optional_text(tmp_path / "doc.txt")

    pages = _pages_from_markdown(markdown)
    if not pages:
        pages = _pages_from_text(text)
    if not pages:
        pages = _pages_from_json(raw)
    return PdfDocumentExtract(
        pages=pages,
        markdown=markdown,
        html=html,
        text=text,
        raw_json=raw,
        hybrid_requested=hybrid,
        hybrid_backend_available=hybrid_backend_available,
        hybrid_mode=hybrid_mode if hybrid else None,
    )


def _read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _hybrid_backend_available(url: str) -> bool:
    health_url = f"{url.rstrip('/')}/health"
    try:
        with urlopen(health_url, timeout=_HYBRID_HEALTH_TIMEOUT_SECONDS) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def _pages_from_markdown(markdown: str) -> list[PageExtract]:
    return _pages_from_marked_text(markdown, _MARKDOWN_PAGE_RE)


def _pages_from_text(text: str) -> list[PageExtract]:
    return _pages_from_marked_text(text, _TEXT_PAGE_RE)


def _pages_from_marked_text(text: str, marker_re: re.Pattern[str]) -> list[PageExtract]:
    if not text.strip():
        return []

    pages: list[PageExtract] = []
    current_page: int | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        marker = marker_re.match(line)
        if marker:
            if current_page is not None:
                page_text = "\n".join(current_lines).strip()
                if page_text:
                    pages.append(PageExtract(page_no=current_page, text=page_text))
            current_page = int(marker.group("page"))
            current_lines = []
            continue
        if current_page is not None:
            current_lines.append(line)

    if current_page is not None:
        page_text = "\n".join(current_lines).strip()
        if page_text:
            pages.append(PageExtract(page_no=current_page, text=page_text))

    if pages:
        return pages
    return [PageExtract(page_no=1, text=text.strip())]


def _pages_from_json(raw: dict | list | None) -> list[PageExtract]:
    elements: list[dict] = (
        raw.get("kids", [])
        if isinstance(raw, dict)
        else (raw if isinstance(raw, list) else [])
    )
    pages: dict[int, list[str]] = {}
    for element in elements:
        page_no = int(element.get("page number", 1))
        content = element.get("content", "").strip()
        if content:
            pages.setdefault(page_no, []).append(content)

    return [
        PageExtract(page_no=page_no, text="\n".join(texts))
        for page_no, texts in sorted(pages.items())
    ]
