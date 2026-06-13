from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.main import fastapi_app as app
from tender.schemas import (
    MatrixCell,
    MatrixGroup,
    MatrixQuoteCell,
    MatrixResponse,
    TaxonomyCellView,
    TaxonomySearchResult,
)
from tender.services import taxonomy

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


def test_matrix_endpoint_returns_grouped_cells(client: TestClient) -> None:
    matrix = MatrixResponse(
        comparison_id=COMPARISON_ID,
        groups=[
            MatrixGroup(
                name="Appliances",
                cells=[
                    MatrixCell(
                        code="18.01",
                        name="Cooktop",
                        quotes={
                            str(QUOTE_ID): MatrixQuoteCell(
                                status="pc",
                                amount_cents=200_000,
                                flags=["Allowance appears low"],
                            )
                        },
                    )
                ],
            )
        ],
    )

    with (
        patch("tender.router.require_comparison_owner", new=AsyncMock()),
        patch("tender.router.matrix.build_matrix", new=AsyncMock(return_value=matrix)),
    ):
        response = client.get(f"/api/tender/comparisons/{COMPARISON_ID}/matrix")

    assert response.status_code == 200
    payload = response.json()
    assert payload["groups"][0]["name"] == "Appliances"
    assert payload["groups"][0]["cells"][0]["quotes"][str(QUOTE_ID)]["status"] == "pc"


def test_taxonomy_endpoints_return_cells_and_search_results(client: TestClient) -> None:
    cell = TaxonomyCellView(
        code="03.05",
        name="Retaining walls",
        group="Site works",
        stage="base",
        description="Retaining structures.",
    )
    result = TaxonomySearchResult(
        code="03.05",
        name="Retaining walls",
        group="Site works",
        stage="base",
        similarity=0.94,
        via="retaining wall",
    )

    with (
        patch("tender.router.taxonomy.list_taxonomy", new=AsyncMock(return_value=[cell])),
        patch("tender.router.taxonomy.search_taxonomy", new=AsyncMock(return_value=[result])),
    ):
        list_response = client.get("/api/tender/taxonomy")
        search_response = client.get("/api/tender/taxonomy/search?q=retaning+wall")

    assert list_response.status_code == 200
    assert list_response.json()["cells"][0]["code"] == "03.05"
    assert search_response.status_code == 200
    assert search_response.json()["results"][0]["via"] == "retaining wall"


def test_taxonomy_search_statement_uses_trigram_similarity() -> None:
    compiled = str(
        taxonomy.taxonomy_search_statement("retaning wall").compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "similarity" in compiled
    assert "taxonomy_synonyms.phrase_norm" in compiled
    assert "ORDER BY similarity DESC" in compiled
