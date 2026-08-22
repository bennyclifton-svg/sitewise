"""Link classified commercial submissions to issued procurement requests."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.procurement_request import ProcurementRequest
from app.database.procurement_request_submission import ProcurementRequestSubmission
from app.database.source_document import SourceDocument
from app.email.models import ProjectEmail, ProjectEmailAttachment, ProjectEmailDraft
from app.procurement.strategy import advance_strategy_status


def _header_message_ids(email: ProjectEmail) -> set[str]:
    ids: set[str] = set()
    headers = email.headers or {}
    for key in ("in-reply-to", "In-Reply-To", "references", "References"):
        value = headers.get(key)
        if isinstance(value, str):
            ids.update(part.strip() for part in value.split() if part.strip())
        elif isinstance(value, list):
            ids.update(str(item).strip() for item in value if str(item).strip())
    if email.provider_thread_id:
        ids.add(email.provider_thread_id)
    return ids


def _matches_issue_thread(email: ProjectEmail, draft: ProjectEmailDraft) -> bool:
    if draft.provider_message_id and draft.provider_message_id == email.provider_message_id:
        return True
    reply_ids = _header_message_ids(email)
    if draft.provider_message_id and draft.provider_message_id in reply_ids:
        return True
    thread_id = (draft.references or {}).get("provider_thread_id")
    if thread_id and email.provider_thread_id == thread_id:
        return True
    return False


def _matches_target(
    request: ProcurementRequest, *, filename: str, subject: str
) -> bool:
    haystack = f"{filename} {subject}".lower()
    collapsed = haystack.replace("_", " ").replace("-", " ")
    name = (request.target_name or "").lower()
    slug = (request.target_slug or "").lower()
    if name and name in collapsed:
        return True
    if slug and slug in haystack.replace(" ", "_"):
        return True
    slug_words = slug.replace("_", " ")
    if slug_words and slug_words in collapsed:
        return True
    return False


async def list_request_submissions(
    session: AsyncSession, *, request_id: uuid.UUID
) -> list[ProcurementRequestSubmission]:
    result = await session.execute(
        select(ProcurementRequestSubmission).where(
            ProcurementRequestSubmission.request_id == request_id
        )
    )
    return list(result.scalars())


async def link_submission_to_request(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    source_document_id: uuid.UUID,
) -> ProcurementRequest | None:
    document = await session.get(SourceDocument, source_document_id)
    if document is None or document.project_id != project_id:
        return None
    if document.document_class != "commercial":
        return None
    metadata = document.document_metadata or {}
    if metadata.get("procurement_stage") != "submission":
        return None

    attachment = (
        await session.execute(
            select(ProjectEmailAttachment).where(
                ProjectEmailAttachment.source_document_id == source_document_id
            )
        )
    ).scalar_one_or_none()
    email = None
    if attachment is not None:
        email = await session.get(ProjectEmail, attachment.email_id)

    issued = list(
        (
            await session.execute(
                select(ProcurementRequest).where(
                    ProcurementRequest.project_id == project_id,
                    ProcurementRequest.status == "issued",
                )
            )
        ).scalars()
    )
    filename = document.filename or ""
    subject = email.subject if email is not None else ""

    matched: ProcurementRequest | None = None
    for request in issued:
        if request.issue_email_draft_id is None:
            continue
        draft = await session.get(ProjectEmailDraft, request.issue_email_draft_id)
        if (
            email is not None
            and draft is not None
            and _matches_issue_thread(email, draft)
        ):
            matched = request
            break
    if matched is None:
        for request in issued:
            if _matches_target(request, filename=filename, subject=subject):
                matched = request
                break
    if matched is None:
        return None

    existing = (
        await session.execute(
            select(ProcurementRequestSubmission).where(
                ProcurementRequestSubmission.request_id == matched.id,
                ProcurementRequestSubmission.source_document_id == source_document_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            ProcurementRequestSubmission(
                request_id=matched.id,
                source_document_id=source_document_id,
            )
        )
        await session.flush()
    await advance_strategy_status(
        session, request=matched, status="responses_received"
    )
    return matched
