import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.session import get_db
from app.main import fastapi_app as app
from tender.models import TenderComparison, TenderDocument, TenderJob, TenderQuote

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
COMPARISON_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
QUOTE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
DOCUMENT_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
JOB_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")
NOW = datetime(2026, 6, 12, 12, 0, 0, tzinfo=timezone.utc)


def _context_payload(**overrides) -> dict:
    payload = {
        "state": "NSW",
        "region": "metro",
        "build_type": "new_build",
        "dwelling_class": "class_1a",
        "storeys": 2,
        "floor_area_m2": 220.5,
        "site_area_m2": 450.0,
        "soil_class": "M",
        "slope_class": "moderate",
        "bal_rating": "12.5",
        "wind_rating": "N2",
        "flood_overlay": False,
        "heritage_overlay": None,
        "existing_dwelling_era": None,
        "demolition_required": False,
        "spec_level": "mid",
        "target_budget_cents": 95_000_000,
        "notes": "steep rear yard",
    }
    payload.update(overrides)
    return payload


def _comparison() -> TenderComparison:
    return TenderComparison(
        id=COMPARISON_ID,
        project_id=PROJECT_ID,
        status="intake",
        context=_context_payload(context_version=1),
        created_by=USER_ID,
        created_at=NOW,
        updated_at=NOW,
    )


def _quote() -> TenderQuote:
    return TenderQuote(
        id=QUOTE_ID,
        comparison_id=COMPARISON_ID,
        builder_name="Acme Builders",
        gst_treatment="inclusive",
        contract_type="hia",
        stage="intake",
        created_at=NOW,
        updated_at=NOW,
    )


def _document() -> TenderDocument:
    return TenderDocument(
        id=DOCUMENT_ID,
        quote_id=QUOTE_ID,
        storage_path=f"tender/{COMPARISON_ID}/{QUOTE_ID}/quote.pdf",
        original_filename="quote.pdf",
        mime_type="application/pdf",
        ocr_applied=False,
        ingest_status="pending",
        created_at=NOW,
        updated_at=NOW,
    )


def _job() -> TenderJob:
    return TenderJob(
        id=JOB_ID,
        kind="ingest_document",
        comparison_id=COMPARISON_ID,
        quote_id=QUOTE_ID,
        payload={"document_id": str(DOCUMENT_ID)},
        status="queued",
        attempts=0,
        run_after=NOW,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
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


def _refresh_with_test_values(targets: dict[type, object]):
    async def _refresh(instance) -> None:
        template = targets[type(instance)]
        for key, value in template.__dict__.items():
            if not key.startswith("_"):
                setattr(instance, key, value)

    return _refresh


def test_create_comparison_validates_context(
    client: TestClient, mock_session: AsyncMock
) -> None:
    response = client.post(
        "/api/tender/comparisons",
        json={"project_id": str(PROJECT_ID), "context": _context_payload(soil_class="Z9")},
    )

    assert response.status_code == 422
    mock_session.add.assert_not_called()


def test_create_comparison_returns_created_row(
    client: TestClient, mock_session: AsyncMock
) -> None:
    mock_session.refresh = AsyncMock(
        side_effect=_refresh_with_test_values({TenderComparison: _comparison()})
    )

    response = client.post(
        "/api/tender/comparisons",
        json={"project_id": str(PROJECT_ID), "context": _context_payload()},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == str(COMPARISON_ID)
    assert payload["created_by"] == str(USER_ID)
    assert payload["context"]["context_version"] == 1
    added = mock_session.add.call_args.args[0]
    assert isinstance(added, TenderComparison)
    assert added.project_id == PROJECT_ID


def test_create_quote_under_comparison(client: TestClient, mock_session: AsyncMock) -> None:
    mock_session.get = AsyncMock(return_value=_comparison())
    mock_session.refresh = AsyncMock(
        side_effect=_refresh_with_test_values({TenderQuote: _quote()})
    )

    response = client.post(
        f"/api/tender/comparisons/{COMPARISON_ID}/quotes",
        json={"builder_name": "Acme Builders", "gst_treatment": "inclusive"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == str(QUOTE_ID)
    assert payload["builder_name"] == "Acme Builders"
    added = mock_session.add.call_args.args[0]
    assert isinstance(added, TenderQuote)
    assert added.comparison_id == COMPARISON_ID


def test_create_quote_returns_404_for_missing_comparison(
    client: TestClient, mock_session: AsyncMock
) -> None:
    mock_session.get = AsyncMock(return_value=None)

    response = client.post(
        f"/api/tender/comparisons/{COMPARISON_ID}/quotes",
        json={"builder_name": "Acme Builders"},
    )

    assert response.status_code == 404


def test_upload_document_stores_registers_and_enqueues(
    client: TestClient, mock_session: AsyncMock
) -> None:
    quote = _quote()
    mock_session.get = AsyncMock(return_value=quote)
    mock_session.refresh = AsyncMock(
        side_effect=_refresh_with_test_values(
            {TenderDocument: _document(), TenderJob: _job()}
        )
    )

    with (
        patch("tender.router.upload_project_file", return_value=_document().storage_path)
        as mock_upload,
        patch("tender.router.enqueue", new=AsyncMock(return_value=_job())) as mock_enqueue,
    ):
        response = client.post(
            f"/api/tender/quotes/{QUOTE_ID}/documents",
            files={"file": ("quote.pdf", b"%PDF-1.7\npayload", "application/pdf")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["document"]["id"] == str(DOCUMENT_ID)
    assert payload["job"]["id"] == str(JOB_ID)
    mock_upload.assert_called_once()
    assert mock_upload.call_args.kwargs["storage_key"] == (
        f"tender/{COMPARISON_ID}/{QUOTE_ID}/quote.pdf"
    )
    mock_enqueue.assert_awaited_once()
    assert mock_enqueue.await_args.kwargs["kind"] == "ingest_document"
    assert mock_enqueue.await_args.kwargs["payload"] == {"document_id": str(DOCUMENT_ID)}


def test_upload_document_rejects_empty_file(
    client: TestClient, mock_session: AsyncMock
) -> None:
    mock_session.get = AsyncMock(return_value=_quote())

    response = client.post(
        f"/api/tender/quotes/{QUOTE_ID}/documents",
        files={"file": ("quote.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400


def test_get_comparison_detail_shape(client: TestClient, mock_session: AsyncMock) -> None:
    comparison = _comparison()
    quote = _quote()
    document = _document()
    quote.documents = [document]
    comparison.quotes = [quote]

    result = MagicMock()
    result.scalars.return_value.unique.return_value.one_or_none.return_value = comparison
    mock_session.execute = AsyncMock(return_value=result)

    response = client.get(f"/api/tender/comparisons/{COMPARISON_ID}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(COMPARISON_ID)
    assert payload["quotes"][0]["documents"][0]["ingest_status"] == "pending"
