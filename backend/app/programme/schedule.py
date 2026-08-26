from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Literal

ActivityKind = Literal["stage", "activity", "milestone"]
DependencyEndpoint = Literal["start", "finish"]


@dataclass(frozen=True, slots=True)
class ActivityDraft:
    activity_key: str
    kind: ActivityKind
    start_date: date
    duration_days: int
    parent_key: str | None = None
    finish_date: date | None = None
    name: str = ""
    display_order: int = 0
    assumption: bool = True
    notes: str = ""


@dataclass(frozen=True, slots=True)
class DependencyDraft:
    dependency_key: str
    source_activity_key: str
    target_activity_key: str
    source_endpoint: DependencyEndpoint
    target_endpoint: DependencyEndpoint
    lag_days: int = 0


def dependency_constraint_start(
    dependency: DependencyDraft,
    *,
    source: ActivityDraft,
    target_duration_days: int,
) -> date:
    source_anchor = (
        source.start_date
        if dependency.source_endpoint == "start"
        else source.finish_date
    )
    if source_anchor is None:
        raise ValueError(f"{source.activity_key} is missing a finish date")
    target_offset = target_duration_days if dependency.target_endpoint == "finish" else 0
    return source_anchor + timedelta(days=dependency.lag_days - target_offset)


def schedule_activities(
    rows: list[ActivityDraft],
    dependencies: list[DependencyDraft] | None = None,
) -> list[ActivityDraft]:
    """Compute the earliest schedule satisfying every directed dependency."""
    dependencies = dependencies or []
    by_key = {row.activity_key: row for row in rows}
    if len(by_key) != len(rows):
        raise ValueError("activity_key values must be unique")

    for row in rows:
        if row.duration_days < 0:
            raise ValueError(f"{row.activity_key} duration_days cannot be negative")
        if row.kind == "milestone" and row.duration_days != 0:
            raise ValueError(f"{row.activity_key} milestone duration_days must be 0")
    incoming: dict[str, list[DependencyDraft]] = {}
    seen_dependencies: set[str] = set()
    for dependency in dependencies:
        if dependency.dependency_key in seen_dependencies:
            raise ValueError(f"duplicate dependency {dependency.dependency_key}")
        seen_dependencies.add(dependency.dependency_key)
        if dependency.lag_days < 0:
            raise ValueError(f"{dependency.dependency_key} lag_days cannot be negative")
        if dependency.source_activity_key not in by_key:
            raise ValueError(
                f"dependency source {dependency.source_activity_key} does not exist"
            )
        if dependency.target_activity_key not in by_key:
            raise ValueError(
                f"dependency target {dependency.target_activity_key} does not exist"
            )
        if dependency.source_activity_key == dependency.target_activity_key:
            raise ValueError("a dependency cannot link an activity to itself")
        incoming.setdefault(dependency.target_activity_key, []).append(dependency)

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
        constraints = incoming.get(key, [])
        if constraints:
            starts = [
                dependency_constraint_start(
                    dependency,
                    source=resolve(dependency.source_activity_key),
                    target_duration_days=row.duration_days,
                )
                for dependency in constraints
            ]
            start = max(starts)
        finish = start if row.kind == "milestone" else start + timedelta(days=row.duration_days)
        scheduled = replace(row, start_date=start, finish_date=finish)
        visiting.remove(key)
        resolved[key] = scheduled
        return scheduled

    return [resolve(row.activity_key) for row in rows]


def driving_dependency(
    rows: list[ActivityDraft],
    dependencies: list[DependencyDraft],
    target_key: str,
) -> DependencyDraft | None:
    """Return the stable incoming dependency currently controlling target start."""
    by_key = {row.activity_key: row for row in rows}
    target = by_key.get(target_key)
    if target is None:
        return None
    candidates: list[tuple[date, str, DependencyDraft]] = []
    for dependency in dependencies:
        if dependency.target_activity_key != target_key:
            continue
        source = by_key.get(dependency.source_activity_key)
        if source is None:
            continue
        candidates.append(
            (
                dependency_constraint_start(
                    dependency,
                    source=source,
                    target_duration_days=target.duration_days,
                ),
                dependency.dependency_key,
                dependency,
            )
        )
    if not candidates:
        return None
    return max(candidates)[2]


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
