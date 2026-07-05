import asyncio
import mimetypes
import time
import uuid
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.billing.entitlements import require_active_entitlement
from app.database.activity_events import (
    delete_project_activity_runs,
    list_project_activity_runs,
)
from app.database.chats import create_thread, title_from_message
from app.database.draft_artifacts import (
    accept_draft,
    create_draft_revision,
    get_draft_artifact,
    get_latest_draft_artifact_summaries,
    get_latest_draft_artifact,
)
from app.database.projects import (
    create_project,
    ensure_default_project_catalog,
    get_project,
    list_projects,
    project_overlay_summary,
    user_owns_project,
)
from app.database.session import get_db
from app.database.draft_artifact import DraftArtifact
from app.database.source_document import SourceDocument
from app.database.users import ensure_user_exists
from app.schemas.chat import ThreadResponse
from app.schemas.projects import (
    CreateCostPlanRequest,
    CreateCostPlanResponse,
    CreateProjectRequest,
    CreatePmpRequest,
    CreatePmpResponse,
    DeleteProjectActivityRequest,
    DeleteProjectActivityResponse,
    PatchDraftRequest,
    UpdatePmpRequest,
    SortFilesRequest,
    SortFilesResponse,
    DraftArtifactResponse,
    DraftArtifactSummary,
    EvidencePreview,
    InboxUploadResponse,
    InboxUploadResult,
    PdfAnalyzeResponse,
    PdfSheetProposal,
    PlatformKnowledgeBucket,
    PlatformKnowledgeStatus,
    ProjectActivityEvent,
    ProjectActivityReferences,
    ProjectActivityResponse,
    ProjectActivityRun,
    ProjectCockpitBootstrapResponse,
    ProjectDetail,
    ProjectListResponse,
    ProjectSummary,
    ProjectWorkspaceTreeResponse,
    StagedSplitRequest,
    WorkbookPreviewResponse,
)
from app.evidence.service import delete_project_evidence
from app.storage.project_files import delete_project_files, download_project_file
from app.inbox.service import InboxUploadItem, upload_inbox_files
from app.inbox.split_service import (
    analyze_pdf_upload,
    commit_staged_pdf_single,
    split_staged_pdf,
)
from app.database.workspace_file import WorkspaceFile
from app.database.workspace_files import get_workspace_file_by_path, list_workspace_files_for_project
from app.inbox.paths import is_inbox_workspace_path
from app.sitewise.cost_plan_workbook import workbook_preview_from_bytes
from app.sitewise.taxonomy import taxonomy_options_payload, validate_project_taxonomy
from app.sitewise.workspace_tree import build_project_workspace_tree
from app.workflows.create_cost_plan import (
    draft_workspace_path as cost_plan_draft_workspace_path,
    is_cost_plan_workflow,
    run_create_cost_plan_workflow,
    sync_cost_plan_draft_workspace,
)
from app.workflows.create_pmp import (
    canonical_pmp_workspace_path,
    draft_workspace_path,
    is_pmp_workflow,
    run_create_pmp_workflow,
    sync_pmp_draft_workspace,
)
from app.workflows.sort_files import run_sort_files_workflow
from app.workflows.update_pmp import run_update_pmp_workflow
from app.logging import get_logger

router = APIRouter(prefix="/projects", tags=["projects"])
sitewise_router = APIRouter(prefix="/sitewise", tags=["sitewise"])
log = get_logger(__name__)


def _require_project_owner(project, user_id: uuid.UUID):
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    if not user_owns_project(project, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return project


def _project_summary(project) -> ProjectSummary:
    return ProjectSummary.model_validate(
        {
            "id": project.id,
            "slug": project.slug,
            "title": project.title,
            "workspace_path": project.workspace_path,
            "phase": project.phase,
            "archetype": project.archetype,
            "building_class": project.building_class,
            "work_type": project.work_type,
            "user_role": project.user_role,
            "state": project.state,
            "status": project.status,
            "overlay_status": project_overlay_summary(project),
            "updated_at": project.updated_at,
        }
    )


def _excerpt(text: str, limit: int = 360) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3].rstrip()}..."


def _metadata_text(metadata: dict | None, key: str) -> str | None:
    if not metadata:
        return None
    value = metadata.get(key)
    return value if isinstance(value, str) and value.strip() else None


def _filename_title(filename: str) -> str:
    stem = filename.rsplit("/", maxsplit=1)[-1]
    stem = stem.rsplit(".", maxsplit=1)[0]
    return stem.replace("_", " ").replace("-", " ").strip() or filename


def _register_title_from_fields(
    *,
    metadata: dict | None,
    document_type: str | None,
    document_class: str,
    filename: str,
) -> str:
    metadata = metadata if isinstance(metadata, dict) else {}
    if document_class == "specification":
        return _filename_title(filename)
    return (
        _metadata_text(metadata, "title")
        or document_type
        or filename
    )


def _is_xlsx_filename(filename: str) -> bool:
    return filename.lower().endswith(".xlsx")


def _download_headers(filename: str) -> dict[str, str]:
    safe_filename = filename.replace('"', "")
    return {
        "Content-Disposition": (
            f'attachment; filename="{safe_filename}"; '
            f"filename*=UTF-8''{quote(filename)}"
        )
    }


def _evidence_preview_from_values(
    *,
    document_id: uuid.UUID,
    document_type: str | None,
    metadata: dict | None,
    filename: str,
    relative_path: str,
    source_type: str | None,
    document_class: str,
    excerpt_source: str,
    content: str | None = None,
) -> EvidencePreview:
    metadata = metadata if isinstance(metadata, dict) else {}
    return EvidencePreview(
        id=document_id,
        title=_register_title_from_fields(
            metadata=metadata,
            document_type=document_type,
            document_class=document_class,
            filename=filename,
        ),
        filename=filename,
        relative_path=relative_path,
        source_type=source_type,
        document_class=document_class,
        excerpt=_excerpt(excerpt_source),
        content=content,
        document_number=_metadata_text(metadata, "document_number"),
        revision=_metadata_text(metadata, "revision"),
        category=_metadata_text(metadata, "discipline"),
    )


def _evidence_preview_from_workspace_file(record: WorkspaceFile) -> EvidencePreview:
    return EvidencePreview(
        id=record.id,
        title=record.filename,
        filename=record.filename,
        relative_path=record.workspace_path,
        source_type="project_evidence",
        document_class="inbox_pending",
        excerpt="",
        content=None,
        document_number=None,
        revision=None,
        category=None,
    )


def _append_unindexed_inbox_workspace_files(
    previews: list[EvidencePreview],
    workspace_files: list[WorkspaceFile],
) -> list[EvidencePreview]:
    indexed_paths = {
        preview.relative_path.replace("\\", "/") for preview in previews
    }
    for record in workspace_files:
        path = record.workspace_path.replace("\\", "/")
        if not _is_inbox_path(path) or path in indexed_paths:
            continue
        previews.append(_evidence_preview_from_workspace_file(record))
    return previews


def _evidence_preview_from_document(
    document: SourceDocument,
    *,
    include_content: bool = False,
) -> EvidencePreview:
    metadata = document.document_metadata if isinstance(document.document_metadata, dict) else {}
    excerpt_source = document.normalized_content or ""
    return _evidence_preview_from_values(
        document_id=document.id,
        document_type=document.document_type,
        metadata=metadata,
        filename=document.filename,
        relative_path=document.relative_path,
        source_type=document.source_type,
        document_class=document.document_class,
        excerpt_source=excerpt_source,
        content=excerpt_source if include_content else None,
    )


def _is_inbox_path(relative_path: str) -> bool:
    return is_inbox_workspace_path(relative_path)


def _filter_stale_inbox_documents(
    documents: list[SourceDocument],
    workspace_paths: set[str],
) -> list[SourceDocument]:
    if not workspace_paths:
        return documents
    normalised_workspace_paths = {path.replace("\\", "/") for path in workspace_paths}
    return [
        document
        for document in documents
        if not (
            _is_inbox_path(document.relative_path)
            and document.relative_path.replace("\\", "/") not in normalised_workspace_paths
        )
    ]


async def _ensure_pmp_workspace_file(
    session: AsyncSession,
    *,
    project,
    workspace_files,
    draft_summaries: dict[str, DraftArtifactSummary | None],
) -> list:
    pmp_summary = draft_summaries.get("create_pmp")
    if pmp_summary is None:
        return workspace_files

    canonical_path = draft_workspace_path(project, pmp_summary.version)
    if any(record.workspace_path == canonical_path for record in workspace_files):
        return workspace_files

    draft = await get_latest_draft_artifact(
        session,
        project_id=project.id,
        workflow_type="create_pmp",
    )
    if draft is None:
        return workspace_files

    await sync_pmp_draft_workspace(session, project=project, draft=draft)
    return await list_workspace_files_for_project(session, project_id=project.id)


async def _ensure_cost_plan_workspace_file(
    session: AsyncSession,
    *,
    project,
    workspace_files,
    draft_summaries: dict[str, DraftArtifactSummary | None],
) -> list:
    cost_plan_summary = draft_summaries.get("create_cost_plan")
    if cost_plan_summary is None:
        return workspace_files

    canonical_path = cost_plan_draft_workspace_path(project, cost_plan_summary.version)
    if any(record.workspace_path == canonical_path for record in workspace_files):
        return workspace_files

    draft = await get_latest_draft_artifact(
        session,
        project_id=project.id,
        workflow_type="create_cost_plan",
    )
    if draft is None:
        return workspace_files

    await sync_cost_plan_draft_workspace(session, project=project, draft=draft)
    return await list_workspace_files_for_project(session, project_id=project.id)


def _workspace_paths_for_tree(
    workspace_files,
    *,
    draft_summaries: dict[str, DraftArtifactSummary | None],
) -> list[str]:
    paths = {record.workspace_path for record in workspace_files}
    for draft in draft_summaries.values():
        if draft is None:
            continue
        paths.add(draft.workspace_path)
        if is_pmp_workflow(draft.workflow_type):
            canonical = canonical_pmp_workspace_path(draft.workspace_path)
            if canonical is not None:
                paths.add(canonical)
    return sorted(paths)


async def _list_project_evidence_previews(
    session: AsyncSession,
    *,
    project_slug: str,
    workspace_paths: set[str],
    workspace_files: list[WorkspaceFile] | None = None,
) -> list[EvidencePreview]:
    content_excerpt = func.left(SourceDocument.normalized_content, 720).label(
        "content_excerpt"
    )
    stmt = (
        select(
            SourceDocument.id,
            SourceDocument.document_type,
            SourceDocument.document_metadata,
            SourceDocument.filename,
            SourceDocument.relative_path,
            SourceDocument.source_type,
            SourceDocument.document_class,
            content_excerpt,
        )
        .where(
            SourceDocument.project == project_slug,
            SourceDocument.source_type == "project_evidence",
        )
        .order_by(SourceDocument.relative_path.asc())
    )
    result = await session.execute(stmt)
    normalised_workspace_paths = {
        path.replace("\\", "/")
        for path in workspace_paths
    }
    previews: list[EvidencePreview] = []
    for row in result.all():
        relative_path = row.relative_path
        if (
            normalised_workspace_paths
            and _is_inbox_path(relative_path)
            and relative_path.replace("\\", "/") not in normalised_workspace_paths
        ):
            continue
        previews.append(
            _evidence_preview_from_values(
                document_id=row.id,
                document_type=row.document_type,
                metadata=row.document_metadata,
                filename=row.filename,
                relative_path=relative_path,
                source_type=row.source_type,
                document_class=row.document_class,
                excerpt_source=row.content_excerpt or "",
            )
        )
    if workspace_files:
        previews = _append_unindexed_inbox_workspace_files(previews, workspace_files)
        previews.sort(key=lambda preview: preview.relative_path)
    return previews


async def _first_evidence_preview(
    session: AsyncSession,
    project_slug: str,
) -> EvidencePreview | None:
    stmt = (
        select(SourceDocument)
        .where(
            SourceDocument.project == project_slug,
            SourceDocument.source_type == "project_evidence",
        )
        .order_by(SourceDocument.created_at.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    document = result.scalar_one_or_none()
    if document is None:
        return None
    return _evidence_preview_from_document(document)


async def _platform_knowledge_status(session: AsyncSession) -> PlatformKnowledgeStatus:
    kind_expr = SourceDocument.document_metadata["sitewise_knowledge_kind"].astext
    stmt = (
        select(kind_expr.label("kind"), func.count(SourceDocument.id).label("count"))
        .where(SourceDocument.document_metadata["knowledge_scope"].astext == "platform")
        .group_by(kind_expr)
        .order_by(kind_expr.asc())
    )
    result = await session.execute(stmt)
    buckets = [
        PlatformKnowledgeBucket(kind=row.kind or "unknown", document_count=row.count)
        for row in result.all()
    ]
    return PlatformKnowledgeStatus(available=bool(buckets), buckets=buckets)


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _project_taxonomy_metadata(body: CreateProjectRequest) -> dict | None:
    taxonomy = {
        "subclasses": body.subclasses,
        "scale": body.scale,
        "complexity": body.complexity,
        "work_scope": body.work_scope,
    }
    compact = {key: value for key, value in taxonomy.items() if value is not None}
    return compact or None


def _activity_references_from_metadata(
    metadata: dict | None,
) -> ProjectActivityReferences | None:
    if not isinstance(metadata, dict):
        return None

    def string_list(key: str) -> list[str]:
        value = metadata.get(key)
        if not isinstance(value, list):
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    references = ProjectActivityReferences(
        seed_consulted=string_list("seed_consulted"),
        evidence_refs=string_list("evidence_refs"),
        context_refs=string_list("context_refs"),
    )
    if not (
        references.seed_consulted
        or references.evidence_refs
        or references.context_refs
    ):
        return None
    return references


@router.get("")
async def get_projects(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    await ensure_user_exists(session, user)
    await ensure_default_project_catalog(session, user.id)
    projects = await list_projects(session, user.id)
    return ProjectListResponse(projects=[_project_summary(project) for project in projects])


@router.post("", status_code=status.HTTP_201_CREATED)
async def post_project(
    body: CreateProjectRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectDetail:
    await ensure_user_exists(session, user)
    await require_active_entitlement(session, user)
    taxonomy_errors = validate_project_taxonomy(
        building_class=body.building_class,
        work_type=body.work_type,
        subclasses=body.subclasses,
    )
    if taxonomy_errors:
        raise HTTPException(
            status_code=422,
            detail=taxonomy_errors,
        )
    project = await create_project(
        session,
        user_id=user.id,
        title=body.title,
        slug=body.slug,
        archetype=body.archetype,
        building_class=body.building_class,
        work_type=body.work_type,
        user_role=body.user_role,
        state=body.state,
        phase=body.phase,
        taxonomy=_project_taxonomy_metadata(body),
    )
    summary = _project_summary(project)
    return ProjectDetail(
        **summary.model_dump(),
        metadata=project.project_metadata,
        evidence_preview=None,
    )


@router.get("/taxonomy")
async def get_project_taxonomy(
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await ensure_user_exists(session, user)
    response.headers["Cache-Control"] = "private, max-age=3600"
    return taxonomy_options_payload()


@router.get("/{project_id}")
async def get_project_detail(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectDetail:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    summary = _project_summary(project)
    return ProjectDetail(
        **summary.model_dump(),
        metadata=project.project_metadata,
        evidence_preview=await _first_evidence_preview(session, project.slug),
    )


@router.get("/{project_id}/cockpit-bootstrap")
async def get_project_cockpit_bootstrap(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectCockpitBootstrapResponse:
    total_start = time.perf_counter()
    timings_ms: dict[str, int] = {}

    step_start = time.perf_counter()
    await ensure_user_exists(session, user)
    await ensure_default_project_catalog(session, user.id)
    timings_ms["catalog"] = _elapsed_ms(step_start)

    step_start = time.perf_counter()
    project = _require_project_owner(await get_project(session, project_id), user.id)
    projects = await list_projects(session, user.id)
    timings_ms["projects"] = _elapsed_ms(step_start)

    workflow_types = ["create_pmp", "create_cost_plan", "sort_files"]
    step_start = time.perf_counter()
    draft_rows = await get_latest_draft_artifact_summaries(
        session,
        project_id=project.id,
        workflow_types=workflow_types,
    )
    latest_drafts = {
        workflow_type: (
            DraftArtifactSummary.model_validate(draft_rows[workflow_type])
            if workflow_type in draft_rows
            else None
        )
        for workflow_type in workflow_types
    }
    timings_ms["draft_summaries"] = _elapsed_ms(step_start)

    step_start = time.perf_counter()
    workspace_files = await list_workspace_files_for_project(session, project_id=project.id)
    workspace_files = await _ensure_pmp_workspace_file(
        session,
        project=project,
        workspace_files=workspace_files,
        draft_summaries=latest_drafts,
    )
    workspace_files = await _ensure_cost_plan_workspace_file(
        session,
        project=project,
        workspace_files=workspace_files,
        draft_summaries=latest_drafts,
    )
    workspace_path_list = _workspace_paths_for_tree(
        workspace_files,
        draft_summaries=latest_drafts,
    )
    workspace_paths = set(workspace_path_list)
    workspace_tree = ProjectWorkspaceTreeResponse(
        project_id=project.id,
        root_path=project.workspace_path,
        tree=build_project_workspace_tree(
            root_path=project.workspace_path,
            workspace_paths=workspace_path_list,
        ),
    )
    timings_ms["workspace_tree"] = _elapsed_ms(step_start)

    step_start = time.perf_counter()
    evidence = await _list_project_evidence_previews(
        session,
        project_slug=project.slug,
        workspace_paths=workspace_paths,
        workspace_files=workspace_files,
    )
    timings_ms["evidence"] = _elapsed_ms(step_start)

    step_start = time.perf_counter()
    platform_knowledge = await _platform_knowledge_status(session)
    timings_ms["platform_knowledge"] = _elapsed_ms(step_start)
    timings_ms["total"] = _elapsed_ms(total_start)

    summary = _project_summary(project)
    log.info(
        "project_cockpit_bootstrap_complete",
        project_id=str(project.id),
        evidence_count=len(evidence),
        timings_ms=timings_ms,
    )
    return ProjectCockpitBootstrapResponse(
        project=ProjectDetail(
            **summary.model_dump(),
            metadata=project.project_metadata,
            evidence_preview=evidence[0] if evidence else None,
        ),
        projects=[_project_summary(item) for item in projects],
        evidence=evidence,
        workspace_tree=workspace_tree,
        platform_knowledge=platform_knowledge,
        latest_drafts=latest_drafts,
        timings_ms=timings_ms,
    )


@router.get("/{project_id}/workspace-tree")
async def get_project_workspace_tree(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectWorkspaceTreeResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    workspace_files = await list_workspace_files_for_project(session, project_id=project.id)
    draft_rows = await get_latest_draft_artifact_summaries(
        session,
        project_id=project.id,
        workflow_types=["create_pmp", "create_cost_plan", "sort_files"],
    )
    draft_summaries = {
        workflow_type: (
            DraftArtifactSummary.model_validate(draft_rows[workflow_type])
            if workflow_type in draft_rows
            else None
        )
        for workflow_type in ["create_pmp", "create_cost_plan", "sort_files"]
    }
    workspace_files = await _ensure_pmp_workspace_file(
        session,
        project=project,
        workspace_files=workspace_files,
        draft_summaries=draft_summaries,
    )
    workspace_files = await _ensure_cost_plan_workspace_file(
        session,
        project=project,
        workspace_files=workspace_files,
        draft_summaries=draft_summaries,
    )
    return ProjectWorkspaceTreeResponse(
        project_id=project.id,
        root_path=project.workspace_path,
        tree=build_project_workspace_tree(
            root_path=project.workspace_path,
            workspace_paths=_workspace_paths_for_tree(
                workspace_files,
                draft_summaries=draft_summaries,
            ),
        ),
    )


@router.get("/{project_id}/activity")
async def get_project_activity(
    project_id: uuid.UUID,
    since: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectActivityResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    runs = await list_project_activity_runs(
        session,
        project_id=project.id,
        since=since,
        limit=limit,
    )
    draft_reference_ids = [
        run.reference_id
        for run in runs
        if run.reference_type == "draft_artifact" and run.reference_id is not None
    ]
    references_by_draft_id: dict[uuid.UUID, ProjectActivityReferences | None] = {}
    if draft_reference_ids:
        draft_rows = await session.execute(
            select(DraftArtifact.id, DraftArtifact.provenance_metadata).where(
                DraftArtifact.project_id == project.id,
                DraftArtifact.id.in_(draft_reference_ids),
            )
        )
        references_by_draft_id = {
            row.id: _activity_references_from_metadata(row.provenance_metadata)
            for row in draft_rows.all()
        }
    response_runs = [
        ProjectActivityRun(
            run_id=run.run_id,
            source=run.source,
            reference_type=run.reference_type,
            reference_id=run.reference_id,
            status=run.status,
            created_at=run.created_at,
            updated_at=run.updated_at,
            references=references_by_draft_id.get(run.reference_id),
            events=[
                ProjectActivityEvent(
                    id=event.id,
                    step=event.step,
                    status=event.status,
                    message=event.message,
                    metadata=event.event_metadata or {},
                    created_at=event.created_at,
                )
                for event in run.events
            ],
        )
        for run in runs
    ]
    newest = max((run.updated_at for run in response_runs), default=None)
    return ProjectActivityResponse(runs=response_runs, newest_created_at=newest)


@router.delete("/{project_id}/activity")
async def delete_project_activity(
    project_id: uuid.UUID,
    body: DeleteProjectActivityRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DeleteProjectActivityResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    deleted = await delete_project_activity_runs(
        session,
        project_id=project.id,
        run_ids=body.run_ids,
    )
    return DeleteProjectActivityResponse(deleted=deleted)


@router.get("/{project_id}/workspace-files/preview")
async def get_project_workspace_file_preview(
    project_id: uuid.UUID,
    path: str = Query(..., min_length=1),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WorkbookPreviewResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    record = await get_workspace_file_by_path(
        session,
        project_id=project.id,
        workspace_path=path,
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace file not found",
        )
    if not _is_xlsx_filename(record.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace preview is only available for Excel workbooks",
        )

    content = await asyncio.to_thread(download_project_file, storage_key=record.storage_key)
    preview = workbook_preview_from_bytes(content)
    return WorkbookPreviewResponse(
        filename=record.filename,
        workspace_path=record.workspace_path,
        sheets=[
            {
                "name": sheet.name,
                "column_count": sheet.column_count,
                "rows": sheet.rows,
                "styles": sheet.styles,
            }
            for sheet in preview.sheets
        ],
        warnings=preview.warnings,
    )


@router.get("/{project_id}/workspace-files/download")
async def download_project_workspace_file(
    project_id: uuid.UUID,
    path: str = Query(..., min_length=1),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    record = await get_workspace_file_by_path(
        session,
        project_id=project.id,
        workspace_path=path,
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace file not found",
        )

    content = await asyncio.to_thread(download_project_file, storage_key=record.storage_key)
    media_type, _ = mimetypes.guess_type(record.filename)
    return Response(
        content=content,
        media_type=media_type or "application/octet-stream",
        headers=_download_headers(record.filename),
    )


@router.post("/{project_id}/inbox/upload", status_code=status.HTTP_201_CREATED)
async def post_inbox_upload(
    project_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    relative_path: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InboxUploadResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    await ensure_user_exists(session, user)
    await require_active_entitlement(session, user)

    items: list[InboxUploadItem] = []
    for upload in files:
        content = await upload.read()
        filename = upload.filename or "upload"
        items.append(
            InboxUploadItem(
                filename=filename,
                content=content,
                relative_path=relative_path,
            )
        )

    outcomes = await upload_inbox_files(session, project=project, items=items)
    return InboxUploadResponse(
        files=[
            InboxUploadResult(
                id=outcome.id,
                filename=outcome.filename,
                workspace_path=outcome.workspace_path,
                content_hash=outcome.content_hash,
                size_bytes=outcome.size_bytes,
                ingest_status=outcome.ingest_status,
                message=outcome.message,
            )
            for outcome in outcomes
        ]
    )


@router.get("/{project_id}/evidence")
async def get_project_evidence(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, list[EvidencePreview]]:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    workspace_files = await list_workspace_files_for_project(session, project_id=project.id)
    workspace_paths = {record.workspace_path for record in workspace_files}
    previews = await _list_project_evidence_previews(
        session,
        project_slug=project.slug,
        workspace_paths=workspace_paths,
        workspace_files=workspace_files,
    )
    return {"evidence": previews}


@router.get("/{project_id}/evidence/{evidence_id}")
async def get_project_evidence_document(
    project_id: uuid.UUID,
    evidence_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EvidencePreview:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    result = await session.execute(
        select(SourceDocument).where(
            SourceDocument.id == evidence_id,
            SourceDocument.project == project.slug,
            SourceDocument.source_type == "project_evidence",
        )
    )
    document = result.scalar_one_or_none()
    if document is not None:
        return _evidence_preview_from_document(document, include_content=True)

    workspace_file = await session.scalar(
        select(WorkspaceFile).where(
            WorkspaceFile.id == evidence_id,
            WorkspaceFile.project_id == project.id,
        )
    )
    if workspace_file is None or not _is_inbox_path(workspace_file.workspace_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )
    return _evidence_preview_from_workspace_file(workspace_file)


@router.delete(
    "/{project_id}/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project_evidence_document(
    project_id: uuid.UUID,
    evidence_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    storage_keys = await delete_project_evidence(
        session, project=project, evidence_id=evidence_id
    )
    # The database delete is what removes the document from the repository view,
    # so return immediately and let the slower object-storage cleanup run after
    # the response is sent.
    if storage_keys:
        background_tasks.add_task(delete_project_files, storage_keys=storage_keys)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _upload_results(outcomes) -> InboxUploadResponse:
    return InboxUploadResponse(
        files=[
            InboxUploadResult(
                id=outcome.id,
                filename=outcome.filename,
                workspace_path=outcome.workspace_path,
                content_hash=outcome.content_hash,
                size_bytes=outcome.size_bytes,
                ingest_status=outcome.ingest_status,
                message=outcome.message,
            )
            for outcome in outcomes
        ]
    )


@router.post("/{project_id}/inbox/analyze")
async def post_inbox_analyze(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PdfAnalyzeResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    await ensure_user_exists(session, user)
    content = await file.read()
    result = await analyze_pdf_upload(
        project=project, filename=file.filename or "upload.pdf", content=content
    )
    return PdfAnalyzeResponse(
        staging_id=result.staging_id,
        is_drawing_set=result.is_drawing_set,
        confidence=result.confidence,
        page_count=result.page_count,
        scores=result.scores,
        pages=[
            PdfSheetProposal(
                index=p.index,
                proposed_title=p.proposed_title,
                filename=p.filename,
                has_text=p.has_text,
            )
            for p in result.pages
        ],
    )


@router.post("/{project_id}/inbox/{staging_id}/split", status_code=status.HTTP_201_CREATED)
async def post_inbox_split(
    project_id: uuid.UUID,
    staging_id: str,
    body: StagedSplitRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InboxUploadResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    outcomes = await split_staged_pdf(
        session,
        project=project,
        staging_id=staging_id,
        source_filename=body.source_filename,
    )
    return _upload_results(outcomes)


@router.post("/{project_id}/inbox/{staging_id}/commit", status_code=status.HTTP_201_CREATED)
async def post_inbox_commit_single(
    project_id: uuid.UUID,
    staging_id: str,
    body: StagedSplitRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InboxUploadResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    outcome = await commit_staged_pdf_single(
        session,
        project=project,
        staging_id=staging_id,
        source_filename=body.source_filename,
    )
    return _upload_results([outcome])


@router.post("/{project_id}/threads", status_code=status.HTTP_201_CREATED)
async def post_project_thread(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ThreadResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    await ensure_user_exists(session, user)
    await require_active_entitlement(session, user)
    thread = await create_thread(
        session,
        user.id,
        title=title_from_message(f"{project.title} project chat"),
        project_id=project.id,
    )
    return ThreadResponse.model_validate(thread)


@router.get("/{project_id}/drafts/latest")
async def get_latest_project_draft(
    project_id: uuid.UUID,
    workflow_type: str = Query(default="create_pmp"),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DraftArtifactResponse | None:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    draft = await get_latest_draft_artifact(
        session,
        project_id=project.id,
        workflow_type=workflow_type,
    )
    return DraftArtifactResponse.model_validate(draft) if draft is not None else None


@router.get("/{project_id}/drafts/{draft_id}")
async def get_project_draft(
    project_id: uuid.UUID,
    draft_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DraftArtifactResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    draft = await get_draft_artifact(session, draft_id)
    if draft is None or draft.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )
    return DraftArtifactResponse.model_validate(draft)


@router.post("/{project_id}/workflows/create-pmp")
async def post_create_pmp(
    project_id: uuid.UUID,
    body: CreatePmpRequest = Body(default_factory=CreatePmpRequest),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CreatePmpResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    await require_active_entitlement(session, user)
    result = await run_create_pmp_workflow(
        session,
        user_id=user.id,
        project=project,
        thread_id=body.thread_id,
        chat_model=body.chat_model,
    )
    return result


@router.post("/{project_id}/workflows/create-cost-plan")
async def post_create_cost_plan(
    project_id: uuid.UUID,
    body: CreateCostPlanRequest = Body(default_factory=CreateCostPlanRequest),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CreateCostPlanResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    await require_active_entitlement(session, user)
    result = await run_create_cost_plan_workflow(
        session,
        user_id=user.id,
        project=project,
        thread_id=body.thread_id,
        chat_model=body.chat_model,
    )
    return result


@router.post("/{project_id}/workflows/update-pmp")
async def post_update_pmp(
    project_id: uuid.UUID,
    body: UpdatePmpRequest = Body(default_factory=UpdatePmpRequest),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CreatePmpResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    await require_active_entitlement(session, user)
    result = await run_update_pmp_workflow(
        session,
        user_id=user.id,
        project=project,
        thread_id=body.thread_id,
        chat_model=body.chat_model,
    )
    return result


@router.patch("/{project_id}/drafts/{draft_id}")
async def patch_project_draft(
    project_id: uuid.UUID,
    draft_id: uuid.UUID,
    body: PatchDraftRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DraftArtifactResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    await require_active_entitlement(session, user)
    draft = await get_draft_artifact(session, draft_id)
    if draft is None or draft.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )
    updated = await create_draft_revision(
        session,
        draft=draft,
        author_user_id=user.id,
        content_markdown=body.content_markdown,
        edit_source="user",
    )
    if is_pmp_workflow(updated.workflow_type):
        await sync_pmp_draft_workspace(
            session,
            project=project,
            draft=updated,
            markdown=body.content_markdown,
        )
    elif is_cost_plan_workflow(updated.workflow_type):
        await sync_cost_plan_draft_workspace(
            session,
            project=project,
            draft=updated,
            markdown=body.content_markdown,
        )
    return DraftArtifactResponse.model_validate(updated)


@router.post("/{project_id}/drafts/{draft_id}/accept")
async def post_accept_project_draft(
    project_id: uuid.UUID,
    draft_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DraftArtifactResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    await require_active_entitlement(session, user)
    draft = await get_draft_artifact(session, draft_id)
    if draft is None or draft.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )
    accepted = await accept_draft(session, draft)
    if is_pmp_workflow(accepted.workflow_type):
        await sync_pmp_draft_workspace(session, project=project, draft=accepted)
    return DraftArtifactResponse.model_validate(accepted)


@router.post("/{project_id}/workflows/sort-files")
async def post_sort_files(
    project_id: uuid.UUID,
    body: SortFilesRequest = Body(default_factory=SortFilesRequest),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SortFilesResponse:
    project = _require_project_owner(await get_project(session, project_id), user.id)
    await require_active_entitlement(session, user)
    result = await run_sort_files_workflow(
        session,
        user_id=user.id,
        project=project,
        thread_id=body.thread_id,
    )
    return result


@sitewise_router.get("/platform-knowledge")
async def get_platform_knowledge_status(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PlatformKnowledgeStatus:
    await ensure_user_exists(session, user)
    return await _platform_knowledge_status(session)
