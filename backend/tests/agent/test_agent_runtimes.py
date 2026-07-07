import pytest

from app.agent.agent_runtimes import (
    HERMES_RUNTIME_ID,
    PI_RUNTIME_ID,
    InvalidAgentRuntimeError,
    agent_runtime_options,
    resolve_agent_runtime,
)
from app.config import settings


def test_agent_runtime_options_include_hermes_and_pi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "agent_runtime_enabled", True)
    monkeypatch.setattr(settings, "pi_runtime_enabled", False)

    options = agent_runtime_options()
    ids = {option.id for option in options}

    assert HERMES_RUNTIME_ID in ids
    assert PI_RUNTIME_ID in ids
    hermes = next(option for option in options if option.id == HERMES_RUNTIME_ID)
    assert hermes.model == settings.hermes_model
    pi = next(option for option in options if option.id == PI_RUNTIME_ID)
    assert pi.model == settings.pi_model
    assert pi.enabled is False


def test_resolve_agent_runtime_rejects_disabled_pi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "agent_runtime_enabled", True)
    monkeypatch.setattr(settings, "pi_runtime_enabled", False)

    with pytest.raises(InvalidAgentRuntimeError):
        resolve_agent_runtime(PI_RUNTIME_ID)


def test_resolve_agent_runtime_accepts_enabled_pi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "agent_runtime_enabled", True)
    monkeypatch.setattr(settings, "pi_runtime_enabled", True)

    assert resolve_agent_runtime(PI_RUNTIME_ID) == PI_RUNTIME_ID
