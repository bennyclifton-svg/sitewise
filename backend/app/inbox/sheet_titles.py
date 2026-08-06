from __future__ import annotations

import re
from dataclasses import dataclass

import fitz

from ingest.drawing_parse import parse_drawing_filename
from ingest.title_block import TextSpan, extract_title_block_fields, page_title_block_spans

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
_MAX_REGISTER_VALUE_GAP = 60.0
_COVER_REGISTER_HEADING = re.compile(
    r"\b(?:DRAWING|DOCUMENT|SHEET)\s+(?:INDEX|LIST|REGISTER|SCHEDULE)\b",
    re.I,
)
_DRAWING_NUMBER_TOKEN = re.compile(
    r"(?<![A-Z0-9])"
    r"(?P<prefix>[A-Z]{1,5}(?:[-.][A-Z]{1,5})?[-.]?)"
    r"(?P<serial>\d{2,4})"
    r"(?![A-Z0-9])",
    re.I,
)
_NON_DRAWING_PREFIXES = {
    "AS",
    "BCA",
    "DA",
    "DEP",
    "DP",
    "ISO",
    "MOD",
    "NCC",
}


@dataclass(frozen=True, slots=True)
class SheetPlan:
    index: int          # 1-based page number
    title: str
    filename: str
    sheet_number_label: str | None
    scale: str | None
    document_number: str | None
    revision: str | None
    title_method: str
    document_number_method: str | None
    revision_method: str | None


@dataclass(frozen=True, slots=True)
class _RegisterEntry:
    document_number: str | None
    title: str
    revision: str | None


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


def _normalized_cell(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().rstrip(".:#").strip().upper()


def _shares_row(left: TextSpan, right: TextSpan) -> bool:
    overlap = min(left.y1, right.y1) - max(left.y0, right.y0)
    return overlap > 0.25 * min(left.height, right.height)


def _join_row(spans: list[TextSpan]) -> str:
    return " ".join(
        dict.fromkeys(span.text.strip() for span in sorted(spans, key=lambda item: item.x0))
    ).strip()


def _cover_sheet_register(page, *, page_count: int) -> list[_RegisterEntry] | None:
    """Read a complete first-page drawing register when its columns are explicit."""
    if page_count < 2:
        return None

    spans = page_title_block_spans(page)
    headings = [span for span in spans if _COVER_REGISTER_HEADING.search(span.text)]
    for heading in headings:
        header_zone = [
            span
            for span in spans
            if heading.y0 <= span.y0 <= heading.y1 + 100
            and span.x0 >= heading.x0 - 20
        ]
        sheet_header = next(
            (
                span
                for span in header_zone
                if _normalized_cell(span.text)
                in {"SHEET", "SHEET NO", "SHEET NUMBER", "SHEET #", "DRAWING NO"}
            ),
            None,
        )
        title_header = next(
            (
                span
                for span in header_zone
                if _normalized_cell(span.text) in {"DRAWING TITLE", "SHEET TITLE", "TITLE"}
            ),
            None,
        )
        revision_header = next(
            (
                span
                for span in header_zone
                if _normalized_cell(span.text) in {"REV", "REVISION", "ISSUE"}
            ),
            None,
        )
        if not sheet_header or not title_header or not revision_header:
            continue
        if not (sheet_header.x0 < title_header.x0 < revision_header.x0):
            continue

        first_row_y = max(sheet_header.y1, title_header.y1, revision_header.y1)
        row_limit = first_row_y + max(120.0, page_count * 28.0)
        number_spans = [
            span
            for span in spans
            if first_row_y < span.y0 <= row_limit
            and sheet_header.x0 - 4 <= span.x0 < title_header.x0 - 4
            and re.match(r"^/?[A-Z]*(?:[-.]?[A-Z]+)*[-.]?\d{1,4}$", span.text.strip(), re.I)
        ]

        entries: list[_RegisterEntry] = []
        for number_span in sorted(number_spans, key=lambda item: item.y0):
            title_spans = [
                span
                for span in spans
                if title_header.x0 - 4 <= span.x0 < revision_header.x0 - 4
                and _shares_row(number_span, span)
            ]
            revision_spans = [
                span
                for span in spans
                if revision_header.x0 - 4 <= span.x0
                and span.x0 - revision_header.x1 <= _MAX_REGISTER_VALUE_GAP
                and _shares_row(number_span, span)
                and re.match(r"^[A-Z0-9]{1,4}$", span.text.strip(), re.I)
            ]
            title = _join_row(title_spans)
            if not title:
                continue
            number = number_span.text.strip()
            entries.append(
                _RegisterEntry(
                    document_number=None if number.startswith("/") else number,
                    title=title,
                    revision=_join_row(revision_spans) or None,
                )
            )

        if len(entries) == page_count:
            return entries
    return None


def _cover_drawing_sequence(text: str, *, page_count: int) -> list[str] | None:
    """Read an unambiguous consecutive drawing-number run from the cover sheet."""
    if page_count < 2 or not _COVER_REGISTER_HEADING.search(text):
        return None

    groups: dict[tuple[str, int], dict[int, str]] = {}
    for match in _DRAWING_NUMBER_TOKEN.finditer(text):
        prefix = match.group("prefix").upper()
        if prefix.rstrip("-.") in _NON_DRAWING_PREFIXES:
            continue
        serial_text = match.group("serial")
        serial = int(serial_text)
        token = f"{prefix}{serial_text}"
        groups.setdefault((prefix, len(serial_text)), {}).setdefault(serial, token)

    candidates: list[list[str]] = []
    for serials in groups.values():
        if len(serials) != page_count:
            continue
        ordered = sorted(serials)
        if ordered != list(range(ordered[0], ordered[0] + page_count)):
            continue
        candidates.append([serials[serial] for serial in ordered])

    return candidates[0] if len(candidates) == 1 else None


def _source_stem_and_revision(source_filename: str) -> tuple[str, str | None]:
    stem = re.sub(r"\.pdf$", "", source_filename, flags=re.I).strip()
    revision = parse_drawing_filename(source_filename).revision
    if revision:
        stem = re.sub(
            rf"\s*(?:\[{re.escape(revision)}\]|-\({re.escape(revision)}\))\s*$",
            "",
            stem,
            flags=re.I,
        ).strip()
    return stem, revision


def _filename_document_number(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9]+", "-", value)).strip("-")


def build_sheet_plan(data: bytes, *, source_filename: str) -> list[SheetPlan]:
    stem, source_revision = _source_stem_and_revision(source_filename)
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        plans: list[SheetPlan] = []
        used: set[str] = set()
        first_page_text = doc[0].get_text() or "" if doc.page_count else ""
        register = (
            _cover_sheet_register(doc[0], page_count=doc.page_count)
            if doc.page_count
            else None
        )
        document_numbers = _cover_drawing_sequence(
            first_page_text,
            page_count=doc.page_count,
        )
        for i in range(doc.page_count):
            page = doc[i]
            text = page.get_text() or ""
            title_block = extract_title_block_fields(page_title_block_spans(page))
            register_entry = register[i] if register else None
            seq = _SHEET_SEQ.search(text)
            sheet_no = int(seq.group(1)) if seq else (i + 1)
            number_label = seq.group(0).upper() if seq else None
            scale_match = _SCALE.search(text)
            if title_block.document_number:
                document_number = title_block.document_number
                document_number_method = "title_block_v1"
            elif register_entry and register_entry.document_number:
                document_number = register_entry.document_number
                document_number_method = "drawing_schedule_v1"
            elif document_numbers:
                document_number = document_numbers[i]
                document_number_method = "cover_sequence_v1"
            else:
                document_number = None
                document_number_method = None

            if register_entry:
                title = _titlecase(register_entry.title)
                title_method = "drawing_schedule_v1"
            elif title_block.title:
                title = _titlecase(title_block.title)
                title_method = "title_block_v1"
            elif extracted_title := _extract_title(text):
                title = extracted_title
                title_method = "heuristic_v1"
            else:
                title = f"Sheet {i + 1:02d}"
                title_method = "position_v1"

            if register_entry and register_entry.revision:
                revision = register_entry.revision
                revision_method = "drawing_schedule_v1"
            elif title_block.revision:
                revision = title_block.revision
                revision_method = "title_block_v1"
            else:
                revision = source_revision
                revision_method = "source_filename_v1" if revision else None

            nn = f"{sheet_no:02d}"
            if document_number and document_number_method in {
                "drawing_schedule_v1",
                "title_block_v1",
            }:
                safe_number = _filename_document_number(document_number)
                base = f"{safe_number} - {_slugify(title)}"
            else:
                safe_number = _slugify(document_number) if document_number else None
                prefix = f"{safe_number} - {stem}" if safe_number else stem
                base = f"{prefix} - {nn} {_slugify(title)}".strip()
            revision_suffix = f" [{revision}]" if revision else ""
            filename = f"{base}{revision_suffix}.pdf"
            suffix = 2
            while filename.lower() in used:
                filename = f"{base} ({suffix}){revision_suffix}.pdf"
                suffix += 1
            used.add(filename.lower())

            plans.append(
                SheetPlan(
                    index=i + 1,
                    title=title,
                    filename=filename,
                    sheet_number_label=number_label,
                    scale=scale_match.group(0) if scale_match else None,
                    document_number=document_number,
                    revision=revision,
                    title_method=title_method,
                    document_number_method=document_number_method,
                    revision_method=revision_method,
                )
            )
        return plans
    finally:
        doc.close()
