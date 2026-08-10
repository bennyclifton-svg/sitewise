"""Deterministic outbound document registers for procurement requests."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.source_document import SourceDocument
from ingest.document_metadata import (
    infer_discipline_from_file_name,
    infer_discipline_from_path,
    parse_document_metadata,
)

_MAIN_WORKS_NAMES = frozenset(
    {"main works", "head contractor", "main contractor", "builder"}
)
_BRIEF_PATH_MARKER = "/00-brief-pmp/"
_AUTHORITY_PATH_MARKER = "/04-planning-and-authorities/"
_PROJECT_INTENT_RE = re.compile(
    r"\b(?:ppr|principal'?s?\s+project\s+requirements?|"
    r"(?:owner|client|project)\s+brief)\b",
    re.IGNORECASE,
)


async def load_procurement_document_register(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    target_name: str,
) -> list[dict[str, Any]]:
    """Return issue documents by package without using semantic retrieval.

    Main Works receives the complete project evidence corpus. Narrow packages
    receive their discipline, the architectural/general base, the brief/PPR,
    and approval documents needed to understand interfaces.
    """
    result = await session.execute(
        select(
            SourceDocument.id,
            SourceDocument.filename,
            SourceDocument.relative_path,
            SourceDocument.document_class,
            SourceDocument.document_metadata,
            SourceDocument.content_hash,
        )
        .where(
            SourceDocument.project_id == project_id,
            SourceDocument.source_type == "project_evidence",
        )
        .order_by(SourceDocument.relative_path.asc(), SourceDocument.id.asc())
    )
    target_key = _normalise(target_name)
    include_all = target_key in _MAIN_WORKS_NAMES
    primary_discipline = infer_discipline_from_file_name(target_name)

    documents: list[dict[str, Any]] = []
    for document in result.all():
        metadata = (
            dict(document.document_metadata)
            if isinstance(document.document_metadata, dict)
            else {}
        )
        metadata_discipline = str(metadata.get("discipline") or "").strip()
        inferred_discipline = infer_discipline_from_file_name(document.filename)
        path = str(document.relative_path).replace("\\", "/")
        path_discipline = infer_discipline_from_path(path)
        effective_discipline = (
            path_discipline
            or inferred_discipline
            or (metadata_discipline if metadata_discipline.casefold() != "project" else "")
        )
        is_primary = bool(
            primary_discipline
            and (
                metadata_discipline.casefold() == primary_discipline.casefold()
                or inferred_discipline == primary_discipline
                or path_discipline == primary_discipline
            )
        )
        is_context = (
            _BRIEF_PATH_MARKER in path
            or _AUTHORITY_PATH_MARKER in path
            or _is_project_intent(document.filename, metadata)
            or metadata_discipline.casefold() == "architectural"
            or inferred_discipline == "Architectural"
        )
        if not include_all and not is_primary and not is_context:
            continue

        if is_primary and primary_discipline:
            metadata["discipline"] = primary_discipline
        elif effective_discipline:
            metadata["discipline"] = effective_discipline

        _normalise_register_identity(
            metadata,
            filename=document.filename,
            relative_path=path,
        )

        document_number = metadata.get("document_number") or metadata.get(
            "drawing_number"
        )
        label = str(document_number or document.filename)
        documents.append(
            {
                "role": "issued_document",
                "role_label": _inclusion_label(
                    include_all=include_all,
                    is_primary=is_primary,
                ),
                "document_id": str(document.id),
                "chunk_id": "",
                "filename": document.filename,
                "relative_path": document.relative_path,
                "page_or_section": metadata.get("revision") or None,
                "snippet": (
                    f"Issue register entry: {label}. "
                    f"Title: {metadata.get('title') or document.filename}."
                ),
                "score": None,
                "document_class": document.document_class,
                "document_metadata": metadata,
                "content_hash": getattr(document, "content_hash", None),
            }
        )
    return sorted(
        documents,
        key=lambda item: (
            str(item.get("relative_path") or "").casefold(),
            str(item.get("document_id") or ""),
        ),
    )


def _normalise(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def _is_project_intent(filename: str, metadata: dict[str, Any]) -> bool:
    text = " ".join(
        (
            filename,
            str(metadata.get("title") or ""),
            str(metadata.get("document_type") or ""),
        )
    )
    return _PROJECT_INTENT_RE.search(text) is not None


def _inclusion_label(*, include_all: bool, is_primary: bool) -> str:
    if include_all:
        return "Main Works issue document"
    if is_primary:
        return "Primary discipline issue document"
    return "Package context issue document"


def _normalise_register_identity(
    metadata: dict[str, Any], *, filename: str, relative_path: str
) -> None:
    parsed = parse_document_metadata(
        file_name=filename,
        filed_path=relative_path,
    )
    revision = str(metadata.get("revision") or "").strip()
    if not revision or revision.casefold() == "current":
        revision = "" if parsed.revision == "Current" else parsed.revision
        metadata["revision"] = revision

    document_number = str(
        metadata.get("document_number") or metadata.get("drawing_number") or ""
    ).strip()
    if not document_number and parsed.document_number:
        document_number = parsed.document_number
    if revision and document_number:
        document_number = re.sub(
            rf"(?:\s+|[-_/]){re.escape(revision)}$",
            "",
            document_number,
            flags=re.IGNORECASE,
        ).strip()
    if document_number:
        metadata["document_number"] = document_number
    if not str(metadata.get("title") or "").strip() and parsed.title:
        metadata["title"] = parsed.title
