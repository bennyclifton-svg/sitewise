import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app.config import settings
from app.mcp_bridge.tokens import mint_turn_token
from tests.conftest import run_async

SECRET = "test-secret"
USER_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()
OTHER_PROJECT_ID = uuid.uuid4()
COMPARISON_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def _token_secret(monkeypatch):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)


class _ScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        return self._values


class _ExecuteResult:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._values)

    def scalar_one_or_none(self) -> Any | None:
        return self._values[0] if self._values else None


class _Session:
    """Stub async session: session.get -> project, execute -> queued results."""

    def __init__(self, *, project: Any = None, execute_values: list[list[Any]] | None = None) -> None:
        self.project = project
        self.execute_values = execute_values or []

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, model: type, item_id: uuid.UUID) -> Any:
        if self.project is not None and item_id == self.project.id:
            return self.project
        return None

    async def execute(self, statement: Any) -> _ExecuteResult:
        return _ExecuteResult(self.execute_values.pop(0))


def _project(project_id: uuid.UUID = PROJECT_ID) -> SimpleNamespace:
    return SimpleNamespace(id=project_id, owner_user_id=USER_ID)


def _comparison(project_id: uuid.UUID = PROJECT_ID) -> SimpleNamespace:
    return SimpleNamespace(
        id=COMPARISON_ID,
        project_id=project_id,
        status="intake",
        quotes=[
            SimpleNamespace(id=uuid.uuid4(), builder_name="NexusBuilt", stage="intake"),
        ],
    )


def _install(monkeypatch, session: _Session, *, token_project: uuid.UUID = PROJECT_ID):
    from app.mcp_bridge import server

    token = mint_turn_token(user_id=USER_ID, project_id=token_project, secret=SECRET)
    monkeypatch.setattr(
        server, "get_http_headers", lambda: {"authorization": f"Bearer {token}"}
    )
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    return server


def test_list_tender_comparisons_returns_summaries(monkeypatch):
    session = _Session(project=_project(), execute_values=[[_comparison()]])
    server = _install(monkeypatch, session)

    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool(
                "list_tender_comparisons", {"project_id": str(PROJECT_ID)}
            )

    result = run_async(_run())
    summaries = result.data
    assert len(summaries) == 1
    assert summaries[0]["id"] == str(COMPARISON_ID)
    assert summaries[0]["status"] == "intake"
    assert summaries[0]["quotes"][0]["builder"] == "NexusBuilt"
    assert summaries[0]["quotes"][0]["stage"] == "intake"


def test_cross_project_token_rejected(monkeypatch):
    session = _Session(project=_project(), execute_values=[[_comparison()]])
    server = _install(monkeypatch, session, token_project=OTHER_PROJECT_ID)

    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool(
                "list_tender_comparisons", {"project_id": str(PROJECT_ID)}
            )

    with pytest.raises(ToolError, match="scoped"):
        run_async(_run())


def test_get_comparison_in_other_project_rejected(monkeypatch):
    comparison = _comparison(project_id=OTHER_PROJECT_ID)
    session = _Session(project=_project(), execute_values=[[comparison]])
    server = _install(monkeypatch, session, token_project=PROJECT_ID)

    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool(
                "get_tender_comparison", {"comparison_id": str(COMPARISON_ID)}
            )

    with pytest.raises(ToolError, match="scoped"):
        run_async(_run())
