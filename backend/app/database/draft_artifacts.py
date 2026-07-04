import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.draft_artifact import DraftArtifact


async def next_draft_version(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    workflow_type: str,
) -> int:
    result = await session.execute(
        select(func.max(DraftArtifact.version)).where(
            DraftArtifact.project_id == project_id,
            DraftArtifact.workflow_type == workflow_type,
        )
    )
    current = result.scalar_one_or_none()
    return int(current or 0) + 1


async def create_draft_artifact(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    workflow_type: str,
    title: str,
    workspace_path: str,
    author_user_id: uuid.UUID,
    content_markdown: str,
    model: str | None,
    runtime: str,
    provenance_metadata: dict,
) -> DraftArtifact:
    version = await next_draft_version(
        session,
        project_id=project_id,
        workflow_type=workflow_type,
    )
    draft = DraftArtifact(
        project_id=project_id,
        workflow_type=workflow_type,
        version=version,
        status="draft",
        title=title,
        workspace_path=workspace_path,
        author_user_id=author_user_id,
        content_markdown=content_markdown,
        model=model,
        runtime=runtime,
        provenance_metadata=provenance_metadata,
    )
    session.add(draft)
    await session.flush()
    await session.refresh(draft)
    return draft


async def get_latest_draft_artifact(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    workflow_type: str,
) -> DraftArtifact | None:
    result = await session.execute(
        select(DraftArtifact)
        .where(
            DraftArtifact.project_id == project_id,
            DraftArtifact.workflow_type == workflow_type,
        )
        .order_by(DraftArtifact.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_draft_artifact_by_workspace_path(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    workspace_path: str,
) -> DraftArtifact | None:
    result = await session.execute(
        select(DraftArtifact)
        .where(
            DraftArtifact.project_id == project_id,
            DraftArtifact.workspace_path == workspace_path,
        )
        .order_by(DraftArtifact.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_draft_artifact_summaries(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    workflow_types: list[str],
) -> dict[str, dict]:
    if not workflow_types:
        return {}

    result = await session.execute(
        select(
            DraftArtifact.id,
            DraftArtifact.project_id,
            DraftArtifact.workflow_type,
            DraftArtifact.version,
            DraftArtifact.status,
            DraftArtifact.title,
            DraftArtifact.workspace_path,
            DraftArtifact.author_user_id,
            DraftArtifact.model,
            DraftArtifact.runtime,
            DraftArtifact.created_at,
            DraftArtifact.updated_at,
        )
        .where(
            DraftArtifact.project_id == project_id,
            DraftArtifact.workflow_type.in_(workflow_types),
        )
        .order_by(DraftArtifact.workflow_type.asc(), DraftArtifact.version.desc())
    )
    summaries: dict[str, dict] = {}
    for row in result.mappings().all():
        workflow_type = row["workflow_type"]
        if workflow_type not in summaries:
            summaries[workflow_type] = dict(row)
    return summaries


async def get_draft_artifact(
    session: AsyncSession,
    draft_id: uuid.UUID,
) -> DraftArtifact | None:
    return await session.get(DraftArtifact, draft_id)


async def update_draft_content(
    session: AsyncSession,
    draft: DraftArtifact,
    *,
    content_markdown: str,
) -> DraftArtifact:
    draft.content_markdown = content_markdown
    await session.flush()
    await session.refresh(draft)
    return draft


async def create_draft_revision(
    session: AsyncSession,
    *,
    draft: DraftArtifact,
    author_user_id: uuid.UUID,
    content_markdown: str,
    edit_source: str,
) -> DraftArtifact:
    provenance_metadata = dict(draft.provenance_metadata or {})
    provenance_metadata["edited_from"] = {
        "draft_id": str(draft.id),
        "version": draft.version,
        "workspace_path": draft.workspace_path,
        "edit_source": edit_source,
    }
    return await create_draft_artifact(
        session,
        project_id=draft.project_id,
        workflow_type=draft.workflow_type,
        title=draft.title,
        workspace_path=draft.workspace_path,
        author_user_id=author_user_id,
        content_markdown=content_markdown,
        model=draft.model,
        runtime=draft.runtime,
        provenance_metadata=provenance_metadata,
    )


async def accept_draft(
    session: AsyncSession,
    draft: DraftArtifact,
) -> DraftArtifact:
    draft.status = "accepted"
    await session.flush()
    await session.refresh(draft)
    return draft
