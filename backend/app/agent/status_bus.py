import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any


AgentStatusPayload = dict[str, Any]


class AgentTurnStatusBus:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._queues_by_turn_id: dict[str, set[asyncio.Queue[AgentStatusPayload]]] = {}

    @asynccontextmanager
    async def subscribe(self, turn_id: str) -> AsyncIterator[AsyncIterator[AgentStatusPayload]]:
        queue: asyncio.Queue[AgentStatusPayload] = asyncio.Queue()
        async with self._lock:
            self._queues_by_turn_id.setdefault(turn_id, set()).add(queue)
        try:
            yield self._stream(queue)
        finally:
            async with self._lock:
                queues = self._queues_by_turn_id.get(turn_id)
                if queues is not None:
                    queues.discard(queue)
                    if not queues:
                        self._queues_by_turn_id.pop(turn_id, None)

    async def publish(
        self,
        turn_id: str | None,
        *,
        message: str,
        kind: str = "tool",
        tool: str | None = None,
        state: str | None = None,
        **metadata: Any,
    ) -> None:
        if turn_id is None:
            return

        payload: AgentStatusPayload = {
            "message": message,
            "kind": kind,
            "tool": tool,
            "state": state,
        }
        payload.update(metadata)
        payload = {key: value for key, value in payload.items() if value is not None}

        async with self._lock:
            queues = list(self._queues_by_turn_id.get(turn_id, ()))

        for queue in queues:
            queue.put_nowait(payload)

    async def _stream(
        self,
        queue: asyncio.Queue[AgentStatusPayload],
    ) -> AsyncIterator[AgentStatusPayload]:
        while True:
            yield await queue.get()


agent_turn_status_bus = AgentTurnStatusBus()
