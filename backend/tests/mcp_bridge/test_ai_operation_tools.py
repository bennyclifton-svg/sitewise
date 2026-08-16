"""F8 MCP authorization, isolation, schema and allowlist for AI operations."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app.config import settings
from app.database.project import Project
from app.mcp_bridge.auth import ToolAuthError
from app.mcp_bridge.tokens import mint_turn_token
from app.projects.artefact_revisions import ArtefactRevisionConflict
from tests.conftest import run_async

SECRET = "test-secret-for-f8-ai-operations-32b"
USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
OTHER_PROJECT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
DRAFT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
BLOCK_ID = "blk_" + ("a" * 32)


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setattr(settings, "agent_turn_token_secret", SECRET)


class _Session:
    def __init__(self, project: Project) -> None:
        self.project = project
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc_info):
        return None

    async def get(self, _model, item_id, **_kwargs):
        return self.project if item_id == self.project.id else None

    async def commit(self):
        self.committed = True

    async def flush(self):
        return None

    async def refresh(self, _obj):
        return None


def _project(project_id: uuid.UUID = PROJECT_ID) -> Project:
    return Project(
        id=project_id,
        owner_user_id=USER_ID,
        slug="demo",
        title="Demo",
        workspace_path="04-projects/demo",
        phase="brief-planning",
        project_metadata={},
    )


def _authorization(project: Project):
    return SimpleNamespace(
        project=project,
        claims=SimpleNamespace(user_id=USER_ID, turn_id=uuid.uuid4()),
    )


def _draft(*, project_id: uuid.UUID = PROJECT_ID, version: int = 1):
    return SimpleNamespace(
        id=DRAFT_ID,
        project_id=project_id,
        version=version,
        workflow_type="create_pmp",
        content_markdown=(
            f"## Scope\n\n<!-- clerk:block id={BLOCK_ID} -->\nExisting kitchen works.\n"
        ),
        provenance_metadata={
            "blocks": {
                BLOCK_ID: {
                    "id": BLOCK_ID,
                    "type": "paragraph",
                    "user_protected": False,
                    "baseline_content_hash": "abc",
                }
            }
        },
    )


def _install(monkeypatch, session: _Session, *, authorization=None):
    from app.mcp_bridge import server

    access = AsyncMock(return_value=authorization or _authorization(session.project))
    mutation = AsyncMock(return_value=authorization or _authorization(session.project))
    monkeypatch.setattr(server, "authorize_project_access_with_claims", access)
    monkeypatch.setattr(server, "authorize_project_mutation_with_claims", mutation)
    monkeypatch.setattr(server, "get_http_headers", lambda **_kwargs: {})
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)
    return server, access, mutation


def _call(server, name: str, arguments: dict) -> Any:
    async def run():
        async with Client(server.mcp) as client:
            return await client.call_tool(name, arguments)

    return run_async(run()).data


def test_direct_tools_allowlist_includes_ai_operation_surface() -> None:
    from app.agent.pi_process import PI_MCP_DIRECT_TOOLS

    for name in (
        "apply_artefact_operations",
        "apply_cost_plan_operations",
        "apply_programme_operations",
        "get_programme",
        "ensure_programme",
        "set_programme_view",
        "get_artefact_blocks",
        "appoint_consultant",
    ):
        assert name in PI_MCP_DIRECT_TOOLS


def test_pi_discovers_operation_tools(monkeypatch) -> None:
    session = _Session(_project())
    server, _access, _mutation = _install(monkeypatch, session)

    async def run():
        async with Client(server.mcp) as client:
            tools = await client.list_tools()
            return {tool.name for tool in tools}

    names = run_async(run())
    assert "apply_artefact_operations" in names
    assert "apply_cost_plan_operations" in names
    assert "apply_programme_operations" in names
    assert "get_programme" in names
    assert "get_artefact_blocks" in names
    assert "appoint_consultant" in names


def test_apply_artefact_operations_rejects_unauthorized(monkeypatch) -> None:
    session = _Session(_project())
    server, _access, mutation = _install(monkeypatch, session)
    mutation.side_effect = ToolAuthError("mutation denied")

    with pytest.raises(ToolError, match="mutation denied"):
        _call(
            server,
            "apply_artefact_operations",
            {
                "project_id": str(PROJECT_ID),
                "draft_id": str(DRAFT_ID),
                "expected_base_version": 1,
                "operations": [
                    {
                        "operation": "ADD",
                        "target": {"id": BLOCK_ID, "type": "paragraph"},
                        "content": "Filtered water tap",
                        "placement": "after",
                    }
                ],
            },
        )


def test_apply_artefact_operations_rejects_cross_project_draft(monkeypatch) -> None:
    session = _Session(_project())
    server, _access, _mutation = _install(monkeypatch, session)
    monkeypatch.setattr(
        server,
        "get_draft_artifact",
        AsyncMock(return_value=_draft(project_id=OTHER_PROJECT_ID)),
    )

    with pytest.raises(ToolError, match="Draft not found"):
        _call(
            server,
            "apply_artefact_operations",
            {
                "project_id": str(PROJECT_ID),
                "draft_id": str(DRAFT_ID),
                "expected_base_version": 1,
                "operations": [
                    {
                        "operation": "DUPLICATE",
                        "target": {"id": BLOCK_ID, "type": "paragraph"},
                    }
                ],
            },
        )


def test_apply_artefact_operations_rejects_invalid_schema(monkeypatch) -> None:
    session = _Session(_project())
    server, _access, _mutation = _install(monkeypatch, session)
    monkeypatch.setattr(
        server, "get_draft_artifact", AsyncMock(return_value=_draft())
    )

    with pytest.raises(ToolError):
        _call(
            server,
            "apply_artefact_operations",
            {
                "project_id": str(PROJECT_ID),
                "draft_id": str(DRAFT_ID),
                "expected_base_version": 1,
                "operations": [
                    {
                        "operation": "ADD",
                        "target": {"id": BLOCK_ID, "type": "paragraph"},
                        "placement": "after",
                    }
                ],
            },
        )


def test_apply_artefact_operations_rejects_stale_revision(monkeypatch) -> None:
    session = _Session(_project())
    server, _access, _mutation = _install(monkeypatch, session)
    monkeypatch.setattr(
        server, "get_draft_artifact", AsyncMock(return_value=_draft(version=2))
    )
    monkeypatch.setattr(
        server,
        "revise_workflow_artefact",
        AsyncMock(side_effect=ArtefactRevisionConflict("Expected create_pmp v1, current version is v2")),
    )
    monkeypatch.setattr(
        server,
        "apply_block_operations",
        Mock(
            return_value=SimpleNamespace(
                markdown="updated",
                metadata={},
                changed_block_ids=(BLOCK_ID,),
            )
        ),
    )

    with pytest.raises(ToolError, match="Expected create_pmp v1"):
        _call(
            server,
            "apply_artefact_operations",
            {
                "project_id": str(PROJECT_ID),
                "draft_id": str(DRAFT_ID),
                "expected_base_version": 1,
                "operations": [
                    {
                        "operation": "UPDATE",
                        "target": {"id": BLOCK_ID, "type": "paragraph"},
                        "content": "Updated kitchen works.",
                    }
                ],
            },
        )


def test_apply_artefact_add_row_changes_one_object(monkeypatch) -> None:
    session = _Session(_project())
    server, _access, mutation = _install(monkeypatch, session)
    draft = _draft()
    monkeypatch.setattr(server, "get_draft_artifact", AsyncMock(return_value=draft))
    revise = AsyncMock(
        return_value=SimpleNamespace(
            id=DRAFT_ID,
            version=2,
            provenance_metadata=dict(draft.provenance_metadata),
        )
    )
    monkeypatch.setattr(server, "revise_workflow_artefact", revise)

    result = _call(
        server,
        "apply_artefact_operations",
        {
            "project_id": str(PROJECT_ID),
            "draft_id": str(DRAFT_ID),
            "expected_base_version": 1,
            "operations": [
                {
                    "operation": "ADD",
                    "target": {"id": BLOCK_ID, "type": "paragraph"},
                    "content": "Filtered water tap in kitchen.",
                    "placement": "after",
                }
            ],
        },
    )

    assert result["kind"] == "artefact_operations_applied"
    assert result["version"] == 2
    assert len(result["changed_block_ids"]) == 1
    assert "task_route" not in result
    mutation.assert_called()
    assert session.committed is True
    revise.assert_awaited_once()
    assert revise.await_args.kwargs["expected_base_version"] == 1
    assert "Filtered water tap in kitchen." in revise.await_args.kwargs["content_markdown"]
    assert "Existing kitchen works." in revise.await_args.kwargs["content_markdown"]


def test_apply_cost_plan_two_rows_one_revision_one_workbook(monkeypatch) -> None:
    session = _Session(_project())
    server, _access, _mutation = _install(monkeypatch, session)
    persist = AsyncMock(
        return_value=SimpleNamespace(
            delta=SimpleNamespace(
                model_dump=lambda mode="json": {
                    "version": 3,
                    "changed_items": [
                        {"item_key": "loose-furniture"},
                        {"item_key": "av-equipment"},
                    ],
                    "deleted_item_keys": [],
                    "totals": {},
                    "workbook_status": "pending",
                }
            ),
            state=SimpleNamespace(version=3),
        )
    )
    schedule = Mock(return_value={"status": "queued", "version": 3})
    monkeypatch.setattr(server, "persist_cost_operations", persist)
    monkeypatch.setattr(server, "schedule_cost_plan_workbook_rebuild", schedule)

    result = _call(
        server,
        "apply_cost_plan_operations",
        {
            "project_id": str(PROJECT_ID),
            "expected_base_version": 2,
            "operations": [
                {
                    "operation": "ADD",
                    "target_type": "cost_item",
                    "values": {
                        "item_key": "loose-furniture",
                        "cost_code": "FF-01",
                        "category": "Loose Furniture",
                        "item": "Loose Furniture",
                        "basis": "allowance",
                        "budget": "50000",
                    },
                },
                {
                    "operation": "ADD",
                    "target_type": "cost_item",
                    "values": {
                        "item_key": "av-equipment",
                        "cost_code": "AV-01",
                        "category": "AV Equipment",
                        "item": "AV Equipment",
                        "basis": "allowance",
                        "budget": "25000",
                    },
                },
            ],
        },
    )

    assert result["kind"] == "cost_plan_operations_applied"
    assert result["delta"]["version"] == 3
    assert len(result["delta"]["changed_items"]) == 2
    assert "task_route" not in result
    persist.assert_awaited_once()
    schedule.assert_called_once_with(PROJECT_ID, 3)
    assert result["workbook"] == {"status": "queued", "version": 3}


def test_apply_cost_plan_rejects_invalid_schema(monkeypatch) -> None:
    session = _Session(_project())
    server, _access, _mutation = _install(monkeypatch, session)

    with pytest.raises(ToolError):
        _call(
            server,
            "apply_cost_plan_operations",
            {
                "project_id": str(PROJECT_ID),
                "expected_base_version": 1,
                "operations": [
                    {
                        "operation": "UPDATE",
                        "target_type": "cost_item",
                        "values": {"budget": "100"},
                    }
                ],
            },
        )


def test_apply_cost_plan_rejects_stale_revision(monkeypatch) -> None:
    session = _Session(_project())
    server, _access, _mutation = _install(monkeypatch, session)
    monkeypatch.setattr(
        server,
        "persist_cost_operations",
        AsyncMock(side_effect=ArtefactRevisionConflict("stale cost plan version")),
    )

    with pytest.raises(ToolError, match="stale cost plan version"):
        _call(
            server,
            "apply_cost_plan_operations",
            {
                "project_id": str(PROJECT_ID),
                "expected_base_version": 1,
                "operations": [
                    {
                        "operation": "DELETE",
                        "target_type": "cost_item",
                        "target_id": "row-1",
                    }
                ],
            },
        )


def test_apply_programme_operations_writes_state(monkeypatch) -> None:
    session = _Session(_project())
    server, _access, _mutation = _install(monkeypatch, session)
    persist = AsyncMock(
        return_value=SimpleNamespace(
            model_dump=lambda mode="json": {"version": 2, "activities": []}
        )
    )
    monkeypatch.setattr(server, "persist_programme_operations", persist)

    result = _call(
        server,
        "apply_programme_operations",
        {
            "project_id": str(PROJECT_ID),
            "expected_base_version": 1,
            "operations": [
                {
                    "operation": "ADD",
                    "target_type": "activity",
                    "values": {
                        "name": "Slab",
                        "parent_key": "delivery",
                        "start_date": "2027-02-01",
                        "duration_days": 14,
                    },
                }
            ],
        },
    )

    persist.assert_awaited_once()
    assert result["kind"] == "programme_operations_applied"
    assert result["state"]["version"] == 2


def test_apply_programme_operations_schema_describes_operation_shape(monkeypatch) -> None:
    session = _Session(_project())
    server, _access, _mutation = _install(monkeypatch, session)

    async def run():
        async with Client(server.mcp) as client:
            tools = await client.list_tools()
            return next(tool for tool in tools if tool.name == "apply_programme_operations")

    tool = run_async(run())
    items = tool.inputSchema["properties"]["operations"]["items"]
    assert items["properties"]["operation"]["enum"] == ["ADD", "UPDATE", "DELETE", "MOVE"]
    assert "activity" in items["properties"]["target_type"]["enum"]
    assert items["properties"]["values"]["type"] == "object"


def test_apply_programme_operations_accepts_flattened_fields(monkeypatch) -> None:
    session = _Session(_project())
    server, _access, _mutation = _install(monkeypatch, session)
    persist = AsyncMock(
        return_value=SimpleNamespace(
            model_dump=lambda mode="json": {"version": 2, "activities": []}
        )
    )
    monkeypatch.setattr(server, "persist_programme_operations", persist)

    result = _call(
        server,
        "apply_programme_operations",
        {
            "project_id": str(PROJECT_ID),
            "expected_base_version": 1,
            "operations": [
                {
                    "operation": "ADD",
                    "target_type": "activity",
                    "name": "Concept design",
                    "parent_key": "planning",
                    "start_date": "2026-08-16",
                    "duration_days": 42,
                }
            ],
        },
    )

    parsed = persist.await_args.kwargs["operations"][0]
    assert parsed.values["name"] == "Concept design"
    assert parsed.values["parent_key"] == "planning"
    assert result["kind"] == "programme_operations_applied"


def test_turn_token_project_isolation_for_artefact_ops(monkeypatch) -> None:
    from app.mcp_bridge import server

    project = _project(OTHER_PROJECT_ID)
    session = _Session(project)
    token = mint_turn_token(
        user_id=USER_ID, project_id=PROJECT_ID, secret=SECRET
    )
    monkeypatch.setattr(
        server,
        "get_http_headers",
        lambda **_kwargs: {"authorization": f"Bearer {token}"},
    )
    monkeypatch.setattr(server, "get_session_factory", lambda: lambda: session)

    with pytest.raises(ToolError):
        _call(
            server,
            "apply_artefact_operations",
            {
                "project_id": str(OTHER_PROJECT_ID),
                "draft_id": str(DRAFT_ID),
                "expected_base_version": 1,
                "operations": [
                    {
                        "operation": "DELETE",
                        "target": {"id": BLOCK_ID, "type": "paragraph"},
                    }
                ],
            },
        )


def test_get_artefact_blocks_bounded_read_contract(monkeypatch) -> None:
    session = _Session(_project())
    server, access, _mutation = _install(monkeypatch, session)
    monkeypatch.setattr(
        server, "get_draft_artifact", AsyncMock(return_value=_draft(version=4))
    )

    result = _call(
        server,
        "get_artefact_blocks",
        {"project_id": str(PROJECT_ID), "draft_id": str(DRAFT_ID)},
    )

    assert result["project_id"] == str(PROJECT_ID)
    assert result["draft_id"] == str(DRAFT_ID)
    assert result["version"] == 4
    assert result["workflow_type"] == "create_pmp"
    assert len(result["blocks"]) == 1
    block = result["blocks"][0]
    assert block["id"] == BLOCK_ID
    assert block["type"] == "paragraph"
    assert "Existing kitchen works." in block["content"]
    assert block["user_protected"] is False
    access.assert_called()


def test_get_artefact_blocks_resolves_latest_pmp_when_draft_id_omitted(
    monkeypatch,
) -> None:
    session = _Session(_project())
    server, access, _mutation = _install(monkeypatch, session)
    latest = _draft(version=7)
    get_latest = AsyncMock(return_value=latest)
    monkeypatch.setattr(server, "get_latest_draft_artifact", get_latest)

    result = _call(
        server,
        "get_artefact_blocks",
        {"project_id": str(PROJECT_ID)},
    )

    assert result["draft_id"] == str(DRAFT_ID)
    assert result["version"] == 7
    get_latest.assert_awaited_once()
    assert get_latest.await_args.kwargs["workflow_type"] == "create_pmp"
    access.assert_called()
