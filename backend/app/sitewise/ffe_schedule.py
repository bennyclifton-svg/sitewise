"""Deterministic FFE Schedule helpers from shared ffe_item facts."""

from __future__ import annotations

from typing import Any

from app.database.project import Project
from app.projects.project_knowledge import list_shared_project_objects
from app.sitewise.ffe_typical import ffe_sequence_key

_FFE_FIELDS = (
    "item",
    "location",
    "quantity",
    "finish",
    "model",
    "dimensions",
    "supplier",
    "status",
    "package",
    "notes",
)


def ffe_schedule_rows(project: Project) -> list[dict[str, Any]]:
    """Return active FFE schedule rows for PMP rendering and agent edits."""
    rows: list[dict[str, Any]] = []
    for item in list_shared_project_objects(project, kind="ffe_item"):
        value = item.value if isinstance(item.value, dict) else {}
        status = str(value.get("status") or "").strip()
        if status.casefold() == "removed":
            continue
        label = str(value.get("item") or item.id).strip()
        if not label:
            continue
        row = {field: _cell(value.get(field)) for field in _FFE_FIELDS}
        row["item"] = label
        row["id"] = item.id
        row["revision"] = item.revision
        rows.append(row)
    rows.sort(key=lambda row: (*ffe_sequence_key(row), row["id"]))
    return rows


def _cell(raw: object) -> str:
    text = str(raw or "").strip()
    return text or "TBC"
