import uuid

import pytest

from app.mcp_bridge.tokens import (
    TurnTokenConfigurationError,
    TurnTokenError,
    mint_turn_token,
    verify_turn_token,
)

SECRET = "test-secret"
USER = uuid.uuid4()
PROJECT = uuid.uuid4()


def test_round_trip():
    token = mint_turn_token(user_id=USER, project_id=PROJECT, secret=SECRET, now=1000.0)
    claims = verify_turn_token(token, secret=SECRET, now=1500.0)
    assert claims.user_id == USER
    assert claims.project_id == PROJECT


def test_expired_token_rejected():
    token = mint_turn_token(
        user_id=USER, project_id=PROJECT, secret=SECRET, now=1000.0, ttl_seconds=60
    )
    with pytest.raises(TurnTokenError):
        verify_turn_token(token, secret=SECRET, now=1061.0)


def test_tampered_token_rejected():
    token = mint_turn_token(user_id=USER, project_id=PROJECT, secret=SECRET)
    body, sig = token.rsplit(".", 1)
    with pytest.raises(TurnTokenError):
        verify_turn_token(body + ".AAAA", secret=SECRET)


def test_wrong_secret_rejected():
    token = mint_turn_token(user_id=USER, project_id=PROJECT, secret=SECRET)
    with pytest.raises(TurnTokenError):
        verify_turn_token(token, secret="other")


def test_empty_secret_rejected():
    with pytest.raises(TurnTokenConfigurationError):
        mint_turn_token(user_id=USER, project_id=PROJECT, secret="")
    token = mint_turn_token(user_id=USER, project_id=PROJECT, secret=SECRET)
    with pytest.raises(TurnTokenConfigurationError):
        verify_turn_token(token, secret="")
