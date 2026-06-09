import uuid

from app.assistant.outputs import Citation, EvidenceLabel, GroundedAnswer
from app.chat.streaming import (
    clerk_status_event,
    iter_chat_turn_with_status,
    stream_grounded_answer,
)
from tests.conftest import run_async


async def _collect_events(answer: GroundedAnswer) -> list[str]:
    return [event async for event in stream_grounded_answer(answer, chunk_delay_s=0)]


def test_stream_grounded_answer_emits_text_and_sources() -> None:
    chunk_id = uuid.uuid4()
    answer = GroundedAnswer(
        answer="Hello world",
        citations=[
            Citation(
                chunk_id=chunk_id,
                document_id=uuid.uuid4(),
                excerpt="Hello",
                filename="brief.md",
                project="clerk",
                source_type="doctrine",
                label=EvidenceLabel.FACT,
            )
        ],
    )

    events = run_async(_collect_events(answer))
    joined = "".join(events)

    assert '"type":"start"' in joined.replace(" ", "")
    assert '"type":"text-delta"' in joined.replace(" ", "")
    assert '"type":"source-document"' in joined.replace(" ", "")
    assert str(chunk_id) in joined
    assert '"providerMetadata"' in joined.replace(" ", "")
    assert "brief.md" in joined
    assert "[DONE]" in joined


def test_clerk_status_event_uses_data_stream_type() -> None:
    event = clerk_status_event("Loading seed file list")
    assert '"type":"data-clerk-status"' in event.replace(" ", "")
    assert "Loading seed file list" in event


async def _collect_turn_events() -> list[str | GroundedAnswer]:
    items: list[str | GroundedAnswer] = []

    async def fake_turn(on_status):
        if on_status is not None:
            await on_status("Loading seed file list")
        return GroundedAnswer(answer="Done", evidence_sufficient=False)

    async for item in iter_chat_turn_with_status(run_turn=fake_turn):
        items.append(item)
    return items


def test_iter_chat_turn_with_status_emits_progress_events() -> None:
    items = run_async(_collect_turn_events())
    status_events = [item for item in items if isinstance(item, str)]
    answers = [item for item in items if isinstance(item, GroundedAnswer)]

    assert any("Received your question" in event for event in status_events)
    assert any("Loading seed file list" in event for event in status_events)
    assert len(answers) == 1
    assert answers[0].answer == "Done"
