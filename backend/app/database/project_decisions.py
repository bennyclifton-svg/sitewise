from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.project_decision import ProjectDecision
from app.sitewise.pmp_decisions import PmpDecision, extract_decisions


async def upsert_decision(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    decision_id: str,
    section: str,
    label: str,
    options: list[dict[str, Any]],
    selected: str,
    source: str,
    workflow_type: str = "create_pmp",
) -> ProjectDecision:
    stmt = (
        insert(ProjectDecision)
        .values(
            project_id=project_id,
            decision_id=decision_id,
            section=section,
            label=label,
            options=options,
            selected=selected,
            source=source,
            workflow_type=workflow_type,
        )
        .on_conflict_do_update(
            index_elements=["project_id", "decision_id"],
            set_={
                "section": section,
                "label": label,
                "options": options,
                "selected": selected,
                "source": source,
                "workflow_type": workflow_type,
            },
        )
        .returning(ProjectDecision)
    )
    result = await session.execute(stmt)
    row = result.scalar_one()
    await session.flush()
    await session.refresh(row)
    return row


async def list_decisions(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> list[ProjectDecision]:
    result = await session.execute(
        select(ProjectDecision)
        .where(ProjectDecision.project_id == project_id)
        .order_by(ProjectDecision.label.asc(), ProjectDecision.decision_id.asc())
    )
    return list(result.scalars().all())


async def locked_selections(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
) -> dict[str, str]:
    result = await session.execute(
        select(ProjectDecision.decision_id, ProjectDecision.selected).where(
            ProjectDecision.project_id == project_id,
            ProjectDecision.source == "user",
        )
    )
    return {row.decision_id: row.selected for row in result.all()}


async def sync_decisions_from_markdown(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    markdown: str,
    workflow_type: str,
    locked: dict[str, str] | None = None,
) -> None:
    locked = locked or {}
    for decision in extract_decisions(markdown):
        source = "user" if decision.id in locked else decision.source
        selected = locked.get(decision.id, decision.selected)
        await upsert_decision(
            session,
            project_id=project_id,
            decision_id=decision.id,
            section=decision.section,
            label=decision.label,
            options=[dict(option) for option in decision.options],
            selected=selected,
            source=source,
            workflow_type=workflow_type,
        )


def decision_row_from_pmp(decision: PmpDecision) -> dict[str, Any]:
    return {
        "decision_id": decision.id,
        "section": decision.section,
        "label": decision.label,
        "options": [dict(option) for option in decision.options],
        "selected": decision.selected,
        "source": decision.source,
    }
