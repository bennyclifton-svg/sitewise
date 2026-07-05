import uuid

import app.database.models  # noqa: F401 — register all ORM mappers
import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app.database.document_chunk import DocumentChunk
from app.database.source_document import SourceDocument
from ingest.chunkers.base import TextChunk
from ingest.db import get_sync_session_factory
from ingest.extractors.base import ExtractedDocument
from ingest.hashing import file_content_hash
from ingest.ids import chunk_id, document_id
from ingest.document_metadata import parse_document_metadata
from ingest.frontmatter import parse_frontmatter
from ingest.metadata import infer_document_type
from ingest.platform import sitewise_platform_metadata
from ingest.types import IngestPlan

logger = structlog.get_logger(__name__)

_PREVIEW_SNIPPET_MAX_CHARS = 4000


def _preview_snippet(extracted: ExtractedDocument) -> str | None:
    content = extracted.normalized_content.strip()
    if not content:
        return None

    if "## Title block" in content:
        snippet = content.split("## Title block", maxsplit=1)[1].strip()
        return snippet[:_PREVIEW_SNIPPET_MAX_CHARS] if snippet else None

    if extracted.pages:
        first_page = extracted.pages[0].text.strip()
        if first_page:
            return first_page[:_PREVIEW_SNIPPET_MAX_CHARS]

    return content[:_PREVIEW_SNIPPET_MAX_CHARS]


def _register_metadata(plan: IngestPlan, extracted: ExtractedDocument) -> dict[str, str]:
    try:
        preview_snippet = (
            None
            if plan.classification.document_class == "specification"
            else _preview_snippet(extracted)
        )
        parsed = parse_document_metadata(
            file_name=plan.entry.filename,
            filed_path=plan.entry.relative_path,
            preview_snippet=preview_snippet,
            source_path=plan.entry.relative_path,
        )
    except Exception:
        logger.exception(
            "document_metadata_parse_failed",
            relative_path=plan.entry.relative_path,
        )
        return {}

    fields: dict[str, str] = {
        "document_number": parsed.document_number,
        "title": parsed.title,
        "revision": parsed.revision,
        "discipline": parsed.discipline,
        "canonical_file_name": parsed.canonical_file_name,
        "metadata_confidence": parsed.confidence,
    }
    if parsed.document_number:
        fields["drawing_number"] = parsed.document_number
    return fields


def _merged_metadata(plan: IngestPlan, extracted: ExtractedDocument) -> dict:
    metadata = dict(plan.classification.document_metadata)
    platform_metadata = sitewise_platform_metadata(plan.entry.relative_path)
    metadata.update(platform_metadata)
    if platform_metadata and plan.entry.filename.lower().endswith(".md"):
        frontmatter = parse_frontmatter(extracted.normalized_content)
        if frontmatter:
            metadata["frontmatter"] = frontmatter
    metadata.update(_register_metadata(plan, extracted))
    metadata["filename"] = plan.entry.filename
    return metadata


def should_skip_unchanged(session, plan: IngestPlan, content_hash: str) -> bool:
    existing = session.scalar(
        select(SourceDocument.content_hash).where(
            SourceDocument.relative_path == plan.entry.relative_path
        )
    )
    return existing == content_hash


def upsert_document(
    session,
    plan: IngestPlan,
    extracted: ExtractedDocument,
    content_hash: str,
) -> uuid.UUID:
    doc_id = document_id(plan.entry.relative_path)
    document_type = infer_document_type(
        plan.entry.filename,
        plan.classification.document_class,
    )
    values = {
        "id": doc_id,
        "project": plan.context.project,
        "phase": plan.context.phase,
        "document_type": document_type,
        "document_class": plan.classification.document_class,
        "ingest_mode": plan.classification.ingest_mode,
        "document_metadata": _merged_metadata(plan, extracted),
        "content_hash": content_hash,
        "source_type": plan.context.source_type,
        "filename": plan.entry.filename,
        "relative_path": plan.entry.relative_path,
        "normalized_content": extracted.normalized_content,
    }
    stmt = (
        insert(SourceDocument)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["relative_path"],
            set_={
                "project": values["project"],
                "phase": values["phase"],
                "document_type": values["document_type"],
                "document_class": values["document_class"],
                "ingest_mode": values["ingest_mode"],
                "document_metadata": values["document_metadata"],
                "content_hash": values["content_hash"],
                "source_type": values["source_type"],
                "filename": values["filename"],
                "normalized_content": values["normalized_content"],
                "updated_at": func.now(),
            },
        )
    )
    session.execute(stmt)
    return doc_id


def delete_document_chunks(session, doc_id: uuid.UUID) -> None:
    session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc_id))


def upsert_chunks(
    session,
    plan: IngestPlan,
    doc_id: uuid.UUID,
    chunks: list[TextChunk],
    embeddings: list[list[float]],
) -> None:
    if len(chunks) != len(embeddings):
        msg = f"Chunk/embedding mismatch: {len(chunks)} vs {len(embeddings)}"
        raise ValueError(msg)

    for chunk, embedding in zip(chunks, embeddings, strict=True):
        values = {
            "id": chunk_id(plan.entry.relative_path, chunk.chunk_index),
            "document_id": doc_id,
            "chunk_index": chunk.chunk_index,
            "page_or_section": chunk.page_or_section,
            "content": chunk.content,
            "embedding": embedding,
            "token_count": chunk.token_count,
            "chunk_metadata": chunk.chunk_metadata,
        }
        stmt = (
            insert(DocumentChunk)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["document_id", "chunk_index"],
                set_={
                    "page_or_section": values["page_or_section"],
                    "content": values["content"],
                    "embedding": values["embedding"],
                    "token_count": values["token_count"],
                    "chunk_metadata": values["chunk_metadata"],
                },
            )
        )
        session.execute(stmt)

    session.execute(
        delete(DocumentChunk).where(
            DocumentChunk.document_id == doc_id,
            DocumentChunk.chunk_index >= len(chunks),
        )
    )


def persist_ingest(
    plan: IngestPlan,
    extracted: ExtractedDocument,
    chunks: list[TextChunk],
    embeddings: list[list[float]],
    *,
    skip_if_unchanged: bool = True,
) -> bool:
    content_hash = file_content_hash(plan.entry.absolute_path)
    factory = get_sync_session_factory()

    with factory() as session:
        if skip_if_unchanged and should_skip_unchanged(session, plan, content_hash):
            logger.info("ingest_skipped_unchanged", relative_path=plan.entry.relative_path)
            return False

        doc_id = upsert_document(session, plan, extracted, content_hash)
        if chunks:
            upsert_chunks(session, plan, doc_id, chunks, embeddings)
        else:
            delete_document_chunks(session, doc_id)
        session.commit()

    logger.info(
        "ingest_persisted",
        relative_path=plan.entry.relative_path,
        chunks=len(chunks),
    )
    return True
