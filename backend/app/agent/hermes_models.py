"""Hermes model selection for agent chat turns."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.agent.agent_runtimes import (
    AgentRuntimeOption,
    agent_runtime_options,
    default_agent_runtime,
)
from app.config import settings

HERMES_DEFAULT_MODEL_ID = "__hermes_config__"


class HermesModelOption(BaseModel):
    id: str
    label: str
    is_default: bool = False
    provider: str | None = None
    model: str | None = None


class HermesModelsResponse(BaseModel):
    default_model: str
    default_runtime: str = "hermes"
    agent_runtime_enabled: bool
    models: list[HermesModelOption] = Field(default_factory=list)
    runtimes: list[AgentRuntimeOption] = Field(default_factory=list)


class InvalidHermesModelError(ValueError):
    """Raised when a requested Hermes model option is not allowlisted."""


@dataclass(frozen=True)
class HermesModelOverride:
    provider: str
    model: str


def _model_id(provider: str, model: str) -> str:
    return f"{provider}:{model}"


def _parse_option(raw: str) -> HermesModelOption | None:
    parts = [part.strip() for part in raw.split(":", 2)]
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    provider, model = parts[0], parts[1]
    label = parts[2] if len(parts) == 3 and parts[2] else f"{model} ({provider})"
    return HermesModelOption(
        id=_model_id(provider, model),
        label=label,
        provider=provider,
        model=model,
    )


def hermes_model_options() -> list[HermesModelOption]:
    options = [
        HermesModelOption(
            id=HERMES_DEFAULT_MODEL_ID,
            label="Hermes default",
            is_default=True,
        )
    ]
    seen = {HERMES_DEFAULT_MODEL_ID}
    for raw in settings.hermes_model_options.split(","):
        option = _parse_option(raw)
        if option is None or option.id in seen:
            continue
        seen.add(option.id)
        options.append(option)
    return options


def hermes_models_response() -> HermesModelsResponse:
    return HermesModelsResponse(
        default_model=HERMES_DEFAULT_MODEL_ID,
        default_runtime=default_agent_runtime(),
        agent_runtime_enabled=settings.agent_runtime_enabled,
        models=hermes_model_options(),
        runtimes=agent_runtime_options(),
    )


def resolve_hermes_model_override(
    model_id: str | None,
) -> HermesModelOverride | None:
    if model_id is None or not model_id.strip():
        return None

    stripped = model_id.strip()
    if stripped == HERMES_DEFAULT_MODEL_ID:
        return None

    for option in hermes_model_options():
        if option.id != stripped:
            continue
        if option.provider is None or option.model is None:
            return None
        return HermesModelOverride(provider=option.provider, model=option.model)

    allowed = ", ".join(option.id for option in hermes_model_options())
    raise InvalidHermesModelError(
        f"Unsupported Hermes model {stripped!r}. Allowed models: {allowed}"
    )
