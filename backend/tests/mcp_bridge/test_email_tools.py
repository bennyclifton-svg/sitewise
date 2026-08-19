"""X1 Stage 19: MCP email tools are project-scoped; forbidden send/delete names absent."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

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
TURN_ID = uuid.uuid4()
EMAIL_ID = uuid.uuid4()

ALLOWED_EMAIL_TOOLS = {
    "search_project_email",
    "read_email_thread",
    "get_email_attachment",
    "list_project_correspondence",
    "create_email_draft",
    "reply_email_draft",
    "forward_email_draft",
    "link_email_to_project",
    "propose_email_action",
    "propose_project_decision",
}

FORBIDDEN_EMAIL_TOOLS = {
    "send_email_unattended",
    "delete_email",
    "change_mailbox_rules",
    "bulk_forward",
    "send_email",
}


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)


class _Session:
    def __init__(self, *, project: Any) -> None:
        self.project = project
        self.commit = AsyncMock()
        self.flush = AsyncMock()
        self.add = lambda _obj: None

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, model: type, item_id: uuid.UUID, **_kwargs: Any) -> Any:
        if item_id == self.project.id:
            return self.project
        return None

    async def execute(self, _statement: Any) -> Any:
        return SimpleNamespace(
            all=lambda: [],
            scalars=lambda: SimpleNamespace(all=lambda: []),
            scalar_one_or_none=lambda: None,
        )


def _project(project_id: uuid.UUID = PROJECT_ID) -> SimpleNamespace:
    return SimpleNamespace(
        id=project_id,
        owner_user_id=USER_ID,
        slug="test-project",
    )


def _install(
    monkeypatch: pytest.MonkeyPatch,
    session: _Session,
    *,
    token_project: uuid.UUID = PROJECT_ID,
    turn_id: uuid.UUID | None = None,
):
    from app.mcp_bridge import server

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
    return server


def _call(server: Any, name: str, arguments: dict) -> Any:
    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool(name, arguments)

    return run_async(_run())


def _tool_names(server: Any) -> set[str]:
    async def _run():
        async with Client(server.mcp) as client:
            tools = await client.list_tools()
            return {tool.name for tool in tools}

    return run_async(_run())


def test_forbidden_email_tool_names_are_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    server = _install(monkeypatch, _Session(project=_project()))
    names = _tool_names(server)
    for allowed in ALLOWED_EMAIL_TOOLS:
        assert allowed in names, allowed
    for forbidden in FORBIDDEN_EMAIL_TOOLS:
        assert forbidden not in names, forbidden
    assert "send_email_draft" not in names


def test_search_project_email_is_project_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _Session(project=_project())
    server = _install(monkeypatch, session)
    search = AsyncMock(
        return_value=[
            {
                "email_id": str(EMAIL_ID),
                "project_id": str(PROJECT_ID),
                "subject": "Fee proposal",
            }
        ]
    )
    monkeypatch.setattr(server, "search_project_emails", search)

    with pytest.raises(ToolError, match="scoped"):
        _call(
            server,
            "search_project_email",
            {"project_id": str(OTHER_PROJECT_ID), "query": "fee"},
        )
    search.assert_not_awaited()

    result = _call(
        server,
        "search_project_email",
        {"project_id": str(PROJECT_ID), "query": "fee"},
    )
    search.assert_awaited()
    assert search.await_args.kwargs["project_id"] == PROJECT_ID
    assert result.data[0]["project_id"] == str(PROJECT_ID)


def test_create_email_draft_requires_mutation_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _Session(project=_project())
    server = _install(monkeypatch, session, turn_id=None)

    with pytest.raises(ToolError, match="durable turn"):
        _call(
            server,
            "create_email_draft",
            {
                "project_id": str(PROJECT_ID),
                "to_addresses": ["qs@consultant.com"],
                "subject": "Re: Fee proposal",
                "body_text": "Thanks.",
            },
        )
