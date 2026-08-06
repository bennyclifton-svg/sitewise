"""Read drawing identity out of a PDF title block by geometry.

A CAD title block is a grid. Its text has no reliable reading order — ArchiCAD
and Revit commonly emit every label first and every value second, and NSW
Regulated Design Record stamps add a second label column on the same sheet. So
pairing a label with the next line of text invents values ("Rev" ->
"Project Address:"). Pairing by position does not.

Two layouts cover the sheets seen so far:

* ``label: value`` side by side on one row (compliance stamps, report covers).
* ``label`` above its value in the same grid cell (main title blocks), where the
  cell runs from the label's left edge to the next label's left edge on that row.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class TextSpan:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass(frozen=True, slots=True)
class TitleBlockFields:
    document_number: str | None = None
    title: str | None = None
    revision: str | None = None


_LABELS: dict[str, tuple[str, ...]] = {
    # Ordered: a sheet may carry both a drawing number and an internal
    # reference ("dwg no" -> "221102 - SK-003"), and the register wants the
    # drawing's own number.
    "document_number": (
        "DRAWING NO", "DRAWING NUMBER", "DRAWING #", "DRAWING / SKETCH NO",
        "DRAWING/SKETCH NO", "SKETCH NO", "SHEET NUMBER", "SHEET NO",
        "DOCUMENT NO", "DOCUMENT NUMBER", "DWG NO", "DRG NO",
    ),
    "title": ("DRAWING TITLE", "SHEET TITLE", "DOCUMENT TITLE", "TITLE"),
    "revision": ("REV", "REVISION", "ISSUE", "AMENDMENT", "VERSION"),
}

# Every label token we know, so a value candidate that is really a neighbouring
# label can be rejected regardless of which field we are filling.
_ALL_LABELS: frozenset[str] = frozenset(
    alias for aliases in _LABELS.values() for alias in aliases
) | frozenset(
    {
        "PROJECT", "PROJECT NUMBER", "PROJECT NO", "PROJECT TITLE",
        "PROJECT ADDRESS", "PLOT DATE", "DATE", "DESCRIPTION", "DRAWN",
        "CHECKED", "APPROVED", "DESIGNED", "SCALE", "SHEET SCALE", "SHEET SIZE",
        "CLIENT", "STATUS", "STAGE", "NORTH", "BUILDER", "ARCHITECT",
        "CONSULTANT", "CONTRACTOR", "ELECTRICAL ENGINEER", "REG NO",
        "DP FULL NAME", "BODY CORPORATE REG NO", "CONSENT NO",
        "REGULATED DESIGN RECORD", "JOB NO", "REFERENCE NO",
    }
)

# Discipline banners are stacked above the sheet title inside the same cell.
_DISCIPLINE_HEADING_RE = re.compile(
    r"^(?:ELECTRICAL|HYDRAULIC|MECHANICAL|STRUCTURAL|CIVIL|FIRE|ARCHITECTURAL"
    r"|LANDSCAPE|ACOUSTIC)\s+(?:SERVICES|ENGINEERING|DRAWINGS?)$",
    re.I,
)
_REVISION_TOKEN_RE = re.compile(r"^[A-Z0-9]{1,4}$")

# A value belongs to its label's grid cell. The cell edge — the next label along
# the row — is the real boundary; these caps only stop a match running away when
# no next label exists.
_MAX_ROW_GAP = 220.0
_MAX_STACK_GAP = 90.0
_REGULATED_RECORD_LABEL_GAP = 140.0


def _normalize_label(text: str) -> str:
    without_periods = re.sub(r"\.+", " ", text)
    return re.sub(r"\s+", " ", without_periods).strip().rstrip(":#").strip().upper()


def _field_for_label(text: str) -> tuple[str, int] | None:
    """The field this label fills, plus its rank among that field's aliases."""
    normalized = _normalize_label(text)
    for field, aliases in _LABELS.items():
        if normalized in aliases:
            return field, aliases.index(normalized)
    return None


def _is_label(span: TextSpan) -> bool:
    text = span.text.strip()
    if not text:
        return True
    if text.endswith(":"):
        return True
    return _normalize_label(text) in _ALL_LABELS


def _is_regulated_record_label(label: TextSpan, spans: Sequence[TextSpan]) -> bool:
    """Exclude the identity-looking fields inside a statutory design stamp."""
    for anchor in spans:
        if _normalize_label(anchor.text) != "REGULATED DESIGN RECORD":
            continue
        vertical_gap = label.y0 - anchor.y1
        horizontal_gap = max(
            anchor.x0 - label.x1,
            label.x0 - anchor.x1,
            0.0,
        )
        if (
            -10.0 <= vertical_gap <= _REGULATED_RECORD_LABEL_GAP
            and horizontal_gap <= _REGULATED_RECORD_LABEL_GAP
        ):
            return True
    return False


def _shares_row(label: TextSpan, other: TextSpan) -> bool:
    overlap = min(label.y1, other.y1) - max(label.y0, other.y0)
    return overlap > 0.4 * min(label.height, other.height)


def _value_right_of(label: TextSpan, spans: Sequence[TextSpan]) -> tuple[float, str] | None:
    right_edge = _cell_right_edge(label, spans)
    best: tuple[float, str] | None = None
    for span in spans:
        if span is label or _is_label(span):
            continue
        gap = span.x0 - label.x1
        if gap < -1.0 or gap > _MAX_ROW_GAP or span.x0 >= right_edge:
            continue
        if not _shares_row(label, span):
            continue
        if best is None or gap < best[0]:
            best = (gap, span.text.strip())
    return best


def _cell_right_edge(label: TextSpan, spans: Sequence[TextSpan]) -> float:
    """Where the label's grid cell ends: the next label along the same row."""
    edges = [
        span.x0
        for span in spans
        if span is not label
        and _is_label(span)
        and span.x0 > label.x1
        and _shares_row(label, span)
    ]
    return min(edges) if edges else float("inf")


def _values_below(label: TextSpan, spans: Sequence[TextSpan]) -> list[tuple[float, str]]:
    right_edge = _cell_right_edge(label, spans)
    found: list[TextSpan] = []
    for span in spans:
        if span is label or _is_label(span):
            continue
        gap = span.y0 - label.y1
        if gap < -1.0 or gap > _MAX_STACK_GAP:
            continue
        if span.x0 < label.x0 - 4.0 or span.x0 >= right_edge:
            continue
        # Without a next label, cap the open-ended cell instead of requiring
        # every fragment to overlap the narrow label. CAD commonly emits the
        # final digit of a drawing number as a separate span to its right.
        if right_edge == float("inf") and span.x0 - label.x1 > _MAX_ROW_GAP:
            continue
        found.append(span)

    rows: list[list[TextSpan]] = []
    for span in sorted(found, key=lambda item: (item.y0, item.x0)):
        row = next((row for row in rows if _shares_row(row[0], span)), None)
        if row is None:
            rows.append([span])
        else:
            row.append(span)

    values: list[tuple[float, str]] = []
    for row in rows:
        ordered = sorted(row, key=lambda item: item.x0)
        text = " ".join(dict.fromkeys(item.text.strip() for item in ordered))
        gap = min(item.y0 for item in ordered) - label.y1
        values.append((gap, text))
    return sorted(values, key=lambda item: item[0])


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" -:–—")


def _resolve_title(candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        cleaned = _clean(candidate)
        if cleaned and not _DISCIPLINE_HEADING_RE.match(cleaned):
            return cleaned
    return None


def _resolve_revision(candidates: Iterable[str]) -> str | None:
    # Revision tables conventionally append the current issue as the last row.
    # Walking bottom-up avoids reading the first historical issue (usually A).
    for candidate in reversed(list(candidates)):
        # Issue cells often stack "C1 / CONSTRUCTION ISSUE / 06.11.2023".
        first_line = _clean(candidate.splitlines()[0] if candidate else "")
        token = first_line.split(" ")[0] if first_line else ""
        if _REVISION_TOKEN_RE.match(token.upper()):
            return token.upper()
    return None


def _resolve_document_number(candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        cleaned = _clean(candidate.splitlines()[0] if candidate else "")
        if cleaned and re.match(r"^[A-Z0-9][A-Z0-9./\- ]{0,31}$", cleaned, re.I):
            return cleaned.upper()
    return None


def extract_title_block_fields(spans: Sequence[TextSpan]) -> TitleBlockFields:
    """Pair title-block labels with their values positionally."""

    # Ranked by which label matched, then by layout: a value beside its label on
    # one row is unambiguous, so it outranks one merely stacked underneath.
    candidates: dict[str, list[tuple[int, int, float, str]]] = {
        field: [] for field in _LABELS
    }
    for span in spans:
        matched = _field_for_label(span.text)
        if matched is None:
            continue
        if _is_regulated_record_label(span, spans):
            continue
        field, alias_rank = matched
        beside = _value_right_of(span, spans)
        if beside is not None:
            candidates[field].append((alias_rank, 0, beside[0], beside[1]))
        for gap, text in _values_below(span, spans):
            candidates[field].append((alias_rank, 1, gap, text))

    ordered = {
        field: [text for _, _, _, text in sorted(entries, key=lambda item: item[:3])]
        for field, entries in candidates.items()
    }
    revision_entries = candidates["revision"]
    if revision_entries:
        best_revision_alias = min(entry[0] for entry in revision_entries)
        ordered["revision"] = [
            text
            for _, _, _, text in sorted(
                (
                    entry
                    for entry in revision_entries
                    if entry[0] == best_revision_alias
                ),
                key=lambda item: item[:3],
            )
        ]
    return TitleBlockFields(
        document_number=_resolve_document_number(ordered["document_number"]),
        title=_resolve_title(ordered["title"]),
        revision=_resolve_revision(ordered["revision"]),
    )


def render_title_block_preview(fields: TitleBlockFields) -> str | None:
    """Render extracted fields as the canonical labelled form.

    Downstream merge, validation and confidence rules already live in
    ``document_metadata``; handing them well-formed labelled lines keeps one
    code path instead of a second, parallel set of rules.
    """
    lines: list[str] = []
    if fields.document_number:
        lines.append(f"Drawing No. {fields.document_number}")
    if fields.title:
        lines.append(f"Drawing Title {fields.title}")
    if fields.revision:
        lines.append(f"Revision {fields.revision}")
    return "\n".join(lines) if lines else None


def pdf_title_block_preview(content: bytes) -> str | None:
    """Canonical labelled preview read off the first page's title block."""
    import fitz

    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception:
        return None
    try:
        if document.needs_pass or document.page_count == 0:
            return None
        fields = extract_title_block_fields(page_title_block_spans(document[0]))
    except Exception:
        return None
    finally:
        document.close()
    return render_title_block_preview(fields)


def page_title_block_spans(page) -> list[TextSpan]:
    """Text spans of a PyMuPDF page, in reading orientation.

    Span rectangles are reported in the page's unrotated frame, but "beside" and
    "below" only mean what a reader sees once the page's rotation is applied —
    landscape sheets are routinely stored as portrait plus a 90-degree rotation.
    """
    import fitz

    rotation = page.rotation_matrix
    spans: list[TextSpan] = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span["text"].strip()
                if not text:
                    continue
                rect = fitz.Rect(span["bbox"]) * rotation
                rect.normalize()
                spans.append(
                    TextSpan(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1, text=text)
                )
    return spans


def extract_pdf_title_block_fields(path: Path) -> TitleBlockFields:
    import fitz

    document = fitz.open(path)
    try:
        if document.page_count == 0:
            return TitleBlockFields()
        return extract_title_block_fields(page_title_block_spans(document[0]))
    finally:
        document.close()
