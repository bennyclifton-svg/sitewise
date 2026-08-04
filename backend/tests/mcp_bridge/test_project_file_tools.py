import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app.config import settings
from app.cost_plan.schemas import (
    CostPlanMutationResult,
    CostPlanState,
    DependencySnapshot,
)
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
    def __init__(self, *, project: Any, turn: Any | None = None) -> None:
        self.project = project
        self.turn = turn
        self.commit = AsyncMock()

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, model: type, item_id: uuid.UUID, **_kwargs: Any) -> Any:
        if item_id == self.project.id:
            return self.project
        if self.turn is not None and item_id == self.turn.id:
            return self.turn
        return None


def _project(project_id: uuid.UUID = PROJECT_ID) -> SimpleNamespace:
    return SimpleNamespace(
        id=project_id,
        owner_user_id=USER_ID,
        workspace_path="04-projects/walsh-reno",
        title="Walsh Reno",
        work_type="extend",
    )


def _workspace_file(
    *,
    workspace_path: str,
    filename: str,
    ingest_status: str = "generated",
    source_document_id: uuid.UUID | None = None,
    source_document: Any | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        workspace_path=workspace_path,
        filename=filename,
        size_bytes=1234,
        ingest_status=ingest_status,
        source_document_id=source_document_id,
        storage_key=f"{PROJECT_ID}/{workspace_path}",
        source_document=source_document,
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
    turn_id: uuid.UUID | None = None,
):
    from app.mcp_bridge import server

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


def test_list_project_files_hides_legacy_cost_plan_markdown(monkeypatch) -> None:
    session = _Session(project=_project())
    installed_server = _install(monkeypatch, session)
    workbook = _workspace_file(
        workspace_path="04-projects/walsh-reno/01-cost/Cost_Plan_v10.draft.xlsx",
        filename="Cost_Plan_v10.draft.xlsx",
    )
    markdown = _workspace_file(
        workspace_path="04-projects/walsh-reno/01-cost/cost_plan_v10.md",
        filename="cost_plan_v10.md",
    )
    monkeypatch.setattr(
        installed_server,
        "search_workspace_files_for_project",
        AsyncMock(return_value=[markdown, workbook]),
    )

    result = _call(
        installed_server,
        "list_project_files",
        {"project_id": str(PROJECT_ID)},
    )

    assert [item["filename"] for item in result.data] == ["Cost_Plan_v10.draft.xlsx"]


def test_list_project_files_includes_ingested_document_identity(monkeypatch) -> None:
    session = _Session(project=_project())
    server = _install(monkeypatch, session)
    source_id = uuid.uuid4()
    drawing = _workspace_file(
        workspace_path="04-projects/walsh-reno/03-design/hydraulic/HY-SK-01.pdf",
        filename="HY-SK-01.pdf",
        ingest_status="ingested",
        source_document_id=source_id,
        source_document=SimpleNamespace(
            document_metadata={
                "document_number": "HY-SK-01",
                "title": "HYDRAULICS SERVICES SPATIALS",
                "revision": "P1",
                "discipline": "Hydraulic",
                "metadata_confidence": "high",
            }
        ),
    )
    monkeypatch.setattr(
        server, "search_workspace_files_for_project", AsyncMock(return_value=[drawing])
    )

    result = _call(server, "list_project_files", {"project_id": str(PROJECT_ID)})

    assert result.data[0]["document_metadata"] == {
        "document_number": "HY-SK-01",
        "title": "HYDRAULICS SERVICES SPATIALS",
        "revision": "P1",
        "discipline": "Hydraulic",
        "metadata_confidence": "high",
    }


def test_pi_runtime_allows_project_file_tools() -> None:
    from app.agent.pi_process import PI_MCP_DIRECT_TOOLS

    assert "list_project_files" in PI_MCP_DIRECT_TOOLS
    assert "read_project_workbook" in PI_MCP_DIRECT_TOOLS
    assert "read_workspace_file" in PI_MCP_DIRECT_TOOLS
    assert "forecast_consultant_fees" in PI_MCP_DIRECT_TOOLS
    assert "apply_consultant_fee_forecast" in PI_MCP_DIRECT_TOOLS
    assert "apply_cost_plan_budget_forecast" in PI_MCP_DIRECT_TOOLS
    assert "get_cost_plan" in PI_MCP_DIRECT_TOOLS
    assert "upsert_cost_item" in PI_MCP_DIRECT_TOOLS
    assert "draft_consultant_procurement_artifact" in PI_MCP_DIRECT_TOOLS
    assert "list_document_register" in PI_MCP_DIRECT_TOOLS
    assert "select_document_register_files" in PI_MCP_DIRECT_TOOLS
    assert "start_transmittal" in PI_MCP_DIRECT_TOOLS


def test_list_document_register_supports_keyword_and_numeric_filters(monkeypatch) -> None:
    from app.projects.document_register import DocumentRegisterRow

    session = _Session(project=_project())
    installed_server = _install(monkeypatch, session)
    basement = DocumentRegisterRow(
        id=uuid.uuid4(),
        workspace_file_id=uuid.uuid4(),
        source_document_id=uuid.uuid4(),
        workspace_path="04-projects/walsh-reno/03-design/A250.pdf",
        filename="A250.pdf",
        document_number="250",
        title="Basement floor plan",
        revision="C02",
        category="Architectural",
    )
    roof = DocumentRegisterRow(
        id=uuid.uuid4(),
        workspace_file_id=uuid.uuid4(),
        workspace_path="04-projects/walsh-reno/_inbox/roof.pdf",
        filename="roof.pdf",
        title="Roof plan",
    )
    monkeypatch.setattr(
        installed_server,
        "list_document_register_rows",
        AsyncMock(return_value=[basement, roof]),
    )

    result = _call(
        installed_server,
        "list_document_register",
        {
            "project_id": str(PROJECT_ID),
            "query": "Basement",
            "query_field": "title",
        },
    )

    assert [item["id"] for item in result.data] == [str(basement.id)]
    assert result.data[0]["document_number"] == "250"

    numeric_result = _call(
        installed_server,
        "list_document_register",
        {
            "project_id": str(PROJECT_ID),
            "document_number_greater_than": 200,
        },
    )

    assert [item["id"] for item in numeric_result.data] == [str(basement.id)]


def test_select_document_register_files_updates_turn_and_publishes_ui_event(
    monkeypatch,
) -> None:
    from app.agent.document_context import SelectedTurnDocument
    from app.projects.document_register import DocumentRegisterRow

    turn_id = uuid.uuid4()
    turn = SimpleNamespace(
        id=turn_id,
        project_id=PROJECT_ID,
        user_id=USER_ID,
        state="active",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        input_context={
            "selected_documents": [],
            "unrelated": "preserved",
        },
    )
    session = _Session(project=_project(), turn=turn)
    installed_server = _install(monkeypatch, session, turn_id=turn_id)
    source_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    row = DocumentRegisterRow(
        id=source_id,
        workspace_file_id=workspace_id,
        source_document_id=source_id,
        workspace_path="04-projects/walsh-reno/03-design/A250.pdf",
        filename="A250.pdf",
        document_number="250",
        title="Basement floor plan",
        revision="C02",
        category="Architectural",
    )
    selected = SelectedTurnDocument(
        workspace_file_id=workspace_id,
        source_document_id=source_id,
        workspace_path=row.workspace_path,
        filename=row.filename,
        content_hash="a" * 64,
        size_bytes=1234,
        document_number=row.document_number,
        title=row.title,
        revision=row.revision,
        category=row.category,
    )
    monkeypatch.setattr(
        installed_server,
        "list_document_register_rows",
        AsyncMock(return_value=[row]),
    )
    resolve = AsyncMock(return_value=[selected])
    monkeypatch.setattr(installed_server, "resolve_selected_turn_documents", resolve)
    publish = AsyncMock()
    monkeypatch.setattr(installed_server.agent_turn_status_bus, "publish", publish)

    result = _call(
        installed_server,
        "select_document_register_files",
        {
            "project_id": str(PROJECT_ID),
            "document_ids": [str(source_id)],
            "action": "replace",
        },
    )

    assert result.data["selected_count"] == 1
    assert turn.input_context["unrelated"] == "preserved"
    assert turn.input_context["selected_documents"][0]["source_document_id"] == str(
        source_id
    )
    resolve.assert_awaited_once_with(
        session,
        project_id=PROJECT_ID,
        document_ids=[source_id],
    )
    session.commit.assert_awaited_once()
    publish.assert_awaited_once_with(
        str(turn_id),
        kind="document_selection",
        message="Selected 1 document",
        projectId=str(PROJECT_ID),
        action="replace",
        requestedAction="replace",
        documentIds=[str(source_id)],
    )


def test_pi_runtime_allows_project_profile_tools() -> None:
    from app.agent.pi_process import PI_MCP_DIRECT_TOOLS

    assert "get_project_profile" in PI_MCP_DIRECT_TOOLS
    assert "get_project_profile_options" in PI_MCP_DIRECT_TOOLS
    assert "get_project_snapshot" in PI_MCP_DIRECT_TOOLS
    assert "propose_project_profile_change" in PI_MCP_DIRECT_TOOLS
    assert "accept_project_profile_proposal" in PI_MCP_DIRECT_TOOLS
    assert "reject_project_profile_proposal" in PI_MCP_DIRECT_TOOLS
    assert "update_project_profile" in PI_MCP_DIRECT_TOOLS


def test_read_project_workbook_returns_sheet_rows(monkeypatch) -> None:
    session = _Session(project=_project())
    server = _install(monkeypatch, session)
    workbook = _workspace_file(
        workspace_path="04-projects/walsh-reno/01-cost/Cost_Plan_v01.draft.xlsx",
        filename="Cost_Plan_v01.draft.xlsx",
    )
    monkeypatch.setattr(
        server, "get_workspace_file_by_path", AsyncMock(return_value=workbook)
    )
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
    monkeypatch.setattr(
        server, "get_latest_draft_artifact", AsyncMock(return_value=draft)
    )

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
    monkeypatch.setattr(
        server, "get_latest_draft_artifact", AsyncMock(return_value=source)
    )
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


def test_upsert_cost_item_publishes_its_workbook_revision(monkeypatch) -> None:
    session = _Session(project=_project())
    server = _install(monkeypatch, session)
    updated = _draft(version=10, content="# typed Cost Plan v10")
    dependencies = DependencySnapshot(
        profile_revision=2,
        evidence_fingerprint="current-evidence",
        decision_set_revision=3,
        runtime_version="cost-plan-tool-test",
    )
    state = CostPlanState(
        project_id=PROJECT_ID,
        artefact_revision_id=updated.id,
        version=10,
        dependency_snapshot=dependencies,
        items=[],
    )
    persist = AsyncMock(
        return_value=CostPlanMutationResult(
            state=state,
            changed_item_keys=["kitchen-engineered-stone"],
        )
    )
    sync_artifacts = AsyncMock(
        return_value={
            "file_name": "Cost_Plan_v10.draft.xlsx",
            "workspace_path": "04-projects/walsh-reno/01-cost/Cost_Plan_v10.draft.xlsx",
            "version": 10,
        }
    )
    monkeypatch.setattr(
        server,
        "read_project_snapshot",
        AsyncMock(return_value=SimpleNamespace()),
    )
    monkeypatch.setattr(server, "persist_cost_item", persist)
    monkeypatch.setattr(server, "get_draft_artifact", AsyncMock(return_value=updated))
    monkeypatch.setattr(server, "sync_cost_plan_revision_artifacts", sync_artifacts)

    result = _call(
        server,
        "upsert_cost_item",
        {
            "project_id": str(PROJECT_ID),
            "expected_base_version": 9,
            "item": {
                "item_key": "kitchen-engineered-stone",
                "cost_code": "14-010",
                "category": "Construction",
                "item": "Kitchen — including engineered stone benchtops",
                "budget": "33000",
                "forecast": "33000",
                "allowance_type": "pc",
                "basis": "User-adopted planning allowance",
            },
        },
    )

    assert result.data["workbook"] == {
        "file_name": "Cost_Plan_v10.draft.xlsx",
        "workspace_path": "04-projects/walsh-reno/01-cost/Cost_Plan_v10.draft.xlsx",
        "version": 10,
    }
    sync_artifacts.assert_awaited_once_with(
        session,
        project=session.project,
        draft=updated,
        typed_state=state,
    )
    session.commit.assert_awaited_once()


def test_apply_cost_plan_budget_forecast_refreshes_all_rows_and_workbook(
    monkeypatch,
) -> None:
    from tests.sitewise.test_cost_plan_budget_forecast import GREENBANK_COST_PLAN

    session = _Session(project=_project())
    server = _install(monkeypatch, session)
    source = _draft(version=1, content=GREENBANK_COST_PLAN)
    updated = _draft(version=2, content="# typed Cost Plan v2")
    dependencies = DependencySnapshot(
        profile_revision=2,
        evidence_fingerprint="current-evidence",
        decision_set_revision=3,
        runtime_version="adopted-budget-test",
    )
    base_state = CostPlanState(
        project_id=PROJECT_ID,
        artefact_revision_id=source.id,
        version=1,
        dependency_snapshot=dependencies,
        items=[],
    )

    async def persist_refresh(_session, **kwargs):
        state = CostPlanState(
            project_id=PROJECT_ID,
            artefact_revision_id=updated.id,
            version=2,
            dependency_snapshot=dependencies,
            assumptions=kwargs["assumptions"],
            items=kwargs["proposed_items"],
        )
        return CostPlanMutationResult(
            state=state,
            changed_item_keys=[item.item_key for item in kwargs["proposed_items"]],
        )

    persist = AsyncMock(side_effect=persist_refresh)
    sync_artifacts = AsyncMock(
        return_value={
            "file_name": "Cost_Plan_v02.draft.xlsx",
            "workspace_path": "04-projects/walsh-reno/01-cost/Cost_Plan_v02.draft.xlsx",
            "version": 2,
            "row_count": 25,
        }
    )
    monkeypatch.setattr(
        server, "get_latest_draft_artifact", AsyncMock(return_value=source)
    )
    monkeypatch.setattr(
        server, "read_typed_cost_plan", AsyncMock(return_value=base_state)
    )
    monkeypatch.setattr(
        server,
        "read_project_snapshot",
        AsyncMock(
            return_value=SimpleNamespace(profile=SimpleNamespace(work_type="extend"))
        ),
    )
    monkeypatch.setattr(
        server, "cost_dependency_snapshot", lambda *_args, **_kwargs: dependencies
    )
    monkeypatch.setattr(server, "persist_cost_refresh", persist)
    monkeypatch.setattr(server, "get_draft_artifact", AsyncMock(return_value=updated))
    monkeypatch.setattr(server, "sync_cost_plan_revision_artifacts", sync_artifacts)

    result = _call(
        server,
        "apply_cost_plan_budget_forecast",
        {
            "project_id": str(PROJECT_ID),
            "construction_budget_ex_gst": "300000",
        },
    )

    assert result.data["kind"] == "cost_plan_budget_forecast_applied"
    assert result.data["version"] == 2
    assert result.data["forecast"]["row_count"] == 25
    assert result.data["forecast"]["construction_envelope_total"] == "300000.00"
    assert result.data["forecast"]["total_excluding_gst"] == "399500.00"
    assert len(persist.await_args.kwargs["proposed_items"]) == 25
    assert persist.await_args.kwargs["expected_base_version"] == 1
    assert persist.await_args.kwargs["contingency_percent"] == Decimal("0")
    sync_artifacts.assert_awaited_once()
    sync_kwargs = sync_artifacts.await_args.kwargs
    assert sync_kwargs["project"] == session.project
    assert sync_kwargs["draft"] == updated
    assert sync_kwargs["markdown"] == updated.content_markdown
    assert sync_kwargs["typed_state"].version == 2
    assert (
        sync_kwargs["provenance_updates"]["adopted_budget_forecast"]["row_count"] == 25
    )
