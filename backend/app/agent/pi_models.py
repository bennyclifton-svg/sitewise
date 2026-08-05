"""Pi model selection for Clerk agent chat."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.config import settings

PI_RUNTIME_ID = "pi"
PI_MODEL_TIER_LABELS = {
    "gpt-5.6-luna": "Fast",
    "gpt-5.6-terra": "Balanced",
    "gpt-5.6-sol": "Complex",
}
PI_MODEL_TIER_ORDER = {model: index for index, model in enumerate(PI_MODEL_TIER_LABELS)}


class PiModelOption(BaseModel):
    id: str
    label: str
    is_default: bool = False
    provider: str
    model: str


class PiModelsResponse(BaseModel):
    default_model: str
    agent_runtime_enabled: bool
    models: list[PiModelOption] = Field(default_factory=list)


class InvalidPiModelError(ValueError):
    """Raised when a requested Pi model is not allowlisted."""


@dataclass(frozen=True)
class PiModelOverride:
    provider: str
    model: str


def _model_id(provider: str, model: str) -> str:
    return f"{provider}:{model}"


def _parse_pi_model_option(raw: str) -> PiModelOption | None:
    parts = [part.strip() for part in raw.split(":", 2)]
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    provider, model = parts[0], parts[1]
    configured_label = parts[2] if len(parts) == 3 and parts[2] else model
    label = PI_MODEL_TIER_LABELS.get(model, configured_label)
    return PiModelOption(
        id=_model_id(provider, model),
        label=label,
        is_default=(
            provider == settings.pi_model_provider and model == settings.pi_model
        ),
        provider=provider,
        model=model,
    )


def pi_model_options() -> list[PiModelOption]:
    options: list[PiModelOption] = []
    seen: set[str] = set()
    for raw in settings.pi_model_options.split(","):
        option = _parse_pi_model_option(raw)
        if option is None or option.id in seen:
            continue
        seen.add(option.id)
        options.append(option)
    options.sort(
        key=lambda option: PI_MODEL_TIER_ORDER.get(
            option.model, len(PI_MODEL_TIER_ORDER)
        )
    )
    return options


def resolve_pi_model_override(model_id: str | None) -> PiModelOverride | None:
    if model_id is None or not model_id.strip():
        return None

    stripped = model_id.strip()
    for option in pi_model_options():
        if option.id == stripped:
            return PiModelOverride(provider=option.provider, model=option.model)

    allowed = ", ".join(option.id for option in pi_model_options())
    raise InvalidPiModelError(
        f"Unsupported Pi model {stripped!r}. Allowed models: {allowed}"
    )


def pi_models_response() -> PiModelsResponse:
    return PiModelsResponse(
        default_model=_model_id(settings.pi_model_provider, settings.pi_model),
        agent_runtime_enabled=settings.agent_runtime_enabled,
        models=pi_model_options(),
    )
