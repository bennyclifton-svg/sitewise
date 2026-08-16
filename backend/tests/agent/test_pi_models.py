import pytest

from app.agent.pi_models import (
    pi_models_response,
    resolve_pi_model_override,
)
from app.config import settings


def test_pi_models_response_defaults_to_fast_luna_and_thorough_grok() -> None:
    response = pi_models_response()

    assert [model.id for model in response.models] == [
        "openai:gpt-5.6-luna",
        "xai:grok-4.6",
    ]
    assert [model.label for model in response.models] == ["Fast", "Thorough"]
    assert response.default_model == "openai:gpt-5.6-luna"
    assert response.models[0].is_default is True
    assert response.models[1].provider == "xai"
    assert response.models[1].model == "grok-4.6"


def test_resolve_pi_model_override_accepts_thorough_grok() -> None:
    override = resolve_pi_model_override("xai:grok-4.6")

    assert override is not None
    assert override.provider == "xai"
    assert override.model == "grok-4.6"


def test_resolve_pi_model_override_maps_retired_sol_thorough_to_grok() -> None:
    override = resolve_pi_model_override("openai:gpt-5.6-sol")

    assert override is not None
    assert override.provider == "xai"
    assert override.model == "grok-4.6"


def test_resolve_pi_model_override_maps_bare_sol_id_to_grok() -> None:
    override = resolve_pi_model_override("gpt-5.6-sol")

    assert override is not None
    assert override.provider == "xai"
    assert override.model == "grok-4.6"


def test_pi_models_response_exposes_only_allowlisted_pi_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "agent_runtime_enabled", True)
    monkeypatch.setattr(settings, "pi_model_provider", "openai")
    monkeypatch.setattr(settings, "pi_model", "gpt-5.6-luna")
    monkeypatch.setattr(
        settings,
        "pi_model_options",
        (
            "openai:gpt-5.6-sol:GPT-5.6 Sol (complex),"
            "openai:gpt-5.6-luna:GPT-5.6 Luna (fast)"
        ),
    )

    response = pi_models_response()

    assert response.agent_runtime_enabled is True
    assert response.default_model == "openai:gpt-5.6-luna"
    assert [model.id for model in response.models] == [
        "openai:gpt-5.6-luna",
        "openai:gpt-5.6-sol",
    ]
    assert [model.label for model in response.models] == ["Fast", "Thorough"]
