import uuid
from types import SimpleNamespace
from typing import Any

from fastmcp import Client

from app.mcp_bridge.auth import ToolAuthorization
from app.mcp_bridge.tokens import TurnClaims
from tests.conftest import run_async

USER_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()
TURN_ID = uuid.uuid4()


class _Session:
    committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def commit(self):
        self.committed = True

    async def rollback(self):
        return None


def test_start_tender_comparison_delegates_to_atomic_intake(monkeypatch) -> None:
    from app.mcp_bridge import server

    session = _Session()
    captured: dict[str, Any] = {}
    claims = TurnClaims(user_id=USER_ID, project_id=PROJECT_ID, turn_id=TURN_ID, expires_at=4_000_000_000)
    authorization = ToolAuthorization(
        project=SimpleNamespace(id=PROJECT_ID, owner_user_id=USER_ID),
        claims=claims,
    )

    async def authorize(*args, **kwargs):
        return authorization

    async def create(session_arg, *, request, owner_user_id):
        captured.update(request=request, owner_user_id=owner_user_id, session=session_arg)
        return SimpleNamespace(model_dump=lambda **kwargs: {"comparison": {"id": "comparison-1"}, "idempotent_replay": False})

    monkeypatch.setattr(server, "authorize_project_mutation_with_claims", authorize)
    monkeypatch.setattr(server.tender_intake, "create_immutable_intake", create)
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    monkeypatch.setattr(server, "get_http_headers", lambda **kwargs: {"authorization": "Bearer test"})

    async def call():
        async with Client(server.mcp) as client:
            return await client.call_tool("start_tender_comparison", {
                "project_id": str(PROJECT_ID),
                "expected_profile_revision": 7,
                "expected_selection_revision": 3,
                "context_overrides": {"region": "metro", "spec_level": "mid"},
            })

    result = run_async(call())
    assert result.data["comparison"]["id"] == "comparison-1"
    assert captured["request"].expected_profile_revision == 7
    assert captured["request"].expected_selection_revision == 3
    assert captured["request"].turn_id == str(TURN_ID)
    assert captured["owner_user_id"] == USER_ID
    assert session.committed is True
