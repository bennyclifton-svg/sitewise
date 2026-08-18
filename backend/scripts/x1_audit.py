"""X1 read-only audit. Writes nothing. Run before any backfill."""
from __future__ import annotations

import asyncio
import json

from sqlalchemy import func, select, text

import app.database.models  # noqa: F401 — register ORM mappers (DocumentChunk)
from app.database.session import get_session_factory
from app.database.source_document import SourceDocument


def _pairs(rows: list[tuple[object, object]]) -> dict[str, int]:
    return {str(key): int(value) for key, value in rows}


def _count(value: object) -> int:
    return int(value or 0)


async def audit() -> dict[str, object]:
    factory = get_session_factory()
    async with factory() as session:
        report: dict[str, object] = {}

        report["total"] = _count(
            (await session.execute(select(func.count()).select_from(SourceDocument))).scalar_one()
        )

        report["by_class"] = _pairs(
            (await session.execute(
                select(SourceDocument.document_class, func.count()).group_by(
                    SourceDocument.document_class
                )
            )).all()
        )

        report["by_ingest_mode"] = _pairs(
            (await session.execute(
                select(SourceDocument.ingest_mode, func.count()).group_by(
                    SourceDocument.ingest_mode
                )
            )).all()
        )

        # The headline number: suppressed but carries useful text.
        report["suppressed_with_text"] = _count(
            (
                await session.execute(
                    text(
                        """
                SELECT count(*) FROM source_documents
                WHERE ingest_mode = 'register_only'
                  AND length(btrim(normalized_content)) >= 200
            """
                    )
                )
            ).scalar_one()
        )

        # Same wound, other side: has text, has no chunks.
        report["text_without_chunks"] = _count(
            (
                await session.execute(
                    text(
                        """
                SELECT count(*) FROM source_documents sd
                WHERE length(btrim(sd.normalized_content)) >= 200
                  AND NOT EXISTS (
                    SELECT 1 FROM document_chunks c WHERE c.document_id = sd.id
                  )
            """
                    )
                )
            ).scalar_one()
        )

        report["legacy_procurement_classes"] = _count(
            (
                await session.execute(
                    text(
                        """
                SELECT count(*) FROM source_documents
                WHERE document_class IN
                  ('tep','eoi','rft','addendum','tender_submission','evaluation','trr')
            """
                    )
                )
            ).scalar_one()
        )

        report["planning_instrument"] = _count(
            (
                await session.execute(
                    text(
                        "SELECT count(*) FROM source_documents WHERE document_class='planning_instrument'"
                    )
                )
            ).scalar_one()
        )

        report["undeclared_classes"] = _pairs(
            (
                await session.execute(
                    text(
                        """
                SELECT document_class, count(*) FROM source_documents
                WHERE document_class IN ('inbox_pending','corpus_catalog')
                GROUP BY 1
            """
                    )
                )
            ).all()
        )

        report["null_content_hash"] = _count(
            (
                await session.execute(
                    text("SELECT count(*) FROM source_documents WHERE content_hash IS NULL")
                )
            ).scalar_one()
        )

        return report


if __name__ == "__main__":
    print(json.dumps(asyncio.run(audit()), indent=2, default=str))
