from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.cost_plan.schemas import CostItemInput, CostPlanState, DependencySnapshot
from app.database.project import Project
from app.database.session import get_db
from app.main import fastapi_app as app


USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
ALLOCATION_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
INVOICE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
DRAFT_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def _project() -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="newtown",
        title="Newtown Extension",
        workspace_path="04-projects/newtown",
        phase="procurement",
        archetype="residential-class1-refurb",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata={},
    )


def _item() -> CostItemInput:
    return CostItemInput(
        item_key="architect",
        cost_code="1",
        category="Consultants",
        item="Architect",
        basis="Manual",
        status="manual",
    )


def _state(*, version: int = 12) -> CostPlanState:
    return CostPlanState(
        project_id=PROJECT_ID,
        version=version,
        artefact_revision_id=DRAFT_ID,
        dependency_snapshot=DependencySnapshot(
            profile_revision=1,
            evidence_fingerprint="fixture",
            decision_set_revision=1,
            runtime_version="test",
        ),
        items=[_item()],
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    return session


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


def _ledger() -> dict[str, object]:
    return {
        "cost_plan_version": 12,
        "workbook_path": "01-cost/Cost_Plan_v12.draft.xlsx",
        "rows": [],
        "cost_items": [],
    }


def test_allocation_save_ignores_stale_cost_plan_version(client: TestClient) -> None:
    invoice = SimpleNamespace(id=INVOICE_ID, revision=2)
    update = AsyncMock(return_value=invoice)
    schedule = MagicMock()

    with (
        patch("app.api.cost_invoices.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.cost_invoices.get_cost_plan", new=AsyncMock(return_value=_state(version=12))),
        patch(
            "app.api.cost_invoices.complete_cost_plan_state",
            new=AsyncMock(return_value=_state(version=12)),
        ),
        patch("app.api.cost_invoices.require_active_entitlement", new=AsyncMock()),
        patch("app.api.cost_invoices.update_invoice_allocation", new=update),
        patch("app.api.cost_invoices.schedule_cost_plan_workbook_rebuild", schedule),
        patch(
            "app.api.cost_invoices.invoice_ledger_response",
            new=AsyncMock(return_value=_ledger()),
        ),
        patch(
            "app.api.cost_invoices.workbook_workspace_path",
            return_value="01-cost/Cost_Plan_v12.draft.xlsx",
        ),
    ):
        response = client.patch(
            f"/projects/{PROJECT_ID}/invoice-allocations/{ALLOCATION_ID}",
            json={
                "expected_revision": 1,
                "expected_cost_plan_version": 11,
                "cost_item_key": "architect",
            },
        )

    assert response.status_code == 200
    update.assert_awaited_once()
    assert update.await_args.kwargs["cost_item_key"] == "architect"
    assert update.await_args.kwargs["cost_item_label"] == "Architect"
    schedule.assert_called_once_with(PROJECT_ID, 12)


def test_allocation_save_does_not_touch_the_cost_plan_draft(
    client: TestClient, mock_session: AsyncMock
) -> None:
    invoice = SimpleNamespace(id=INVOICE_ID, revision=2)

    with (
        patch("app.api.cost_invoices.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.cost_invoices.get_cost_plan", new=AsyncMock(return_value=_state())),
        patch(
            "app.api.cost_invoices.complete_cost_plan_state",
            new=AsyncMock(return_value=_state()),
        ),
        patch("app.api.cost_invoices.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.cost_invoices.update_invoice_allocation",
            new=AsyncMock(return_value=invoice),
        ),
        patch("app.api.cost_invoices.schedule_cost_plan_workbook_rebuild", MagicMock()),
        patch(
            "app.api.cost_invoices.invoice_ledger_response",
            new=AsyncMock(return_value=_ledger()),
        ),
        patch(
            "app.api.cost_invoices.workbook_workspace_path",
            return_value="01-cost/Cost_Plan_v12.draft.xlsx",
        ),
    ):
        response = client.patch(
            f"/projects/{PROJECT_ID}/invoice-allocations/{ALLOCATION_ID}",
            json={
                "expected_revision": 1,
                "expected_cost_plan_version": 12,
                "cost_item_key": "architect",
            },
        )

    assert response.status_code == 200
    mock_session.get.assert_not_awaited()
    mock_session.commit.assert_awaited()
