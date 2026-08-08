import re
from dataclasses import dataclass

_REVISION_BRACKET_RE = re.compile(r"\[([A-Z0-9]+)\]\s*$")
_REVISION_PAREN_RE = re.compile(r"-\((\d{2})\)\s*$")
_SHEET_NUMBER_RE = re.compile(
    # Prefer CC-A-### before the shorter [A-Z]-### form so "CC-A-010" is not
    # collapsed to the inner "A-010". Reject other mid-token hits.
    r"(?<![A-Z0-9-])(CC-A-\d{3}|[A-Z]{1,3}-\d{2,4})(?![A-Z0-9-])",
    re.IGNORECASE,
)
# Flat architectural exports: optional project no + CC-## + title + trailing rev.
_CC_SHEET_RE = re.compile(
    r"^(?:\d{3,6}\s+)?(CC-\d{2,3})\s+(.+?)\s+([A-Z]\d?)$",
    re.IGNORECASE,
)
# Job-prefixed structural: shared project no + S#### + title (rev already stripped).
_JOB_STRUCTURAL_RE = re.compile(
    r"^\d{4,6}_(S\d{3,4})_(.+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class DrawingIdentity:
    drawing_number: str | None
    revision: str | None
    title: str | None


def parse_drawing_filename(filename: str) -> DrawingIdentity:
    stem = filename.rsplit(".", maxsplit=1)[0]
    revision: str | None = None

    bracket = _REVISION_BRACKET_RE.search(stem)
    if bracket:
        revision = bracket.group(1)
        stem = stem[: bracket.start()].strip()

    paren = _REVISION_PAREN_RE.search(stem)
    if paren:
        revision = paren.group(1)
        stem = stem[: paren.start()].strip()

    cc_sheet = _CC_SHEET_RE.match(stem)
    if cc_sheet:
        return DrawingIdentity(
            drawing_number=cc_sheet.group(1).upper(),
            revision=cc_sheet.group(3).upper(),
            title=cc_sheet.group(2).strip() or None,
        )

    job_structural = _JOB_STRUCTURAL_RE.match(stem)
    if job_structural:
        return DrawingIdentity(
            drawing_number=job_structural.group(1).upper(),
            revision=revision,
            title=re.sub(r"_+", " ", job_structural.group(2)).strip() or None,
        )

    electrical_short = re.match(r"^(E\d{2})-[A-Z0-9]{2}~\d+$", stem, re.I)
    if electrical_short:
        return DrawingIdentity(
            drawing_number=electrical_short.group(1).upper(),
            revision=revision,
            title=None,
        )

    electrical = re.match(r"^(E\d{2})\b", stem, re.I)
    if electrical:
        drawing_number = electrical.group(1).upper()
        title = re.sub(r"^E\d{2}\s*[-–—]?\s*", "", stem, flags=re.I).strip(" -_")
        return DrawingIdentity(
            drawing_number=drawing_number,
            revision=revision,
            title=title or None,
        )

    number_match = _SHEET_NUMBER_RE.search(stem)
    drawing_number = number_match.group(1).upper() if number_match else None

    title = stem
    if drawing_number:
        title = re.sub(re.escape(drawing_number), "", title, count=1, flags=re.IGNORECASE).strip(" -_")

    return DrawingIdentity(
        drawing_number=drawing_number,
        revision=revision,
        title=title or None,
    )
