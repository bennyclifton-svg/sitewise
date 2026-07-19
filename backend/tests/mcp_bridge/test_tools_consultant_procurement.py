import asyncio
import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app.agent.status_bus import agent_turn_status_bus
from app.config import settings
from app.mcp_bridge.tokens import mint_turn_token
from tests.conftest import run_async

SECRET = "test-secret"
USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
OTHER_PROJECT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
DRAFT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
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


def _project(project_id: uuid.UUID = PROJECT_ID) -> SimpleNamespace:
    return SimpleNamespace(
        id=project_id,
        owner_user_id=USER_ID,
        slug="demo",
        title="Walsh Renovation",
        workspace_path="04-projects/walsh-renovation",
    )


def _draft() -> SimpleNamespace:
    return SimpleNamespace(
        id=DRAFT_ID,
        project_id=PROJECT_ID,
        workflow_type="consultant_procurement_structural_engineer",
        version=1,
        title="Request for Fee Proposal - Structural engineer",
        workspace_path=(
            "04-projects/walsh-renovation/02-consultant/"
            "consultant_procurement_structural_engineer_v01.draft.md"
        ),
    )


def _source_trace() -> dict[str, Any]:
    return {
        "project_documents": [
            {
                "document_id": str(uuid.uuid4()),
                "filename": "project-brief.pdf",
                "relative_path": "04-projects/walsh-renovation/00-brief/project-brief.pdf",
                "role": "project_brief",
            }
        ],
        "platform_knowledge": [
            {
                "path": "seed/consultant-procurement.md",
                "title": "Consultant procurement guide",
                "section": "scope",
            }
        ],
        "forecast": {"used": True, "forecast_budget": 16_500},
        "assumptions": [],
        "missing_inputs": [],
        "tools": [],
    }


def _install(
    monkeypatch,
    session: _Session,
    *,
    token_project: uuid.UUID = PROJECT_ID,
    turn_id: uuid.UUID | None = None,
) -> tuple[Any, AsyncMock]:
    from app.mcp_bridge import server

    monkeypatch.setattr(server, "read_project_snapshot", AsyncMock(return_value=object()))
    monkeypatch.setattr(server, "capability_block_message", lambda *_args: None)

    monkeypatch.setattr(
        server,
        "authorize_project_mutation_with_claims",
        server.authorize_project_access_with_claims,
    )

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
    run_workflow = AsyncMock(
        return_value=SimpleNamespace(
            draft=_draft(),
            discipline="Structural engineer",
            source_trace=_source_trace(),
        )
    )
    monkeypatch.setattr(server, "run_consultant_procurement_artifact", run_workflow)
    return server, run_workflow


def _call(server, arguments: dict) -> Any:
    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool(
                "draft_consultant_procurement_artifact",
                arguments,
            )

    return run_async(_run())


def test_draft_consultant_procurement_tool_returns_artefact_metadata(monkeypatch) -> None:
    session = _Session(project=_project())
    server, run_workflow = _install(monkeypatch, session)

    result = _call(
        server,
        {
            "project_id": str(PROJECT_ID),
            "discipline": "structural engineer",
            "max_pages": 1,
            "instructions": "Ask for hourly rates.",
        },
    )

    assert result.data["kind"] == "artefact"
    assert result.data["title"] == "Request for Fee Proposal - Structural engineer"
    assert result.data["draftId"] == str(DRAFT_ID)
    assert result.data["workflowType"] == "consultant_procurement_structural_engineer"
    assert result.data["workspace_path"].endswith(
        "/consultant_procurement_structural_engineer_v01.draft.md"
    )
    assert result.data["source_trace"]["forecast"]["used"] is True
    run_workflow.assert_awaited_once()
    assert run_workflow.await_args.kwargs["project"] is session.project
    assert run_workflow.await_args.kwargs["user_id"] == USER_ID
    assert run_workflow.await_args.kwargs["discipline"] == "structural engineer"


def test_draft_consultant_procurement_rejects_unauthorized_project(monkeypatch) -> None:
    session = _Session(project=_project())
    server, run_workflow = _install(
        monkeypatch,
        session,
        token_project=OTHER_PROJECT_ID,
    )

    with pytest.raises(ToolError, match="scoped"):
        _call(
            server,
            {
                "project_id": str(PROJECT_ID),
                "discipline": "structural engineer",
            },
        )

    run_workflow.assert_not_awaited()


def test_draft_consultant_procurement_publishes_status_and_artefact(monkeypatch) -> None:
    turn_id = uuid.uuid4()
    session = _Session(project=_project())
    server, _run_workflow = _install(monkeypatch, session, turn_id=turn_id)

    async def _run():
        async with agent_turn_status_bus.subscribe(str(turn_id)) as statuses:
            async with Client(server.mcp) as client:
                result = await client.call_tool(
                    "draft_consultant_procurement_artifact",
                    {
                        "project_id": str(PROJECT_ID),
                        "discipline": "structural engineer",
                    },
                )
            running = await asyncio.wait_for(anext(statuses), timeout=0.1)
            done = await asyncio.wait_for(anext(statuses), timeout=0.1)
            artefact = await asyncio.wait_for(anext(statuses), timeout=0.1)
            return result, running, done, artefact

    result, running, done, artefact = run_async(_run())

    assert result.data["kind"] == "artefact"
    assert running["tool"] == "draft_consultant_procurement_artifact"
    assert running["state"] == "running"
    assert done["state"] == "done"
    assert done["document_count"] == 1
    assert done["knowledge_count"] == 1
    assert done["forecast_used"] is True
    assert done["source_documents"][0]["relative_path"].endswith("project-brief.pdf")
    assert done["platform_knowledge"][0]["path"] == "seed/consultant-procurement.md"
    assert artefact["kind"] == "artefact"
    assert artefact["draftId"] == str(DRAFT_ID)
    assert artefact["workflowType"] == "consultant_procurement_structural_engineer"
