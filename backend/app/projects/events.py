from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from app.database.project import Project
from app.database.project_event import ProjectEvent

_FORBIDDEN_PAYLOAD_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "cookie",
    "password",
    "prompt",
    "refresh_token",
    "secret",
    "token",
}


class UnsafeProjectEventPayload(ValueError):
    pass


class ProjectEventProjectNotFound(LookupError):
    pass


def _validate_safe_payload(value: Any, *, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in _FORBIDDEN_PAYLOAD_KEYS:
                raise UnsafeProjectEventPayload(
                    f"project event payload cannot contain {path}.{key}"
                )
            _validate_safe_payload(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_safe_payload(item, path=f"{path}[{index}]")


async def publish_project_event(
    session,
    *,
    project_id: uuid.UUID,
    actor_source: str,
    resource_type: str,
    resource_id: str | uuid.UUID,
    resource_revision: int | None,
    action: str,
    payload: dict[str, Any] | None = None,
    deduplication_key: str | None = None,
    locked_project: Project | None = None,
) -> ProjectEvent:
    safe_payload = dict(payload or {})
    _validate_safe_payload(safe_payload)
    project = locked_project
    if project is None:
        result = await session.execute(
            select(Project).where(Project.id == project_id).with_for_update()
        )
        project = result.scalar_one_or_none()
    if project is None or project.id != project_id:
        raise ProjectEventProjectNotFound(str(project_id))

    if deduplication_key:
        existing_result = await session.execute(
            select(ProjectEvent).where(
                ProjectEvent.project_id == project_id,
                ProjectEvent.deduplication_key == deduplication_key,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            return existing

    project.event_sequence = (project.event_sequence or 0) + 1
    event = ProjectEvent(
        project_id=project_id,
        sequence=project.event_sequence,
        schema_version=1,
        actor_source=actor_source.strip(),
        resource_type=resource_type.strip(),
        resource_id=str(resource_id),
        resource_revision=resource_revision,
        action=action.strip(),
        payload=safe_payload,
        deduplication_key=deduplication_key,
    )
    session.add(event)
    await session.flush()
    return event


async def list_project_events(
    session,
    *,
    project_id: uuid.UUID,
    after: int = 0,
    limit: int = 100,
) -> list[ProjectEvent]:
    result = await session.execute(
        select(ProjectEvent)
        .where(
            ProjectEvent.project_id == project_id,
            ProjectEvent.sequence > after,
        )
        .order_by(ProjectEvent.sequence.asc())
        .limit(limit)
    )
    return list(result.scalars().all())
