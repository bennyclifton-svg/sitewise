from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.cost_plan.service import accept_cost_plan_version
from app.projects.artefact_revisions import (
    ArtefactPolicyViolation,
    ArtefactRevisionConflict,
    revise,
)
from app.projects.decisions import locked_selections, sync_decisions_from_markdown
from app.projects.events import publish_project_event
from app.sitewise.pmp_decisions import render_decisions_static, restamp_decisions
from app.workflows.consultant_procurement import (
    is_consultant_procurement_workflow,
    sync_consultant_procurement_draft_workspace,
)
from app.workflows.create_cost_plan import (
    is_cost_plan_workflow,
    sync_cost_plan_revision_artifacts,
)
from app.workflows.create_pmp import is_pmp_workflow, sync_pmp_draft_workspace


async def revise_workflow_artefact(
    session: AsyncSession,
    *,
    project: Project,
    draft: DraftArtifact,
    expected_base_version: int,
    author_user_id: uuid.UUID,
    content_markdown: str,
    actor_source: str,
) -> DraftArtifact:
    if draft.project_id != project.id:
        raise ArtefactPolicyViolation("artefact does not belong to project")
    if draft.workflow_type == "tender_report":
        raise ArtefactPolicyViolation("Tender reports can only be revised by TCM")
    if is_cost_plan_workflow(draft.workflow_type):
        raise ArtefactPolicyViolation(
            "Cost Plans are canonical typed state; use the row, contingency, assumption, or refresh actions"
        )

    if is_pmp_workflow(draft.workflow_type):
        locked = await locked_selections(session, project_id=project.id)
        content_markdown = restamp_decisions(content_markdown, locked)

    result = await revise(
        session,
        base_revision=draft,
        expected_base_version=expected_base_version,
        author_user_id=author_user_id,
        content_markdown=content_markdown,
        actor_source=actor_source,
    )
    revision = result.revision
    if is_pmp_workflow(revision.workflow_type):
        await sync_pmp_draft_workspace(
            session, project=project, draft=revision, markdown=content_markdown
        )
        await sync_decisions_from_markdown(
            session,
            project_id=project.id,
            markdown=content_markdown,
            workflow_type=revision.workflow_type,
        )
    elif is_cost_plan_workflow(revision.workflow_type):
        await sync_cost_plan_revision_artifacts(
            session, project=project, draft=revision, markdown=content_markdown
        )
        await sync_decisions_from_markdown(
            session,
            project_id=project.id,
            markdown=content_markdown,
            workflow_type=revision.workflow_type,
        )
    elif is_consultant_procurement_workflow(revision.workflow_type):
        await sync_consultant_procurement_draft_workspace(
            session, project=project, draft=revision, markdown=content_markdown
        )
    else:
        raise ArtefactPolicyViolation(
            f"{revision.workflow_type} is not an editable artefact"
        )
    return revision


async def accept_workflow_artefact(
    session: AsyncSession,
    *,
    project: Project,
    draft: DraftArtifact,
    expected_version: int,
    actor_source: str,
) -> DraftArtifact:
    if draft.project_id != project.id:
        raise ArtefactPolicyViolation("artefact does not belong to project")
    if draft.workflow_type == "tender_report":
        raise ArtefactPolicyViolation("Tender approval is owned by TCM")
    if draft.version != expected_version:
        raise ArtefactRevisionConflict(
            f"Expected {draft.workflow_type} v{expected_version}, received v{draft.version}"
        )

    from app.database.draft_artifacts import get_latest_draft_artifact

    latest = await get_latest_draft_artifact(
        session, project_id=project.id, workflow_type=draft.workflow_type
    )
    if latest is None or latest.id != draft.id:
        current = latest.version if latest is not None else 0
        raise ArtefactRevisionConflict(
            f"Expected {draft.workflow_type} v{expected_version}, current version is v{current}"
        )

    draft.status = "accepted"
    if is_pmp_workflow(draft.workflow_type):
        static_markdown = render_decisions_static(draft.content_markdown)
        await sync_pmp_draft_workspace(
            session, project=project, draft=draft, markdown=static_markdown
        )
        await sync_decisions_from_markdown(
            session,
            project_id=project.id,
            markdown=draft.content_markdown,
            workflow_type=draft.workflow_type,
        )
    elif is_cost_plan_workflow(draft.workflow_type):
        await accept_cost_plan_version(
            session,
            project_id=project.id,
            artefact_revision_id=draft.id,
        )
        await sync_cost_plan_revision_artifacts(
            session, project=project, draft=draft, markdown=draft.content_markdown
        )
    elif is_consultant_procurement_workflow(draft.workflow_type):
        await sync_consultant_procurement_draft_workspace(
            session, project=project, draft=draft, markdown=draft.content_markdown
        )
    else:
        raise ArtefactPolicyViolation(
            f"{draft.workflow_type} has no acceptance transition"
        )
    await session.flush()
    await publish_project_event(
        session,
        project_id=project.id,
        actor_source=actor_source,
        resource_type="artefact_revision",
        resource_id=draft.id,
        resource_revision=draft.version,
        action="accepted",
        payload={"workflow_type": draft.workflow_type, "status": draft.status},
        deduplication_key=f"artefact:{draft.id}:accepted",
    )
    return draft
