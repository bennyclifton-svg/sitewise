from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.database.project import Project
from app.database.project_profile_proposal import ProjectProfileProposal
from app.projects.profile_proposals import (
    ProfileProposalRevisionConflict,
    accept_profile_proposal,
    list_profile_proposals,
    propose_project_profile_change,
    reject_profile_proposal,
)


def _project(**overrides) -> Project:
    values = {
        "id": uuid.uuid4(),
        "owner_user_id": uuid.uuid4(),
        "slug": "demo",
        "title": "Demo",
        "workspace_path": "04-projects/demo",
        "phase": "brief-planning",
        "archetype": None,
        "building_class": "residential",
        "work_type": "new",
        "user_role": "architect-pm",
        "state": "NSW",
        "profile_revision": 3,
        "event_sequence": 0,
        "status": "active",
        "project_metadata": {"taxonomy": {"subclasses": ["house"]}},
    }
    values.update(overrides)
    return Project(**values)


def _proposal(project: Project, **overrides) -> ProjectProfileProposal:
    now = datetime.now(UTC)
    values = {
        "id": uuid.uuid4(),
        "project_id": project.id,
        "profile_revision": project.profile_revision,
        "current_values": {"state": project.state},
        "proposed_values": {"state": "VIC"},
        "evidence_references": [],
        "confidence": 0.9,
        "state": "pending",
        "proposer": "agent",
        "resolver_source": None,
        "created_at": now,
        "updated_at": now,
        "resolved_at": None,
    }
    values.update(overrides)
    return ProjectProfileProposal(**values)


def test_evidence_derived_proposal_persists_values_and_references() -> None:
    project = _project()
    source_id = uuid.uuid4()
    session = AsyncMock()
    session.add = MagicMock()

    async def flush() -> None:
        proposal = session.add.call_args.args[0]
        proposal.id = uuid.uuid4()
        proposal.created_at = proposal.updated_at = datetime.now(UTC)

    session.flush.side_effect = flush
    publish = AsyncMock()
    with patch(
        "app.projects.profile_proposals.publish_project_event", new=publish
    ):
        result = asyncio.run(
            propose_project_profile_change(
                session,
                project=project,
                proposed_values={"state": "VIC"},
                evidence_references=[
                    {
                        "source_document_id": source_id,
                        "locator": "page 2",
                        "claim": "Site is in Victoria",
                    }
                ],
                confidence=0.9,
                proposer="agent",
            )
        )

    assert result.state == "pending"
    assert result.profile_revision == 3
    assert result.current_values["state"] == "NSW"
    assert result.proposed_values == {"state": "VIC"}
    assert result.evidence_references[0].source_document_id == source_id
    publish.assert_awaited_once()


def test_accept_reject_stale_proposal_when_profile_changed() -> None:
    project = _project(profile_revision=4)
    proposal = _proposal(project, profile_revision=3)
    session = AsyncMock()
    session.get.return_value = proposal

    with pytest.raises(ProfileProposalRevisionConflict) as raised:
        asyncio.run(
            accept_profile_proposal(
                session,
                project=project,
                proposal_id=proposal.id,
                expected_profile_revision=4,
                actor_source="user",
            )
        )

    assert raised.value.proposal_revision == 3
    assert raised.value.current_revision == 4
    assert proposal.state == "pending"


def test_reject_proposal_persists_resolution_without_profile_change() -> None:
    project = _project()
    proposal = _proposal(project)
    session = AsyncMock()
    session.get.return_value = proposal
    publish = AsyncMock()
    with patch(
        "app.projects.profile_proposals.publish_project_event", new=publish
    ):
        resolution = asyncio.run(
            reject_profile_proposal(
                session,
                project=project,
                proposal_id=proposal.id,
                expected_profile_revision=3,
                actor_source="user",
            )
        )

    assert resolution.proposal.state == "rejected"
    assert resolution.profile_change is None
    assert proposal.resolved_at is not None
    publish.assert_awaited_once()


def test_list_proposals_rehydrates_evidence_references() -> None:
    project = _project()
    source_id = uuid.uuid4()
    proposal = _proposal(
        project,
        evidence_references=[{"source_document_id": str(source_id), "locator": "p3"}],
    )
    class Scalars:
        def __iter__(self):
            return iter([proposal])

    scalars = Scalars()
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(scalars=lambda: scalars)

    proposals = asyncio.run(
        list_profile_proposals(session, project_id=project.id, state="pending")
    )

    assert proposals[0].evidence_references[0].source_document_id == source_id
