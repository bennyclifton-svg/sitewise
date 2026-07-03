import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from app.config import settings


class AgentTurnAlreadyRunning(RuntimeError):
    """Raised when a turn or thread already has a registered agent task."""


class AgentTurnRegistry:
    def __init__(self, *, max_concurrent: int) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()
        self._tasks_by_turn_id: dict[str, asyncio.Task[Any]] = {}
        self._turn_ids_by_thread_id: dict[str, str] = {}

    @asynccontextmanager
    async def turn_scope(
        self,
        turn_id: str,
        *,
        thread_id: str | None = None,
        task: asyncio.Task[Any] | None = None,
    ) -> AsyncIterator[None]:
        await self._semaphore.acquire()
        registered = False
        try:
            await self.register(
                turn_id,
                task or _current_task(),
                thread_id=thread_id,
            )
            registered = True
            yield
        finally:
            if registered:
                await self.unregister(turn_id)
            self._semaphore.release()

    async def register(
        self,
        turn_id: str,
        task: asyncio.Task[Any],
        *,
        thread_id: str | None = None,
    ) -> None:
        async with self._lock:
            if turn_id in self._tasks_by_turn_id:
                raise AgentTurnAlreadyRunning(f"agent turn is already running: {turn_id}")
            if thread_id is not None and thread_id in self._turn_ids_by_thread_id:
                raise AgentTurnAlreadyRunning(f"agent thread is already running: {thread_id}")

            self._tasks_by_turn_id[turn_id] = task
            if thread_id is not None:
                self._turn_ids_by_thread_id[thread_id] = turn_id

    async def unregister(self, turn_id: str) -> None:
        async with self._lock:
            self._tasks_by_turn_id.pop(turn_id, None)
            for thread_id, mapped_turn_id in list(self._turn_ids_by_thread_id.items()):
                if mapped_turn_id == turn_id:
                    self._turn_ids_by_thread_id.pop(thread_id, None)

    async def cancel(self, key: str) -> bool:
        async with self._lock:
            turn_id = self._turn_ids_by_thread_id.get(key, key)
            task = self._tasks_by_turn_id.get(turn_id)

        if task is None:
            return False

        task.cancel()
        return True


def _current_task() -> asyncio.Task[Any]:
    task = asyncio.current_task()
    if task is None:
        raise RuntimeError("agent turn registry requires an active asyncio task")
    return task


agent_turn_registry = AgentTurnRegistry(max_concurrent=settings.agent_max_concurrent_turns)
