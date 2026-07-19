"""Per-quote matrix totals reconciled against the quote's stated total.

Single source of the column-total computation: consumed by the matrix API
and the report renderer so the on-screen grid and the frozen PDF can never
disagree.

Counting rule: a cell contributes its ``amount_cents`` when its status is
included/pc/ps — ``_allocated_amount`` already folds pc/ps allowances into
the cell amount, and printed quote totals include allowances. Excluded,
not-required, silent-ambiguous, and bundled cells contribute nothing (a
bundled cell's money is carried by the cell it was bundled into). This
intentionally differs from extract-time reconciliation, which sums raw line
items; the matrix total is the user-facing figure.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence

from app.config import settings
from tender.schemas import MatrixQuoteTotal

COUNTED_STATUSES = frozenset({"included", "pc", "ps"})


def delta_ratio(expected_cents: int, actual_cents: int) -> float:
    if expected_cents == 0:
        return 0.0 if actual_cents == 0 else 1.0
    return abs(actual_cents - expected_cents) / abs(expected_cents)


def compute_quote_totals(
    cell_rows: Iterable[tuple[uuid.UUID | str, str, int | None]],
    quotes: Sequence[tuple[uuid.UUID, int | None, str | None]],
    *,
    tolerance: float | None = None,
) -> list[MatrixQuoteTotal]:
    """Sum matrix cells per quote and reconcile against the stated total.

    ``cell_rows`` is ``(quote_id, status, amount_cents)`` per matrix cell;
    ``quotes`` is ``(quote_id, stated_total_cents, stated_total_source)`` in
    display order. Quotes with no cells still get a (zero) total.
    """
    tol = (
        settings.tender_reconciliation_tolerance if tolerance is None else tolerance
    )
    sums: dict[str, int] = defaultdict(int)
    for quote_id, status, amount_cents in cell_rows:
        if status in COUNTED_STATUSES and amount_cents is not None:
            sums[str(quote_id)] += amount_cents

    totals: list[MatrixQuoteTotal] = []
    for quote_id, stated_total_cents, stated_total_source in quotes:
        computed = sums.get(str(quote_id), 0)
        if stated_total_cents is None:
            totals.append(
                MatrixQuoteTotal(
                    quote_id=quote_id,
                    computed_total_cents=computed,
                    reconciliation="not_stated",
                )
            )
            continue
        ratio = delta_ratio(stated_total_cents, computed)
        totals.append(
            MatrixQuoteTotal(
                quote_id=quote_id,
                computed_total_cents=computed,
                stated_total_cents=stated_total_cents,
                stated_total_source=stated_total_source,
                delta_cents=computed - stated_total_cents,
                delta_ratio=ratio,
                reconciliation="match" if ratio <= tol else "mismatch",
            )
        )
    return totals
