from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any
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
from tender.services import matrix
from tender.services import taxonomy
from tests.conftest import run_async

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


def test_build_matrix_includes_multi_candidate_mapping_choices() -> None:
    mapping_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    session = FakeMatrixSession(
        status_rows=[
            FakeRow(
                quote_id=QUOTE_ID,
                cell_code="03.05",
                status="included",
                amount_cents=500_000,
                cell_name="Retaining walls",
                group_name="Site works",
                sort_order=1,
            )
        ],
        flag_rows=[],
        mapping_rows=[
            FakeRow(
                mapping_id=mapping_id,
                quote_id=QUOTE_ID,
                selected_cell_code="03.05",
                qa_state="needs_review",
                adjudication={
                    "choice": {"cell_code": "03.05", "name": "Retaining walls"},
                    "candidates": [
                        {
                            "cell_code": "03.05",
                            "name": "Retaining walls",
                            "similarity": 0.78,
                            "via": "retaining",
                        },
                        {
                            "cell_code": "03.01",
                            "name": "Site costs",
                            "similarity": 0.72,
                            "via": "site costs",
                        },
                    ],
                },
            )
        ],
    )

    response = run_async(matrix.build_matrix(session, comparison_id=COMPARISON_ID))

    quote_cell = response.groups[0].cells[0].quotes[str(QUOTE_ID)]
    assert quote_cell.mapping_choices[0].mapping_id == mapping_id
    assert quote_cell.mapping_choices[0].selected_cell_code == "03.05"
    assert quote_cell.mapping_choices[0].locked is False
    assert [candidate.cell_code for candidate in quote_cell.mapping_choices[0].candidates] == [
        "03.05",
        "03.01",
    ]


def test_build_matrix_computes_totals_with_reconciliation() -> None:
    other_quote_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    session = FakeMatrixSession(
        status_rows=[
            FakeRow(
                quote_id=QUOTE_ID,
                cell_code="03.05",
                status="included",
                amount_cents=90_000_00,
                cell_name="Retaining walls",
                group_name="Site works",
                sort_order=1,
            ),
            FakeRow(
                quote_id=QUOTE_ID,
                cell_code="18.01",
                status="pc",
                amount_cents=10_000_00,
                cell_name="Cooktop",
                group_name="Appliances",
                sort_order=2,
            ),
            FakeRow(
                quote_id=QUOTE_ID,
                cell_code="03.01",
                status="excluded_explicit",
                amount_cents=5_000_00,
                cell_name="Site costs",
                group_name="Site works",
                sort_order=3,
            ),
        ],
        flag_rows=[],
        mapping_rows=[],
        quote_rows=[
            FakeRow(
                id=QUOTE_ID,
                stated_total_cents=100_000_00,
                stated_total_source="extracted",
            ),
            FakeRow(
                id=other_quote_id,
                stated_total_cents=None,
                stated_total_source=None,
            ),
        ],
    )

    response = run_async(matrix.build_matrix(session, comparison_id=COMPARISON_ID))

    assert [str(total.quote_id) for total in response.totals] == [
        str(QUOTE_ID),
        str(other_quote_id),
    ]
    first = response.totals[0]
    assert first.computed_total_cents == 100_000_00
    assert first.stated_total_cents == 100_000_00
    assert first.stated_total_source == "extracted"
    assert first.reconciliation == "match"
    assert first.delta_cents == 0
    second = response.totals[1]
    assert second.computed_total_cents == 0
    assert second.reconciliation == "not_stated"


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


@dataclass(frozen=True)
class FakeRow:
    def __init__(self, **values: Any) -> None:
        object.__setattr__(self, "_values", values)
        for key, value in values.items():
            object.__setattr__(self, key, value)


class FakeMatrixSession:
    def __init__(
        self,
        *,
        status_rows: list[FakeRow],
        flag_rows: list[FakeRow],
        mapping_rows: list[FakeRow],
        quote_rows: list[FakeRow] | None = None,
    ) -> None:
        self.results = [
            FakeResult(status_rows),
            FakeResult(flag_rows),
            FakeResult(mapping_rows),
            FakeResult(quote_rows or []),
        ]

    async def execute(self, statement: Any) -> "FakeResult":
        return self.results.pop(0)


class FakeResult:
    def __init__(self, rows: list[FakeRow]) -> None:
        self.rows = rows

    def all(self) -> list[FakeRow]:
        return self.rows
