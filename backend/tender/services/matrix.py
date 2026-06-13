from __future__ import annotations

import uuid
from collections import OrderedDict, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import TaxonomyCell, TenderCellStatus, TenderFlag
from tender.schemas import MatrixCell, MatrixGroup, MatrixQuoteCell, MatrixResponse


async def build_matrix(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
) -> MatrixResponse:
    status_result = await session.execute(
        select(
            TenderCellStatus.quote_id,
            TenderCellStatus.cell_code,
            TenderCellStatus.status,
            TenderCellStatus.amount_cents,
            TaxonomyCell.name.label("cell_name"),
            TaxonomyCell.grp.label("group_name"),
            TaxonomyCell.sort_order,
        )
        .join(TaxonomyCell, TaxonomyCell.code == TenderCellStatus.cell_code)
        .where(TenderCellStatus.comparison_id == comparison_id)
        .order_by(TaxonomyCell.sort_order, TenderCellStatus.cell_code)
    )
    flag_result = await session.execute(
        select(TenderFlag.quote_id, TenderFlag.cell_code, TenderFlag.headline).where(
            TenderFlag.comparison_id == comparison_id,
            TenderFlag.include_in_report.is_(True),
            TenderFlag.cell_code.is_not(None),
            TenderFlag.quote_id.is_not(None),
        )
    )
    flags_by_cell: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in flag_result.all():
        flags_by_cell[(str(row.quote_id), row.cell_code)].append(row.headline)

    groups: "OrderedDict[str, OrderedDict[str, MatrixCell]]" = OrderedDict()
    for row in status_result.all():
        group_cells = groups.setdefault(row.group_name, OrderedDict())
        cell = group_cells.setdefault(
            row.cell_code,
            MatrixCell(code=row.cell_code, name=row.cell_name, quotes={}),
        )
        quote_id = str(row.quote_id)
        cell.quotes[quote_id] = MatrixQuoteCell(
            status=row.status,
            amount_cents=row.amount_cents,
            flags=flags_by_cell.get((quote_id, row.cell_code), []),
        )

    return MatrixResponse(
        comparison_id=comparison_id,
        groups=[
            MatrixGroup(name=group_name, cells=list(cells.values()))
            for group_name, cells in groups.items()
        ],
    )


def _row_value(row: Any, key: str) -> Any:
    if hasattr(row, key):
        return getattr(row, key)
    if hasattr(row, "_mapping"):
        return row._mapping[key]
    return row[key]
