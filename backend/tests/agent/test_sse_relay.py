import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

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
        "data-clerk-status",
        "text-delta",
        "text-delta",
        "text-end",
        "finish",
        "[DONE]",
    ]
    assert payloads[2]["data"]["message"] == "Reading your request…"
    assert payloads[3]["delta"] == "Hello"
    assert payloads[4]["delta"] == " world"


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
    status_payloads = [
        payload
        for payload in payloads
        if isinstance(payload, dict) and payload["type"] == "data-clerk-status"
    ]

    assert status_payloads[0]["data"] == {"message": "Reading your request…"}
    status_payload = status_payloads[1]
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


async def _open_status_stream() -> AsyncIterator[dict[str, Any] | str]:
    yield "Still working"
    await asyncio.sleep(60)


def test_relay_agent_turn_finishes_without_waiting_for_status_stream_end() -> None:
    events = run_async(_collect(_text_chunks(), status=_open_status_stream()))
    payloads = [_payload(event) for event in events]

    assert payloads[-2]["type"] == "finish"
    assert payloads[-1] == "[DONE]"


async def _timeout_chunks() -> AsyncIterator[str]:
    from app.agent.pi_process import PiTurnTimeout

    raise PiTurnTimeout("Pi turn timed out")
    yield "unreachable"


def test_relay_agent_turn_reraises_pi_turn_errors() -> None:
    from app.agent.pi_process import PiTurnTimeout

    with pytest.raises(PiTurnTimeout):
        run_async(_collect(_timeout_chunks()))


async def _failing_chunks() -> AsyncIterator[str]:
    yield "Partial"
    raise RuntimeError("Pi stopped with Bearer ch03-sse-chunk-provider-token")


def test_relay_agent_turn_emits_error_and_done_on_failure() -> None:
    events = run_async(_collect(_failing_chunks()))
    payloads = [_payload(event) for event in events]

    assert [payload["type"] if isinstance(payload, dict) else payload for payload in payloads] == [
        "start",
        "text-start",
        "data-clerk-status",
        "text-delta",
        "error",
        "[DONE]",
    ]
    assert payloads[-1] == "[DONE]"
    assert payloads[-2]["errorText"] == "Agent turn failed"
    assert "ch03-sse-chunk-provider-token" not in str(payloads)


async def _failing_status() -> AsyncIterator[dict[str, Any] | str]:
    raise RuntimeError("status failed with token=ch03-sse-status-provider-token")
    yield "unreachable"


def test_relay_agent_turn_masks_status_stream_failure() -> None:
    events = run_async(_collect(_slow_text_chunk(), status=_failing_status()))
    payloads = [_payload(event) for event in events]

    assert [
        payload["type"] if isinstance(payload, dict) else payload
        for payload in payloads
    ] == ["start", "text-start", "data-clerk-status", "error", "[DONE]"]
    assert payloads[-2]["errorText"] == "Agent status stream failed"
    assert "ch03-sse-status-provider-token" not in str(payloads)
