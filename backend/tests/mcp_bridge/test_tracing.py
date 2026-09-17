import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Client, FastMCP

from app.agent.observability import ToolTrace, current_tool_trace, provider_span
from app.config import settings
from app.mcp_bridge import tracing, tool_commits
from app.mcp_bridge.tokens import mint_turn_token
from tests.conftest import run_async


def test_common_middleware_traces_each_call_and_masks_content(monkeypatch):
    turn_id, project_id = uuid.uuid4(), uuid.uuid4()
    monkeypatch.setattr(settings, "agent_turn_token_secret", "test-tracing-secret")
    bearer = mint_turn_token(
        user_id=uuid.uuid4(), project_id=project_id, turn_id=turn_id
    )
    monkeypatch.setattr(
        tracing, "get_http_headers", lambda: {"authorization": f"Bearer {bearer}"}
    )
    store = SimpleNamespace(start=AsyncMock(), finish=AsyncMock())
    mcp = FastMCP("trace-test", mask_error_details=True)
    mcp.add_middleware(tracing.ToolTracingMiddleware(store))

    @mcp.tool
    async def search(project_id: str, query: str, fail: bool = False):
        async with provider_span("test-provider", "search"):
            if fail:
                raise ValueError("private provider secret")
            return {"content": query}

    async def run():
        async with Client(mcp) as client:
            for fail in (False, False, True):
                await client.call_tool(
                    "search",
                    {
                        "project_id": str(project_id),
                        "query": "private project content",
                        "fail": fail,
                    },
                    raise_on_error=False,
                )

    run_async(run())
    traces = [call.args[0] for call in store.start.await_args_list]
    assert len({trace.id for trace in traces}) == 3
    assert all(trace.turn_id == turn_id for trace in traces)
    assert [call.kwargs["outcome"] for call in store.finish.await_args_list] == [
        "succeeded",
        "succeeded",
        "failed",
    ]
    assert traces[-1].providers[0]["error_type"] == "ValueError"
    assert "private" not in repr(traces)
    assert current_tool_trace.get() is None


@pytest.mark.parametrize("header", ["", "Bearer invalid"])
def test_unverified_call_cannot_forge_a_turn_trace(monkeypatch, header):
    monkeypatch.setattr(tracing, "get_http_headers", lambda: {"authorization": header})
    store = SimpleNamespace(start=AsyncMock(), finish=AsyncMock())
    middleware = tracing.ToolTracingMiddleware(store)
    next_call = AsyncMock(side_effect=PermissionError("denied"))
    context = SimpleNamespace(
        message=SimpleNamespace(
            name="write", arguments={"project_id": str(uuid.uuid4())}
        )
    )
    with pytest.raises(PermissionError):
        run_async(middleware.on_call_tool(context, next_call))
    store.start.assert_not_awaited()


def test_committed_receipts_share_the_mutation_transaction_and_rollback_discards():
    from app.database.procurement_strategy import ProcurementStrategy

    trace = ToolTrace(
        uuid.uuid4(), uuid.uuid4(), "apply_procurement_strategy_operations"
    )
    strategy = ProcurementStrategy(id=uuid.uuid4(), revision=12)
    session = MagicMock()
    session.info = {}
    session.new, session.dirty, session.deleted = [], [strategy], []
    token = current_tool_trace.set(trace)
    try:
        tool_commits.capture_mutations(session, None, None)
        tool_commits.capture_flushed_revisions(session, None)
        tool_commits.persist_commit_receipts(session)
        session.flush.assert_called_once()
        stmt = session.execute.call_args.args[0]
        values = stmt.compile().params
        assert any(
            isinstance(value, list) and value[0]["revision"] == 12
            for value in values.values()
        )
        assert trace.id in values.values()
        session.commit.assert_not_called()
        tool_commits.capture_mutations(session, None, None)
        tool_commits.discard_rolled_back_receipts(session)
        assert "agent_commit_receipts" not in session.info
    finally:
        current_tool_trace.reset(token)


def test_cancelled_provider_records_type_not_exception_text():
    async def run():
        trace = ToolTrace(uuid.uuid4(), uuid.uuid4(), "search")
        token = current_tool_trace.set(trace)
        try:
            with pytest.raises(asyncio.CancelledError):
                async with provider_span("brave", "search"):
                    raise asyncio.CancelledError("private query")
            assert trace.providers[0]["error_type"] == "CancelledError"
            assert "private" not in str(trace.providers)
        finally:
            current_tool_trace.reset(token)

    run_async(run())
