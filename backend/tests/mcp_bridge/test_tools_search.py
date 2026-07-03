import uuid
import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app.config import settings
from app.agent.status_bus import agent_turn_status_bus
from app.mcp_bridge.tokens import mint_turn_token
from tests.conftest import run_async

SECRET = "test-secret"
USER_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def _token_secret(monkeypatch):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)


class _Session:
    def __init__(self, *, project: Any = None) -> None:
        self.project = project

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, model: type, item_id: uuid.UUID) -> Any:
        if self.project is not None and item_id == self.project.id:
            return self.project
        return None


class _StubRetriever:
    instances: list["_StubRetriever"] = []

    def __init__(self, session: Any) -> None:
        self.session = session
        self.calls: list[dict] = []
        _StubRetriever.instances.append(self)

    async def retrieve(self, query: str, **kwargs: Any) -> list[Any]:
        self.calls.append({"query": query, **kwargs})
        return [
            SimpleNamespace(
                filename="geotech-report.pdf",
                content="Bearing capacity 150 kPa at 1.2m depth.",
                score=0.042,
            )
        ]


def _project() -> SimpleNamespace:
    return SimpleNamespace(id=PROJECT_ID, owner_user_id=USER_ID, slug="test-project")


def _install(
    monkeypatch,
    session: _Session,
    *,
    token_project: uuid.UUID = PROJECT_ID,
    turn_id: uuid.UUID | None = None,
):
    from app.mcp_bridge import server

    _StubRetriever.instances = []
    token = mint_turn_token(
        user_id=USER_ID,
        project_id=token_project,
        turn_id=turn_id,
        secret=SECRET,
    )
    monkeypatch.setattr(
        server,
        "get_http_headers",
        lambda **_kwargs: {"authorization": f"Bearer {token}"},
    )
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    monkeypatch.setattr(server, "DocumentRetriever", _StubRetriever)
    return server


def _call(server, arguments: dict) -> Any:
    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool("search_documents", arguments)

    return run_async(_run())


def test_authorized_search_returns_mapped_passages(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session)

    result = _call(
        server, {"project_id": str(PROJECT_ID), "query": "bearing capacity"}
    )

    data = result.data
    assert data == [
        {
            "document": "geotech-report.pdf",
            "snippet": "Bearing capacity 150 kPa at 1.2m depth.",
            "score": 0.042,
        }
    ]

    (retriever,) = _StubRetriever.instances
    (call,) = retriever.calls
    assert call["query"] == "bearing capacity"
    filters = call["filters"]
    assert filters.active_project == "test-project"
    assert filters.include_platform_knowledge is False


def test_authorized_search_publishes_tool_status(monkeypatch):
    turn_id = uuid.uuid4()
    session = _Session(project=_project())
    server = _install(monkeypatch, session, turn_id=turn_id)

    async def _run():
        async with agent_turn_status_bus.subscribe(str(turn_id)) as statuses:
            async with Client(server.mcp) as client:
                result = await client.call_tool(
                    "search_documents",
                    {"project_id": str(PROJECT_ID), "query": "bearing capacity"},
                )
            running = await asyncio.wait_for(anext(statuses), timeout=0.1)
            done = await asyncio.wait_for(anext(statuses), timeout=0.1)
            return result, running, done

    result, running, done = run_async(_run())

    assert result.data
    assert running["tool"] == "search_documents"
    assert running["state"] == "running"
    assert done["tool"] == "search_documents"
    assert done["state"] == "done"


def test_unauthorized_search_rejected(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session, token_project=uuid.uuid4())

    with pytest.raises(ToolError, match="scoped"):
        _call(server, {"project_id": str(PROJECT_ID), "query": "bearing capacity"})

    assert _StubRetriever.instances == []
