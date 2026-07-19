import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.chat import require_thread_owner
from app.auth.dependencies import CurrentUser, get_current_user
from app.database.chat_message import ChatMessage
from app.database.chat_thread import ChatThread
from app.database.session import get_db
from app.main import app as cors_app
from app.main import fastapi_app as app

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
THREAD_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
NOW = datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc)


def _thread(owner_id: uuid.UUID = USER_ID) -> ChatThread:
    return ChatThread(
        id=THREAD_ID,
        user_id=owner_id,
        title="Test thread",
        created_at=NOW,
        updated_at=NOW,
    )


def _message() -> ChatMessage:
    return ChatMessage(
        id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        thread_id=THREAD_ID,
        role="user",
        content="Hello",
        message_data=None,
        created_at=NOW,
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_session: AsyncMock) -> TestClient:
    current_user = CurrentUser(id=USER_ID, email="user@example.com")

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_require_thread_owner_returns_thread() -> None:
    thread = _thread()
    assert require_thread_owner(thread, USER_ID) is thread


def test_require_thread_owner_not_found() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_thread_owner(None, USER_ID)
    assert exc_info.value.status_code == 404


def test_require_thread_owner_forbidden() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_thread_owner(_thread(owner_id=OTHER_USER_ID), USER_ID)
    assert exc_info.value.status_code == 403


def test_get_threads_returns_user_threads(client: TestClient, mock_session: AsyncMock) -> None:
    thread = _thread()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "app.api.chat.list_threads_page",
            AsyncMock(return_value=([thread], None)),
        )
        response = client.get("/chat/threads")

    assert response.status_code == 200
    payload = response.json()
    assert payload["threads"][0]["id"] == str(THREAD_ID)
    assert payload["threads"][0]["title"] == "Test thread"


def test_post_thread_creates_thread(client: TestClient, mock_session: AsyncMock) -> None:
    thread = _thread()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.api.chat.ensure_user_exists", AsyncMock())
        patch.setattr("app.api.chat.create_thread", AsyncMock(return_value=thread))
        response = client.post("/chat/threads", json={"title": "Test thread"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == str(THREAD_ID)


def test_get_thread_returns_thread(client: TestClient, mock_session: AsyncMock) -> None:
    thread = _thread()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.api.chat.get_thread_by_id", AsyncMock(return_value=thread))
        response = client.get(f"/chat/threads/{THREAD_ID}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(THREAD_ID)
    assert payload["title"] == "Test thread"


def test_patch_thread_updates_title(client: TestClient, mock_session: AsyncMock) -> None:
    thread = _thread()
    updated = ChatThread(
        id=THREAD_ID,
        user_id=USER_ID,
        title="Renamed thread",
        created_at=NOW,
        updated_at=NOW,
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.api.chat.get_thread_by_id", AsyncMock(return_value=thread))
        patch.setattr("app.api.chat.update_thread", AsyncMock(return_value=updated))
        response = client.patch(
            f"/chat/threads/{THREAD_ID}",
            json={"title": "Renamed thread"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Renamed thread"


def test_delete_thread_deletes_owned_thread(
    client: TestClient,
    mock_session: AsyncMock,
) -> None:
    thread = _thread()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.api.chat.get_thread_by_id", AsyncMock(return_value=thread))
        delete_thread = AsyncMock()
        patch.setattr("app.api.chat.delete_thread", delete_thread)
        response = client.delete(f"/chat/threads/{THREAD_ID}")

    assert response.status_code == 204
    delete_thread.assert_awaited_once_with(mock_session, thread)
    mock_session.commit.assert_awaited_once()


def test_delete_thread_forbidden(client: TestClient, mock_session: AsyncMock) -> None:
    other_thread = _thread(owner_id=OTHER_USER_ID)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.api.chat.get_thread_by_id", AsyncMock(return_value=other_thread))
        response = client.delete(f"/chat/threads/{THREAD_ID}")

    assert response.status_code == 403


def test_get_thread_messages_returns_messages(
    client: TestClient,
    mock_session: AsyncMock,
) -> None:
    thread = _thread()
    message = _message()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.api.chat.get_thread_by_id", AsyncMock(return_value=thread))
        patch.setattr("app.api.chat.list_messages", AsyncMock(return_value=[message]))
        response = client.get(f"/chat/threads/{THREAD_ID}/messages")

    assert response.status_code == 200
    payload = response.json()
    assert payload["messages"][0]["content"] == "Hello"


def test_get_thread_messages_forbidden(client: TestClient, mock_session: AsyncMock) -> None:
    other_thread = _thread(owner_id=OTHER_USER_ID)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.api.chat.get_thread_by_id", AsyncMock(return_value=other_thread))
        response = client.get(f"/chat/threads/{THREAD_ID}/messages")

    assert response.status_code == 403


def test_get_thread_messages_not_found(client: TestClient, mock_session: AsyncMock) -> None:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.api.chat.get_thread_by_id", AsyncMock(return_value=None))
        response = client.get(f"/chat/threads/{THREAD_ID}/messages")

    assert response.status_code == 404


def test_database_errors_return_cors_503() -> None:
    path = f"/__test_database_error_{uuid.uuid4().hex}"

    async def raise_database_error() -> None:
        raise SQLAlchemyError("database unavailable")

    app.add_api_route(path, raise_database_error, methods=["GET"])
    with TestClient(cors_app, raise_server_exceptions=False) as test_client:
        response = test_client.get(path, headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.json() == {
        "detail": "Database unavailable. Check DATABASE_URL and network access.",
    }
