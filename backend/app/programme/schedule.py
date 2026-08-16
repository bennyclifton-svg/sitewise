from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Literal

ActivityKind = Literal["stage", "activity", "milestone"]


@dataclass(frozen=True, slots=True)
class ActivityDraft:
    activity_key: str
    kind: ActivityKind
    start_date: date
    duration_days: int
    parent_key: str | None = None
    predecessor_key: str | None = None
    lag_days: int = 0
    finish_date: date | None = None
    name: str = ""
    display_order: int = 0
    assumption: bool = True
    notes: str = ""


def schedule_activities(rows: list[ActivityDraft]) -> list[ActivityDraft]:
    """Compute finishes and apply finish-to-start links in topological order."""
    by_key = {row.activity_key: row for row in rows}
    if len(by_key) != len(rows):
        raise ValueError("activity_key values must be unique")

    for row in rows:
        if row.duration_days < 0:
            raise ValueError(f"{row.activity_key} duration_days cannot be negative")
        if row.kind == "milestone" and row.duration_days != 0:
            raise ValueError(f"{row.activity_key} milestone duration_days must be 0")
        if row.predecessor_key and row.predecessor_key not in by_key:
            raise ValueError(
                f"{row.activity_key} predecessor {row.predecessor_key} does not exist"
            )

    visiting: set[str] = set()
    resolved: dict[str, ActivityDraft] = {}

    def resolve(key: str) -> ActivityDraft:
        if key in resolved:
            return resolved[key]
        if key in visiting:
            raise ValueError(f"predecessor cycle involving {key}")
        visiting.add(key)
        row = by_key[key]
        start = row.start_date
        if row.predecessor_key:
            predecessor = resolve(row.predecessor_key)
            predecessor_finish = predecessor.finish_date
            if predecessor_finish is None:
                raise ValueError(f"{row.predecessor_key} is missing a finish date")
            start = predecessor_finish + timedelta(days=row.lag_days)
        finish = start if row.kind == "milestone" else start + timedelta(days=row.duration_days)
        scheduled = replace(row, start_date=start, finish_date=finish)
        visiting.remove(key)
        resolved[key] = scheduled
        return scheduled

    return [resolve(row.activity_key) for row in rows]


def apply_link_move(row: ActivityDraft, *, new_start: date) -> ActivityDraft:
    """Dragging a bar sets an explicit start and converts the row to floating."""
    return replace(row, start_date=new_start, predecessor_key=None, lag_days=0)


def rollup_stages(rows: list[ActivityDraft]) -> list[ActivityDraft]:
    """Stage bars span their children. Childless stages keep their own dates."""
    children_by_parent: dict[str, list[ActivityDraft]] = {}
    for row in rows:
        if row.parent_key:
            children_by_parent.setdefault(row.parent_key, []).append(row)

    rolled: list[ActivityDraft] = []
    for row in rows:
        children = children_by_parent.get(row.activity_key)
        if row.kind != "stage" or not children:
            rolled.append(row)
            continue
        starts = [child.start_date for child in children]
        finishes = [
            child.finish_date
            for child in children
            if child.finish_date is not None
        ]
        if not finishes:
            rolled.append(row)
            continue
        start = min(starts)
        finish = max(finishes)
        rolled.append(
            replace(
                row,
                start_date=start,
                finish_date=finish,
                duration_days=(finish - start).days,
            )
        )
    return rolled
