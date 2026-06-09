from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.project import Project
from app.database.source_document import SourceDocument
from app.inbox.drawing_detection import detect_from_info
from app.inbox.pdf_inspect import inspect_pdf
from app.inbox.pdf_split import split_pdf_pages
from app.inbox.service import InboxUploadItem, InboxUploadOutcome, upload_inbox_files
from app.inbox.sheet_titles import SheetPlan, build_sheet_plan
from app.storage.project_files import (
    delete_project_file,
    download_project_file,
    upload_project_file,
)

logger = structlog.get_logger(__name__)

_SUCCESS_STATUSES = {"ingested", "skipped"}


@dataclass(frozen=True, slots=True)
class SheetProposal:
    index: int
    proposed_title: str
    filename: str
    has_text: bool


@dataclass(frozen=True, slots=True)
class AnalyzeResult:
    staging_id: str
    storage_key: str
    is_drawing_set: bool
    confidence: float
    page_count: int
    scores: dict
    pages: list[SheetProposal]


def _staging_storage_key(project_id: uuid.UUID, staging_id: str) -> str:
    return f"{project_id}/_staging/{staging_id}.pdf"


async def analyze_pdf_upload(
    *, project: Project, filename: str, content: bytes
) -> AnalyzeResult:
    staging_id = uuid.uuid4().hex
    storage_key = _staging_storage_key(project.id, staging_id)

    await asyncio.to_thread(
        upload_project_file, storage_key=storage_key, content=content, filename=filename
    )

    info = inspect_pdf(content)
    detection = detect_from_info(info)
    sheet_plan = build_sheet_plan(content, source_filename=filename)

    pages = [
        SheetProposal(
            index=plan.index,
            proposed_title=plan.title,
            filename=plan.filename,
            has_text=page.has_text if page is not None else False,
        )
        for plan, page in zip(sheet_plan, info.pages)
    ]

    logger.info(
        "pdf_analyzed",
        project=project.slug,
        staging_id=staging_id,
        is_drawing_set=detection.is_drawing_set,
        page_count=detection.page_count,
    )

    return AnalyzeResult(
        staging_id=staging_id,
        storage_key=storage_key,
        is_drawing_set=detection.is_drawing_set,
        confidence=detection.confidence,
        page_count=detection.page_count,
        scores=detection.scores,
        pages=pages,
    )


async def _attach_split_provenance(
    session: AsyncSession,
    *,
    outcomes: list[InboxUploadOutcome],
    sheet_plans: list[SheetPlan],
    source_filename: str,
    source_hash: str,
) -> None:
    by_filename = {plan.filename: plan for plan in sheet_plans}
    for outcome in outcomes:
        plan = by_filename.get(outcome.filename)
        if plan is None or outcome.ingest_status not in _SUCCESS_STATUSES:
            continue
        provenance = {
            "split_from": source_filename,
            "split_source_hash": source_hash,
            "sheet_index": plan.index,
            "sheet_total": len(sheet_plans),
            "sheet_number_label": plan.sheet_number_label,
            "sheet_scale": plan.scale,
            "split_method": "heuristic_v1",
            "title": plan.title,
        }
        doc = await session.get(SourceDocument, outcome.id)
        if doc is not None:
            merged = dict(doc.document_metadata or {})
            merged.update({k: v for k, v in provenance.items() if v is not None})
            doc.document_metadata = merged
    await session.flush()


async def split_staged_pdf(
    session: AsyncSession,
    *,
    project: Project,
    staging_id: str,
    source_filename: str,
) -> list[InboxUploadOutcome]:
    storage_key = _staging_storage_key(project.id, staging_id)
    content = await asyncio.to_thread(download_project_file, storage_key=storage_key)
    source_hash = hashlib.sha256(content).hexdigest()

    page_blobs = await asyncio.to_thread(split_pdf_pages, content)
    sheet_plans = build_sheet_plan(content, source_filename=source_filename)

    items = [
        InboxUploadItem(filename=plan.filename, content=blob)
        for plan, blob in zip(sheet_plans, page_blobs)
    ]
    outcomes = await upload_inbox_files(session, project=project, items=items)

    succeeded = [o for o in outcomes if o.ingest_status in _SUCCESS_STATUSES]
    if succeeded:
        await _attach_split_provenance(
            session,
            outcomes=outcomes,
            sheet_plans=sheet_plans,
            source_filename=source_filename,
            source_hash=source_hash,
        )
        await session.commit()
        await asyncio.to_thread(delete_project_file, storage_key=storage_key)
    else:
        logger.warning(
            "pdf_split_all_failed", staging_id=staging_id, project=project.slug
        )

    return outcomes


async def commit_staged_pdf_single(
    session: AsyncSession,
    *,
    project: Project,
    staging_id: str,
    source_filename: str,
) -> InboxUploadOutcome:
    storage_key = _staging_storage_key(project.id, staging_id)
    content = await asyncio.to_thread(download_project_file, storage_key=storage_key)
    outcomes = await upload_inbox_files(
        session,
        project=project,
        items=[InboxUploadItem(filename=source_filename, content=content)],
    )
    await asyncio.to_thread(delete_project_file, storage_key=storage_key)
    return outcomes[0]
