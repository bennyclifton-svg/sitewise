from __future__ import annotations

from dataclasses import dataclass

import fitz


@dataclass(frozen=True, slots=True)
class PageInfo:
    index: int          # 1-based page number
    width: float
    height: float
    text: str

    @property
    def is_landscape(self) -> bool:
        return self.width > self.height

    @property
    def long_edge(self) -> float:
        return max(self.width, self.height)

    @property
    def has_text(self) -> bool:
        return len(self.text.strip()) > 0


@dataclass(frozen=True, slots=True)
class PdfInfo:
    page_count: int
    encrypted: bool
    pages: list[PageInfo]


def inspect_pdf(data: bytes) -> PdfInfo:
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        encrypted = bool(doc.needs_pass)
        pages: list[PageInfo] = []
        if not encrypted:
            for i in range(doc.page_count):
                page = doc[i]
                rect = page.rect
                pages.append(
                    PageInfo(
                        index=i + 1,
                        width=round(rect.width, 2),
                        height=round(rect.height, 2),
                        text=page.get_text() or "",
                    )
                )
        return PdfInfo(page_count=doc.page_count, encrypted=encrypted, pages=pages)
    finally:
        doc.close()
