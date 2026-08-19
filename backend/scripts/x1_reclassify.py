"""X1 reclassify: run the Stage 4 classifier over historical unknown rows.

Idempotent. Dry-run unless --apply. Never touches basis=user (D4).
"""
from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

import app.database.models  # noqa: F401 — register ORM mappers
from app.database.source_document import SourceDocument
from ingest.classify import classify_entry
from ingest.db import get_sync_session_factory
from ingest.router import has_useful_text
from ingest.types import ManifestEntry

SessionFactory = Callable[[], Session]

CANDIDATES_SQL = text(
    """
    SELECT sd.id
    FROM source_documents sd
    WHERE sd.document_class = 'unknown'
      AND (
        sd.document_metadata->>'basis' IS NULL
        OR sd.document_metadata->>'basis' = 'default'
      )
      AND sd.document_metadata->>'machine_class' IS NULL
    ORDER BY sd.created_at
    """
)

CAPTURE_LOG_DDL = text(
    """
    CREATE TABLE IF NOT EXISTS x1_reclassify_log (
        id uuid PRIMARY KEY,
        prior_class text,
        prior_basis text,
        captured_at timestamptz NOT NULL DEFAULT now()
    )
    """
)

CAPTURE_LOG_INSERT = text(
    """
    INSERT INTO x1_reclassify_log (id, prior_class, prior_basis, captured_at)
    SELECT sd.id, sd.document_class, sd.document_metadata->>'basis', now()
    FROM source_documents sd
    WHERE sd.document_class = 'unknown'
      AND (
        sd.document_metadata->>'basis' IS NULL
        OR sd.document_metadata->>'basis' = 'default'
      )
      AND sd.document_metadata->>'machine_class' IS NULL
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


def class_counts(session: Session) -> Counter[str]:
    rows = session.execute(
        text(
            "SELECT document_class, count(*) FROM source_documents GROUP BY 1"
        )
    ).all()
    return Counter({str(document_class): int(count) for document_class, count in rows})


def _entry_for(doc: SourceDocument) -> ManifestEntry:
    filename = doc.filename or "document.txt"
    relative_path = doc.relative_path or filename
    return ManifestEntry(
        absolute_path=Path(relative_path),
        relative_path=relative_path,
        project=doc.project or "unknown",
        filename=filename,
        extension=Path(filename).suffix.lower(),
        size_bytes=0,
    )


def reclassify_document(doc: SourceDocument) -> bool:
    """Apply classify_entry to one unknown row. Returns True if the class changed."""
    metadata = dict(doc.document_metadata or {})
    if metadata.get("basis") == "user":
        return False
    classification = classify_entry(
        _entry_for(doc),
        extracted_text=doc.normalized_content or None,
    )
    existing_machine = {
        key: metadata[key]
        for key in (
            "machine_class",
            "machine_subject",
            "machine_confidence",
            "machine_basis",
        )
        if key in metadata
    }
    merged = {**metadata, **classification.document_metadata, **existing_machine}
    if classification.basis != "user":
        merged.setdefault("machine_class", classification.document_class)
        merged.setdefault("machine_subject", classification.document_subject)
        merged.setdefault("machine_confidence", f"{classification.confidence:.2f}")
        merged.setdefault("machine_basis", classification.basis)
    changed = doc.document_class != classification.document_class
    doc.document_class = classification.document_class
    doc.document_metadata = merged
    doc.ingest_mode = (
        "full_text" if has_useful_text(doc.normalized_content) else "register_only"
    )
    return changed


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
) -> int:
    factory = session_factory or _factory()
    with factory() as session:
        before = class_counts(session)
        candidates = load_candidates(session)
        total = len(candidates)
        print("class counts before:")
        for document_class, count in sorted(before.items()):
            print(f"  {document_class}: {count}")
        if not apply:
            session.rollback()
            print(f"would re-classify {total} documents")
            return total

        if total:
            _capture_rollback_log(session)
            session.commit()

        updated = 0
        for start in range(0, total, batch_size):
            batch: Sequence[SourceDocument] = candidates[start : start + batch_size]
            for doc in batch:
                reclassify_document(doc)
                updated += 1
            session.commit()
            print(f"progress: re-classified {updated}/{total} documents", flush=True)

        after = class_counts(session)
        print("class counts after:")
        for document_class, count in sorted(after.items()):
            print(f"  {document_class}: {count}")
        print(f"re-classified {updated} documents")
        return updated


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
