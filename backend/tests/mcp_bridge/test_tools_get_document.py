import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app.config import settings
from app.mcp_bridge.tokens import mint_turn_token
from tests.conftest import run_async

SECRET = "test-secret"
USER_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()
DOCUMENT_ID = uuid.uuid4()
OTHER_PROJECT_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)
    monkeypatch.setattr(settings, "whole_document_content_chars", 80)


class _ExecuteResult:
    def __init__(self, value: Any) -> None:
        self.value = value

    def scalar_one_or_none(self) -> Any:
        return self.value


class _Session:
    def __init__(self, *, project: Any, source_document: Any = None) -> None:
        self.project = project
        self.source_document = source_document

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, model: type, item_id: uuid.UUID) -> Any:
        if item_id == self.project.id:
            return self.project
        return None

    async def execute(self, statement: Any) -> _ExecuteResult:
        return _ExecuteResult(self.source_document)


def _project(project_id: uuid.UUID = PROJECT_ID) -> SimpleNamespace:
    return SimpleNamespace(
        id=project_id,
        owner_user_id=USER_ID,
        slug="test-project",
    )


def _source_document(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=DOCUMENT_ID,
        filename="Specification.docx",
        relative_path="04-projects/test-project/_inbox/Specification.docx",
        project="test-project",
        phase="procurement",
        source_type="project_evidence",
        document_class="specification",
        document_metadata={"filename": "Specification.docx"},
        normalized_content=content,
    )


def _install(
    monkeypatch,
    session: _Session,
    *,
    token_project: uuid.UUID = PROJECT_ID,
    workspace_file: Any = None,
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
        "get_workspace_file_by_path",
        AsyncMock(return_value=workspace_file),
    )
    return server


def _call(server, arguments: dict) -> Any:
    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool("get_document", arguments)

    return run_async(_run())


def test_get_document_reads_ingested_text_by_document_id(monkeypatch) -> None:
    content = "Caesarstone reconstituted stone benchtops with pencil-round edge."
    session = _Session(project=_project(), source_document=_source_document(content))
    server = _install(monkeypatch, session)

    result = _call(
        server,
        {
            "project_id": str(PROJECT_ID),
            "document_id": str(DOCUMENT_ID),
            "max_chars": 32,
        },
    )

    assert result.data["kind"] == "source_document"
    assert result.data["document_id"] == str(DOCUMENT_ID)
    assert result.data["relative_path"] == "04-projects/test-project/_inbox/Specification.docx"
    assert result.data["content"] == content[:32]
    assert result.data["content_truncated"] is True


def test_get_document_reads_ingested_text_by_workspace_path(monkeypatch) -> None:
    content = "Laundry, bathroom and ensuite benchtops are Caesarstone."
    session = _Session(project=_project(), source_document=_source_document(content))
    workspace_file = SimpleNamespace(
        source_document_id=DOCUMENT_ID,
        ingest_status="ingested",
    )
    server = _install(monkeypatch, session, workspace_file=workspace_file)

    result = _call(
        server,
        {
            "project_id": str(PROJECT_ID),
            "workspace_path": "04-projects/test-project/_inbox/Specification.docx",
        },
    )

    assert result.data["content"] == content
    assert result.data["content_truncated"] is False


def test_get_document_reports_when_ingested_text_is_not_available(monkeypatch) -> None:
    session = _Session(project=_project(), source_document=None)
    workspace_file = SimpleNamespace(
        source_document_id=None,
        ingest_status="pending",
    )
    server = _install(monkeypatch, session, workspace_file=workspace_file)

    with pytest.raises(ToolError, match="ingest_status=pending"):
        _call(
            server,
            {
                "project_id": str(PROJECT_ID),
                "workspace_path": "04-projects/test-project/_inbox/Specification.docx",
            },
        )


def test_get_document_rejects_cross_project_token(monkeypatch) -> None:
    content = "Caesarstone reconstituted stone benchtops."
    session = _Session(project=_project(), source_document=_source_document(content))
    server = _install(monkeypatch, session, token_project=OTHER_PROJECT_ID)

    with pytest.raises(ToolError, match="scoped"):
        _call(
            server,
            {"project_id": str(PROJECT_ID), "document_id": str(DOCUMENT_ID)},
        )
