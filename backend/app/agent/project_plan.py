"""Execute explicit plan commands without asking a model to promise a tool call."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.workflow_run import WorkflowRun
from app.projects.locks import lock_project
from app.projects.snapshot import get_project_snapshot
from app.projects.workflow_capabilities import capability_block_message
from app.schemas.workflow_runs import WorkflowRunStartRequest
from app.workflows.runs import WorkflowRunCapabilityConflict, start_workflow_run


def project_plan_command(text: str) -> str | None:
    # Match a complete command, never a quoted example, negation, or compound edit.
    match = re.fullmatch(
        r"(?:(?:can|could|would) you\s+)?(?:please\s+)?"
        r"(create|generate|prepare|draft|update|refresh)\s+(?:a\s+|the\s+|my\s+)?"
        r"(?:pmp|project (?:management )?plan)"
        r"(?:\s+(?:based on|from|using)\s+(?:the\s+|my\s+)?"
        r"(?:(?:current|saved)\s+)?project (?:profile|snapshot))?"
        r"(?:\s+(?:please|now))?[.!?]*",
        " ".join(text.casefold().split()),
    )
    if not match:
        return None
    return (
        "refresh_project_plan"
        if match[1] in {"update", "refresh"}
        else "create_project_plan"
    )


async def queue_project_plan(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    thread_id: uuid.UUID,
    turn_id: uuid.UUID,
    workflow_type: str,
) -> WorkflowRun:
    project = await lock_project(session, project_id=project_id)
    if project is None or project.owner_user_id != user_id:
        raise WorkflowRunCapabilityConflict("Project is no longer available.")
    # Serialize repeated clicks and freeze the profile in the same transaction.
    snapshot = await get_project_snapshot(
        session, project_id=project_id, owner_user_id=user_id
    )
    existing = await session.scalar(
        select(WorkflowRun)
        .where(
            WorkflowRun.project_id == project_id,
            WorkflowRun.queue_scope == settings.workflow_queue_scope,
            WorkflowRun.workflow_type == workflow_type,
            or_(
                WorkflowRun.requested_by_turn_id == turn_id,
                and_(
                    WorkflowRun.state.in_(("queued", "running")),
                    WorkflowRun.frozen_snapshot_fingerprint
                    == snapshot.content_fingerprint,
                ),
            ),
        )
        .order_by(WorkflowRun.created_at.desc())
        .limit(1)
    )
    if existing is not None:
        return existing
    capability = (
        "create_pmp" if workflow_type == "create_project_plan" else "update_pmp"
    )
    if message := capability_block_message(snapshot, capability):
        raise WorkflowRunCapabilityConflict(message)
    latest = next(
        (
            item
            for item in snapshot.latest_artefacts
            if item.workflow_type == "create_pmp"
        ),
        None,
    )
    if workflow_type == "refresh_project_plan" and latest is None:
        raise WorkflowRunCapabilityConflict(
            "Create a Project Management Plan before updating it."
        )
    run, _ = await start_workflow_run(
        session,
        project=project,
        user_id=user_id,
        workflow_type=workflow_type,
        snapshot=snapshot,
        request=WorkflowRunStartRequest(
            idempotency_key=f"chat:{turn_id}:{workflow_type}",
            expected_snapshot_fingerprint=snapshot.content_fingerprint,
            expected_profile_revision=snapshot.profile.profile_revision,
            expected_decision_set_revision=snapshot.decisions.set_revision,
            expected_artefact_version=latest.version if latest else None,
            thread_id=thread_id,
            turn_id=turn_id,
        ),
    )
    await session.commit()
    return run
