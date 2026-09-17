import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from typing import Any

from app.agent.pi_process import PiTurnError
from app.chat.streaming import _sse, clerk_status_event


StatusEvent = Mapping[str, Any] | str
HEARTBEAT_SECONDS = 15.0


def _status_event(payload: StatusEvent) -> str:
    if isinstance(payload, str):
        return clerk_status_event(payload)

    message = str(payload.get("message") or "Agent tool update")
    metadata = dict(payload)
    metadata.pop("message", None)
    return clerk_status_event(message, **metadata)


async def _next_item(iterator: AsyncIterator[Any]) -> Any:
    return await anext(iterator)


def _cancel_pending(*tasks: asyncio.Task[Any] | None) -> None:
    for task in tasks:
        if task is not None and not task.done():
            task.cancel()


async def _drain_cancelled(*tasks: asyncio.Task[Any] | None) -> None:
    await asyncio.gather(
        *(task for task in tasks if task is not None), return_exceptions=True,
    )


async def relay_agent_turn(
    chunks: AsyncIterator[str],
    *,
    status: AsyncIterator[StatusEvent] | None = None,
    on_complete: Callable[[], Awaitable[None]] | None = None,
) -> AsyncIterator[str]:
    message_id = f"msg_{uuid.uuid4().hex}"
    text_id = f"text_{uuid.uuid4().hex}"

    yield _sse({"type": "start", "messageId": message_id})
    yield _sse({"type": "text-start", "id": text_id})
    yield clerk_status_event("Reading your request…")

    chunk_task: asyncio.Task[str] | None = asyncio.create_task(_next_item(chunks))
    status_task: asyncio.Task[StatusEvent] | None = (
        asyncio.create_task(_next_item(status)) if status is not None else None
    )

    try:
        while chunk_task is not None:
            pending = {task for task in (chunk_task, status_task) if task is not None}
            done, _ = await asyncio.wait(
                pending, timeout=HEARTBEAT_SECONDS,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                # SSE comments keep quiet model/tool calls connected without
                # adding user-visible activity or cancelling the pending read.
                yield ": keep-alive\n\n"
                continue

            if status_task is not None and status_task in done:
                try:
                    status_payload = status_task.result()
                except StopAsyncIteration:
                    status_task = None
                except Exception as exc:
                    _cancel_pending(chunk_task)
                    raise PiTurnError(
                        f"Agent status stream failed ({type(exc).__name__})"
                    ) from exc
                else:
                    yield _status_event(status_payload)
                    status_task = asyncio.create_task(_next_item(status)) if status is not None else None

            if chunk_task is not None and chunk_task in done:
                try:
                    chunk = chunk_task.result()
                except StopAsyncIteration:
                    chunk_task = None
                except PiTurnError:
                    _cancel_pending(status_task)
                    raise
                except Exception as exc:
                    _cancel_pending(status_task)
                    raise PiTurnError(
                        f"Agent output stream failed ({type(exc).__name__})"
                    ) from exc
                else:
                    yield _sse({"type": "text-delta", "id": text_id, "delta": chunk})
                    chunk_task = asyncio.create_task(_next_item(chunks))

        _cancel_pending(status_task)
        await _drain_cancelled(status_task)
        status_task = None
        if on_complete is not None:
            try:
                await on_complete()
            except Exception as exc:
                raise PiTurnError(
                    f"Agent completion persistence failed ({type(exc).__name__})"
                ) from exc
        yield _sse({"type": "text-end", "id": text_id})
        yield _sse({"type": "finish"})
        yield _sse("[DONE]")
    finally:
        _cancel_pending(chunk_task, status_task)
        await _drain_cancelled(chunk_task, status_task)
