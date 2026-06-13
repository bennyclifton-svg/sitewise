from __future__ import annotations

from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from tender.models import TaxonomyCell, TaxonomySynonym
from tender.schemas import TaxonomyCellView, TaxonomySearchResult
from tender.seeds.load import normalize_phrase


async def list_taxonomy(session: AsyncSession) -> list[TaxonomyCellView]:
    result = await session.execute(
        select(TaxonomyCell)
        .where(TaxonomyCell.active.is_(True))
        .order_by(TaxonomyCell.sort_order, TaxonomyCell.code)
    )
    return [_cell_view(cell) for cell in result.scalars()]


def taxonomy_search_statement(query: str):
    phrase_norm = normalize_phrase(query)
    similarity = func.similarity(TaxonomySynonym.phrase_norm, phrase_norm).label(
        "similarity"
    )
    return (
        select(
            TaxonomyCell.code,
            TaxonomyCell.name,
            TaxonomyCell.grp,
            TaxonomyCell.stage,
            TaxonomyCell.description,
            TaxonomySynonym.phrase,
            similarity,
        )
        .join(TaxonomySynonym, TaxonomySynonym.cell_code == TaxonomyCell.code)
        .where(
            TaxonomyCell.active.is_(True),
            similarity >= settings.tender_t0_trgm_threshold,
        )
        .order_by(desc(similarity), TaxonomyCell.sort_order, TaxonomyCell.code)
        .limit(10)
    )


async def search_taxonomy(
    session: AsyncSession,
    *,
    query: str,
) -> list[TaxonomySearchResult]:
    result = await session.execute(taxonomy_search_statement(query))
    by_code: dict[str, TaxonomySearchResult] = {}
    for row in result.all():
        code = str(_row_value(row, "code"))
        if code in by_code:
            continue
        by_code[code] = TaxonomySearchResult(
            code=code,
            name=str(_row_value(row, "name")),
            group=str(_row_value(row, "grp")),
            stage=str(_row_value(row, "stage")),
            description=_row_value(row, "description"),
            similarity=float(_row_value(row, "similarity")),
            via=str(_row_value(row, "phrase")),
        )
    return list(by_code.values())


def _cell_view(cell: TaxonomyCell) -> TaxonomyCellView:
    return TaxonomyCellView(
        code=cell.code,
        name=cell.name,
        group=cell.grp,
        stage=cell.stage,
        description=cell.description,
    )


def _row_value(row: Any, key: str) -> Any:
    if hasattr(row, key):
        return getattr(row, key)
    if hasattr(row, "_mapping"):
        return row._mapping[key]
    return row[key]
