import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastmcp.exceptions import ToolError

from app.mcp_bridge.auth import ToolAuthorization
from app.mcp_bridge.tokens import TurnClaims
from app.workflows.transmittal import WORKFLOW_TYPE
from tests.conftest import run_async


USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
TURN_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
WORKSPACE_FILE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


class _Session:
    def __init__(self, turn) -> None:
        self.turn = turn
        self.commit = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, _model, _id):
        return self.turn


def _turn_context() -> dict:
    return {
        "selected_documents": [
            {
                "workspace_file_id": str(WORKSPACE_FILE_ID),
                "workspace_path": "04-projects/demo/02-design/A101.pdf",
                "filename": "A101.pdf",
                "content_hash": "a" * 64,
                "size_bytes": 1234,
                "document_number": "A101",
                "title": "Ground floor plan",
                "revision": "C02",
                "category": "Architectural",
            }
        ]
    }


def _install(monkeypatch, *, turn_context: dict):
    from app.mcp_bridge import server

    session = _Session(SimpleNamespace(input_context=turn_context))
    authorization = ToolAuthorization(
        project=SimpleNamespace(id=PROJECT_ID, owner_user_id=USER_ID),
        claims=TurnClaims(
            user_id=USER_ID,
            project_id=PROJECT_ID,
            turn_id=TURN_ID,
            expires_at=4_000_000_000,
        ),
    )
    persist = AsyncMock(return_value=(SimpleNamespace(id=uuid.uuid4()), True))
    locks = AsyncMock()
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    monkeypatch.setattr(server, "authorize_project_mutation_with_claims", AsyncMock(return_value=authorization))
    monkeypatch.setattr(server, "read_project_snapshot", AsyncMock(return_value=object()))
    monkeypatch.setattr(server, "capability_block_message", lambda *_args: None)
    monkeypatch.setattr(server, "persist_workflow_run", persist)
    monkeypatch.setattr(server, "lock_workflow_inputs", locks)
    monkeypatch.setattr(server.agent_turn_status_bus, "publish", AsyncMock())
    monkeypatch.setattr(
        server,
        "WorkflowRunView",
        SimpleNamespace(
            model_validate=lambda _run: SimpleNamespace(
                model_dump=lambda **_kwargs: {"status": "queued"}
            )
        ),
    )
    return server, session, persist, locks


def _args() -> dict:
    return {
        "project_id": str(PROJECT_ID),
        "idempotency_key": "turn-1:transmittal",
        "expected_snapshot_fingerprint": "a" * 64,
        "expected_profile_revision": 2,
        "expected_decision_set_revision": 3,
    }


def test_transmittal_uses_only_the_server_stored_turn_selection(monkeypatch) -> None:
    server, session, persist, locks = _install(monkeypatch, turn_context=_turn_context())

    result = run_async(
        server.start_transmittal(
            **_args(),
            recipient="Builder@example.com",
            purpose="Issue for construction",
        )
    )

    assert result == {"status": "queued"}
    assert persist.await_args.kwargs["workflow_type"] == WORKFLOW_TYPE
    parameters = persist.await_args.kwargs["request"].parameters
    assert parameters["recipient"] == "Builder@example.com"
    assert parameters["purpose"] == "Issue for construction"
    assert parameters["selected_documents"][0]["workspace_file_id"] == str(WORKSPACE_FILE_ID)
    assert locks.await_args.kwargs["workspace_file_ids"] == [WORKSPACE_FILE_ID]
    assert session.commit.await_count == 1


def test_transmittal_rejects_a_turn_without_document_register_selection(monkeypatch) -> None:
    server, _session, persist, locks = _install(monkeypatch, turn_context={})

    with pytest.raises(ToolError, match="Select one or more project documents"):
        run_async(server.start_transmittal(**_args()))

    persist.assert_not_awaited()
    locks.assert_not_awaited()
