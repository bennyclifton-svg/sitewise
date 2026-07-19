import asyncio
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app.agent.status_bus import agent_turn_status_bus
from app.config import settings
from app.mcp_bridge.tokens import mint_turn_token
from app.sitewise.knowledge_catalog import LoadedKnowledge
from tests.conftest import run_async

SECRET = "test-secret"
USER_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()

DOCTRINE = "docs/clerk-brief.md"
CONTRACT_ADMIN = "seed/contract-administration-guide.md"
RENOVATION = "seed/renovation-guide.md"


@pytest.fixture(autouse=True)
def _token_secret(monkeypatch):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)


class _Session:
    def __init__(self, *, project: Any = None) -> None:
        self.project = project

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, model: type, item_id: uuid.UUID) -> Any:
        if self.project is not None and item_id == self.project.id:
            return self.project
        return None


def _project(**overrides: Any) -> SimpleNamespace:
    fields = {
        "id": PROJECT_ID,
        "owner_user_id": USER_ID,
        "slug": "test-project",
        "archetype": "new-dwelling",
        "building_class": None,
        "work_type": None,
        "user_role": "builder",
        "state": "NSW",
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _install(
    monkeypatch,
    session: _Session,
    *,
    token_project: uuid.UUID = PROJECT_ID,
    turn_id: uuid.UUID | None = None,
):
    from app.mcp_bridge import server

    token = mint_turn_token(
        user_id=USER_ID,
        project_id=token_project,
        turn_id=turn_id,
        secret=SECRET,
    )
    monkeypatch.setattr(
        server,
        "get_http_headers",
        lambda **_kwargs: {"authorization": f"Bearer {token}"},
    )
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    return server


def _call(server, tool: str, arguments: dict) -> Any:
    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool(tool, arguments)

    return run_async(_run())


def _stub_catalog(monkeypatch, server, entries: list[dict]):
    calls: list[dict] = []

    async def _catalog(session, **kwargs):
        calls.append(kwargs)
        return entries

    monkeypatch.setattr(server, "catalog_platform_knowledge", _catalog)
    return calls


class _StubRetriever:
    instances: list["_StubRetriever"] = []
    passages: list[Any] = []

    def __init__(self, session: Any) -> None:
        self.session = session
        self.calls: list[dict] = []
        _StubRetriever.instances.append(self)

    async def retrieve(self, query: str, **kwargs: Any) -> list[Any]:
        self.calls.append({"query": query, **kwargs})
        return self.passages


def _passage(
    *,
    path: str,
    content: str = "Contract administration guidance.",
    source_type: str | None = "reference",
    metadata: dict | None = None,
    section: str | None = "Contract families",
    score: float = 0.1,
) -> SimpleNamespace:
    return SimpleNamespace(
        relative_path=path,
        filename=path.rsplit("/", maxsplit=1)[-1],
        page_or_section=section,
        content=content,
        score=score,
        source_type=source_type,
        document_metadata=metadata or {"knowledge_scope": "platform"},
    )


def test_gate_blocks_listing_when_overlays_missing(monkeypatch):
    session = _Session(project=_project(archetype=None, state=None))
    server = _install(monkeypatch, session)
    catalog_calls = _stub_catalog(monkeypatch, server, entries=[{"path": "x"}])

    result = _call(server, "list_platform_knowledge", {"project_id": str(PROJECT_ID)})

    data = result.data
    assert data["gate"]["ready"] is False
    assert {issue["field"] for issue in data["gate"]["issues"]} == {
        "building_class",
        "work_type",
        "state",
    }
    assert data["required"] == {}
    assert data["available"] == []
    assert "blocked" in data["message"]
    assert catalog_calls == []


def test_listing_returns_required_paths_and_catalog(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session)
    entries = [
        {
            "path": "seed/new-dwelling-guide.md",
            "title": "Archetype seed — New dwelling",
            "tier": "archetype",
            "topics": [],
            "summary": "New dwelling coverage.",
            "sections": ["scope-of-this-archetype"],
            "related_doctrine_sections": ["§evidence-discipline"],
            "ingested": True,
        }
    ]
    catalog_calls = _stub_catalog(monkeypatch, server, entries=entries)

    result = _call(
        server,
        "list_platform_knowledge",
        {"project_id": str(PROJECT_ID), "topics": ["cost"]},
    )

    data = result.data
    assert data["gate"]["ready"] is True
    assert data["required"]["create-pmp"][0] == DOCTRINE
    assert data["required"]["create-pmp"][1] == "seed/new-dwelling-guide.md"
    assert data["required"]["create-pmp"][2] == "seed/role-builder.md"
    assert (
        "skills/reference/nsw-residential-cost-breakdown-reference.md"
        in data["required"]["create-cost-plan"]
    )
    assert data["available"] == entries
    (call,) = catalog_calls
    assert call == {
        "archetype": "new-dwelling",
        "user_role": "builder",
        "building_class": None,
        "work_type": None,
        "topics": ["cost"],
    }


def test_listing_for_taxonomy_only_project_does_not_crash(monkeypatch):
    # Regression: a project set up via Class + Work type with no legacy
    # archetype used to raise ValueError in select_required_paths (legacy
    # branch keyed on archetype: None). It must now resolve via the taxonomy.
    session = _Session(
        project=_project(
            archetype=None,
            building_class="residential",
            work_type="refurb",
        )
    )
    server = _install(monkeypatch, session)
    catalog_calls = _stub_catalog(monkeypatch, server, entries=[])

    result = _call(server, "list_platform_knowledge", {"project_id": str(PROJECT_ID)})

    data = result.data
    assert data["gate"]["ready"] is True
    assert data["required"]["create-pmp"][0] == DOCTRINE
    assert data["required"]["create-pmp"]  # non-empty, resolved via taxonomy
    (call,) = catalog_calls
    assert call["building_class"] == "residential"
    assert call["work_type"] == "refurb"


def test_read_returns_content_and_publishes_consulted_path(monkeypatch):
    turn_id = uuid.uuid4()
    session = _Session(project=_project())
    server = _install(monkeypatch, session, turn_id=turn_id)

    loaded = LoadedKnowledge(
        passage=SimpleNamespace(content="## 01-cost\nCost doctrine."),
        missing_sections=[],
        available_sections=["01-cost", "02-consultant"],
    )

    async def _load(session, path, section_ids, *, max_chars):
        assert path == DOCTRINE
        assert section_ids == ["01-cost"]
        assert max_chars == settings.whole_document_content_chars
        return loaded

    monkeypatch.setattr(server, "load_platform_sections", _load)

    async def _run():
        async with agent_turn_status_bus.subscribe(str(turn_id)) as statuses:
            async with Client(server.mcp) as client:
                result = await client.call_tool(
                    "read_platform_knowledge",
                    {
                        "project_id": str(PROJECT_ID),
                        "path": DOCTRINE,
                        "section_ids": ["01-cost"],
                    },
                )
            running = await asyncio.wait_for(anext(statuses), timeout=0.1)
            done = await asyncio.wait_for(anext(statuses), timeout=0.1)
            return result, running, done

    result, running, done = run_async(_run())

    data = result.data
    assert data["content"] == "## 01-cost\nCost doctrine."
    assert data["available_sections"] == ["01-cost", "02-consultant"]
    assert running["state"] == "running"
    assert done["state"] == "done"
    assert done["knowledge_path"] == DOCTRINE
    assert done["section_ids"] == ["01-cost"]


def test_read_with_unknown_sections_returns_available_ids(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session)

    loaded = LoadedKnowledge(
        passage=None,
        missing_sections=["not-a-section"],
        available_sections=["01-cost"],
    )

    async def _load(session, path, section_ids, *, max_chars):
        return loaded

    monkeypatch.setattr(server, "load_platform_sections", _load)

    result = _call(
        server,
        "read_platform_knowledge",
        {
            "project_id": str(PROJECT_ID),
            "path": DOCTRINE,
            "section_ids": ["not-a-section"],
        },
    )

    data = result.data
    assert data["error"] == "unknown_sections"
    assert data["missing_sections"] == ["not-a-section"]
    assert data["available_sections"] == ["01-cost"]


def test_read_missing_document_raises_tool_error(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session)

    async def _load(session, path, section_ids, *, max_chars):
        return None

    monkeypatch.setattr(server, "load_platform_sections", _load)

    with pytest.raises(ToolError, match="list_platform_knowledge"):
        _call(
            server,
            "read_platform_knowledge",
            {"project_id": str(PROJECT_ID), "path": "seed/nope.md"},
        )


def test_read_rejects_inapplicable_platform_path(monkeypatch):
    session = _Session(project=_project(archetype="new-dwelling"))
    server = _install(monkeypatch, session)
    load_calls = []

    async def _load(session, path, section_ids, *, max_chars):
        load_calls.append(path)
        return None

    monkeypatch.setattr(server, "load_platform_sections", _load)

    with pytest.raises(ToolError, match="not available"):
        _call(
            server,
            "read_platform_knowledge",
            {"project_id": str(PROJECT_ID), "path": RENOVATION},
        )

    assert load_calls == []


def test_search_platform_knowledge_returns_only_applicable_platform_rows(monkeypatch):
    session = _Session(project=_project(archetype="new-dwelling"))
    server = _install(monkeypatch, session)
    _StubRetriever.instances = []
    _StubRetriever.passages = [
        _passage(path=CONTRACT_ADMIN, score=0.1),
        _passage(path=RENOVATION, content="Renovation-only guidance.", score=0.9),
        _passage(
            path="04-projects/test-project/_inbox/contract.pdf",
            content="Project evidence must not leak.",
            source_type="project_evidence",
            metadata={},
            score=1.0,
        ),
    ]
    monkeypatch.setattr(server, "DocumentRetriever", _StubRetriever)

    result = _call(
        server,
        "search_platform_knowledge",
        {"project_id": str(PROJECT_ID), "query": "contract notices"},
    )

    data = result.data
    assert [item["path"] for item in data] == [CONTRACT_ADMIN]
    assert data[0]["source_type"] == "reference"
    assert data[0]["mandatory"] is True
    assert data[0]["mandatory_for"] == ["create-pmp"]
    assert "contract-admin" in data[0]["topics"]
    (retriever,) = _StubRetriever.instances
    (call,) = retriever.calls
    assert call["query"] == "contract notices"
    assert call["filters"].platform_knowledge_only is True
    assert call["filters"].phase == "reference"


def test_search_platform_knowledge_requires_overlay_gate(monkeypatch):
    session = _Session(project=_project(archetype=None, state=None))
    server = _install(monkeypatch, session)
    _StubRetriever.instances = []
    monkeypatch.setattr(server, "DocumentRetriever", _StubRetriever)

    with pytest.raises(ToolError, match="blocked"):
        _call(
            server,
            "search_platform_knowledge",
            {"project_id": str(PROJECT_ID), "query": "contract notices"},
        )

    assert _StubRetriever.instances == []


def test_unauthorized_access_rejected_for_both_tools(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session, token_project=uuid.uuid4())

    with pytest.raises(ToolError, match="scoped"):
        _call(server, "list_platform_knowledge", {"project_id": str(PROJECT_ID)})
    with pytest.raises(ToolError, match="scoped"):
        _call(
            server,
            "search_platform_knowledge",
            {"project_id": str(PROJECT_ID), "query": "contract notices"},
        )
    with pytest.raises(ToolError, match="scoped"):
        _call(
            server,
            "read_platform_knowledge",
            {"project_id": str(PROJECT_ID), "path": DOCTRINE},
        )
