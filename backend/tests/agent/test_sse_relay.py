import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from app.agent.sse_relay import relay_agent_turn
from tests.conftest import run_async


def _payload(event: str) -> dict[str, Any] | str:
    data = event.removeprefix("data: ").strip()
    if data == "[DONE]":
        return data
    return json.loads(data)


async def _collect(
    chunks: AsyncIterator[str],
    *,
    status: AsyncIterator[dict[str, Any] | str] | None = None,
) -> list[str]:
    return [event async for event in relay_agent_turn(chunks, status=status)]


async def _text_chunks() -> AsyncIterator[str]:
    yield "Hello"
    yield " world"


def test_relay_agent_turn_emits_ai_sdk_event_order() -> None:
    events = run_async(_collect(_text_chunks()))
    payloads = [_payload(event) for event in events]

    assert [payload["type"] if isinstance(payload, dict) else payload for payload in payloads] == [
        "start",
        "text-start",
        "text-delta",
        "text-delta",
        "text-end",
        "finish",
        "[DONE]",
    ]
    assert payloads[2]["delta"] == "Hello"
    assert payloads[3]["delta"] == " world"


async def _slow_text_chunk() -> AsyncIterator[str]:
    await asyncio.sleep(0.02)
    yield "Done"


async def _tool_status() -> AsyncIterator[dict[str, Any] | str]:
    yield {
        "message": "Searching project documents",
        "kind": "tool",
        "tool": "search_project_documents",
        "state": "running",
    }


def test_relay_agent_turn_interleaves_structured_status_events() -> None:
    events = run_async(_collect(_slow_text_chunk(), status=_tool_status()))
    payloads = [_payload(event) for event in events]
    status_payload = next(
        payload
        for payload in payloads
        if isinstance(payload, dict) and payload["type"] == "data-clerk-status"
    )

    assert status_payload["data"] == {
        "message": "Searching project documents",
        "kind": "tool",
        "tool": "search_project_documents",
        "state": "running",
    }
    assert payloads.index(status_payload) < next(
        index
        for index, payload in enumerate(payloads)
        if isinstance(payload, dict) and payload["type"] == "text-delta"
    )


async def _failing_chunks() -> AsyncIterator[str]:
    yield "Partial"
    raise RuntimeError("Hermes stopped")


def test_relay_agent_turn_emits_error_and_done_on_failure() -> None:
    events = run_async(_collect(_failing_chunks()))
    payloads = [_payload(event) for event in events]

    assert [payload["type"] if isinstance(payload, dict) else payload for payload in payloads] == [
        "start",
        "text-start",
        "text-delta",
        "error",
        "[DONE]",
    ]
    assert payloads[-1] == "[DONE]"
    assert "Hermes stopped" in payloads[-2]["errorText"]
