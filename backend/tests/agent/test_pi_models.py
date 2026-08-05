import pytest

from app.config import settings


def test_pi_models_response_exposes_only_allowlisted_pi_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agent.pi_models import pi_models_response

    monkeypatch.setattr(settings, "agent_runtime_enabled", True)
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
    assert response.default_model == "openai:gpt-5.6-terra"
    assert [model.id for model in response.models] == [
        "openai:gpt-5.6-sol",
        "openai:gpt-5.6-luna",
    ]
