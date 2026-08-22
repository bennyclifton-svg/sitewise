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
from app.projects.artefact_revisions import ArtefactRevisionConflict

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


CLIENT_OPERATION_ID = "0f2a4c6e-8b1d-4f3a-9c5e-7d8f0a1b2c3d"


def _add_row_body(list_item_id: str, base_version: int) -> dict:
    """One logical `add row below`, replayable because the id never changes."""
    return {
        "expected_base_version": base_version,
        "client_operation_id": CLIENT_OPERATION_ID,
        "operations": [
            {
                "operation": "ADD",
                "target": {"id": list_item_id, "type": "list_item"},
                "placement": "after",
                "content": "- Added item",
            }
        ],
    }


def _revision_stream(initial: DraftArtifact):
    """Mimic `revise`: a new row per revision, inheriting the base provenance."""
    state = {"draft": initial}

    async def revise_side_effect(*_args, **kwargs):
        base = state["draft"]
        if kwargs["expected_base_version"] != base.version:
            raise ArtefactRevisionConflict(
                f"Expected v{kwargs['expected_base_version']}, current version is v{base.version}"
            )
        revision = _draft(
            workflow_type=base.workflow_type,
            content=kwargs["content_markdown"],
            version=base.version + 1,
            provenance=dict(base.provenance_metadata or {}),
        )
        revision.id = uuid.uuid4()
        state["draft"] = revision
        return revision

    async def get_draft(*_args, **_kwargs):
        return state["draft"]

    return state, revise_side_effect, get_draft


def _seeded_list_draft() -> tuple[DraftArtifact, str]:
    generated = materialize_block_identity(
        "## Scope\n\n- First item\n", actor_source="ai", now=NOW
    )
    list_item = markdown_blocks(generated.markdown)[0]
    assert list_item.id is not None
    return (
        _draft(
            workflow_type="create_pmp",
            content=generated.markdown,
            provenance={"blocks": generated.metadata},
        ),
        list_item.id,
    )


def test_replayed_client_operation_id_does_not_apply_twice(
    client: TestClient,
) -> None:
    original, list_item_id = _seeded_list_draft()
    state, revise_side_effect, get_draft = _revision_stream(original)

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.get_draft_artifact", new=AsyncMock(side_effect=get_draft)),
        patch(
            "app.api.projects.revise_workflow_artefact",
            new=AsyncMock(side_effect=revise_side_effect),
        ) as revise_artefact,
    ):
        first = client.post(
            f"/projects/{PROJECT_ID}/drafts/{original.id}/blocks",
            json=_add_row_body(list_item_id, 1),
        )
        assert first.status_code == 200, first.text
        applied = state["draft"]
        assert applied.content_markdown.count("- Added item") == 1

        # The reply was lost; the client rebased onto the latest revision and
        # re-sent the same logical operation.
        replay = client.post(
            f"/projects/{PROJECT_ID}/drafts/{applied.id}/blocks",
            json=_add_row_body(list_item_id, applied.version),
        )

    assert replay.status_code == 200, replay.text
    # The bug this packet closes: one logical insert, two rows.
    assert state["draft"].content_markdown.count("- Added item") == 1
    assert revise_artefact.await_count == 1


def test_replay_returns_the_original_delta(client: TestClient) -> None:
    original, list_item_id = _seeded_list_draft()
    state, revise_side_effect, get_draft = _revision_stream(original)

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.get_draft_artifact", new=AsyncMock(side_effect=get_draft)),
        patch(
            "app.api.projects.revise_workflow_artefact",
            new=AsyncMock(side_effect=revise_side_effect),
        ),
    ):
        first = client.post(
            f"/projects/{PROJECT_ID}/drafts/{original.id}/blocks",
            json=_add_row_body(list_item_id, 1),
        )
        assert first.status_code == 200, first.text
        applied = state["draft"]
        replay = client.post(
            f"/projects/{PROJECT_ID}/drafts/{applied.id}/blocks",
            json=_add_row_body(list_item_id, applied.version),
        )

    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()


def test_replay_wins_over_a_stale_base_version(client: TestClient) -> None:
    original, list_item_id = _seeded_list_draft()
    state, revise_side_effect, get_draft = _revision_stream(original)

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.get_draft_artifact", new=AsyncMock(side_effect=get_draft)),
        patch(
            "app.api.projects.revise_workflow_artefact",
            new=AsyncMock(side_effect=revise_side_effect),
        ) as revise_artefact,
    ):
        first = client.post(
            f"/projects/{PROJECT_ID}/drafts/{original.id}/blocks",
            json=_add_row_body(list_item_id, 1),
        )
        assert first.status_code == 200, first.text
        applied = state["draft"]
        # The retry still carries the pre-apply base version. Without
        # idempotency this 409s, and the client's rebase double-applies.
        replay = client.post(
            f"/projects/{PROJECT_ID}/drafts/{applied.id}/blocks",
            json=_add_row_body(list_item_id, 1),
        )

    assert replay.status_code == 200, replay.text
    assert replay.json()["delta"] == first.json()["delta"]
    assert revise_artefact.await_count == 1


def test_unknown_client_operation_id_still_applies(client: TestClient) -> None:
    original, list_item_id = _seeded_list_draft()
    state, revise_side_effect, get_draft = _revision_stream(original)

    with (
        patch("app.api.projects.get_project", new=AsyncMock(return_value=_project())),
        patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
        patch("app.api.projects.get_draft_artifact", new=AsyncMock(side_effect=get_draft)),
        patch(
            "app.api.projects.revise_workflow_artefact",
            new=AsyncMock(side_effect=revise_side_effect),
        ) as revise_artefact,
    ):
        first = client.post(
            f"/projects/{PROJECT_ID}/drafts/{original.id}/blocks",
            json=_add_row_body(list_item_id, 1),
        )
        assert first.status_code == 200, first.text
        applied = state["draft"]
        second = client.post(
            f"/projects/{PROJECT_ID}/drafts/{applied.id}/blocks",
            json={
                **_add_row_body(list_item_id, applied.version),
                "client_operation_id": "d3c2b1a0-9f8e-4d7c-8b6a-5f4e3d2c1b0a",
            },
        )

    assert second.status_code == 200, second.text
    assert revise_artefact.await_count == 2
    assert state["draft"].content_markdown.count("- Added item") == 2
