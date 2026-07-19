from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app.agent.turn_context import build_agent_prompt
from app.config import settings
from app.database.project import Project
from app.mcp_bridge.auth import ToolAuthError
from app.mcp_bridge.tokens import mint_turn_token
from app.projects.profile import ProfileRevisionConflict
from app.schemas.profile_proposals import (
    ProfileProposalResolution,
    ProjectProfileProposalView,
)
from app.schemas.projects import ProjectProfileChange, ProjectProfileView
from app.sitewise.gate import OverlayStatus
from tests.conftest import run_async

SECRET = "test-secret"
USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)


class _Session:
    def __init__(self, project: Project) -> None:
        self.project = project
        self.added: list[Any] = []
        self.committed = False
        self.get_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc_info):
        return None

    async def get(self, _model, item_id, **_kwargs):
        self.get_count += 1
        return self.project if item_id == self.project.id else None

    async def refresh(self, _row, **_kwargs):
        return None

    def add(self, row):
        self.added.append(row)

    async def flush(self):
        return None

    async def commit(self):
        self.committed = True


def _project(**overrides) -> Project:
    values = {
        "id": PROJECT_ID,
        "owner_user_id": USER_ID,
        "slug": "demo",
        "title": "Demo Project",
        "workspace_path": "04-projects/demo",
        "phase": "brief-planning",
        "archetype": None,
        "building_class": None,
        "work_type": None,
        "user_role": None,
        "state": None,
        "profile_revision": 1,
        "event_sequence": 0,
        "status": "active",
        "project_metadata": {
            "taxonomy": {"complexity": {"environmental_sensitivity": "standard"}}
        },
    }
    values.update(overrides)
    return Project(**values)


def _authorization(project: Project):
    return SimpleNamespace(
        project=project,
        claims=SimpleNamespace(user_id=USER_ID, turn_id=uuid.uuid4()),
    )


def _install(monkeypatch, session: _Session, *, authorization=None):
    from app.mcp_bridge import server

    access = AsyncMock(return_value=authorization or _authorization(session.project))
    mutation = AsyncMock(return_value=authorization or _authorization(session.project))
    monkeypatch.setattr(server, "authorize_project_access_with_claims", access)
    monkeypatch.setattr(server, "authorize_project_mutation_with_claims", mutation)
    monkeypatch.setattr(server, "get_http_headers", lambda **_kwargs: {})
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    return server, access, mutation


def _call(server, name: str, arguments: dict) -> Any:
    async def run():
        async with Client(server.mcp) as client:
            return await client.call_tool(name, arguments)

    return run_async(run()).data


def _proposal(project: Project) -> ProjectProfileProposalView:
    now = datetime.now(UTC)
    return ProjectProfileProposalView(
        id=uuid.uuid4(),
        project_id=project.id,
        profile_revision=project.profile_revision,
        current_values={"state": project.state},
        proposed_values={"state": "VIC"},
        evidence_references=[],
        confidence=0.8,
        state="pending",
        proposer="agent",
        resolver_source=None,
        created_at=now,
        updated_at=now,
        resolved_at=None,
    )


def test_direct_update_uses_bound_scope_and_refreshes_next_prompt(monkeypatch) -> None:
    project = _project()
    session = _Session(project)
    server, _, mutation = _install(monkeypatch, session)
    publish = AsyncMock()
    monkeypatch.setattr(server.agent_turn_status_bus, "publish", publish)
    changes = {
        "building_class": "residential",
        "work_type": "refurb",
        "user_role": "architect-pm",
        "state": "NSW",
    }

    result = _call(
        server,
        "update_project_profile",
        {
            "project_id": str(PROJECT_ID),
            "expected_revision": 1,
            "changes": changes,
        },
    )

    assert result["new_revision"] == 2
    assert result["overlay_status"]["ready"] is True
    assert project.profile_revision == 2
    assert project.project_metadata["taxonomy"]["complexity"] == {
        "environmental_sensitivity": "standard"
    }
    assert mutation.await_args.kwargs["required_scope"] == "profile_mutation"
    assert mutation.await_args.kwargs["requested_profile_patch"] == changes
    assert session.committed is True
    assert publish.await_args.kwargs == {
        "kind": "resource",
        "message": "Updated project profile",
        "projectId": str(PROJECT_ID),
        "resourceType": "project_profile",
        "resourceId": str(PROJECT_ID),
        "action": "updated",
        "revision": 2,
        "changedFields": ["building_class", "work_type", "user_role", "state"],
        "clearedFields": [],
    }
    prompt = build_agent_prompt(
        "What is the current setup?",
        project_id=str(project.id),
        title=project.title,
        archetype=project.archetype,
        user_role=project.user_role,
        state=project.state,
        phase=project.phase,
        building_class=project.building_class,
        work_type=project.work_type,
        history=[],
        project_metadata=project.project_metadata,
    )
    assert "building_class: residential" in prompt
    assert "work_type: refurb" in prompt
    assert "user_role: architect-pm" in prompt


def test_update_rejects_unscoped_turn_before_profile_service(monkeypatch) -> None:
    project = _project()
    session = _Session(project)
    server, _, mutation = _install(monkeypatch, session)
    mutation.side_effect = ToolAuthError(
        "agent turn lacks required mutation scope: profile_mutation"
    )
    apply_patch = AsyncMock()
    monkeypatch.setattr(server, "apply_profile_patch", apply_patch)

    with pytest.raises(ToolError, match="lacks required mutation scope"):
        _call(
            server,
            "update_project_profile",
            {
                "project_id": str(PROJECT_ID),
                "expected_revision": 1,
                "changes": {"state": "VIC"},
            },
        )

    apply_patch.assert_not_awaited()
    assert session.committed is False


def test_evidence_derived_change_creates_proposal_without_profile_mutation(
    monkeypatch,
) -> None:
    project = _project()
    session = _Session(project)
    server, _, mutation = _install(monkeypatch, session)
    proposal = _proposal(project)
    persist = AsyncMock(return_value=proposal)
    apply_patch = AsyncMock()
    monkeypatch.setattr(server, "persist_profile_proposal", persist)
    monkeypatch.setattr(server, "apply_profile_patch", apply_patch)
    source_id = uuid.uuid4()

    result = _call(
        server,
        "propose_project_profile_change",
        {
            "project_id": str(PROJECT_ID),
            "proposed_values": {"state": "VIC"},
            "evidence_references": [
                {"source_document_id": str(source_id), "locator": "page 2"}
            ],
            "confidence": 0.8,
        },
    )

    assert result["state"] == "pending"
    persist.assert_awaited_once()
    assert persist.await_args.kwargs["evidence_references"][0].source_document_id == source_id
    assert "required_scope" not in mutation.await_args.kwargs
    apply_patch.assert_not_awaited()
    assert project.profile_revision == 1


def test_profile_revision_conflict_is_stable_tool_error(monkeypatch) -> None:
    project = _project(profile_revision=2)
    session = _Session(project)
    server, _, _ = _install(monkeypatch, session)
    monkeypatch.setattr(
        server,
        "apply_profile_patch",
        AsyncMock(
            side_effect=ProfileRevisionConflict(
                expected_revision=1,
                current_revision=2,
            )
        ),
    )

    with pytest.raises(
        ToolError,
        match="profile_revision_conflict: expected=1, current=2",
    ):
        _call(
            server,
            "update_project_profile",
            {
                "project_id": str(PROJECT_ID),
                "expected_revision": 1,
                "changes": {"state": "VIC"},
            },
        )


def test_invalid_profile_value_is_rejected_without_commit(monkeypatch) -> None:
    project = _project()
    session = _Session(project)
    server, _, _ = _install(monkeypatch, session)

    with pytest.raises(ToolError, match="Unknown state"):
        _call(
            server,
            "update_project_profile",
            {
                "project_id": str(PROJECT_ID),
                "expected_revision": 1,
                "changes": {"state": "XX"},
            },
        )

    assert project.state is None
    assert project.profile_revision == 1
    assert session.committed is False


def test_accept_and_reject_tools_delegate_to_revisioned_proposal_services(
    monkeypatch,
) -> None:
    project = _project()
    session = _Session(project)
    server, _, _ = _install(monkeypatch, session)
    proposal = _proposal(project)
    accepted_change = ProjectProfileChange(
        profile=ProjectProfileView(
            project_id=project.id,
            profile_revision=2,
            state="VIC",
        ),
        previous_revision=1,
        new_revision=2,
        changed_fields=["state"],
        cleared_fields=[],
        overlay_status=OverlayStatus(ready=False),
        risk_flags=[],
    )
    accept = AsyncMock(
        return_value=ProfileProposalResolution(
            proposal=proposal.model_copy(update={"state": "accepted"}),
            profile_change=accepted_change,
        )
    )
    reject = AsyncMock(
        return_value=ProfileProposalResolution(
            proposal=proposal.model_copy(update={"state": "rejected"})
        )
    )
    monkeypatch.setattr(server, "accept_profile_proposal", accept)
    monkeypatch.setattr(server, "reject_profile_proposal", reject)

    accepted = _call(
        server,
        "accept_project_profile_proposal",
        {
            "project_id": str(PROJECT_ID),
            "proposal_id": str(proposal.id),
            "expected_revision": 1,
        },
    )
    rejected = _call(
        server,
        "reject_project_profile_proposal",
        {
            "project_id": str(PROJECT_ID),
            "proposal_id": str(proposal.id),
            "expected_revision": 1,
        },
    )

    assert accepted["proposal"]["state"] == "accepted"
    assert rejected["proposal"]["state"] == "rejected"
    assert accept.await_args.kwargs["expected_profile_revision"] == 1
    assert reject.await_args.kwargs["expected_profile_revision"] == 1


def test_cross_project_token_fails_before_profile_read(monkeypatch) -> None:
    from app.mcp_bridge import server

    project = _project()
    session = _Session(project)
    other_project = uuid.uuid4()
    token = mint_turn_token(
        user_id=USER_ID,
        project_id=other_project,
        secret=SECRET,
    )
    monkeypatch.setattr(
        server,
        "get_http_headers",
        lambda **_kwargs: {"authorization": f"Bearer {token}"},
    )
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    read = AsyncMock()
    monkeypatch.setattr(server, "read_profile", read)

    with pytest.raises(ToolError, match="not scoped to this project"):
        _call(
            server,
            "get_project_profile",
            {"project_id": str(PROJECT_ID)},
        )

    read.assert_not_awaited()
    assert session.get_count == 0
