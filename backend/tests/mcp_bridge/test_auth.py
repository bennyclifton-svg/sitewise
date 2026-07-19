import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.mcp_bridge.tokens import mint_turn_token
from tests.conftest import run_async

SECRET = "test-secret"
USER_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def _token_secret(monkeypatch):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)


def _project(owner_id: uuid.UUID = USER_ID) -> SimpleNamespace:
    return SimpleNamespace(id=PROJECT_ID, owner_user_id=owner_id)


def _bearer(user_id: uuid.UUID = USER_ID, project_id: uuid.UUID = PROJECT_ID) -> str:
    return "Bearer " + mint_turn_token(
        user_id=user_id, project_id=project_id, secret=SECRET
    )


def test_valid_token_and_owned_project_returns_project(monkeypatch):
    from app.mcp_bridge import auth

    project = _project()

    async def fake_get_project(session, project_id):
        assert project_id == PROJECT_ID
        return project

    monkeypatch.setattr(auth, "get_project", fake_get_project)

    result = run_async(
        auth.authorize_project_access(
            object(),
            authorization_header=_bearer(),
            project_id=PROJECT_ID,
        )
    )
    assert result is project


def test_token_scoped_to_other_project_rejected(monkeypatch):
    from app.mcp_bridge import auth

    async def fake_get_project(session, project_id):  # pragma: no cover
        raise AssertionError("must reject before hitting the database")

    monkeypatch.setattr(auth, "get_project", fake_get_project)

    with pytest.raises(auth.ToolAuthError):
        run_async(
            auth.authorize_project_access(
                object(),
                authorization_header=_bearer(project_id=uuid.uuid4()),
                project_id=PROJECT_ID,
            )
        )


def test_project_owned_by_someone_else_rejected(monkeypatch):
    from app.mcp_bridge import auth

    async def fake_get_project(session, project_id):
        return _project(owner_id=uuid.uuid4())

    monkeypatch.setattr(auth, "get_project", fake_get_project)

    with pytest.raises(auth.ToolAuthError):
        run_async(
            auth.authorize_project_access(
                object(),
                authorization_header=_bearer(),
                project_id=PROJECT_ID,
            )
        )


@pytest.mark.parametrize("header", [None, "", "Bearer garbage", "Basic abc"])
def test_missing_or_garbage_token_rejected(header):
    from app.mcp_bridge import auth

    with pytest.raises(auth.ToolAuthError):
        run_async(
            auth.authorize_project_access(
                object(),
                authorization_header=header,
                project_id=PROJECT_ID,
            )
        )


def test_mutation_authorization_passes_bound_scope_to_durable_turn(monkeypatch):
    from app.mcp_bridge import auth

    turn_id = uuid.uuid4()
    token = mint_turn_token(
        user_id=USER_ID,
        project_id=PROJECT_ID,
        turn_id=turn_id,
        secret=SECRET,
    )
    monkeypatch.setattr(auth, "get_project", AsyncMock(return_value=_project()))
    require_turn = AsyncMock()
    monkeypatch.setattr(auth, "require_active_mutation_turn", require_turn)
    session = object()

    result = run_async(
        auth.authorize_project_mutation_with_claims(
            session,
            authorization_header=f"Bearer {token}",
            project_id=PROJECT_ID,
            required_scope="profile_mutation",
            requested_profile_patch={"state": "VIC"},
        )
    )

    assert result.project.id == PROJECT_ID
    require_turn.assert_awaited_once_with(
        session,
        turn_id=turn_id,
        project_id=PROJECT_ID,
        user_id=USER_ID,
        required_scope="profile_mutation",
        requested_profile_patch={"state": "VIC"},
    )
