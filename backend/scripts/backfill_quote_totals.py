"""Backfill tender_quotes.stated_total_cents from cached extraction payloads.

Quotes created via the from-project-files flow carry no stated total; the
extraction pipeline now persists the printed quote total, but comparisons
processed before that change only hold it inside ``tender_extract_cache``
payloads. This script promotes those cached totals onto the quote with
``stated_total_source='extracted'``. Quotes whose documents were extracted
under an older extractor version have no matching cache row and are reported
as misses — re-running extraction is the fallback for those.

Dry-run by default; pass ``--apply`` to write.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from dataclasses import asdict, dataclass, field

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session_factory
from tender.models import (
    TenderComparison,
    TenderDocument,
    TenderExtractCache,
    TenderQuote,
)
from tender.schemas import ExtractionStructuredOutput
from tender.services.extract_cache import EXTRACTOR_VERSION


@dataclass
class BackfillSummary:
    quotes_missing_total: int = 0
    backfilled: int = 0
    no_cached_total: list[str] = field(default_factory=list)
    applied: bool = False


async def backfill_quote_totals(
    session: AsyncSession, *, apply: bool
) -> BackfillSummary:
    summary = BackfillSummary(applied=apply)
    result = await session.execute(
        select(TenderQuote, TenderComparison.project_id)
        .join(TenderComparison, TenderComparison.id == TenderQuote.comparison_id)
        .where(TenderQuote.stated_total_cents.is_(None))
        .order_by(TenderQuote.created_at)
    )
    rows = result.all()
    summary.quotes_missing_total = len(rows)
    for quote, project_id in rows:
        total = await _cached_total(session, quote_id=quote.id, project_id=project_id)
        if total is None:
            summary.no_cached_total.append(str(quote.id))
            continue
        summary.backfilled += 1
        if apply:
            quote.stated_total_cents = total
            quote.stated_total_source = "extracted"
    if apply:
        await session.commit()
    return summary


async def _cached_total(
    session: AsyncSession, *, quote_id: uuid.UUID, project_id: uuid.UUID
) -> int | None:
    result = await session.execute(
        select(TenderExtractCache.payload)
        .join(
            TenderDocument,
            TenderDocument.content_hash == TenderExtractCache.content_hash,
        )
        .where(
            TenderDocument.quote_id == quote_id,
            TenderExtractCache.project_id == project_id,
            TenderExtractCache.extractor_version == EXTRACTOR_VERSION,
        )
        .order_by(TenderDocument.created_at)
    )
    for (payload,) in result.all():
        try:
            structured = ExtractionStructuredOutput.model_validate(payload)
        except ValidationError:
            continue
        if structured.quote_total_cents is not None:
            return structured.quote_total_cents
    return None


async def _run(apply: bool) -> None:
    factory = get_session_factory()
    async with factory() as session:
        summary = await backfill_quote_totals(session, apply=apply)
        print(json.dumps(asdict(summary), indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="write changes (default: dry run)"
    )
    args = parser.parse_args()
    asyncio.run(_run(args.apply))


if __name__ == "__main__":
    main()
