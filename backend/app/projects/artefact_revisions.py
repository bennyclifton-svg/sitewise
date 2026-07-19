from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.activity_events import record_activity_events
from app.database.artefact_export import ArtefactExport
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.projects.events import publish_project_event
from app.schemas.projects import WorkflowTraceEvent


class ArtefactRevisionConflict(RuntimeError):
    pass


class ArtefactPolicyViolation(ValueError):
    pass


class ArtefactRevisionNotFound(LookupError):
    pass


EditPolicy = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class ExportSpec:
    export_type: str
    workspace_path: str
    storage_key: str


@dataclass(frozen=True, slots=True)
class ArtefactRevisionResult:
    revision: DraftArtifact
    export_jobs: tuple[ArtefactExport, ...]


async def _lock_revision_stream(
    session: AsyncSession, *, project_id: uuid.UUID, workflow_type: str
) -> None:
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        lock_key = f"artefact-revision:{project_id}:{workflow_type}"
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": lock_key},
        )
        return

    # Non-Postgres unit fixtures still serialize through the owning project row.
    await session.execute(select(Project.id).where(Project.id == project_id).with_for_update())


async def _latest_revision(
    session: AsyncSession, *, project_id: uuid.UUID, workflow_type: str
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


async def publish(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    workflow_type: str,
    expected_base_version: int,
    title: str,
    workspace_path: str,
    author_user_id: uuid.UUID,
    content_markdown: str,
    model: str | None,
    runtime: str,
    provenance: dict,
    actor_source: str,
    exports: Sequence[ExportSpec] = (),
    policy: EditPolicy | None = None,
) -> ArtefactRevisionResult:
    if expected_base_version < 0:
        raise ArtefactPolicyViolation("expected_base_version must be zero or greater")
    if not workflow_type.strip():
        raise ArtefactPolicyViolation("workflow_type is required")
    if policy is not None:
        content_markdown = policy(content_markdown)

    await _lock_revision_stream(
        session, project_id=project_id, workflow_type=workflow_type
    )
    latest = await _latest_revision(
        session, project_id=project_id, workflow_type=workflow_type
    )
    current_version = latest.version if latest is not None else 0
    if current_version != expected_base_version:
        raise ArtefactRevisionConflict(
            f"Expected {workflow_type} v{expected_base_version}, current version is v{current_version}"
        )

    version = current_version + 1
    revision = DraftArtifact(
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
        provenance_metadata={
            **provenance,
            "revision": version,
            "expected_base_version": expected_base_version,
            "actor_source": actor_source,
        },
    )
    session.add(revision)
    await session.flush()

    jobs: list[ArtefactExport] = []
    seen_types: set[str] = set()
    for spec in exports:
        export_type = spec.export_type.strip().lower()
        if not export_type or export_type in seen_types:
            raise ArtefactPolicyViolation("export types must be non-empty and unique")
        seen_types.add(export_type)
        job = ArtefactExport(
            project_id=project_id,
            draft_id=revision.id,
            revision=version,
            export_type=export_type,
            workspace_path=spec.workspace_path,
            storage_key=spec.storage_key,
            status="pending",
        )
        session.add(job)
        jobs.append(job)
    await session.flush()

    await publish_project_event(
        session,
        project_id=project_id,
        actor_source=actor_source,
        resource_type="artefact_revision",
        resource_id=revision.id,
        resource_revision=version,
        action="published",
        payload={
            "workflow_type": workflow_type,
            "status": revision.status,
            "export_status": "pending" if jobs else "not_required",
        },
        deduplication_key=f"artefact:{revision.id}:published",
    )
    await record_activity_events(
        session,
        project_id=project_id,
        source=actor_source,
        run_id=uuid.uuid4(),
        reference_type="draft_artifact",
        reference_id=revision.id,
        events=[
            WorkflowTraceEvent(
                step="artefact_revision",
                status="complete",
                message=f"Published {workflow_type} revision v{version}.",
                metadata={"version": version, "workflow_type": workflow_type},
            )
        ],
    )
    await session.refresh(revision)
    return ArtefactRevisionResult(revision=revision, export_jobs=tuple(jobs))


async def revise(
    session: AsyncSession,
    *,
    base_revision: DraftArtifact,
    expected_base_version: int,
    author_user_id: uuid.UUID,
    content_markdown: str,
    actor_source: str,
    exports: Sequence[ExportSpec] = (),
    policy: EditPolicy | None = None,
) -> ArtefactRevisionResult:
    provenance = dict(base_revision.provenance_metadata or {})
    provenance["edited_from"] = {
        "draft_id": str(base_revision.id),
        "version": base_revision.version,
        "workspace_path": base_revision.workspace_path,
        "edit_source": actor_source,
    }
    return await publish(
        session,
        project_id=base_revision.project_id,
        workflow_type=base_revision.workflow_type,
        expected_base_version=expected_base_version,
        title=base_revision.title,
        workspace_path=base_revision.workspace_path,
        author_user_id=author_user_id,
        content_markdown=content_markdown,
        model=base_revision.model,
        runtime=base_revision.runtime,
        provenance=provenance,
        actor_source=actor_source,
        exports=exports,
        policy=policy,
    )


async def list_revisions(
    session: AsyncSession, *, project_id: uuid.UUID, workflow_type: str
) -> list[DraftArtifact]:
    result = await session.execute(
        select(DraftArtifact)
        .where(
            DraftArtifact.project_id == project_id,
            DraftArtifact.workflow_type == workflow_type,
        )
        .order_by(DraftArtifact.version.desc())
    )
    return list(result.scalars().all())


async def get_revision(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    workflow_type: str,
    version: int,
) -> DraftArtifact:
    result = await session.execute(
        select(DraftArtifact).where(
            DraftArtifact.project_id == project_id,
            DraftArtifact.workflow_type == workflow_type,
            DraftArtifact.version == version,
        )
    )
    revision = result.scalar_one_or_none()
    if revision is None:
        raise ArtefactRevisionNotFound(f"{workflow_type} v{version}")
    return revision


async def regenerate_exports(
    session: AsyncSession, *, revision: DraftArtifact
) -> tuple[ArtefactExport, ...]:
    result = await session.execute(
        select(ArtefactExport).where(ArtefactExport.draft_id == revision.id)
    )
    jobs = tuple(result.scalars().all())
    for job in jobs:
        job.status = "pending"
        job.error = None
    await session.flush()
    return jobs


async def set_export_result(
    session: AsyncSession,
    *,
    job: ArtefactExport,
    content_hash: str | None = None,
    error: str | None = None,
) -> ArtefactExport:
    job.attempt_count += 1
    job.content_hash = content_hash
    job.error = error
    job.status = "failed" if error else "ready"
    await session.flush()
    await publish_project_event(
        session,
        project_id=job.project_id,
        actor_source="artefact_exporter",
        resource_type="artefact_revision",
        resource_id=job.draft_id,
        resource_revision=job.revision,
        action=f"export_{job.status}",
        payload={"export_type": job.export_type, "status": job.status},
        deduplication_key=f"artefact-export:{job.id}:{job.attempt_count}:{job.status}",
    )
    return job


async def set_export_result_for_path(
    session: AsyncSession,
    *,
    revision: DraftArtifact,
    workspace_path: str,
    content_hash: str | None = None,
    error: str | None = None,
) -> ArtefactExport | None:
    result = await session.execute(
        select(ArtefactExport).where(
            ArtefactExport.draft_id == revision.id,
            ArtefactExport.workspace_path == workspace_path,
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        return None
    return await set_export_result(
        session, job=job, content_hash=content_hash, error=error
    )


async def mark_stale(
    session: AsyncSession, *, revision: DraftArtifact, reason: str
) -> DraftArtifact:
    revision.is_stale = True
    revision.stale_reason = reason.strip()
    await session.flush()
    await publish_project_event(
        session,
        project_id=revision.project_id,
        actor_source="system",
        resource_type="artefact_revision",
        resource_id=revision.id,
        resource_revision=revision.version,
        action="marked_stale",
        payload={"reason": revision.stale_reason},
        deduplication_key=f"artefact:{revision.id}:stale:{revision.stale_reason}",
    )
    return revision
