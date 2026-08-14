from __future__ import annotations

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from app.mcp_bridge import server
from tests.conftest import run_async


UNEXPECTED_TOOL = "ch03_unexpected_failure"
UNEXPECTED_CANARY = "ch03-mcp-provider-token-xxxxxxxxxxxxxxxxxxxxxxxx"
CONTROLLED_TOOL = "ch03_controlled_failure"
CONTROLLED_MESSAGE = "Select a project document before retrying."


async def _call_tool(name: str) -> None:
    async with Client(server.mcp) as client:
        await client.call_tool(name)


def test_mcp_masks_uncaught_tool_exception_details() -> None:
    def fail_unexpectedly() -> str:
        raise RuntimeError(f"provider rejected token={UNEXPECTED_CANARY}")

    server.mcp.tool(name=UNEXPECTED_TOOL)(fail_unexpectedly)
    try:
        with pytest.raises(ToolError) as captured:
            run_async(_call_tool(UNEXPECTED_TOOL))
    finally:
        server.mcp.local_provider.remove_tool(UNEXPECTED_TOOL)

    rendered = str(captured.value)
    assert rendered == f"Error calling tool {UNEXPECTED_TOOL!r}"
    assert UNEXPECTED_CANARY not in rendered


def test_mcp_preserves_controlled_tool_error_message() -> None:
    def fail_with_guidance() -> str:
        raise ToolError(CONTROLLED_MESSAGE)

    server.mcp.tool(name=CONTROLLED_TOOL)(fail_with_guidance)
    try:
        with pytest.raises(ToolError) as captured:
            run_async(_call_tool(CONTROLLED_TOOL))
    finally:
        server.mcp.local_provider.remove_tool(CONTROLLED_TOOL)

    assert str(captured.value) == CONTROLLED_MESSAGE
