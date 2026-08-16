from __future__ import annotations

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
from app.web_research import WebSearchResult, WebSource
from tests.conftest import run_async

SECRET = "test-secret"
USER_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()
OTHER_PROJECT_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)
    monkeypatch.setattr(settings, "agent_web_research_enabled", True)


class _Session:
    def __init__(self) -> None:
        self.project = SimpleNamespace(
            id=PROJECT_ID,
            owner_user_id=USER_ID,
            slug="newtown-extension",
        )
        self.added: list[object] = []

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, _model: type, item_id: uuid.UUID) -> Any:
        return self.project if item_id == PROJECT_ID else None

    async def execute(self, _stmt):
        return SimpleNamespace(scalar_one_or_none=lambda: None)

    def add(self, obj) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None


class _WebResearch:
    async def search(self, query: str, *, jurisdiction: str | None, max_results: int):
        assert query == "Planning Act 2016 development approval"
        assert jurisdiction == "QLD"
        assert max_results == 6
        return [
            WebSearchResult(
                url="https://www.legislation.qld.gov.au/view/html/inforce/current/act-2016-025",
                title="Planning Act 2016",
                snippet="Current Queensland legislation.",
                publisher="Queensland Government",
                jurisdiction="QLD",
                authority_class="official_legislation",
                source_type="web_legislation",
            )
        ]

    async def read(self, url: str, *, section_hint: str | None = None) -> WebSource:
        assert url == "https://www.legislation.qld.gov.au/view/html/inforce/current/act-2016-025"
        assert section_hint == "section 8"
        return WebSource(
            url=url,
            title="Planning Act 2016",
            publisher="Queensland Government",
            jurisdiction="QLD",
            authority_class="official_legislation",
            source_type="web_legislation",
            version_status="current",
            effective_date="29 November 2024",
            section="section 8",
            excerpt="A planning instrument sets out policies for planning.",
            content_hash="a" * 64,
            retrieved_at="2026-08-08T10:00:00+00:00",
        )


def _install(monkeypatch, *, token_project: uuid.UUID = PROJECT_ID, turn_id=None):
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
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: _Session())
    monkeypatch.setattr(server, "get_web_research_service", lambda: _WebResearch())
    return server


def _call(server, tool: str, arguments: dict) -> Any:
    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool(tool, arguments)

    return run_async(_run())


def test_search_web_returns_official_results_and_publishes_status(monkeypatch) -> None:
    turn_id = uuid.uuid4()
    server = _install(monkeypatch, turn_id=turn_id)

    async def _run():
        async with agent_turn_status_bus.subscribe(str(turn_id)) as statuses:
            async with Client(server.mcp) as client:
                result = await client.call_tool(
                    "search_web",
                    {
                        "project_id": str(PROJECT_ID),
                        "query": "Planning Act 2016 development approval",
                        "jurisdiction": "QLD",
                    },
                )
            running = await asyncio.wait_for(anext(statuses), timeout=0.1)
            done = await asyncio.wait_for(anext(statuses), timeout=0.1)
            return result, running, done

    result, running, done = run_async(_run())

    assert result.data[0]["title"] == "Planning Act 2016"
    assert result.data[0]["source_type"] == "web_legislation"
    assert running["tool"] == "search_web"
    assert running["state"] == "running"
    assert done["state"] == "done"
    assert done["result_count"] == 1
    assert done["query"] == "Planning Act 2016 development approval"


def test_read_web_source_returns_text_and_publishes_persistable_provenance(
    monkeypatch,
) -> None:
    turn_id = uuid.uuid4()
    server = _install(monkeypatch, turn_id=turn_id)
    url = "https://www.legislation.qld.gov.au/view/html/inforce/current/act-2016-025"

    async def _run():
        async with agent_turn_status_bus.subscribe(str(turn_id)) as statuses:
            async with Client(server.mcp) as client:
                result = await client.call_tool(
                    "read_web_source",
                    {
                        "project_id": str(PROJECT_ID),
                        "url": url,
                        "section_hint": "section 8",
                    },
                )
            running = await asyncio.wait_for(anext(statuses), timeout=0.1)
            done = await asyncio.wait_for(anext(statuses), timeout=0.1)
            return result, running, done

    result, running, done = run_async(_run())

    assert result.data["excerpt"].startswith("A planning instrument")
    assert result.data["version_status"] == "current"
    assert running["tool"] == "read_web_source"
    assert done["state"] == "done"
    assert done["web_source"]["url"] == url
    assert done["web_source"]["authority_class"] == "official_legislation"


def test_attach_official_instrument_from_nsw_instrument_id(monkeypatch) -> None:
    class _Research(_WebResearch):
        async def read(self, url: str, *, section_hint: str | None = None) -> WebSource:
            assert url.endswith("/act-1979-203")
            return WebSource(
                url=url,
                title="Environmental Planning and Assessment Act 1979",
                publisher="NSW Government",
                jurisdiction="NSW",
                authority_class="official_legislation",
                source_type="web_legislation",
                version_status="current",
                effective_date="1 July 2026",
                section=section_hint,
                excerpt="A consent authority is to take into consideration the relevant matters.",
                content_hash="a" * 64,
                retrieved_at="2026-08-16T00:00:00+00:00",
            )

    server = _install(monkeypatch)
    monkeypatch.setattr(server, "get_web_research_service", lambda: _Research())

    result = _call(
        server,
        "attach_official_instrument",
        {
            "project_id": str(PROJECT_ID),
            "instrument_id": "act-1979-203",
        },
    )

    assert result.data["title"] == "Environmental Planning and Assessment Act 1979"
    assert result.data["document_id"]
    assert result.data["relative_path"] == "official/act-1979-203"
    assert result.data["knowledge_scope"] == "official"


def test_attach_official_instrument_from_council_pdf_url(monkeypatch) -> None:
    pdf_url = "https://www.innerwest.nsw.gov.au/ArticleDocuments/123/DCP-2022.pdf"

    class _Research(_WebResearch):
        async def read(self, url: str, *, section_hint: str | None = None) -> WebSource:
            assert url == pdf_url
            return WebSource(
                url=url,
                title="Inner West DCP 2022",
                publisher="NSW Government",
                jurisdiction="NSW",
                authority_class="official_planning",
                source_type="web_planning",
                version_status="current",
                effective_date=None,
                section=section_hint,
                excerpt="Heritage conservation area controls for alterations and additions.",
                content_hash="d" * 64,
                retrieved_at="2026-08-16T00:00:00+00:00",
            )

    server = _install(monkeypatch)
    monkeypatch.setattr(server, "get_web_research_service", lambda: _Research())

    result = _call(
        server,
        "attach_official_instrument",
        {"project_id": str(PROJECT_ID), "url": pdf_url},
    )

    assert result.data["title"] == "Inner West DCP 2022"
    assert result.data["relative_path"] == "official/dcp-2022.pdf"
    assert result.data["knowledge_scope"] == "official"


def test_attach_official_instrument_from_uploaded_document(monkeypatch) -> None:
    document_id = uuid.uuid4()
    document = SimpleNamespace(
        id=document_id,
        project_id=PROJECT_ID,
        source_type="project_evidence",
        document_class="unknown",
        document_type="unknown",
        ingest_mode="full_text",
        filename="Inner West DCP 2022.pdf",
        relative_path="04-projects/newtown/_inbox/Inner West DCP 2022.pdf",
        normalized_content="Heritage conservation area controls.",
        content_hash="e" * 64,
        document_metadata={},
    )
    server = _install(monkeypatch)
    session = server.get_session_factory()()
    session.existing_document = document

    async def execute(_stmt):
        return SimpleNamespace(scalar_one_or_none=lambda: document)

    session.execute = execute
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)

    result = _call(
        server,
        "attach_official_instrument",
        {
            "project_id": str(PROJECT_ID),
            "document_id": str(document_id),
        },
    )

    assert document.source_type == "reference"
    assert document.document_class == "planning_instrument"
    assert document.document_metadata["knowledge_scope"] == "official"
    assert result.data["document_id"] == str(document_id)
    assert result.data["title"] == "Inner West DCP 2022.pdf"


def test_attach_official_instrument_rejects_non_gov_url(monkeypatch) -> None:
    server = _install(monkeypatch)

    with pytest.raises(ToolError, match="official"):
        _call(
            server,
            "attach_official_instrument",
            {
                "project_id": str(PROJECT_ID),
                "url": "https://example.com/planning-act.pdf",
            },
        )


def test_web_research_rejects_a_token_bound_to_another_project(monkeypatch) -> None:
    server = _install(monkeypatch, token_project=OTHER_PROJECT_ID)

    with pytest.raises(ToolError, match="project"):
        _call(
            server,
            "search_web",
            {
                "project_id": str(PROJECT_ID),
                "query": "Planning Act 2016 development approval",
                "jurisdiction": "QLD",
            },
        )
