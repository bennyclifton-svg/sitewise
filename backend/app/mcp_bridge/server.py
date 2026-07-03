"""Clerk's MCP tool server: thin tools delegating to existing services."""
from __future__ import annotations

import uuid

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers

from app.database.session import get_session_factory
from app.mcp_bridge.auth import ToolAuthError, authorize_project_access
from tender.router import get_comparison_detail, list_comparisons

mcp = FastMCP("clerk")


def _auth_header() -> str | None:
    headers = get_http_headers()
    return headers.get("authorization")


def _comparison_summary(comparison) -> dict:
    return {
        "id": str(comparison.id),
        "status": getattr(comparison, "status", None),
        "quotes": [
            {"id": str(q.id), "builder": q.builder_name, "stage": q.stage}
            for q in comparison.quotes
        ],
    }


@mcp.tool
async def list_tender_comparisons(project_id: str) -> list[dict]:
    """List tender comparisons for a project with their quotes and stages."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            await authorize_project_access(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        comparisons = await list_comparisons(session, project_id=pid)
        return [_comparison_summary(c) for c in comparisons]


@mcp.tool
async def get_tender_comparison(comparison_id: str) -> dict:
    """Get one tender comparison with its quotes and stages."""
    cid = uuid.UUID(comparison_id)
    async with get_session_factory()() as session:
        comparison = await get_comparison_detail(session, cid)
        if comparison is None:
            raise ToolError("comparison not found")
        try:
            await authorize_project_access(
                session,
                authorization_header=_auth_header(),
                project_id=comparison.project_id,
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        return _comparison_summary(comparison)
