import pytest

from app.assistant.pmp_models import (
    InvalidPmpModelError,
    resolve_pmp_model,
)
from app.config import settings


def test_resolve_pmp_model_defaults_to_configured_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "pmp_model_provider", "openai-api")
    monkeypatch.setattr(settings, "pmp_model", "gpt-5.6-terra")
    monkeypatch.setattr(settings, "pmp_model_label", "GPT-5.6 Terra (balanced)")

    spec = resolve_pmp_model(None)

    assert spec.provider == "openai-api"
    assert spec.model == "gpt-5.6-terra"
    assert spec.label == "GPT-5.6 Terra (balanced)"
    assert spec.configured_id == "openai-api:gpt-5.6-terra"
    assert spec.execution_provider == "openai-responses"
    assert spec.execution_id == "openai-responses:gpt-5.6-terra"
    assert spec.source == "PMP_MODEL"


@pytest.mark.parametrize("configured", ["openai-api", "openai-chat", "openai-codex"])
def test_every_configured_provider_executes_via_responses(
    monkeypatch: pytest.MonkeyPatch, configured: str
) -> None:
    """GPT-5.6 rejects function tools alongside reasoning on chat completions.

    Whatever provenance records, the typed runner must execute via the Responses
    provider or PydanticAI's typed output would 400.
    """
    monkeypatch.setattr(settings, "pmp_model_provider", configured)
    monkeypatch.setattr(settings, "pmp_model", "gpt-5.6-sol")
    monkeypatch.setattr(settings, "pmp_model_label", "")

    spec = resolve_pmp_model(None)

    assert spec.provider == configured
    assert spec.configured_id == f"{configured}:gpt-5.6-sol"
    assert spec.execution_provider == "openai-responses"
    assert spec.execution_id == "openai-responses:gpt-5.6-sol"


def test_resolve_pmp_model_accepts_plain_request_override() -> None:
    spec = resolve_pmp_model("gpt-5.6-sol")

    assert spec.provider == "openai-api"
    assert spec.model == "gpt-5.6-sol"
    assert spec.execution_id == "openai-responses:gpt-5.6-sol"
    assert spec.source == "request"


def test_resolve_pmp_model_accepts_provider_qualified_override() -> None:
    spec = resolve_pmp_model("openai-codex:gpt-5.6-sol")

    assert spec.provider == "openai-codex"
    assert spec.model == "gpt-5.6-sol"
    assert spec.label == "gpt-5.6-sol (Codex)"
    assert spec.execution_id == "openai-responses:gpt-5.6-sol"


def test_resolve_pmp_model_rejects_unknown_provider() -> None:
    with pytest.raises(InvalidPmpModelError):
        resolve_pmp_model("unknown:gpt-5.6-sol")
