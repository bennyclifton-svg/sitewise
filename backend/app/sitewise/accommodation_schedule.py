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
    rows.sort(
        key=lambda row: (
            _level_rank(row["level"]),
            row["level"].casefold(),
            row["space"].casefold(),
            row["id"],
        )
    )
    return rows


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
