"""Quote ledger assembly — every printed figure summing to the stated total (I2)."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import (
    TaxonomyCell,
    TenderLineItem,
    TenderMapping,
    TenderProjectTrade,
    TenderQuote,
    TenderQuoteReconciliation,
)
from tender.schemas import CellItemsResponse, CellLineItem, LedgerItem, QuoteLedgerResponse


async def build_quote_ledger(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    quote_id: uuid.UUID,
) -> QuoteLedgerResponse:
    quote = await session.get(TenderQuote, quote_id)
    if quote is None or quote.comparison_id != comparison_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Quote not found")

    recon = await session.scalar(
        select(TenderQuoteReconciliation).where(
            TenderQuoteReconciliation.quote_id == quote_id,
            TenderQuoteReconciliation.comparison_id == comparison_id,
        )
    )

    rows = (
        await session.scalars(
            select(TenderLineItem)
            .where(TenderLineItem.quote_id == quote_id)
            .order_by(TenderLineItem.page_no, TenderLineItem.figure_key)
        )
    ).all()

    by_id: dict[uuid.UUID, LedgerItem] = {}
    for row in rows:
        by_id[row.id] = LedgerItem(
            id=row.id,
            figure_key=row.figure_key or str(row.id),
            page_no=row.page_no,
            description_raw=row.description_raw,
            printed_text=None,
            amount_cents=row.amount_cents,
            amount_ex_gst_cents=row.amount_ex_gst_cents,
            gst_basis=row.gst_basis,
            role=row.role,
            is_rollup=bool(row.is_rollup),
            counted_in_total=bool(row.counted_in_total),
            duplicate_of_id=row.duplicate_of_id,
            parent_id=row.parent_id,
            children=[],
        )

    roots: list[LedgerItem] = []
    for row in rows:
        item = by_id[row.id]
        if row.parent_id and row.parent_id in by_id:
            by_id[row.parent_id].children.append(item)
        else:
            roots.append(item)

    residual = int(recon.residual_cents) if recon is not None else 0
    if residual != 0:
        roots.append(
            LedgerItem(
                figure_key="residual",
                description_raw="Unexplained difference vs stated total",
                amount_cents=residual,
                counted_in_total=True,
            )
        )

    return QuoteLedgerResponse(
        quote_id=quote.id,
        builder_name=quote.builder_name,
        stated_total_cents=quote.stated_total_cents
        if recon is None
        else recon.stated_total_cents,
        stated_basis=None if recon is None else recon.stated_basis,
        status="not_stated" if recon is None else recon.status,
        residual_cents=residual,
        computed_ex_gst_cents=None if recon is None else recon.computed_ex_gst_cents,
        uncaptured=list(recon.uncaptured) if recon is not None else [],
        items=roots,
    )


async def build_cell_items(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    cell_code: str,
    quote_id: uuid.UUID,
) -> CellItemsResponse:
    quote = await session.get(TenderQuote, quote_id)
    if quote is None or quote.comparison_id != comparison_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Quote not found")

    cell = await session.get(TaxonomyCell, cell_code)
    if cell is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Taxonomy cell not found")

    result = await session.execute(
        select(TenderMapping, TenderLineItem)
        .join(TenderLineItem, TenderLineItem.id == TenderMapping.line_item_id)
        .where(
            TenderLineItem.quote_id == quote_id,
            TenderMapping.cell_code == cell_code,
            TenderLineItem.duplicate_of_id.is_(None),
        )
        .order_by(TenderLineItem.page_no, TenderLineItem.figure_key)
    )

    items: list[CellLineItem] = []
    sum_ex_gst = 0
    for mapping, line_item in result.all():
        fraction = float(mapping.allocation_fraction)
        amount_ex = line_item.amount_ex_gst_cents
        if amount_ex is None:
            amount_ex = line_item.amount_cents
        if amount_ex is not None:
            sum_ex_gst += round(amount_ex * fraction)
        items.append(
            CellLineItem(
                line_item_id=line_item.id,
                description_raw=line_item.description_raw,
                page_no=line_item.page_no,
                role=line_item.role,
                allocation_fraction=fraction,
                amount_cents=line_item.amount_cents,
                amount_ex_gst_cents=line_item.amount_ex_gst_cents,
                mapping_tier=mapping.tier,
                qa_state=mapping.qa_state,
            )
        )

    return CellItemsResponse(
        cell_code=cell.code,
        name=cell.name,
        quote_id=quote_id,
        items=items,
        sum_ex_gst_cents=sum_ex_gst,
    )


async def build_trade_items(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    trade_id: uuid.UUID,
    quote_id: uuid.UUID,
) -> CellItemsResponse:
    quote = await session.get(TenderQuote, quote_id)
    if quote is None or quote.comparison_id != comparison_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Quote not found")

    trade = await session.get(TenderProjectTrade, trade_id)
    if trade is None or trade.comparison_id != comparison_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project trade not found")

    result = await session.execute(
        select(TenderMapping, TenderLineItem)
        .join(TenderLineItem, TenderLineItem.id == TenderMapping.line_item_id)
        .where(
            TenderLineItem.quote_id == quote_id,
            TenderMapping.project_trade_id == trade_id,
            TenderLineItem.duplicate_of_id.is_(None),
        )
        .order_by(TenderLineItem.page_no, TenderLineItem.figure_key)
    )

    items: list[CellLineItem] = []
    sum_ex_gst = 0
    for mapping, line_item in result.all():
        fraction = float(mapping.allocation_fraction)
        amount_ex = line_item.amount_ex_gst_cents
        if amount_ex is None:
            amount_ex = line_item.amount_cents
        if amount_ex is not None:
            sum_ex_gst += round(amount_ex * fraction)
        items.append(
            CellLineItem(
                line_item_id=line_item.id,
                description_raw=line_item.description_raw,
                page_no=line_item.page_no,
                role=line_item.role,
                allocation_fraction=fraction,
                amount_cents=line_item.amount_cents,
                amount_ex_gst_cents=line_item.amount_ex_gst_cents,
                mapping_tier=mapping.tier,
                qa_state=mapping.qa_state,
            )
        )

    return CellItemsResponse(
        cell_code=trade.code,
        name=trade.name,
        quote_id=quote_id,
        project_trade_id=trade.id,
        items=items,
        sum_ex_gst_cents=sum_ex_gst,
    )
