"""Clerk's MCP tool server: thin tools delegating to existing services."""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from sqlalchemy.orm.attributes import set_committed_value

from app.database.session import get_session_factory
from app.mcp_bridge.auth import ToolAuthError, authorize_project_access
from tender.router import (
    create_comparison,
    create_quote,
    get_comparison_detail,
    list_comparisons,
    store_project_file_quote_document,
)
from tender.schemas import QuoteCreate
from tender.services import jobs

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


@mcp.tool
async def start_tender_comparison(
    project_id: str,
    context: dict,
    quotes: list[dict],
) -> dict:
    """Start a tender comparison: create quotes from workspace files and queue ingestion.

    Each quote is {"builder_name": str, "workspace_paths": [str, ...]}. A quote
    whose workspace path cannot be found is reported in its "error" field;
    the other quotes still proceed.
    """
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            project = await authorize_project_access(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc

        comparison = await create_comparison(
            session,
            project_id=pid,
            context=context,
            created_by=project.owner_user_id,
        )

        quote_results: list[dict] = []
        for spec in quotes:
            quote = await create_quote(
                session,
                comparison_id=comparison.id,
                body=QuoteCreate(builder_name=spec["builder_name"]),
            )
            set_committed_value(quote, "comparison", comparison)
            entry: dict = {
                "quote_id": str(quote.id),
                "builder_name": quote.builder_name,
                "documents": [],
            }
            workspace_path = None
            try:
                for workspace_path in spec.get("workspace_paths", []):
                    document = await store_project_file_quote_document(
                        session, quote=quote, workspace_path=workspace_path
                    )
                    await jobs.enqueue(
                        session,
                        kind="ingest_document",
                        comparison_id=quote.comparison_id,
                        quote_id=quote.id,
                        payload={"document_id": str(document.id)},
                    )
                    entry["documents"].append(str(document.id))
            except HTTPException as exc:
                entry["error"] = f"{workspace_path}: {exc.detail}"
            quote_results.append(entry)

        await session.commit()
        return {"comparison_id": str(comparison.id), "quotes": quote_results}
