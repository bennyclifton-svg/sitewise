from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from app.inbox.pdf_inspect import PdfInfo, inspect_pdf

_KEYWORD_PATTERNS = [
    re.compile(r"\bSCALE\b", re.I),
    re.compile(r"\bSHEET\b", re.I),
    re.compile(r"\bDRAWN\b", re.I),
    re.compile(r"\bREV\b", re.I),
    re.compile(r"\bDWG\b", re.I),
    re.compile(r"\bDATE\b", re.I),
    re.compile(r"\b\d+\s*OF\s*\d+\b", re.I),
]


@dataclass(frozen=True, slots=True)
class DetectionConfig:
    min_pages: int = 2
    uniform_dims_tolerance_pt: float = 2.0
    uniform_dims_min_fraction: float = 0.8
    min_long_edge_pt: float = 1000.0
    min_keyword_hits_per_page: int = 2
    keyword_min_fraction: float = 0.5


@dataclass(frozen=True, slots=True)
class DetectionResult:
    is_drawing_set: bool
    confidence: float
    page_count: int
    scores: dict = field(default_factory=dict)


def _page_has_title_block(text: str, min_hits: int) -> bool:
    hits = sum(1 for pat in _KEYWORD_PATTERNS if pat.search(text))
    return hits >= min_hits


def detect_from_info(info: PdfInfo, config: DetectionConfig | None = None) -> DetectionResult:
    config = config or DetectionConfig()

    if info.encrypted or info.page_count < config.min_pages or not info.pages:
        return DetectionResult(False, 0.0, info.page_count, {"reason": "gate"})

    # Modal page size within tolerance.
    size_keys = [
        (round(p.width / config.uniform_dims_tolerance_pt),
         round(p.height / config.uniform_dims_tolerance_pt))
        for p in info.pages
    ]
    modal_key, modal_count = Counter(size_keys).most_common(1)[0]
    uniform_fraction = modal_count / len(info.pages)

    modal_pages = [p for p, k in zip(info.pages, size_keys) if k == modal_key]
    modal_page = modal_pages[0]
    large_landscape = (
        modal_page.is_landscape and modal_page.long_edge >= config.min_long_edge_pt
    )

    keyword_pages = sum(
        1 for p in info.pages
        if _page_has_title_block(p.text, config.min_keyword_hits_per_page)
    )
    keyword_fraction = keyword_pages / len(info.pages)

    is_drawing_set = (
        uniform_fraction >= config.uniform_dims_min_fraction
        and large_landscape
        and keyword_fraction >= config.keyword_min_fraction
    )

    confidence = round(
        (0.4 * uniform_fraction)
        + (0.3 * (1.0 if large_landscape else 0.0))
        + (0.3 * keyword_fraction),
        3,
    )

    return DetectionResult(
        is_drawing_set=is_drawing_set,
        confidence=confidence,
        page_count=info.page_count,
        scores={
            "uniform_dims_fraction": round(uniform_fraction, 3),
            "large_format_landscape": large_landscape,
            "keyword_fraction": round(keyword_fraction, 3),
        },
    )


def detect_drawing_set(data: bytes, config: DetectionConfig | None = None) -> DetectionResult:
    return detect_from_info(inspect_pdf(data), config)
