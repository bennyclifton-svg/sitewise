"""REST authorization for document classification overrides (X1 Stage 5.4)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.project import Project
from app.database.session import get_db
from app.database.source_document import SourceDocument
from app.main import fastapi_app as app

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_B = uuid.UUID("22222222-2222-2222-2222-222222222222")
PROJECT_A = uuid.UUID("33333333-3333-3333-3333-333333333333")
DOCUMENT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _project(project_id: uuid.UUID) -> Project:
    return Project(
        id=project_id,
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
    )


def _document() -> SourceDocument:
    return SourceDocument(
        id=DOCUMENT_ID,
        project_id=PROJECT_A,
        project="other",
        phase="delivery",
        document_class="report",
        filename="Heritage Impact Statement.pdf",
        relative_path="04-projects/other/_inbox/Heritage Impact Statement.pdf",
        normalized_content="x" * 200,
        content_hash="b" * 64,
        document_metadata={"basis": "filename", "confidence": "0.85"},
        source_type="project_evidence",
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.get = AsyncMock(return_value=_document())
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


def test_override_rejects_cross_project_document(client: TestClient) -> None:
    """Doc belongs to project A; caller is authorized for project B → 404, not 403."""
    with (
        patch(
            "app.api.projects.get_project",
            new=AsyncMock(return_value=_project(PROJECT_B)),
        ),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
    ):
        response = client.put(
            f"/projects/{PROJECT_B}/documents/{DOCUMENT_ID}/classification",
            json={
                "document_class": "certificate",
                "document_subject": "town_planner",
            },
        )

    assert response.status_code == 404
    assert "document" in str(response.json()["detail"]).lower()
    assert response.status_code != 403


def test_bulk_override_updates_selected_documents(client: TestClient) -> None:
    first = _document()
    second = _document()
    second.id = uuid.uuid4()
    second.filename = "Structural Plan.pdf"
    second.document_class = "drawing"
    second.document_metadata = {"subject": "structural"}

    with (
        patch(
            "app.api.projects.get_project",
            new=AsyncMock(return_value=_project(PROJECT_A)),
        ),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.projects.set_document_classifications",
            new=AsyncMock(return_value=[first, second]),
        ) as update,
    ):
        response = client.put(
            f"/projects/{PROJECT_A}/documents/classification/batch",
            json={
                "document_ids": [str(first.id), str(second.id)],
                "document_subject": "architect",
            },
        )

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["documents"]] == [
        str(first.id),
        str(second.id),
    ]
    assert update.await_args.kwargs["document_class"] is None
    assert update.await_args.kwargs["document_subject"] == "architect"


def test_bulk_override_requires_a_type_or_category(client: TestClient) -> None:
    response = client.put(
        f"/projects/{PROJECT_A}/documents/classification/batch",
        json={"document_ids": [str(DOCUMENT_ID)]},
    )

    assert response.status_code == 422
