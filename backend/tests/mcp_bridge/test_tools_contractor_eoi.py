from unittest.mock import AsyncMock

from app.mcp_bridge import server
from tests.conftest import run_async


def _workflow_args() -> dict:
    return {
        "project_id": "22222222-2222-2222-2222-222222222222",
        "idempotency_key": "turn-1:contractor-eoi",
        "expected_snapshot_fingerprint": "a" * 64,
        "expected_profile_revision": 2,
        "expected_decision_set_revision": 3,
    }


def test_start_contractor_eoi_queues_expected_workflow(monkeypatch) -> None:
    start = AsyncMock(return_value={"kind": "workflow_run", "status": "queued"})
    monkeypatch.setattr(server, "_start_mcp_workflow", start)

    result = run_async(
        server.start_contractor_eoi(
            **_workflow_args(),
            package="Main Works",
            max_pages=2,
            instructions="Focus on occupied-site experience.",
        )
    )

    assert result["status"] == "queued"
    assert start.await_args.kwargs["workflow_type"] == "contractor_eoi"
    assert start.await_args.kwargs["parameters"] == {
        "package": "Main Works",
        "max_pages": 2,
        "instructions": "Focus on occupied-site experience.",
    }


def test_consultant_tool_blocks_contractor_before_queueing(monkeypatch) -> None:
    start = AsyncMock()
    monkeypatch.setattr(server, "_start_mcp_workflow", start)

    result = run_async(
        server.start_consultant_procurement(
            **_workflow_args(),
            discipline="head contractor",
        )
    )

    assert result["kind"] == "blocked"
    assert result["redirect"] == "start_trade_procurement"
    start.assert_not_awaited()


def test_start_trade_procurement_queues_expected_workflow(monkeypatch) -> None:
    start = AsyncMock(return_value={"kind": "workflow_run", "status": "queued"})
    monkeypatch.setattr(server, "_start_mcp_workflow", start)

    result = run_async(
        server.start_trade_procurement(
            **_workflow_args(),
            package="Electrical contractor",
            kind="rfq",
            max_pages=5,
            instructions="Include lead times.",
        )
    )

    assert result["status"] == "queued"
    assert start.await_args.kwargs["workflow_type"] == "trade_procurement"
    assert start.await_args.kwargs["parameters"] == {
        "package": "Electrical contractor",
        "kind": "rfq",
        "max_pages": 5,
        "instructions": "Include lead times.",
    }
