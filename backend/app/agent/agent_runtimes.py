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


class InvalidAgentRuntimeError(ValueError):
    """Raised when a requested agent runtime is unknown or disabled."""


def agent_runtime_options() -> list[AgentRuntimeOption]:
    return [
        AgentRuntimeOption(
            id=HERMES_RUNTIME_ID,
            label="Hermes",
            enabled=settings.agent_runtime_enabled,
            description="Default Clerk agent with MCP tool surface.",
        ),
        AgentRuntimeOption(
            id=PI_RUNTIME_ID,
            label="Pi",
            enabled=settings.agent_runtime_enabled and settings.pi_runtime_enabled,
            description="Pi coding agent with retrieval-only MCP tools.",
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
