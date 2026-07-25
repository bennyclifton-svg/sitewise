"""Agent runtime selection (Hermes vs Pi) for project chat turns."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.config import settings

HERMES_RUNTIME_ID = "hermes"
PI_RUNTIME_ID = "pi"


class AgentRuntimeOption(BaseModel):
    id: str
    label: str
    enabled: bool = True
    description: str | None = None
    provider: str | None = None
    model: str | None = None
    model_label: str | None = None
    default_model: str | None = None
    model_options: list["AgentRuntimeModelOption"] = Field(default_factory=list)


class AgentRuntimeModelOption(BaseModel):
    id: str
    label: str
    is_default: bool = False
    provider: str
    model: str


class InvalidAgentRuntimeError(ValueError):
    """Raised when a requested agent runtime is unknown or disabled."""


class InvalidPiModelError(ValueError):
    """Raised when a requested Pi model is not allowlisted."""


@dataclass(frozen=True)
class PiModelOverride:
    provider: str
    model: str


def _pi_model_id(provider: str, model: str) -> str:
    return f"{provider}:{model}"


def _parse_pi_model_option(raw: str) -> AgentRuntimeModelOption | None:
    parts = [part.strip() for part in raw.split(":", 2)]
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return None
    provider, model = parts[0], parts[1]
    label = parts[2] if len(parts) == 3 and parts[2] else model
    return AgentRuntimeModelOption(
        id=_pi_model_id(provider, model),
        label=label,
        is_default=(
            provider == settings.pi_model_provider and model == settings.pi_model
        ),
        provider=provider,
        model=model,
    )


def pi_model_options() -> list[AgentRuntimeModelOption]:
    options: list[AgentRuntimeModelOption] = []
    seen: set[str] = set()
    for raw in settings.pi_model_options.split(","):
        option = _parse_pi_model_option(raw)
        if option is None or option.id in seen:
            continue
        seen.add(option.id)
        options.append(option)
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


def agent_runtime_options() -> list[AgentRuntimeOption]:
    pi_models = pi_model_options()
    pi_default_model = _pi_model_id(settings.pi_model_provider, settings.pi_model)
    pi_label = next(
        (option.label for option in pi_models if option.id == pi_default_model),
        f"{settings.pi_model} ({settings.pi_model_provider})",
    )
    return [
        AgentRuntimeOption(
            id=HERMES_RUNTIME_ID,
            label="Hermes",
            enabled=settings.agent_runtime_enabled,
            description="Default Clerk agent with MCP tool surface.",
            provider=settings.hermes_model_provider,
            model=settings.hermes_model,
            model_label=f"{settings.hermes_model} ({settings.hermes_model_provider})",
        ),
        AgentRuntimeOption(
            id=PI_RUNTIME_ID,
            label="Pi",
            enabled=settings.agent_runtime_enabled and settings.pi_runtime_enabled,
            description="Pi coding agent with file-based prompts for mutation turns.",
            provider=settings.pi_model_provider,
            model=settings.pi_model,
            model_label=pi_label,
            default_model=pi_default_model,
            model_options=pi_models,
        ),
    ]


def default_agent_runtime() -> str:
    return HERMES_RUNTIME_ID


def resolve_agent_runtime(runtime_id: str | None) -> str:
    stripped = (runtime_id or default_agent_runtime()).strip().lower()
    for option in agent_runtime_options():
        if option.id != stripped:
            continue
        if not option.enabled:
            raise InvalidAgentRuntimeError(
                f"Agent runtime {stripped!r} is not enabled on this server."
            )
        return option.id
    allowed = ", ".join(option.id for option in agent_runtime_options())
    raise InvalidAgentRuntimeError(
        f"Unsupported agent runtime {stripped!r}. Allowed runtimes: {allowed}"
    )


def resolve_agent_runtime_for_turn(
    runtime_id: str | None,
    *,
    needs_mutation_tools: bool,
) -> str:
    """Resolve runtime, routing Hermes mutation turns to Pi when required.

    Hermes still places prompt text on argv. Until a non-argv transport is
    verified, mutation tools stay blocked for Hermes turns. Profile enrichment,
    profile updates, and artefact/workflow writes therefore use Pi when it is
    enabled.
    """
    runtime = resolve_agent_runtime(runtime_id)
    if (
        not needs_mutation_tools
        or runtime != HERMES_RUNTIME_ID
        or settings.hermes_mutations_enabled
    ):
        return runtime

    for option in agent_runtime_options():
        if option.id == PI_RUNTIME_ID and option.enabled:
            return PI_RUNTIME_ID

    raise InvalidAgentRuntimeError(
        "Hermes mutations are disabled until a non-argv prompt transport is "
        "verified, and the Pi runtime is not enabled for mutation turns."
    )
