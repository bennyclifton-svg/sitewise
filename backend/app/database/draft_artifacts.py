import uuid
from pathlib import PurePosixPath

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
    expected_base_version: int,
    actor_source: str = "workflow",
) -> DraftArtifact:
    from app.inbox.paths import build_storage_key
    from app.projects.artefact_revisions import ExportSpec, publish

    exports = [
        ExportSpec(
            export_type="markdown",
            workspace_path=workspace_path,
            storage_key=build_storage_key(str(project_id), workspace_path),
        )
    ]
    if workflow_type == "create_cost_plan":
        workbook_path = str(
            PurePosixPath(workspace_path).parent
            / f"Cost_Plan_v{expected_base_version + 1:02d}.draft.xlsx"
        )
        exports.append(
            ExportSpec(
                export_type="workbook",
                workspace_path=workbook_path,
                storage_key=build_storage_key(str(project_id), workbook_path),
            )
        )

    result = await publish(
        session,
        project_id=project_id,
        workflow_type=workflow_type,
        expected_base_version=expected_base_version,
        title=title,
        workspace_path=workspace_path,
        author_user_id=author_user_id,
        content_markdown=content_markdown,
        model=model,
        runtime=runtime,
        provenance=provenance_metadata,
        actor_source=actor_source,
        exports=exports,
    )
    return result.revision


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


async def get_latest_consultant_procurement_draft_summaries(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    prefix: str = "consultant_procurement_",
) -> dict[str, dict]:
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
            DraftArtifact.workflow_type.like(f"{prefix}%"),
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
