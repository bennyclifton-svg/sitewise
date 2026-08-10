"""Small explicit shared project objects used across artefacts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.database.project import Project
from app.projects.dependencies import DirtyCategory, mark_project_dirty
from app.projects.events import publish_project_event


ProjectObjectKind = Literal[
    "consultant",
    "stakeholder",
    "scope_item",
    "ffe_item",
    "cost_item",
    "milestone",
    "procurement_package",
    "project_decision",
]


class SharedProjectObjectUpdate(BaseModel):
    expected_revision: int = Field(ge=0)
    value: dict[str, Any]
    user_protected: bool = False


class SharedProjectObject(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    kind: ProjectObjectKind
    revision: int = Field(ge=1)
    value: dict[str, Any]
    source: Literal["user", "ai", "evidence", "system"]
    user_protected: bool = False
    updated_at: datetime


class SharedProjectObjectConflict(RuntimeError):
    pass


_DIRTY_BY_KIND: dict[ProjectObjectKind, tuple[DirtyCategory, ...]] = {
    "consultant": ("consultants_dirty",),
    "stakeholder": ("consultants_dirty",),
    "scope_item": ("scope_dirty",),
    "ffe_item": ("ffe_dirty", "cost_dirty"),
    "cost_item": ("cost_dirty",),
    "milestone": ("programme_dirty",),
    "procurement_package": ("procurement_dirty",),
    "project_decision": ("design_dirty", "procurement_dirty"),
}


def upsert_shared_project_object(
    project: Project,
    *,
    kind: ProjectObjectKind,
    object_id: str,
    update: SharedProjectObjectUpdate,
    source: Literal["user", "ai", "evidence", "system"],
    now: datetime | None = None,
) -> SharedProjectObject:
    """Mutate a loaded Project only; persistence callers must use the locked writer."""
    metadata = dict(project.project_metadata or {})
    knowledge = dict(metadata.get("shared_knowledge") or {})
    key = f"{kind}:{object_id}"
    existing = knowledge.get(key)
    current_revision = (
        int(existing.get("revision", 0)) if isinstance(existing, dict) else 0
    )
    if current_revision != update.expected_revision:
        raise SharedProjectObjectConflict(
            f"Expected {key} revision {update.expected_revision}, current revision is {current_revision}"
        )
    if (
        isinstance(existing, dict)
        and existing.get("user_protected")
        and source != "user"
    ):
        raise SharedProjectObjectConflict(f"{key} is protected by the user")
    result = SharedProjectObject(
        id=object_id,
        kind=kind,
        revision=current_revision + 1,
        value=update.value,
        source=source,
        user_protected=update.user_protected,
        updated_at=now or datetime.now(UTC),
    )
    knowledge[key] = result.model_dump(mode="json")
    metadata["shared_knowledge"] = knowledge
    project.project_metadata = metadata
    mark_project_dirty(project, _DIRTY_BY_KIND[kind])
    return result


async def write_shared_project_object(
    session,
    *,
    project: Project,
    kind: ProjectObjectKind,
    object_id: str,
    update: SharedProjectObjectUpdate,
    source: Literal["user", "ai", "evidence", "system"],
    now: datetime | None = None,
) -> SharedProjectObject:
    """Persist one shared fact while serializing its project-context revision."""
    await session.refresh(project, with_for_update=True)
    result = upsert_shared_project_object(
        project,
        kind=kind,
        object_id=object_id,
        update=update,
        source=source,
        now=now,
    )
    await publish_project_event(
        session,
        project_id=project.id,
        actor_source=source,
        resource_type="shared_project_object",
        resource_id=object_id,
        resource_revision=result.revision,
        action="upserted",
        payload={"kind": kind},
        changes_context=True,
        locked_project=project,
    )
    return result
