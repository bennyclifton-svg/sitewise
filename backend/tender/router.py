from __future__ import annotations

import asyncio
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.storage.project_files import upload_project_file
from tender.models import TenderComparison, TenderDocument, TenderQuote
from tender.schemas import (
    ComparisonCreate,
    ComparisonDetail,
    ComparisonView,
    DocumentUploadResponse,
    QuoteCreate,
    QuoteView,
)
from tender.services.jobs import enqueue

router = APIRouter(prefix="/api/tender", tags=["tender"])


def _safe_filename(filename: str | None) -> str:
    name = Path(filename or "document.pdf").name.strip() or "document.pdf"
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-") or "document.pdf"


@router.post(
    "/comparisons",
    response_model=ComparisonView,
    status_code=status.HTTP_201_CREATED,
)
async def create_comparison(
    request: ComparisonCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenderComparison:
    comparison = TenderComparison(
        id=uuid.uuid4(),
        project_id=request.project_id,
        status="intake",
        context=request.context.model_dump(mode="json"),
        created_by=user.id,
    )
    session.add(comparison)
    await session.flush()
    await session.refresh(comparison)
    return comparison


@router.post(
    "/comparisons/{comparison_id}/quotes",
    response_model=QuoteView,
    status_code=status.HTTP_201_CREATED,
)
async def create_quote(
    comparison_id: uuid.UUID,
    request: QuoteCreate,
    session: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> TenderQuote:
    comparison = await session.get(TenderComparison, comparison_id)
    if comparison is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparison not found")

    quote = TenderQuote(
        id=uuid.uuid4(),
        comparison_id=comparison_id,
        builder_name=request.builder_name,
        builder_abn=request.builder_abn,
        quote_ref=request.quote_ref,
        quote_date=request.quote_date,
        stated_total_cents=request.stated_total_cents,
        gst_treatment=request.gst_treatment,
        contract_type=request.contract_type,
        validity_days=request.validity_days,
        stage="intake",
    )
    session.add(quote)
    await session.flush()
    await session.refresh(quote)
    return quote


@router.post(
    "/quotes/{quote_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_quote_document(
    quote_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> DocumentUploadResponse:
    quote = await session.get(TenderQuote, quote_id)
    if quote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    filename = _safe_filename(file.filename)
    storage_key = f"tender/{quote.comparison_id}/{quote.id}/{filename}"
    await asyncio.to_thread(
        upload_project_file,
        storage_key=storage_key,
        content=content,
        filename=filename,
    )

    document = TenderDocument(
        id=uuid.uuid4(),
        quote_id=quote.id,
        storage_path=storage_key,
        original_filename=filename,
        mime_type=file.content_type or "application/octet-stream",
        ocr_applied=False,
        ingest_status="pending",
    )
    session.add(document)
    await session.flush()
    await session.refresh(document)

    job = await enqueue(
        session,
        kind="ingest_document",
        comparison_id=quote.comparison_id,
        quote_id=quote.id,
        payload={"document_id": str(document.id)},
    )
    await session.refresh(job)
    return DocumentUploadResponse(document=document, job=job)


@router.get("/comparisons/{comparison_id}", response_model=ComparisonDetail)
async def get_comparison(
    comparison_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> TenderComparison:
    result = await session.execute(
        select(TenderComparison)
        .where(TenderComparison.id == comparison_id)
        .options(selectinload(TenderComparison.quotes).selectinload(TenderQuote.documents))
    )
    comparison = result.scalars().unique().one_or_none()
    if comparison is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparison not found")
    return comparison
