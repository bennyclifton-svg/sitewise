import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.api.prompt_library import router
from app.auth.dependencies import CurrentUser, get_current_user
from app.database.session import get_db


@pytest.fixture
def client_and_session():
    app = FastAPI()
    app.include_router(router)
    user = CurrentUser(id=uuid.uuid4(), email="owner@example.com")
    session = AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as client:
        yield client, session, user


def test_library_requires_authentication():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    with TestClient(app) as client:
        assert client.get("/prompt-library").status_code == 401
        assert client.put("/prompt-library", json={}).status_code == 401


def test_reads_only_authenticated_users_library(client_and_session):
    client, session, user = client_and_session
    session.get.return_value = None
    response = client.get("/prompt-library")
    assert response.json() == {"version": 0, "prompts": None}
    assert session.get.call_args.args[1] == user.id


def test_update_scopes_write_and_checks_version(client_and_session):
    client, session, user = client_and_session
    result = MagicMock()
    result.scalar_one_or_none.return_value = 3
    session.execute.return_value = result
    payload = {
        "expected_version": 2,
        "prompts": [{"id": "custom", "title": "Topic", "text": "Do this"}],
    }
    response = client.put("/prompt-library", json=payload)
    assert response.status_code == 200
    statement = session.execute.call_args.args[0].compile(dialect=postgresql.dialect())
    assert user.id in statement.params.values()
    assert 2 in statement.params.values()
    assert "prompt_libraries.version =" in str(statement)
    assert response.json()["version"] == 3


def test_stale_save_conflicts_instead_of_overwriting(client_and_session):
    client, session, _ = client_and_session
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    response = client.put(
        "/prompt-library", json={"expected_version": 1, "prompts": []}
    )
    assert response.status_code == 409


def test_first_save_cannot_replace_an_existing_library(client_and_session):
    client, session, user = client_and_session
    result = MagicMock()
    result.scalar_one_or_none.return_value = 1
    session.execute.return_value = result
    response = client.put(
        "/prompt-library", json={"expected_version": 0, "prompts": []}
    )
    assert response.status_code == 200
    statement = session.execute.call_args.args[0].compile(dialect=postgresql.dialect())
    assert statement.params["user_id"] == user.id
    assert "ON CONFLICT (user_id) DO NOTHING" in str(statement)


def test_cannot_choose_another_users_library(client_and_session):
    client, session, _ = client_and_session
    response = client.put(
        "/prompt-library",
        json={
            "expected_version": 0,
            "prompts": [],
            "user_id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 422
    session.execute.assert_not_called()


@pytest.mark.parametrize(
    "prompts",
    [
        [{"id": "one", "title": " ", "text": "Prompt"}],
        [{"id": "one", "title": "Title", "text": " "}],
        [{"id": "same", "title": "Title", "text": "Prompt"}] * 2,
    ],
)
def test_rejects_invalid_prompts(client_and_session, prompts):
    client, session, _ = client_and_session
    assert (
        client.put(
            "/prompt-library", json={"expected_version": 0, "prompts": prompts}
        ).status_code
        == 422
    )
    session.execute.assert_not_called()
