from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.main import fastapi_app as app
from tender.models import (
    TaxonomySynonym,
    TenderCellStatus,
    TenderCorrection,
    TenderLineItem,
    TenderMapping,
    TenderProjectTrade,
)
from tender.schemas import QAResolveRequest, QAReviewItem
from tender.services import qa
from tests.conftest import run_async

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
COMPARISON_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
ITEM_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=timezone.utc)


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


def test_qa_queue_endpoint_returns_review_items(client: TestClient) -> None:
    item = QAReviewItem(
        id=ITEM_ID,
        entity_type="cell_status",
        report_impact_cents=450_000,
        confidence=0.61,
        payload={"cell_code": "18.01", "status": "silent_ambiguous"},
    )

    with (
        patch("tender.router.require_comparison_owner", new=AsyncMock()),
        patch("tender.router.qa.list_review_items", new=AsyncMock(return_value=[item])),
    ):
        response = client.get(f"/api/tender/comparisons/{COMPARISON_ID}/qa/queue")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["id"] == str(ITEM_ID)
    assert payload["items"][0]["entity_type"] == "cell_status"


def test_qa_queue_statement_orders_by_priority_impact_then_confidence() -> None:
    compiled = str(
        qa.review_queue_statement(COMPARISON_ID).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    priority_pos = compiled.index("entity_priority ASC")
    impact_pos = compiled.index("report_impact_cents DESC")
    confidence_pos = compiled.index("confidence ASC NULLS LAST")
    assert priority_pos < impact_pos < confidence_pos


def test_qa_queue_statement_excludes_multi_candidate_mapping_adjudications() -> None:
    compiled = str(
        qa.review_queue_statement(COMPARISON_ID).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert (
        "coalesce(jsonb_array_length(tender_mappings.adjudication -> 'candidates'), 0) < 2"
        in compiled
    )


def test_resolve_endpoint_checks_owner_and_resolves_item(client: TestClient) -> None:
    resolved = qa.QAResolveResult(
        id=ITEM_ID,
        entity_type="cell_status",
        action="accept",
        qa_state="confirmed",
    )

    with (
        patch(
            "tender.router.qa.get_item_comparison_id",
            new=AsyncMock(return_value=COMPARISON_ID),
        ),
        patch("tender.router.require_comparison_owner", new=AsyncMock()),
        patch("tender.router.require_active_entitlement", new=AsyncMock()),
        patch("tender.router.qa.resolve_qa_item", new=AsyncMock(return_value=resolved)),
    ):
        response = client.post(
            f"/api/tender/qa/items/{ITEM_ID}/resolve",
            json={"action": "accept", "corrected_value": None, "reason": "Looks right"},
        )

    assert response.status_code == 200
    assert response.json()["qa_state"] == "confirmed"


def test_resolve_cell_status_accept_writes_correction() -> None:
    session = FakeQASession(cell_status=True)

    result = run_async(
        qa.resolve_qa_item(
            session,
            item_id=session.cell_status.id,
            reviewer_id=USER_ID,
            request=QAResolveRequest(action="accept", reason="Evidence checked"),
        )
    )

    correction = _only_added(session, TenderCorrection)
    assert result.qa_state == "confirmed"
    assert session.cell_status.qa_state == "confirmed"
    assert correction.entity_type == "tender_cell_status"
    assert correction.entity_id == session.cell_status.id
    assert correction.before["qa_state"] == "needs_review"
    assert correction.after["qa_state"] == "confirmed"
    assert correction.reviewer == USER_ID


def test_resolve_mapping_correction_inserts_taxonomy_synonym() -> None:
    session = FakeQASession(mapping=True)

    result = run_async(
        qa.resolve_qa_item(
            session,
            item_id=session.mapping.id,
            reviewer_id=USER_ID,
            request=QAResolveRequest(
                action="correct",
                corrected_value={"cell_code": "03.05"},
                reason="Wrong taxonomy cell",
            ),
        )
    )

    correction = _only_added(session, TenderCorrection)
    synonym = _only_added(session, TaxonomySynonym)
    assert result.entity_type == "mapping"
    assert result.qa_state == "corrected"
    assert correction.entity_type == "tender_mapping"
    assert synonym.cell_code == "03.05"
    assert synonym.phrase_norm == "retaining wall allowance"
    assert synonym.source == "correction"


def test_resolve_mapping_correction_accepts_project_trade_id() -> None:
    trade_id = uuid.uuid4()
    session = FakeQASession(
        mapping=True,
        trade=TenderProjectTrade(
            id=trade_id,
            comparison_id=COMPARISON_ID,
            code="PT.JOINERY",
            name="Joinery / cabinetry",
            sort_order=1,
            source="generated",
            anchor_cell_codes=["08.01"],
            seed_assignments=[],
        ),
    )

    result = run_async(
        qa.resolve_qa_item(
            session,
            item_id=session.mapping.id,
            reviewer_id=USER_ID,
            request=QAResolveRequest(
                action="correct",
                corrected_value={"project_trade_id": str(trade_id)},
                reason="Reassign to project trade",
            ),
        )
    )

    correction = _only_added(session, TenderCorrection)
    synonym = _only_added(session, TaxonomySynonym)
    assert result.entity_type == "mapping"
    assert result.qa_state == "corrected"
    assert session.mapping.project_trade_id == trade_id
    assert session.mapping.cell_code is None
    assert correction.field == "project_trade_id"
    assert synonym.cell_code == "08.01"


def test_resolve_mapping_correction_prefers_project_trade_id_over_cell_code() -> None:
    trade_id = uuid.uuid4()
    session = FakeQASession(
        mapping=True,
        trade=TenderProjectTrade(
            id=trade_id,
            comparison_id=COMPARISON_ID,
            code="PT.JOINERY",
            name="Joinery / cabinetry",
            sort_order=1,
            source="generated",
            anchor_cell_codes=["08.01"],
            seed_assignments=[],
        ),
    )

    run_async(
        qa.resolve_qa_item(
            session,
            item_id=session.mapping.id,
            reviewer_id=USER_ID,
            request=QAResolveRequest(
                action="correct",
                corrected_value={
                    "project_trade_id": str(trade_id),
                    "cell_code": "03.05",
                },
                reason="Trade wins",
            ),
        )
    )

    assert session.mapping.project_trade_id == trade_id
    assert session.mapping.cell_code is None
    synonym = _only_added(session, TaxonomySynonym)
    assert synonym.cell_code == "08.01"


def test_report_guard_rejects_pending_review_items() -> None:
    session = FakePendingReviewSession(has_pending=True)

    with pytest.raises(qa.PendingReviewError):
        run_async(qa.assert_no_pending_review(session, comparison_id=COMPARISON_ID))


def test_accept_all_endpoint_checks_owner_and_returns_counts(client: TestClient) -> None:
    result = qa.QAAcceptAllResult(accepted=7, skipped_documents=2)

    with (
        patch("tender.router.require_comparison_owner", new=AsyncMock()),
        patch("tender.router.require_active_entitlement", new=AsyncMock()),
        patch("tender.router.qa.accept_all_pending", new=AsyncMock(return_value=result)),
    ):
        response = client.post(
            f"/api/tender/comparisons/{COMPARISON_ID}/qa/accept-all"
        )

    assert response.status_code == 200
    assert response.json() == {"accepted": 7, "skipped_documents": 2}


def test_accept_all_confirms_items_and_skips_documents() -> None:
    session = FakeAcceptAllSession()

    result = run_async(
        qa.accept_all_pending(
            session,
            comparison_id=COMPARISON_ID,
            reviewer_id=USER_ID,
        )
    )

    assert result.accepted == 1
    assert result.skipped_documents == 1
    assert session.cell_status.qa_state == "confirmed"
    assert session.cell_status.reviewed_by == USER_ID
    correction = _only_added(session, TenderCorrection)
    assert correction.reason == "Bulk accept from matrix review"


def test_mapping_review_item_payload_includes_quote_id() -> None:
    session = FakeQASession(mapping=True)
    row = {
        "item_id": session.mapping.id,
        "entity_type": "mapping",
        "report_impact_cents": 500_000,
        "confidence": 0.58,
    }

    item = run_async(qa._review_item_from_row(session, row))

    assert item.payload["quote_id"] == str(session.line_item.quote_id)
    assert item.payload["cell_code"] == "03.01"
    assert item.payload["project_trade_id"] is None


def test_mapping_review_item_payload_includes_project_trade_id() -> None:
    trade_id = uuid.uuid4()
    session = FakeQASession(mapping=True)
    session.mapping.cell_code = None
    session.mapping.project_trade_id = trade_id
    row = {
        "item_id": session.mapping.id,
        "entity_type": "mapping",
        "report_impact_cents": 500_000,
        "confidence": 0.58,
    }

    item = run_async(qa._review_item_from_row(session, row))

    assert item.payload["project_trade_id"] == str(trade_id)
    assert item.payload["cell_code"] is None


class FakeQASession:
    def __init__(
        self,
        *,
        cell_status: bool = False,
        mapping: bool = False,
        trade: TenderProjectTrade | None = None,
    ) -> None:
        self.cell_status = TenderCellStatus(
            id=ITEM_ID,
            comparison_id=COMPARISON_ID,
            quote_id=uuid.uuid4(),
            cell_code="18.01",
            status="silent_ambiguous",
            amount_cents=250_000,
            bundled_into_cell=None,
            evidence={},
            confidence=0.61,
            qa_state="needs_review",
        )
        self.mapping = TenderMapping(
            id=ITEM_ID,
            line_item_id=uuid.uuid4(),
            cell_code="03.01",
            project_trade_id=None,
            tier="t1_embedding",
            confidence=0.58,
            qa_state="needs_review",
        )
        self.line_item = TenderLineItem(
            id=self.mapping.line_item_id,
            quote_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            page_no=2,
            description_raw="Retaining WALL allowance",
            item_status="included",
            amount_cents=500_000,
        )
        self.trade = trade
        self.include_cell_status = cell_status
        self.include_mapping = mapping
        self.added: list[Any] = []

    async def get(self, model: type, ident: uuid.UUID) -> object | None:
        if model is TenderCellStatus and self.include_cell_status and ident == self.cell_status.id:
            return self.cell_status
        if model is TenderMapping and self.include_mapping and ident == self.mapping.id:
            return self.mapping
        if model is TenderLineItem and ident == self.line_item.id:
            return self.line_item
        if model is TenderProjectTrade and self.trade is not None and ident == self.trade.id:
            return self.trade
        return None

    async def execute(self, statement: Any) -> "FakeResult":
        return FakeResult(None)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()


class FakePendingReviewSession:
    def __init__(self, *, has_pending: bool) -> None:
        self.has_pending = has_pending

    async def execute(self, statement: Any) -> "FakeScalarResult":
        return FakeScalarResult(self.has_pending)


class FakeAcceptAllSession:
    def __init__(self) -> None:
        self.cell_status = TenderCellStatus(
            id=ITEM_ID,
            comparison_id=COMPARISON_ID,
            quote_id=uuid.uuid4(),
            cell_code="18.01",
            status="silent_ambiguous",
            amount_cents=250_000,
            bundled_into_cell=None,
            evidence={},
            confidence=0.61,
            qa_state="needs_review",
        )
        self.document_id = uuid.uuid4()
        self.added: list[Any] = []

    async def execute(self, statement: Any) -> "FakeMappingsResult":
        return FakeMappingsResult(
            [
                {
                    "item_id": self.cell_status.id,
                    "entity_type": "cell_status",
                    "report_impact_cents": 250_000,
                    "confidence": 0.61,
                },
                {
                    "item_id": self.document_id,
                    "entity_type": "document_classification",
                    "report_impact_cents": 0,
                    "confidence": None,
                },
            ]
        )

    async def get(self, model: type, ident: uuid.UUID) -> object | None:
        if model is TenderCellStatus and ident == self.cell_status.id:
            return self.cell_status
        return None

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()


class FakeMappingsResult:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def mappings(self) -> "FakeMappingsResult":
        return self

    def all(self) -> list[dict]:
        return self.rows


class FakeResult:
    def __init__(self, item: object | None) -> None:
        self.item = item

    def scalars(self) -> "FakeResult":
        return self

    def first(self) -> object | None:
        return self.item


class FakeScalarResult:
    def __init__(self, value: bool) -> None:
        self.value = value

    def scalar(self) -> bool:
        return self.value


def _only_added(session: FakeQASession, model: type) -> Any:
    matches = [obj for obj in session.added if isinstance(obj, model)]
    assert len(matches) == 1
    return matches[0]
