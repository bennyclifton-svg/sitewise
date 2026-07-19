import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app.config import settings
from app.database.draft_artifact import DraftArtifact
from app.mcp_bridge.tokens import mint_turn_token
from tests.conftest import run_async

SECRET = "test-secret"
USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
OTHER_PROJECT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
NOW = datetime(2026, 7, 4, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _settings(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)
    monkeypatch.setattr(settings, "agent_workspace_root", tmp_path)


class _Session:
    def __init__(self, *, project: Any) -> None:
        self.project = project
        self.commit = AsyncMock()

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, model: type, item_id: uuid.UUID) -> Any:
        if item_id == self.project.id:
            return self.project
        return None


def _project() -> SimpleNamespace:
    return SimpleNamespace(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        workspace_path="04-projects/demo",
    )


def _draft(*, version: int, content: str) -> DraftArtifact:
    return DraftArtifact(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        workflow_type="create_pmp",
        version=version,
        status="draft",
        title="Project Management Plan",
        workspace_path="04-projects/demo/00-brief-pmp/PMP.md",
        author_user_id=USER_ID,
        content_markdown=content,
        model="gpt-4.1-mini",
        runtime="clerk-sitewise-create-pmp",
        provenance_metadata={"source": "test"},
        created_at=NOW,
        updated_at=NOW,
    )


def _install(
    monkeypatch,
    session: _Session,
    *,
    token_project: uuid.UUID = PROJECT_ID,
):
    from app.mcp_bridge import server

    token = mint_turn_token(user_id=USER_ID, project_id=token_project, secret=SECRET)
    monkeypatch.setattr(
        server,
        "get_http_headers",
        lambda **_kwargs: {"authorization": f"Bearer {token}"},
    )
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    monkeypatch.setattr(
        server,
        "authorize_project_mutation_with_claims",
        server.authorize_project_access_with_claims,
    )
    monkeypatch.setattr(
        server,
        "get_latest_draft_artifact_by_workspace_path",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(server, "get_workspace_file_by_path", AsyncMock(return_value=None))
    return server


def _call(server, tool: str, arguments: dict) -> Any:
    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool(tool, arguments)

    return run_async(_run())


def test_authorized_scratch_write_read_and_list(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session)

    write = _call(
        server,
        "write_workspace_file",
        {
            "project_id": str(PROJECT_ID),
            "path": "notes/hello.md",
            "content": "# Hello",
        },
    )
    read = _call(
        server,
        "read_workspace_file",
        {"project_id": str(PROJECT_ID), "path": "notes/hello.md"},
    )
    listing = _call(
        server,
        "list_workspace",
        {"project_id": str(PROJECT_ID), "path": "notes"},
    )

    assert write.data["kind"] == "scratch"
    assert write.data["bytes_written"] == 7
    assert read.data["content"] == "# Hello"
    assert read.data["kind"] == "scratch"
    assert listing.data == [
        {
            "name": "hello.md",
            "path": "notes/hello.md",
            "kind": "file",
            "size_bytes": 7,
        }
    ]


def test_workspace_tools_reject_traversal(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session)

    with pytest.raises(ToolError, match="workspace path"):
        _call(
            server,
            "read_workspace_file",
            {"project_id": str(PROJECT_ID), "path": "../secret.txt"},
        )


def test_workspace_tools_reject_cross_project_token(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session, token_project=OTHER_PROJECT_ID)

    with pytest.raises(ToolError, match="scoped"):
        _call(
            server,
            "write_workspace_file",
            {
                "project_id": str(PROJECT_ID),
                "path": "notes/hello.md",
                "content": "# Hello",
            },
        )


def test_read_workspace_file_returns_latest_draft_artifact(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session)
    latest = _draft(version=2, content="# Edited in app")
    monkeypatch.setattr(
        server,
        "get_latest_draft_artifact_by_workspace_path",
        AsyncMock(return_value=latest),
    )

    result = _call(
        server,
        "read_workspace_file",
        {"project_id": str(PROJECT_ID), "path": latest.workspace_path},
    )

    assert result.data["kind"] == "artefact"
    assert result.data["draftId"] == str(latest.id)
    assert result.data["version"] == 2
    assert result.data["content"] == "# Edited in app"


def test_write_workspace_file_versions_existing_draft_artifact(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session)
    existing = _draft(version=1, content="# Original")
    updated = _draft(version=2, content="# Edited by agent")
    monkeypatch.setattr(
        server,
        "get_latest_draft_artifact_by_workspace_path",
        AsyncMock(return_value=existing),
    )
    revise_artefact = AsyncMock(return_value=updated)
    monkeypatch.setattr(server, "revise_workflow_artefact", revise_artefact)

    result = _call(
        server,
        "write_workspace_file",
        {
            "project_id": str(PROJECT_ID),
            "path": existing.workspace_path,
            "content": "# Edited by agent",
        },
    )

    assert result.data["kind"] == "artefact"
    assert result.data["draftId"] == str(updated.id)
    assert result.data["version"] == 2
    revise_artefact.assert_awaited_once()
    assert revise_artefact.await_args.kwargs["draft"] is existing
    assert revise_artefact.await_args.kwargs["expected_base_version"] == 1
    assert revise_artefact.await_args.kwargs["content_markdown"] == "# Edited by agent"
    session.commit.assert_awaited_once()


def test_write_workspace_file_rejects_source_document_paths(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session)
    monkeypatch.setattr(
        server,
        "get_workspace_file_by_path",
        AsyncMock(return_value=SimpleNamespace(workspace_path="04-projects/demo/source.pdf")),
    )

    with pytest.raises(ToolError, match="read-only"):
        _call(
            server,
            "write_workspace_file",
            {
                "project_id": str(PROJECT_ID),
                "path": "04-projects/demo/source.pdf",
                "content": "changed",
            },
        )

