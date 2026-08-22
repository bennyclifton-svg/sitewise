from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastmcp import Client

from app.agent.mutation_intent import PROCUREMENT_STRATEGY_MUTATION_SCOPE
from app.database.project import Project
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
STRATEGY_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
ROW_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


class _Session:
    committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc_info):
        return None

    async def commit(self):
        self.committed = True


def _authorization():
    project = Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="demo",
        title="Demo",
        workspace_path="04-projects/demo",
        phase="procurement",
        project_metadata={},
    )
    return SimpleNamespace(
        project=project,
        claims=SimpleNamespace(user_id=USER_ID, turn_id=uuid.uuid4()),
    )


def _call(server, name: str, arguments: dict):
    async def run():
        async with Client(server.mcp) as client:
            return await client.call_tool(name, arguments)

    return run_async(run()).data


def _install(monkeypatch):
    from app.mcp_bridge import server

    session = _Session()
    authorization = _authorization()
    access = AsyncMock(return_value=authorization)
    mutation = AsyncMock(return_value=authorization)
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    monkeypatch.setattr(server, "get_http_headers", lambda **_kwargs: {})
    monkeypatch.setattr(server, "authorize_project_access_with_claims", access)
    monkeypatch.setattr(server, "authorize_project_mutation_with_claims", mutation)
    monkeypatch.setattr(server.agent_turn_status_bus, "publish", AsyncMock())
    return server, session, access, mutation


def test_procurement_strategy_tools_are_direct_and_discoverable(monkeypatch) -> None:
    from app.agent.pi_process import PI_MCP_DIRECT_TOOLS

    expected = {
        "get_procurement_strategy",
        "refresh_procurement_strategy",
        "apply_procurement_strategy_operations",
        "search_procurement_candidates",
    }
    assert expected.issubset(PI_MCP_DIRECT_TOOLS)

    server, *_ = _install(monkeypatch)

    async def run():
        async with Client(server.mcp) as client:
            return {tool.name for tool in await client.list_tools()}

    assert expected.issubset(run_async(run()))


def test_apply_operations_requires_strategy_scope_and_publishes_resource(
    monkeypatch,
) -> None:
    server, session, _access, mutation = _install(monkeypatch)
    strategy = SimpleNamespace(id=STRATEGY_ID, revision=4)
    apply = AsyncMock(return_value=strategy)
    snapshot = AsyncMock(return_value={"id": str(STRATEGY_ID), "revision": 4})
    monkeypatch.setattr(server, "persist_procurement_strategy_operations", apply)
    monkeypatch.setattr(server, "procurement_strategy_snapshot", snapshot)

    result = _call(
        server,
        "apply_procurement_strategy_operations",
        {
            "project_id": str(PROJECT_ID),
            "expected_revision": 3,
            "operations": [
                {
                    "operation": "UPDATE_ROW",
                    "row_id": str(ROW_ID),
                    "status": "shortlisting",
                }
            ],
        },
    )

    assert result["revision"] == 4
    assert session.committed is True
    assert mutation.await_args.kwargs["required_scope"] == (
        PROCUREMENT_STRATEGY_MUTATION_SCOPE
    )
    operation = apply.await_args.kwargs["operations"][0]
    assert operation["row_id"] == ROW_ID
    assert operation["status"] == "shortlisting"
    publish = server.agent_turn_status_bus.publish
    assert any(
        call.kwargs.get("resourceType") == "procurement_strategy"
        for call in publish.await_args_list
    )


def test_candidate_search_is_read_only_and_returns_sourced_results(monkeypatch) -> None:
    server, _session, access, mutation = _install(monkeypatch)
    research = SimpleNamespace(
        search=AsyncMock(
            return_value={
                "discipline_code": "consultant.structural",
                "results": [
                    {
                        "title": "Example Structural",
                        "url": "https://example.com",
                        "source_type": "candidate_web_result",
                    }
                ],
            }
        )
    )
    monkeypatch.setattr(
        server, "get_procurement_candidate_research", lambda: research
    )

    result = _call(
        server,
        "search_procurement_candidates",
        {
            "project_id": str(PROJECT_ID),
            "discipline_code": "consultant.structural",
            "location": "Sydney NSW",
            "max_results": 3,
        },
    )

    assert result["results"][0]["url"] == "https://example.com"
    access.assert_awaited_once()
    mutation.assert_not_awaited()
