from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.main import fastapi_app as app
from tender.schemas import LedgerItem, QuoteLedgerResponse

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
COMPARISON_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
QUOTE_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_session: AsyncMock) -> TestClient:
    current_user = CurrentUser(id=USER_ID, email="operator@example.com")

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_ledger_endpoint_returns_items_summing_to_stated(client: TestClient) -> None:
    ledger = QuoteLedgerResponse(
        quote_id=QUOTE_ID,
        builder_name="Coastal",
        stated_total_cents=100_00,
        stated_basis="inc",
        status="reconciled",
        residual_cents=0,
        computed_ex_gst_cents=91_00,
        items=[
            LedgerItem(
                figure_key="p1-1",
                description_raw="Category A",
                amount_cents=60_00,
                counted_in_total=True,
            ),
            LedgerItem(
                figure_key="p1-2",
                description_raw="Category B",
                amount_cents=40_00,
                counted_in_total=True,
            ),
        ],
    )

    with (
        patch("tender.router.require_comparison_owner", new=AsyncMock()),
        patch(
            "tender.router.ledger.build_quote_ledger",
            new=AsyncMock(return_value=ledger),
        ),
    ):
        response = client.get(
            f"/api/tender/comparisons/{COMPARISON_ID}/quotes/{QUOTE_ID}/ledger"
        )

    assert response.status_code == 200
    payload = response.json()
    counted = sum(
        item["amount_cents"]
        for item in payload["items"]
        if item.get("counted_in_total")
    )
    assert counted + payload["residual_cents"] == payload["stated_total_cents"]
    assert payload["builder_name"] == "Coastal"
