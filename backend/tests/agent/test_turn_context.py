import pytest

from app.agent.mutation_intent import classify_mutation_intent
from app.agent.turn_context import (
    HistoryMessage,
    build_agent_prompt,
    turn_needs_mutation_tools,
    turn_needs_profile_mutation_tools,
)
from app.config import settings

PROJECT_ID = "22222222-2222-2222-2222-222222222222"


def test_prompt_carries_overlays_and_history_before_user_text() -> None:
    prompt = build_agent_prompt(
        "Compare the tenders",
        project_id=PROJECT_ID,
        title="Harbour House",
        archetype="renovation",
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
    assert "state: NSW" in prompt
    assert "site_address: (not declared)" in prompt
    assert "client: (not declared)" in prompt
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
    assert "<recent-conversation>" not in prompt


def test_broad_profile_update_runs_document_enrichment_before_replying() -> None:
    prompt = build_agent_prompt(
        "Update the project profile where possible.",
        project_id=PROJECT_ID,
        title="Walsh Reno",
        archetype=None,
        state=None,
        phase=None,
        building_class=None,
        work_type=None,
        history=[],
    )

    assert "<profile-enrichment-request>" in prompt
    assert "get_project_profile and get_project_profile_options" in prompt
    assert "Review every unset or" in prompt
    assert "update_project_profile" in prompt
    assert "profile is already up to date" in prompt
    assert "profile_mutation authority" in prompt


def test_available_facts_profile_update_needs_mutation_tools() -> None:
    user_text = "update the project profile to reflect avaliable facts"
    intent = classify_mutation_intent(user_text)

    assert turn_needs_profile_mutation_tools(user_text, intent) is True
    assert turn_needs_mutation_tools(user_text, intent) is True
    assert intent.scopes


def test_create_rfp_request_needs_mutation_tools() -> None:
    user_text = "create rfp for structural engineer"
    intent = classify_mutation_intent(user_text)

    assert turn_needs_profile_mutation_tools(user_text, intent) is False
    assert turn_needs_mutation_tools(user_text, intent) is True


def test_read_only_project_question_does_not_need_mutation_tools() -> None:
    user_text = "what is the project budget?"
    intent = classify_mutation_intent(user_text)

    assert turn_needs_mutation_tools(user_text, intent) is False


def test_update_cost_plan_with_adopted_budget_needs_mutation_tools() -> None:
    user_text = (
        "adopt a total construction cost of 300,000, update cost plan and "
        "estimate reasonable cost for all line items."
    )
    intent = classify_mutation_intent(user_text)

    assert turn_needs_mutation_tools(user_text, intent) is True
    prompt = build_agent_prompt(
        user_text,
        project_id=PROJECT_ID,
        title="Greenbank",
        archetype="renovation",
        state="NSW",
        phase="design",
        building_class="residential",
        work_type="extend",
        history=[],
        mutation_intent=intent,
    )
    assert "<adopted-cost-plan-budget-request>" in prompt
    assert "apply_cost_plan_budget_forecast" in prompt
    assert "Do not ask the user to regenerate" in prompt


def test_check_and_fix_profile_phrasing_runs_document_enrichment() -> None:
    """Regression: broad check/fix phrasing grants enrichment write authority."""
    user_text = (
        "Please check the project profile attributes and change any that are "
        "incorrect or empty."
    )
    intent = classify_mutation_intent(user_text)
    prompt = build_agent_prompt(
        user_text,
        project_id=PROJECT_ID,
        title="Walsh Reno",
        archetype=None,
        state=None,
        phase=None,
        building_class=None,
        work_type=None,
        history=[],
        mutation_intent=intent,
    )

    assert intent.scopes
    assert "<profile-enrichment-request>" in prompt
    assert "update_project_profile" in prompt
    assert "unbound profile_mutation authority" in prompt


def test_profile_proposal_confirmation_uses_acceptance_without_direct_mutation_scope() -> (
    None
):
    prompt = build_agent_prompt(
        "Confirm and set that site address and client on the profile.",
        project_id=PROJECT_ID,
        title="Walsh Reno",
        archetype=None,
        state=None,
        phase=None,
        building_class=None,
        work_type=None,
        history=[],
    )

    assert "<profile-proposal-confirmation>" in prompt
    assert "accept_project_profile_proposal" in prompt
    assert "profile_mutation scope" in prompt
    assert "get_project_snapshot" in prompt
    assert "Do not call update_project_profile" in prompt


def test_confirmed_profile_values_are_reported_only_after_server_acceptance() -> None:
    prompt = build_agent_prompt(
        "Confirm and set that site address and client on the profile.",
        project_id=PROJECT_ID,
        title="Walsh Reno",
        archetype=None,
        state=None,
        phase=None,
        building_class=None,
        work_type=None,
        history=[],
        confirmed_profile_values={
            "site_address": "42 Hargrave Street, Paddington NSW 2021",
            "client": "David and Emma Walsh",
        },
    )

    assert "<profile-proposal-confirmed>" in prompt
    assert '"client": "David and Emma Walsh"' in prompt
    assert "Do not call a profile mutation tool" in prompt
    assert "<profile-proposal-confirmation>" not in prompt


def test_prompt_routes_head_contractor_eoi_without_tender_comparison_gate() -> None:
    prompt = build_agent_prompt(
        "Draft an EOI for the main works contractor tender",
        project_id=PROJECT_ID,
        title="Petersham Apartments",
        archetype=None,
        state="NSW",
        phase="procurement",
        building_class="residential",
        work_type="new",
        history=[],
    )

    assert "start_contractor_eoi" in prompt
    assert "does not use Tender Comparison's Class 1a coverage gate" in prompt


def test_prompt_treats_taxonomy_profile_as_authoritative() -> None:
    prompt = build_agent_prompt(
        "What do you know about the project?",
        project_id=PROJECT_ID,
        title="Walsh Reno",
        archetype=None,
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
    assert (
        "scale: GFA sqm=200, Storeys=(not declared), Bedrooms=(not declared), Garage spaces=(not declared)"
        in prompt
    )


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
        state="NSW",
        phase=None,
        building_class=None,
        work_type=None,
        history=history,
    )

    assert "message number 3" not in prompt
    conversation = prompt.split("<recent-conversation>\n")[1].split(
        "\n</recent-conversation>"
    )[0]
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
        state="NSW",
        phase=None,
        building_class=None,
        work_type=None,
        history=[],
        mutation_intent=classify_mutation_intent(user_text),
    )

    assert "does not authorize a direct profile mutation" in prompt
    assert "ask the user to confirm" in prompt


def test_bound_profile_patch_includes_exact_json_and_scale_fields() -> None:
    user_text = (
        "Make this a Class 1a residential refurbishment in NSW. "
        "I'm the architect/PM. Set it as a single-storey house around 280 m² GFA."
    )
    prompt = build_agent_prompt(
        user_text,
        project_id=PROJECT_ID,
        title="Harbour House",
        archetype=None,
        state=None,
        phase=None,
        building_class=None,
        work_type=None,
        history=[],
        mutation_intent=classify_mutation_intent(user_text),
    )

    assert '"gfa_sqm": 280' in prompt
    assert '"storeys": 1' in prompt
    assert '"subclasses": ["house"]' in prompt
    assert "never claim that scale fields" in prompt
    assert "<profile-enrichment-request>" not in prompt
