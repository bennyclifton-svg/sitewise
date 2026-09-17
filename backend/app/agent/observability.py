"""Content-free timing context shared by MCP calls and provider clients."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class ToolTrace:
    id: uuid.UUID
    turn_id: uuid.UUID
    tool: str
    providers: list[dict] = field(default_factory=list)


current_tool_trace: ContextVar[ToolTrace | None] = ContextVar(
    "tool_trace", default=None
)
current_turn_id: ContextVar[str | None] = ContextVar("agent_turn_id", default=None)


@asynccontextmanager
async def provider_span(provider: str, operation: str):
    started = time.perf_counter()
    error_type = None
    try:
        yield
    except BaseException as exc:
        error_type = type(exc).__name__
        raise
    finally:
        trace = current_tool_trace.get()
        if trace is not None:
            trace.providers.append(
                {
                    "provider": provider,
                    "operation": operation,
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                    "error_type": error_type,
                }
            )
