from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.database.project import Project
from app.database.project_profile_proposal import ProjectProfileProposal
from app.projects.events import publish_project_event
from app.projects.profile import (
    PROFILE_FIELDS,
    ProfileValidationError,
    apply_profile_patch,
    read_profile,
    validate_profile_patch,
)
from app.schemas.profile_proposals import (
    ProfileEvidenceReference,
    ProfileProposalResolution,
    ProjectProfileProposalView,
)
from app.schemas.projects import ProjectProfilePatch


class ProfileProposalNotFound(LookupError):
    pass


class ProfileProposalStateConflict(RuntimeError):
    def __init__(self, state: str) -> None:
        self.state = state
        super().__init__(f"profile proposal is already {state}")


class ProfileProposalRevisionConflict(RuntimeError):
    def __init__(self, *, proposal_revision: int, current_revision: int) -> None:
        self.proposal_revision = proposal_revision
        self.current_revision = current_revision
        super().__init__(
            f"profile proposal revision {proposal_revision} does not match "
            f"current revision {current_revision}"
        )


IDENTITY_PROPOSAL_FIELDS = frozenset({"client", "site_address"})

# Setup fields a descriptive opening prompt establishes. They may be auto-applied
# on the same terms identity fields already are: only into a field that is still
# empty, never over a value the user has already settled. Writing them matters
# beyond the profile panel — work_scope drives consultant selection and seed
# routing, complexity drives risk flags, and leaving them unset is what made
# every small-works PMP render as an empty scaffold.
SETUP_PROPOSAL_FIELDS = frozenset(
    {
        "building_class",
        "work_type",
        "subclasses",
        "scale",
        "complexity",
        "work_scope",
        "assets",
        "budget",
        "state",
    }
)
AUTO_APPLY_PROPOSAL_FIELDS = IDENTITY_PROPOSAL_FIELDS | SETUP_PROPOSAL_FIELDS


def _is_unset(value: Any) -> bool:
    """Empty containers count as unset: scale={} and work_scope=[] are not answers."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return not value
    return False


def should_auto_apply_proposal(
    proposal: ProjectProfileProposal,
    project: Project,
    *,
    evidence_derived: bool | None = None,
) -> bool:
    """True when a proposal only fills blanks, so approving it destroys nothing.

    Identity proposals keep their existing behaviour (they resolve conflicts by
    rejecting). Setup proposals auto-apply only when strictly additive; anything
    that would overwrite a settled value stays pending for explicit approval.
    """
    fields = set(proposal.proposed_values) - {"clear_incompatible"}
    if not fields or not fields <= AUTO_APPLY_PROPOSAL_FIELDS:
        return False
    if fields <= IDENTITY_PROPOSAL_FIELDS:
        return True
    # Setup values only pass straight through when the user stated them. A value
    # read out of a document is a reading rather than an instruction, and keeps
    # its review step however empty the field is.
    if evidence_derived is None:
        evidence_derived = bool(getattr(proposal, "evidence_references", None))
    if evidence_derived:
        return False
    current = read_profile(project)
    return all(_is_unset(getattr(current, field, None)) for field in fields)


async def propose_project_profile_change(
    session,
    *,
    project: Project,
    proposed_values: dict[str, Any],
    evidence_references: list[ProfileEvidenceReference | dict[str, Any]],
    confidence: float | None,
    proposer: str,
) -> ProjectProfileProposalView:
    reserved_fields = {"expected_revision"} & set(proposed_values)
    if reserved_fields:
        raise ProfileValidationError(
            ["Proposal values cannot contain expected_revision"]
        )
    if confidence is not None and not 0 <= confidence <= 1:
        raise ProfileValidationError(["Proposal confidence must be between 0 and 1"])
    proposer = proposer.strip()
    if not proposer:
        raise ProfileValidationError(["Proposal proposer is required"])
    await session.refresh(project, with_for_update=True)
    patch = ProjectProfilePatch(
        expected_revision=project.profile_revision,
        **proposed_values,
    )
    plan = validate_profile_patch(project, patch)
    if not plan.changed_fields and not plan.cleared_fields:
        raise ProfileValidationError(["Profile proposal must contain an effective change"])
    normalized_values = {
        field: getattr(patch, field)
        for field in PROFILE_FIELDS
        if field in patch.model_fields_set
    }
    if patch.clear_incompatible:
        normalized_values["clear_incompatible"] = True
    references = [
        reference
        if isinstance(reference, ProfileEvidenceReference)
        else ProfileEvidenceReference.model_validate(reference)
        for reference in evidence_references
    ]
    proposal = ProjectProfileProposal(
        project_id=project.id,
        profile_revision=project.profile_revision,
        current_values=plan.before.model_dump(mode="json"),
        proposed_values=_json_values(normalized_values),
        evidence_references=[reference.model_dump(mode="json") for reference in references],
        confidence=confidence,
        state="pending",
        proposer=proposer,
    )
    session.add(proposal)
    await session.flush()
    await publish_project_event(
        session,
        project_id=project.id,
        actor_source=proposer,
        resource_type="project_profile_proposal",
        resource_id=proposal.id,
        resource_revision=project.profile_revision,
        action="proposed",
        payload={
            "profile_revision": project.profile_revision,
            "proposed_fields": sorted(normalized_values),
            "evidence_count": len(references),
            "confidence": confidence,
        },
        locked_project=project,
    )
    return ProjectProfileProposalView.model_validate(proposal)


async def list_profile_proposals(
    session,
    *,
    project_id: uuid.UUID,
    state: str | None = None,
) -> list[ProjectProfileProposalView]:
    statement = select(ProjectProfileProposal).where(
        ProjectProfileProposal.project_id == project_id
    )
    if state is not None:
        statement = statement.where(ProjectProfileProposal.state == state)
    result = await session.execute(
        statement.order_by(ProjectProfileProposal.created_at.desc())
    )
    return [ProjectProfileProposalView.model_validate(row) for row in result.scalars()]


async def accept_profile_proposal(
    session,
    *,
    project: Project,
    proposal_id: uuid.UUID,
    expected_profile_revision: int,
    actor_source: str,
) -> ProfileProposalResolution:
    await session.refresh(project, with_for_update=True)
    proposal = await _locked_proposal(session, project.id, proposal_id)
    _require_pending(proposal)
    if _is_identity_proposal(proposal) or should_auto_apply_proposal(proposal, project):
        return await _accept_additive_proposal(
            session,
            project=project,
            proposal=proposal,
            actor_source=actor_source,
        )
    _require_revision(proposal, project, expected_profile_revision)
    change = await apply_profile_patch(
        session,
        project=project,
        patch=ProjectProfilePatch(
            expected_revision=expected_profile_revision,
            **proposal.proposed_values,
        ),
        actor_source=actor_source,
    )
    proposal.state = "accepted"
    proposal.resolver_source = actor_source
    proposal.resolved_at = datetime.now(UTC)
    await publish_project_event(
        session,
        project_id=project.id,
        actor_source=actor_source,
        resource_type="project_profile_proposal",
        resource_id=proposal.id,
        resource_revision=change.new_revision,
        action="accepted",
        payload={"profile_revision": change.new_revision},
        locked_project=project,
    )
    await session.refresh(proposal)
    return ProfileProposalResolution(
        proposal=ProjectProfileProposalView.model_validate(proposal),
        profile_change=change,
    )


async def _accept_additive_proposal(
    session,
    *,
    project: Project,
    proposal: ProjectProfileProposal,
    actor_source: str,
) -> ProfileProposalResolution:
    """Apply proposed values to empty fields, even if another edit advanced the revision."""
    current = read_profile(project)
    values: dict[str, Any] = {}
    conflicts = False
    for field, value in proposal.proposed_values.items():
        existing = getattr(current, field, None)
        if _is_unset(existing):
            values[field] = value
        elif _identity_values_match(existing, value):
            continue
        else:
            conflicts = True

    change = None
    if conflicts:
        proposal.state = "rejected"
        action = "rejected"
    else:
        if values:
            change = await apply_profile_patch(
                session,
                project=project,
                patch=ProjectProfilePatch(
                    expected_revision=project.profile_revision,
                    **values,
                ),
                actor_source=(
                    "identity_autofill" if actor_source == "user" else actor_source
                ),
            )
        proposal.state = "accepted"
        action = "accepted"
    proposal.resolver_source = actor_source
    proposal.resolved_at = datetime.now(UTC)
    revision = change.new_revision if change is not None else project.profile_revision
    await publish_project_event(
        session,
        project_id=project.id,
        actor_source=actor_source,
        resource_type="project_profile_proposal",
        resource_id=proposal.id,
        resource_revision=revision,
        action=action,
        payload={"profile_revision": revision},
        locked_project=project,
    )
    await session.refresh(proposal)
    return ProfileProposalResolution(
        proposal=ProjectProfileProposalView.model_validate(proposal),
        profile_change=change,
    )


async def reject_profile_proposal(
    session,
    *,
    project: Project,
    proposal_id: uuid.UUID,
    expected_profile_revision: int,
    actor_source: str,
) -> ProfileProposalResolution:
    await session.refresh(project, with_for_update=True)
    proposal = await _locked_proposal(session, project.id, proposal_id)
    _require_pending(proposal)
    _require_revision(proposal, project, expected_profile_revision)
    proposal.state = "rejected"
    proposal.resolver_source = actor_source
    proposal.resolved_at = datetime.now(UTC)
    await publish_project_event(
        session,
        project_id=project.id,
        actor_source=actor_source,
        resource_type="project_profile_proposal",
        resource_id=proposal.id,
        resource_revision=project.profile_revision,
        action="rejected",
        payload={"profile_revision": project.profile_revision},
        locked_project=project,
    )
    await session.refresh(proposal)
    return ProfileProposalResolution(
        proposal=ProjectProfileProposalView.model_validate(proposal)
    )


async def _locked_proposal(
    session,
    project_id: uuid.UUID,
    proposal_id: uuid.UUID,
) -> ProjectProfileProposal:
    proposal = await session.get(
        ProjectProfileProposal,
        proposal_id,
        with_for_update=True,
    )
    if proposal is None or proposal.project_id != project_id:
        raise ProfileProposalNotFound(str(proposal_id))
    return proposal


def _require_pending(proposal: ProjectProfileProposal) -> None:
    if proposal.state != "pending":
        raise ProfileProposalStateConflict(proposal.state)


def _is_identity_proposal(proposal: ProjectProfileProposal) -> bool:
    fields = set(proposal.proposed_values)
    return bool(fields) and fields <= IDENTITY_PROPOSAL_FIELDS


def _identity_values_match(existing: Any, proposed: Any) -> bool:
    if not isinstance(existing, str) or not isinstance(proposed, str):
        return existing == proposed
    return existing.strip().casefold() == proposed.strip().casefold()


def _require_revision(
    proposal: ProjectProfileProposal,
    project: Project,
    expected_profile_revision: int,
) -> None:
    if (
        proposal.profile_revision != project.profile_revision
        or expected_profile_revision != project.profile_revision
    ):
        raise ProfileProposalRevisionConflict(
            proposal_revision=proposal.profile_revision,
            current_revision=project.profile_revision,
        )


def _json_values(values: dict[str, Any]) -> dict[str, Any]:
    return ProjectProfilePatch(
        expected_revision=1,
        **values,
    ).model_dump(mode="json", include=set(values))
