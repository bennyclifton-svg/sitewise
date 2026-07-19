from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.project import Project
from app.database.project_decision import ProjectDecision
from app.projects.events import publish_project_event
from app.sitewise.pmp_decisions import extract_decisions


class DecisionNotFound(LookupError):
    pass


class DecisionRevisionConflict(ValueError):
    def __init__(self, expected: int, current: int) -> None:
        self.expected = expected
        self.current = current
        super().__init__(
            f"expected decision revision {expected}, current revision is {current}"
        )


class DecisionSetRevisionConflict(ValueError):
    def __init__(self, expected: int, current: int) -> None:
        self.expected = expected
        self.current = current
        super().__init__(
            f"expected decision set revision {expected}, current revision is {current}"
        )


class DecisionLockedConflict(ValueError):
    pass


class DecisionValidationError(ValueError):
    pass


async def _locked_project(session: AsyncSession, project_id: uuid.UUID) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id).with_for_update()
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise DecisionNotFound(f"project {project_id}")
    return project


async def list_project_decisions(
    session: AsyncSession, *, project_id: uuid.UUID
) -> tuple[list[ProjectDecision], int]:
    project_result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    if project is None:
        raise DecisionNotFound(f"project {project_id}")
    result = await session.execute(
        select(ProjectDecision)
        .where(ProjectDecision.project_id == project_id)
        .order_by(ProjectDecision.label.asc(), ProjectDecision.decision_id.asc())
    )
    return list(result.scalars().all()), project.decision_set_revision


async def get_project_decision(
    session: AsyncSession, *, project_id: uuid.UUID, decision_id: str
) -> tuple[ProjectDecision, int]:
    rows, set_revision = await list_project_decisions(session, project_id=project_id)
    row = next((item for item in rows if item.decision_id == decision_id), None)
    if row is None:
        raise DecisionNotFound(decision_id)
    return row, set_revision


def _check_revisions(
    *,
    row: ProjectDecision,
    project: Project,
    expected_revision: int,
    expected_set_revision: int,
) -> None:
    if row.revision != expected_revision:
        raise DecisionRevisionConflict(expected_revision, row.revision)
    if project.decision_set_revision != expected_set_revision:
        raise DecisionSetRevisionConflict(
            expected_set_revision, project.decision_set_revision
        )


async def _locked_decision(
    session: AsyncSession, *, project_id: uuid.UUID, decision_id: str
) -> ProjectDecision:
    result = await session.execute(
        select(ProjectDecision)
        .where(
            ProjectDecision.project_id == project_id,
            ProjectDecision.decision_id == decision_id,
        )
        .with_for_update()
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise DecisionNotFound(decision_id)
    return row


async def _publish_change(
    session: AsyncSession,
    *,
    project: Project,
    row: ProjectDecision,
    actor_source: str,
    action: str,
) -> None:
    project.decision_set_revision += 1
    await session.flush()
    await publish_project_event(
        session,
        project_id=project.id,
        actor_source=actor_source,
        resource_type="project_decision",
        resource_id=row.decision_id,
        resource_revision=row.revision,
        action=action,
        payload={
            "decision_id": row.decision_id,
            "decision_set_revision": project.decision_set_revision,
            "locked": row.locked,
            "evidence_conflict": row.evidence_conflict,
        },
        locked_project=project,
    )


async def update_project_decision(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    decision_id: str,
    selected: str,
    expected_revision: int,
    expected_set_revision: int,
    actor_source: str,
    provenance: dict[str, Any] | None = None,
    lock: bool | None = None,
) -> tuple[ProjectDecision, int]:
    project = await _locked_project(session, project_id)
    row = await _locked_decision(
        session, project_id=project_id, decision_id=decision_id
    )
    _check_revisions(
        row=row,
        project=project,
        expected_revision=expected_revision,
        expected_set_revision=expected_set_revision,
    )
    valid_values = {str(option.get("value")) for option in row.options}
    if selected not in valid_values:
        raise DecisionValidationError(f"invalid option for decision '{decision_id}'")
    if row.locked and actor_source != "user":
        raise DecisionLockedConflict(f"decision '{decision_id}' is locked")
    row.selected = selected
    row.source = actor_source
    row.provenance = dict(provenance or {})
    if lock is not None:
        row.locked = lock
    row.evidence_conflict = False
    row.agent_suggestion = None
    row.revision += 1
    await _publish_change(
        session,
        project=project,
        row=row,
        actor_source=actor_source,
        action="updated_and_locked" if lock is True else "updated",
    )
    return row, project.decision_set_revision


async def _set_lock(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    decision_id: str,
    expected_revision: int,
    expected_set_revision: int,
    locked: bool,
    actor_source: str,
) -> tuple[ProjectDecision, int]:
    project = await _locked_project(session, project_id)
    row = await _locked_decision(
        session, project_id=project_id, decision_id=decision_id
    )
    _check_revisions(
        row=row,
        project=project,
        expected_revision=expected_revision,
        expected_set_revision=expected_set_revision,
    )
    row.locked = locked
    row.source = actor_source
    row.revision += 1
    await _publish_change(
        session,
        project=project,
        row=row,
        actor_source=actor_source,
        action="locked" if locked else "unlocked",
    )
    return row, project.decision_set_revision


async def lock_project_decision(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    decision_id: str,
    expected_revision: int,
    expected_set_revision: int,
    actor_source: str,
) -> tuple[ProjectDecision, int]:
    return await _set_lock(
        session,
        project_id=project_id,
        decision_id=decision_id,
        expected_revision=expected_revision,
        expected_set_revision=expected_set_revision,
        actor_source=actor_source,
        locked=True,
    )


async def unlock_project_decision(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    decision_id: str,
    expected_revision: int,
    expected_set_revision: int,
    actor_source: str,
) -> tuple[ProjectDecision, int]:
    return await _set_lock(
        session,
        project_id=project_id,
        decision_id=decision_id,
        expected_revision=expected_revision,
        expected_set_revision=expected_set_revision,
        actor_source=actor_source,
        locked=False,
    )


async def locked_selections(
    session: AsyncSession, *, project_id: uuid.UUID
) -> dict[str, str]:
    result = await session.execute(
        select(ProjectDecision.decision_id, ProjectDecision.selected).where(
            ProjectDecision.project_id == project_id,
            ProjectDecision.locked.is_(True),
        )
    )
    return {row.decision_id: row.selected for row in result.all()}


async def sync_decisions_from_markdown(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    markdown: str,
    workflow_type: str,
    locked: dict[str, str] | None = None,
) -> None:
    """Merge generated decisions without ever replacing a locked selection."""
    decisions = extract_decisions(markdown)
    if not decisions:
        return
    project = await _locked_project(session, project_id)
    existing_result = await session.execute(
        select(ProjectDecision)
        .where(ProjectDecision.project_id == project_id)
        .with_for_update()
    )
    existing = {row.decision_id: row for row in existing_result.scalars().all()}
    for decision in decisions:
        row = existing.get(decision.id)
        if row is None:
            row = ProjectDecision(
                project_id=project_id,
                decision_id=decision.id,
                section=decision.section,
                label=decision.label,
                options=[dict(option) for option in decision.options],
                selected=decision.selected,
                source=decision.source,
                workflow_type=workflow_type,
                provenance={"workflow_type": workflow_type},
            )
            session.add(row)
            await session.flush()
            existing[decision.id] = row
            await _publish_change(
                session,
                project=project,
                row=row,
                actor_source="workflow",
                action="created",
            )
            continue

        incoming_differs = decision.selected != row.selected
        if row.locked:
            incoming_conflict = decision.evidence_conflict or incoming_differs
            incoming_suggestion = decision.agent_suggestion
            if incoming_suggestion is None and incoming_differs:
                incoming_suggestion = decision.selected
            conflict_changed = (
                row.evidence_conflict != incoming_conflict
                or row.agent_suggestion != incoming_suggestion
            )
            row.section = decision.section
            row.label = decision.label
            row.options = [dict(option) for option in decision.options]
            row.workflow_type = workflow_type
            if conflict_changed:
                row.evidence_conflict = incoming_conflict
                row.agent_suggestion = incoming_suggestion
                row.revision += 1
                await _publish_change(
                    session,
                    project=project,
                    row=row,
                    actor_source="workflow",
                    action="conflict_detected"
                    if incoming_conflict
                    else "conflict_cleared",
                )
            continue

        changed = any(
            (
                incoming_differs,
                row.section != decision.section,
                row.label != decision.label,
                row.options != [dict(option) for option in decision.options],
                row.source != decision.source,
            )
        )
        if changed:
            row.section = decision.section
            row.label = decision.label
            row.options = [dict(option) for option in decision.options]
            row.selected = decision.selected
            row.source = decision.source
            row.workflow_type = workflow_type
            row.provenance = {"workflow_type": workflow_type}
            row.evidence_conflict = False
            row.agent_suggestion = None
            row.revision += 1
            await _publish_change(
                session,
                project=project,
                row=row,
                actor_source="workflow",
                action="updated",
            )
