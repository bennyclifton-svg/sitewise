import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app.config import settings
from app.mcp_bridge.tokens import mint_turn_token
from tender.models import TenderComparison, TenderDocument, TenderJob, TenderQuote
from tests.conftest import run_async

SECRET = "test-secret"
USER_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()


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

    def scalar_one_or_none(self) -> Any | None:
        return self._values[0] if self._values else None


class _Session:
    """Stub async session recording adds/jobs; workspace lookups pop execute_values."""

    def __init__(self, *, project: Any = None, workspace_files: dict[str, Any] | None = None) -> None:
        self.project = project
        self.workspace_files = workspace_files or {}
        self.added: list[Any] = []
        self.committed = False

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, model: type, item_id: uuid.UUID) -> Any:
        if self.project is not None and item_id == self.project.id:
            return self.project
        return None

    async def execute(self, statement: Any) -> _ExecuteResult:
        # Only workspace-file lookups reach execute; match on the bound
        # workspace_path parameter.
        params = statement.compile().params
        path = params.get("workspace_path_1")
        record = self.workspace_files.get(path)
        return _ExecuteResult([record] if record is not None else [])

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    async def refresh(self, obj: Any) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    @property
    def jobs(self) -> list[TenderJob]:
        return [obj for obj in self.added if isinstance(obj, TenderJob)]


def _project() -> SimpleNamespace:
    return SimpleNamespace(id=PROJECT_ID, owner_user_id=USER_ID)


def _workspace_record(path: str) -> SimpleNamespace:
    return SimpleNamespace(
        storage_key=f"storage/{path}",
        filename=path.rsplit("/", 1)[-1],
        content_hash="hash-" + path,
    )


def _install(monkeypatch, session: _Session, *, token_project: uuid.UUID = PROJECT_ID):
    from app.mcp_bridge import server

    monkeypatch.setattr(
        server,
        "authorize_project_mutation_with_claims",
        server.authorize_project_access_with_claims,
    )

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
            return await client.call_tool("start_tender_comparison", arguments)

    return run_async(_run())


def test_happy_path_creates_everything_and_enqueues_per_document(monkeypatch):
    session = _Session(
        project=_project(),
        workspace_files={
            "quotes/nexus.pdf": _workspace_record("quotes/nexus.pdf"),
            "quotes/nexus-annexure.pdf": _workspace_record("quotes/nexus-annexure.pdf"),
            "quotes/kaposi.pdf": _workspace_record("quotes/kaposi.pdf"),
        },
    )
    server = _install(monkeypatch, session)

    result = _call(
        server,
        {
            "project_id": str(PROJECT_ID),
            "context": {"trade": "structural"},
            "quotes": [
                {
                    "builder_name": "NexusBuilt",
                    "workspace_paths": ["quotes/nexus.pdf", "quotes/nexus-annexure.pdf"],
                },
                {"builder_name": "Kaposi", "workspace_paths": ["quotes/kaposi.pdf"]},
            ],
        },
    )

    data = result.data
    comparisons = [o for o in session.added if isinstance(o, TenderComparison)]
    quotes = [o for o in session.added if isinstance(o, TenderQuote)]
    documents = [o for o in session.added if isinstance(o, TenderDocument)]
    assert len(comparisons) == 1
    assert comparisons[0].context == {"trade": "structural"}
    assert comparisons[0].created_by == USER_ID
    assert len(quotes) == 2
    assert len(documents) == 3
    assert data["comparison_id"] == str(comparisons[0].id)
    assert len(data["quotes"]) == 2

    jobs = session.jobs
    assert len(jobs) == 3
    assert all(job.kind == "ingest_document" for job in jobs)
    job_document_ids = {job.payload["document_id"] for job in jobs}
    assert job_document_ids == {str(d.id) for d in documents}
    assert session.committed


def test_unauthorized_project_persists_nothing(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session, token_project=uuid.uuid4())

    with pytest.raises(ToolError, match="scoped"):
        _call(
            server,
            {
                "project_id": str(PROJECT_ID),
                "context": {},
                "quotes": [
                    {"builder_name": "NexusBuilt", "workspace_paths": ["quotes/a.pdf"]}
                ],
            },
        )

    assert session.added == []
    assert not session.committed


def test_unknown_workspace_path_fails_that_quote_only(monkeypatch):
    session = _Session(
        project=_project(),
        workspace_files={"quotes/kaposi.pdf": _workspace_record("quotes/kaposi.pdf")},
    )
    server = _install(monkeypatch, session)

    result = _call(
        server,
        {
            "project_id": str(PROJECT_ID),
            "context": {},
            "quotes": [
                {"builder_name": "NexusBuilt", "workspace_paths": ["quotes/missing.pdf"]},
                {"builder_name": "Kaposi", "workspace_paths": ["quotes/kaposi.pdf"]},
            ],
        },
    )

    data = result.data
    assert len(data["quotes"]) == 2
    nexus, kaposi = data["quotes"]
    assert nexus["builder_name"] == "NexusBuilt"
    assert "error" in nexus and nexus["error"]
    assert kaposi["builder_name"] == "Kaposi"
    assert "error" not in kaposi or not kaposi["error"]

    quotes = [o for o in session.added if isinstance(o, TenderQuote)]
    documents = [o for o in session.added if isinstance(o, TenderDocument)]
    assert len(quotes) == 2  # both quotes exist; only the document failed
    assert len(documents) == 1
    assert len(session.jobs) == 1
    assert session.committed
