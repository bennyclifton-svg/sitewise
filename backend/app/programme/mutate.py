from __future__ import annotations

import re

from app.programme.schedule import ActivityDraft, rollup_stages, schedule_activities
from app.programme.schemas import (
    MAX_PROGRAMME_OPERATIONS,
    ProgrammeActivityInput,
    ProgrammeOperation,
    normalize_activity_values,
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def activity_slug(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return slug or "activity"


def apply_operations(
    activities: list[ProgrammeActivityInput],
    operations: list[ProgrammeOperation],
) -> list[ProgrammeActivityInput]:
    if not operations or len(operations) > MAX_PROGRAMME_OPERATIONS:
        raise ValueError(
            f"operations must contain between 1 and {MAX_PROGRAMME_OPERATIONS} items"
        )
    rows = [item.model_copy(deep=True) for item in activities]
    for operation in operations:
        rows = _apply_one(rows, operation)
    return reschedule(rows)


def reschedule(activities: list[ProgrammeActivityInput]) -> list[ProgrammeActivityInput]:
    drafts = [
        ActivityDraft(
            activity_key=item.activity_key,
            kind=item.kind,
            start_date=item.start_date,
            duration_days=item.duration_days,
            parent_key=item.parent_key,
            predecessor_key=item.predecessor_key,
            lag_days=item.lag_days,
            name=item.name,
            display_order=item.display_order,
            assumption=item.assumption,
            notes=item.notes,
        )
        for item in activities
    ]
    scheduled = rollup_stages(schedule_activities(drafts))
    by_key = {item.activity_key: item for item in activities}
    return [
        by_key[row.activity_key].model_copy(
            update={
                "start_date": row.start_date,
                "duration_days": row.duration_days,
                "finish_date": row.finish_date,
                "predecessor_key": row.predecessor_key,
                "lag_days": row.lag_days,
            }
        )
        for row in scheduled
    ]


def _apply_one(
    rows: list[ProgrammeActivityInput],
    operation: ProgrammeOperation,
) -> list[ProgrammeActivityInput]:
    if operation.operation == "ADD":
        return _add(rows, operation)
    index = _index(rows, operation.target_id)
    if operation.operation == "UPDATE":
        return _update(rows, index, operation)
    if operation.operation == "DELETE":
        return _delete(rows, operation.target_id)
    if operation.operation == "MOVE":
        return _move(rows, operation)
    raise ValueError(f"unsupported operation {operation.operation}")


def _add(
    rows: list[ProgrammeActivityInput],
    operation: ProgrammeOperation,
) -> list[ProgrammeActivityInput]:
    values = normalize_activity_values(dict(operation.values))
    values.setdefault("kind", operation.target_type)
    name = str(values.get("name") or "").strip()
    if not name:
        raise ValueError("ADD requires a name")
    key = str(values.get("activity_key") or activity_slug(name))
    key = _unique_key(rows, key)
    values["activity_key"] = key
    if values.get("kind") != "stage" and not values.get("parent_key"):
        inferred = _infer_parent_key(rows, operation, values)
        if inferred:
            values["parent_key"] = inferred
    values.setdefault("display_order", _next_order(rows, values.get("parent_key")))
    if "start_date" not in values:
        parent = _find(rows, values.get("parent_key"))
        values["start_date"] = parent.start_date if parent else rows[0].start_date
    values.setdefault("duration_days", 0 if operation.target_type == "milestone" else 14)
    item = ProgrammeActivityInput.model_validate(values)
    if item.kind == "stage" and item.parent_key:
        raise ValueError("stage cannot have parent_key")
    if item.kind != "stage" and item.parent_key and _find(rows, item.parent_key) is None:
        raise ValueError(f"parent {item.parent_key!r} was not found")
    if operation.reference_id:
        insert_at = _insert_index(rows, operation.reference_id, operation.placement)
        if item.kind == "stage" and operation.placement != "before":
            insert_at = _after_stage_block(rows, operation.reference_id, insert_at)
        rows.insert(insert_at, item)
    else:
        rows.append(item)
    return _tree_order(rows)


def _update(
    rows: list[ProgrammeActivityInput],
    index: int,
    operation: ProgrammeOperation,
) -> list[ProgrammeActivityInput]:
    current = rows[index]
    values = current.model_dump()
    incoming = normalize_activity_values(dict(operation.values))
    if "start_date" in incoming and current.predecessor_key:
        incoming["predecessor_key"] = None
        incoming["lag_days"] = 0
    values.update(incoming)
    values["activity_key"] = current.activity_key
    values["kind"] = current.kind
    rows[index] = ProgrammeActivityInput.model_validate(values)
    return rows


def _delete(
    rows: list[ProgrammeActivityInput],
    target_id: str | None,
) -> list[ProgrammeActivityInput]:
    if not target_id:
        raise ValueError("DELETE requires target_id")
    remaining = [
        item
        for item in rows
        if item.activity_key != target_id and item.parent_key != target_id
    ]
    if len(remaining) == len(rows):
        raise ValueError(f"activity {target_id!r} was not found")
    cleared: list[ProgrammeActivityInput] = []
    for item in remaining:
        if item.predecessor_key == target_id:
            cleared.append(
                item.model_copy(update={"predecessor_key": None, "lag_days": 0})
            )
        else:
            cleared.append(item)
    return cleared


def _move(
    rows: list[ProgrammeActivityInput],
    operation: ProgrammeOperation,
) -> list[ProgrammeActivityInput]:
    item = rows[_index(rows, operation.target_id)]
    reference = rows[_index(rows, operation.reference_id)]
    placement = operation.placement or "after"
    if item.activity_key == reference.activity_key:
        return rows
    if item.kind == "stage":
        return _move_stage(rows, item, reference, placement)
    return _move_child(rows, item, reference, placement)


def _move_stage(
    rows: list[ProgrammeActivityInput],
    item: ProgrammeActivityInput,
    reference: ProgrammeActivityInput,
    placement: str,
) -> list[ProgrammeActivityInput]:
    ref_stage = (
        reference
        if reference.kind == "stage"
        else _find(rows, reference.parent_key)
    )
    if ref_stage is None or ref_stage.activity_key == item.activity_key:
        return rows
    block_keys = {item.activity_key} | {
        row.activity_key for row in rows if row.parent_key == item.activity_key
    }
    block = [row for row in rows if row.activity_key in block_keys]
    remaining = [row for row in rows if row.activity_key not in block_keys]
    insert_at = next(
        index
        for index, row in enumerate(remaining)
        if row.activity_key == ref_stage.activity_key
    )
    if placement == "after":
        insert_at = _after_stage_block(remaining, ref_stage.activity_key, insert_at + 1)
    return _tree_order(remaining[:insert_at] + block + remaining[insert_at:])


def _move_child(
    rows: list[ProgrammeActivityInput],
    item: ProgrammeActivityInput,
    reference: ProgrammeActivityInput,
    placement: str,
) -> list[ProgrammeActivityInput]:
    remaining = [row for row in rows if row.activity_key != item.activity_key]
    if reference.kind == "stage":
        if placement == "after":
            parent_key = reference.activity_key
            insert_at = _index(remaining, reference.activity_key) + 1
        else:
            previous = _previous_stage(remaining, reference)
            if previous:
                parent_key = previous.activity_key
                insert_at = _after_stage_block(
                    remaining, previous.activity_key, _index(remaining, previous.activity_key) + 1
                )
            else:
                parent_key = reference.activity_key
                insert_at = _index(remaining, reference.activity_key) + 1
    else:
        parent_key = reference.parent_key
        insert_at = _insert_index(remaining, reference.activity_key, placement)
    moved = item.model_copy(update={"parent_key": parent_key})
    return _tree_order(remaining[:insert_at] + [moved] + remaining[insert_at:])


def _tree_order(
    rows: list[ProgrammeActivityInput],
) -> list[ProgrammeActivityInput]:
    stages = [row for row in rows if row.kind == "stage"]
    children: dict[str, list[ProgrammeActivityInput]] = {}
    loose: list[ProgrammeActivityInput] = []
    for row in rows:
        if row.kind == "stage":
            continue
        if row.parent_key:
            children.setdefault(row.parent_key, []).append(row)
        else:
            loose.append(row)
    ordered: list[ProgrammeActivityInput] = []
    for stage in stages:
        ordered.append(stage)
        ordered.extend(children.pop(stage.activity_key, []))
    for leftover in children.values():
        ordered.extend(leftover)
    ordered.extend(loose)
    return [
        row.model_copy(update={"display_order": index})
        for index, row in enumerate(ordered)
    ]


def _insert_index(
    rows: list[ProgrammeActivityInput],
    reference_id: str,
    placement: str | None,
) -> int:
    index = _index(rows, reference_id)
    return index if placement == "before" else index + 1


def _after_stage_block(
    rows: list[ProgrammeActivityInput],
    reference_id: str,
    start: int,
) -> int:
    reference = _find(rows, reference_id)
    stage_key = (
        reference.activity_key
        if reference and reference.kind == "stage"
        else (reference.parent_key if reference else None)
    )
    insert_at = start
    while insert_at < len(rows) and rows[insert_at].parent_key == stage_key:
        insert_at += 1
    return insert_at


def _previous_stage(
    rows: list[ProgrammeActivityInput],
    reference: ProgrammeActivityInput,
) -> ProgrammeActivityInput | None:
    previous: ProgrammeActivityInput | None = None
    for row in rows:
        if row.activity_key == reference.activity_key:
            return previous
        if row.kind == "stage":
            previous = row
    return previous


def _index(rows: list[ProgrammeActivityInput], key: str | None) -> int:
    if not key:
        raise ValueError("target_id is required")
    for index, item in enumerate(rows):
        if item.activity_key == key:
            return index
    raise ValueError(f"activity {key!r} was not found")


def _infer_parent_key(
    rows: list[ProgrammeActivityInput],
    operation: ProgrammeOperation,
    values: dict[str, object],
) -> str | None:
    for candidate in (operation.reference_id, values.get("predecessor_key")):
        parent = _parent_of(rows, str(candidate) if candidate else None)
        if parent:
            return parent
    stage = next((row for row in rows if row.kind == "stage"), None)
    return stage.activity_key if stage else None


def _parent_of(
    rows: list[ProgrammeActivityInput], key: str | None
) -> str | None:
    item = _find(rows, key)
    if item is None:
        return None
    return item.activity_key if item.kind == "stage" else item.parent_key


def _find(
    rows: list[ProgrammeActivityInput], key: str | None
) -> ProgrammeActivityInput | None:
    if not key:
        return None
    return next((item for item in rows if item.activity_key == key), None)


def _unique_key(rows: list[ProgrammeActivityInput], key: str) -> str:
    existing = {item.activity_key for item in rows}
    if key not in existing:
        return key
    suffix = 2
    while f"{key}-{suffix}" in existing:
        suffix += 1
    return f"{key}-{suffix}"


def _next_order(rows: list[ProgrammeActivityInput], parent_key: object) -> int:
    siblings = [
        item.display_order
        for item in rows
        if item.parent_key == parent_key
    ]
    return max(siblings, default=-1) + 1
