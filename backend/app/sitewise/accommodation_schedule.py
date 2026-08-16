"""Deterministic Accommodation Schedule helpers from shared space facts."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from app.database.project import Project
from app.projects.project_knowledge import list_shared_project_objects

_ACCOMMODATION_FIELDS = (
    "space",
    "level",
    "area",
    "characteristics",
    "status",
)

_TOTAL_LABELS = frozenset({"total", "scheduled area", "**scheduled area**"})

_LEVEL_ORDER = {
    "basement": 0,
    "lower ground": 1,
    "ground": 2,
    "ground floor": 2,
    "first": 3,
    "first floor": 3,
    "level 1": 3,
    "second": 4,
    "second floor": 4,
    "level 2": 4,
    "third": 5,
    "level 3": 5,
    "roof": 80,
    "external": 90,
    "site": 91,
}

_AREA_PATTERN = re.compile(r"(\d[\d,]*(?:\.\d+)?)")

# Longest phrase first. Counts ("four bedrooms") and work words ("extension")
# are not spaces — only names the user actually wrote.
_SPACE_TERMS: tuple[tuple[str, str], ...] = tuple(
    sorted(
        (
            ("open plan living dining", "Living / dining"),
            ("open-plan living dining", "Living / dining"),
            ("living dining", "Living / dining"),
            ("living/dining", "Living / dining"),
            ("open plan living", "Living"),
            ("parents retreat", "Parents retreat"),
            ("parent's retreat", "Parents retreat"),
            ("parents' retreat", "Parents retreat"),
            ("rear sitting room", "Rear sitting room"),
            ("sitting room", "Sitting room"),
            ("master bedroom", "Master bedroom"),
            ("guest bedroom", "Guest bedroom"),
            ("walk-in robe", "Walk-in robe"),
            ("walk in robe", "Walk-in robe"),
            ("butler's pantry", "Butler's pantry"),
            ("butlers pantry", "Butler's pantry"),
            ("powder room", "Powder room"),
            ("family room", "Family room"),
            ("rumpus room", "Rumpus"),
            ("media room", "Media room"),
            ("home office", "Home office"),
            ("covered deck", "Covered deck"),
            ("outdoor kitchen", "Outdoor kitchen"),
            ("plant room", "Plant room"),
            ("loading dock", "Loading dock"),
            ("circulation core", "Circulation core"),
            ("wine cellar", "Wine cellar"),
            ("mud room", "Mud room"),
            ("mudroom", "Mud room"),
            ("ensuite", "Ensuite"),
            ("bathroom", "Bathroom"),
            ("laundry", "Laundry"),
            ("kitchen", "Kitchen"),
            ("pantry", "Pantry"),
            ("dining", "Dining"),
            ("living", "Living"),
            ("lounge", "Lounge"),
            ("rumpus", "Rumpus"),
            ("study", "Study"),
            ("garage", "Garage"),
            ("carport", "Carport"),
            ("balcony", "Balcony"),
            ("terrace", "Terrace"),
            ("courtyard", "Courtyard"),
            ("patio", "Patio"),
            ("verandah", "Verandah"),
            ("veranda", "Verandah"),
            ("alfresco", "Alfresco"),
            ("foyer", "Foyer"),
            ("hallway", "Hallway"),
            ("bedroom", "Bedroom"),
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
)

_LEVEL_CUES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:upstairs|first\s+floor|second\s+stor(?:e)?y|second\s+floor|level\s*1)\b", re.I), "First"),
    (re.compile(r"\b(?:ground(?:\s+floor)?|downstairs)\b", re.I), "Ground"),
    (re.compile(r"\bbasement\b", re.I), "Basement"),
    (re.compile(r"\b(?:external|outdoor|outside)\b", re.I), "External"),
    (re.compile(r"\broof\b", re.I), "Roof"),
)

_STATUS_CUES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bdemolish(?:ed|ing)?\b", re.I), "Demolished"),
    (re.compile(r"\b(?:to be removed|take out|taken out|non-original)\b", re.I), "Demolished"),
    (re.compile(r"\bretain(?:ed|ing)?\b", re.I), "Retained"),
    (re.compile(r"\bexisting\b", re.I), "Existing"),
    (re.compile(r"\b(?:new|proposed)\b", re.I), "New"),
)

_TABLE_HEADER_ALIASES = {
    "space": "space",
    "room": "space",
    "level": "level",
    "area": "area",
    "characteristics": "characteristics",
    "status": "status",
}
_TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
_REQUIRED_TABLE_FIELDS = frozenset({"space", "status"})

_OPEN_PLAN_RE = re.compile(r"\bopen[-\s]?plan\b", re.I)
_CLAUSE_SPLIT = re.compile(r"[,;]+")


def accommodation_schedule_rows(project: Project) -> list[dict[str, Any]]:
    """Return active accommodation rows for PMP rendering and agent edits."""
    rows: list[dict[str, Any]] = []
    for item in list_shared_project_objects(project, kind="accommodation_space"):
        value = item.value if isinstance(item.value, dict) else {}
        status = str(value.get("status") or "").strip()
        if status.casefold() == "removed":
            continue
        label = str(value.get("space") or item.id).strip()
        if not label or label.casefold() in _TOTAL_LABELS:
            continue
        row = {field: _cell(value.get(field)) for field in _ACCOMMODATION_FIELDS}
        row["space"] = label
        row["id"] = item.id
        row["revision"] = item.revision
        rows.append(row)
    return _sorted_rows(rows)


def brief_accommodation_rows(project: Project) -> list[dict[str, Any]]:
    """Spaces the user already named in scope_narrative. Not typical rooms."""
    from app.projects.profile import project_scope_narrative

    return _spaces_from_text(" ".join(project_scope_narrative(project)))


def parse_accommodation_schedule_tables(text: str) -> list[dict[str, Any]]:
    """Read Space/Level/Area/Characteristics/Status tables from a brief."""
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        mapping = _header_mapping(_split_table_row(lines[index]))
        if mapping is None:
            index += 1
            continue
        index += 1
        if index < len(lines) and _is_table_separator(lines[index]):
            index += 1
        while index < len(lines):
            cells = _split_table_row(lines[index])
            if not cells:
                break
            if _is_table_separator(lines[index]):
                index += 1
                continue
            row = _row_from_table_cells(cells, mapping)
            index += 1
            if row is None:
                continue
            key = _row_identity(row)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    return rows


def accommodation_schedule_evidence_rows(
    project: Project,
    document_texts: Sequence[str] = (),
) -> list[dict[str, Any]]:
    """Shared rows plus demolished/new spaces named in an uploaded brief table."""
    explicit = accommodation_schedule_rows(project)
    claimed = {_row_name_status(row) for row in explicit}
    removed = _removed_space_names(project)
    extras: list[dict[str, Any]] = []
    for text in document_texts:
        for row in parse_accommodation_schedule_tables(text):
            if _row_name_status(row) in claimed:
                continue
            if row["space"].casefold() in removed:
                continue
            claimed.add(_row_name_status(row))
            extras.append(row)
    return _sorted_rows(explicit + extras)


def accommodation_schedule_display_rows(
    project: Project,
    document_texts: Sequence[str] = (),
) -> list[dict[str, Any]]:
    """Shared rows, brief-table rows, then any brief-named spaces still missing."""
    evidence = accommodation_schedule_evidence_rows(
        project, document_texts=document_texts
    )
    claimed = {_row_name_status(row) for row in evidence}
    removed = _removed_space_names(project)
    extras = [
        row
        for row in brief_accommodation_rows(project)
        if _row_name_status(row) not in claimed
        and row["space"].casefold() not in removed
    ]
    return _sorted_rows(evidence + extras)


def accommodation_source_texts(
    *,
    documents: Sequence[Any] = (),
    fallback: Sequence[str] | None = None,
) -> list[str]:
    """Prefer full stored document text over a compressed evidence digest."""
    texts = [
        text
        for document in documents
        if (text := getattr(document, "normalized_content", None) or "").strip()
    ]
    return texts or [text for text in (fallback or ()) if text and text.strip()]


def apply_accommodation_schedule_facts(
    markdown: str,
    *,
    project: Project,
    source_texts: Sequence[str] = (),
) -> str:
    """Replace the Accommodation Schedule table from brief evidence and shared rows."""
    from app.sitewise.pmp_evidence_validation import _replace_markdown_section
    from app.sitewise.section_contracts import heading_for_section_id

    rows = accommodation_schedule_evidence_rows(project, document_texts=source_texts)
    if not rows:
        return markdown
    heading = heading_for_section_id(
        "accommodation-schedule", work_type=project.work_type
    )
    return _replace_markdown_section(markdown, heading, _format_schedule_section(rows))


def parse_area_m2(raw: object) -> float | None:
    """Read a square-metre figure out of the loose text a PM actually types.

    Handles "24", "24 m²", "approx 24", "24–28". First number wins.
    Returns None rather than guessing when nothing parses.
    """
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw) if raw > 0 else None
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text or text.casefold() in {"tbc", "—", "-"}:
        return None
    match = _AREA_PATTERN.search(text.replace("m²", " ").replace("m2", " "))
    if match is None:
        return None
    try:
        amount = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    return amount if amount > 0 else None


def scheduled_area_total(rows: list[dict[str, Any]]) -> float | None:
    """Sum parseable areas, excluding demolished spaces."""
    total = 0.0
    found = False
    for row in rows:
        if str(row.get("status") or "").casefold() == "demolished":
            continue
        amount = parse_area_m2(row.get("area"))
        if amount is None:
            continue
        total += amount
        found = True
    return total if found else None


def _level_rank(level: str) -> int:
    return _LEVEL_ORDER.get(level.strip().casefold(), 70)


def _cell(raw: object) -> str:
    text = str(raw or "").strip()
    return text or "TBC"


def _sorted_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            _level_rank(str(row.get("level") or "")),
            str(row.get("level") or "").casefold(),
            str(row.get("space") or "").casefold(),
            str(row.get("id") or ""),
        ),
    )


def _removed_space_names(project: Project) -> set[str]:
    names: set[str] = set()
    for item in list_shared_project_objects(project, kind="accommodation_space"):
        value = item.value if isinstance(item.value, dict) else {}
        if str(value.get("status") or "").strip().casefold() != "removed":
            continue
        label = str(value.get("space") or item.id).strip()
        if label:
            names.add(label.casefold())
    return names


def _spaces_from_text(text: str) -> list[dict[str, Any]]:
    if not text.strip():
        return []
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for clause in _CLAUSE_SPLIT.split(text):
        clause = clause.strip()
        if not clause:
            continue
        occupied: list[tuple[int, int]] = []
        for phrase, label in _SPACE_TERMS:
            pattern = re.compile(
                rf"(?<![\w/]){re.escape(phrase)}(?![\w/])",
                re.IGNORECASE,
            )
            for match in pattern.finditer(clause):
                start, end = match.span()
                if any(start < stop and end > begin for begin, stop in occupied):
                    continue
                occupied.append((start, end))
                status = _first_cue(clause, _STATUS_CUES)
                row = {
                    "space": label,
                    "level": _first_cue(clause, _LEVEL_CUES),
                    "area": "TBC",
                    "characteristics": _infer_characteristics(clause),
                    "status": status,
                    "id": _slug(f"{label}-{status}"),
                    "revision": 0,
                }
                key = _row_identity(row)
                if key in seen:
                    continue
                found.append(row)
                seen.add(key)
    return _sorted_rows(found)


def _first_cue(window: str, cues: tuple[tuple[re.Pattern[str], str], ...]) -> str:
    for pattern, value in cues:
        if pattern.search(window):
            return value
    return "TBC"


def _infer_characteristics(window: str) -> str:
    if _OPEN_PLAN_RE.search(window):
        return "open plan"
    return "TBC"


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-")


def _row_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("space") or "").casefold(),
        str(row.get("status") or "").casefold(),
        str(row.get("level") or "").casefold(),
    )


def _row_name_status(row: dict[str, Any]) -> tuple[str, str]:
    return (
        str(row.get("space") or "").casefold(),
        str(row.get("status") or "").casefold(),
    )


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _is_table_separator(line: str) -> bool:
    cells = _split_table_row(line)
    return bool(cells) and all(_TABLE_SEPARATOR_RE.match(cell.replace(" ", "")) for cell in cells)


def _header_mapping(cells: list[str]) -> dict[str, int] | None:
    mapping: dict[str, int] = {}
    for index, cell in enumerate(cells):
        field = _TABLE_HEADER_ALIASES.get(cell.casefold())
        if field is not None:
            mapping[field] = index
    if not _REQUIRED_TABLE_FIELDS.issubset(mapping):
        return None
    return mapping


def _row_from_table_cells(
    cells: list[str],
    mapping: dict[str, int],
) -> dict[str, Any] | None:
    def cell(field: str) -> str:
        index = mapping.get(field)
        if index is None or index >= len(cells):
            return ""
        return cells[index].strip()

    space = cell("space")
    if not space or space.casefold() in _TOTAL_LABELS or space.startswith("**"):
        return None
    status = cell("status") or "TBC"
    if status.casefold() == "removed":
        return None
    return {
        "space": space,
        "level": cell("level") or "TBC",
        "area": cell("area") or "TBC",
        "characteristics": cell("characteristics") or "TBC",
        "status": status,
        "id": _slug(f"{space}-{status}-{cell('level')}"),
        "revision": 0,
    }


def _format_schedule_section(rows: list[dict[str, Any]]) -> str:
    table = [
        "",
        "Rooms, zones and outdoor spaces the project covers. Area is "
        "scheduled area, not GFA or NLA. Add or tidy rows in chat. "
        "Missing fields stay TBC.",
        "",
        "| Space | Level | Area | Characteristics | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        table.append(
            "| {space} | {level} | {area} | {characteristics} | {status} |".format(
                space=row["space"],
                level=row["level"],
                area=row["area"],
                characteristics=row["characteristics"],
                status=row["status"],
            )
        )
    total = scheduled_area_total(rows)
    total_cell = f"{total:g} m²" if total is not None else "TBC"
    table.append(f"| **Scheduled area** |  | {total_cell} |  |  |")
    return "\n".join(table) + "\n"
