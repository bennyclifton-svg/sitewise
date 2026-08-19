from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.cost_plan.invoice_service import (
    InvoiceDecisionBlocked,
    InvoiceIllegalTransition,
    InvoiceNotFound,
)
from app.cost_plan.schemas import CostPlanState, DependencySnapshot
from app.database.project import Project
from app.database.session import get_db
from app.main import fastapi_app as app

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER = uuid.UUID("22222222-2222-2222-2222-222222222222")
PROJECT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
INVOICE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _project(*, owner: uuid.UUID = USER_ID) -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=owner,
        slug="demo",
        title="Demo Project",
        workspace_path="04-projects/demo",
        phase="procurement",
        archetype="small-commercial",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata={},
    )


def _state() -> CostPlanState:
    return CostPlanState(
        project_id=PROJECT_ID,
        version=1,
        artefact_revision_id=uuid.uuid4(),
        dependency_snapshot=DependencySnapshot(
            profile_revision=1,
            evidence_fingerprint="fixture",
            decision_set_revision=1,
            runtime_version="test",
        ),
        items=[],
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


def test_decide_invoice_on_another_projects_invoice_returns_404(client: TestClient) -> None:
    with (
        patch("app.api.cost_invoices.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.cost_invoices.get_cost_plan", new=AsyncMock(return_value=_state())),
        patch(
            "app.api.cost_invoices.complete_cost_plan_state",
            new=AsyncMock(return_value=_state()),
        ),
        patch("app.api.cost_invoices.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.cost_invoices.decide_invoice",
            new=AsyncMock(side_effect=InvoiceNotFound(str(INVOICE_ID))),
        ),
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/invoices/{INVOICE_ID}/decision",
            json={"decision": "approve"},
        )
    assert response.status_code == 404
    assert response.status_code != 403


def test_decide_invoice_by_non_owner_returns_404(client: TestClient) -> None:
    with patch(
        "app.api.cost_invoices.get_project",
        new=AsyncMock(return_value=_project(owner=OTHER_USER)),
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/invoices/{INVOICE_ID}/decision",
            json={"decision": "approve"},
        )
    assert response.status_code == 404
    assert response.status_code != 403


def test_approve_with_open_error_issues_returns_409(client: TestClient) -> None:
    with (
        patch("app.api.cost_invoices.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.cost_invoices.get_cost_plan", new=AsyncMock(return_value=_state())),
        patch(
            "app.api.cost_invoices.complete_cost_plan_state",
            new=AsyncMock(return_value=_state()),
        ),
        patch("app.api.cost_invoices.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.cost_invoices.decide_invoice",
            new=AsyncMock(side_effect=InvoiceDecisionBlocked("Open error issues block approval")),
        ),
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/invoices/{INVOICE_ID}/decision",
            json={"decision": "approve"},
        )
    assert response.status_code == 409


def test_illegal_transition_returns_409(client: TestClient) -> None:
    with (
        patch("app.api.cost_invoices.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.cost_invoices.get_cost_plan", new=AsyncMock(return_value=_state())),
        patch(
            "app.api.cost_invoices.complete_cost_plan_state",
            new=AsyncMock(return_value=_state()),
        ),
        patch("app.api.cost_invoices.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.cost_invoices.decide_invoice",
            new=AsyncMock(side_effect=InvoiceIllegalTransition("Cannot move")),
        ),
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/invoices/{INVOICE_ID}/decision",
            json={"decision": "reject"},
        )
    assert response.status_code == 409
