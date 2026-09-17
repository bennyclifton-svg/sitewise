"""Postgres event journal and conservative recovery; never replay tool mutations."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, text

from app.chat.streaming import _sse
from app.database.agent_event import AgentToolCall, AgentTurnEvent
from app.database.agent_turn import AgentTurn
from app.database.chat_message import ChatMessage
from app.database.session import get_session_factory

RECOVERY_MESSAGE = (
    "This turn was interrupted by a server restart or execution failure. "
    "Saved changes were kept. Review them before sending another request."
)


class PostgresTurnJournal:
    async def _append(self, session, turn_id: uuid.UUID, events: list[str]) -> None:
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"agent-events:{turn_id}"},
        )
        last = await session.scalar(
            select(AgentTurnEvent)
            .where(AgentTurnEvent.turn_id == turn_id)
            .order_by(AgentTurnEvent.sequence.desc())
            .limit(1)
        )
        if last is not None and last.terminal:
            return
        sequence = last.sequence if last is not None else 0
        for event in events:
            sequence += 1
            session.add(
                AgentTurnEvent(
                    turn_id=turn_id,
                    sequence=sequence,
                    event=event,
                    terminal=event.strip() == "data: [DONE]",
                )
            )

    async def append(self, turn_id: uuid.UUID, events: list[str]) -> None:
        async with get_session_factory()() as session:
            await self._append(session, turn_id, events)
            await session.commit()

    async def read(
        self, turn_id: uuid.UUID, after: int = 0
    ) -> tuple[list[tuple[int, str]], bool]:
        async with get_session_factory()() as session:
            rows = (
                await session.scalars(
                    select(AgentTurnEvent)
                    .where(
                        AgentTurnEvent.turn_id == turn_id,
                        AgentTurnEvent.sequence > after,
                    )
                    .order_by(AgentTurnEvent.sequence)
                    .limit(256)
                )
            ).all()
            latest = await session.scalar(
                select(AgentTurnEvent)
                .where(AgentTurnEvent.turn_id == turn_id)
                .order_by(AgentTurnEvent.sequence.desc())
                .limit(1)
            )
            consumed = rows[-1].sequence if rows else after
            # The writer may commit between the two SELECTs. Do not close a
            # reader before it has actually received that terminal sequence.
            terminal = latest is not None and latest.terminal and latest.sequence <= consumed
            return [(row.sequence, row.event) for row in rows], bool(terminal)

    async def reconcile(self) -> None:
        # Single API process only: run before accepting traffic. A crashed Pi
        # may have committed; revoke its capability instead of rerunning it.
        async with get_session_factory()() as session:
            unfinished_journal = (
                select(AgentTurnEvent.turn_id)
                .group_by(AgentTurnEvent.turn_id)
                .having(~func.bool_or(AgentTurnEvent.terminal))
            )
            unfinished_tools = select(AgentToolCall.turn_id).where(
                AgentToolCall.outcome == "running"
            )
            ids = (
                await session.scalars(
                    select(AgentTurn.id).where(
                        (AgentTurn.state == "active")
                        | AgentTurn.id.in_(unfinished_journal)
                        | AgentTurn.id.in_(unfinished_tools)
                    )
                )
            ).all()
        for turn_id in ids:
            await self.repair(turn_id)

    async def repair(self, turn_id: uuid.UUID) -> None:
        async with get_session_factory()() as session:
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": f"agent-turn:{turn_id}"},
            )
            turn = await session.get(AgentTurn, turn_id, with_for_update=True)
            if turn is None:
                return
            terminal = await session.scalar(
                select(AgentTurnEvent.sequence)
                .where(AgentTurnEvent.turn_id == turn_id, AgentTurnEvent.terminal)
                .limit(1)
            )
            if terminal is not None:
                calls = (
                    await session.scalars(
                        select(AgentToolCall).where(
                            AgentToolCall.turn_id == turn_id,
                            AgentToolCall.outcome == "running",
                        )
                    )
                ).all()
                for call in calls:
                    call.outcome = "interrupted"
                await session.commit()
                return
            saved = await session.scalar(
                select(ChatMessage)
                .where(
                    ChatMessage.thread_id == turn.thread_id,
                    ChatMessage.role == "assistant",
                    ChatMessage.message_data["agent"]["turnId"].astext == str(turn_id),
                )
                .limit(1)
            )
            rows = (
                await session.scalars(
                    select(AgentTurnEvent)
                    .where(AgentTurnEvent.turn_id == turn_id)
                    .order_by(AgentTurnEvent.sequence)
                )
            ).all()
            if turn.state == "completed" and saved is not None:
                # Commit succeeded but the process died before journalling finish.
                events = _completed_events(
                    turn_id, [row.event for row in rows], saved.content
                )
            else:
                turn.state = "revoked"
                if turn.status not in {"cancelled", "not_started"}:
                    turn.status = "interrupted"
                turn.revoked_at = datetime.now(UTC)
                turn.completed_at = datetime.now(UTC)
                if saved is None and turn.thread_id is not None:
                    partial = _partial_text([row.event for row in rows]).rstrip()
                    session.add(
                        ChatMessage(
                            thread_id=turn.thread_id,
                            role="assistant",
                            content=f"{partial}\n\n{RECOVERY_MESSAGE}"
                            if partial
                            else RECOVERY_MESSAGE,
                            message_data={
                                "agent": {"runtime": "pi", "turnId": str(turn_id)}
                            },
                        )
                    )
                events = [
                    _sse({"type": "error", "errorText": RECOVERY_MESSAGE}),
                    _sse("[DONE]"),
                ]
            calls = (
                await session.scalars(
                    select(AgentToolCall).where(
                        AgentToolCall.turn_id == turn_id,
                        AgentToolCall.outcome == "running",
                    )
                )
            ).all()
            for call in calls:
                call.outcome = "interrupted"
            await self._append(session, turn_id, events)
            await session.commit()


def _partial_text(events: list[str]) -> str:
    parts = []
    for event in events:
        for line in event.splitlines():
            if not line.startswith("data: {"):
                continue
            payload = json.loads(line[6:])
            if payload.get("type") == "text-delta":
                parts.append(payload.get("delta", ""))
    return "".join(parts)


def _completed_events(turn_id: uuid.UUID, events: list[str], content: str) -> list[str]:
    payloads = [
        json.loads(line[6:])
        for event in events
        for line in event.splitlines()
        if line.startswith("data: {")
    ]
    recovered = []
    if not any(payload.get("type") == "start" for payload in payloads):
        recovered.append(_sse({"type": "start", "messageId": f"msg_{turn_id.hex}"}))
    text_id = next(
        (payload["id"] for payload in payloads if payload.get("type") == "text-start"),
        None,
    )
    if text_id is None:
        text_id = f"text_{turn_id.hex}"
        recovered.append(_sse({"type": "text-start", "id": text_id}))
    partial = _partial_text(events)
    if content.startswith(partial) and content[len(partial) :]:
        recovered.append(
            _sse(
                {"type": "text-delta", "id": text_id, "delta": content[len(partial) :]}
            )
        )
    if not any(payload.get("type") == "text-end" for payload in payloads):
        recovered.append(_sse({"type": "text-end", "id": text_id}))
    recovered.extend([_sse({"type": "finish"}), _sse("[DONE]")])
    return recovered
