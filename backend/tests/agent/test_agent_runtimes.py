import pytest

from app.agent.agent_runtimes import (
    HERMES_RUNTIME_ID,
    PI_RUNTIME_ID,
    InvalidAgentRuntimeError,
    agent_runtime_options,
    pi_model_options,
    resolve_pi_model_override,
    resolve_agent_runtime,
    resolve_agent_runtime_for_turn,
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


def test_pi_model_options_include_the_gpt_5_6_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings,
        "pi_model_options",
        (
            "openai:gpt-5.6-sol:GPT-5.6 Sol (complex),"
            "openai:gpt-5.6-terra:GPT-5.6 Terra (balanced),"
            "openai:gpt-5.6-luna:GPT-5.6 Luna (fast)"
        ),
    )

    options = pi_model_options()

    assert [option.id for option in options] == [
        "openai:gpt-5.6-sol",
        "openai:gpt-5.6-terra",
        "openai:gpt-5.6-luna",
    ]
    assert resolve_pi_model_override("openai:gpt-5.6-sol").model == "gpt-5.6-sol"


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


def test_profile_mutation_turns_route_to_pi_while_hermes_mutations_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "agent_runtime_enabled", True)
    monkeypatch.setattr(settings, "pi_runtime_enabled", True)
    monkeypatch.setattr(settings, "hermes_mutations_enabled", False)

    assert (
        resolve_agent_runtime_for_turn(
            HERMES_RUNTIME_ID,
            needs_mutation_tools=True,
        )
        == PI_RUNTIME_ID
    )


def test_read_only_turns_keep_hermes_while_mutations_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "agent_runtime_enabled", True)
    monkeypatch.setattr(settings, "pi_runtime_enabled", True)
    monkeypatch.setattr(settings, "hermes_mutations_enabled", False)

    assert (
        resolve_agent_runtime_for_turn(
            HERMES_RUNTIME_ID,
            needs_mutation_tools=False,
        )
        == HERMES_RUNTIME_ID
    )


def test_workflow_mutation_turns_route_to_pi_while_hermes_mutations_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "agent_runtime_enabled", True)
    monkeypatch.setattr(settings, "pi_runtime_enabled", True)
    monkeypatch.setattr(settings, "hermes_mutations_enabled", False)

    assert (
        resolve_agent_runtime_for_turn(
            HERMES_RUNTIME_ID,
            needs_mutation_tools=True,
        )
        == PI_RUNTIME_ID
    )


def test_profile_mutation_turns_keep_hermes_when_mutations_are_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "agent_runtime_enabled", True)
    monkeypatch.setattr(settings, "pi_runtime_enabled", True)
    monkeypatch.setattr(settings, "hermes_mutations_enabled", True)

    assert (
        resolve_agent_runtime_for_turn(
            HERMES_RUNTIME_ID,
            needs_mutation_tools=True,
        )
        == HERMES_RUNTIME_ID
    )


def test_profile_mutation_turns_fail_clearly_when_no_safe_runtime_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "agent_runtime_enabled", True)
    monkeypatch.setattr(settings, "pi_runtime_enabled", False)
    monkeypatch.setattr(settings, "hermes_mutations_enabled", False)

    with pytest.raises(InvalidAgentRuntimeError, match="non-argv"):
        resolve_agent_runtime_for_turn(
            HERMES_RUNTIME_ID,
            needs_mutation_tools=True,
        )
