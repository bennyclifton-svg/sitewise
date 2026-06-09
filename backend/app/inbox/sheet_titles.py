from __future__ import annotations

import re
from dataclasses import dataclass

import fitz

_SHEET_SEQ = re.compile(r"(\d+)\s*OF\s*(\d+)", re.I)
_SCALE = re.compile(r"\b1\s*:\s*\d+\b")
_BOILERPLATE = re.compile(
    r"copyright|owned by|liable|disclaimer|gspublisher|abn|pty|ph:|phone|fax|"
    r"avenue|street|road|nsw|submission plans",
    re.I,
)
# Longer phrases first so the alternation prefers the most specific caption.
_TITLE_CANDIDATES = re.compile(
    r"\b(SITE PLAN|GROUND FLOOR PLAN|GROUND FLOOR|FIRST FLOOR PLAN|FIRST FLOOR|"
    r"SLAB PENETRATIONS?|SLAB PLAN|ELEVATIONS?|SECTIONS?|ELECTRICAL PLAN|ELECTRICAL|"
    r"WET AREA[S]?|KITCHEN|WINDOW SCHEDULE|LANDSCAPE PLAN|LANDSCAPE|SEDIMENT CONTROL|"
    r"SEDIMENT|EXTERNAL COLOURS|EXTERNAL|CONCEPT STORMWATER|CONCEPT|TITLE PAGE|"
    r"FLOOR PLAN|ROOF PLAN|DRAINAGE|STORMWATER|FOOTING|BRACING|FRAMING)\b",
    re.I,
)
_MAX_TITLE_LEN = 60


@dataclass(frozen=True, slots=True)
class SheetPlan:
    index: int          # 1-based page number
    title: str
    filename: str
    sheet_number_label: str | None
    scale: str | None


def _titlecase(value: str) -> str:
    cleaned = " ".join(value.split())
    return cleaned[:_MAX_TITLE_LEN].title()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", " ", value).strip()
    return " ".join(slug.split())


def _extract_title(text: str) -> str | None:
    if not text.strip():
        return None
    # Prefer a known drawing-type caption anywhere in the text (captions often
    # share a line with boilerplate like "SUBMISSION PLANS").
    match = _TITLE_CANDIDATES.search(text)
    if match:
        return _titlecase(match.group(1))
    # Fallback: first short, non-boilerplate, mostly-alpha line.
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if 3 <= len(line) <= 40 and not _BOILERPLATE.search(line):
            alpha = sum(c.isalpha() for c in line)
            if alpha >= max(3, len(line) // 2):
                return _titlecase(line)
    return None


def build_sheet_plan(data: bytes, *, source_filename: str) -> list[SheetPlan]:
    stem = re.sub(r"\.pdf$", "", source_filename, flags=re.I)
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        plans: list[SheetPlan] = []
        used: set[str] = set()
        for i in range(doc.page_count):
            text = doc[i].get_text() or ""
            seq = _SHEET_SEQ.search(text)
            sheet_no = int(seq.group(1)) if seq else (i + 1)
            number_label = seq.group(0).upper() if seq else None
            scale_match = _SCALE.search(text)

            title = _extract_title(text) or f"Sheet {i + 1:02d}"
            nn = f"{sheet_no:02d}"
            base = f"{stem} - {nn} {_slugify(title)}".strip()
            filename = f"{base}.pdf"
            suffix = 2
            while filename.lower() in used:
                filename = f"{base} ({suffix}).pdf"
                suffix += 1
            used.add(filename.lower())

            plans.append(
                SheetPlan(
                    index=i + 1,
                    title=title,
                    filename=filename,
                    sheet_number_label=number_label,
                    scale=scale_match.group(0) if scale_match else None,
                )
            )
        return plans
    finally:
        doc.close()
