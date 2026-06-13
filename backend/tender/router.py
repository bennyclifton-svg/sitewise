from __future__ import annotations

import asyncio
import hashlib
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentUser, get_current_user
from app.billing.entitlements import require_active_entitlement
from app.database.projects import get_project, user_owns_project
from app.database.session import get_db
from app.database.users import ensure_user_exists
from app.storage.project_files import upload_project_file
from tender.models import QUOTE_STAGES, TenderComparison, TenderDocument, TenderQuote
from tender.schemas import (
    ComparisonContextPatch,
    ComparisonCreate,
    ComparisonDetail,
    DocumentUploadResponse,
    JobView,
    MatrixResponse,
    QAQueueResponse,
    QAResolveRequest,
    QAResolveResponse,
    QuoteCreate,
    QuoteView,
    ReportDeliveredRequest,
    ReportLifecycleResponse,
    TaxonomyListResponse,
    TaxonomySearchResponse,
)
from tender.services import jobs, matrix, qa, report, taxonomy

router = APIRouter(prefix="/api/tender", tags=["tender"])


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
    await ensure_user_exists(session, user)
    await require_active_entitlement(session, user)
    await _require_project_owner(session, project_id=body.project_id, user_id=user.id)
    return await create_comparison(
        session,
        project_id=body.project_id,
        context=body.context.model_dump(),
        created_by=user.id,
    )


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
    if stage not in QUOTE_STAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown tender stage",
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
    return await report.approve_report(
        session,
        comparison_id=comparison_id,
        user_id=user.id,
    )


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
