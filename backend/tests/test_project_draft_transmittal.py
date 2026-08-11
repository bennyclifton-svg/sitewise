"""HTTP coverage for draft Transmittal register replace."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.database.session import get_db
from app.main import fastapi_app as app
from app.schemas.projects import EvidencePreview

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
EVIDENCE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
NOW = datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)


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


def _draft(*, content: str, version: int = 1) -> DraftArtifact:
    return DraftArtifact(
        id=DRAFT_ID,
        project_id=PROJECT_ID,
        workflow_type="consultant_procurement_structural_engineer",
        version=version,
        status="draft",
        title="Structural RFP",
        workspace_path="04-projects/demo/rfp.md",
        author_user_id=USER_ID,
        content_markdown=content,
        model="gpt-5.6-luna",
        runtime="clerk-sitewise",
        provenance_metadata={},
        created_at=NOW,
        updated_at=NOW,
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


def test_replace_draft_transmittal_rewrites_register(
    client: TestClient,
    mock_session: AsyncMock,
) -> None:
    original = _draft(
        content="\n".join(
            [
                "# Request for Proposal",
                "",
                "## Project Documents (1 document)",
                "",
                "| Document number | Title | Rev | Category |",
                "| --- | --- | --- | --- |",
                "| A001 | Old drawing | A | Architectural |",
                "",
                "## Citation key",
                "[1] Project Profile — current",
                "",
            ]
        )
    )
    preview = EvidencePreview(
        id=EVIDENCE_ID,
        title="Electrical layout",
        filename="E001.pdf",
        relative_path="04-projects/demo/E001.pdf",
        source_type="project_evidence",
        document_class="drawing",
        excerpt="",
        document_number="E001",
        revision="C",
        category="Electrical",
    )

    async def revise_side_effect(*_args, **kwargs):
        return _draft(content=kwargs["content_markdown"], version=2)

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.projects.get_draft_artifact", new=AsyncMock(return_value=original)
        ),
        patch(
            "app.api.projects.require_project_evidence_ids",
            new=AsyncMock(),
        ),
        patch(
            "app.api.projects.list_workspace_files_for_project",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.api.projects._list_project_evidence_previews",
            new=AsyncMock(return_value=[preview]),
        ),
        patch(
            "app.api.projects.revise_workflow_artefact",
            new=AsyncMock(side_effect=revise_side_effect),
        ) as revise_artefact,
    ):
        response = client.post(
            f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}/transmittal",
            json={
                "expected_base_version": 1,
                "evidence_ids": [str(EVIDENCE_ID)],
            },
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["draft"]["version"] == 2
    markdown = body["draft"]["content_markdown"]
    assert "## Transmittal (1 document)" in markdown
    assert "| E001 | Electrical layout | C | Electrical |" in markdown
    assert "| A001 | Old drawing | A | Architectural |" not in markdown
    revise_artefact.assert_awaited_once()
