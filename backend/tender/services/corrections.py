from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import TaxonomySynonym, TenderCorrection, TenderLineItem, TenderMapping
from tender.seeds.load import normalize_phrase


async def record_mapping_correction(
    session: AsyncSession,
    *,
    mapping_id: uuid.UUID,
    corrected_cell_code: str,
    reviewer_id: uuid.UUID,
    reason: str | None,
) -> None:
    mapping = await session.get(TenderMapping, mapping_id)
    if mapping is None:
        raise ValueError(f"unknown tender mapping: {mapping_id}")
    line_item = await session.get(TenderLineItem, mapping.line_item_id)
    if line_item is None:
        raise ValueError(f"mapping has no line item: {mapping.line_item_id}")

    before = {
        "cell_code": mapping.cell_code,
        "tier": mapping.tier,
        "qa_state": mapping.qa_state,
    }
    after = {
        "cell_code": corrected_cell_code,
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

    phrase_norm = normalize_phrase(line_item.description_raw)
    existing = await session.execute(
        select(TaxonomySynonym).where(
            TaxonomySynonym.cell_code == corrected_cell_code,
            TaxonomySynonym.phrase_norm == phrase_norm,
        )
    )
    if existing.scalars().first() is None:
        session.add(
            TaxonomySynonym(
                cell_code=corrected_cell_code,
                phrase=line_item.description_raw,
                phrase_norm=phrase_norm,
                source="correction",
                confidence=1.0,
                correction_id=correction.id,
            )
        )
    await session.flush()
