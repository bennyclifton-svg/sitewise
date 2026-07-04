from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.config import settings
from app.database.chat_message import ChatMessage
from app.database.chat_thread import ChatThread


@dataclass(frozen=True, slots=True)
class AgentUsageState:
    used_turns: int
    quota: int
    percent: int
    warning: bool


def month_start(now: datetime | None = None) -> datetime:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def count_monthly_agent_turns(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
) -> int:
    stmt = (
        select(func.count(ChatMessage.id))
        .join(ChatThread, ChatMessage.thread_id == ChatThread.id)
        .where(
            ChatThread.user_id == user_id,
            ChatMessage.role == "assistant",
            ChatMessage.created_at >= month_start(now),
            ChatMessage.message_data["agent"]["runtime"].as_string() == "hermes",
        )
    )
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def agent_usage_state(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
) -> AgentUsageState:
    quota = max(0, settings.agent_monthly_turn_quota)
    used_turns = await count_monthly_agent_turns(session, user_id=user_id, now=now)
    if quota == 0:
        return AgentUsageState(
            used_turns=used_turns,
            quota=quota,
            percent=0,
            warning=False,
        )
    percent = min(100, int((used_turns / quota) * 100))
    return AgentUsageState(
        used_turns=used_turns,
        quota=quota,
        percent=percent,
        warning=percent >= 80,
    )


async def require_turn_within_quota(
    session: AsyncSession,
    user: CurrentUser,
) -> AgentUsageState:
    state = await agent_usage_state(session, user_id=user.id)
    if state.quota > 0 and state.used_turns >= state.quota:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Monthly agent turn quota exceeded.",
        )
    return state

