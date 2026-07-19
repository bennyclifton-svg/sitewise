import pytest

from app.agent.mutation_intent import classify_mutation_intent
from app.agent.turn_context import HistoryMessage, build_agent_prompt
from app.config import settings

PROJECT_ID = "22222222-2222-2222-2222-222222222222"


def test_prompt_carries_overlays_and_history_before_user_text() -> None:
    prompt = build_agent_prompt(
        "Compare the tenders",
        project_id=PROJECT_ID,
        title="Harbour House",
        archetype="renovation",
        user_role="architect-pm",
        state="NSW",
        phase="procurement",
        building_class="1a",
        work_type="alterations-additions",
        history=[
            HistoryMessage(role="user", content="Any update on the quotes?"),
            HistoryMessage(role="assistant", content="Two received, one pending."),
        ],
    )

    assert prompt.index("<persona>") < prompt.index("<project-context>")
    assert prompt.index("<project-context>") < prompt.index("<document-access>")
    assert prompt.index("<document-access>") < prompt.index("<recent-conversation>")
    assert prompt.rstrip().endswith("Compare the tenders")
    assert "construction management intelligence agent" in prompt
    assert "this software repository" in prompt
    assert "project_title: Harbour House" in prompt
    assert "archetype: renovation" in prompt
    assert "building_class: 1a" in prompt
    assert "work_type: alterations-additions" in prompt
    assert "phase: procurement" in prompt
    assert "user_role: architect-pm" in prompt
    assert "state: NSW" in prompt
    assert f"project_id: {PROJECT_ID}" in prompt
    assert "find_document_text is the first choice" in prompt
    assert "run shell commands" in prompt
    assert "user: Any update on the quotes?" in prompt
    assert "assistant: Two received, one pending." in prompt


def test_prompt_marks_undeclared_overlays_and_omits_empty_history() -> None:
    prompt = build_agent_prompt(
        "Hello",
        project_id=PROJECT_ID,
        title="Harbour House",
        archetype=None,
        user_role="builder",
        state=None,
        phase=None,
        building_class=None,
        work_type=None,
        history=[],
    )

    assert "archetype: (not declared)" in prompt
    assert "state: (not declared)" in prompt
    assert "building_class: (not declared)" in prompt
    assert "work_type: (not declared)" in prompt
    assert "phase: (not declared)" in prompt
    assert "user_role: builder" in prompt
    assert "<recent-conversation>" not in prompt


def test_prompt_treats_taxonomy_profile_as_authoritative() -> None:
    prompt = build_agent_prompt(
        "What do you know about the project?",
        project_id=PROJECT_ID,
        title="Walsh Reno",
        archetype=None,
        user_role="architect-pm",
        state="NSW",
        phase="brief-planning",
        building_class="residential",
        work_type="refurb",
        project_metadata={
            "taxonomy": {
                "subclasses": ["house"],
                "scale": {"gfa_sqm": 200},
            }
        },
        history=[],
    )

    assert "archetype: (not declared)" not in prompt
    assert "classification_source: project_taxonomy" in prompt
    assert "project_title: Walsh Reno" in prompt
    assert "building_class: residential" in prompt
    assert "work_type: refurb" in prompt
    assert "subclasses: House (Class 1a)" in prompt
    assert "scale: GFA sqm=200" in prompt


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
        project_id=PROJECT_ID,
        title="Harbour House",
        archetype="new-dwelling",
        user_role="builder",
        state="NSW",
        phase=None,
        building_class=None,
        work_type=None,
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
        project_id=PROJECT_ID,
        title="Harbour House",
        archetype="new-dwelling",
        user_role="builder",
        state="NSW",
        phase=None,
        building_class=None,
        work_type=None,
        history=[HistoryMessage(role="assistant", content="line one\n\nline two")],
    )

    assert "assistant: line one line two" in prompt


def test_ambiguous_profile_claim_prompts_for_confirmation_without_authority() -> None:
    user_text = "The report says this may be a residential refurbishment."
    prompt = build_agent_prompt(
        user_text,
        project_id=PROJECT_ID,
        title="Harbour House",
        archetype=None,
        user_role=None,
        state="NSW",
        phase=None,
        building_class=None,
        work_type=None,
        history=[],
        mutation_intent=classify_mutation_intent(user_text),
    )

    assert "does not authorize a direct profile mutation" in prompt
    assert "ask the user to confirm" in prompt
