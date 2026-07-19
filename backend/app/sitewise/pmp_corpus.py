"""Active project corpus helpers for PMP evidence sweeps."""

from __future__ import annotations

from dataclasses import dataclass
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.source_document import SourceDocument

SUPERSEDED_STATUS = "superseded"


@dataclass(frozen=True, slots=True)
class CorpusListingResult:
    documents: tuple[SourceDocument, ...]
    total_indexed: int
    skipped_superseded: int
    skipped_revision_duplicate: int
    capped: bool


def _metadata_dict(document: SourceDocument) -> dict:
    metadata = document.document_metadata
    return metadata if isinstance(metadata, dict) else {}


def document_metadata_status(document: SourceDocument) -> str | None:
    metadata = _metadata_dict(document)
    for key in ("status", "document_status"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return None


def is_retained_active(document: SourceDocument) -> bool:
    return _metadata_dict(document).get("retained_active") is True


def is_active_pmp_corpus_document(document: SourceDocument) -> bool:
    """Return True when a source document belongs to the current active corpus."""
    if document.source_type != "project_evidence":
        return False
    status = document_metadata_status(document)
    if status == SUPERSEDED_STATUS and not is_retained_active(document):
        return False
    return True


def _document_number(document: SourceDocument) -> str | None:
    value = _metadata_dict(document).get("document_number")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _dedupe_revision_groups(
    documents: list[SourceDocument],
) -> tuple[list[SourceDocument], int]:
    """Keep the latest active revision per document number."""
    without_number: list[SourceDocument] = []
    grouped: dict[str, list[SourceDocument]] = {}
    for document in documents:
        number = _document_number(document)
        if number is None:
            without_number.append(document)
            continue
        grouped.setdefault(number, []).append(document)

    active = list(without_number)
    skipped = 0
    for group in grouped.values():
        if len(group) == 1:
            active.append(group[0])
            continue

        retained = [doc for doc in group if is_retained_active(doc)]
        candidates = [doc for doc in group if doc not in retained]
        winner = max(candidates or group, key=lambda doc: doc.updated_at)
        chosen = {doc.id: doc for doc in retained}
        chosen[winner.id] = winner
        active.extend(chosen.values())
        skipped += len(group) - len(chosen)
    return active, skipped


async def list_current_pmp_corpus_documents(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    max_documents: int | None = None,
) -> CorpusListingResult:
    """Return current active project evidence documents for PMP sweeps."""
    result = await session.execute(
        select(SourceDocument)
        .where(
            SourceDocument.project_id == project_id,
            SourceDocument.source_type == "project_evidence",
        )
        .order_by(SourceDocument.relative_path.asc())
    )
    indexed = list(result.scalars().all())
    active_candidates = [doc for doc in indexed if is_active_pmp_corpus_document(doc)]
    skipped_superseded = len(indexed) - len(active_candidates)
    active_candidates, skipped_revision_duplicate = _dedupe_revision_groups(active_candidates)
    active_candidates.sort(key=lambda doc: doc.relative_path)

    capped = False
    if max_documents is not None and len(active_candidates) > max_documents:
        active_candidates = active_candidates[:max_documents]
        capped = True

    return CorpusListingResult(
        documents=tuple(active_candidates),
        total_indexed=len(indexed),
        skipped_superseded=skipped_superseded,
        skipped_revision_duplicate=skipped_revision_duplicate,
        capped=capped,
    )
