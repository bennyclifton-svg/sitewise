"""OpenAI chat model allowlist and runtime selection."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import settings

DEFAULT_OPENAI_CHAT_MODELS: tuple[str, ...] = (
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
)

MODEL_LABELS: dict[str, str] = {
    "gpt-5.6-luna": "Fast",
    "gpt-5.6-terra": "Balanced",
    "gpt-5.6-sol": "Complex",
}


class ChatModelOption(BaseModel):
    id: str
    label: str
    is_default: bool = False


class ChatModelsResponse(BaseModel):
    default_model: str
    models: list[ChatModelOption] = Field(default_factory=list)


class InvalidChatModelError(ValueError):
    """Raised when a requested chat model is not allowlisted."""


def allowed_chat_models() -> tuple[str, ...]:
    configured = [
        model.strip()
        for model in settings.openai_chat_models.split(",")
        if model.strip()
    ]
    if not configured:
        return DEFAULT_OPENAI_CHAT_MODELS

    ordered: list[str] = []
    seen: set[str] = set()
    for model in configured:
        if model in seen:
            continue
        seen.add(model)
        ordered.append(model)

    default = settings.openai_chat_model
    if default not in seen:
        ordered.insert(0, default)
    return tuple(ordered)


def resolve_chat_model(override: str | None = None) -> str:
    """Return the chat model id to use for this request."""
    if override is None or not override.strip():
        return settings.openai_chat_model

    model = override.strip()
    if model not in allowed_chat_models():
        allowed = ", ".join(allowed_chat_models())
        raise InvalidChatModelError(
            f"Unsupported chat model {model!r}. Allowed models: {allowed}"
        )
    return model


def openai_chat_provider(model: str) -> str:
    return f"openai-responses:{model}"


def chat_model_options() -> list[ChatModelOption]:
    default = settings.openai_chat_model
    options: list[ChatModelOption] = []
    for model_id in allowed_chat_models():
        options.append(
            ChatModelOption(
                id=model_id,
                label=MODEL_LABELS.get(model_id, model_id),
                is_default=model_id == default,
            )
        )
    return options


def chat_models_response() -> ChatModelsResponse:
    return ChatModelsResponse(
        default_model=settings.openai_chat_model,
        models=chat_model_options(),
    )
