"""X1 Stage 19: REST send of project email drafts is owner-scoped (404 never 403)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.project import Project
from app.database.session import get_db
from app.email.service import EmailDraftConflict, EmailNotFound
from app.main import fastapi_app as app

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER = uuid.UUID("22222222-2222-2222-2222-222222222222")
PROJECT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DRAFT_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _project(*, owner: uuid.UUID = USER_ID, project_id: uuid.UUID = PROJECT_ID) -> Project:
    return Project(
        id=project_id,
        owner_user_id=owner,
        slug="demo",
        title="Demo Project",
        workspace_path="04-projects/demo",
        phase="procurement",
        status="active",
        project_metadata={},
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


def test_send_draft_on_another_project_returns_404(client: TestClient) -> None:
    with (
        patch(
            "app.api.project_emails.get_project",
            new=AsyncMock(return_value=_project()),
        ),
        patch("app.api.project_emails.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.project_emails.send_email_draft",
            new=AsyncMock(side_effect=EmailNotFound(str(DRAFT_ID))),
        ),
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/emails/drafts/{DRAFT_ID}/send"
        )
    assert response.status_code == 404
    assert response.status_code != 403


def test_send_draft_by_non_owner_returns_404(client: TestClient) -> None:
    with patch(
        "app.api.project_emails.get_project",
        new=AsyncMock(return_value=_project(owner=OTHER_USER)),
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/emails/drafts/{DRAFT_ID}/send"
        )
    assert response.status_code == 404
    assert response.status_code != 403


def test_send_already_sent_returns_409(client: TestClient) -> None:
    with (
        patch(
            "app.api.project_emails.get_project",
            new=AsyncMock(return_value=_project()),
        ),
        patch("app.api.project_emails.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.project_emails.send_email_draft",
            new=AsyncMock(side_effect=EmailDraftConflict("cannot send draft in status sent")),
        ),
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/emails/drafts/{DRAFT_ID}/send"
        )
    assert response.status_code == 409


def test_reply_draft_creates_draft_without_sending(client: TestClient) -> None:
    email_id = uuid.uuid4()
    draft = SimpleNamespace(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        status="draft",
        to_addresses=["qs@consultant.com"],
        cc_addresses=[],
        subject="Re: RFI",
        body_text="",
        in_reply_to_email_id=email_id,
        provider_draft_id=None,
        provider_message_id=None,
        send_error=None,
        sent_at=None,
        sent_by_user_id=None,
    )
    with (
        patch(
            "app.api.project_emails.get_project",
            new=AsyncMock(return_value=_project()),
        ),
        patch("app.api.project_emails.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.project_emails.reply_email_draft",
            new=AsyncMock(return_value=draft),
        ) as reply,
        patch("app.api.project_emails.send_email_draft", new=AsyncMock()) as send,
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/emails/{email_id}/reply-draft",
            json={"body_text": ""},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "draft"
    assert payload["in_reply_to_email_id"] == str(email_id)
    reply.assert_called_once()
    send.assert_not_called()


def test_read_email_thread_returns_messages(client: TestClient) -> None:
    email_id = uuid.uuid4()
    thread = [
        {
            "email_id": str(email_id),
            "project_id": str(PROJECT_ID),
            "subject": "RFI-12",
            "body_text": "Please confirm slab thickness.",
            "from_address": "qs@consultant.com",
            "to_addresses": ["pm@owner.com"],
            "cc_addresses": [],
            "sent_at": "2026-08-14T00:00:00+00:00",
            "message_category": "rfi",
        }
    ]
    with (
        patch(
            "app.api.project_emails.get_project",
            new=AsyncMock(return_value=_project()),
        ),
        patch("app.api.project_emails.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.project_emails.read_email_thread",
            new=AsyncMock(return_value=thread),
        ),
    ):
        response = client.get(
            f"/projects/{PROJECT_ID}/emails/{email_id}/thread"
        )

    assert response.status_code == 200
    assert response.json()[0]["subject"] == "RFI-12"
