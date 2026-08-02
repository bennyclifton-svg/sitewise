import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import projects as projects_api
from app.auth.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.main import fastapi_app as app
from app.schemas.projects import ProcurementRequestView

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
PROJECT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
REQUEST_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
NOW = datetime(2026, 8, 2, tzinfo=UTC)


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_session: AsyncMock) -> TestClient:
    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=USER_ID, email="user@example.com"
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _project(owner_user_id: uuid.UUID = USER_ID):
    return SimpleNamespace(id=PROJECT_ID, owner_user_id=owner_user_id)


def _view() -> ProcurementRequestView:
    return ProcurementRequestView(
        id=REQUEST_ID,
        project_id=PROJECT_ID,
        created_by_user_id=USER_ID,
        kind="trade_rfq",
        target_name="Electrical Services",
        target_slug="electrical_services",
        status="draft",
        current_draft_artifact_id=None,
        revision=1,
        created_at=NOW,
        updated_at=NOW,
    )


def test_create_request_is_owner_scoped_and_returns_slim_view(
    client: TestClient, mock_session: AsyncMock
) -> None:
    created = SimpleNamespace(id=REQUEST_ID)
    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.projects.create_procurement_request",
            new=AsyncMock(return_value=created),
        ) as create_request,
        patch(
            "app.api.projects._procurement_request_view",
            new=AsyncMock(return_value=_view()),
        ),
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/procurement-requests",
            json={"kind": "trade_rfq", "target_name": "Electrical Services"},
        )

    assert response.status_code == 201
    assert response.json()["id"] == str(REQUEST_ID)
    create_request.assert_awaited_once_with(
        mock_session,
        project_id=PROJECT_ID,
        created_by_user_id=USER_ID,
        kind="trade_rfq",
        target_name="Electrical Services",
    )


def test_other_project_owner_cannot_list_requests(client: TestClient) -> None:
    with patch(
        "app.api.projects.get_project",
        new=AsyncMock(return_value=_project(OTHER_USER_ID)),
    ):
        response = client.get(f"/projects/{PROJECT_ID}/procurement-requests")

    assert response.status_code == 403


def test_status_update_maps_lifecycle_conflict(client: TestClient) -> None:
    request = SimpleNamespace(id=REQUEST_ID)
    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.projects.get_procurement_request",
            new=AsyncMock(return_value=request),
        ),
        patch(
            "app.api.projects.transition_procurement_request",
            new=AsyncMock(
                side_effect=projects_api.ProcurementRequestStateConflict(
                    "invalid transition"
                )
            ),
        ),
    ):
        response = client.patch(
            f"/projects/{PROJECT_ID}/procurement-requests/{REQUEST_ID}/status",
            json={"status": "closed", "expected_revision": 1},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "invalid transition"


def test_request_kind_is_validated_before_creation(client: TestClient) -> None:
    response = client.post(
        f"/projects/{PROJECT_ID}/procurement-requests",
        json={"kind": "rfq", "target_name": "Electrical"},
    )

    assert response.status_code == 422
