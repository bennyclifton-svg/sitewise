"""Per-quote matrix totals conserved against reconciliation ex-GST (I4).

Column totals come from ``tender_quote_reconciliations.computed_ex_gst_cents``.
Cell sums (including Unallocated 99.01 / PT.UNALLOC) explain that total; any
remainder is ``not_itemised_cents``. Money is never discarded by cell status.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import (
    TenderCellStatus,
    TenderProjectTrade,
    TenderQuote,
    TenderQuoteReconciliation,
    UNALLOCATED_TRADE_CODE,
)
from tender.schemas import MatrixQuoteTotal
from tender.services.mapping import UNALLOCATED_CELL_CODE

# Legacy export kept for report/analysis callers that still filter by status.
COUNTED_STATUSES = frozenset({"included", "pc", "ps", "mixed"})
UNALLOCATED_ROW_CODES = frozenset({UNALLOCATED_CELL_CODE, UNALLOCATED_TRADE_CODE})


@dataclass(frozen=True)
class QuoteTotalInput:
    quote_id: uuid.UUID
    stated_total_cents: int | None
    stated_total_source: str | None
    contract_type: str
    computed_ex_gst_cents: int | None
    residual_cents: int = 0
    recon_status: str | None = None


def delta_ratio(expected_cents: int, actual_cents: int) -> float:
    if expected_cents == 0:
        return 0.0 if actual_cents == 0 else 1.0
    return abs(actual_cents - expected_cents) / abs(expected_cents)


def compute_quote_totals(
    quotes: Sequence[QuoteTotalInput],
    cell_rows: Iterable[tuple[uuid.UUID, str, int | None]] = (),
) -> list[MatrixQuoteTotal]:
    """Build conserved ex-GST column totals.

    ``cell_rows`` is ``(quote_id, cell_code, amount_cents)`` — amounts are
    already ex-GST countable sums from the grid (I4).
    """
    cell_sums: dict[str, int] = defaultdict(int)
    unallocated: dict[str, int] = defaultdict(int)
    for quote_id, cell_code, amount_cents in cell_rows:
        if amount_cents is None:
            continue
        key = str(quote_id)
        cell_sums[key] += amount_cents
        if cell_code in UNALLOCATED_ROW_CODES:
            unallocated[key] += amount_cents

    totals: list[MatrixQuoteTotal] = []
    for quote in quotes:
        key = str(quote.quote_id)
        itemised = cell_sums.get(key, 0)
        unalloc = unallocated.get(key, 0)
        if quote.computed_ex_gst_cents is not None:
            computed = quote.computed_ex_gst_cents
        else:
            computed = itemised
        not_itemised = computed - itemised
        non_comparable = quote.contract_type == "cost_plus" or (
            quote.recon_status == "non_comparable"
        )
        reconciliation = _reconciliation_label(quote, computed)
        stated = quote.stated_total_cents
        delta = None if stated is None else computed - stated
        ratio = None if stated is None else delta_ratio(stated, computed)
        totals.append(
            MatrixQuoteTotal(
                quote_id=quote.quote_id,
                computed_total_cents=computed,
                basis="ex",
                residual_cents=quote.residual_cents,
                unallocated_cents=unalloc,
                not_itemised_cents=not_itemised,
                stated_native_cents=stated,
                stated_total_cents=stated,
                stated_total_source=(
                    quote.stated_total_source
                    if quote.stated_total_source in {"manual", "extracted"}
                    else None
                ),
                non_comparable=non_comparable,
                delta_cents=delta,
                delta_ratio=ratio,
                reconciliation=reconciliation,
            )
        )
    return totals


def _reconciliation_label(
    quote: QuoteTotalInput, computed: int
) -> str:
    if quote.recon_status == "not_stated" or quote.stated_total_cents is None:
        return "not_stated"
    if quote.recon_status == "reconciled" and quote.residual_cents == 0:
        return "match"
    if quote.recon_status == "residual" or quote.residual_cents != 0:
        return "mismatch"
    if quote.recon_status == "non_comparable":
        return "mismatch"
    # Fallback when recon row missing: compare computed to stated native
    # (legacy path; may mix bases — preferred path always has recon).
    if quote.stated_total_cents is None:
        return "not_stated"
    return "match" if computed == quote.stated_total_cents else "mismatch"


async def load_quote_totals(
    session: AsyncSession, comparison_id: uuid.UUID
) -> list[MatrixQuoteTotal]:
    quote_result = await session.execute(
        select(TenderQuote)
        .where(TenderQuote.comparison_id == comparison_id)
        .order_by(TenderQuote.created_at)
    )
    quotes = list(quote_result.scalars())
    recon_result = await session.execute(
        select(TenderQuoteReconciliation).where(
            TenderQuoteReconciliation.comparison_id == comparison_id
        )
    )
    recons = {row.quote_id: row for row in recon_result.scalars()}
    cell_result = await session.execute(
        select(
            TenderCellStatus.quote_id,
            TenderCellStatus.cell_code,
            TenderCellStatus.amount_cents,
            TenderProjectTrade.code.label("trade_code"),
        )
        .outerjoin(
            TenderProjectTrade,
            TenderProjectTrade.id == TenderCellStatus.project_trade_id,
        )
        .where(TenderCellStatus.comparison_id == comparison_id)
    )
    cell_rows = [
        (
            row.quote_id,
            row.cell_code
            if row.cell_code is not None
            else getattr(row, "trade_code", None),
            row.amount_cents,
        )
        for row in cell_result.all()
    ]
    inputs = [
        QuoteTotalInput(
            quote_id=quote.id,
            stated_total_cents=quote.stated_total_cents,
            stated_total_source=quote.stated_total_source,
            contract_type=quote.contract_type,
            computed_ex_gst_cents=(
                recons[quote.id].computed_ex_gst_cents
                if quote.id in recons
                else None
            ),
            residual_cents=recons[quote.id].residual_cents if quote.id in recons else 0,
            recon_status=recons[quote.id].status if quote.id in recons else None,
        )
        for quote in quotes
    ]
    return compute_quote_totals(inputs, cell_rows=cell_rows)
