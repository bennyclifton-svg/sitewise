"""Agent runtime selection (Hermes vs Pi) for project chat turns."""

from __future__ import annotations

from pydantic import BaseModel

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


class InvalidAgentRuntimeError(ValueError):
    """Raised when a requested agent runtime is unknown or disabled."""


def agent_runtime_options() -> list[AgentRuntimeOption]:
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
            model_label=f"{settings.pi_model} ({settings.pi_model_provider})",
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
