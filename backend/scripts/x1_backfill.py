"""X1 backfill: re-index documents whose text was suppressed by the pre-Stage-1 bug.

Idempotent. Dry-run unless --apply.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

import app.database.models  # noqa: F401 — register ORM mappers
from app.database.source_document import SourceDocument
from ingest.chunk import chunk_document
from ingest.classify import canonicalize_document_class
from ingest.db import get_sync_session_factory
from ingest.embed import embed_texts
from ingest.extractors.base import ExtractedDocument
from ingest.persist import delete_document_chunks, upsert_chunks
from ingest.router import _chunker_for, has_useful_text
from ingest.types import Classification, IngestPlan, ManifestEntry, ProjectContext, SourceType

EmbedFn = Callable[[list[str]], list[list[float]]]
SessionFactory = Callable[[], Session]

CANDIDATES_SQL = text(
    """
    SELECT sd.id
    FROM source_documents sd
    WHERE length(btrim(sd.normalized_content)) >= 200
      AND NOT EXISTS (
        SELECT 1 FROM document_chunks c WHERE c.document_id = sd.id
      )
    ORDER BY sd.created_at
    """
)

REPAIR_MODE_SQL = text(
    """
    UPDATE source_documents
    SET ingest_mode = 'full_text'
    WHERE ingest_mode IS DISTINCT FROM 'full_text'
      AND length(btrim(normalized_content)) >= 200
      AND EXISTS (
        SELECT 1 FROM document_chunks c WHERE c.document_id = source_documents.id
      )
    """
)

CAPTURE_LOG_DDL = text(
    """
    CREATE TABLE IF NOT EXISTS x1_backfill_log (
        id uuid PRIMARY KEY,
        prior_ingest_mode text,
        captured_at timestamptz NOT NULL DEFAULT now()
    )
    """
)

CAPTURE_LOG_INSERT = text(
    """
    INSERT INTO x1_backfill_log (id, prior_ingest_mode, captured_at)
    SELECT sd.id, sd.ingest_mode, now()
    FROM source_documents sd
    WHERE length(btrim(sd.normalized_content)) >= 200
      AND NOT EXISTS (
        SELECT 1 FROM document_chunks c WHERE c.document_id = sd.id
      )
    ON CONFLICT (id) DO NOTHING
    """
)


def load_candidates(session: Session, *, limit: int | None = None) -> list[SourceDocument]:
    ids = list(session.execute(CANDIDATES_SQL).scalars())
    if limit is not None:
        ids = ids[:limit]
    if not ids:
        return []
    docs = {
        doc.id: doc
        for doc in session.execute(
            select(SourceDocument).where(SourceDocument.id.in_(ids))
        ).scalars()
    }
    return [docs[doc_id] for doc_id in ids if doc_id in docs]


def _plan_for(doc: SourceDocument) -> IngestPlan:
    document_class, metadata = canonicalize_document_class(
        doc.document_class or "unknown", {}
    )
    classification = Classification(
        document_class=document_class,
        ingest_mode="full_text",
        document_metadata=metadata,
        document_subject="none",
        confidence=0.5 if document_class != "unknown" else 0.0,
        basis="default",
    )
    filename = doc.filename or "document.txt"
    relative_path = doc.relative_path or filename
    source_type = cast(SourceType, doc.source_type or "project_evidence")
    entry = ManifestEntry(
        absolute_path=Path(relative_path),
        relative_path=relative_path,
        project=doc.project or "unknown",
        filename=filename,
        extension=Path(filename).suffix.lower(),
        size_bytes=0,
    )
    context = ProjectContext(
        project=doc.project or "unknown",
        phase=doc.phase or "delivery",
        source_type=source_type,
        project_id=doc.project_id,
    )
    return IngestPlan(
        entry=entry,
        context=context,
        classification=classification,
        extractor="unused",
        chunker=_chunker_for(classification),
    )


def reindex_document(session: Session, doc: SourceDocument, *, embed_fn: EmbedFn) -> int:
    if not has_useful_text(doc.normalized_content):
        msg = f"candidate {doc.id} failed has_useful_text"
        raise AssertionError(msg)

    extracted = ExtractedDocument(normalized_content=doc.normalized_content)
    plan = _plan_for(doc)
    chunks = chunk_document(extracted, plan)
    if not chunks:
        return 0

    embeddings = embed_fn([chunk.content for chunk in chunks])
    delete_document_chunks(session, doc.id)
    upsert_chunks(session, plan, doc.id, chunks, embeddings)
    doc.ingest_mode = "full_text"
    return len(chunks)


def _capture_rollback_log(session: Session) -> None:
    session.execute(CAPTURE_LOG_DDL)
    session.execute(CAPTURE_LOG_INSERT)


def _factory() -> sessionmaker[Session]:
    return get_sync_session_factory()


def run(
    *,
    apply: bool,
    batch_size: int = 100,
    session_factory: SessionFactory | sessionmaker[Session] | None = None,
    embed_fn: EmbedFn | None = None,
    capture_rollback_log: bool = True,
) -> int:
    factory = session_factory or _factory()
    embed = embed_fn or embed_texts

    with factory() as session:
        candidates = load_candidates(session)
        total = len(candidates)
        if not apply:
            session.rollback()
            print(f"would re-index {total} documents")
            return total

        if capture_rollback_log:
            _capture_rollback_log(session)
            session.commit()

        reindexed = 0
        for start in range(0, total, batch_size):
            batch: Sequence[SourceDocument] = candidates[start : start + batch_size]
            for doc in batch:
                if not has_useful_text(doc.normalized_content):
                    continue
                n_chunks = reindex_document(session, doc, embed_fn=embed)
                if n_chunks == 0:
                    print(
                        f"skip (no chunks): {doc.id} {getattr(doc, 'filename', '')}",
                        flush=True,
                    )
                    continue
                reindexed += 1
            session.commit()
            print(
                f"progress: re-indexed {reindexed}/{total} documents",
                flush=True,
            )

        if capture_rollback_log:
            session.execute(REPAIR_MODE_SQL)
            session.commit()

        print(f"re-indexed {reindexed} documents")
        return reindexed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually write (default: dry-run)",
    )
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    run(apply=args.apply, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
