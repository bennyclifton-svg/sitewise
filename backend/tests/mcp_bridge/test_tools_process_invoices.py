from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastmcp.exceptions import ToolError

from app.mcp_bridge import server
from tests.conftest import run_async


def _workflow_args() -> dict:
    return {
        "project_id": "22222222-2222-2222-2222-222222222222",
        "idempotency_key": "turn-1:process-invoices",
        "expected_snapshot_fingerprint": "a" * 64,
        "expected_profile_revision": 2,
        "expected_decision_set_revision": 3,
        "expected_artefact_version": 5,
    }


def test_process_invoices_queues_named_sources(monkeypatch) -> None:
    start = AsyncMock(return_value={"state": "queued"})
    monkeypatch.setattr(server, "_start_mcp_workflow", start)
    source_id = uuid.uuid4()

    result = run_async(
        server.process_invoices(
            **_workflow_args(),
            source_document_ids=[str(source_id)],
        )
    )

    assert result["state"] == "queued"
    assert start.await_args.kwargs["workflow_type"] == "process_invoices"
    assert start.await_args.kwargs["expected_artefact_version"] == 5
    assert start.await_args.kwargs["parameters"] == {
        "source_document_ids": [str(source_id)]
    }


def test_process_invoices_rejects_invalid_source_ids(monkeypatch) -> None:
    start = AsyncMock()
    monkeypatch.setattr(server, "_start_mcp_workflow", start)

    with pytest.raises(ToolError, match="must contain UUIDs"):
        run_async(
            server.process_invoices(
                **_workflow_args(),
                source_document_ids=["not-a-uuid"],
            )
        )
    start.assert_not_awaited()
