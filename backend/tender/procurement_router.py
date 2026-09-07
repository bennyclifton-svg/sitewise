"""One-action procurement review endpoints; reuse tender jobs and core artefacts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONPATH
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.billing.entitlements import require_active_entitlement
from app.database.projects import get_project, user_owns_project
from app.database.session import get_db
from app.database.users import ensure_user_exists
from app.procurement.strategy import (
    ProcurementStrategyConflict,
    ProcurementStrategyValidationError,
)
from tender.models import (
    TenderComparison,
    TenderDocument,
    TenderJob,
    TenderQuote,
    TenderReport,
)
from tender.services.artefact_publisher import tender_artefact_publisher
from tender.services.procurement_intake import start_procurement_review
from tender.services.procurement_review import review_evidence
from tender.services.review_progress import document_progress, review_activity

router = APIRouter(prefix="/procurement-reviews")
REVIEW_JOB_KINDS = {
    "ingest_document",
    "read_review_document",
    "prepare_procurement_review",
}
PROCESSING_UPDATE_MESSAGE = (
    "This review needs a service update before it can continue. "
    "Your submission files are saved; you do not need to upload them again."
)


class ReviewStart(BaseModel):
    project_id: uuid.UUID
    row_id: uuid.UUID
    expected_submission_revision: int = Field(ge=1)
    rerun: bool = False


async def _owned(
    session: AsyncSession, comparison_id: uuid.UUID, user: CurrentUser
) -> TenderComparison:
    comparison = await session.get(TenderComparison, comparison_id)
    if comparison is None or not user_owns_project(
        await get_project(session, comparison.project_id), user.id
    ):
        raise HTTPException(404, "Comparison not found")
    if not comparison.context.get("review_profile"):
        raise HTTPException(404, "Procurement review not found")
    return comparison


@router.post("")
async def start_review(
    body: ReviewStart,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await ensure_user_exists(session, user)
    await require_active_entitlement(session, user)
    try:
        comparison = await start_procurement_review(
            session,
            project_id=body.project_id,
            row_id=body.row_id,
            owner_user_id=user.id,
            expected_submission_revision=body.expected_submission_revision,
            rerun=body.rerun,
        )
    except ProcurementStrategyConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ProcurementStrategyValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"comparison_id": str(comparison.id)}


@router.get("/{comparison_id}")
async def get_review(
    comparison_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    comparison = await _owned(session, comparison_id, user)
    pending = list(
        (
            await session.execute(
                select(TenderJob)
                .where(TenderJob.comparison_id == comparison_id)
                .order_by(TenderJob.created_at)
            )
        ).scalars()
    )
    documents = list(
        (
            await session.execute(
                select(
                    TenderDocument.id,
                    TenderDocument.original_filename.label("filename"),
                    TenderQuote.builder_name.label("firm_name"),
                    TenderDocument.page_count.label("pages"),
                    TenderDocument.updated_at,
                    TenderDocument.review_data["complete"]
                    .as_boolean()
                    .label("complete"),
                    func.jsonb_path_query_array(
                        TenderDocument.review_data,
                        cast("$.windows.*.coverage[*].page_no", JSONPATH),
                    ).label("read_pages"),
                )
                .join(TenderQuote)
                .where(TenderQuote.comparison_id == comparison_id)
                .order_by(
                    TenderDocument.quote_group_position, TenderDocument.input_position
                )
            )
        ).mappings()
    )
    failed = next((job for job in pending if job.status == "failed"), None)
    wrong_pipeline = any(job.kind not in REVIEW_JOB_KINDS for job in pending)
    now = datetime.now(UTC)
    progress = [document_progress(doc, pending, now=now) for doc in documents]
    report = await session.scalar(
        select(TenderReport)
        .where(TenderReport.comparison_id == comparison_id)
        .order_by(TenderReport.version.desc())
        .limit(1)
    )
    draft = (
        await tender_artefact_publisher().read_projection(
            session, draft_id=report.draft_id
        )
        if report
        else None
    )
    phase = (
        "complete"
        if draft
        else "failed"
        if failed or wrong_pipeline
        else "preparing"
        if (progress and all(doc["complete"] for doc in progress))
        or any(job.kind == "prepare_procurement_review" for job in pending)
        else "reading"
    )
    error = None
    if wrong_pipeline:
        error = PROCESSING_UPDATE_MESSAGE
    elif failed:
        filename = next(
            (
                doc["filename"]
                for doc in documents
                if str(doc["id"]) == str((failed.payload or {}).get("document_id"))
            ),
            None,
        )
        error = (
            f"Could not finish reading {filename}. Retry from the saved pages, or link a clearer or updated copy in procurement."
            if filename
            else "Could not prepare the recommendation. Your submission files and completed reading are saved; retry the review."
        )
    return {
        "comparison_id": str(comparison.id),
        "row_id": comparison.context_provenance["row_id"],
        "phase": phase,
        "activity": review_activity(pending, now=now),
        "started_at": comparison.created_at,
        "package_name": comparison.context["package_name"],
        "draft": draft,
        "error": error,
        "can_retry": not wrong_pipeline,
        "documents": progress,
    }


@router.get("/{comparison_id}/evidence")
async def get_review_evidence(
    comparison_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    comparison = await _owned(session, comparison_id, user)
    if comparison.status != "report_draft":
        raise HTTPException(409, "The review is still being prepared")
    quotes, documents = await review_evidence(session, comparison)
    return {
        "quotes": quotes,
        "documents": documents,
        "review": comparison.context_provenance.get("review"),
    }


@router.post("/{comparison_id}/retry")
async def retry_review(
    comparison_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await _owned(session, comparison_id, user)
    await require_active_entitlement(session, user)
    pending = list(
        (
            await session.execute(
                select(TenderJob)
                .where(TenderJob.comparison_id == comparison_id)
                .with_for_update()
            )
        ).scalars()
    )
    if any(job.kind not in REVIEW_JOB_KINDS for job in pending):
        raise HTTPException(409, PROCESSING_UPDATE_MESSAGE)
    for job in pending:
        if job.status != "failed":
            continue
        job.status = "queued"
        job.attempts = 0
        job.last_error = None
        job.run_after = datetime.now(UTC)
    return {"comparison_id": str(comparison_id)}
