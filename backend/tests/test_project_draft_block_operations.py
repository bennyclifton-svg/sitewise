"""HTTP coverage for versioned artefact block operations."""

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
from app.projects.artefact_blocks import materialize_block_identity, markdown_blocks

USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
NOW = datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc)


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


def _draft(
    *,
    workflow_type: str,
    content: str,
    version: int = 1,
    provenance: dict | None = None,
) -> DraftArtifact:
    return DraftArtifact(
        id=DRAFT_ID,
        project_id=PROJECT_ID,
        workflow_type=workflow_type,
        version=version,
        status="draft",
        title="Artefact",
        workspace_path="04-projects/demo/artefact.md",
        author_user_id=USER_ID,
        content_markdown=content,
        model="gpt-5.6-luna",
        runtime="clerk-sitewise",
        provenance_metadata=provenance or {},
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


@pytest.mark.parametrize(
    "workflow_type",
    [
        "create_pmp",
        "consultant_procurement_structural_engineer",
        "trade_rft_electrical_services",
    ],
)
def test_block_update_add_duplicate_delete_and_protect(
    client: TestClient,
    mock_session: AsyncMock,
    workflow_type: str,
) -> None:
    generated = materialize_block_identity(
        "## Scope\n\nExisting paragraph.\n\n- First item\n",
        actor_source="ai",
        now=NOW,
    )
    paragraph, list_item = markdown_blocks(generated.markdown)[:2]
    original = _draft(
        workflow_type=workflow_type,
        content=generated.markdown,
        provenance={"blocks": generated.metadata},
    )

    async def revise_side_effect(*_args, **kwargs):
        return _draft(
            workflow_type=workflow_type,
            content=kwargs["content_markdown"],
            version=2,
            provenance=dict(original.provenance_metadata or {}),
        )

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.projects.get_draft_artifact", new=AsyncMock(return_value=original)
        ),
        patch(
            "app.api.projects.revise_workflow_artefact",
            new=AsyncMock(side_effect=revise_side_effect),
        ) as revise_artefact,
    ):
        update_response = client.post(
            f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}/blocks",
            json={
                "expected_base_version": 1,
                "operations": [
                    {
                        "operation": "UPDATE",
                        "target": {"id": paragraph.id, "type": "paragraph"},
                        "content": "Updated paragraph.",
                    }
                ],
            },
        )
        assert update_response.status_code == 200, update_response.text
        update_payload = update_response.json()
        assert "draft" not in update_payload
        assert paragraph.id in update_payload["changed_block_ids"]
        assert paragraph.id in update_payload["delta"]["changed_block_ids"]
        assert (
            update_payload["delta"]["blocks"][paragraph.id]["last_modified_by"]
            == "user"
        )
        assert len(update_payload["delta"]["content_sha256"]) == 64
        # Provenance flush expires server-default updated_at; response build must
        # refresh the ORM row before reading it (async MissingGreenlet otherwise).
        mock_session.refresh.assert_awaited()
        assert revise_artefact.await_args.kwargs["content_markdown"].count(
            "Updated paragraph."
        )
        assert (
            "Existing paragraph."
            not in revise_artefact.await_args.kwargs["content_markdown"]
        )
        assert "- First item" in revise_artefact.await_args.kwargs["content_markdown"]

        protect_response = client.post(
            f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}/blocks",
            json={
                "expected_base_version": 1,
                "operations": [
                    {
                        "operation": "PROTECT",
                        "target": {"id": paragraph.id, "type": "paragraph"},
                    }
                ],
            },
        )
        assert protect_response.status_code == 200, protect_response.text
        protect_payload = protect_response.json()
        assert (
            protect_payload["delta"]["blocks"][paragraph.id]["user_protected"] is True
        )
        assert (
            revise_artefact.await_args.kwargs["content_markdown"] == generated.markdown
        )

        add_response = client.post(
            f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}/blocks",
            json={
                "expected_base_version": 1,
                "operations": [
                    {
                        "operation": "ADD",
                        "target": {"id": list_item.id, "type": "list_item"},
                        "placement": "after",
                        "content": "- Added item",
                    }
                ],
            },
        )
        assert add_response.status_code == 200, add_response.text
        assert "- Added item" in revise_artefact.await_args.kwargs["content_markdown"]
        assert add_response.json()["delta"]["changed_block_ids"]

        duplicate_response = client.post(
            f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}/blocks",
            json={
                "expected_base_version": 1,
                "operations": [
                    {
                        "operation": "DUPLICATE",
                        "target": {"id": list_item.id, "type": "list_item"},
                    }
                ],
            },
        )
        assert duplicate_response.status_code == 200, duplicate_response.text
        assert (
            revise_artefact.await_args.kwargs["content_markdown"].count("- First item")
            == 2
        )

        delete_response = client.post(
            f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}/blocks",
            json={
                "expected_base_version": 1,
                "operations": [
                    {
                        "operation": "DELETE",
                        "target": {"id": list_item.id, "type": "list_item"},
                    }
                ],
            },
        )
        assert delete_response.status_code == 200, delete_response.text
        assert (
            "- First item"
            not in revise_artefact.await_args.kwargs["content_markdown"]
        )
        assert (
            "Existing paragraph."
            in revise_artefact.await_args.kwargs["content_markdown"]
        )
        assert list_item.id in delete_response.json()["delta"]["deleted_block_ids"]

    assert revise_artefact.await_count == 5
    assert all(
        call.kwargs["actor_source"] == "user_block_operation"
        for call in revise_artefact.await_args_list
    )

    conflict_provenance = {
        "blocks": {
            paragraph.id: {
                **generated.metadata[paragraph.id],
                "status": "conflict",
            }
        }
    }
    keep_draft = _draft(
        workflow_type=workflow_type,
        content=generated.markdown,
        provenance=conflict_provenance,
    )

    async def keep_revise(*_args, **kwargs):
        return _draft(
            workflow_type=workflow_type,
            content=kwargs["content_markdown"],
            version=2,
            provenance=conflict_provenance,
        )

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch(
            "app.api.projects.get_draft_artifact",
            new=AsyncMock(return_value=keep_draft),
        ),
        patch(
            "app.api.projects.revise_workflow_artefact",
            new=AsyncMock(side_effect=keep_revise),
        ),
    ):
        keep_response = client.post(
            f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}/blocks",
            json={
                "expected_base_version": 1,
                "operations": [
                    {
                        "operation": "KEEP",
                        "target": {"id": paragraph.id, "type": "paragraph"},
                    }
                ],
            },
        )
    assert keep_response.status_code == 200, keep_response.text
    assert (
        keep_response.json()["delta"]["blocks"][paragraph.id]["status"] == "active"
    )
