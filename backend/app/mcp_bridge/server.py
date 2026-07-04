"""Clerk's MCP tool server: thin tools delegating to existing services."""
from __future__ import annotations

import asyncio
import uuid
from collections import Counter
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import HTTPException
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from sqlalchemy import select
from sqlalchemy.orm.attributes import set_committed_value

from app.agent.workspace_paths import (
    WorkspacePathError,
    normalize_workspace_path,
    project_workspace_root,
    resolve_workspace_path,
)
from app.database.draft_artifacts import (
    create_draft_revision,
    get_draft_artifact,
    get_latest_draft_artifact_by_workspace_path,
)
from app.database.session import get_session_factory
from app.agent.status_bus import agent_turn_status_bus
from app.database.workspace_files import (
    get_workspace_file_by_path,
    list_workspace_files_for_project,
)
from app.config import settings
from app.mcp_bridge.auth import ToolAuthError, authorize_project_access_with_claims
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters
from app.sitewise.gate import format_overlay_failure, overlay_status
from app.sitewise.knowledge_catalog import (
    list_platform_knowledge as catalog_platform_knowledge,
    load_sections as load_platform_sections,
    select_required_paths,
)
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


def _tool_workspace_path(path: str | None) -> str:
    try:
        return normalize_workspace_path(path)
    except WorkspacePathError as exc:
        raise ToolError(f"invalid workspace path: {exc}") from exc


def _tool_resolve_path(project_id: uuid.UUID, path: str | None) -> Path:
    try:
        return resolve_workspace_path(project_id, path)
    except WorkspacePathError as exc:
        raise ToolError(f"invalid workspace path: {exc}") from exc


def _scratch_relative_path(project_id: uuid.UUID, path: Path) -> str:
    root = project_workspace_root(project_id).resolve(strict=False)
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise WorkspacePathError("workspace path escapes the project root")
    return resolved.relative_to(root).as_posix()


def _list_scratch_directory(project_id: uuid.UUID, path: Path) -> list[dict]:
    entries: list[dict] = []
    for item in sorted(path.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower())):
        rel_path = _scratch_relative_path(project_id, item)
        entries.append(
            {
                "name": item.name,
                "path": rel_path,
                "kind": "directory" if item.is_dir() else "file",
                "size_bytes": item.stat().st_size if item.is_file() else 0,
            }
        )
    return entries


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text_file(path: Path, content: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path.stat().st_size


def _draft_file_payload(draft) -> dict:
    content = draft.content_markdown
    return {
        "kind": "artefact",
        "path": draft.workspace_path,
        "draftId": str(draft.id),
        "workflowType": draft.workflow_type,
        "version": draft.version,
        "title": draft.title,
        "content": content,
        "size_bytes": len(content.encode("utf-8")),
    }


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
) -> AsyncIterator[dict]:
    await agent_turn_status_bus.publish(
        turn_id,
        message=running,
        tool=tool,
        state="running",
    )
    extra: dict = {}
    try:
        yield extra
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
            **extra,
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
        ) as extra:
            payload = await _comparison_status_payload(session, comparison)
            progress = payload.get("progress")
            if progress:
                extra["stage"] = progress["stage"]
                extra["percent"] = progress["percent"]
                extra["doneUnits"] = progress["done_units"]
                extra["totalUnits"] = progress["total_units"]
            return payload


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
async def list_workspace(project_id: str, path: str = ".") -> list[dict]:
    """List text scratch files under the project's scoped agent workspace."""
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
            tool="list_workspace",
            running="Listing workspace files",
            done="Listed workspace files",
            error="Workspace listing failed",
        ):
            target = _tool_resolve_path(pid, path)
            root = _tool_resolve_path(pid, ".")
            await asyncio.to_thread(root.mkdir, parents=True, exist_ok=True)
            if not await asyncio.to_thread(target.exists):
                return []
            if not await asyncio.to_thread(target.is_dir):
                raise ToolError("workspace path is not a directory")
            try:
                return await asyncio.to_thread(_list_scratch_directory, pid, target)
            except WorkspacePathError as exc:
                raise ToolError(f"invalid workspace path: {exc}") from exc


@mcp.tool
async def read_workspace_file(project_id: str, path: str) -> dict:
    """Read a UTF-8 scratch file or latest editable artefact for this project."""
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
            tool="read_workspace_file",
            running="Reading workspace file",
            done="Read workspace file",
            error="Workspace file read failed",
        ):
            workspace_path = _tool_workspace_path(path)
            draft = await get_latest_draft_artifact_by_workspace_path(
                session,
                project_id=pid,
                workspace_path=workspace_path,
            )
            if draft is not None:
                return _draft_file_payload(draft)

            source = await get_workspace_file_by_path(
                session,
                project_id=pid,
                workspace_path=workspace_path,
            )
            if source is not None:
                raise ToolError("source documents must be read through document tools")

            target = _tool_resolve_path(pid, workspace_path)
            if not await asyncio.to_thread(target.exists):
                raise ToolError("workspace file not found")
            if not await asyncio.to_thread(target.is_file):
                raise ToolError("workspace path is not a file")
            try:
                content = await asyncio.to_thread(_read_text_file, target)
            except UnicodeDecodeError as exc:
                raise ToolError("workspace file is not UTF-8 text") from exc
            return {
                "kind": "scratch",
                "path": workspace_path,
                "content": content,
                "size_bytes": len(content.encode("utf-8")),
            }


@mcp.tool
async def write_workspace_file(project_id: str, path: str, content: str) -> dict:
    """Write a UTF-8 scratch file or create a new version of an editable artefact."""
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
            tool="write_workspace_file",
            running="Writing workspace file",
            done="Wrote workspace file",
            error="Workspace file write failed",
        ):
            workspace_path = _tool_workspace_path(path)
            draft = await get_latest_draft_artifact_by_workspace_path(
                session,
                project_id=pid,
                workspace_path=workspace_path,
            )
            if draft is not None:
                updated = await create_draft_revision(
                    session,
                    draft=draft,
                    author_user_id=authorization.claims.user_id,
                    content_markdown=content,
                    edit_source="agent",
                )
                await session.commit()
                return {
                    "kind": "artefact",
                    "path": updated.workspace_path,
                    "draftId": str(updated.id),
                    "workflowType": updated.workflow_type,
                    "version": updated.version,
                    "bytes_written": len(content.encode("utf-8")),
                }

            source = await get_workspace_file_by_path(
                session,
                project_id=pid,
                workspace_path=workspace_path,
            )
            if source is not None:
                raise ToolError("source documents are read-only")

            target = _tool_resolve_path(pid, workspace_path)
            bytes_written = await asyncio.to_thread(_write_text_file, target, content)
            return {
                "kind": "scratch",
                "path": workspace_path,
                "bytes_written": bytes_written,
            }


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
                    # Platform knowledge stays out of evidence search by design:
                    # it arrives through list/read_platform_knowledge so the
                    # evidence-beats-seed authority stack stays structural.
                    include_platform_knowledge=False,
                ),
                include_neighbours=False,
            )
        return [
            {"document": p.filename, "snippet": p.content, "score": p.score}
            for p in passages
        ]


@mcp.tool
async def list_platform_knowledge(project_id: str, topics: list[str] | None = None) -> dict:
    """Catalog SiteWise platform knowledge (doctrine + seed guides) for this project.

    Applies the three-overlay gate: if the project has not declared archetype,
    user_role, and state, no knowledge is listed — resolve the gate with the
    user first. When the gate passes, returns the mandatory reading list per
    workflow and the guides that apply to the declared overlays (metadata and
    section IDs only — load content with read_platform_knowledge). Optionally
    filter by topics (e.g. ["cost", "programme"]). Platform knowledge informs
    drafting; project evidence always beats it.
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
            tool="list_platform_knowledge",
            running="Listing platform knowledge",
            done="Listed platform knowledge",
            error="Platform knowledge listing failed",
        ):
            status = overlay_status(
                archetype=project.archetype,
                user_role=project.user_role,
                state=project.state,
            )
            gate = {
                "archetype": project.archetype,
                "user_role": project.user_role,
                "state": project.state,
                "ready": status.ready,
                "issues": [issue.model_dump() for issue in status.issues],
            }
            if not status.ready:
                return {
                    "gate": gate,
                    "message": format_overlay_failure(
                        status, workflow="Platform knowledge access"
                    ),
                    "required": {},
                    "available": [],
                }
            required = {
                workflow: select_required_paths(
                    workflow=workflow,
                    archetype=project.archetype,
                    user_role=project.user_role,
                )
                for workflow in ("create-pmp", "create-cost-plan")
            }
            available = await catalog_platform_knowledge(
                session,
                archetype=project.archetype,
                user_role=project.user_role,
                topics=topics,
            )
        return {"gate": gate, "required": required, "available": available}


@mcp.tool
async def read_platform_knowledge(
    project_id: str, path: str, section_ids: list[str] | None = None
) -> dict:
    """Read a platform knowledge document, whole or by targeted sections.

    Use paths and section IDs from list_platform_knowledge. Reading the
    doctrine without section_ids serves its core (authority stack and
    cross-cutting rules); stage sections (e.g. "01-cost", "07-construction")
    load by section ID. Cite the source path in any output that uses this
    content, and record it as consulted knowledge, not project evidence.
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
            tool="read_platform_knowledge",
            running=f"Reading platform knowledge: {path}",
            done=f"Read platform knowledge: {path}",
            error="Platform knowledge read failed",
        ) as extra:
            loaded = await load_platform_sections(
                session,
                path,
                section_ids,
                max_chars=settings.whole_document_content_chars,
            )
            if loaded is None:
                raise ToolError(
                    f"Platform document not in the corpus: {path}. "
                    "Check the path against list_platform_knowledge."
                )
            # The Hermes analog of the deterministic workflows' seed_consulted
            # audit: every knowledge read is visible on the turn's status feed.
            extra["knowledge_path"] = path
            extra["section_ids"] = section_ids or []
        if loaded.passage is None:
            return {
                "path": path,
                "error": "unknown_sections",
                "missing_sections": loaded.missing_sections,
                "available_sections": loaded.available_sections,
            }
        return {
            "path": path,
            "section_ids": section_ids or [],
            "available_sections": loaded.available_sections,
            "content": loaded.passage.content,
        }
