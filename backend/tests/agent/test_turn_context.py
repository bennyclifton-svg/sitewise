import pytest

from app.agent.turn_context import HistoryMessage, build_agent_prompt
from app.config import settings


def test_prompt_carries_overlays_and_history_before_user_text() -> None:
    prompt = build_agent_prompt(
        "Compare the tenders",
        archetype="renovation",
        user_role="architect-pm",
        state="NSW",
        history=[
            HistoryMessage(role="user", content="Any update on the quotes?"),
            HistoryMessage(role="assistant", content="Two received, one pending."),
        ],
    )

    assert prompt.index("<project-context>") < prompt.index("<recent-conversation>")
    assert prompt.rstrip().endswith("Compare the tenders")
    assert "archetype: renovation" in prompt
    assert "user_role: architect-pm" in prompt
    assert "state: NSW" in prompt
    assert "user: Any update on the quotes?" in prompt
    assert "assistant: Two received, one pending." in prompt


def test_prompt_marks_undeclared_overlays_and_omits_empty_history() -> None:
    prompt = build_agent_prompt(
        "Hello",
        archetype=None,
        user_role="builder",
        state=None,
        history=[],
    )

    assert "archetype: (not declared)" in prompt
    assert "state: (not declared)" in prompt
    assert "user_role: builder" in prompt
    assert "<recent-conversation>" not in prompt


def test_history_window_is_bounded_by_count_and_chars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "agent_history_message_limit", 2)
    monkeypatch.setattr(settings, "agent_history_message_chars", 20)

    history = [
        HistoryMessage(role="user", content=f"message number {index} " * 5)
        for index in range(6)
    ]
    prompt = build_agent_prompt(
        "Next",
        archetype="new-dwelling",
        user_role="builder",
        state="NSW",
        history=history,
    )

    assert "message number 3" not in prompt
    conversation = prompt.split("<recent-conversation>\n")[1].split("\n</recent-conversation>")[0]
    lines = conversation.splitlines()
    assert len(lines) == 2
    for line in lines:
        content = line.split(": ", 1)[1]
        assert len(content) <= 20
        assert content.endswith("…")


def test_multiline_history_messages_are_flattened() -> None:
    prompt = build_agent_prompt(
        "Next",
        archetype="new-dwelling",
        user_role="builder",
        state="NSW",
        history=[HistoryMessage(role="assistant", content="line one\n\nline two")],
    )

    assert "assistant: line one line two" in prompt
