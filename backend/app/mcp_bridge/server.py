"""Clerk's MCP tool server: thin tools delegating to existing services."""
from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import HTTPException
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from sqlalchemy import select
from sqlalchemy.orm.attributes import set_committed_value

from app.database.draft_artifacts import get_draft_artifact
from app.database.session import get_session_factory
from app.database.workspace_files import list_workspace_files_for_project
from app.agent.status_bus import agent_turn_status_bus
from app.mcp_bridge.auth import ToolAuthError, authorize_project_access_with_claims
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters
from tender.router import (
    create_comparison,
    create_quote,
    get_comparison_detail,
    list_comparisons,
    store_project_file_quote_document,
)
from tender.models import TenderAnalysisResult, TenderJob, TenderReport
from tender.schemas import QuoteCreate
from tender.services import jobs, matrix, qa

mcp = FastMCP("clerk")

TENDER_DOCUMENT_KEYWORDS = (
    "tender",
    "quote",
    "proposal",
    "pricing",
    "price",
    "boq",
    "schedule",
    "inclusion",
    "builder",
)
QUOTE_STAGE_UNITS = {
    "intake": 0,
    "ingest_document": 1,
    "classify_document": 2,
    "extract_line_items": 3,
    "embed_items": 4,
    "map_items": 5,
}
COMPARISON_STATUS_UNITS = {
    "intake": 0,
    "processing": 1,
    "qa": 2,
    "report_draft": 4,
    "approved": 4,
    "delivered": 4,
    "failed": 1,
}


def _auth_header() -> str | None:
    headers = get_http_headers(include={"authorization"})
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


def _document_summary(document) -> dict:
    return {
        "id": str(document.id),
        "filename": document.original_filename,
        "mime_type": document.mime_type,
        "doc_type": document.doc_type,
        "ingest_status": document.ingest_status,
        "page_count": document.page_count,
    }


def _quote_status_summary(quote) -> dict:
    return {
        "id": str(quote.id),
        "builder_name": quote.builder_name,
        "stage": quote.stage,
        "documents": [
            _document_summary(document)
            for document in getattr(quote, "documents", [])
        ],
    }


def _job_summary(job: TenderJob) -> dict:
    return {
        "id": str(job.id),
        "kind": job.kind,
        "status": job.status,
        "attempts": job.attempts,
        "quote_id": str(job.quote_id) if job.quote_id else None,
        "last_error": job.last_error,
        "run_after": job.run_after.isoformat() if job.run_after else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


def _progress_payload(comparison, pending_review_count: int) -> dict:
    quote_units = sum(
        QUOTE_STAGE_UNITS.get(getattr(quote, "stage", "intake"), 0)
        for quote in comparison.quotes
    )
    comparison_units = COMPARISON_STATUS_UNITS.get(comparison.status, 0)
    total_units = max(1, len(comparison.quotes) * max(QUOTE_STAGE_UNITS.values()) + 4)
    done_units = min(total_units, quote_units + comparison_units)
    if pending_review_count and comparison.status not in {"approved", "delivered"}:
        stage = "qa"
    elif comparison.status == "report_draft":
        stage = "report_draft"
    elif comparison.status in {"approved", "delivered"}:
        stage = comparison.status
    elif any(getattr(quote, "stage", "intake") != "intake" for quote in comparison.quotes):
        stage = "processing"
    else:
        stage = comparison.status
    return {
        "stage": stage,
        "done_units": done_units,
        "total_units": total_units,
        "percent": round((done_units / total_units) * 100, 1),
    }


def _candidate_document(record) -> dict | None:
    path = record.workspace_path.replace("\\", "/")
    filename = record.filename
    if not filename.lower().endswith(".pdf") and not path.lower().endswith(".pdf"):
        return None

    haystack = f"{path} {filename}".lower()
    matches = [keyword for keyword in TENDER_DOCUMENT_KEYWORDS if keyword in haystack]
    return {
        "workspace_path": path,
        "filename": filename,
        "size_bytes": record.size_bytes,
        "content_hash": record.content_hash,
        "source_document_id": (
            str(record.source_document_id) if record.source_document_id else None
        ),
        "selection_source": "candidate_workspace_files",
        "candidate_score": 10 + len(matches),
        "candidate_reasons": matches or ["pdf"],
    }


def _candidate_documents(records) -> list[dict]:
    candidates = [candidate for record in records if (candidate := _candidate_document(record))]
    return sorted(
        candidates,
        key=lambda item: (
            -item["candidate_score"],
            item["workspace_path"].lower(),
        ),
    )


def _turn_id(authorization) -> str | None:
    return str(authorization.claims.turn_id) if authorization.claims.turn_id else None


async def _comparison_jobs(
    session,
    comparison_id: uuid.UUID,
    *,
    limit: int = 25,
) -> list[TenderJob]:
    result = await session.execute(
        select(TenderJob)
        .where(TenderJob.comparison_id == comparison_id)
        .order_by(TenderJob.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def _pending_review_count(session, comparison_id: uuid.UUID) -> int:
    return len(await qa.list_review_items(session, comparison_id=comparison_id))


async def _latest_report_payload(session, comparison_id: uuid.UUID) -> dict | None:
    result = await session.execute(
        select(TenderReport)
        .where(TenderReport.comparison_id == comparison_id)
        .order_by(TenderReport.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if latest is None:
        return None

    draft = await get_draft_artifact(session, latest.draft_id)
    return {
        "report_id": str(latest.id),
        "comparison_id": str(latest.comparison_id),
        "draftId": str(latest.draft_id),
        "workflowType": "tender_report",
        "title": draft.title if draft is not None else "Tender comparison report",
        "version": latest.version,
        "html_path": latest.html_path,
        "pdf_path": latest.pdf_path,
        "approved_at": latest.approved_at.isoformat() if latest.approved_at else None,
        "delivered_at": latest.delivered_at.isoformat() if latest.delivered_at else None,
    }


async def _analysis_payload(session, comparison_id: uuid.UUID) -> dict | None:
    result = await session.execute(
        select(TenderAnalysisResult).where(
            TenderAnalysisResult.comparison_id == comparison_id
        )
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        return None
    return {
        "version": analysis.version,
        "gap_matrix": analysis.gap_matrix,
        "ledgers": analysis.ledgers,
        "questions": analysis.questions,
    }


async def _comparison_status_payload(session, comparison) -> dict:
    jobs_for_comparison = await _comparison_jobs(session, comparison.id)
    job_counts = Counter(job.status for job in jobs_for_comparison)
    pending_review_count = await _pending_review_count(session, comparison.id)
    report_payload = await _latest_report_payload(session, comparison.id)
    return {
        "comparison_id": str(comparison.id),
        "project_id": str(comparison.project_id),
        "status": comparison.status,
        "progress": _progress_payload(comparison, pending_review_count),
        "quotes": [_quote_status_summary(quote) for quote in comparison.quotes],
        "jobs": {
            "counts": dict(sorted(job_counts.items())),
            "latest": [_job_summary(job) for job in jobs_for_comparison],
        },
        "qa": {"pending_count": pending_review_count},
        "report": report_payload,
    }


async def _publish_report_artefact(
    turn_id: str | None,
    *,
    report_payload: dict | None,
    project_id: uuid.UUID,
) -> None:
    if report_payload is None:
        return
    await agent_turn_status_bus.publish(
        turn_id,
        kind="artefact",
        message=report_payload["title"],
        title=report_payload["title"],
        workflowType="tender_report",
        draftId=report_payload["draftId"],
        comparisonId=report_payload["comparison_id"],
        projectId=str(project_id),
    )


@asynccontextmanager
async def _tool_status(
    turn_id: str | None,
    *,
    tool: str,
    running: str,
    done: str,
    error: str,
) -> AsyncIterator[None]:
    await agent_turn_status_bus.publish(
        turn_id,
        message=running,
        tool=tool,
        state="running",
    )
    try:
        yield
    except Exception:
        await agent_turn_status_bus.publish(
            turn_id,
            message=error,
            tool=tool,
            state="error",
        )
        raise
    else:
        await agent_turn_status_bus.publish(
            turn_id,
            message=done,
            tool=tool,
            state="done",
        )


@mcp.tool
async def list_tender_comparisons(project_id: str) -> list[dict]:
    """List tender comparisons for a project with their quotes and stages."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        async with _tool_status(
            _turn_id(authorization),
            tool="list_tender_comparisons",
            running="Listing tender comparisons",
            done="Listed tender comparisons",
            error="Tender comparison listing failed",
        ):
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
            authorization = await authorize_project_access_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=comparison.project_id,
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        async with _tool_status(
            _turn_id(authorization),
            tool="get_tender_comparison",
            running="Loading tender comparison",
            done="Loaded tender comparison",
            error="Tender comparison lookup failed",
        ):
            return _comparison_summary(comparison)


@mcp.tool
async def get_comparison_status(comparison_id: str) -> dict:
    """Return progress, queued work, QA count, and report state for a comparison."""
    cid = uuid.UUID(comparison_id)
    async with get_session_factory()() as session:
        comparison = await get_comparison_detail(session, cid)
        if comparison is None:
            raise ToolError("comparison not found")
        try:
            authorization = await authorize_project_access_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=comparison.project_id,
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        async with _tool_status(
            _turn_id(authorization),
            tool="get_comparison_status",
            running="Checking comparison progress",
            done="Checked comparison progress",
            error="Comparison status lookup failed",
        ):
            return await _comparison_status_payload(session, comparison)


@mcp.tool
async def get_comparison_result(comparison_id: str) -> dict:
    """Return matrix, analysis, report metadata, and status for a comparison."""
    cid = uuid.UUID(comparison_id)
    async with get_session_factory()() as session:
        comparison = await get_comparison_detail(session, cid)
        if comparison is None:
            raise ToolError("comparison not found")
        try:
            authorization = await authorize_project_access_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=comparison.project_id,
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        async with _tool_status(
            _turn_id(authorization),
            tool="get_comparison_result",
            running="Loading comparison result",
            done="Loaded comparison result",
            error="Comparison result lookup failed",
        ):
            status_payload = await _comparison_status_payload(session, comparison)
            report_payload = status_payload["report"]
            await _publish_report_artefact(
                _turn_id(authorization),
                report_payload=report_payload,
                project_id=comparison.project_id,
            )
            matrix_payload = await matrix.build_matrix(session, comparison_id=cid)
            return {
                "status": status_payload,
                "matrix": matrix_payload.model_dump(mode="json"),
                "analysis": await _analysis_payload(session, cid),
                "report": report_payload,
            }


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
            authorization = await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        project = authorization.project

        async with _tool_status(
            _turn_id(authorization),
            tool="start_tender_comparison",
            running="Starting tender comparison",
            done="Started tender comparison",
            error="Tender comparison start failed",
        ):
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


@mcp.tool
async def list_selected_documents(project_id: str) -> list[dict]:
    """Return candidate tender PDFs from the project workspace.

    Clerk does not yet persist a backend document-selection model. This tool
    therefore returns likely tender/quote PDFs so Hermes can ask the user to
    confirm explicit workspace_paths before starting a comparison.
    """
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        async with _tool_status(
            _turn_id(authorization),
            tool="list_selected_documents",
            running="Finding candidate tender documents",
            done="Found candidate tender documents",
            error="Candidate document lookup failed",
        ):
            records = await list_workspace_files_for_project(session, project_id=pid)
        return _candidate_documents(records)


@mcp.tool
async def search_documents(project_id: str, query: str) -> list[dict]:
    """Search the project's ingested documents; returns snippets with scores."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        project = authorization.project
        async with _tool_status(
            _turn_id(authorization),
            tool="search_documents",
            running="Searching project documents",
            done="Searched project documents",
            error="Project document search failed",
        ):
            retriever = DocumentRetriever(session)
            passages = await retriever.retrieve(
                query,
                filters=RetrievalFilters(
                    active_project=project.slug,
                    include_platform_knowledge=False,
                ),
                include_neighbours=False,
            )
        return [
            {"document": p.filename, "snippet": p.content, "score": p.score}
            for p in passages
        ]
