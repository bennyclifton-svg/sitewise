"""Freeze a procurement row's submissions into the existing tender queue."""

from __future__ import annotations

import mimetypes
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database.procurement_strategy import (
    ProcurementStrategy,
    ProcurementStrategyRow,
)
from app.database.project import Project
from app.procurement.candidate_submissions import resolve_submission_files
from app.procurement.strategy import (
    ProcurementStrategyConflict,
    ProcurementStrategyValidationError,
)
from app.projects.document_selections import lock_workflow_inputs
from tender.models import TenderComparison, TenderDocument, TenderJob, TenderQuote
from tender.schemas import ProjectContext
from tender.services import jobs
from tender.services.intake import _digest


def review_profile(row: ProcurementStrategyRow) -> str:
    if (
        row.discipline_code == "trade.main_works"
        or row.request_kind == "contractor_eoi"
    ):
        return "head_contractor"
    return "consultant" if row.participant_type == "consultant" else "trade"


async def start_procurement_review(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    row_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    expected_submission_revision: int,
    rerun: bool = False,
) -> TenderComparison:
    # Serialize intake with edits, and reject all cross-project identifiers before enqueueing.
    project = await session.scalar(
        select(Project)
        .where(
            Project.id == project_id,
            Project.owner_user_id == owner_user_id,
        )
        .with_for_update()
    )
    if project is None:
        raise ProcurementStrategyValidationError("Project not found")
    row = await session.scalar(
        select(ProcurementStrategyRow)
        .join(ProcurementStrategy)
        .where(
            ProcurementStrategy.project_id == project_id,
            ProcurementStrategyRow.id == row_id,
        )
        .options(selectinload(ProcurementStrategyRow.candidates))
        .with_for_update()
    )
    if row is None:
        raise ProcurementStrategyValidationError("Procurement row not found")
    if (row.submission_revision or 1) != expected_submission_revision:
        raise ProcurementStrategyConflict(
            "Submission files have changed; refresh and compare again"
        )
    submissions = []
    for candidate in sorted(row.candidates, key=lambda value: value.slot):
        if not candidate.submission_files:
            continue
        files = await resolve_submission_files(
            session,
            project_id=project_id,
            file_ids=[link.workspace_file_id for link in candidate.submission_files],
        )
        submissions.append((candidate, files))
    if not submissions:
        raise ProcurementStrategyValidationError(
            "Link at least one submission to a firm before comparing"
        )
    snapshot = {
        "queue_scope": settings.workflow_queue_scope,
        "row_id": str(row.id),
        "submission_revision": row.submission_revision or 1,
        "profile": review_profile(row),
        "package_name": row.discipline_label,
        "submissions": [
            {
                "candidate_id": str(candidate.id),
                "firm": candidate.company_name,
                "files": [
                    {
                        "id": str(file.id),
                        "hash": file.content_hash,
                        "path": file.workspace_path,
                        "filename": file.filename,
                        "storage_key": file.storage_key,
                    }
                    for file in files
                ],
            }
            for candidate, files in submissions
        ],
    }
    fingerprint = _digest(snapshot)
    existing = await session.scalar(
        select(TenderComparison)
        .where(
            TenderComparison.project_id == project_id,
            TenderComparison.input_fingerprint == fingerprint,
        )
        .order_by(TenderComparison.created_at.desc())
        .limit(1)
    )
    active = None
    if existing is not None and rerun and existing.status in {"intake", "processing"}:
        active = await session.scalar(
            select(TenderJob.id)
            .where(
                TenderJob.comparison_id == existing.id,
                TenderJob.status.in_(("queued", "running")),
            )
            .limit(1)
        )
    if existing is not None and (not rerun or active is not None):
        row.comparison_id = existing.id
        return existing
    comparison = TenderComparison(
        project_id=project_id,
        created_by=owner_user_id,
        status="processing",
        context=ProjectContext(
            context_source="repository_selection",
            review_profile=snapshot["profile"],
            package_name=row.discipline_label,
        ).model_dump(mode="json"),
        context_provenance={
            **snapshot,
            "review_date": datetime.now(UTC).date().isoformat(),
            "review_version": "1.0.0",
        },
        input_fingerprint=fingerprint,
    )
    session.add(comparison)
    await session.flush()
    file_ids = []
    for position, (candidate, files) in enumerate(submissions):
        quote = TenderQuote(
            comparison_id=comparison.id,
            builder_name=candidate.company_name,
            stage="ingest_document",
        )
        session.add(quote)
        await session.flush()
        seen_hashes = set()
        for file_position, file in enumerate(files):
            if file.content_hash in seen_hashes:
                continue
            seen_hashes.add(file.content_hash)
            document = TenderDocument(
                quote_id=quote.id,
                storage_path=file.storage_key,
                original_filename=file.filename,
                mime_type=mimetypes.guess_type(file.filename)[0]
                or "application/octet-stream",
                content_hash=file.content_hash,
                workspace_file_id=file.id,
                storage_bucket=file.storage_bucket,
                storage_version=file.content_hash,
                quote_group_position=position,
                input_position=file_position,
                ingest_status="pending",
                review_data={},
            )
            session.add(document)
            await session.flush()
            await jobs.enqueue(
                session,
                kind="ingest_document",
                comparison_id=comparison.id,
                quote_id=quote.id,
                payload={"document_id": str(document.id), "procurement_review": True},
            )
            file_ids.append(file.id)
    await lock_workflow_inputs(
        session,
        project_id=project_id,
        workflow_type="tender_comparison",
        workflow_id=comparison.id,
        workspace_file_ids=file_ids,
    )
    row.comparison_id = comparison.id
    row.recommendation_stale = row.recommendation_draft_id is not None
    if row.status not in {"awarded", "cancelled"}:
        row.status = "evaluating"
    return comparison
