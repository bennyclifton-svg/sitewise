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


async def propose_project_profile_change(
    session,
    *,
    project: Project,
    proposed_values: dict[str, Any],
    evidence_references: list[ProfileEvidenceReference | dict[str, Any]],
    confidence: float | None,
    proposer: str,
) -> ProjectProfileProposalView:
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
