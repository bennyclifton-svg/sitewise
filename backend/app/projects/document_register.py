"""Structured, selectable rows from a project's document register."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.source_document import SourceDocument
from app.database.workspace_file import WorkspaceFile
from app.database.workspace_files import list_workspace_files_for_project
from app.inbox.paths import is_inbox_workspace_path
from ingest.document_metadata import strip_markdown_emphasis


class DocumentRegisterRow(BaseModel):
    """One UI document-register row that resolves to a stored project file."""

    id: uuid.UUID
    workspace_file_id: uuid.UUID
    source_document_id: uuid.UUID | None = None
    workspace_path: str = Field(max_length=1024)
    filename: str = Field(max_length=512)
    document_number: str | None = Field(default=None, max_length=255)
    title: str = Field(max_length=512)
    revision: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=255)


async def list_document_register_rows(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> list[DocumentRegisterRow]:
    """Return register rows backed by files that agent workflows can consume."""
    workspace_files = await list_workspace_files_for_project(
        session,
        project_id=project_id,
    )
    result = await session.execute(
        select(SourceDocument)
        .where(
            SourceDocument.project_id == project_id,
            SourceDocument.source_type == "project_evidence",
        )
        .order_by(SourceDocument.relative_path.asc(), SourceDocument.id.asc())
    )
    source_documents = list(result.scalars().all())
    return build_document_register_rows(source_documents, workspace_files)


def build_document_register_rows(
    source_documents: Sequence[SourceDocument],
    workspace_files: Sequence[WorkspaceFile],
) -> list[DocumentRegisterRow]:
    """Mirror UI register identity while excluding rows with no stored file."""
    workspace_by_path = {
        _normalise_path(record.workspace_path): record for record in workspace_files
    }
    indexed_paths: set[str] = set()
    rows: list[DocumentRegisterRow] = []

    for document in source_documents:
        path = _normalise_path(document.relative_path)
        indexed_paths.add(path)
        workspace_file = workspace_by_path.get(path)
        if workspace_file is None:
            continue
        metadata = (
            document.document_metadata
            if isinstance(document.document_metadata, dict)
            else {}
        )
        title = _register_title(document, metadata)
        rows.append(
            DocumentRegisterRow(
                id=document.id,
                workspace_file_id=workspace_file.id,
                source_document_id=document.id,
                workspace_path=workspace_file.workspace_path,
                filename=workspace_file.filename,
                document_number=_metadata_text(metadata, "document_number"),
                title=title,
                revision=_metadata_text(metadata, "revision"),
                category=_metadata_text(metadata, "discipline"),
            )
        )

    for workspace_file in workspace_files:
        path = _normalise_path(workspace_file.workspace_path)
        if path in indexed_paths or not is_inbox_workspace_path(path):
            continue
        rows.append(
            DocumentRegisterRow(
                id=workspace_file.id,
                workspace_file_id=workspace_file.id,
                source_document_id=None,
                workspace_path=workspace_file.workspace_path,
                filename=workspace_file.filename,
                title=workspace_file.filename,
            )
        )

    return sorted(rows, key=lambda row: (_normalise_path(row.workspace_path), str(row.id)))


def search_document_register_rows(
    rows: Iterable[DocumentRegisterRow],
    *,
    query: str | None,
    query_field: str = "any",
    document_number_greater_than: int | None = None,
    limit: int,
) -> list[DocumentRegisterRow]:
    """Apply a case-insensitive keyword search over structured register fields."""
    terms = [term.casefold() for term in (query or "").split() if term.strip()]
    matches: list[DocumentRegisterRow] = []
    for row in rows:
        haystack = " ".join(_search_values(row, query_field)).casefold()
        if terms and not all(term in haystack for term in terms):
            continue
        if document_number_greater_than is not None:
            number = _numeric_document_number(row.document_number)
            if number is None or number <= document_number_greater_than:
                continue
        matches.append(row)
        if len(matches) >= limit:
            break
    return matches


def _search_values(row: DocumentRegisterRow, query_field: str) -> list[str]:
    values = {
        "document_number": row.document_number,
        "title": row.title,
        "revision": row.revision,
        "category": row.category,
        "filename": row.filename,
        "path": row.workspace_path,
    }
    if query_field == "any":
        return [value for value in values.values() if value]
    value = values.get(query_field)
    return [value] if value else []


def _numeric_document_number(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        number = Decimal(value.replace(",", "").strip())
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _register_title(document: SourceDocument, metadata: dict) -> str:
    if document.document_class == "specification":
        stem = document.filename.rsplit("/", maxsplit=1)[-1]
        stem = stem.rsplit(".", maxsplit=1)[0]
        return stem.replace("_", " ").replace("-", " ").strip() or document.filename
    return (
        _metadata_text(metadata, "title")
        or document.document_type
        or document.filename
    )


def _metadata_text(metadata: dict, key: str) -> str | None:
    value = metadata.get(key)
    if not isinstance(value, str):
        return None
    stripped = strip_markdown_emphasis(" ".join(value.split()))
    return stripped or None


def _normalise_path(path: str) -> str:
    return path.replace("\\", "/")
