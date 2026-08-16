"""Trusted document-register context for a single agent turn."""
from __future__ import annotations

import uuid
from collections.abc import Sequence

from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.source_document import SourceDocument
from app.database.workspace_file import WorkspaceFile
from ingest.document_metadata import strip_markdown_emphasis


class SelectedDocumentContextError(ValueError):
    """The requested document-register selection cannot be used for this turn."""


class SelectedTurnDocument(BaseModel):
    """Server-derived reference to one immutable file version."""

    workspace_file_id: uuid.UUID
    source_document_id: uuid.UUID | None = None
    workspace_path: str = Field(max_length=1024)
    filename: str = Field(max_length=512)
    content_hash: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)
    document_number: str | None = Field(default=None, max_length=255)
    title: str = Field(max_length=512)
    revision: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=255)


async def resolve_selected_turn_documents(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    document_ids: Sequence[uuid.UUID],
) -> list[SelectedTurnDocument]:
    """Resolve UI register rows to canonical project files in the submitted order."""
    if not document_ids:
        return []
    if len(set(document_ids)) != len(document_ids):
        raise SelectedDocumentContextError("A selected document was included more than once.")

    rows = (
        await session.execute(
            select(WorkspaceFile, SourceDocument)
            .outerjoin(
                SourceDocument,
                WorkspaceFile.source_document_id == SourceDocument.id,
            )
            .where(
                WorkspaceFile.project_id == project_id,
                or_(
                    WorkspaceFile.id.in_(document_ids),
                    SourceDocument.id.in_(document_ids),
                ),
            )
        )
    ).all()
    by_register_id: dict[uuid.UUID, SelectedTurnDocument] = {}
    for workspace_file, source_document in rows:
        document = _selected_document(workspace_file, source_document)
        by_register_id[workspace_file.id] = document
        if source_document is not None:
            by_register_id[source_document.id] = document

    resolved = [by_register_id.get(document_id) for document_id in document_ids]
    if any(document is None for document in resolved):
        raise SelectedDocumentContextError(
            "One or more selected documents are no longer available in this project."
        )
    documents = [document for document in resolved if document is not None]
    if len({document.workspace_file_id for document in documents}) != len(documents):
        raise SelectedDocumentContextError("A selected file was included more than once.")
    return documents


def documents_from_turn_context(value: object) -> list[SelectedTurnDocument]:
    """Read the server-derived selection stored when a turn was reserved."""
    if not isinstance(value, dict):
        return []
    raw_documents = value.get("selected_documents")
    if not isinstance(raw_documents, list):
        return []
    try:
        return [SelectedTurnDocument.model_validate(item) for item in raw_documents]
    except (TypeError, ValueError):
        return []


def _selected_document(
    workspace_file: WorkspaceFile,
    source_document: SourceDocument | None,
) -> SelectedTurnDocument:
    metadata = source_document.document_metadata if source_document is not None else None
    metadata = metadata if isinstance(metadata, dict) else {}
    title = _metadata_text(metadata, "title")
    if title is None and source_document is not None:
        title = source_document.document_type
    return SelectedTurnDocument(
        workspace_file_id=workspace_file.id,
        source_document_id=workspace_file.source_document_id,
        workspace_path=workspace_file.workspace_path,
        filename=workspace_file.filename,
        content_hash=workspace_file.content_hash,
        size_bytes=workspace_file.size_bytes,
        document_number=_metadata_text(metadata, "document_number"),
        title=title or workspace_file.filename,
        revision=_metadata_text(metadata, "revision"),
        category=_metadata_text(metadata, "discipline"),
    )


def _metadata_text(metadata: dict, key: str) -> str | None:
    value = metadata.get(key)
    if not isinstance(value, str):
        return None
    stripped = strip_markdown_emphasis(" ".join(value.split()))
    return stripped or None
