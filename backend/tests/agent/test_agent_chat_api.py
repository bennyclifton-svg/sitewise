import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.auth.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.database.chat_message import ChatMessage
from app.database.chat_thread import ChatThread
from app.database.session import get_db
from app.main import fastapi_app as app

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
PROJECT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
THREAD_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
NOW = datetime(2026, 7, 3, 12, 0, 0, tzinfo=timezone.utc)

BODY = {
    "threadId": str(THREAD_ID),
    "messages": [
        {
            "role": "user",
            "parts": [{"type": "text", "text": "Compare the tender quotes"}],
        }
    ],
}


def _thread(
    *,
    owner_id: uuid.UUID = USER_ID,
    project_id: uuid.UUID | None = PROJECT_ID,
    title: str | None = "Test thread",
) -> ChatThread:
    return ChatThread(
        id=THREAD_ID,
        user_id=owner_id,
        project_id=project_id,
        title=title,
        created_at=NOW,
        updated_at=NOW,
    )


class _SessionContext:
    def __init__(self, session) -> None:
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *exc_info):
        return None


class _SessionFactory:
    def __init__(self, session) -> None:
        self.session = session

    def __call__(self) -> _SessionContext:
        return _SessionContext(self.session)


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_session: AsyncMock, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    current_user = CurrentUser(id=USER_ID, email="user@example.com")

    async def override_get_db():
        yield mock_session

    monkeypatch.setattr(settings, "agent_runtime_enabled", True)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_agent_stream_requires_auth(mock_session: AsyncMock) -> None:
    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        response = client.post("/chat/agent/stream", json=BODY)
    app.dependency_overrides.clear()

    assert response.status_code == 401


def test_agent_stream_forbidden_for_other_users_thread(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        chat_api,
        "get_thread_by_id",
        AsyncMock(return_value=_thread(owner_id=OTHER_USER_ID)),
    )

    response = client.post("/chat/agent/stream", json=BODY)

    assert response.status_code == 403


def test_agent_stream_requires_active_entitlement(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(chat_api, "get_thread_by_id", AsyncMock(return_value=_thread()))
    monkeypatch.setattr(
        chat_api,
        "require_active_entitlement",
        AsyncMock(
            side_effect=HTTPException(
                status_code=402,
                detail="Subscription required",
            )
        ),
    )

    response = client.post("/chat/agent/stream", json=BODY)

    assert response.status_code == 402


def test_agent_stream_persists_user_then_successful_assistant_message(
    client: TestClient,
    mock_session: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    thread = _thread(title=None)
    assistant_session = AsyncMock()
    seen: dict[str, str] = {}

    async def fake_create_message(session, *, thread_id, role, content, message_data=None):
        return ChatMessage(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role=role,
            content=content,
            message_data=message_data,
            created_at=NOW,
        )

    async def fake_stream_hermes_turn(prompt, *, mcp_url, turn_token, cwd):
        seen.update(
            {
                "prompt": prompt,
                "mcp_url": mcp_url,
                "turn_token": turn_token,
                "cwd": cwd,
            }
        )
        yield "Hello"
        yield " there"

    token_mint = Mock(return_value="turn-token")

    monkeypatch.setattr(settings, "agent_workspace_root", tmp_path)
    monkeypatch.setattr(settings, "agent_mcp_url", "http://testserver/mcp")
    monkeypatch.setattr(chat_api, "get_thread_by_id", AsyncMock(return_value=thread))
    monkeypatch.setattr(chat_api, "require_active_entitlement", AsyncMock())
    monkeypatch.setattr(
        chat_api,
        "require_project_owner",
        AsyncMock(return_value=SimpleNamespace(id=PROJECT_ID)),
    )
    monkeypatch.setattr(chat_api, "update_thread", AsyncMock(return_value=thread))
    monkeypatch.setattr(
        chat_api,
        "create_message",
        AsyncMock(side_effect=fake_create_message),
    )
    monkeypatch.setattr(chat_api, "mint_turn_token", token_mint)
    monkeypatch.setattr(chat_api, "stream_hermes_turn", fake_stream_hermes_turn)
    monkeypatch.setattr(
        chat_api,
        "get_session_factory",
        lambda: _SessionFactory(assistant_session),
    )

    with client.stream("POST", "/chat/agent/stream", json=BODY) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"type":"text-delta"' in body
    assert "Hello" in body
    assert '"type":"finish"' in body
    assert "[DONE]" in body
    assert seen == {
        "prompt": "Compare the tender quotes",
        "mcp_url": "http://testserver/mcp",
        "turn_token": "turn-token",
        "cwd": str(tmp_path / str(PROJECT_ID) / str(THREAD_ID)),
    }
    token_mint.assert_called_once()
    assert token_mint.call_args.kwargs["user_id"] == USER_ID
    assert token_mint.call_args.kwargs["project_id"] == PROJECT_ID
    assert isinstance(token_mint.call_args.kwargs["turn_id"], uuid.UUID)
    assert mock_session.commit.await_count == 1
    assert assistant_session.commit.await_count == 1

    calls = chat_api.create_message.await_args_list
    assert calls[0].kwargs["role"] == "user"
    assert calls[0].kwargs["content"] == "Compare the tender quotes"
    assert calls[1].kwargs["role"] == "assistant"
    assert calls[1].kwargs["content"] == "Hello there"
    assert calls[1].kwargs["message_data"]["agent"]["runtime"] == "hermes"


def test_agent_cancel_requires_thread_owner_and_cancels(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cancel = AsyncMock(return_value=True)

    monkeypatch.setattr(chat_api, "get_thread_by_id", AsyncMock(return_value=_thread()))
    monkeypatch.setattr(chat_api.agent_turn_registry, "cancel", cancel)

    response = client.post(f"/chat/agent/{THREAD_ID}/cancel")

    assert response.status_code == 200
    assert response.json() == {"cancelled": True}
    cancel.assert_awaited_once_with(str(THREAD_ID))
