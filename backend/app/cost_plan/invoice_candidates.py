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
    r"^#\s+(?:tax\s+)?invoice\b",
    re.IGNORECASE | re.MULTILINE,
)
_INVOICE_NUMBER_RE = re.compile(
    r"(?:"
    r"^\*\*invoice\s+(?:number|no\.?):\*\*\s*\S+"
    r"|"
    r"^\|\s*\*\*invoice\s+(?:number|no\.?)\*\*\s*\|"
    r")",
    re.IGNORECASE | re.MULTILINE,
)
_INVOICE_FILENAME_RE = re.compile(r"(?:invoice|\binv[-_])", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class InvoiceCandidate:
    source_document_id: uuid.UUID
    workspace_file_id: uuid.UUID | None
    filename: str
    relative_path: str
    content_hash: str
    content: str


def is_invoice_document(
    *,
    filename: str,
    content: str,
    document_class: str | None = None,
    document_metadata: dict | None = None,
) -> bool:
    metadata = document_metadata if isinstance(document_metadata, dict) else {}
    cls = (document_class or "").strip().lower()
    if cls == "commercial":
        return metadata.get("commercial_type") == "invoice"
    if cls and cls != "unknown":
        return False
    filename_hint = _INVOICE_FILENAME_RE.search(filename) is not None
    return bool(
        _INVOICE_HEADING_RE.search(content)
        or (filename_hint and _INVOICE_NUMBER_RE.search(content))
    )


async def resolve_invoice_source_document_ids(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    document_ids: list[uuid.UUID],
) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
    """Map UI/tool ids to SourceDocument ids.

    Accepts either ``source_document_id`` or ``workspace_file_id`` values. Returns
    ``(resolved_source_document_ids, unresolved_ids)`` in stable first-seen order.
    """
    if not document_ids:
        return [], []

    workspace_rows = (
        await session.execute(
            select(WorkspaceFile.id, WorkspaceFile.source_document_id).where(
                WorkspaceFile.project_id == project_id,
                WorkspaceFile.id.in_(document_ids),
                WorkspaceFile.source_document_id.is_not(None),
            )
        )
    ).all()
    workspace_to_source = {
        workspace_id: source_id
        for workspace_id, source_id in workspace_rows
        if source_id is not None
    }

    existing_sources = set(
        (
            await session.execute(
                select(SourceDocument.id).where(
                    SourceDocument.project_id == project_id,
                    SourceDocument.id.in_(document_ids),
                    SourceDocument.source_type == "project_evidence",
                )
            )
        )
        .scalars()
        .all()
    )

    resolved: list[uuid.UUID] = []
    unresolved: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    for document_id in document_ids:
        source_id = (
            document_id
            if document_id in existing_sources
            else workspace_to_source.get(document_id)
        )
        if source_id is None:
            unresolved.append(document_id)
            continue
        if source_id in seen:
            continue
        seen.add(source_id)
        resolved.append(source_id)
    return resolved, unresolved


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
        resolved_ids, _unresolved = await resolve_invoice_source_document_ids(
            session,
            project_id=project_id,
            document_ids=source_document_ids,
        )
        if not resolved_ids:
            return []
        statement = statement.where(SourceDocument.id.in_(resolved_ids))

    rows = (await session.execute(statement)).all()
    candidates: list[InvoiceCandidate] = []
    for document, workspace_file in rows:
        if workspace_file is not None and workspace_file.ingest_status != "ingested":
            continue
        # An explicit selection is the user's invoice even if the heading
        # heuristic has not seen this layout before. Extraction then accepts
        # the file or records a precise error instead of failing the run.
        if source_document_ids is None and not is_invoice_document(
            filename=document.filename,
            content=document.normalized_content,
            document_class=document.document_class,
            document_metadata=(
                document.document_metadata
                if isinstance(document.document_metadata, dict)
                else None
            ),
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
