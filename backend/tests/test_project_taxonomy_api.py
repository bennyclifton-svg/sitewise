import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.main import fastapi_app as app
from app.projects.profile import (
    ProfileDependencyConflict,
    ProfileRevisionConflict,
    ProfileValidationError,
)
from app.schemas.workflow_capabilities import WorkflowCapabilityMatrix

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
NOW = datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)


def _capabilities() -> WorkflowCapabilityMatrix:
    return WorkflowCapabilityMatrix(
        snapshot_content_fingerprint="test-snapshot",
        capabilities={},
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
    with (
        patch("app.api.projects.get_project_snapshot", new=AsyncMock(return_value=object())),
        patch("app.api.projects.workflow_capabilities", return_value=_capabilities()),
        TestClient(app) as test_client,
    ):
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
        "profile_revision": 1,
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


def _profile_change(**overrides) -> dict:
    values = {
        "profile": {
            "project_id": str(PROJECT_ID),
            "profile_revision": 2,
            "building_class": "commercial",
            "work_type": "refurb",
            "subclasses": [{"value": "other", "label": "Laboratory office"}],
            "scale": {"nla_sqm": 1200},
            "complexity": {"operational_constraints": "live_environment"},
            "work_scope": ["fire_services"],
            "user_role": "architect-pm",
            "state": "NSW",
        },
        "previous_revision": 1,
        "new_revision": 2,
        "changed_fields": [
            "building_class",
            "work_type",
            "subclasses",
            "scale",
            "complexity",
            "work_scope",
        ],
        "cleared_fields": [],
        "overlay_status": {"ready": True, "missing": [], "invalid": []},
        "risk_flags": [
            {
                "value": "live_operations",
                "severity": "high",
                "title": "Live operations",
                "description": "Works occur in an operating environment.",
            }
        ],
    }
    values.update(overrides)
    return values


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
    assert [flag["value"] for flag in payload["risk_flags"]] == [
        "live_operations",
        "critical_infrastructure",
    ]
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
        project_metadata={
            "taxonomy": {
                "subclasses": ["house"],
                "complexity": {"access_constraints": "remote"},
            }
        },
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
    assert payload["metadata"]["taxonomy"]["subclasses"] == ["house"]
    assert [flag["value"] for flag in payload["risk_flags"]] == ["remote_site"]


def test_patch_project_updates_taxonomy_and_risk_flags(client: TestClient) -> None:
    project = _project()
    apply_patch = AsyncMock(return_value=_profile_change())

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=project)),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.apply_profile_patch", new=apply_patch),
    ):
        response = client.patch(
            f"/projects/{PROJECT_ID}",
            json={
                "expected_revision": 1,
                "building_class": "commercial",
                "work_type": "refurb",
                "subclasses": [{"value": "other", "label": "Laboratory office"}],
                "scale": {"nla_sqm": 1200},
                "complexity": {"operational_constraints": "live_environment"},
                "work_scope": ["fire_services"],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["previous_revision"] == 1
    assert payload["new_revision"] == 2
    assert payload["profile"]["building_class"] == "commercial"
    assert payload["profile"]["subclasses"] == [
        {"value": "other", "label": "Laboratory office"}
    ]
    assert [flag["value"] for flag in payload["risk_flags"]] == ["live_operations"]
    apply_patch.assert_awaited_once()
    kwargs = apply_patch.await_args.kwargs
    assert kwargs["project"] is project
    assert kwargs["actor_source"] == "user"
    assert kwargs["patch"].expected_revision == 1
    assert [item.model_dump() for item in kwargs["patch"].subclasses] == [
        {"value": "other", "label": "Laboratory office"}
    ]


def test_patch_project_returns_conflict_for_stale_profile_revision(
    client: TestClient,
) -> None:
    apply_patch = AsyncMock(
        side_effect=ProfileRevisionConflict(
            expected_revision=4,
            current_revision=5,
        )
    )

    with (
        patch(
            "app.api.projects.get_project",
            new=AsyncMock(return_value=_project(profile_revision=5)),
        ),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.apply_profile_patch", new=apply_patch),
    ):
        response = client.patch(
            f"/projects/{PROJECT_ID}",
            json={"expected_revision": 4, "state": "VIC"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "profile_revision_conflict",
        "expected_revision": 4,
        "current_revision": 5,
    }


def test_patch_project_persists_user_role_and_state(client: TestClient) -> None:
    project = _project(user_role="architect-pm", state="NSW")
    change = _profile_change(
        profile={
            **_profile_change()["profile"],
            "user_role": "builder",
            "state": "VIC",
        },
        changed_fields=["user_role", "state"],
    )
    apply_patch = AsyncMock(return_value=change)

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=project)),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.apply_profile_patch", new=apply_patch),
    ):
        response = client.patch(
            f"/projects/{PROJECT_ID}",
            json={"expected_revision": 1, "user_role": "builder", "state": "VIC"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]["user_role"] == "builder"
    assert payload["profile"]["state"] == "VIC"
    body = apply_patch.await_args.kwargs["patch"]
    assert body.model_fields_set == {"expected_revision", "user_role", "state"}


def test_patch_project_taxonomy_satisfies_overlay_gate_without_archetype(
    client: TestClient,
) -> None:
    apply_patch = AsyncMock(return_value=_profile_change())

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.apply_profile_patch", new=apply_patch),
    ):
        response = client.patch(
            f"/projects/{PROJECT_ID}",
            json={
                "expected_revision": 1,
                "building_class": "residential",
                "work_type": "refurb",
                "subclasses": ["house"],
            },
        )

    assert response.status_code == 200
    overlay = response.json()["overlay_status"]
    assert overlay["ready"] is True
    assert overlay["missing"] == []
    assert overlay["invalid"] == []


def test_patch_project_rejects_invalid_taxonomy_combo(client: TestClient) -> None:
    apply_patch = AsyncMock(
        side_effect=ProfileValidationError(["Residential allows only one subclass"])
    )

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.apply_profile_patch", new=apply_patch),
    ):
        response = client.patch(
            f"/projects/{PROJECT_ID}",
            json={
                "expected_revision": 1,
                "building_class": "residential",
                "work_type": "new",
                "subclasses": ["house", "apartments"],
            },
        )

    assert response.status_code == 422
    assert "allows only one subclass" in str(response.json()["detail"])
    apply_patch.assert_awaited_once()


def test_patch_project_requires_clear_confirmation_for_dependency_conflicts(
    client: TestClient,
) -> None:
    apply_patch = AsyncMock(
        side_effect=ProfileDependencyConflict(("subclasses", "scale"))
    )
    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.apply_profile_patch", new=apply_patch),
    ):
        response = client.patch(
            f"/projects/{PROJECT_ID}",
            json={"expected_revision": 1, "building_class": "commercial"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "profile_dependency_conflict",
        "fields": ["subclasses", "scale"],
    }


def test_project_events_are_read_after_an_owned_project_cursor(
    client: TestClient,
) -> None:
    event = SimpleNamespace(
        id=uuid.uuid4(),
        sequence=5,
        schema_version=1,
        project_id=PROJECT_ID,
        actor_source="worker",
        resource_type="workflow_run",
        resource_id="run-1",
        resource_revision=2,
        action="completed",
        payload={"status": "complete"},
        deduplication_key="workflow:run-1:complete",
        created_at=NOW,
    )
    list_events = AsyncMock(return_value=[event])
    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.list_project_events", new=list_events),
    ):
        response = client.get(f"/projects/{PROJECT_ID}/events?after=4&limit=2")

    assert response.status_code == 200
    assert response.json()["next_after"] == 5
    assert response.json()["events"][0]["resource_type"] == "workflow_run"
    assert list_events.await_args.kwargs == {
        "project_id": PROJECT_ID,
        "after": 4,
        "limit": 2,
    }


def test_project_events_reject_cross_tenant_reads_before_cursor_query(
    client: TestClient,
) -> None:
    list_events = AsyncMock()
    with (
        patch(
            "app.api.projects.get_project",
            new=AsyncMock(return_value=_project(owner_user_id=uuid.uuid4())),
        ),
        patch("app.api.projects.list_project_events", new=list_events),
    ):
        response = client.get(f"/projects/{PROJECT_ID}/events?after=0")

    assert response.status_code == 403
    list_events.assert_not_awaited()


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
