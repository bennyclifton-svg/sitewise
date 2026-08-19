"""Email attachments enter canonical intake through the inbox upload path."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.project import Project
from app.database.workspace_file import WorkspaceFile
from app.email.models import ProjectEmailAttachment, ProjectEmailInterpretation
from app.inbox.service import (
    InboxUploadItem,
    InboxUploadOutcome,
    store_and_queue_inbox_file,
)
from app.projects.snapshot import get_project_snapshot


class EmailAttachmentUnmatched(LookupError):
    """Attachment ingest requires a project match (Stage 17)."""


async def ingest_email_attachment(
    session: AsyncSession,
    *,
    project: Project,
    email_id: uuid.UUID,
    filename: str,
    content: bytes,
    created_by_user_id: uuid.UUID,
) -> InboxUploadOutcome:
    """Store and ingest via the same inbox path as a manual upload."""
    interpretation = await session.get(ProjectEmailInterpretation, email_id)
    if interpretation is None or interpretation.project_id is None:
        raise EmailAttachmentUnmatched(
            "email attachment ingest requires a project match"
        )
    if interpretation.project_id != project.id:
        raise EmailAttachmentUnmatched(
            "email is matched to a different project"
        )

    snapshot = await get_project_snapshot(session, project_id=project.id)
    outcome = await store_and_queue_inbox_file(
        session,
        project=project,
        item=InboxUploadItem(
            filename=filename,
            content=content,
            ingest_metadata={"source": "email", "email_id": str(email_id)},
        ),
        user_id=created_by_user_id,
        snapshot=snapshot,
    )
    attachment = (
        await session.execute(
            select(ProjectEmailAttachment).where(
                ProjectEmailAttachment.email_id == email_id,
                ProjectEmailAttachment.filename == filename,
            )
        )
    ).scalar_one_or_none()
    if attachment is not None:
        attachment.content_hash = outcome.content_hash
        workspace = await session.get(WorkspaceFile, outcome.id)
        if workspace is not None:
            attachment.source_document_id = workspace.source_document_id
            if workspace.source_document_id is not None:
                from app.procurement.submissions import link_submission_to_request

                await link_submission_to_request(
                    session,
                    project_id=project.id,
                    source_document_id=workspace.source_document_id,
                )
    return outcome
