from app.agent.mutation_intent import (
    PROFILE_MUTATION_SCOPE,
    classify_mutation_intent,
    hash_user_message,
    is_profile_proposal_confirmation,
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


def test_broad_profile_completion_request_grants_unbound_enrichment_mutation_scope() -> None:
    from app.agent.mutation_intent import PROFILE_ENRICHMENT_REASON

    intent = classify_mutation_intent("Update the project profile where possible.")

    assert intent.scopes == (PROFILE_MUTATION_SCOPE,)
    assert dict(intent.profile_patch) == {}
    assert intent.requires_confirmation is False
    assert intent.reason == PROFILE_ENRICHMENT_REASON


def test_available_facts_profile_update_grants_enrichment_mutation_scope() -> None:
    from app.agent.mutation_intent import PROFILE_ENRICHMENT_REASON

    intent = classify_mutation_intent(
        "update the project profile to reflect avaliable facts"
    )

    assert intent.scopes == (PROFILE_MUTATION_SCOPE,)
    assert dict(intent.profile_patch) == {}
    assert intent.reason == PROFILE_ENRICHMENT_REASON


def test_profile_proposal_confirmation_is_recognized_without_a_direct_patch() -> None:
    assert is_profile_proposal_confirmation(
        "Confirm and set that site address and client on the profile."
    )
    assert not is_profile_proposal_confirmation("Confirm the tender comparison.")


def test_cost_plan_update_for_residential_project_does_not_grant_profile_scope() -> None:
    intent = classify_mutation_intent(
        "Update the cost plan for this residential project."
    )

    assert intent.scopes == ()


def test_explicit_site_address_imperative_binds_identity_field() -> None:
    text = "Set the project address to: 82 Queen Street, Petersham NSW 2049"
    intent = classify_mutation_intent(text)

    assert intent.scopes == (PROFILE_MUTATION_SCOPE,)
    assert dict(intent.profile_patch) == {
        "site_address": "82 Queen Street, Petersham NSW 2049",
    }


def test_explicit_client_imperative_binds_identity_field() -> None:
    text = 'Set the client to "Walsh Family"'
    intent = classify_mutation_intent(text)

    assert intent.scopes == (PROFILE_MUTATION_SCOPE,)
    assert dict(intent.profile_patch) == {"client": "Walsh Family"}


def test_class_1a_house_scale_are_bound() -> None:
    text = (
        "Make this a Class 1a residential refurbishment in NSW. "
        "Set it as a single-storey house around 280 m² GFA."
    )
    intent = classify_mutation_intent(text)

    assert intent.scopes == (PROFILE_MUTATION_SCOPE,)
    assert dict(intent.profile_patch) == {
        "building_class": "residential",
        "work_type": "refurb",
        "state": "NSW",
        "subclasses": ["house"],
        "scale": {"storeys": 1, "gfa_sqm": 280},
    }


def test_two_storey_gfa_binds_scale_without_forcing_subclass() -> None:
    intent = classify_mutation_intent(
        "Set scale to a two-storey dwelling with 320 sqm GFA."
    )

    assert intent.scopes == (PROFILE_MUTATION_SCOPE,)
    assert dict(intent.profile_patch) == {
        "scale": {"storeys": 2, "gfa_sqm": 320},
    }


def test_site_area_binds_without_stealing_gfa() -> None:
    intent = classify_mutation_intent(
        "Set scale to a 450 sqm site and 280 sqm GFA."
    )

    assert dict(intent.profile_patch) == {
        "scale": {"site_sqm": 450, "gfa_sqm": 280},
    }


def test_update_profile_bedrooms_and_garage_spaces_are_bound() -> None:
    text = "update profile to have 5 bedrooms and 0 garage space"
    intent = classify_mutation_intent(text)

    assert intent.scopes == (PROFILE_MUTATION_SCOPE,)
    assert dict(intent.profile_patch) == {
        "scale": {"bedrooms": 5, "garage_spaces": 0},
    }


PROMPT_11_DUE_DILIGENCE = (
    "Client is buying a distribution centre and wants technical due diligence "
    "before settlement in six weeks. Building condition, compliance, capex "
    "forecast, any deal-breakers."
)


def test_due_diligence_brief_maps_to_advisory_industrial_logistics() -> None:
    """Wave 2 prompt 11 never raised a proposal; advisory was unreachable."""
    intent = classify_mutation_intent(PROMPT_11_DUE_DILIGENCE)

    assert dict(intent.profile_patch) == {
        "building_class": "industrial",
        "work_type": "advisory",
        "subclasses": ["logistics_ecommerce"],
    }
    assert intent.scopes == ()


def test_materialize_merges_partial_scale_with_current_profile() -> None:
    from app.agent.mutation_intent import materialize_profile_patch

    intent = classify_mutation_intent(
        "update profile to have 5 bedrooms and 0 garage space"
    )
    bound = materialize_profile_patch(
        intent,
        current_scale={"gfa_sqm": 280, "storeys": 1},
    )

    assert dict(bound.profile_patch) == {
        "scale": {
            "gfa_sqm": 280,
            "storeys": 1,
            "bedrooms": 5,
            "garage_spaces": 0,
        }
    }
