from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.project import Project
from app.database.session import get_db
from app.main import fastapi_app as app
from tender.router import create_comparison
from tender.schemas import ComparisonDetail

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
COMPARISON_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
QUOTE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
DOCUMENT_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
JOB_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")
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


def test_create_comparison_returns_created_comparison(client: TestClient) -> None:
    created = _comparison(id=COMPARISON_ID)

    with (
        patch("tender.router.ensure_user_exists", new=AsyncMock()),
        patch("tender.router.require_active_entitlement", new=AsyncMock()),
        patch("tender.router.get_project", new=AsyncMock(return_value=_project())),
        patch("tender.router.create_comparison", new=AsyncMock(return_value=created)),
    ):
        response = client.post(
            "/api/tender/comparisons",
            json={"project_id": str(PROJECT_ID), "context": _context()},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == str(COMPARISON_ID)
    assert payload["project_id"] == str(PROJECT_ID)
    assert payload["status"] == "intake"
    assert payload["context"]["state"] == "NSW"


def test_create_comparison_preloads_empty_quotes() -> None:
    session = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock(side_effect=_refresh_comparison)

    async def _run() -> None:
        comparison = await create_comparison(
            session,
            project_id=PROJECT_ID,
            context=_context(),
            created_by=USER_ID,
        )

        assert "quotes" not in inspect(comparison).unloaded
        assert ComparisonDetail.model_validate(comparison).quotes == []

    from tests.conftest import run_async

    run_async(_run())


def test_list_comparisons_returns_project_scoped_rows(client: TestClient) -> None:
    comparison = _comparison(id=COMPARISON_ID)
    comparison.quotes = [_quote()]

    with (
        patch("tender.router.get_project", new=AsyncMock(return_value=_project())),
        patch("tender.router.list_comparisons", new=AsyncMock(return_value=[comparison])),
    ):
        response = client.get(f"/api/tender/comparisons?project_id={PROJECT_ID}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["comparisons"][0]["id"] == str(COMPARISON_ID)
    assert payload["comparisons"][0]["quotes"][0]["id"] == str(QUOTE_ID)


def test_get_comparison_returns_full_state(client: TestClient) -> None:
    comparison = _comparison(id=COMPARISON_ID)
    quote = _quote()
    quote.documents = [_document()]
    comparison.quotes = [quote]

    with patch(
        "tender.router.require_comparison_owner",
        new=AsyncMock(return_value=comparison),
    ):
        response = client.get(f"/api/tender/comparisons/{COMPARISON_ID}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(COMPARISON_ID)
    assert payload["quotes"][0]["id"] == str(QUOTE_ID)
    assert payload["quotes"][0]["documents"][0]["id"] == str(DOCUMENT_ID)


def test_patch_context_requeues_expectations(client: TestClient) -> None:
    comparison = _comparison(id=COMPARISON_ID)
    enqueue = AsyncMock(return_value=_job("run_expectations"))

    with (
        patch(
            "tender.router.require_comparison_owner",
            new=AsyncMock(return_value=comparison),
        ),
        patch("tender.router.jobs.enqueue", new=enqueue),
    ):
        response = client.patch(
            f"/api/tender/comparisons/{COMPARISON_ID}/context",
            json={"context": {**_context(), "storeys": 1}},
        )

    assert response.status_code == 200
    assert response.json()["context"]["storeys"] == 1
    enqueue.assert_awaited_once()
    assert enqueue.await_args.kwargs["kind"] == "run_expectations"
    assert enqueue.await_args.kwargs["comparison_id"] == COMPARISON_ID


def test_create_quote_returns_quote(client: TestClient) -> None:
    quote = _quote()

    with (
        patch(
            "tender.router.require_comparison_owner",
            new=AsyncMock(return_value=_comparison(id=COMPARISON_ID)),
        ),
        patch("tender.router.create_quote", new=AsyncMock(return_value=quote)),
    ):
        response = client.post(
            f"/api/tender/comparisons/{COMPARISON_ID}/quotes",
            json={
                "builder_name": "A Homes",
                "stated_total_cents": 1_100_000_00,
                "gst_treatment": "inclusive",
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == str(QUOTE_ID)
    assert payload["builder_name"] == "A Homes"


def test_upload_document_stores_pending_document_and_enqueues_ingest(
    client: TestClient,
) -> None:
    quote = _quote()
    document = _document()
    enqueue = AsyncMock(return_value=_job("ingest_document"))

    with (
        patch(
            "tender.router.require_quote_owner",
            new=AsyncMock(return_value=quote),
        ),
        patch(
            "tender.router.store_quote_document",
            new=AsyncMock(return_value=document),
        ),
        patch("tender.router.jobs.enqueue", new=enqueue),
    ):
        response = client.post(
            f"/api/tender/quotes/{QUOTE_ID}/documents",
            files=[("file", ("quote.pdf", b"%PDF-1.4\nbody", "application/pdf"))],
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["document"]["id"] == str(DOCUMENT_ID)
    assert payload["document"]["ingest_status"] == "pending"
    assert payload["job"]["kind"] == "ingest_document"
    enqueue.assert_awaited_once()
    assert enqueue.await_args.kwargs["quote_id"] == QUOTE_ID
    assert enqueue.await_args.kwargs["payload"] == {"document_id": str(DOCUMENT_ID)}


def test_attach_project_file_document_enqueues_ingest(client: TestClient) -> None:
    quote = _quote()
    document = _document()
    enqueue = AsyncMock(return_value=_job("ingest_document"))

    with (
        patch(
            "tender.router.require_quote_owner",
            new=AsyncMock(return_value=quote),
        ),
        patch(
            "tender.router.store_project_file_quote_document",
            new=AsyncMock(return_value=document),
        ),
        patch("tender.router.jobs.enqueue", new=enqueue),
    ):
        response = client.post(
            f"/api/tender/quotes/{QUOTE_ID}/documents/from-project-file",
            json={"workspace_path": "04-projects/demo/05-procurement/a-homes.pdf"},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["document"]["id"] == str(DOCUMENT_ID)
    assert payload["job"]["kind"] == "ingest_document"
    enqueue.assert_awaited_once()
    assert enqueue.await_args.kwargs["quote_id"] == QUOTE_ID
    assert enqueue.await_args.kwargs["payload"] == {"document_id": str(DOCUMENT_ID)}


def test_retry_stage_enqueues_requested_stage(client: TestClient) -> None:
    enqueue = AsyncMock(return_value=_job("map_items"))

    with (
        patch(
            "tender.router.require_quote_owner",
            new=AsyncMock(return_value=_quote()),
        ),
        patch("tender.router.jobs.enqueue", new=enqueue),
    ):
        response = client.post(f"/api/tender/quotes/{QUOTE_ID}/retry/map_items")

    assert response.status_code == 201
    payload = response.json()
    assert payload["kind"] == "map_items"
    enqueue.assert_awaited_once()
    assert enqueue.await_args.kwargs["kind"] == "map_items"
    assert enqueue.await_args.kwargs["quote_id"] == QUOTE_ID
    assert enqueue.await_args.kwargs["payload"] == {"retry": True}


def test_quote_retry_rejects_internal_silence_stage(client: TestClient) -> None:
    enqueue = AsyncMock()

    with patch("tender.router.jobs.enqueue", new=enqueue):
        response = client.post(f"/api/tender/quotes/{QUOTE_ID}/retry/infer_silence")

    assert response.status_code == 400
    assert response.json()["detail"] == "Tender stage cannot be manually run for a quote"
    enqueue.assert_not_awaited()


def test_comparison_retry_enqueues_comparison_stage(client: TestClient) -> None:
    comparison = _comparison(id=COMPARISON_ID)
    enqueue = AsyncMock(return_value=_job("run_analysis"))

    with (
        patch(
            "tender.router.require_comparison_owner",
            new=AsyncMock(return_value=comparison),
        ),
        patch("tender.router.jobs.enqueue", new=enqueue),
    ):
        response = client.post(
            f"/api/tender/comparisons/{COMPARISON_ID}/retry/run_analysis"
        )

    assert response.status_code == 201
    assert response.json()["kind"] == "run_analysis"
    assert comparison.status == "processing"
    enqueue.assert_awaited_once()
    assert enqueue.await_args.kwargs["kind"] == "run_analysis"
    assert enqueue.await_args.kwargs["comparison_id"] == COMPARISON_ID
    assert "quote_id" not in enqueue.await_args.kwargs
    assert enqueue.await_args.kwargs["payload"] == {"retry": True}


def test_comparison_retry_rejects_internal_silence_stage(client: TestClient) -> None:
    enqueue = AsyncMock()

    with patch("tender.router.jobs.enqueue", new=enqueue):
        response = client.post(
            f"/api/tender/comparisons/{COMPARISON_ID}/retry/infer_silence"
        )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Tender stage cannot be manually run for a comparison"
    )
    enqueue.assert_not_awaited()


def _project() -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        slug="demo",
        title="Demo Project",
        workspace_path="04-projects/demo",
        phase="procurement",
        archetype="small-commercial",
        user_role="architect-pm",
        state="NSW",
        status="active",
        project_metadata={},
        created_at=NOW,
        updated_at=NOW,
    )


def _comparison(*, id: uuid.UUID = COMPARISON_ID):
    from tender.models import TenderComparison

    return TenderComparison(
        id=id,
        project_id=PROJECT_ID,
        status="intake",
        context=_context(),
        created_by=USER_ID,
        created_at=NOW,
        updated_at=NOW,
    )


async def _refresh_comparison(comparison) -> None:
    comparison.id = COMPARISON_ID
    comparison.status = "intake"
    comparison.created_at = NOW
    comparison.updated_at = NOW


def _quote():
    from tender.models import TenderQuote

    return TenderQuote(
        id=QUOTE_ID,
        comparison_id=COMPARISON_ID,
        builder_name="A Homes",
        builder_abn=None,
        quote_ref=None,
        quote_date=None,
        stated_total_cents=1_100_000_00,
        gst_treatment="inclusive",
        contract_type="unknown",
        validity_days=None,
        stage="intake",
        created_at=NOW,
        updated_at=NOW,
    )


def _document():
    from tender.models import TenderDocument

    return TenderDocument(
        id=DOCUMENT_ID,
        quote_id=QUOTE_ID,
        storage_path="tender/comparisons/333/quotes/444/quote.pdf",
        original_filename="quote.pdf",
        mime_type="application/pdf",
        doc_type="quote_letter",
        ocr_applied=False,
        page_count=None,
        ingest_status="pending",
        created_at=NOW,
        updated_at=NOW,
    )


def _job(kind: str):
    return SimpleNamespace(
        id=JOB_ID,
        kind=kind,
        comparison_id=COMPARISON_ID,
        quote_id=QUOTE_ID,
        status="queued",
        attempts=0,
        last_error=None,
        run_after=NOW,
        created_at=NOW,
    )


def _context() -> dict:
    return {
        "state": "NSW",
        "region": "metro",
        "build_type": "new_build",
        "dwelling_class": "class_1a",
        "storeys": 2,
        "floor_area_m2": 220,
        "soil_class": "H2",
        "slope_class": "flat",
        "bal_rating": "none",
        "spec_level": "mid",
    }
