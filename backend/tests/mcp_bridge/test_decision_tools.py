import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastmcp import Client

from tests.conftest import run_async


PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


class _Session:
    committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc_info):
        return None

    async def commit(self):
        self.committed = True


def _row():
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        decision_id="procurement-route",
        section="Procurement",
        label="Procurement route",
        options=[{"value": "traditional", "label": "Traditional"}],
        selected="traditional",
        source="user",
        workflow_type="create_pmp",
        revision=3,
        locked=True,
        evidence_conflict=False,
        agent_suggestion=None,
        provenance={"interface": "http"},
        created_at=now,
        updated_at=now,
    )


def _call(server, name: str, arguments: dict):
    async def run():
        async with Client(server.mcp) as client:
            return await client.call_tool(name, arguments)

    return run_async(run()).data


def test_decision_read_and_update_tools_share_revision_contract(monkeypatch) -> None:
    from app.mcp_bridge import server

    session = _Session()
    row = _row()
    authorization = SimpleNamespace(
        project=SimpleNamespace(id=PROJECT_ID),
        claims=SimpleNamespace(user_id=uuid.uuid4(), turn_id=uuid.uuid4()),
    )
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    monkeypatch.setattr(server, "get_http_headers", lambda **_kwargs: {})
    monkeypatch.setattr(
        server,
        "authorize_project_access_with_claims",
        AsyncMock(return_value=authorization),
    )
    monkeypatch.setattr(
        server,
        "authorize_project_mutation_with_claims",
        AsyncMock(return_value=authorization),
    )
    monkeypatch.setattr(
        server,
        "read_project_decisions",
        AsyncMock(return_value=([row], 7)),
    )
    update = AsyncMock(return_value=(row, 8))
    monkeypatch.setattr(server, "persist_decision_update", update)

    listed = _call(server, "list_project_decisions", {"project_id": str(PROJECT_ID)})
    updated = _call(
        server,
        "update_project_decision",
        {
            "project_id": str(PROJECT_ID),
            "decision_id": row.decision_id,
            "selected": "traditional",
            "expected_revision": 3,
            "expected_set_revision": 7,
        },
    )

    assert listed["set_revision"] == 7
    assert listed["decisions"][0]["revision"] == 3
    assert updated["set_revision"] == 8
    assert update.await_args.kwargs["expected_revision"] == 3
    assert update.await_args.kwargs["expected_set_revision"] == 7
    assert session.committed is True


def test_snapshot_tool_returns_shared_snapshot_version(monkeypatch) -> None:
    from app.mcp_bridge import server

    session = _Session()
    owner_user_id = uuid.uuid4()
    authorization = SimpleNamespace(
        project=SimpleNamespace(id=PROJECT_ID, owner_user_id=owner_user_id),
        claims=SimpleNamespace(user_id=owner_user_id, turn_id=uuid.uuid4()),
    )
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    monkeypatch.setattr(server, "get_http_headers", lambda **_kwargs: {})
    monkeypatch.setattr(
        server,
        "authorize_project_access_with_claims",
        AsyncMock(return_value=authorization),
    )
    read = AsyncMock(
        return_value=SimpleNamespace(
            model_dump=lambda **_kwargs: {
                "schema_version": 1,
                "content_fingerprint": "snapshot-fingerprint",
            }
        )
    )
    monkeypatch.setattr(server, "read_project_snapshot", read)

    result = _call(server, "get_project_snapshot", {"project_id": str(PROJECT_ID)})

    assert result["schema_version"] == 1
    assert result["content_fingerprint"] == "snapshot-fingerprint"
    assert read.await_args.kwargs["owner_user_id"] == owner_user_id
