from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.project import Project
from app.database.session import get_db
from tender import procurement_router
from tender.services.review_progress import document_progress, review_activity


@pytest.fixture
def endpoint():
    owner_id, project_id, comparison_id = uuid4(), uuid4(), uuid4()
    comparison = SimpleNamespace(
        id=comparison_id,
        project_id=project_id,
        context={"review_profile": "head_contractor", "package_name": "Main works"},
        context_provenance={"row_id": str(uuid4())},
        created_at=datetime.now(UTC),
        status="processing",
    )
    project = SimpleNamespace(id=project_id, owner_user_id=owner_id)
    session = AsyncMock()
    session.get.side_effect = lambda model, key: (
        project if model is Project else comparison
    )
    result = MagicMock()
    result.scalars.return_value = []
    result.mappings.return_value = []
    session.execute.return_value = result
    session.scalar.return_value = None
    app = FastAPI()
    app.include_router(procurement_router.router)

    async def database():
        yield session

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        owner_id, "owner@example.test"
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, comparison, project, session


def test_owner_can_poll_new_comparison(endpoint):
    client, comparison, _, _ = endpoint
    response = client.get(f"/procurement-reviews/{comparison.id}")
    assert response.status_code == 200, response.text
    assert response.json()["comparison_id"] == str(comparison.id)


@pytest.mark.parametrize(
    ("suffix", "method"), [("", "get"), ("/evidence", "get"), ("/retry", "post")]
)
def test_other_owners_cannot_read_or_retry_comparison(endpoint, suffix, method):
    client, comparison, project, session = endpoint
    project.owner_user_id = uuid4()
    response = getattr(client, method)(f"/procurement-reviews/{comparison.id}{suffix}")
    assert response.status_code == 404, response.text
    session.execute.assert_not_awaited()


def test_missing_project_is_not_accessible(endpoint):
    client, comparison, _, session = endpoint
    session.get.side_effect = lambda model, key: (
        None if model is Project else comparison
    )
    assert client.get(f"/procurement-reviews/{comparison.id}").status_code == 404


def test_progress_counts_unique_saved_pages_and_retains_blank_pages():
    now = datetime.now(UTC)
    document = dict(
        id=uuid4(),
        filename="Quote.pdf",
        firm_name="Builder",
        pages=5,
        read_pages=[1, 2, 2, 3, 0, 99],
        complete=False,
    )
    job = SimpleNamespace(
        status="running",
        kind="read_review_document",
        locked_at=now,
        attempts=0,
        payload={"document_id": str(document["id"])},
    )
    progress = document_progress(document, [job], now=now)
    assert progress["pages_read"] == 3
    assert progress["state"] == "reading"
    assert progress["firm_name"] == "Builder"
    assert (
        document_progress({**document, "complete": True}, [job], now=now)["state"]
        == "complete"
    )


@pytest.mark.parametrize(
    ("status", "attempts", "age", "expected"),
    [
        ("queued", 0, 0, "queued"),
        ("queued", 1, 0, "retrying"),
        ("running", 0, 20, "running"),
        ("running", 0, 120, "waiting"),
        ("done", 0, 0, "waiting"),
    ],
)
def test_activity_distinguishes_waiting_retry_and_live_worker(
    status, attempts, age, expected
):
    now = datetime.now(UTC)
    job = SimpleNamespace(
        status=status, attempts=attempts, locked_at=now - timedelta(seconds=age)
    )
    assert review_activity([job], now=now) == expected


def test_completed_reading_moves_to_preparation_even_before_job_is_claimed(endpoint):
    client, comparison, _, session = endpoint
    document = dict(
        id=uuid4(),
        filename="Fee.pdf",
        firm_name="Engineers",
        pages=2,
        read_pages=[1, 2],
        complete=True,
    )
    session.execute.return_value.mappings.return_value = [document]
    response = client.get(f"/procurement-reviews/{comparison.id}")
    assert response.status_code == 200, response.text
    assert response.json()["phase"] == "preparing"
    assert response.json()["activity"] == "waiting"
    assert response.json()["documents"][0]["pages_read"] == 2


def test_failure_keeps_page_counts_and_names_the_failed_file(endpoint):
    client, comparison, _, session = endpoint
    doc_id = uuid4()
    session.execute.return_value.mappings.return_value = [
        dict(
            id=doc_id,
            filename="Fee.pdf",
            firm_name="Engineers",
            pages=5,
            read_pages=[1, 2, 3],
            complete=False,
        )
    ]
    session.execute.return_value.scalars.return_value = [
        SimpleNamespace(
            status="failed",
            attempts=3,
            kind="read_review_document",
            locked_at=None,
            payload={"document_id": str(doc_id)},
        )
    ]
    response = client.get(f"/procurement-reviews/{comparison.id}")
    assert response.status_code == 200, response.text
    assert response.json()["phase"] == "failed"
    assert "Fee.pdf" in response.json()["error"]
    assert response.json()["documents"][0]["pages_read"] == 3


def test_wrong_worker_pipeline_is_visible_and_cannot_be_retried(endpoint):
    client, comparison, _, session = endpoint
    job = SimpleNamespace(
        status="failed",
        attempts=3,
        kind="classify_document",
        locked_at=None,
        payload={},
    )
    session.execute.return_value.scalars.return_value = [job]
    response = client.get(f"/procurement-reviews/{comparison.id}")
    assert response.status_code == 200
    assert response.json()["phase"] == "failed"
    assert response.json()["can_retry"] is False
    assert "service update" in response.json()["error"]
    with patch.object(procurement_router, "require_active_entitlement", AsyncMock()):
        retry = client.post(f"/procurement-reviews/{comparison.id}/retry")
    assert retry.status_code == 409
    assert job.status == "failed"


def test_owner_can_retry_failed_reader_without_resetting_finished_work(endpoint):
    client, comparison, _, session = endpoint
    failed = SimpleNamespace(
        status="failed",
        attempts=3,
        kind="read_review_document",
        locked_at=None,
        payload={},
        last_error="read failed",
    )
    done = SimpleNamespace(
        status="done", attempts=0, kind="ingest_document", locked_at=None, payload={}
    )
    session.execute.return_value.scalars.return_value = [done, failed]
    with patch.object(procurement_router, "require_active_entitlement", AsyncMock()):
        response = client.post(f"/procurement-reviews/{comparison.id}/retry")
    assert response.status_code == 200, response.text
    assert failed.status == "queued"
    assert failed.attempts == 0
    assert done.status == "done"
