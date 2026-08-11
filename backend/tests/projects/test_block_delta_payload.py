"""F9: block mutation deltas are materially smaller than full draft state."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

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
NOW = datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)


def test_single_block_delta_is_materially_smaller_than_full_draft() -> None:
    paragraphs = "\n\n".join(f"Paragraph {index} with filler text." for index in range(40))
    generated = materialize_block_identity(
        f"## Scope\n\n{paragraphs}\n",
        actor_source="ai",
        now=NOW,
    )
    target = markdown_blocks(generated.markdown)[0]
    manifest = {
        "schema_version": 1,
        "artefact_type": "pmp",
        "context_version": 3,
        "source_version": "aaaaaaaaaaaaaaaa",
        "seed_version": "bbbbbbbbbbbbbbbb",
        "input_fingerprint": "d" * 64,
        "generation_brief": {"input_fingerprint": "d" * 64, "constraints": ["x"] * 20},
        "taxonomy": {"building_class": "commercial"},
        "known_profile": {f"field_{i}": i for i in range(30)},
        "unknown_relevant_fields": [f"u{i}" for i in range(20)],
        "explicitly_excluded_fields": ["scope.ffe"],
        "evidence_used": [f"doc-{i}.pdf" for i in range(20)],
        "seed_knowledge": [f"seed-{i}" for i in range(20)],
        "constraints": ["Keep allowances separate"],
    }
    original = DraftArtifact(
        id=DRAFT_ID,
        project_id=PROJECT_ID,
        workflow_type="create_pmp",
        version=1,
        status="draft",
        title="PMP",
        workspace_path="PMP.md",
        author_user_id=USER_ID,
        content_markdown=generated.markdown,
        model="gpt-5.6-luna",
        runtime="test",
        provenance_metadata={
            "generation_manifest": manifest,
            "blocks": generated.metadata,
        },
        created_at=NOW,
        updated_at=NOW,
    )

    async def revise_side_effect(*_args, **kwargs):
        return DraftArtifact(
            id=uuid.uuid4(),
            project_id=PROJECT_ID,
            workflow_type="create_pmp",
            version=2,
            status="draft",
            title="PMP",
            workspace_path="PMP.md",
            author_user_id=USER_ID,
            content_markdown=kwargs["content_markdown"],
            model="gpt-5.6-luna",
            runtime="test",
            provenance_metadata=dict(original.provenance_metadata or {}),
            created_at=NOW,
            updated_at=NOW,
        )

    mock_session = AsyncMock()
    current_user = CurrentUser(id=USER_ID, email="user@example.com")

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    try:
        with (
            TestClient(app) as client,
            patch(
                "app.api.projects.get_project",
                new=AsyncMock(
                    return_value=Project(
                        id=PROJECT_ID,
                        owner_user_id=USER_ID,
                        slug="demo",
                        title="Demo",
                        workspace_path="04-projects/demo",
                    )
                ),
            ),
            patch("app.api.projects.require_active_entitlement", new=AsyncMock()),
            patch(
                "app.api.projects.get_draft_artifact",
                new=AsyncMock(return_value=original),
            ),
            patch(
                "app.api.projects.revise_workflow_artefact",
                new=AsyncMock(side_effect=revise_side_effect),
            ),
        ):
            response = client.post(
                f"/projects/{PROJECT_ID}/drafts/{DRAFT_ID}/blocks",
                json={
                    "expected_base_version": 1,
                    "operations": [
                        {
                            "operation": "UPDATE",
                            "target": {"id": target.id, "type": "paragraph"},
                            "content": "Updated only one paragraph.",
                        }
                    ],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "draft" not in payload
    delta_size = len(json.dumps(payload["delta"], separators=(",", ":")))
    full_size = len(
        json.dumps(
            {
                "id": str(DRAFT_ID),
                "project_id": str(PROJECT_ID),
                "workflow_type": "create_pmp",
                "version": 2,
                "status": "draft",
                "title": "PMP",
                "workspace_path": "PMP.md",
                "author_user_id": str(USER_ID),
                "content_markdown": generated.markdown,
                "model": "gpt-5.6-luna",
                "runtime": "test",
                "provenance_metadata": original.provenance_metadata,
                "created_at": NOW.isoformat(),
                "updated_at": NOW.isoformat(),
            },
            separators=(",", ":"),
            default=str,
        )
    )
    assert delta_size * 3 < full_size
    assert payload["delta"]["generation_manifest_present"] is True
