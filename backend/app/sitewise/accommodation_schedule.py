"""Deterministic Accommodation Schedule helpers from shared space facts."""

from __future__ import annotations

import re
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
    (re.compile(r"\bretain(?:ed|ing)?\b", re.I), "Retained"),
    (re.compile(r"\bexisting\b", re.I), "Existing"),
    (re.compile(r"\b(?:new|proposed)\b", re.I), "New"),
)

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


def accommodation_schedule_display_rows(project: Project) -> list[dict[str, Any]]:
    """Shared rows plus any brief-named spaces not already recorded or removed."""
    explicit = accommodation_schedule_rows(project)
    claimed = {row["space"].casefold() for row in explicit}
    claimed.update(_removed_space_names(project))
    extras = [
        row
        for row in brief_accommodation_rows(project)
        if row["space"].casefold() not in claimed
    ]
    return _sorted_rows(explicit + extras)


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
    seen: set[str] = set()
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
                if label.casefold() in seen:
                    continue
                found.append(
                    {
                        "space": label,
                        "level": _first_cue(clause, _LEVEL_CUES),
                        "area": "TBC",
                        "characteristics": _infer_characteristics(clause),
                        "status": _first_cue(clause, _STATUS_CUES),
                        "id": _slug(label),
                        "revision": 0,
                    }
                )
                seen.add(label.casefold())
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
