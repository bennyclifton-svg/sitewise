import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.auth.dependencies import CurrentUser
from app.billing import usage
from app.config import settings
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER = CurrentUser(id=USER_ID, email="a@example.com")


def test_under_quota_allows_agent_turn(monkeypatch):
    monkeypatch.setattr(settings, "agent_monthly_turn_quota", 100)
    monkeypatch.setattr(usage, "count_monthly_agent_turns", AsyncMock(return_value=12))

    state = run_async(usage.require_turn_within_quota(AsyncMock(), USER))

    assert state.used_turns == 12
    assert state.warning is False


def test_at_eighty_percent_returns_soft_warning(monkeypatch):
    monkeypatch.setattr(settings, "agent_monthly_turn_quota", 100)
    monkeypatch.setattr(usage, "count_monthly_agent_turns", AsyncMock(return_value=80))

    state = run_async(usage.require_turn_within_quota(AsyncMock(), USER))

    assert state.warning is True
    assert state.percent == 80


def test_over_quota_blocks_agent_turn(monkeypatch):
    monkeypatch.setattr(settings, "agent_monthly_turn_quota", 100)
    monkeypatch.setattr(usage, "count_monthly_agent_turns", AsyncMock(return_value=100))

    with pytest.raises(HTTPException) as exc_info:
        run_async(usage.require_turn_within_quota(AsyncMock(), USER))

    assert exc_info.value.status_code == 402


@pytest.mark.parametrize("runtime", ["hermes", "pi"])
def test_reservation_charges_both_agent_runtimes_equally(monkeypatch, runtime: str) -> None:
    monkeypatch.setattr(settings, "agent_monthly_turn_quota", 100)
    monkeypatch.setattr(usage, "count_monthly_agent_turns", AsyncMock(return_value=0))
    monkeypatch.setattr(usage, "_advisory_lock", AsyncMock())
    session = MagicMock()
    session.scalar = AsyncMock(return_value=None)
    session.flush = AsyncMock()

    turn, state, created = run_async(
        usage.reserve_agent_turn(
            session,
            turn_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            user_id=USER_ID,
            thread_id=uuid.uuid4(),
            user_message_id=f"message-{runtime}",
            runtime=runtime,
            model="test-model",
        )
    )

    assert created is True
    assert state.used_turns == 1
    assert turn.runtime == runtime
    session.add.assert_called_once_with(turn)


def test_reservation_retry_reuses_durable_turn_without_double_count(monkeypatch) -> None:
    existing = SimpleNamespace(id=uuid.uuid4())
    monkeypatch.setattr(settings, "agent_monthly_turn_quota", 100)
    monkeypatch.setattr(usage, "count_monthly_agent_turns", AsyncMock(return_value=1))
    monkeypatch.setattr(usage, "_advisory_lock", AsyncMock())
    session = MagicMock()
    session.scalar = AsyncMock(return_value=existing)

    turn, state, created = run_async(
        usage.reserve_agent_turn(
            session,
            turn_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            user_id=USER_ID,
            thread_id=uuid.uuid4(),
            user_message_id="stable-message-id",
            runtime="pi",
            model="test-model",
        )
    )

    assert turn is existing
    assert state.used_turns == 1
    assert created is False
    session.add.assert_not_called()


def test_reservation_persists_message_hash_and_bound_mutation_intent(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_monthly_turn_quota", 100)
    monkeypatch.setattr(usage, "count_monthly_agent_turns", AsyncMock(return_value=0))
    monkeypatch.setattr(usage, "_advisory_lock", AsyncMock())
    session = MagicMock()
    session.scalar = AsyncMock(return_value=None)
    session.flush = AsyncMock()

    turn, _, created = run_async(
        usage.reserve_agent_turn(
            session,
            turn_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            user_id=USER_ID,
            thread_id=uuid.uuid4(),
            user_message_id="mutation-message",
            user_message_hash="a" * 64,
            mutation_scopes=["profile_mutation"],
            mutation_intent={"profile_patch": {"state": "VIC"}},
            runtime="pi",
            model="test-model",
        )
    )

    assert created is True
    assert turn.user_message_hash == "a" * 64
    assert turn.mutation_scopes == ["profile_mutation"]
    assert turn.mutation_intent["profile_patch"] == {"state": "VIC"}


def _active_turn(*, runtime: str = "pi", state: str = "active") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        project_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        user_id=USER_ID,
        runtime=runtime,
        state=state,
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
        mutation_scopes=["profile_mutation"],
        mutation_intent={"profile_patch": {"state": "VIC"}},
    )


def test_mutation_authorization_rejects_revoked_durable_turn(monkeypatch) -> None:
    turn = _active_turn(state="revoked")
    monkeypatch.setattr(usage, "_advisory_lock", AsyncMock())
    session = MagicMock()
    session.get = AsyncMock(return_value=turn)

    with pytest.raises(PermissionError, match="revoked or expired"):
        run_async(
            usage.require_active_mutation_turn(
                session,
                turn_id=turn.id,
                project_id=turn.project_id,
                user_id=turn.user_id,
            )
        )


def test_mutation_authorization_requires_bound_scope_and_exact_values(monkeypatch) -> None:
    turn = _active_turn()
    monkeypatch.setattr(usage, "_advisory_lock", AsyncMock())
    session = MagicMock()
    session.get = AsyncMock(return_value=turn)

    allowed = run_async(
        usage.require_active_mutation_turn(
            session,
            turn_id=turn.id,
            project_id=turn.project_id,
            user_id=turn.user_id,
            required_scope="profile_mutation",
            requested_profile_patch={"state": "VIC"},
        )
    )
    assert allowed is turn

    with pytest.raises(PermissionError, match="does not match bound user intent"):
        run_async(
            usage.require_active_mutation_turn(
                session,
                turn_id=turn.id,
                project_id=turn.project_id,
                user_id=turn.user_id,
                required_scope="profile_mutation",
                requested_profile_patch={"state": "QLD"},
            )
        )


def test_hermes_mutations_are_blocked_until_prompt_transport_is_safe(monkeypatch) -> None:
    turn = _active_turn(runtime="hermes")
    monkeypatch.setattr(settings, "hermes_mutations_enabled", False)
    monkeypatch.setattr(usage, "_advisory_lock", AsyncMock())
    session = MagicMock()
    session.get = AsyncMock(return_value=turn)

    with pytest.raises(PermissionError, match="non-argv"):
        run_async(
            usage.require_active_mutation_turn(
                session,
                turn_id=turn.id,
                project_id=turn.project_id,
                user_id=turn.user_id,
            )
        )

