import asyncio
import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client

from app.agent.status_bus import agent_turn_status_bus
from app.config import settings
from app.mcp_bridge.tokens import mint_turn_token
from tender.models import TenderJob
from tests.conftest import run_async

SECRET = "test-secret"
USER_ID = uuid.uuid4()
PROJECT_ID = uuid.uuid4()
COMPARISON_ID = uuid.uuid4()
TURN_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def _token_secret(monkeypatch):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)


class _Session:
    def __init__(self, *, project: Any) -> None:
        self.project = project

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, model: type, item_id: uuid.UUID) -> Any:
        if item_id == self.project.id:
            return self.project
        return None


def _project() -> SimpleNamespace:
    return SimpleNamespace(id=PROJECT_ID, owner_user_id=USER_ID)


def _comparison() -> SimpleNamespace:
    quote_id = uuid.uuid4()
    return SimpleNamespace(
        id=COMPARISON_ID,
        project_id=PROJECT_ID,
        status="processing",
        quotes=[
            SimpleNamespace(
                id=quote_id,
                builder_name="NexusBuilt",
                stage="map_items",
                documents=[
                    SimpleNamespace(
                        id=uuid.uuid4(),
                        original_filename="nexus-tender.pdf",
                        mime_type="application/pdf",
                        doc_type="quote",
                        ingest_status="ingested",
                        page_count=12,
                    )
                ],
            )
        ],
    )


def _job(status: str) -> TenderJob:
    return TenderJob(
        id=uuid.uuid4(),
        kind="map_items",
        status=status,
        attempts=0,
    )


def _install(monkeypatch, *, turn_id: uuid.UUID | None = None):
    from app.mcp_bridge import server

    session = _Session(project=_project())
    token = mint_turn_token(
        user_id=USER_ID,
        project_id=PROJECT_ID,
        turn_id=turn_id,
        secret=SECRET,
    )
    monkeypatch.setattr(
        server,
        "get_http_headers",
        lambda **_kwargs: {"authorization": f"Bearer {token}"},
    )
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    monkeypatch.setattr(
        server,
        "get_comparison_detail",
        AsyncMock(return_value=_comparison()),
    )
    return server


def test_get_comparison_status_returns_progress_jobs_and_report(monkeypatch) -> None:
    server = _install(monkeypatch)
    monkeypatch.setattr(
        server,
        "_comparison_jobs",
        AsyncMock(return_value=[_job("queued"), _job("running")]),
    )
    monkeypatch.setattr(server, "_pending_review_count", AsyncMock(return_value=2))
    monkeypatch.setattr(
        server,
        "_latest_report_payload",
        AsyncMock(return_value={"draftId": str(uuid.uuid4()), "title": "Report"}),
    )

    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool(
                "get_comparison_status", {"comparison_id": str(COMPARISON_ID)}
            )

    result = run_async(_run())
    data = result.data

    assert data["comparison_id"] == str(COMPARISON_ID)
    assert data["progress"]["stage"] == "qa"
    assert data["jobs"]["counts"] == {"queued": 1, "running": 1}
    assert data["qa"]["pending_count"] == 2
    assert data["quotes"][0]["documents"][0]["filename"] == "nexus-tender.pdf"


def test_get_comparison_result_publishes_report_artefact(monkeypatch) -> None:
    server = _install(monkeypatch, turn_id=TURN_ID)
    draft_id = uuid.uuid4()
    report_payload = {
        "comparison_id": str(COMPARISON_ID),
        "draftId": str(draft_id),
        "workflowType": "tender_report",
        "title": "Tender comparison report v01",
    }
    monkeypatch.setattr(
        server,
        "_comparison_status_payload",
        AsyncMock(
            return_value={
                "comparison_id": str(COMPARISON_ID),
                "project_id": str(PROJECT_ID),
                "status": "report_draft",
                "report": report_payload,
            }
        ),
    )
    monkeypatch.setattr(
        server.matrix,
        "build_matrix",
        AsyncMock(return_value=SimpleNamespace(model_dump=lambda mode: {"groups": []})),
    )
    monkeypatch.setattr(server, "_analysis_payload", AsyncMock(return_value=None))

    async def _run():
        async with agent_turn_status_bus.subscribe(str(TURN_ID)) as stream:
            async with Client(server.mcp) as client:
                result = await client.call_tool(
                    "get_comparison_result",
                    {"comparison_id": str(COMPARISON_ID)},
                )
            events = [
                await asyncio.wait_for(anext(stream), timeout=1),
                await asyncio.wait_for(anext(stream), timeout=1),
                await asyncio.wait_for(anext(stream), timeout=1),
            ]
        return result, events

    result, events = run_async(_run())

    assert result.data["report"]["draftId"] == str(draft_id)
    artefact_events = [event for event in events if event.get("kind") == "artefact"]
    assert artefact_events == [
        {
            "message": "Tender comparison report v01",
            "kind": "artefact",
            "title": "Tender comparison report v01",
            "workflowType": "tender_report",
            "draftId": str(draft_id),
            "comparisonId": str(COMPARISON_ID),
            "projectId": str(PROJECT_ID),
        }
    ]
