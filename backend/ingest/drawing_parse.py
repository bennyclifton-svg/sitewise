import re
from dataclasses import dataclass

_REVISION_BRACKET_RE = re.compile(r"\[([A-Z0-9]+)\]\s*$")
_REVISION_PAREN_RE = re.compile(r"-\((\d{2})\)\s*$")
_SHEET_NUMBER_RE = re.compile(
    r"([A-Z]{1,3}-\d{3,4})|(\d{5}_[A-Z]\d{4})",
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
    drawing_number = None
    if number_match:
        drawing_number = (number_match.group(1) or number_match.group(2)).upper()

    title = stem
    if drawing_number:
        title = re.sub(re.escape(drawing_number), "", title, count=1, flags=re.IGNORECASE).strip(" -_")

    return DrawingIdentity(
        drawing_number=drawing_number,
        revision=revision,
        title=title or None,
    )
