import pytest

from app.config import settings


def test_hermes_models_response_includes_default_and_allowlisted_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agent.hermes_models import (
        HERMES_DEFAULT_MODEL_ID,
        hermes_models_response,
    )

    monkeypatch.setattr(settings, "agent_runtime_enabled", True)
    monkeypatch.setattr(
        settings,
        "hermes_model_options",
        "openai-codex:gpt-5.5:gpt-5.5 (Codex),openai-api:gpt-5.1",
    )

    response = hermes_models_response()

    assert response.agent_runtime_enabled is True
    assert response.default_runtime == "hermes"
    assert response.default_model == HERMES_DEFAULT_MODEL_ID
    assert len(response.runtimes) == 2
    assert response.models[0].id == HERMES_DEFAULT_MODEL_ID
    assert response.models[0].is_default is True
    assert response.models[1].id == "openai-codex:gpt-5.5"
    assert response.models[1].label == "gpt-5.5 (Codex)"
    assert response.models[2].id == "openai-api:gpt-5.1"


def test_hermes_model_override_rejects_unknown_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agent.hermes_models import (
        InvalidHermesModelError,
        resolve_hermes_model_override,
    )

    monkeypatch.setattr(settings, "hermes_model_options", "openai-codex:gpt-5.5")

    with pytest.raises(InvalidHermesModelError):
        resolve_hermes_model_override("xai-oauth:gpt-5.5")
