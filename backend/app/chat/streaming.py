import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from app.assistant.outputs import GroundedAnswer

StatusCallback = Callable[[str], Awaitable[None]]

STUB_RESPONSE = (
    "This is a stub assistant response from Clerk. "
    "Real retrieval and grounding will replace this in later phases."
)

STUB_CITATION: dict[str, Any] = {
    "sourceId": "stub-source-1",
    "title": "Stub procurement brief",
    "mediaType": "application/pdf",
    "excerpt": "Example cited passage for UI wiring.",
}


def _sse(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        return f"data: {payload}\n\n"
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"


def _source_type_media_type(source_type: str | None) -> str:
    if source_type == "doctrine":
        return "text/markdown"
    if source_type == "reference":
        return "text/markdown"
    return "application/pdf"


def _citation_provider_metadata(citation) -> dict[str, Any]:
    return {
        "clerk": {
            "chunkId": str(citation.chunk_id),
            "documentId": str(citation.document_id),
            "project": citation.project,
            "phase": citation.phase,
            "sourceType": citation.source_type,
            "pageOrSection": citation.page_or_section,
            "excerpt": citation.excerpt,
            "label": citation.label.value,
        }
    }


async def stream_grounded_answer(
    answer: GroundedAnswer,
    *,
    chunk_delay_s: float = 0.01,
) -> AsyncIterator[str]:
    message_id = f"msg_{uuid.uuid4().hex}"
    text_id = f"text_{uuid.uuid4().hex}"

    yield _sse({"type": "start", "messageId": message_id})
    yield _sse({"type": "text-start", "id": text_id})

    words = answer.answer.split(" ")
    for index, word in enumerate(words):
        delta = word if index == 0 else f" {word}"
        yield _sse({"type": "text-delta", "id": text_id, "delta": delta})
        if chunk_delay_s:
            await asyncio.sleep(chunk_delay_s)

    yield _sse({"type": "text-end", "id": text_id})

    for citation in answer.citations:
        yield _sse(
            {
                "type": "source-document",
                "sourceId": str(citation.chunk_id),
                "mediaType": _source_type_media_type(citation.source_type),
                "title": citation.filename,
                "filename": citation.filename,
                "providerMetadata": _citation_provider_metadata(citation),
            }
        )

    yield _sse({"type": "finish"})
    yield _sse("[DONE]")


async def stream_error(message: str) -> AsyncIterator[str]:
    yield _sse({"type": "error", "errorText": message})
    yield _sse("[DONE]")


def clerk_status_event(message: str) -> str:
    return _sse({"type": "data-clerk-status", "data": {"message": message}})


async def iter_chat_turn_with_status(
    *,
    run_turn: Callable[[StatusCallback | None], Awaitable[GroundedAnswer]],
) -> AsyncIterator[str | GroundedAnswer]:
    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

    async def on_status(message: str) -> None:
        await queue.put(("status", message))

    async def execute_turn() -> None:
        try:
            answer = await run_turn(on_status)
            await queue.put(("done", answer))
        except Exception as exc:
            await queue.put(("error", exc))

    asyncio.create_task(execute_turn())
    yield clerk_status_event("Received your question")

    while True:
        kind, payload = await queue.get()
        if kind == "status":
            yield clerk_status_event(str(payload))
        elif kind == "done":
            yield payload
            return
        if kind == "error":
            raise payload


async def stream_stub_assistant(
    *,
    response_text: str = STUB_RESPONSE,
    chunk_delay_s: float = 0.05,
) -> AsyncIterator[str]:
    message_id = f"msg_{uuid.uuid4().hex}"
    text_id = f"text_{uuid.uuid4().hex}"

    yield _sse({"type": "start", "messageId": message_id})
    yield _sse({"type": "text-start", "id": text_id})

    words = response_text.split(" ")
    for index, word in enumerate(words):
        delta = word if index == 0 else f" {word}"
        yield _sse({"type": "text-delta", "id": text_id, "delta": delta})
        await asyncio.sleep(chunk_delay_s)

    yield _sse({"type": "text-end", "id": text_id})
    yield _sse(
        {
            "type": "source-document",
            "sourceId": STUB_CITATION["sourceId"],
            "mediaType": STUB_CITATION["mediaType"],
            "title": STUB_CITATION["title"],
        }
    )
    yield _sse({"type": "finish"})
    yield _sse("[DONE]")
