import uuid
from unittest.mock import AsyncMock

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

