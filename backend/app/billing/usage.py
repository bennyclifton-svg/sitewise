from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.config import settings
from app.database.agent_turn import AgentTurn


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


async def _advisory_lock(session: AsyncSession, key: str) -> None:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key}
    )


async def count_monthly_agent_turns(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
) -> int:
    result = await session.execute(
        select(func.count(AgentTurn.id)).where(
            AgentTurn.user_id == user_id,
            AgentTurn.created_at >= month_start(now),
        )
    )
    return int(result.scalar_one() or 0)


def _usage_state(used_turns: int) -> AgentUsageState:
    quota = max(0, settings.agent_monthly_turn_quota)
    percent = min(100, int((used_turns / quota) * 100)) if quota else 0
    return AgentUsageState(
        used_turns=used_turns,
        quota=quota,
        percent=percent,
        warning=bool(quota and percent >= 80),
    )


async def agent_usage_state(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
) -> AgentUsageState:
    return _usage_state(await count_monthly_agent_turns(session, user_id=user_id, now=now))


async def require_turn_within_quota(
    session: AsyncSession, user: CurrentUser
) -> AgentUsageState:
    state = await agent_usage_state(session, user_id=user.id)
    if state.quota > 0 and state.used_turns >= state.quota:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Monthly agent turn quota exceeded.",
        )
    return state


async def reserve_agent_turn(
    session: AsyncSession,
    *,
    turn_id: uuid.UUID,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    thread_id: uuid.UUID,
    user_message_id: str,
    runtime: str,
    model: str | None,
    user_message_hash: str | None = None,
    mutation_scopes: list[str] | None = None,
    mutation_intent: dict | None = None,
    now: datetime | None = None,
) -> tuple[AgentTurn, AgentUsageState, bool]:
    """Atomically reserve one quota slot; retries of a message reuse its row."""
    current = now or datetime.now(UTC)
    await _advisory_lock(session, f"agent-quota:{user_id}:{month_start(current).date()}")
    existing = await session.scalar(
        select(AgentTurn).where(
            AgentTurn.user_id == user_id,
            AgentTurn.project_id == project_id,
            AgentTurn.user_message_id == user_message_id,
        )
    )
    if existing is not None:
        used = await count_monthly_agent_turns(session, user_id=user_id, now=current)
        return existing, _usage_state(used), False

    used = await count_monthly_agent_turns(session, user_id=user_id, now=current)
    state = _usage_state(used)
    if state.quota > 0 and used >= state.quota:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Monthly agent turn quota exceeded.",
        )

    turn = AgentTurn(
        id=turn_id,
        project_id=project_id,
        user_id=user_id,
        thread_id=thread_id,
        user_message_id=user_message_id,
        user_message_hash=user_message_hash,
        mutation_scopes=mutation_scopes or [],
        mutation_intent=mutation_intent or {},
        state="active",
        runtime=runtime,
        model=model,
        status="reserved",
        expires_at=current + timedelta(seconds=settings.agent_turn_timeout_seconds + 30),
    )
    session.add(turn)
    await session.flush()
    return turn, _usage_state(used + 1), True


async def revoke_agent_turn(session: AsyncSession, turn_id: uuid.UUID) -> bool:
    await _advisory_lock(session, f"agent-turn:{turn_id}")
    turn = await session.get(AgentTurn, turn_id, with_for_update=True)
    if turn is None:
        return False
    if turn.state == "revoked":
        return True
    turn.state = "revoked"
    turn.status = "cancelled"
    turn.revoked_at = datetime.now(UTC)
    await session.flush()
    return True


async def require_active_mutation_turn(
    session: AsyncSession,
    *,
    turn_id: uuid.UUID,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    required_scope: str | None = None,
    requested_profile_patch: dict | None = None,
) -> AgentTurn:
    """Acquire the commit lock and re-read durable capability state."""
    await _advisory_lock(session, f"agent-turn:{turn_id}")
    turn = await session.get(AgentTurn, turn_id, with_for_update=True)
    now = datetime.now(UTC)
    if (
        turn is None
        or turn.project_id != project_id
        or turn.user_id != user_id
        or turn.state != "active"
        or turn.expires_at <= now
    ):
        raise PermissionError("agent mutation turn is revoked or expired")
    if turn.runtime == "hermes" and not settings.hermes_mutations_enabled:
        raise PermissionError(
            "Hermes mutations are disabled until a non-argv prompt transport is verified"
        )
    if required_scope is not None and required_scope not in (turn.mutation_scopes or []):
        raise PermissionError(f"agent turn lacks required mutation scope: {required_scope}")
    if requested_profile_patch is not None:
        bound_patch = (turn.mutation_intent or {}).get("profile_patch", {})
        if bound_patch != requested_profile_patch:
            raise PermissionError("profile mutation does not match bound user intent")
    return turn


async def complete_agent_turn(
    session: AsyncSession, turn_id: uuid.UUID, *, status_value: str
) -> None:
    turn = await session.get(AgentTurn, turn_id, with_for_update=True)
    if turn is None or turn.state == "revoked":
        return
    turn.state = "completed"
    turn.status = status_value
    turn.completed_at = datetime.now(UTC)
    await session.flush()
