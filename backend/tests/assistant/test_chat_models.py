import pytest

from app.assistant.chat_models import (
    InvalidChatModelError,
    allowed_chat_models,
    chat_models_response,
    resolve_chat_model,
)


def test_resolve_chat_model_uses_default_when_unset() -> None:
    assert resolve_chat_model(None) == resolve_chat_model("")
    assert resolve_chat_model(None) in allowed_chat_models()


def test_resolve_chat_model_rejects_unknown_model() -> None:
    with pytest.raises(InvalidChatModelError):
        resolve_chat_model("not-a-real-model")


def test_chat_models_response_includes_default_flag() -> None:
    response = chat_models_response()
    assert response.default_model in {model.id for model in response.models}
    assert any(model.is_default for model in response.models)
