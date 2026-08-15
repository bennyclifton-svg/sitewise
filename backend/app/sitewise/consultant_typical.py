"""Starter consultant rows for a house. Not appointments.

A Class 1 house — new, extend, or refurb — needs a design lead, structure,
planning, and civil/stormwater on day one. The form those take varies
(architect vs building designer, combined structural-civil, architect doing
the DA). Seed the four disciplines as Not evidenced so the user can delete,
rename, or combine them.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.database.project import Project
from app.projects.project_knowledge import list_shared_project_objects

_HOUSE_SUBCLASSES = frozenset({"house"})
_HOUSE_WORK_TYPES = frozenset({"new", "extend", "refurb"})

HOUSE_CONSULTANTS: tuple[str, ...] = (
    "Architect",
    "Structural Engineer",
    "Town Planner",
    "Civil / stormwater",
)


def typical_consultant_labels(
    *,
    work_type: str | None,
    subclasses: Sequence[str] = (),
) -> tuple[str, ...]:
    """Return the house starter roster, or empty when it does not apply."""
    if work_type not in _HOUSE_WORK_TYPES:
        return ()
    if not any(str(value) in _HOUSE_SUBCLASSES for value in subclasses):
        return ()
    return HOUSE_CONSULTANTS


def removed_consultant_labels(project: Project | object) -> set[str]:
    """Disciplines the user already deleted from the shared register."""
    names: set[str] = set()
    if not hasattr(project, "project_metadata"):
        return names
    for item in list_shared_project_objects(project, kind="consultant"):
        value = item.value if isinstance(item.value, dict) else {}
        if str(value.get("status") or "").strip().casefold() != "removed":
            continue
        label = str(value.get("discipline") or item.id).strip()
        if label:
            names.add(label.casefold())
    return names
