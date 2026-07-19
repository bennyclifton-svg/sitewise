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


@pytest.fixture(autouse=True)
def _token_secret(monkeypatch):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)


class _ScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        return self._values


class _ExecuteResult:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._values)


class _Session:
    def __init__(self, *, project: Any, workspace_files: list[Any]) -> None:
        self.project = project
        self.workspace_files = workspace_files

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, model: type, item_id: uuid.UUID) -> Any:
        if item_id == self.project.id:
            return self.project
        return None

    async def execute(self, statement: Any) -> _ExecuteResult:
        return _ExecuteResult(self.workspace_files)


def _project(project_id: uuid.UUID = PROJECT_ID) -> SimpleNamespace:
    return SimpleNamespace(id=project_id, owner_user_id=USER_ID)


def _workspace_file(path: str, *, size_bytes: int = 10) -> SimpleNamespace:
    return SimpleNamespace(
        workspace_path=path,
        filename=path.rsplit("/", 1)[-1],
        size_bytes=size_bytes,
        content_hash="hash-" + path,
        source_document_id=None,
    )


def _install(monkeypatch, session: _Session, *, token_project: uuid.UUID = PROJECT_ID):
    from app.mcp_bridge import server

    token = mint_turn_token(user_id=USER_ID, project_id=token_project, secret=SECRET)
    monkeypatch.setattr(
        server,
        "get_http_headers",
        lambda **_kwargs: {"authorization": f"Bearer {token}"},
    )
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    return server


def _call(server, project_id: uuid.UUID = PROJECT_ID) -> Any:
    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool(
                "find_candidate_tender_documents", {"project_id": str(project_id)}
            )

    return run_async(_run())


def test_find_candidate_tender_documents_returns_candidate_tender_pdfs(monkeypatch) -> None:
    session = _Session(
        project=_project(),
        workspace_files=[
            _workspace_file("site/photo.jpg"),
            _workspace_file("quotes/nexus-tender.pdf", size_bytes=100),
            _workspace_file("quotes/kaposi quote.pdf", size_bytes=200),
            _workspace_file("admin/minutes.pdf", size_bytes=300),
        ],
    )
    server = _install(monkeypatch, session)

    result = _call(server)

    documents = result.data
    assert [item["workspace_path"] for item in documents] == [
        "quotes/nexus-tender.pdf",
        "quotes/kaposi quote.pdf",
        "admin/minutes.pdf",
    ]
    assert documents[0]["selection_source"] == "candidate_workspace_files"
    assert documents[0]["candidate_reasons"] == ["tender", "quote"]
    assert documents[0]["size_bytes"] == 100


def test_find_candidate_tender_documents_rejects_cross_project_token(monkeypatch) -> None:
    session = _Session(project=_project(), workspace_files=[])
    server = _install(monkeypatch, session, token_project=OTHER_PROJECT_ID)

    with pytest.raises(ToolError, match="scoped"):
        _call(server)
