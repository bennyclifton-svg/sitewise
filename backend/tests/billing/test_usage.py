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


@pytest.mark.parametrize("state,status_value,expired", [
    ("revoked", "not_started", False), ("active", "running", False),
    ("completed", "completed", False), ("active", "reserved", True),
])
def test_start_rejects_cancelled_duplicate_completed_and_expired_turns(
    monkeypatch, state, status_value, expired,
):
    turn = SimpleNamespace(state=state, status=status_value,
                           expires_at=datetime.now(UTC) + timedelta(seconds=-1 if expired else 60))
    session = AsyncMock()
    session.get.return_value = turn
    monkeypatch.setattr(usage, "_advisory_lock", AsyncMock())
    assert not run_async(usage.start_agent_turn(session, uuid.uuid4()))
    session.flush.assert_not_awaited()


def test_start_claims_only_once(monkeypatch):
    turn = SimpleNamespace(state="active", status="reserved",
                           expires_at=datetime.now(UTC) + timedelta(seconds=60))
    session = AsyncMock()
    session.get.return_value = turn
    monkeypatch.setattr(usage, "_advisory_lock", AsyncMock())
    turn_id = uuid.uuid4()
    assert run_async(usage.start_agent_turn(session, turn_id))
    assert turn.status == "running"
    assert not run_async(usage.start_agent_turn(session, turn_id))


def test_cancel_before_execution_releases_quota_reservation(monkeypatch):
    turn = SimpleNamespace(state="active", status="reserved")
    session = AsyncMock()
    session.get.return_value = turn
    monkeypatch.setattr(usage, "_advisory_lock", AsyncMock())
    assert run_async(usage.revoke_agent_turn(session, uuid.uuid4()))
    assert turn.status == "not_started"
    assert turn.state == "revoked"


def test_late_stop_preserves_an_already_committed_completion(monkeypatch):
    turn = SimpleNamespace(state="completed", status="completed")
    session = AsyncMock()
    session.get.return_value = turn
    monkeypatch.setattr(usage, "_advisory_lock", AsyncMock())
    assert not run_async(usage.revoke_agent_turn(session, uuid.uuid4()))
    assert turn.status == "completed"
    session.flush.assert_not_awaited()


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


def test_reservation_charges_pi_agent_turns(monkeypatch) -> None:
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
            user_message_id="message-pi",
            runtime="pi",
            model="test-model",
        )
    )

    assert created is True
    assert state.used_turns == 1
    assert turn.runtime == "pi"
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


def test_second_message_cannot_bypass_an_active_thread_reservation(monkeypatch):
    monkeypatch.setattr(usage, "_advisory_lock", AsyncMock())
    session = MagicMock()
    session.scalar = AsyncMock(side_effect=[None, uuid.uuid4()])
    with pytest.raises(HTTPException) as error:
        run_async(usage.reserve_agent_turn(
            session, turn_id=uuid.uuid4(), project_id=uuid.uuid4(), user_id=USER_ID,
            thread_id=uuid.uuid4(), user_message_id="second-message", runtime="pi", model="test",
        ))
    assert error.value.status_code == 409
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
            input_context={"selected_documents": [{"workspace_file_id": "file-1"}]},
            runtime="pi",
            model="test-model",
        )
    )

    assert created is True
    assert turn.user_message_hash == "a" * 64
    assert turn.mutation_scopes == ["profile_mutation"]
    assert turn.mutation_intent["profile_patch"] == {"state": "VIC"}
    assert turn.input_context == {
        "selected_documents": [{"workspace_file_id": "file-1"}]
    }


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


def test_complete_agent_turn_persists_task_route_latency_and_usage(monkeypatch) -> None:
    turn = SimpleNamespace(
        id=uuid.uuid4(),
        state="active",
        status="reserved",
        completed_at=None,
        input_tokens=None,
        output_tokens=None,
        input_context={
            "task_route": {
                "task_class": "FAST_SEMANTIC",
                "path": "fast_semantic",
                "retrieval": "none",
                "model": "gpt-5.6-luna",
                "reason": "mapping",
                "latency_ms": None,
                "usage": {"input_tokens": None, "output_tokens": None},
            }
        },
    )
    monkeypatch.setattr(usage, "_advisory_lock", AsyncMock())
    session = MagicMock()
    session.get = AsyncMock(return_value=turn)
    session.flush = AsyncMock()

    run_async(
        usage.complete_agent_turn(
            session,
            turn.id,
            status_value="completed",
            latency_ms=123,
            input_tokens=11,
            output_tokens=5,
        )
    )

    assert turn.status == "completed"
    assert turn.state == "completed"
    assert turn.input_tokens == 11
    assert turn.output_tokens == 5
    assert turn.input_context["task_route"]["latency_ms"] == 123
    assert turn.input_context["task_route"]["usage"] == {
        "input_tokens": 11,
        "output_tokens": 5,
    }


def test_scope_populate_allows_work_scope_checkbox_patch(monkeypatch) -> None:
    turn = _active_turn()
    turn.mutation_intent = {
        "profile_patch": {},
        "reason": "profile_scope_populate",
    }
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
            requested_profile_patch={
                "work_scope": ["substructure", "superstructure", "roofing"],
            },
        )
    )

    assert allowed is turn


def test_setup_from_brief_allows_superset_of_extracted_values(monkeypatch) -> None:
    turn = _active_turn()
    turn.mutation_intent = {
        "profile_patch": {"scale": {"storeys": 2, "bedrooms": 4}},
        "reason": "profile_setup_from_brief",
    }
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
            requested_profile_patch={
                "scale": {"storeys": 2, "bedrooms": 4, "garage_spaces": 2},
                "complexity": {"planning": "da", "procurement_route": "design_construct"},
                "scope_narrative": [
                    "Two-storey 4 bedroom home",
                    "Double garage",
                    "DA planning pathway",
                    "Design and construct",
                ],
            },
        )
    )

    assert allowed is turn


def test_enrichment_authority_allows_evidence_backed_profile_patch(monkeypatch) -> None:
    turn = _active_turn()
    turn.mutation_intent = {
        "profile_patch": {},
        "reason": "profile_enrichment_authority",
    }
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
            requested_profile_patch={
                "site_address": "145-151 Arthur Street, Homebush West NSW 2140",
                "client": "Hale c/o Engine Room VM",
                "scale": {"gfa_sqm": 2135, "office_percent": 9.3, "dock_doors": 1},
            },
        )
    )

    assert allowed is turn

