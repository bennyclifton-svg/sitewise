import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

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


@pytest.mark.parametrize("count", [5, 25, 100])
def test_list_batches_draft_summaries_without_loading_bodies(
    client: TestClient, mock_session: AsyncMock, count: int
) -> None:
    drafts = {
        uuid.UUID(int=index + 100): dict(
            id=uuid.UUID(int=index + 100),
            project_id=PROJECT_ID,
            workflow_type=f"consultant_procurement_{index}",
            version=2,
            status="draft",
            title=f"RFP {index}",
            workspace_path=f"rfp/{index}.md",
            author_user_id=USER_ID,
            model=None,
            runtime="pi",
            created_at=NOW,
            updated_at=NOW,
        )
        for index in range(count)
    }
    requests = [
        SimpleNamespace(
            **{
                **_view().model_dump(exclude={"current_draft"}),
                "id": uuid.UUID(int=index + 1000),
                "current_draft_artifact_id": draft_id,
            }
        )
        for index, draft_id in enumerate(drafts)
    ]
    # Keep the former per-row path functional so this fails on query count,
    # rather than on an unrelated mock/response validation error.
    mock_session.get.side_effect = lambda _model, draft_id: SimpleNamespace(
        **drafts[draft_id]
    )
    result = MagicMock()
    result.mappings.return_value.all.return_value = list(drafts.values())
    mock_session.execute.return_value = result
    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch(
            "app.api.projects.list_procurement_requests",
            new=AsyncMock(return_value=requests),
        ),
    ):
        response = client.get(f"/projects/{PROJECT_ID}/procurement-requests")

    assert response.status_code == 200
    rows = response.json()["requests"]
    assert len(rows) == count
    assert [row["current_draft"]["id"] for row in rows] == [str(key) for key in drafts]
    assert all("markdown" not in row["current_draft"] for row in rows)
    assert "content_markdown" not in rows[0]["current_draft"]
    mock_session.get.assert_not_awaited()
    mock_session.execute.assert_awaited_once()
    statement = mock_session.execute.call_args.args[0]
    assert "content_markdown" not in {
        column.key for column in statement.selected_columns
    }
    assert "provenance_metadata" not in {
        column.key for column in statement.selected_columns
    }
    assert PROJECT_ID in statement.compile().params.values()
    assert "draft_summaries;dur=" in response.headers["server-timing"]


def test_list_without_drafts_does_not_query_drafts(
    client: TestClient, mock_session: AsyncMock
) -> None:
    request = SimpleNamespace(**_view().model_dump(exclude={"current_draft"}))
    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch(
            "app.api.projects.list_procurement_requests",
            new=AsyncMock(return_value=[request]),
        ),
    ):
        response = client.get(f"/projects/{PROJECT_ID}/procurement-requests")
    assert response.status_code == 200
    assert response.json()["requests"][0]["current_draft"] is None
    mock_session.get.assert_not_awaited()
    mock_session.execute.assert_not_awaited()


def test_list_preserves_request_when_its_draft_is_missing(
    client: TestClient, mock_session: AsyncMock
) -> None:
    request = SimpleNamespace(
        **{
            **_view().model_dump(exclude={"current_draft"}),
            "current_draft_artifact_id": uuid.UUID(int=99),
        }
    )
    result = MagicMock()
    result.mappings.return_value.all.return_value = []
    mock_session.execute.return_value = result
    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch(
            "app.api.projects.list_procurement_requests",
            new=AsyncMock(return_value=[request]),
        ),
    ):
        response = client.get(f"/projects/{PROJECT_ID}/procurement-requests")
    assert response.status_code == 200
    assert response.json()["requests"][0]["current_draft"] is None
    assert response.json()["requests"][0]["current_draft_artifact_id"] == str(
        request.current_draft_artifact_id
    )


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
