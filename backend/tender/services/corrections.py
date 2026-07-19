from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import (
    TaxonomySynonym,
    TenderCorrection,
    TenderLineItem,
    TenderMapping,
    TenderProjectTrade,
)
from tender.seeds.load import normalize_phrase


async def record_mapping_correction(
    session: AsyncSession,
    *,
    mapping_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    reason: str | None,
    corrected_cell_code: str | None = None,
    corrected_project_trade_id: uuid.UUID | None = None,
) -> None:
    if corrected_project_trade_id is None and not corrected_cell_code:
        raise ValueError("mapping correction requires project_trade_id or cell_code")

    mapping = await session.get(TenderMapping, mapping_id)
    if mapping is None:
        raise ValueError(f"unknown tender mapping: {mapping_id}")
    line_item = await session.get(TenderLineItem, mapping.line_item_id)
    if line_item is None:
        raise ValueError(f"mapping has no line item: {mapping.line_item_id}")

    # Prefer project_trade_id when both targets are supplied.
    if corrected_project_trade_id is not None:
        await _record_trade_correction(
            session,
            mapping=mapping,
            line_item=line_item,
            corrected_project_trade_id=corrected_project_trade_id,
            reviewer_id=reviewer_id,
            reason=reason,
        )
        return

    await _record_cell_correction(
        session,
        mapping=mapping,
        line_item=line_item,
        corrected_cell_code=corrected_cell_code,
        reviewer_id=reviewer_id,
        reason=reason,
    )


async def _record_trade_correction(
    session: AsyncSession,
    *,
    mapping: TenderMapping,
    line_item: TenderLineItem,
    corrected_project_trade_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    reason: str | None,
) -> None:
    trade = await session.get(TenderProjectTrade, corrected_project_trade_id)
    if trade is None:
        raise ValueError(f"unknown project trade: {corrected_project_trade_id}")

    before = {
        "cell_code": mapping.cell_code,
        "project_trade_id": (
            str(mapping.project_trade_id) if mapping.project_trade_id is not None else None
        ),
        "tier": mapping.tier,
        "qa_state": mapping.qa_state,
    }
    after = {
        "cell_code": None,
        "project_trade_id": str(corrected_project_trade_id),
        "tier": "human",
        "qa_state": "corrected",
    }
    correction = TenderCorrection(
        entity_type="tender_mapping",
        entity_id=mapping.id,
        field="project_trade_id",
        before=before,
        after=after,
        reviewer=reviewer_id,
        reason=reason,
    )
    session.add(correction)
    await session.flush()

    mapping.project_trade_id = corrected_project_trade_id
    mapping.cell_code = None
    mapping.tier = "human"
    mapping.qa_state = "corrected"
    mapping.confidence = 1.0
    mapping.reviewed_by = reviewer_id
    mapping.reviewed_at = datetime.now(timezone.utc)

    anchors = list(trade.anchor_cell_codes or [])
    if len(anchors) == 1:
        await _upsert_synonym(
            session,
            cell_code=anchors[0],
            phrase=line_item.description_raw,
            correction_id=correction.id,
        )
    await session.flush()


async def _record_cell_correction(
    session: AsyncSession,
    *,
    mapping: TenderMapping,
    line_item: TenderLineItem,
    corrected_cell_code: str,
    reviewer_id: uuid.UUID,
    reason: str | None,
) -> None:
    before = {
        "cell_code": mapping.cell_code,
        "project_trade_id": (
            str(mapping.project_trade_id) if mapping.project_trade_id is not None else None
        ),
        "tier": mapping.tier,
        "qa_state": mapping.qa_state,
    }
    after = {
        "cell_code": corrected_cell_code,
        "project_trade_id": (
            str(mapping.project_trade_id) if mapping.project_trade_id is not None else None
        ),
        "tier": "human",
        "qa_state": "corrected",
    }
    correction = TenderCorrection(
        entity_type="tender_mapping",
        entity_id=mapping.id,
        field="cell_code",
        before=before,
        after=after,
        reviewer=reviewer_id,
        reason=reason,
    )
    session.add(correction)
    await session.flush()

    mapping.cell_code = corrected_cell_code
    mapping.tier = "human"
    mapping.qa_state = "corrected"
    mapping.confidence = 1.0
    mapping.reviewed_by = reviewer_id
    mapping.reviewed_at = datetime.now(timezone.utc)

    await _upsert_synonym(
        session,
        cell_code=corrected_cell_code,
        phrase=line_item.description_raw,
        correction_id=correction.id,
    )
    await session.flush()


async def _upsert_synonym(
    session: AsyncSession,
    *,
    cell_code: str,
    phrase: str,
    correction_id: uuid.UUID,
) -> None:
    phrase_norm = normalize_phrase(phrase)
    existing = await session.execute(
        select(TaxonomySynonym).where(
            TaxonomySynonym.cell_code == cell_code,
            TaxonomySynonym.phrase_norm == phrase_norm,
        )
    )
    if existing.scalars().first() is None:
        session.add(
            TaxonomySynonym(
                cell_code=cell_code,
                phrase=phrase,
                phrase_norm=phrase_norm,
                source="correction",
                confidence=1.0,
                correction_id=correction_id,
            )
        )
