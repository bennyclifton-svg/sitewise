import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.main import fastapi_app as app

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
NOW = datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)


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


def _project(**overrides):
    values = {
        "id": PROJECT_ID,
        "owner_user_id": USER_ID,
        "slug": "demo",
        "title": "Demo Project",
        "workspace_path": "04-projects/demo",
        "phase": "brief-planning",
        "archetype": None,
        "building_class": None,
        "work_type": None,
        "user_role": "architect-pm",
        "state": "NSW",
        "status": "active",
        "project_metadata": {
            "source": "hosted-create-project",
            "workspace_model": "sitewise-template-v1",
        },
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_create_project_persists_taxonomy_payload(client: TestClient) -> None:
    create_project = AsyncMock(
        return_value=_project(
            building_class="commercial",
            work_type="refurb",
            project_metadata={
                "source": "hosted-create-project",
                "workspace_model": "sitewise-template-v1",
                "taxonomy": {
                    "subclasses": ["office"],
                    "scale": {"nla_sqm": 1200},
                    "complexity": {"operational_constraints": "live_environment"},
                    "work_scope": ["fire_services"],
                },
            },
        )
    )

    with (
        patch("app.api.projects.ensure_user_exists", new=AsyncMock()),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.create_project", new=create_project),
    ):
        response = client.post(
            "/projects",
            json={
                "title": "Demo Project",
                "building_class": "commercial",
                "work_type": "refurb",
                "subclasses": ["office"],
                "scale": {"nla_sqm": 1200},
                "complexity": {"operational_constraints": "live_environment"},
                "work_scope": ["fire_services"],
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["building_class"] == "commercial"
    assert payload["work_type"] == "refurb"
    assert payload["metadata"]["taxonomy"]["subclasses"] == ["office"]
    create_project.assert_awaited_once()
    kwargs = create_project.await_args.kwargs
    assert kwargs["building_class"] == "commercial"
    assert kwargs["work_type"] == "refurb"
    assert kwargs["taxonomy"] == {
        "subclasses": ["office"],
        "scale": {"nla_sqm": 1200},
        "complexity": {"operational_constraints": "live_environment"},
        "work_scope": ["fire_services"],
    }


def test_create_project_rejects_invalid_taxonomy_combo(client: TestClient) -> None:
    create_project = AsyncMock()

    with (
        patch("app.api.projects.ensure_user_exists", new=AsyncMock()),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.create_project", new=create_project),
    ):
        response = client.post(
            "/projects",
            json={
                "title": "Demo Project",
                "building_class": "residential",
                "work_type": "teleportation",
                "subclasses": ["house"],
            },
        )

    assert response.status_code == 422
    assert "Unknown work_type" in str(response.json()["detail"])
    create_project.assert_not_awaited()


def test_create_project_allows_title_only_minimal_brief(client: TestClient) -> None:
    create_project = AsyncMock(return_value=_project())

    with (
        patch("app.api.projects.ensure_user_exists", new=AsyncMock()),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.create_project", new=create_project),
    ):
        response = client.post("/projects", json={"title": "Minimal Brief"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["building_class"] is None
    assert payload["work_type"] is None
    create_project.assert_awaited_once()
    assert create_project.await_args.kwargs["taxonomy"] is None


def test_get_project_detail_exposes_taxonomy_metadata(client: TestClient) -> None:
    project = _project(
        building_class="residential",
        work_type="new",
        project_metadata={"taxonomy": {"subclasses": ["house"]}},
    )

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=project)),
        patch("app.api.projects._first_evidence_preview", new=AsyncMock(return_value=None)),
    ):
        response = client.get(f"/projects/{PROJECT_ID}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["building_class"] == "residential"
    assert payload["work_type"] == "new"
    assert payload["metadata"]["taxonomy"] == {"subclasses": ["house"]}


def test_taxonomy_endpoint_returns_frontend_option_shape(client: TestClient) -> None:
    with patch("app.api.projects.ensure_user_exists", new=AsyncMock()):
        response = client.get("/projects/taxonomy")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "work_types",
        "building_classes",
        "complexity_dimensions",
        "risk_flags",
        "work_scopes",
        "emphasis_profiles",
    }
    assert [item["value"] for item in payload["building_classes"]] == [
        "residential",
        "commercial",
        "industrial",
        "institution",
        "mixed",
        "infrastructure",
    ]
    assert payload["emphasis_profiles"]["sections"] == [
        "snapshot",
        "scope-client-requirements",
        "compliance-approvals",
        "programme",
        "cost-budget",
        "procurement-delivery",
        "risks",
        "actions-decisions",
    ]


def test_taxonomy_endpoint_includes_universal_dimensions(client: TestClient) -> None:
    with patch("app.api.projects.ensure_user_exists", new=AsyncMock()):
        response = client.get("/projects/taxonomy")

    assert response.status_code == 200
    dimensions = response.json()["complexity_dimensions"]
    for class_name in [
        "residential",
        "commercial",
        "industrial",
        "institution",
        "mixed",
        "infrastructure",
    ]:
        keys = {dimension["key"] for dimension in dimensions[class_name]}
        assert {
            "contamination_level",
            "access_constraints",
            "operational_constraints",
            "procurement_route",
            "stakeholder_complexity",
            "environmental_sensitivity",
        } <= keys
