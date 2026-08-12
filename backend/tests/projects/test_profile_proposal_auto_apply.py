"""Auto-apply rules for profile proposals.

Regression: a chat turn that parsed a project description correctly could not
write it. Every setup proposal queued for explicit approval, so work_scope,
scale and complexity stayed empty and the PMP generated from a blank profile.
Setup fields now follow the identity-field rule already documented in
architecture.md §5.2 — fill a blank, never overwrite an answer.
"""

import uuid
from types import SimpleNamespace

from app.projects.profile_proposals import (
    AUTO_APPLY_PROPOSAL_FIELDS,
    should_auto_apply_proposal,
)

_TAXONOMY_FIELDS = ("subclasses", "scale", "complexity", "work_scope")


def _project(**profile) -> SimpleNamespace:
    """Shape a Project the way read_profile reads one: taxonomy under metadata."""
    taxonomy = {
        field: profile.pop(field) for field in _TAXONOMY_FIELDS if field in profile
    }
    metadata: dict = {"taxonomy": taxonomy} if taxonomy else {}
    if "site_address" in profile:
        metadata["site_address"] = profile.pop("site_address")
    if "client" in profile:
        metadata["client"] = profile.pop("client")
    return SimpleNamespace(
        id=uuid.uuid4(),
        profile_revision=1,
        building_class=profile.pop("building_class", None),
        work_type=profile.pop("work_type", None),
        state=profile.pop("state", None),
        project_metadata=metadata,
        **profile,
    )


def _proposal(evidence_references=(), **values) -> SimpleNamespace:
    return SimpleNamespace(
        proposed_values=values, evidence_references=list(evidence_references)
    )


def test_setup_fields_auto_apply_when_profile_is_blank() -> None:
    proposal = _proposal(
        work_scope=["mechanical_services"],
        scale={"storeys": 1},
        complexity={"operational_constraints": "live_environment"},
    )

    assert should_auto_apply_proposal(proposal, _project()) is True


def test_setup_fields_queue_when_the_field_already_has_a_value() -> None:
    proposal = _proposal(work_scope=["mechanical_services"])
    project = _project(work_scope=["fire_services"])

    assert should_auto_apply_proposal(proposal, project) is False


def test_empty_containers_count_as_blank() -> None:
    """work_scope=[] and scale={} are the shape a fresh project starts in."""
    proposal = _proposal(work_scope=["mechanical_services"], scale={"storeys": 1})
    project = _project(work_scope=[], scale={})

    assert should_auto_apply_proposal(proposal, project) is True


def test_form_created_project_accepts_a_complexity_correction() -> None:
    """The D2/D1 interaction: the creation form used to pre-fill complexity with
    its benign defaults, which read as settled answers and blocked the agent from
    ever recording that a site was occupied. With the form leaving unanswered
    dimensions out, that correction now applies."""
    proposal = _proposal(
        complexity={"operational_constraints": "live_environment"},
        work_scope=["mechanical_hvac"],
    )
    form_created = _project(complexity={}, work_scope=[])

    assert should_auto_apply_proposal(proposal, form_created) is True


def test_a_settled_complexity_answer_is_still_never_overwritten() -> None:
    proposal = _proposal(complexity={"operational_constraints": "live_environment"})
    answered = _project(complexity={"operational_constraints": "vacant"})

    assert should_auto_apply_proposal(proposal, answered) is False


def test_mixed_proposal_queues_when_any_field_is_settled() -> None:
    proposal = _proposal(
        work_scope=["mechanical_services"], building_class="commercial"
    )
    project = _project(building_class="residential")

    assert should_auto_apply_proposal(proposal, project) is False


def test_identity_fields_keep_their_existing_behaviour() -> None:
    """Identity proposals auto-apply regardless; conflicts resolve on accept."""
    proposal = _proposal(client="Acme Pty Ltd")
    project = _project(client="Someone Else")

    assert should_auto_apply_proposal(proposal, project) is True


def test_unknown_fields_never_auto_apply() -> None:
    proposal = _proposal(phase="delivery")

    assert should_auto_apply_proposal(proposal, _project()) is False


def test_empty_proposal_never_auto_applies() -> None:
    assert should_auto_apply_proposal(_proposal(), _project()) is False


def test_clear_incompatible_alone_is_not_an_additive_change() -> None:
    proposal = _proposal(clear_incompatible=True)

    assert should_auto_apply_proposal(proposal, _project()) is False


def test_evidence_derived_setup_values_still_queue_for_review() -> None:
    """A value read out of a document keeps its review step, blank field or not.

    This is the architecture.md §5.2 split: the user telling you what the job is
    differs from the agent reading a claim off page 2 of a report.
    """
    proposal = _proposal(
        evidence_references=[{"source_document_id": "abc", "locator": "page 2"}],
        state="VIC",
    )

    assert should_auto_apply_proposal(proposal, _project()) is False


def test_evidence_derived_identity_still_auto_applies() -> None:
    proposal = _proposal(
        evidence_references=[{"source_document_id": "abc", "locator": "page 1"}],
        client="Atelier North",
    )

    assert should_auto_apply_proposal(proposal, _project()) is True


def test_auto_apply_set_covers_the_routing_relevant_fields() -> None:
    """These are the fields seed routing, consultants and risk flags read."""
    assert {"work_scope", "complexity", "scale"} <= AUTO_APPLY_PROPOSAL_FIELDS
