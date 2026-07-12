from __future__ import annotations

import uuid
from collections import OrderedDict, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import TaxonomyCell, TenderCellStatus, TenderFlag, TenderLineItem, TenderMapping, TenderQuote
from tender.schemas import (
    MatrixCell,
    MatrixGroup,
    MatrixMappingCandidate,
    MatrixMappingChoice,
    MatrixQuoteCell,
    MatrixResponse,
)
from tender.services.mapping import has_multi_candidate_adjudication


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

    mapping_result = await session.execute(
        select(
            TenderMapping.id.label("mapping_id"),
            TenderQuote.id.label("quote_id"),
            TenderMapping.cell_code.label("selected_cell_code"),
            TenderMapping.qa_state,
            TenderMapping.adjudication,
        )
        .join(TenderLineItem, TenderLineItem.id == TenderMapping.line_item_id)
        .join(TenderQuote, TenderQuote.id == TenderLineItem.quote_id)
        .where(TenderQuote.comparison_id == comparison_id)
    )
    cells_by_code: dict[str, MatrixCell] = {
        cell.code: cell for group_cells in groups.values() for cell in group_cells.values()
    }
    for row in mapping_result.all():
        if not has_multi_candidate_adjudication(row.adjudication):
            continue
        cell = cells_by_code.get(row.selected_cell_code)
        if cell is None:
            continue
        quote_id = str(row.quote_id)
        quote_cell = cell.quotes.get(quote_id)
        if quote_cell is None:
            continue
        quote_cell.mapping_choices.append(
            _mapping_choice_from_adjudication(
                mapping_id=row.mapping_id,
                selected_cell_code=row.selected_cell_code,
                qa_state=row.qa_state,
                adjudication=row.adjudication,
            )
        )

    return MatrixResponse(
        comparison_id=comparison_id,
        groups=[
            MatrixGroup(name=group_name, cells=list(cells.values()))
            for group_name, cells in groups.items()
        ],
    )


def _mapping_choice_from_adjudication(
    *,
    mapping_id: uuid.UUID,
    selected_cell_code: str,
    qa_state: str,
    adjudication: dict[str, Any],
) -> MatrixMappingChoice:
    return MatrixMappingChoice(
        mapping_id=mapping_id,
        selected_cell_code=selected_cell_code,
        locked=qa_state == "corrected",
        candidates=[
            MatrixMappingCandidate(
                cell_code=str(candidate["cell_code"]),
                name=candidate.get("name") if isinstance(candidate.get("name"), str) else None,
                similarity=float(candidate["similarity"])
                if isinstance(candidate.get("similarity"), int | float)
                else None,
                via=candidate.get("via") if isinstance(candidate.get("via"), str) else None,
            )
            for candidate in adjudication.get("candidates", [])
            if isinstance(candidate, dict) and isinstance(candidate.get("cell_code"), str)
        ],
    )


def _row_value(row: Any, key: str) -> Any:
    if hasattr(row, key):
        return getattr(row, key)
    if hasattr(row, "_mapping"):
        return row._mapping[key]
    return row[key]
