"""Clerk's MCP tool server: thin tools delegating to existing services."""
from __future__ import annotations

import asyncio
import re
import uuid
from collections import Counter
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import HTTPException
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from sqlalchemy import func, or_, select
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
    get_latest_draft_artifact,
    get_latest_draft_artifact_by_workspace_path,
)
from app.database.session import get_session_factory
from app.agent.status_bus import agent_turn_status_bus
from app.database.source_document import SourceDocument
from app.database.workspace_files import (
    get_workspace_file_by_path,
    list_workspace_files_for_project,
)
from app.config import settings
from app.mcp_bridge.auth import (
    ToolAuthError,
    authorize_project_access_with_claims,
    authorize_project_mutation_with_claims,
)
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters
from app.sitewise.cost_plan_consultant_forecast import (
    forecast_consultant_fees_for_markdown,
)
from app.sitewise.cost_plan_workbook import workbook_preview_from_bytes
from app.sitewise.gate import format_overlay_failure, overlay_status
from app.sitewise.knowledge_catalog import (
    applicable_platform_paths,
    catalog_entry_for_path,
    list_platform_knowledge as catalog_platform_knowledge,
    load_sections as load_platform_sections,
    required_paths_by_workflow,
    required_workflows_for_path,
)
from app.storage.project_files import download_project_file
from app.workflows.create_cost_plan import (
    WORKFLOW_TYPE as CREATE_COST_PLAN_WORKFLOW_TYPE,
    sync_cost_plan_revision_artifacts,
)
from app.workflows.consultant_procurement import (
    draft_consultant_procurement_artifact as run_consultant_procurement_artifact,
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
TEXT_SEARCH_MAX_TERMS = 6
TEXT_SEARCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "document",
    "documents",
    "file",
    "files",
    "for",
    "from",
    "in",
    "is",
    "made",
    "of",
    "please",
    "read",
    "the",
    "to",
    "what",
    "with",
}
PLATFORM_SOURCE_TYPES = {"doctrine", "reference"}
PLATFORM_SEARCH_MAX_RESULTS = 20
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


def _is_xlsx_workspace_file(record) -> bool:
    filename = (getattr(record, "filename", "") or "").lower()
    path = (getattr(record, "workspace_path", "") or "").lower()
    return filename.endswith(".xlsx") or path.endswith(".xlsx")


def _project_file_summary(record) -> dict:
    path = record.workspace_path.replace("\\", "/")
    source_document_id = (
        str(record.source_document_id) if record.source_document_id else None
    )
    if source_document_id:
        read_with = "get_document"
    elif _is_xlsx_workspace_file(record):
        read_with = "read_project_workbook"
    else:
        read_with = "read_workspace_file"
    return {
        "kind": "project_file",
        "workspace_path": path,
        "filename": record.filename,
        "size_bytes": record.size_bytes,
        "ingest_status": record.ingest_status,
        "source_document_id": source_document_id,
        "read_with": read_with,
    }


def _path_matches_prefix(path: str, prefix: str) -> bool:
    clean_path = path.replace("\\", "/").rstrip("/")
    clean_prefix = prefix.replace("\\", "/").rstrip("/")
    return clean_path == clean_prefix or clean_path.startswith(clean_prefix + "/")


def _cost_plan_markdown_path(path: str | None) -> str | None:
    if path is None or not path.strip():
        return None
    workspace_path = _tool_workspace_path(path)
    match = re.search(r"(^|/)Cost_Plan_v(\d+)\.draft\.xlsx$", workspace_path)
    if not match:
        return workspace_path
    folder = workspace_path.rsplit("/", maxsplit=1)[0]
    return f"{folder}/cost_plan_v{match.group(2)}.md"


async def _load_cost_plan_draft(session, *, project_id: uuid.UUID, path: str | None):
    workspace_path = _cost_plan_markdown_path(path)
    if workspace_path is not None:
        draft = await get_latest_draft_artifact_by_workspace_path(
            session,
            project_id=project_id,
            workspace_path=workspace_path,
        )
    else:
        draft = await get_latest_draft_artifact(
            session,
            project_id=project_id,
            workflow_type=CREATE_COST_PLAN_WORKFLOW_TYPE,
        )
    if draft is None:
        raise ToolError("cost plan draft not found")
    if draft.workflow_type != CREATE_COST_PLAN_WORKFLOW_TYPE:
        raise ToolError("draft is not a cost plan")
    return draft


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


def _source_document_payload(document: SourceDocument, *, max_chars: int | None) -> dict:
    default_limit = settings.whole_document_content_chars
    content_limit = max_chars if max_chars and max_chars > 0 else default_limit
    content_limit = min(content_limit, default_limit)
    content = document.normalized_content or ""
    returned = content[:content_limit]
    return {
        "kind": "source_document",
        "document_id": str(document.id),
        "filename": document.filename,
        "relative_path": document.relative_path,
        "project": document.project,
        "phase": document.phase,
        "source_type": document.source_type,
        "document_class": document.document_class,
        "metadata": document.document_metadata or {},
        "content": returned,
        "content_chars": len(content),
        "returned_chars": len(returned),
        "content_truncated": len(content) > len(returned),
    }


def _text_search_terms(query: str) -> list[str]:
    terms = [
        term
        for term in re.findall(r"[a-z0-9][a-z0-9_-]*", query.lower())
        if len(term) > 1 and term not in TEXT_SEARCH_STOPWORDS
    ]
    return terms[:TEXT_SEARCH_MAX_TERMS]


def _snippet_excerpt(content: str, start: int, end: int, *, context_chars: int) -> str:
    left = max(0, start - context_chars)
    right = min(len(content), end + context_chars)
    while left > 0 and not content[left - 1].isspace():
        left -= 1
    while right < len(content) and not content[right].isspace():
        right += 1
    excerpt = " ".join(content[left:right].split())
    if left > 0:
        excerpt = "... " + excerpt
    if right < len(content):
        excerpt += " ..."
    return excerpt


def _find_text_snippets(
    content: str,
    *,
    query: str,
    terms: list[str],
    context_chars: int,
    limit: int = 3,
) -> list[dict]:
    haystack = content.lower()
    candidates: list[tuple[int, int, str]] = []
    phrase = query.strip().lower()
    if phrase:
        start = haystack.find(phrase)
        while start >= 0 and len(candidates) < limit * 3:
            candidates.append((start, start + len(phrase), phrase))
            start = haystack.find(phrase, start + max(1, len(phrase)))

    for term in terms:
        start = haystack.find(term)
        while start >= 0 and len(candidates) < limit * 6:
            candidates.append((start, start + len(term), term))
            start = haystack.find(term, start + max(1, len(term)))

    snippets: list[dict] = []
    seen: set[tuple[int, int]] = set()
    for start, end, match in sorted(candidates, key=lambda item: item[0]):
        if (start, end) in seen:
            continue
        seen.add((start, end))
        snippets.append(
            {
                "match": content[start:end],
                "match_term": match,
                "start": start,
                "excerpt": _snippet_excerpt(
                    content,
                    start,
                    end,
                    context_chars=context_chars,
                ),
            }
        )
        if len(snippets) >= limit:
            break
    return snippets


def _project_overlay_gate(project) -> tuple[object, dict]:
    status = overlay_status(
        archetype=project.archetype,
        user_role=project.user_role,
        state=project.state,
        building_class=project.building_class,
        work_type=project.work_type,
    )
    gate = {
        "archetype": project.archetype,
        "building_class": project.building_class,
        "work_type": project.work_type,
        "user_role": project.user_role,
        "state": project.state,
        "ready": status.ready,
        "issues": [issue.model_dump() for issue in status.issues],
    }
    return status, gate


def _platform_overlay_kwargs(project) -> dict[str, str | None]:
    return {
        "archetype": project.archetype,
        "user_role": project.user_role,
        "building_class": project.building_class,
        "work_type": project.work_type,
    }


def _required_platform_paths_for_project(project) -> dict[str, list[str]]:
    return required_paths_by_workflow(**_platform_overlay_kwargs(project))


def _applicable_platform_paths_for_project(
    project,
    *,
    topics: list[str] | None = None,
    include_required: bool = True,
) -> set[str]:
    return applicable_platform_paths(
        **_platform_overlay_kwargs(project),
        topics=topics,
        include_required=include_required,
    )


def _is_platform_passage(passage) -> bool:
    metadata = passage.document_metadata or {}
    return (
        metadata.get("knowledge_scope") == "platform"
        or passage.source_type in PLATFORM_SOURCE_TYPES
    )


def _platform_topics(path: str, metadata: dict | None) -> list[str]:
    entry = catalog_entry_for_path(path)
    if entry is not None:
        return list(entry.topics)
    frontmatter = (metadata or {}).get("frontmatter")
    if isinstance(frontmatter, dict):
        topics = frontmatter.get("topics")
        if isinstance(topics, list):
            return [str(topic) for topic in topics]
    return []


def _platform_title(path: str, filename: str, metadata: dict | None) -> str:
    entry = catalog_entry_for_path(path)
    if entry is not None:
        return entry.title
    frontmatter = (metadata or {}).get("frontmatter")
    if isinstance(frontmatter, dict) and isinstance(frontmatter.get("title"), str):
        return str(frontmatter["title"])
    return filename


def _score_platform_result(
    base_score: float,
    *,
    topics: list[str],
    requested_topics: list[str] | None,
    mandatory_for: list[str],
    source_type: str | None,
) -> float:
    score = base_score
    wanted = {topic.strip().lower() for topic in requested_topics or [] if topic.strip()}
    if wanted and wanted.intersection(topic.lower() for topic in topics):
        score += 0.05
    if mandatory_for:
        score += 0.03
    if source_type == "doctrine":
        score += 0.02
    return round(score, 6)


async def _load_project_source_document(
    session,
    *,
    project_id: uuid.UUID,
    document_id: uuid.UUID | None = None,
    workspace_path: str | None = None,
) -> SourceDocument | None:
    filters = [SourceDocument.project_id == project_id]
    if document_id is not None:
        filters.append(SourceDocument.id == document_id)
    elif workspace_path is not None:
        filters.append(SourceDocument.relative_path == workspace_path)
    else:
        return None

    result = await session.execute(select(SourceDocument).where(*filters).limit(1))
    return result.scalar_one_or_none()


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


async def _publish_draft_artefact(
    turn_id: str | None,
    *,
    draft,
    project_id: uuid.UUID,
) -> None:
    await agent_turn_status_bus.publish(
        turn_id,
        kind="artefact",
        message=draft.title,
        title=draft.title,
        workflowType=draft.workflow_type,
        draftId=str(draft.id),
        projectId=str(project_id),
    )


def _consultant_procurement_status_metadata(source_trace: dict) -> dict:
    project_documents = source_trace.get("project_documents")
    platform_knowledge = source_trace.get("platform_knowledge")
    forecast = source_trace.get("forecast")
    documents = project_documents if isinstance(project_documents, list) else []
    knowledge = platform_knowledge if isinstance(platform_knowledge, list) else []
    forecast_payload = forecast if isinstance(forecast, dict) else {}
    return {
        "document_count": len(documents),
        "knowledge_count": len(knowledge),
        "forecast_used": bool(forecast_payload.get("used")),
        "source_documents": [
            {
                "document_id": item.get("document_id"),
                "filename": item.get("filename"),
                "relative_path": item.get("relative_path"),
                "role": item.get("role"),
            }
            for item in documents
            if isinstance(item, dict)
        ],
        "platform_knowledge": [
            {
                "path": item.get("path"),
                "title": item.get("title"),
                "section": item.get("section"),
            }
            for item in knowledge
            if isinstance(item, dict)
        ],
    }


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
            authorization = await authorize_project_mutation_with_claims(
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
async def list_project_files(
    project_id: str,
    query: str | None = None,
    path_prefix: str | None = None,
    max_results: int = 50,
) -> list[dict]:
    """List stored Clerk project files, including generated drafts and workbooks.

    Use this when the user names a file or artefact that may not be an ingested
    source document. Generated files are project artefacts; they are not
    independent evidence unless their source_document_id points to an ingested
    document.
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
            tool="list_project_files",
            running="Listing project files",
            done="Listed project files",
            error="Project file listing failed",
        ):
            records = await list_workspace_files_for_project(session, project_id=pid)

    query_text = query.strip().lower() if query and query.strip() else None
    prefix = _tool_workspace_path(path_prefix) if path_prefix and path_prefix.strip() else None
    if prefix == ".":
        prefix = None
    result_limit = max(1, min(max_results, 200))
    matches: list[dict] = []
    for record in records:
        path = record.workspace_path.replace("\\", "/")
        if prefix and not _path_matches_prefix(path, prefix):
            continue
        if query_text:
            haystack = f"{path} {record.filename}".lower()
            if query_text not in haystack:
                continue
        matches.append(_project_file_summary(record))
        if len(matches) >= result_limit:
            break
    return matches


@mcp.tool
async def read_project_workbook(
    project_id: str,
    path: str,
    max_rows: int = 80,
) -> dict:
    """Read an Excel workbook stored in Clerk project files as sheet rows.

    This is for generated or uploaded .xlsx project artefacts. It previews cell
    values; it does not make the workbook an ingested source document.
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
            tool="read_project_workbook",
            running="Reading project workbook",
            done="Read project workbook",
            error="Project workbook read failed",
        ):
            workspace_path = _tool_workspace_path(path)
            record = await get_workspace_file_by_path(
                session,
                project_id=pid,
                workspace_path=workspace_path,
            )
            if record is None:
                raise ToolError("project workbook not found")
            if not _is_xlsx_workspace_file(record):
                raise ToolError("project file is not an Excel workbook")
            content = await asyncio.to_thread(
                download_project_file,
                storage_key=record.storage_key,
            )
            preview = workbook_preview_from_bytes(content)

    row_limit = max(1, min(max_rows, 200))
    return {
        "kind": "workbook_preview",
        "filename": record.filename,
        "workspace_path": record.workspace_path.replace("\\", "/"),
        "ingest_status": record.ingest_status,
        "source_document_id": (
            str(record.source_document_id) if record.source_document_id else None
        ),
        "artifact_role": "generated_artifact"
        if record.ingest_status == "generated" and record.source_document_id is None
        else "project_file",
        "sheets": [
            {
                "name": sheet.name,
                "column_count": sheet.column_count,
                "row_count": len(sheet.rows),
                "rows_truncated": len(sheet.rows) > row_limit,
                "rows": sheet.rows[:row_limit],
            }
            for sheet in preview.sheets
        ],
        "warnings": preview.warnings,
    }


@mcp.tool
async def forecast_consultant_fees(
    project_id: str,
    cost_plan_path: str | None = None,
) -> dict:
    """Preview deterministic consultant fee allowances for the current cost plan."""
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
            tool="forecast_consultant_fees",
            running="Forecasting consultant fees",
            done="Forecasted consultant fees",
            error="Consultant fee forecast failed",
        ):
            draft = await _load_cost_plan_draft(
                session,
                project_id=pid,
                path=cost_plan_path,
            )
            forecast = forecast_consultant_fees_for_markdown(
                draft.content_markdown,
                source_path=draft.workspace_path,
            )

    return {
        "kind": "consultant_fee_forecast",
        "draft_id": str(draft.id),
        "version": draft.version,
        "workspace_path": draft.workspace_path,
        **forecast.to_payload(),
    }


@mcp.tool
async def apply_consultant_fee_forecast(
    project_id: str,
    cost_plan_path: str | None = None,
) -> dict:
    """Create a new cost-plan draft with consultant forecast rows applied."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        async with _tool_status(
            _turn_id(authorization),
            tool="apply_consultant_fee_forecast",
            running="Applying consultant fee forecast",
            done="Applied consultant fee forecast",
            error="Consultant fee forecast apply failed",
        ):
            draft = await _load_cost_plan_draft(
                session,
                project_id=pid,
                path=cost_plan_path,
            )
            forecast = forecast_consultant_fees_for_markdown(
                draft.content_markdown,
                source_path=draft.workspace_path,
            )
            updated = await create_draft_revision(
                session,
                draft=draft,
                author_user_id=authorization.claims.user_id,
                content_markdown=forecast.updated_markdown,
                edit_source="agent_consultant_fee_forecast",
            )
            workbook_metadata = await sync_cost_plan_revision_artifacts(
                session,
                project=authorization.project,
                draft=updated,
                markdown=forecast.updated_markdown,
                provenance_updates={
                    "consultant_fee_forecast": forecast.to_payload(),
                },
            )
            await session.commit()

    return {
        "kind": "consultant_fee_forecast_applied",
        "source_draft_id": str(draft.id),
        "draft_id": str(updated.id),
        "version": updated.version,
        "workspace_path": updated.workspace_path,
        "workbook": workbook_metadata,
        "forecast": forecast.to_payload(),
    }


@mcp.tool
async def draft_consultant_procurement_artifact(
    project_id: str,
    discipline: str,
    max_pages: int = 1,
    instructions: str | None = None,
) -> dict:
    """Create a saved request-for-fee-proposal draft for a consultant discipline.

    Use this for natural-language requests such as "draft a request for fee
    proposal", "draft consultant procurement", "prepare an RFP for the
    structural engineer", or "prepare scope for BASIX assessor". The output is
    always a client-issued request for fee proposal, not a consultant-issued fee
    proposal.
    """
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        turn_id = _turn_id(authorization)
        async with _tool_status(
            turn_id,
            tool="draft_consultant_procurement_artifact",
            running=f"Drafting request for fee proposal: {discipline}",
            done="Created consultant procurement draft",
            error="Consultant procurement draft failed",
        ) as extra:
            result = await run_consultant_procurement_artifact(
                session,
                project=authorization.project,
                user_id=authorization.claims.user_id,
                discipline=discipline,
                max_pages=max_pages,
                instructions=instructions,
            )
            extra.update(
                _consultant_procurement_status_metadata(result.source_trace)
            )
            extra["workflowType"] = result.draft.workflow_type
            extra["draftId"] = str(result.draft.id)
            extra["projectId"] = str(pid)
            extra["workspace_path"] = result.draft.workspace_path

    await _publish_draft_artefact(
        turn_id,
        draft=result.draft,
        project_id=pid,
    )
    return {
        "kind": "artefact",
        "title": result.draft.title,
        "discipline": result.discipline,
        "workflow_type": result.draft.workflow_type,
        "workflowType": result.draft.workflow_type,
        "draft_id": str(result.draft.id),
        "draftId": str(result.draft.id),
        "version": result.draft.version,
        "workspace_path": result.draft.workspace_path,
        "project_id": str(pid),
        "projectId": str(pid),
        "source_trace": result.source_trace,
        "message": "Consultant procurement artefact has been created.",
    }


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
async def get_document(
    project_id: str,
    document_id: str | None = None,
    workspace_path: str | None = None,
    max_chars: int | None = None,
) -> dict:
    """Read an ingested source document's extracted text without OCR.

    Use this after search_documents or list_selected_documents when the user asks
    about the contents of an uploaded source file. Source PDFs/DOCX files are not
    exposed on the agent filesystem; this returns the persisted extracted text
    from source_documents.normalized_content.
    """
    if not document_id and not workspace_path:
        raise ToolError("provide document_id or workspace_path")
    if document_id and workspace_path:
        raise ToolError("provide only one of document_id or workspace_path")

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
            tool="get_document",
            running="Reading ingested document text",
            done="Read ingested document text",
            error="Document read failed",
        ):
            document = None
            if document_id:
                try:
                    parsed_document_id = uuid.UUID(document_id)
                except ValueError as exc:
                    raise ToolError("document_id must be a UUID") from exc
                document = await _load_project_source_document(
                    session,
                    project_id=project.id,
                    document_id=parsed_document_id,
                )
            else:
                path = _tool_workspace_path(workspace_path)
                record = await get_workspace_file_by_path(
                    session,
                    project_id=pid,
                    workspace_path=path,
                )
                if record is not None and record.source_document_id is not None:
                    document = await _load_project_source_document(
                        session,
                        project_id=project.id,
                        document_id=record.source_document_id,
                    )
                if document is None:
                    document = await _load_project_source_document(
                        session,
                        project_id=project.id,
                        workspace_path=path,
                    )
                if document is None and record is not None:
                    ingest_status = getattr(record, "ingest_status", "unknown")
                    raise ToolError(
                        f"document text is not available; ingest_status={ingest_status}"
                    )

            if document is None:
                raise ToolError("document not found or not ingested")
            return _source_document_payload(document, max_chars=max_chars)


@mcp.tool
async def find_document_text(
    project_id: str,
    query: str,
    filename_hint: str | None = None,
    max_results: int = 5,
    context_chars: int = 240,
) -> list[dict]:
    """Fast keyword lookup over ingested project document text.

    Use this before semantic search, OCR, or shell/database work for simple
    source-document questions like "what do the specs say about benchtops?".
    It searches source_documents.normalized_content and returns small snippets.
    """
    terms = _text_search_terms(query)
    if not terms:
        raise ToolError("query must include a searchable term")

    result_limit = max(1, min(max_results, 10))
    snippet_context = max(80, min(context_chars, 800))
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
            tool="find_document_text",
            running="Searching ingested document text",
            done="Searched ingested document text",
            error="Ingested document text search failed",
        ):
            content_filters = [
                func.lower(SourceDocument.normalized_content).contains(term)
                for term in terms
            ]
            filters = [SourceDocument.project_id == project.id, or_(*content_filters)]
            if filename_hint and filename_hint.strip():
                hint = filename_hint.strip().lower()
                filters.append(
                    or_(
                        func.lower(SourceDocument.filename).contains(hint),
                        func.lower(SourceDocument.relative_path).contains(hint),
                    )
                )
            stmt = (
                select(SourceDocument)
                .where(*filters)
                .order_by(SourceDocument.updated_at.desc())
                .limit(result_limit * 3)
            )
            rows = (await session.execute(stmt)).scalars().all()

        matches: list[dict] = []
        for document in rows:
            snippets = _find_text_snippets(
                document.normalized_content or "",
                query=query,
                terms=terms,
                context_chars=snippet_context,
            )
            if not snippets:
                continue
            matches.append(
                {
                    "kind": "source_document_match",
                    "document_id": str(document.id),
                    "filename": document.filename,
                    "relative_path": document.relative_path,
                    "document_class": document.document_class,
                    "content_chars": len(document.normalized_content or ""),
                    "snippets": snippets,
                }
            )
            if len(matches) >= result_limit:
                break
        return matches


@mcp.tool
async def write_workspace_file(project_id: str, path: str, content: str) -> dict:
    """Write a UTF-8 scratch file or create a new version of an editable artefact."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
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
                    active_project_id=project.id,
                    # Platform knowledge stays out of evidence search by design:
                    # it arrives through platform knowledge tools so the
                    # evidence-beats-guidance authority stack stays structural.
                    include_platform_knowledge=False,
                ),
                include_neighbours=False,
            )
        return [
            {
                "document_id": str(p.document_id),
                "chunk_id": str(p.chunk_id),
                "document": p.filename,
                "relative_path": p.relative_path,
                "page_or_section": p.page_or_section,
                "snippet": p.content,
                "score": p.score,
            }
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
            status, gate = _project_overlay_gate(project)
            if not status.ready:
                return {
                    "gate": gate,
                    "message": format_overlay_failure(
                        status, workflow="Platform knowledge access"
                    ),
                    "required": {},
                    "available": [],
                }
            required = _required_platform_paths_for_project(project)
            available = await catalog_platform_knowledge(
                session,
                archetype=project.archetype,
                user_role=project.user_role,
                building_class=project.building_class,
                work_type=project.work_type,
                topics=topics,
            )
        return {"gate": gate, "required": required, "available": available}


@mcp.tool
async def search_platform_knowledge(
    project_id: str,
    query: str,
    topics: list[str] | None = None,
    max_results: int = 8,
) -> list[dict]:
    """Semantically search SiteWise platform guidance applicable to this project.

    Use this for construction-management guidance before falling back to
    general model knowledge. Results are platform guidance, not active-project
    evidence; use project document tools first for facts about the active
    project.
    """
    normalized_query = query.strip()
    if not normalized_query:
        raise ToolError("query must not be blank")

    pid = uuid.UUID(project_id)
    result_limit = max(1, min(max_results, PLATFORM_SEARCH_MAX_RESULTS))
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
            tool="search_platform_knowledge",
            running="Searching platform knowledge",
            done="Searched platform knowledge",
            error="Platform knowledge search failed",
        ) as extra:
            status, _gate = _project_overlay_gate(project)
            if not status.ready:
                raise ToolError(
                    format_overlay_failure(
                        status, workflow="Platform knowledge search"
                    )
                )

            allowed_paths = _applicable_platform_paths_for_project(
                project,
                topics=topics,
                include_required=not topics,
            )
            required = _required_platform_paths_for_project(project)
            retriever = DocumentRetriever(session)
            passages = await retriever.retrieve(
                normalized_query,
                filters=RetrievalFilters(
                    platform_knowledge_only=True,
                    phase="reference",
                ),
                limit=result_limit * 4,
                include_neighbours=False,
            )
            results: list[dict] = []
            for passage in passages:
                if not _is_platform_passage(passage):
                    continue
                if passage.relative_path not in allowed_paths:
                    continue
                path = passage.relative_path
                result_topics = _platform_topics(path, passage.document_metadata)
                mandatory_for = required_workflows_for_path(required, path)
                score = _score_platform_result(
                    passage.score,
                    topics=result_topics,
                    requested_topics=topics,
                    mandatory_for=mandatory_for,
                    source_type=passage.source_type,
                )
                results.append(
                    {
                        "path": path,
                        "title": _platform_title(
                            path, passage.filename, passage.document_metadata
                        ),
                        "section": passage.page_or_section,
                        "snippet": passage.content,
                        "score": score,
                        "topics": result_topics,
                        "source_type": passage.source_type,
                        "mandatory": bool(mandatory_for),
                        "mandatory_for": mandatory_for,
                    }
                )
            results.sort(key=lambda item: item["score"], reverse=True)
            extra["result_count"] = min(len(results), result_limit)
            return results[:result_limit]


@mcp.tool
async def read_platform_knowledge(
    project_id: str, path: str, section_ids: list[str] | None = None
) -> dict:
    """Read a platform knowledge document, whole or by targeted sections.

    Use paths and section IDs from list_platform_knowledge or
    search_platform_knowledge. Reading the doctrine without section_ids serves
    its core (authority stack and cross-cutting rules); stage sections (e.g.
    "01-cost", "07-construction") load by section ID. Cite the source path in
    any output that uses this content, and record it as consulted knowledge,
    not project evidence.
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
            tool="read_platform_knowledge",
            running=f"Reading platform knowledge: {path}",
            done=f"Read platform knowledge: {path}",
            error="Platform knowledge read failed",
        ) as extra:
            status, _gate = _project_overlay_gate(project)
            if not status.ready:
                raise ToolError(
                    format_overlay_failure(status, workflow="Platform knowledge read")
                )
            if path not in _applicable_platform_paths_for_project(project):
                raise ToolError(
                    f"Platform document is not available for this project's overlays: {path}. "
                    "Call list_platform_knowledge or search_platform_knowledge for applicable paths."
                )
            loaded = await load_platform_sections(
                session,
                path,
                section_ids,
                max_chars=settings.whole_document_content_chars,
            )
            if loaded is None:
                raise ToolError(
                    f"Platform document not in the corpus: {path}. "
                    "Call list_platform_knowledge or search_platform_knowledge for applicable paths."
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
