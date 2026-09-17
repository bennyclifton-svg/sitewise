"""Own Pi execution independently of HTTP readers; publish only committed events."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Protocol

from app.logging import get_logger
from app.agent.observability import current_turn_id

log = get_logger(__name__)


class TurnJournal(Protocol):
    async def append(self, turn_id: uuid.UUID, events: list[str]) -> None: ...
    async def read(
        self, turn_id: uuid.UUID, after: int = 0
    ) -> tuple[list[tuple[int, str]], bool]: ...
    async def repair(self, turn_id: uuid.UUID) -> None: ...


class TurnSupervisor:
    def __init__(self, journal: TurnJournal, *, flush_seconds: float = 0.1) -> None:
        self.journal = journal
        self.flush_seconds = flush_seconds
        self._tasks: dict[uuid.UUID, asyncio.Task[None]] = {}

    def running(self, turn_id: uuid.UUID) -> bool:
        task = self._tasks.get(turn_id)
        return task is not None and not task.done()

    def start(self, turn_id: uuid.UUID, source: AsyncIterator[str]) -> None:
        if self.running(turn_id):
            raise ValueError("Turn already supervised")
        task = asyncio.create_task(
            self._run(turn_id, source), name=f"pi-turn:{turn_id}"
        )
        self._tasks[turn_id] = task

        def forget(_task):
            if self._tasks.get(turn_id) is _task:
                self._tasks.pop(turn_id, None)

        task.add_done_callback(forget)

    def cancel(self, turn_id: uuid.UUID) -> bool:
        task = self._tasks.get(turn_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    async def close(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run(self, turn_id: uuid.UUID, source: AsyncIterator[str]) -> None:
        context_token = current_turn_id.set(str(turn_id))
        queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=128)

        async def produce() -> None:
            async with aclosing(source):
                async for event in source:
                    if not event.startswith(":"):
                        await queue.put(event)
            await queue.put(None)

        async def write() -> None:
            batch: list[str] = []
            deadline = 0.0
            while True:
                try:
                    event = (
                        await asyncio.wait_for(
                            queue.get(),
                            timeout=max(
                                0, deadline - asyncio.get_running_loop().time()
                            ),
                        )
                        if batch
                        else await queue.get()
                    )
                except TimeoutError:
                    if batch:
                        await self.journal.append(turn_id, batch)
                        batch = []
                    continue
                if event is None:
                    if batch:
                        await self.journal.append(turn_id, batch)
                    return
                if not batch:
                    deadline = asyncio.get_running_loop().time() + self.flush_seconds
                batch.append(event)
                if len(batch) >= 64 or event.strip() == "data: [DONE]":
                    await self.journal.append(turn_id, batch)
                    batch = []

        try:
            async with asyncio.TaskGroup() as group:
                group.create_task(produce())
                group.create_task(write())
        except BaseException as exc:
            # A failed journal must stop the producer, including a pending tool
            # call. Never continue mutations with progress we cannot recover.
            log.warning(
                "agent_supervisor_stopped",
                turn_id=str(turn_id),
                error_type=type(exc).__name__,
            )
        finally:
            try:
                await self.journal.repair(turn_id)
            except Exception as exc:
                log.error(
                    "agent_reconciliation_failed",
                    turn_id=str(turn_id),
                    error_type=type(exc).__name__,
                )
            finally:
                current_turn_id.reset(context_token)

    async def stream(self, turn_id: uuid.UUID, *, after: int = 0) -> AsyncIterator[str]:
        heartbeat = asyncio.get_running_loop().time()
        while True:
            events, terminal = await self.journal.read(turn_id, after)
            for sequence, event in events:
                after = sequence
                yield f"id: {sequence}\n{event}"
            if terminal and not events:
                return
            if events:
                continue
            now = asyncio.get_running_loop().time()
            if now - heartbeat >= 15:
                heartbeat = now
                yield ": keep-alive\n\n"
            await asyncio.sleep(0.1)
