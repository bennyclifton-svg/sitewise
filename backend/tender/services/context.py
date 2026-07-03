"""Shared context loaders for tender services."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tender.models import TenderComparison, TenderQuote
from tender.schemas import ProjectContext


async def context_for_quote(
    session: AsyncSession, quote_id: uuid.UUID
) -> ProjectContext:
    result = await session.execute(
        select(TenderComparison.context)
        .join(TenderQuote, TenderQuote.comparison_id == TenderComparison.id)
        .where(TenderQuote.id == quote_id)
    )
    return ProjectContext.model_validate(result.scalar_one())
