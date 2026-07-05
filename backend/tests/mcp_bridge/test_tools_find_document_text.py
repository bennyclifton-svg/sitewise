import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app.config import settings
from app.mcp_bridge.tokens import mint_turn_token
from tests.conftest import run_async

SECRET = "test-secret"
USER_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()
OTHER_PROJECT_ID = uuid.uuid4()
DOCUMENT_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)


class _ScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def all(self) -> list[Any]:
        return self.values


class _ExecuteResult:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self.values)


class _Session:
    def __init__(self, *, project: Any, source_documents: list[Any]) -> None:
        self.project = project
        self.source_documents = source_documents

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, model: type, item_id: uuid.UUID) -> Any:
        if item_id == self.project.id:
            return self.project
        return None

    async def execute(self, statement: Any) -> _ExecuteResult:
        return _ExecuteResult(self.source_documents)


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
        document_class="specification",
        normalized_content=content,
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
    return server


def _call(server, arguments: dict) -> Any:
    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool("find_document_text", arguments)

    return run_async(_run())


def test_find_document_text_returns_keyword_snippets(monkeypatch) -> None:
    content = (
        "Kitchen and butler's pantry benchtops are Caesarstone reconstituted stone. "
        "Kitchen island waterfall ends are reconstituted stone.\n\n"
        "Laundry, bathroom and ensuite benchtops are Caesarstone 20mm reconstituted stone."
    )
    session = _Session(
        project=_project(),
        source_documents=[_source_document(content)],
    )
    server = _install(monkeypatch, session)

    result = _call(
        server,
        {
            "project_id": str(PROJECT_ID),
            "query": "what are the benchtops made from?",
            "filename_hint": "Specification",
            "context_chars": 80,
        },
    )

    assert result.data[0]["document_id"] == str(DOCUMENT_ID)
    assert result.data[0]["filename"] == "Specification.docx"
    excerpts = [snippet["excerpt"] for snippet in result.data[0]["snippets"]]
    assert any("Caesarstone reconstituted stone" in excerpt for excerpt in excerpts)
    assert any("Laundry, bathroom and ensuite" in excerpt for excerpt in excerpts)


def test_find_document_text_rejects_empty_search_terms(monkeypatch) -> None:
    session = _Session(project=_project(), source_documents=[])
    server = _install(monkeypatch, session)

    with pytest.raises(ToolError, match="searchable term"):
        _call(server, {"project_id": str(PROJECT_ID), "query": "what is the"})


def test_find_document_text_rejects_cross_project_token(monkeypatch) -> None:
    session = _Session(project=_project(), source_documents=[])
    server = _install(monkeypatch, session, token_project=OTHER_PROJECT_ID)

    with pytest.raises(ToolError, match="scoped"):
        _call(server, {"project_id": str(PROJECT_ID), "query": "benchtops"})
