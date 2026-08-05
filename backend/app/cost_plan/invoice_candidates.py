from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.source_document import SourceDocument
from app.database.workspace_file import WorkspaceFile


_INVOICE_HEADING_RE = re.compile(
    r"^#\s+(?:tax\s+)?invoice(?:\s*/\s*progress\s+claim)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_INVOICE_NUMBER_RE = re.compile(
    r"^\*\*invoice\s+(?:number|no\.?):\*\*\s*\S+",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class InvoiceCandidate:
    source_document_id: uuid.UUID
    workspace_file_id: uuid.UUID | None
    filename: str
    relative_path: str
    content_hash: str
    content: str


def is_invoice_document(*, filename: str, content: str) -> bool:
    filename_hint = "invoice" in filename.lower()
    return bool(
        _INVOICE_HEADING_RE.search(content)
        or (filename_hint and _INVOICE_NUMBER_RE.search(content))
    )


async def discover_invoice_candidates(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    source_document_ids: list[uuid.UUID] | None = None,
) -> list[InvoiceCandidate]:
    statement = (
        select(SourceDocument, WorkspaceFile)
        .outerjoin(
            WorkspaceFile,
            (WorkspaceFile.project_id == SourceDocument.project_id)
            & (WorkspaceFile.source_document_id == SourceDocument.id),
        )
        .where(
            SourceDocument.project_id == project_id,
            SourceDocument.source_type == "project_evidence",
        )
        .order_by(SourceDocument.relative_path, SourceDocument.id)
    )
    if source_document_ids is not None:
        if not source_document_ids:
            return []
        statement = statement.where(SourceDocument.id.in_(source_document_ids))

    rows = (await session.execute(statement)).all()
    candidates: list[InvoiceCandidate] = []
    for document, workspace_file in rows:
        if workspace_file is not None and workspace_file.ingest_status != "ingested":
            continue
        if not is_invoice_document(
            filename=document.filename,
            content=document.normalized_content,
        ):
            continue
        content_hash = (
            document.content_hash
            or hashlib.sha256(document.normalized_content.encode("utf-8")).hexdigest()
        )
        candidates.append(
            InvoiceCandidate(
                source_document_id=document.id,
                workspace_file_id=workspace_file.id if workspace_file is not None else None,
                filename=document.filename,
                relative_path=document.relative_path,
                content_hash=content_hash,
                content=document.normalized_content,
            )
        )
    return candidates


async def count_pending_invoice_ingests(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(WorkspaceFile)
        .where(
            WorkspaceFile.project_id == project_id,
            WorkspaceFile.ingest_status.in_(("pending", "queued", "ingesting")),
            func.lower(WorkspaceFile.filename).contains("invoice"),
        )
    )
    return int(count or 0)
