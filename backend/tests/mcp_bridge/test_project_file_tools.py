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
USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
OTHER_PROJECT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)


class _Session:
    def __init__(self, *, project: Any) -> None:
        self.project = project
        self.commit = AsyncMock()

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
        workspace_path="04-projects/walsh-reno",
    )


def _workspace_file(
    *,
    workspace_path: str,
    filename: str,
    ingest_status: str = "generated",
    source_document_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        workspace_path=workspace_path,
        filename=filename,
        size_bytes=1234,
        ingest_status=ingest_status,
        source_document_id=source_document_id,
        storage_key=f"{PROJECT_ID}/{workspace_path}",
    )


def _draft(*, version: int, content: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        workflow_type="create_cost_plan",
        version=version,
        title="Cost Plan",
        workspace_path=f"04-projects/walsh-reno/01-cost/cost_plan_v{version:02d}.md",
        content_markdown=content,
        provenance_metadata={},
    )


def _cost_plan_markdown() -> str:
    return """# Cost plan

## Cost breakdown by category

| Cost Code | Category | Cost Items | Budget | Status | Basis |
| --- | --- | --- | --- | --- | --- |
| 1 | Fees and charges | Atelier North Pty Ltd architect / PM fee | $96,500 | Approved | Engagement letter |
| 6 | Consultants | Structural engineer | TBC | Assumption | Not yet appointed |
| 7 | Consultants | Geotechnical engineer | TBC | Assumption | Not yet appointed |
| 8 | Consultants | Surveyor | TBC | Assumption | Not yet appointed |
| 9 | Consultants | Hydraulic / wastewater | TBC | Assumption | Not yet appointed |
| 10 | Consultants | BASIX / energy assessor | TBC | Assumption | Not yet appointed |
| 11 | Consultants | Principal certifier | TBC | Assumption | Not yet appointed |
| 12 | Construction | Preliminaries | $920,000 | Assumption | Benchmark % of ceiling |
| | | **Subtotal - Fees and charges** | $96,500 | | |
| | | **Subtotal - Consultants** | TBC | | |
| | | **Subtotal - Construction** | $920,000 | | |
| | | **Grand total (ex GST)** | $1,016,500 | Assumption | Sum of itemised subtotals |
"""


def _install(
    monkeypatch,
    session: _Session,
    *,
    token_project: uuid.UUID = PROJECT_ID,
):
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


def _call(server, tool: str, arguments: dict) -> Any:
    async def _run():
        async with Client(server.mcp) as client:
            return await client.call_tool(tool, arguments)

    return run_async(_run())


def test_list_project_files_finds_generated_workbook(monkeypatch) -> None:
    session = _Session(project=_project())
    server = _install(monkeypatch, session)
    workbook = _workspace_file(
        workspace_path="04-projects/walsh-reno/01-cost/Cost_Plan_v01.draft.xlsx",
        filename="Cost_Plan_v01.draft.xlsx",
    )
    search = AsyncMock(return_value=[workbook])
    monkeypatch.setattr(
        server,
        "search_workspace_files_for_project",
        search,
    )

    result = _call(
        server,
        "list_project_files",
        {"project_id": str(PROJECT_ID), "query": "Cost_Plan_v01.draft.xlsx"},
    )

    assert result.data == [
        {
            "kind": "project_file",
            "workspace_path": "04-projects/walsh-reno/01-cost/Cost_Plan_v01.draft.xlsx",
            "filename": "Cost_Plan_v01.draft.xlsx",
            "size_bytes": 1234,
            "ingest_status": "generated",
            "source_document_id": None,
            "read_with": "read_project_workbook",
        }
    ]
    search.assert_awaited_once_with(
        session,
        project_id=PROJECT_ID,
        query="cost_plan_v01.draft.xlsx",
        path_prefix=None,
        limit=50,
    )


def test_pi_runtime_allows_project_file_tools() -> None:
    from app.agent.pi_process import PI_MCP_DIRECT_TOOLS

    assert "list_project_files" in PI_MCP_DIRECT_TOOLS
    assert "read_project_workbook" in PI_MCP_DIRECT_TOOLS
    assert "read_workspace_file" in PI_MCP_DIRECT_TOOLS
    assert "forecast_consultant_fees" in PI_MCP_DIRECT_TOOLS
    assert "apply_consultant_fee_forecast" in PI_MCP_DIRECT_TOOLS
    assert "draft_consultant_procurement_artifact" in PI_MCP_DIRECT_TOOLS


def test_read_project_workbook_returns_sheet_rows(monkeypatch) -> None:
    session = _Session(project=_project())
    server = _install(monkeypatch, session)
    workbook = _workspace_file(
        workspace_path="04-projects/walsh-reno/01-cost/Cost_Plan_v01.draft.xlsx",
        filename="Cost_Plan_v01.draft.xlsx",
    )
    monkeypatch.setattr(server, "get_workspace_file_by_path", AsyncMock(return_value=workbook))
    monkeypatch.setattr(server, "download_project_file", lambda *, storage_key: b"xlsx")
    monkeypatch.setattr(
        server,
        "workbook_preview_from_bytes",
        lambda content: SimpleNamespace(
            sheets=[
                SimpleNamespace(
                    name="Summary",
                    column_count=3,
                    rows=[
                        ["Cost Code", "Category", "Cost Items"],
                        ["1", "Fees and charges", "Atelier North architect / PM fee"],
                        ["2", "Fees and charges", "DA and CC authority fees"],
                    ],
                )
            ],
            warnings=[],
        ),
    )

    result = _call(
        server,
        "read_project_workbook",
        {
            "project_id": str(PROJECT_ID),
            "path": "04-projects/walsh-reno/01-cost/Cost_Plan_v01.draft.xlsx",
            "max_rows": 2,
        },
    )

    assert result.data["kind"] == "workbook_preview"
    assert result.data["artifact_role"] == "generated_artifact"
    assert result.data["sheets"] == [
        {
            "name": "Summary",
            "column_count": 3,
            "row_count": 3,
            "rows_truncated": True,
            "rows": [
                ["Cost Code", "Category", "Cost Items"],
                ["1", "Fees and charges", "Atelier North architect / PM fee"],
            ],
        }
    ]


def test_read_project_workbook_rejects_cross_project_token(monkeypatch) -> None:
    session = _Session(project=_project())
    server = _install(monkeypatch, session, token_project=OTHER_PROJECT_ID)

    with pytest.raises(ToolError, match="scoped"):
        _call(
            server,
            "read_project_workbook",
            {
                "project_id": str(PROJECT_ID),
                "path": "04-projects/walsh-reno/01-cost/Cost_Plan_v01.draft.xlsx",
            },
        )


def test_forecast_consultant_fees_returns_preview(monkeypatch) -> None:
    session = _Session(project=_project())
    server = _install(monkeypatch, session)
    draft = _draft(version=1, content=_cost_plan_markdown())
    monkeypatch.setattr(server, "get_latest_draft_artifact", AsyncMock(return_value=draft))

    result = _call(
        server,
        "forecast_consultant_fees",
        {"project_id": str(PROJECT_ID)},
    )

    assert result.data["kind"] == "consultant_fee_forecast"
    assert result.data["draft_id"] == str(draft.id)
    assert result.data["version"] == 1
    assert result.data["construction_base"] == 920_000
    assert result.data["missing_consultant_forecast_total"] == 47_000
    assert result.data["consultant_subtotal"] == 47_000
    assert "updated_markdown" not in result.data


def test_apply_consultant_fee_forecast_versions_draft_and_workbook(monkeypatch) -> None:
    session = _Session(project=_project())
    server = _install(monkeypatch, session)
    source = _draft(version=1, content=_cost_plan_markdown())
    updated = _draft(version=2, content="# updated")
    revise_artefact = AsyncMock(return_value=updated)
    sync_artifacts = AsyncMock(
        return_value={
            "file_name": "Cost_Plan_v02.draft.xlsx",
            "workspace_path": "04-projects/walsh-reno/01-cost/Cost_Plan_v02.draft.xlsx",
            "version": 2,
        }
    )
    monkeypatch.setattr(server, "get_latest_draft_artifact", AsyncMock(return_value=source))
    monkeypatch.setattr(server, "revise_workflow_artefact", revise_artefact)
    monkeypatch.setattr(server, "sync_cost_plan_revision_artifacts", sync_artifacts)

    result = _call(
        server,
        "apply_consultant_fee_forecast",
        {"project_id": str(PROJECT_ID)},
    )

    assert result.data["kind"] == "consultant_fee_forecast_applied"
    assert result.data["source_draft_id"] == str(source.id)
    assert result.data["draft_id"] == str(updated.id)
    assert result.data["workbook"]["file_name"] == "Cost_Plan_v02.draft.xlsx"
    content = revise_artefact.await_args.kwargs["content_markdown"]
    assert revise_artefact.await_args.kwargs["expected_base_version"] == 1
    assert "## Consultant fee forecast basis" in content
    assert "| 6 | Consultants | Structural engineer | $16,500 | Judgement |" in content
    sync_artifacts.assert_awaited_once()
    assert sync_artifacts.await_args.kwargs["markdown"] == content
    session.commit.assert_awaited_once()


def test_apply_consultant_fee_forecast_rejects_cross_project_token(monkeypatch) -> None:
    session = _Session(project=_project())
    server = _install(monkeypatch, session, token_project=OTHER_PROJECT_ID)

    with pytest.raises(ToolError, match="scoped"):
        _call(
            server,
            "apply_consultant_fee_forecast",
            {"project_id": str(PROJECT_ID)},
        )
