from app.agent.mutation_intent import (
    PROFILE_MUTATION_SCOPE,
    classify_mutation_intent,
    hash_user_message,
)


def test_explicit_profile_imperative_grants_narrow_bound_scope() -> None:
    text = (
        "Set this to a residential refurbishment in NSW; "
        "I am the architect PM."
    )
    intent = classify_mutation_intent(text)

    assert intent.scopes == (PROFILE_MUTATION_SCOPE,)
    assert dict(intent.profile_patch) == {
        "building_class": "residential",
        "work_type": "refurb",
        "state": "NSW",
        "user_role": "architect-pm",
    }
    assert intent.user_message_hash == hash_user_message(text)
    assert intent.requires_confirmation is False


def test_document_claim_never_grants_mutation_scope() -> None:
    intent = classify_mutation_intent(
        "The report says this may be residential refurbishment."
    )

    assert intent.scopes == ()
    assert dict(intent.profile_patch) == {
        "building_class": "residential",
        "work_type": "refurb",
    }
    assert intent.requires_confirmation is True


def test_quoted_instruction_never_grants_mutation_scope() -> None:
    intent = classify_mutation_intent('"Set this project to commercial."')

    assert intent.scopes == ()
    assert intent.requires_confirmation is True


def test_non_profile_message_has_no_scope_or_confirmation() -> None:
    intent = classify_mutation_intent("Summarise the latest tender comparison.")

    assert intent.scopes == ()
    assert dict(intent.profile_patch) == {}
    assert intent.requires_confirmation is False


def test_cost_plan_update_for_residential_project_does_not_grant_profile_scope() -> None:
    intent = classify_mutation_intent(
        "Update the cost plan for this residential project."
    )

    assert intent.scopes == ()
