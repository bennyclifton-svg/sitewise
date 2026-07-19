from __future__ import annotations

import asyncio
import hashlib
import mimetypes
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.auth.dependencies import CurrentUser, get_current_user
from app.billing.entitlements import require_active_entitlement
from app.database.projects import get_project, user_owns_project
from app.database.session import get_db
from app.database.users import ensure_user_exists
from app.database.workspace_files import get_workspace_file_by_path
from app.projects.snapshot import get_project_snapshot
from app.projects.workflow_capabilities import (
    TENDER_COMPARISON,
    capability_block_message,
)
from app.storage.project_files import upload_project_file
from tender.models import TenderComparison, TenderDocument, TenderQuote
from tender.schemas import (
    ComparisonContextPatch,
    ComparisonCreate,
    ComparisonDetail,
    ComparisonFromProjectFilesCreate,
    ComparisonListResponse,
    ComparisonProgressResponse,
    DocumentUploadResponse,
    JobView,
    MatrixResponse,
    ProcessComparisonResponse,
    ProjectFileDocumentAttach,
    ProjectContext,
    QAAcceptAllResponse,
    QAQueueResponse,
    QAResolveRequest,
    QAResolveResponse,
    QuoteCreate,
    CellItemsResponse,
    ProjectTradesResponse,
    QuoteLedgerResponse,
    QuoteView,
    ReportDeliveredRequest,
    ReportLifecycleResponse,
    TaxonomyListResponse,
    TaxonomySearchResponse,
    TenderPreparationRequest,
    TenderPreparationResponse,
    TenderIntakeRequest,
    TenderIntakeResponse,
    TenderReportStateResponse,
)
from tender.services import (
    intake,
    jobs,
    ledger,
    matrix,
    progress,
    project_taxonomy,
    qa,
    report,
    taxonomy,
)
from tender.services.project_context_adapter import (
    ContextRevisionConflict,
    ContextValidationError,
    ProjectContextAdapter,
)

router = APIRouter(prefix="/api/tender", tags=["tender"])

MANUAL_QUOTE_STAGES = {
    "ingest_document",
    "classify_document",
    "extract_line_items",
    "embed_items",
    "map_items",
}
MANUAL_COMPARISON_STAGES = {
    "generate_project_taxonomy",
    "run_expectations",
    "run_analysis",
    "generate_flags",
}


def _context_conflict(exc: ContextRevisionConflict) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": f"{exc.resource}_revision_conflict",
            "expected_revision": exc.expected,
            "current_revision": exc.current,
        },
    )


@router.post("/prepare", response_model=TenderPreparationResponse)
async def prepare_tender_intake(
    body: TenderPreparationRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenderPreparationResponse:
    await _require_project_owner(session, project_id=body.project_id, user_id=user.id)
    try:
        prepared = await ProjectContextAdapter().prepare(
            session,
            project_id=body.project_id,
            owner_user_id=user.id,
            expected_profile_revision=body.expected_profile_revision,
            expected_selection_revision=body.expected_selection_revision,
            overrides=body.context_overrides,
        )
    except ContextRevisionConflict as exc:
        raise _context_conflict(exc) from exc
    except ContextValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return TenderPreparationResponse(
        **prepared.model_dump(mode="python", exclude={"provenance"}),
        provenance=prepared.provenance.model_dump(mode="json"),
    )


@router.post("/intake", status_code=status.HTTP_201_CREATED, response_model=TenderIntakeResponse)
async def post_tender_intake(
    body: TenderIntakeRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenderIntakeResponse:
    await ensure_user_exists(session, user)
    await require_active_entitlement(session, user)
    await _require_project_owner(session, project_id=body.project_id, user_id=user.id)
    await _require_tender_capability(session, project_id=body.project_id, user_id=user.id)
    try:
        return await intake.create_immutable_intake(session, request=body, owner_user_id=user.id)
    except ContextRevisionConflict as exc:
        raise _context_conflict(exc) from exc
    except intake.TenderIntakeNotReady as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "tender_intake_not_ready", "missing_fields": exc.missing, "unsupported_reasons": exc.unsupported},
        ) from exc
    except intake.TenderIdempotencyConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "tender_idempotency_conflict", "message": str(exc)}) from exc
    except ContextValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


async def create_comparison(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    context: dict,
    created_by: uuid.UUID,
) -> TenderComparison:
    comparison = TenderComparison(
        project_id=project_id,
        context=context,
        created_by=created_by,
    )
    session.add(comparison)
    await session.flush()
    await session.refresh(comparison)
    set_committed_value(comparison, "quotes", [])
    return comparison


async def get_comparison_detail(
    session: AsyncSession,
    comparison_id: uuid.UUID,
) -> TenderComparison | None:
    result = await session.execute(
        select(TenderComparison)
        .options(
            selectinload(TenderComparison.quotes).selectinload(TenderQuote.documents)
        )
        .where(TenderComparison.id == comparison_id)
    )
    return result.scalar_one_or_none()


async def list_comparisons(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> list[TenderComparison]:
    result = await session.execute(
        select(TenderComparison)
        .options(
            selectinload(TenderComparison.quotes).selectinload(TenderQuote.documents)
        )
        .where(TenderComparison.project_id == project_id)
        .order_by(TenderComparison.updated_at.desc(), TenderComparison.created_at.desc())
    )
    return list(result.scalars().all())


async def list_comparisons_page(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    limit: int,
    cursor: uuid.UUID | None = None,
) -> tuple[list[TenderComparison], uuid.UUID | None]:
    stmt = (
        select(TenderComparison)
        .options(
            selectinload(TenderComparison.quotes).selectinload(TenderQuote.documents)
        )
        .where(TenderComparison.project_id == project_id)
    )
    if cursor is not None:
        anchor = await session.get(TenderComparison, cursor)
        if anchor is not None and anchor.project_id == project_id:
            stmt = stmt.where(
                or_(
                    TenderComparison.updated_at < anchor.updated_at,
                    and_(
                        TenderComparison.updated_at == anchor.updated_at,
                        TenderComparison.id < anchor.id,
                    ),
                )
            )
    rows = list(
        (
            await session.execute(
                stmt.order_by(
                    TenderComparison.updated_at.desc(), TenderComparison.id.desc()
                ).limit(limit + 1)
            )
        ).scalars().all()
    )
    next_cursor = rows[limit - 1].id if len(rows) > limit else None
    return rows[:limit], next_cursor


async def create_quote(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    body: QuoteCreate,
) -> TenderQuote:
    quote = TenderQuote(
        comparison_id=comparison_id,
        builder_name=body.builder_name,
        builder_abn=body.builder_abn,
        quote_ref=body.quote_ref,
        quote_date=body.quote_date,
        stated_total_cents=body.stated_total_cents,
        stated_total_source="manual" if body.stated_total_cents is not None else None,
        gst_treatment=body.gst_treatment,
        contract_type=body.contract_type,
        validity_days=body.validity_days,
    )
    session.add(quote)
    await session.flush()
    await session.refresh(quote)
    return quote


async def store_quote_document(
    session: AsyncSession,
    *,
    quote: TenderQuote,
    filename: str,
    content: bytes,
    mime_type: str,
) -> TenderDocument:
    document_id = uuid.uuid4()
    safe_filename = filename.replace("\\", "_").replace("/", "_")
    storage_path = (
        f"tender/comparisons/{quote.comparison_id}/quotes/{quote.id}/"
        f"documents/{document_id}/{safe_filename}"
    )
    await asyncio.to_thread(
        upload_project_file,
        storage_key=storage_path,
        content=content,
        filename=safe_filename,
    )
    document = TenderDocument(
        id=document_id,
        quote_id=quote.id,
        storage_path=storage_path,
        original_filename=filename,
        mime_type=mime_type,
        ingest_status="pending",
        content_hash=hashlib.sha256(content).hexdigest(),
    )
    session.add(document)
    await session.flush()
    await session.refresh(document)
    return document


async def store_project_file_quote_document(
    session: AsyncSession,
    *,
    quote: TenderQuote,
    workspace_path: str,
) -> TenderDocument:
    record = await get_workspace_file_by_path(
        session,
        project_id=quote.comparison.project_id,
        workspace_path=workspace_path,
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project file not found",
        )

    document = TenderDocument(
        quote_id=quote.id,
        storage_path=record.storage_key,
        original_filename=record.filename,
        mime_type=mimetypes.guess_type(record.filename)[0]
        or "application/octet-stream",
        ingest_status="pending",
        content_hash=record.content_hash,
    )
    session.add(document)
    await session.flush()
    await session.refresh(document)
    return document


async def _require_project_owner(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
):
    project = await get_project(session, project_id)
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


async def _require_tender_capability(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    snapshot = await get_project_snapshot(
        session,
        project_id=project_id,
        owner_user_id=user_id,
    )
    message = capability_block_message(snapshot, TENDER_COMPARISON)
    if message:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


async def require_comparison_owner(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TenderComparison:
    comparison = await get_comparison_detail(session, comparison_id)
    if comparison is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comparison not found",
        )
    await _require_project_owner(
        session,
        project_id=comparison.project_id,
        user_id=user_id,
    )
    return comparison


async def require_quote_owner(
    session: AsyncSession,
    *,
    quote_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TenderQuote:
    result = await session.execute(
        select(TenderQuote)
        .options(selectinload(TenderQuote.comparison))
        .where(TenderQuote.id == quote_id)
    )
    quote = result.scalar_one_or_none()
    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found",
        )
    await _require_project_owner(
        session,
        project_id=quote.comparison.project_id,
        user_id=user_id,
    )
    return quote


@router.post(
    "/comparisons",
    status_code=status.HTTP_201_CREATED,
    response_model=ComparisonDetail,
)
async def post_comparison(
    body: ComparisonCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenderComparison:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Use POST /api/tender/intake with a saved quote selection",
    )
    await ensure_user_exists(session, user)
    await require_active_entitlement(session, user)
    await _require_project_owner(session, project_id=body.project_id, user_id=user.id)
    await _require_tender_capability(
        session, project_id=body.project_id, user_id=user.id
    )
    return await create_comparison(
        session,
        project_id=body.project_id,
        context=body.context.model_dump(),
        created_by=user.id,
    )


@router.post(
    "/comparisons/from-project-files",
    status_code=status.HTTP_201_CREATED,
    response_model=ComparisonDetail,
)
async def post_comparison_from_project_files(
    body: ComparisonFromProjectFilesCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenderComparison:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Use POST /api/tender/intake with a saved quote selection",
    )
    await ensure_user_exists(session, user)
    await require_active_entitlement(session, user)
    await _require_project_owner(session, project_id=body.project_id, user_id=user.id)
    await _require_tender_capability(
        session, project_id=body.project_id, user_id=user.id
    )

    comparison = await create_comparison(
        session,
        project_id=body.project_id,
        context=ProjectContext(context_source="repository_selection").model_dump(),
        created_by=user.id,
    )

    quotes: list[TenderQuote] = []
    for index, workspace_path in enumerate(body.workspace_paths, start=1):
        quote = await create_quote(
            session,
            comparison_id=comparison.id,
            body=QuoteCreate(builder_name=f"Quote {index}"),
        )
        set_committed_value(quote, "comparison", comparison)
        document = await store_project_file_quote_document(
            session,
            quote=quote,
            workspace_path=workspace_path,
        )
        set_committed_value(quote, "documents", [document])
        await jobs.enqueue(
            session,
            kind="ingest_document",
            comparison_id=quote.comparison_id,
            quote_id=quote.id,
            payload={"document_id": str(document.id)},
        )
        quotes.append(quote)

    set_committed_value(comparison, "quotes", quotes)
    return comparison


@router.get("/comparisons", response_model=ComparisonListResponse)
async def get_comparisons(
    project_id: uuid.UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: uuid.UUID | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ComparisonListResponse:
    await _require_project_owner(session, project_id=project_id, user_id=user.id)
    comparisons, next_cursor = await list_comparisons_page(
        session, project_id=project_id, limit=limit, cursor=cursor
    )
    return ComparisonListResponse(comparisons=comparisons, next_cursor=next_cursor)


@router.get("/comparisons/{comparison_id}", response_model=ComparisonDetail)
async def get_comparison(
    comparison_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenderComparison:
    return await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )


@router.get(
    "/comparisons/{comparison_id}/progress",
    response_model=ComparisonProgressResponse,
)
async def get_comparison_progress(
    comparison_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ComparisonProgressResponse:
    comparison = await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    return await progress.comparison_progress(
        session,
        comparison_id=comparison_id,
        comparison_status=comparison.status,
    )


@router.post(
    "/comparisons/{comparison_id}/process",
    response_model=ProcessComparisonResponse,
)
async def post_comparison_process(
    comparison_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProcessComparisonResponse:
    await require_active_entitlement(session, user)
    comparison = await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    result = await progress.process_comparison(session, comparison_id=comparison.id)
    if result.queued:
        comparison.status = "processing"
        await session.flush()
    return result


@router.patch("/comparisons/{comparison_id}/context", response_model=ComparisonDetail)
async def patch_comparison_context(
    comparison_id: uuid.UUID,
    body: ComparisonContextPatch,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenderComparison:
    await require_active_entitlement(session, user)
    comparison = await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    comparison.context = body.context.model_dump()
    comparison.status = "processing"
    await jobs.enqueue(
        session,
        kind="run_expectations",
        comparison_id=comparison.id,
        payload={"reason": "context_updated"},
    )
    await session.flush()
    return comparison


@router.post(
    "/comparisons/{comparison_id}/quotes",
    status_code=status.HTTP_201_CREATED,
    response_model=QuoteView,
)
async def post_quote(
    comparison_id: uuid.UUID,
    body: QuoteCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenderQuote:
    await require_active_entitlement(session, user)
    await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    return await create_quote(session, comparison_id=comparison_id, body=body)


@router.post(
    "/quotes/{quote_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentUploadResponse,
)
async def post_quote_document(
    quote_id: uuid.UUID,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    await require_active_entitlement(session, user)
    quote = await require_quote_owner(session, quote_id=quote_id, user_id=user.id)
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded document is empty",
        )
    document = await store_quote_document(
        session,
        quote=quote,
        filename=file.filename or "document",
        content=content,
        mime_type=file.content_type or "application/octet-stream",
    )
    job = await jobs.enqueue(
        session,
        kind="ingest_document",
        comparison_id=quote.comparison_id,
        quote_id=quote.id,
        payload={"document_id": str(document.id)},
    )
    return DocumentUploadResponse(document=document, job=job)


@router.post(
    "/quotes/{quote_id}/documents/from-project-file",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentUploadResponse,
)
async def post_quote_project_file_document(
    quote_id: uuid.UUID,
    body: ProjectFileDocumentAttach,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    await require_active_entitlement(session, user)
    quote = await require_quote_owner(session, quote_id=quote_id, user_id=user.id)
    document = await store_project_file_quote_document(
        session,
        quote=quote,
        workspace_path=body.workspace_path,
    )
    job = await jobs.enqueue(
        session,
        kind="ingest_document",
        comparison_id=quote.comparison_id,
        quote_id=quote.id,
        payload={"document_id": str(document.id)},
    )
    return DocumentUploadResponse(document=document, job=job)


@router.post(
    "/quotes/{quote_id}/retry/{stage}",
    status_code=status.HTTP_201_CREATED,
    response_model=JobView,
)
async def post_quote_stage_retry(
    quote_id: uuid.UUID,
    stage: str,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if stage not in MANUAL_QUOTE_STAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tender stage cannot be manually run for a quote",
        )
    await require_active_entitlement(session, user)
    quote = await require_quote_owner(session, quote_id=quote_id, user_id=user.id)
    quote.stage = stage
    return await jobs.enqueue(
        session,
        kind=stage,
        comparison_id=quote.comparison_id,
        quote_id=quote.id,
        payload={"retry": True},
    )


@router.post(
    "/comparisons/{comparison_id}/retry/{stage}",
    status_code=status.HTTP_201_CREATED,
    response_model=JobView,
)
async def post_comparison_stage_retry(
    comparison_id: uuid.UUID,
    stage: str,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if stage not in MANUAL_COMPARISON_STAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tender stage cannot be manually run for a comparison",
        )
    await require_active_entitlement(session, user)
    comparison = await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    comparison.status = "processing"
    return await jobs.enqueue(
        session,
        kind=stage,
        comparison_id=comparison.id,
        payload={"retry": True},
    )


@router.get(
    "/comparisons/{comparison_id}/qa/queue",
    response_model=QAQueueResponse,
)
async def get_qa_queue(
    comparison_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> QAQueueResponse:
    await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    return QAQueueResponse(
        items=await qa.list_review_items(session, comparison_id=comparison_id)
    )


@router.get(
    "/comparisons/{comparison_id}/matrix",
    response_model=MatrixResponse,
)
async def get_comparison_matrix(
    comparison_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MatrixResponse:
    await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    return await matrix.build_matrix(session, comparison_id=comparison_id)


@router.get(
    "/comparisons/{comparison_id}/trades",
    response_model=ProjectTradesResponse,
)
async def get_comparison_trades(
    comparison_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectTradesResponse:
    await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    return await project_taxonomy.list_project_trades(
        session, comparison_id=comparison_id
    )


@router.get(
    "/comparisons/{comparison_id}/quotes/{quote_id}/ledger",
    response_model=QuoteLedgerResponse,
)
async def get_quote_ledger(
    comparison_id: uuid.UUID,
    quote_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> QuoteLedgerResponse:
    await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    return await ledger.build_quote_ledger(
        session, comparison_id=comparison_id, quote_id=quote_id
    )


@router.get(
    "/comparisons/{comparison_id}/cells/{cell_code}/items",
    response_model=CellItemsResponse,
)
async def get_cell_items(
    comparison_id: uuid.UUID,
    cell_code: str,
    quote_id: uuid.UUID = Query(...),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CellItemsResponse:
    await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    return await ledger.build_cell_items(
        session,
        comparison_id=comparison_id,
        cell_code=cell_code,
        quote_id=quote_id,
    )


@router.get("/taxonomy", response_model=TaxonomyListResponse)
async def get_taxonomy(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TaxonomyListResponse:
    return TaxonomyListResponse(cells=await taxonomy.list_taxonomy(session))


@router.get("/taxonomy/search", response_model=TaxonomySearchResponse)
async def get_taxonomy_search(
    q: str = Query(..., min_length=1),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TaxonomySearchResponse:
    return TaxonomySearchResponse(
        results=await taxonomy.search_taxonomy(session, query=q)
    )


@router.post(
    "/qa/items/{item_id}/resolve",
    response_model=QAResolveResponse,
)
async def post_qa_item_resolve(
    item_id: uuid.UUID,
    body: QAResolveRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> qa.QAResolveResult:
    await require_active_entitlement(session, user)
    try:
        comparison_id = await qa.get_item_comparison_id(session, item_id=item_id)
        await require_comparison_owner(
            session,
            comparison_id=comparison_id,
            user_id=user.id,
        )
        return await qa.resolve_qa_item(
            session,
            item_id=item_id,
            reviewer_id=user.id,
            request=body,
        )
    except qa.QAItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QA item not found",
        ) from exc
    except qa.InvalidQAResolutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/comparisons/{comparison_id}/qa/accept-all",
    response_model=QAAcceptAllResponse,
)
async def post_qa_accept_all(
    comparison_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> qa.QAAcceptAllResult:
    await require_active_entitlement(session, user)
    await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    return await qa.accept_all_pending(
        session,
        comparison_id=comparison_id,
        reviewer_id=user.id,
    )


@router.post(
    "/comparisons/{comparison_id}/report/build",
    response_model=ReportLifecycleResponse,
)
async def post_report_build(
    comparison_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> report.ReportLifecycleResult:
    await require_active_entitlement(session, user)
    await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    try:
        return await report.build_report_draft(
            session,
            comparison_id=comparison_id,
            user_id=user.id,
        )
    except qa.PendingReviewError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Comparison has QA items still needing review",
        ) from exc
    except report.WeasyPrintUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get(
    "/comparisons/{comparison_id}/report",
    response_model=TenderReportStateResponse,
)
async def get_report_state(
    comparison_id: uuid.UUID,
    revision: int | None = Query(default=None, ge=1),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenderReportStateResponse:
    await require_comparison_owner(session, comparison_id=comparison_id, user_id=user.id)
    lifecycle, draft = await report.get_report_state(
        session, comparison_id=comparison_id, version=revision
    )
    return TenderReportStateResponse(
        comparison_id=comparison_id,
        report=ReportLifecycleResponse.model_validate(lifecycle) if lifecycle else None,
        draft=draft,
    )


@router.post(
    "/comparisons/{comparison_id}/report/approve",
    response_model=ReportLifecycleResponse,
)
async def post_report_approve(
    comparison_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> report.ReportLifecycleResult:
    await require_active_entitlement(session, user)
    await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    try:
        return await report.approve_report(
            session,
            comparison_id=comparison_id,
            user_id=user.id,
        )
    except report.WeasyPrintUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post(
    "/comparisons/{comparison_id}/report/delivered",
    response_model=ReportLifecycleResponse,
)
async def post_report_delivered(
    comparison_id: uuid.UUID,
    body: ReportDeliveredRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> report.ReportLifecycleResult:
    await require_active_entitlement(session, user)
    await require_comparison_owner(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )
    return await report.mark_report_delivered(
        session,
        comparison_id=comparison_id,
        delivery_note=body.delivery_note,
    )
