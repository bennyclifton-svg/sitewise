"""Integration proof: the MCP server is mounted at /mcp and auth is on by default."""
import json
from types import SimpleNamespace
import uuid
from unittest.mock import AsyncMock

import httpx

from tests.conftest import run_async

ACCEPT = "application/json, text/event-stream"


def _parse_message(response: httpx.Response) -> dict:
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("text/event-stream"):
        data_lines = [
            line[len("data: "):]
            for line in response.text.splitlines()
            if line.startswith("data: ")
        ]
        assert data_lines, f"no SSE data in body: {response.text!r}"
        return json.loads(data_lines[-1])
    return response.json()


class _Session:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _session_factory():
    return _Session()


async def _initialize_mcp(client: httpx.AsyncClient) -> str:
    init_response = await client.post(
        "/mcp/",
        headers={"Accept": ACCEPT},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "probe", "version": "0"},
            },
        },
    )
    assert init_response.status_code == 200, init_response.text
    init_message = _parse_message(init_response)
    assert init_message["result"]["serverInfo"]["name"] == "clerk"

    session_id = init_response.headers.get("mcp-session-id")
    assert session_id, "server did not issue a session id"

    notified = await client.post(
        "/mcp/",
        headers={"Accept": ACCEPT, "mcp-session-id": session_id},
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert notified.status_code in (200, 202), notified.text
    return session_id


def test_mcp_initialize_and_unauthenticated_tool_call_rejected():
    from app.main import fastapi_app

    async def _run():
        async with fastapi_app.router.lifespan_context(fastapi_app):
            transport = httpx.ASGITransport(app=fastapi_app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                session_id = await _initialize_mcp(client)
                session_headers = {"Accept": ACCEPT, "mcp-session-id": session_id}

                call_response = await client.post(
                    "/mcp/",
                    headers=session_headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "list_tender_comparisons",
                            "arguments": {"project_id": str(uuid.uuid4())},
                        },
                    },
                )
                assert call_response.status_code == 200, call_response.text
                call_message = _parse_message(call_response)
                result = call_message["result"]
                assert result["isError"] is True
                text = " ".join(
                    block.get("text", "") for block in result["content"]
                )
                assert "turn token" in text

    run_async(_run())


def test_mounted_tool_call_passes_authorization_header(monkeypatch):
    from app.main import fastapi_app
    from app.mcp_bridge import server

    project_id = uuid.uuid4()
    seen: dict[str, str | None] = {}

    async def authorize_project_access(session, *, authorization_header, project_id):
        seen["authorization_header"] = authorization_header
        return SimpleNamespace(
            id=project_id,
            owner_user_id=uuid.uuid4(),
            slug="test-project",
        )

    monkeypatch.setattr(server, "get_session_factory", lambda: _session_factory)
    monkeypatch.setattr(server, "authorize_project_access", authorize_project_access)
    monkeypatch.setattr(server, "list_comparisons", AsyncMock(return_value=[]))

    async def _run():
        async with fastapi_app.router.lifespan_context(fastapi_app):
            transport = httpx.ASGITransport(app=fastapi_app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                session_id = await _initialize_mcp(client)
                call_response = await client.post(
                    "/mcp/",
                    headers={
                        "Accept": ACCEPT,
                        "mcp-session-id": session_id,
                        "Authorization": "Bearer smoke-token",
                    },
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "list_tender_comparisons",
                            "arguments": {"project_id": str(project_id)},
                        },
                    },
                )
                assert call_response.status_code == 200, call_response.text
                call_message = _parse_message(call_response)
                assert call_message["result"]["isError"] is False
                assert seen["authorization_header"] == "Bearer smoke-token"

    run_async(_run())
