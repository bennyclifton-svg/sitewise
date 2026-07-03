import asyncio
import contextlib

from app.agent.concurrency import AgentTurnAlreadyRunning, AgentTurnRegistry
from tests.conftest import run_async


async def _scope_blocks_until_previous_turn_releases() -> bool:
    registry = AgentTurnRegistry(max_concurrent=1)
    entered_second = asyncio.Event()

    async with registry.turn_scope("turn-1", thread_id="thread-1"):
        second = asyncio.create_task(
            _enter_turn(registry, "turn-2", "thread-2", entered_second)
        )
        await asyncio.sleep(0.02)
        blocked = not entered_second.is_set()

    await asyncio.wait_for(second, timeout=0.1)
    return blocked and entered_second.is_set()


async def _enter_turn(
    registry: AgentTurnRegistry,
    turn_id: str,
    thread_id: str,
    entered: asyncio.Event,
) -> None:
    async with registry.turn_scope(turn_id, thread_id=thread_id):
        entered.set()


def test_turn_scope_blocks_until_previous_turn_releases() -> None:
    assert run_async(_scope_blocks_until_previous_turn_releases())


async def _cancel_by_thread_releases_slot() -> bool:
    registry = AgentTurnRegistry(max_concurrent=1)
    ready = asyncio.Event()

    async def worker() -> None:
        async with registry.turn_scope("turn-1", thread_id="thread-1"):
            ready.set()
            await asyncio.sleep(60)

    task = asyncio.create_task(worker())
    await ready.wait()

    cancelled = await registry.cancel("thread-1")
    with contextlib.suppress(asyncio.CancelledError):
        await task

    async with asyncio.timeout(0.1):
        async with registry.turn_scope("turn-2", thread_id="thread-2"):
            return cancelled and not await registry.cancel("thread-1")


def test_cancel_by_thread_releases_slot() -> None:
    assert run_async(_cancel_by_thread_releases_slot())


async def _cancel_by_turn_id() -> bool:
    registry = AgentTurnRegistry(max_concurrent=1)
    ready = asyncio.Event()

    async def worker() -> None:
        async with registry.turn_scope("turn-1", thread_id="thread-1"):
            ready.set()
            await asyncio.sleep(60)

    task = asyncio.create_task(worker())
    await ready.wait()

    cancelled = await registry.cancel("turn-1")
    with contextlib.suppress(asyncio.CancelledError):
        await task
    return cancelled


def test_cancel_by_turn_id() -> None:
    assert run_async(_cancel_by_turn_id())


async def _duplicate_thread_is_rejected() -> None:
    registry = AgentTurnRegistry(max_concurrent=2)
    async with registry.turn_scope("turn-1", thread_id="thread-1"):
        try:
            async with registry.turn_scope("turn-2", thread_id="thread-1"):
                pass
        except AgentTurnAlreadyRunning:
            return
    raise AssertionError("duplicate thread was accepted")


def test_duplicate_thread_is_rejected() -> None:
    run_async(_duplicate_thread_is_rejected())
