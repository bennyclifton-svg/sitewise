"""One correlated boundary for every MCP tool, without recording arguments/results."""

from __future__ import annotations

import asyncio
import time
import uuid

from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware
from sqlalchemy import select, update

from app.agent.observability import ToolTrace, current_tool_trace
from app.agent.status_bus import agent_turn_status_bus
from app.database.agent_event import AgentToolCall
from app.database.session import get_session_factory
from app.logging import get_logger
from app.mcp_bridge.tokens import TurnTokenError, verify_turn_token
import app.mcp_bridge.tool_commits  # noqa: F401 — register transaction receipts

log = get_logger(__name__)


async def tool_trace_statuses(turn_id: uuid.UUID) -> list[dict]:
    async with get_session_factory()() as session:
        calls = (
            await session.scalars(
                select(AgentToolCall)
                .where(
                    AgentToolCall.turn_id == turn_id,
                )
                .order_by(AgentToolCall.created_at, AgentToolCall.id)
            )
        ).all()
        return [
            {
                "kind": "tool",
                "tool": call.tool,
                "callId": str(call.id),
                "state": "done" if call.outcome == "succeeded" else "error",
                "outcome": call.outcome,
                "durationMs": call.duration_ms,
                "committedRevisions": call.committed_revisions,
            }
            for call in calls
        ]


class ToolTraceStore:
    async def start(self, trace: ToolTrace) -> None:
        async with get_session_factory()() as session:
            session.add(
                AgentToolCall(
                    id=trace.id,
                    turn_id=trace.turn_id,
                    tool=trace.tool,
                    outcome="running",
                    committed_revisions=[],
                    providers=[],
                )
            )
            await session.commit()

    async def finish(
        self,
        trace: ToolTrace,
        *,
        outcome: str,
        duration_ms: int,
        error_type: str | None,
    ) -> None:
        async with get_session_factory()() as session:
            await session.execute(
                update(AgentToolCall)
                .where(AgentToolCall.id == trace.id)
                .values(
                    outcome=outcome,
                    duration_ms=duration_ms,
                    error_type=error_type,
                    providers=trace.providers,
                )
            )
            await session.commit()


class ToolTracingMiddleware(Middleware):
    def __init__(self, store=None) -> None:
        self.store = store or ToolTraceStore()

    async def on_call_tool(self, context, call_next):
        headers = get_http_headers()
        bearer = headers.get("authorization", "")
        try:
            claims = (
                verify_turn_token(bearer[7:])
                if bearer.lower().startswith("bearer ")
                else None
            )
        except (TurnTokenError, ValueError, KeyError):
            claims = None
        arguments = context.message.arguments or {}
        if (
            claims is None
            or claims.turn_id is None
            or arguments.get("project_id") != str(claims.project_id)
        ):
            # The tool's existing authorization rejects these calls. Never
            # associate an unverified caller with another user's turn.
            return await call_next(context)
        trace = ToolTrace(uuid.uuid4(), claims.turn_id, context.message.name)
        await self.store.start(trace)
        token = current_tool_trace.set(trace)
        started = time.perf_counter()
        outcome, error_type = "succeeded", None
        await agent_turn_status_bus.publish(
            str(trace.turn_id),
            message=f"Running {trace.tool}",
            tool=trace.tool,
            state="running",
            callId=str(trace.id),
        )
        try:
            return await call_next(context)
        except BaseException as exc:
            outcome = (
                "cancelled" if isinstance(exc, asyncio.CancelledError) else "failed"
            )
            error_type = type(exc).__name__
            raise
        finally:
            current_tool_trace.reset(token)
            duration_ms = int((time.perf_counter() - started) * 1000)
            try:
                await self.store.finish(
                    trace,
                    outcome=outcome,
                    duration_ms=duration_ms,
                    error_type=error_type,
                )
            except Exception as exc:
                # A tool may already have committed. Keep its result and the
                # atomic commit receipt; do not turn telemetry failure into a retry.
                log.error(
                    "agent_tool_trace_save_failed",
                    turn_id=str(trace.turn_id),
                    call_id=str(trace.id),
                    error_type=type(exc).__name__,
                )
            log.info(
                "agent_tool_call",
                turn_id=str(trace.turn_id),
                call_id=str(trace.id),
                tool=trace.tool,
                duration_ms=duration_ms,
                outcome=outcome,
                error_type=error_type,
                providers=trace.providers,
            )
            await agent_turn_status_bus.publish(
                str(trace.turn_id),
                message=f"{trace.tool}: {outcome}",
                tool=trace.tool,
                state="done" if outcome == "succeeded" else "error",
                callId=str(trace.id),
                durationMs=duration_ms,
            )
