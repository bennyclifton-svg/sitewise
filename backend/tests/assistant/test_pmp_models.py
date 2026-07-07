import pytest

from app.assistant.pmp_models import (
    InvalidPmpModelError,
    resolve_pmp_model,
)
from app.config import settings


def test_resolve_pmp_model_defaults_to_codex_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "pmp_model_provider", "openai-codex")
    monkeypatch.setattr(settings, "pmp_model", "gpt-5.5")
    monkeypatch.setattr(settings, "pmp_model_label", "gpt-5.5 (Codex)")

    spec = resolve_pmp_model(None)

    assert spec.provider == "openai-codex"
    assert spec.model == "gpt-5.5"
    assert spec.label == "gpt-5.5 (Codex)"
    assert spec.configured_id == "openai-codex:gpt-5.5"
    assert spec.execution_provider == "openai-chat"
    assert spec.execution_id == "openai-chat:gpt-5.5"
    assert spec.source == "PMP_MODEL"


def test_resolve_pmp_model_accepts_plain_request_override() -> None:
    spec = resolve_pmp_model("gpt-4.1")

    assert spec.provider == "openai-chat"
    assert spec.model == "gpt-4.1"
    assert spec.execution_id == "openai-chat:gpt-4.1"
    assert spec.source == "request"


def test_resolve_pmp_model_accepts_provider_qualified_override() -> None:
    spec = resolve_pmp_model("openai-codex:gpt-5.5")

    assert spec.provider == "openai-codex"
    assert spec.model == "gpt-5.5"
    assert spec.label == "gpt-5.5 (Codex)"
    assert spec.execution_id == "openai-chat:gpt-5.5"


def test_resolve_pmp_model_rejects_unknown_provider() -> None:
    with pytest.raises(InvalidPmpModelError):
        resolve_pmp_model("unknown:gpt-5.5")
