from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.project import Project


async def lock_project(
    session: AsyncSession, *, project_id: uuid.UUID
) -> Project | None:
    """Lock and refresh a project before writing rows that reference it."""
    result = await session.execute(
        select(Project)
        .where(Project.id == project_id)
        .with_for_update()
        .execution_options(autoflush=False, populate_existing=True)
    )
    return result.scalar_one_or_none()
