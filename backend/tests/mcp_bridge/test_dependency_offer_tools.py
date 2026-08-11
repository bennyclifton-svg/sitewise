"""F6 MCP authorization and project-isolation for dependency offers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app.config import settings
from app.database.project import Project
from app.mcp_bridge.auth import ToolAuthError
from app.mcp_bridge.tokens import mint_turn_token
from app.projects.project_knowledge import (
    SharedProjectObjectUpdate,
    list_shared_project_objects,
    upsert_shared_project_object,
)
from app.projects.dependencies import list_dependency_offers
from tests.conftest import run_async

SECRET = "test-secret"
USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
OTHER_PROJECT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)


class _Session:
    def __init__(self, project: Project) -> None:
        self.project = project
        self.committed = False
        self.added: list[Any] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc_info):
        return None

    async def get(self, _model, item_id, **_kwargs):
        return self.project if item_id == self.project.id else None

    async def commit(self):
        self.committed = True

    async def refresh(self, _project, **_kwargs):
        return None

    def add(self, row) -> None:
        self.added.append(row)

    async def flush(self) -> None:
        return None


def _project(project_id: uuid.UUID = PROJECT_ID) -> Project:
    return Project(
        id=project_id,
        owner_user_id=USER_ID,
        slug="demo",
        title="Demo",
        workspace_path="04-projects/demo",
        phase="brief-planning",
        project_metadata={},
    )


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
    monkeypatch.setattr(
        server,
        "enrich_dependency_offers",
        AsyncMock(
            side_effect=lambda _session, project, owner_user_id: list_dependency_offers(
                project
            )
        ),
    )
    return server, access, mutation


def _call(server, name: str, arguments: dict) -> Any:
    async def run():
        async with Client(server.mcp) as client:
            return await client.call_tool(name, arguments)

    return run_async(run()).data


def test_list_shared_project_knowledge_and_offers(monkeypatch) -> None:
    project = _project()
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="hydraulic",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={"name": "ABC Engineering"},
        ),
        source="user",
    )
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="hydraulic",
        update=SharedProjectObjectUpdate(
            expected_revision=1,
            value={"name": "Fluid Design"},
        ),
        source="user",
    )
    session = _Session(project)
    server, access, _mutation = _install(monkeypatch, session)

    listed = _call(
        server,
        "list_shared_project_knowledge",
        {"project_id": str(PROJECT_ID)},
    )
    assert len(listed) == 1
    assert listed[0]["id"] == "hydraulic"

    one = _call(
        server,
        "get_shared_project_knowledge",
        {
            "project_id": str(PROJECT_ID),
            "kind": "consultant",
            "object_id": "hydraulic",
        },
    )
    assert one["value"]["name"] == "Fluid Design"

    offers = _call(
        server,
        "list_dependency_update_offers",
        {"project_id": str(PROJECT_ID)},
    )
    assert len(offers) == 1
    assert offers[0]["source"]["object_id"] == "hydraulic"
    access.assert_called()


def test_dependency_tools_reject_unauthorized_project(monkeypatch) -> None:
    session = _Session(_project())
    server, access, _mutation = _install(monkeypatch, session)
    access.side_effect = ToolAuthError("project access denied")

    with pytest.raises(ToolError, match="project access denied"):
        _call(
            server,
            "list_dependency_update_offers",
            {"project_id": str(OTHER_PROJECT_ID)},
        )


def test_reject_dependency_offer_requires_mutation_auth(monkeypatch) -> None:
    project = _project()
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="hydraulic",
        update=SharedProjectObjectUpdate(
            expected_revision=0, value={"name": "ABC"}
        ),
        source="user",
    )
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="hydraulic",
        update=SharedProjectObjectUpdate(
            expected_revision=1, value={"name": "Fluid Design"}
        ),
        source="user",
    )
    offer_id = list_dependency_offers(project)[0].id
    session = _Session(project)
    server, _access, mutation = _install(monkeypatch, session)
    mutation.side_effect = ToolAuthError("mutation denied")

    with pytest.raises(ToolError, match="mutation denied"):
        _call(
            server,
            "reject_dependency_update_offer",
            {"project_id": str(PROJECT_ID), "offer_id": offer_id},
        )


def test_reject_dependency_offer_clears_entries(monkeypatch) -> None:
    project = _project()
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="hydraulic",
        update=SharedProjectObjectUpdate(
            expected_revision=0, value={"name": "ABC"}
        ),
        source="user",
    )
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="hydraulic",
        update=SharedProjectObjectUpdate(
            expected_revision=1, value={"name": "Fluid Design"}
        ),
        source="user",
    )
    offer_id = list_dependency_offers(project)[0].id
    session = _Session(project)
    server, _access, mutation = _install(monkeypatch, session)

    result = _call(
        server,
        "reject_dependency_update_offer",
        {"project_id": str(PROJECT_ID), "offer_id": offer_id},
    )
    assert result["status"] == "rejected"
    assert list_dependency_offers(project) == []
    mutation.assert_called()
    assert session.committed is True


def test_upsert_shared_project_knowledge_writes_ffe_item(monkeypatch) -> None:
    project = _project()
    session = _Session(project)
    server, _access, mutation = _install(monkeypatch, session)

    result = _call(
        server,
        "upsert_shared_project_knowledge",
        {
            "project_id": str(PROJECT_ID),
            "kind": "ffe_item",
            "object_id": "freestanding-bath",
            "expected_revision": 0,
            "value": {
                "item": "Freestanding bath",
                "location": "TBC",
                "quantity": "TBC",
                "finish": "TBC",
                "status": "To be confirmed",
            },
        },
    )

    assert result["id"] == "freestanding-bath"
    assert result["kind"] == "ffe_item"
    assert result["revision"] == 1
    assert result["value"]["item"] == "Freestanding bath"
    assert result["source"] == "ai"
    mutation.assert_called()
    assert session.committed is True
    listed = list_shared_project_objects(project, kind="ffe_item")
    assert len(listed) == 1
    assert listed[0].id == "freestanding-bath"


def test_upsert_shared_project_knowledge_requires_mutation_auth(monkeypatch) -> None:
    session = _Session(_project())
    server, _access, mutation = _install(monkeypatch, session)
    mutation.side_effect = ToolAuthError("mutation denied")

    with pytest.raises(ToolError, match="mutation denied"):
        _call(
            server,
            "upsert_shared_project_knowledge",
            {
                "project_id": str(PROJECT_ID),
                "kind": "ffe_item",
                "object_id": "freestanding-bath",
                "expected_revision": 0,
                "value": {"item": "Freestanding bath"},
            },
        )


def test_direct_tools_allowlist_includes_dependency_surface() -> None:
    from app.agent.pi_process import PI_MCP_DIRECT_TOOLS

    for name in (
        "list_shared_project_knowledge",
        "get_shared_project_knowledge",
        "upsert_shared_project_knowledge",
        "list_dependency_update_offers",
        "accept_dependency_update_offer",
        "reject_dependency_update_offer",
    ):
        assert name in PI_MCP_DIRECT_TOOLS


def test_turn_token_project_isolation_for_knowledge_read(monkeypatch) -> None:
    """Token minted for project A cannot authorize reads against project B."""
    from app.mcp_bridge import server

    project = _project(OTHER_PROJECT_ID)
    session = _Session(project)
    token = mint_turn_token(
        user_id=USER_ID, project_id=PROJECT_ID, secret=SECRET
    )
    monkeypatch.setattr(
        server,
        "get_http_headers",
        lambda **_kwargs: {"authorization": f"Bearer {token}"},
    )
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)

    with pytest.raises(ToolError):
        _call(
            server,
            "list_shared_project_knowledge",
            {"project_id": str(OTHER_PROJECT_ID)},
        )
