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


def test_gate_blocks_listing_when_overlays_missing(monkeypatch):
    session = _Session(project=_project(archetype=None, state=None))
    server = _install(monkeypatch, session)
    catalog_calls = _stub_catalog(monkeypatch, server, entries=[{"path": "x"}])

    result = _call(server, "list_platform_knowledge", {"project_id": str(PROJECT_ID)})

    data = result.data
    assert data["gate"]["ready"] is False
    assert {issue["field"] for issue in data["gate"]["issues"]} == {"archetype", "state"}
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
    assert call == {"archetype": "new-dwelling", "user_role": "builder", "topics": ["cost"]}


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

    with pytest.raises(ToolError, match="not in the corpus"):
        _call(
            server,
            "read_platform_knowledge",
            {"project_id": str(PROJECT_ID), "path": "seed/nope.md"},
        )


def test_unauthorized_access_rejected_for_both_tools(monkeypatch):
    session = _Session(project=_project())
    server = _install(monkeypatch, session, token_project=uuid.uuid4())

    with pytest.raises(ToolError, match="scoped"):
        _call(server, "list_platform_knowledge", {"project_id": str(PROJECT_ID)})
    with pytest.raises(ToolError, match="scoped"):
        _call(
            server,
            "read_platform_knowledge",
            {"project_id": str(PROJECT_ID), "path": DOCTRINE},
        )
