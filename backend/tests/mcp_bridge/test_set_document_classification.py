"""MCP set_document_classification is project-scoped (X1 Stage 5.8)."""

from __future__ import annotations

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
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)


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
        if self.source_document is not None and item_id == self.source_document.id:
            return self.source_document
        return None

    async def execute(self, _statement: Any) -> _ExecuteResult:
        return _ExecuteResult(self.source_document)

    def add(self, _obj: Any) -> None:
        return None

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None


def _project(project_id: uuid.UUID = PROJECT_ID) -> SimpleNamespace:
    return SimpleNamespace(
        id=project_id,
        owner_user_id=USER_ID,
        slug="test-project",
    )


def _source_document() -> SimpleNamespace:
    return SimpleNamespace(
        id=DOCUMENT_ID,
        project_id=PROJECT_ID,
        filename="Heritage Impact Statement.pdf",
        relative_path="04-projects/test-project/_inbox/Heritage Impact Statement.pdf",
        document_class="report",
        document_subject="heritage",
        document_metadata={"basis": "filename", "confidence": "0.85", "subject": "heritage"},
        content_hash="c" * 64,
        normalized_content="x" * 200,
    )


def _install(
    monkeypatch: pytest.MonkeyPatch,
    session: _Session,
    *,
    token_project: uuid.UUID = PROJECT_ID,
    service_result: Any = None,
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
        "set_document_classification_service",
        AsyncMock(return_value=service_result or _source_document()),
    )
    return server


def _call(server: Any, arguments: dict) -> Any:
    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool("set_document_classification", arguments)

    return run_async(_run())


def test_set_document_classification_rejects_cross_project_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _Session(project=_project(), source_document=_source_document())
    server = _install(monkeypatch, session, token_project=OTHER_PROJECT_ID)

    with pytest.raises(ToolError, match="scoped"):
        _call(
            server,
            {
                "project_id": str(PROJECT_ID),
                "document_id": str(DOCUMENT_ID),
                "document_class": "certificate",
            },
        )


def test_set_document_classification_calls_shared_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updated = _source_document()
    updated.document_class = "certificate"
    updated.document_metadata = {
        "basis": "user",
        "confidence": "1.0",
        "subject": "planning",
    }
    session = _Session(project=_project(), source_document=updated)
    server = _install(monkeypatch, session, service_result=updated)
    service = server.set_document_classification_service

    result = _call(
        server,
        {
            "project_id": str(PROJECT_ID),
            "document_id": str(DOCUMENT_ID),
            "document_class": "certificate",
            "document_subject": "planning",
            "reason": "That heritage report is actually a planning certificate.",
        },
    )

    service.assert_awaited()
    assert result.data["document_class"] == "certificate"
    assert result.data["basis"] == "user"
    assert result.data["confidence"] == "1.0"
