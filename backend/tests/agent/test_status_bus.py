import asyncio

from app.agent.status_bus import AgentTurnStatusBus
from tests.conftest import run_async


async def _publish_to_subscriber() -> dict:
    bus = AgentTurnStatusBus()
    async with bus.subscribe("turn-1") as statuses:
        await bus.publish(
            "turn-1",
            message="Searching project documents",
            tool="search_documents",
            state="running",
        )
        return await asyncio.wait_for(anext(statuses), timeout=0.1)


def test_publish_to_subscriber() -> None:
    assert run_async(_publish_to_subscriber()) == {
        "message": "Searching project documents",
        "kind": "tool",
        "tool": "search_documents",
        "state": "running",
    }


async def _ignore_turns_without_subscribers() -> None:
    bus = AgentTurnStatusBus()
    await bus.publish(
        "turn-1",
        message="No subscriber",
        tool="search_documents",
        state="running",
    )


def test_publish_without_subscriber_is_noop() -> None:
    run_async(_ignore_turns_without_subscribers())
