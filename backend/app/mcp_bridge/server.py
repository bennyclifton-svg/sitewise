"""Clerk's MCP tool server: thin tools delegating to existing services."""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from collections import Counter
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from openai import OpenAIError
from pydantic import ValidationError
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.workspace_paths import (
    WorkspacePathError,
    normalize_workspace_path,
    project_workspace_root,
    resolve_workspace_path,
)
from app.agent.document_context import (
    SelectedDocumentContextError,
    documents_from_turn_context,
    resolve_selected_turn_documents,
)
from app.database.agent_turn import AgentTurn
from app.database.draft_artifacts import (
    get_draft_artifact,
    get_latest_draft_artifact,
    get_latest_draft_artifact_by_workspace_path,
)
from app.projects.artefact_adapters import revise_workflow_artefact
from app.projects.artefact_blocks import (
    ArtefactBlockOperation,
    apply_block_operations,
    markdown_blocks,
)
from app.projects.project_knowledge import (
    ProjectObjectKind,
    SharedProjectObjectConflict,
    SharedProjectObjectUpdate,
    get_shared_project_object,
    list_shared_project_objects,
    write_shared_project_object,
)
from app.projects.dependency_offers import (
    accept_dependency_offer,
    enrich_dependency_offers,
    reject_dependency_offer_entries,
)
from app.projects.document_register import (
    DocumentRegisterRow,
    list_document_register_rows,
    search_document_register_rows,
)
from app.projects.classification_override import (
    DocumentClassificationInvalid,
    DocumentClassificationNotFound,
    set_document_classification as set_document_classification_service,
)
from app.projects.artefact_revisions import (
    ArtefactPolicyViolation,
    ArtefactRevisionConflict,
)
from app.database.session import get_session_factory
from app.agent.status_bus import agent_turn_status_bus
from app.database.source_document import SourceDocument
from app.database.workspace_files import (
    get_workspace_file_by_path,
    list_workspace_files_for_project,
    search_workspace_files_for_project,
)
from app.config import settings
from app.mcp_bridge.auth import (
    ToolAuthError,
    authorize_project_access_with_claims,
    authorize_project_mutation_with_claims,
)
from app.agent.mutation_intent import PROFILE_MUTATION_SCOPE
from app.projects.profile import (
    ProfileDependencyConflict,
    ProfileRevisionConflict,
    ProfileValidationError,
    apply_profile_patch,
    profile_options,
    read_profile,
)
from app.projects.profile_proposals import (
    ProfileProposalNotFound,
    ProfileProposalRevisionConflict,
    ProfileProposalStateConflict,
    accept_profile_proposal,
    propose_project_profile_change as persist_profile_proposal,
    reject_profile_proposal,
    should_auto_apply_proposal,
)
from app.projects.decisions import (
    DecisionLockedConflict,
    DecisionNotFound,
    DecisionRevisionConflict,
    DecisionSetRevisionConflict,
    DecisionValidationError,
    get_project_decision as read_project_decision,
    list_project_decisions as read_project_decisions,
    lock_project_decision as persist_decision_lock,
    unlock_project_decision as persist_decision_unlock,
    update_project_decision as persist_decision_update,
)
from app.projects.snapshot import get_project_snapshot as read_project_snapshot
from app.projects.generation_context import resolve_project_generation_context
from app.projects.document_selections import (
    SelectionRevisionConflict,
    SelectionValidationError,
    read_selection as read_document_selection,
    replace_selection as persist_document_selection,
    lock_workflow_inputs,
)
from app.schemas.document_selections import QuoteCandidateInput
from app.projects.workflow_capabilities import (
    CONSULTANT_PROCUREMENT,
    TRANSMITTAL,
    capability_block_message,
    workflow_capabilities,
)
from app.cost_plan.dependencies import dependency_snapshot as cost_dependency_snapshot
from app.cost_plan.schemas import CostItemInput, CostPlanOperation, CostPlanState
from app.cost_plan.consultant_appointment import (
    ConsultantAppointmentError,
    appoint_consultant as persist_consultant_appointment,
)
from app.cost_plan.service import (
    apply_external_proposal,
    get_cost_plan as read_typed_cost_plan,
    apply_cost_plan_operations as persist_cost_operations,
    refresh_cost_plan as persist_cost_refresh,
    set_contingency as persist_cost_contingency,
    set_cost_plan_assumption as persist_cost_assumption,
    upsert_cost_item as persist_cost_item,
)
from app.cost_plan.workbook_rebuild import schedule_cost_plan_workbook_rebuild
from app.programme.schemas import ProgrammeOperation, ProgrammeViewUpdate
from app.programme.service import (
    ProgrammeNotFound,
    ProgrammeRevisionConflict,
    apply_programme_operations as persist_programme_operations,
    ensure_programme as persist_ensure_programme,
    get_programme as read_programme,
    set_programme_view as persist_programme_view,
)
from app.mcp_bridge.tender_cost_handoff import map_tender_handoff
from app.schemas.profile_proposals import ProfileEvidenceReference
from app.schemas.projects import ProjectProfilePatch
from app.schemas.workflow_runs import WorkflowRunStartRequest, WorkflowRunView
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters
from app.sitewise.cost_plan_consultant_forecast import (
    forecast_consultant_fees_for_markdown,
)
from app.sitewise.cost_plan_budget_forecast import (
    AdoptedBudgetForecastError,
    align_forecast_items_to_existing,
    build_adopted_budget_forecast,
)
from app.sitewise.cost_plan_workbook import workbook_preview_from_bytes
from app.sitewise.markdown_sections import normalize_draft_markdown
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
    NonConsultantDiscipline,
    draft_consultant_procurement_artifact as run_consultant_procurement_artifact,
    normalise_discipline as _normalise_consultant_discipline,
)
from app.workflows.trade_procurement import normalise_trade_target
from app.workflows.transmittal import WORKFLOW_TYPE as TRANSMITTAL_WORKFLOW_TYPE
from app.workflows.create_pmp import _upstream_failure_message
from app.workflows.runs import (
    WorkflowRunCapabilityConflict,
    WorkflowRunConflict,
    WorkflowRunNotFound,
    cancel_workflow_run as persist_workflow_cancellation,
    get_workflow_run as read_workflow_run,
    start_workflow_run as persist_workflow_run,
)
from app.web_research.attachments import (
    find_official_attachment,
    persist_official_attachment,
    web_source_from_attachment,
)
from app.web_research.factory import WebResearchDisabled, get_web_research_service
from app.web_research.fetcher import WebFetchError
from app.web_research.nsw_legislation import html_view_url, instrument_id_from_url
from app.web_research.service import WebSearchProviderError, _source_authority
from tender.router import (
    get_comparison_detail,
    list_comparisons,
)
from tender.models import TenderAnalysisResult, TenderJob, TenderReport
from tender.services import matrix, qa
from tender.services import intake as tender_intake
from tender.services.project_context_adapter import (
    ContextRevisionConflict,
    ContextValidationError,
    ProjectContextAdapter,
)
from tender.schemas import TenderIntakeRequest
from tender.services.cost_handoff import (
    TenderCostHandoffError,
    approved_tender_cost_handoff,
)
from tender.services.progress import FAILED_JOB_DETAIL

mcp = FastMCP("clerk", mask_error_details=True)

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
            _document_summary(document) for document in getattr(quote, "documents", [])
        ],
    }


def _job_summary(job: TenderJob) -> dict:
    return {
        "id": str(job.id),
        "kind": job.kind,
        "status": job.status,
        "attempts": job.attempts,
        "quote_id": str(job.quote_id) if job.quote_id else None,
        "last_error": FAILED_JOB_DETAIL if job.last_error else None,
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
    elif any(
        getattr(quote, "stage", "intake") != "intake" for quote in comparison.quotes
    ):
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
    candidates = [
        candidate for record in records if (candidate := _candidate_document(record))
    ]
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


def _is_cost_plan_markdown_workspace_file(record) -> bool:
    path = (getattr(record, "workspace_path", "") or "").replace("\\", "/").lower()
    folder, _, filename = path.rpartition("/")
    return (
        folder.endswith("/01-cost")
        and filename.startswith("cost_plan_v")
        and filename.endswith(".md")
    )


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
    summary = {
        "kind": "project_file",
        "workspace_path": path,
        "filename": record.filename,
        "size_bytes": record.size_bytes,
        "ingest_status": record.ingest_status,
        "source_document_id": source_document_id,
        "read_with": read_with,
    }
    metadata = (
        getattr(getattr(record, "source_document", None), "document_metadata", None)
        or {}
    )
    if metadata:
        summary["document_metadata"] = {
            key: metadata.get(key)
            for key in (
                "document_number",
                "title",
                "revision",
                "discipline",
                "metadata_confidence",
            )
            if metadata.get(key)
        }
    return summary


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


async def _sync_cost_plan_workbook(
    session: AsyncSession,
    *,
    project: Any,
    state: CostPlanState,
) -> dict[str, Any]:
    if state.artefact_revision_id is None:
        raise ToolError("updated Cost Plan revision was not found")
    draft = await get_draft_artifact(session, state.artefact_revision_id)
    if draft is None:
        raise ToolError("updated Cost Plan revision was not found")
    return await sync_cost_plan_revision_artifacts(
        session,
        project=project,
        draft=draft,
        typed_state=state,
    )


def _turn_id(authorization) -> str | None:
    return str(authorization.claims.turn_id) if authorization.claims.turn_id else None


def _document_register_summary(row: DocumentRegisterRow) -> dict[str, Any]:
    return row.model_dump(mode="json")


def _document_register_ids(values: list[str] | None) -> list[uuid.UUID]:
    parsed: list[uuid.UUID] = []
    for value in values or []:
        try:
            parsed.append(uuid.UUID(value))
        except (TypeError, ValueError) as exc:
            raise ToolError(f"invalid document register id: {value}") from exc
    if len(set(parsed)) != len(parsed):
        raise ToolError("A document register id was included more than once.")
    return parsed


async def _active_selection_turn(session: AsyncSession, authorization) -> AgentTurn:
    turn_id = authorization.claims.turn_id
    if turn_id is None:
        raise ToolError("document selection requires a durable agent turn")
    turn = await session.get(AgentTurn, turn_id, with_for_update=True)
    if (
        turn is None
        or turn.project_id != authorization.claims.project_id
        or turn.user_id != authorization.claims.user_id
        or turn.state != "active"
        or turn.expires_at <= datetime.now(UTC)
    ):
        raise ToolError("agent turn is revoked or expired")
    return turn


def _coerce_json_object(value: Any, *, field_name: str) -> dict[str, Any]:
    """Accept dicts or JSON-object strings from MCP clients that stringify args."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ToolError(f"{field_name} must be a JSON object: {exc.msg}") from exc
        if isinstance(parsed, dict):
            return parsed
    raise ToolError(f"{field_name} must be a JSON object")


def _coerce_json_object_list(value: Any, *, field_name: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ToolError(f"{field_name} must be a JSON array: {exc.msg}") from exc
        value = parsed
    if not isinstance(value, list):
        raise ToolError(f"{field_name} must be a JSON array of objects")
    objects: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if isinstance(item, dict):
            objects.append(item)
            continue
        if isinstance(item, str):
            try:
                parsed_item = json.loads(item)
            except json.JSONDecodeError as exc:
                raise ToolError(
                    f"{field_name}[{index}] must be a JSON object: {exc.msg}"
                ) from exc
            if isinstance(parsed_item, dict):
                objects.append(parsed_item)
                continue
        raise ToolError(f"{field_name}[{index}] must be a JSON object")
    return objects


def _profile_tool_error(exc: Exception) -> ToolError:
    if isinstance(exc, ProfileRevisionConflict):
        return ToolError(
            "profile_revision_conflict: "
            f"expected={exc.expected_revision}, current={exc.current_revision}"
        )
    if isinstance(exc, ProfileDependencyConflict):
        return ToolError("profile_dependency_conflict: " + ", ".join(exc.fields))
    if isinstance(exc, ProfileProposalRevisionConflict):
        return ToolError(
            "profile_proposal_revision_conflict: "
            f"proposal={exc.proposal_revision}, current={exc.current_revision}"
        )
    if isinstance(exc, ProfileProposalStateConflict):
        return ToolError(f"profile_proposal_state_conflict: {exc.state}")
    if isinstance(exc, ProfileProposalNotFound):
        return ToolError("profile proposal not found")
    if isinstance(exc, ProfileValidationError):
        return ToolError("invalid project profile: " + "; ".join(exc.errors))
    if isinstance(exc, ValidationError):
        return ToolError(f"invalid project profile request: {exc}")
    return ToolError(str(exc))


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
    for item in sorted(
        path.iterdir(), key=lambda entry: (not entry.is_dir(), entry.name.lower())
    ):
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


def _source_document_payload(
    document: SourceDocument, *, max_chars: int | None
) -> dict:
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
        "knowledge_scope": (document.document_metadata or {}).get("knowledge_scope"),
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
        state=project.state,
        building_class=project.building_class,
        work_type=project.work_type,
    )
    gate = {
        "archetype": project.archetype,
        "building_class": project.building_class,
        "work_type": project.work_type,
        "state": project.state,
        "ready": status.ready,
        "issues": [issue.model_dump() for issue in status.issues],
    }
    return status, gate


def _platform_overlay_kwargs(project) -> dict[str, object]:
    from app.sitewise.archetype_bridge import (
        effective_taxonomy,
        effective_work_scopes,
    )

    if getattr(project, "building_class", None) is None:
        return {
            "archetype": project.archetype,
            "building_class": None,
            "work_type": None,
        }
    taxonomy = effective_taxonomy(project)
    return {
        "archetype": project.archetype,
        "building_class": taxonomy.building_class,
        "work_type": taxonomy.work_type,
        "subclasses": taxonomy.subclasses,
        "work_scopes": effective_work_scopes(project),
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
    wanted = {
        topic.strip().lower() for topic in requested_topics or [] if topic.strip()
    }
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
        "delivered_at": latest.delivered_at.isoformat()
        if latest.delivered_at
        else None,
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


def _clip_status_text(value: str, *, max_len: int = 72) -> str:
    text = " ".join(value.split())
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 1]}…"


def _activity_message(verb: str, *, subject: str | None = None) -> str:
    if subject and subject.strip():
        return f"{verb} · {_clip_status_text(subject.strip())}"
    return verb


def _document_list_subject(filenames: list[str], *, limit: int = 2) -> str | None:
    names = [_clip_status_text(name, max_len=48) for name in filenames if name.strip()]
    if not names:
        return None
    shown = ", ".join(names[:limit])
    remainder = len(names) - limit
    if remainder > 0:
        return f"{shown} +{remainder} more"
    return shown


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
        payload = dict(extra)
        message = payload.pop("message", done)
        if not isinstance(message, str) or not message.strip():
            message = done
        await agent_turn_status_bus.publish(
            turn_id,
            message=message,
            tool=tool,
            state="done",
            **payload,
        )


@mcp.tool
async def get_project_profile(project_id: str) -> dict:
    """Read the confirmed revisioned Project Profile for the active project."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        return read_profile(authorization.project).model_dump(mode="json")


@mcp.tool
async def get_project_profile_options(project_id: str) -> dict:
    """Return valid Project Profile taxonomy and setup options."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            await authorize_project_access_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        return profile_options()


@mcp.tool
async def get_project_snapshot(project_id: str) -> dict:
    """Read the deterministic Project Snapshot shared by agent and manual workflows."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        snapshot = await read_project_snapshot(
            session,
            project_id=pid,
            owner_user_id=authorization.project.owner_user_id,
        )
        return snapshot.model_dump(mode="json")


@mcp.tool
async def get_project_next_actions(project_id: str) -> list[dict[str, Any]]:
    """Return deterministic next actions with blocking facts and exact routes/tools."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        snapshot = await read_project_snapshot(
            session,
            project_id=pid,
            owner_user_id=authorization.project.owner_user_id,
        )
        return [item.model_dump(mode="json") for item in snapshot.next_actions]


@mcp.tool
async def get_workflow_capabilities(project_id: str) -> dict:
    """Return authoritative workflow support, missing inputs, and coverage limits."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        snapshot = await read_project_snapshot(
            session,
            project_id=pid,
            owner_user_id=authorization.project.owner_user_id,
        )
        return workflow_capabilities(snapshot).model_dump(mode="json")


_SHARED_OBJECT_KINDS = frozenset(
    {
        "consultant",
        "stakeholder",
        "scope_item",
        "ffe_item",
        "accommodation_space",
        "cost_item",
        "milestone",
        "procurement_package",
        "project_decision",
    }
)


def _parse_shared_object_kind(kind: str) -> ProjectObjectKind:
    if kind not in _SHARED_OBJECT_KINDS:
        raise ToolError(f"invalid shared object kind: {kind}")
    return kind  # type: ignore[return-value]


@mcp.tool
async def list_shared_project_knowledge(
    project_id: str,
    kind: str | None = None,
) -> list[dict]:
    """List revisioned shared project objects used across artefacts."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        typed_kind = _parse_shared_object_kind(kind) if kind is not None else None
        return [
            item.model_dump(mode="json")
            for item in list_shared_project_objects(
                authorization.project, kind=typed_kind
            )
        ]


@mcp.tool
async def get_shared_project_knowledge(
    project_id: str,
    kind: str,
    object_id: str,
) -> dict:
    """Read one shared project object by kind and id."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        item = get_shared_project_object(
            authorization.project,
            kind=_parse_shared_object_kind(kind),
            object_id=object_id,
        )
        if item is None:
            raise ToolError("Shared project object not found")
        return item.model_dump(mode="json")


@mcp.tool
async def upsert_shared_project_knowledge(
    project_id: str,
    kind: str,
    object_id: str,
    expected_revision: int,
    value: dict,
    user_protected: bool = False,
) -> dict:
    """Create or update one shared project object used across artefacts.

    For FFE schedule rows use kind=ffe_item with a stable slug object_id and a
    value dict (item, location, quantity, finish, model, dimensions, supplier,
    status, package, notes). Missing fields may be "TBC".
    For Accommodation Schedule rows use kind=accommodation_space with a stable
    slug object_id and a value dict (space, level, area, characteristics,
    status). Missing fields may be "TBC". status "removed" deletes the row
    from the schedule; use "Demolished" when the space is coming out of the
    building. Put dimensions and other notes in characteristics — there is
    no dimensions or notes column.
    """
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
            result = await write_shared_project_object(
                session,
                project=authorization.project,
                kind=_parse_shared_object_kind(kind),
                object_id=object_id,
                update=SharedProjectObjectUpdate(
                    expected_revision=expected_revision,
                    value=value,
                    user_protected=user_protected,
                ),
                source="ai",
            )
            await session.commit()
        except SharedProjectObjectConflict as exc:
            raise ToolError(str(exc)) from exc
        except (ToolAuthError, ValueError, LookupError) as exc:
            raise ToolError(str(exc)) from exc
    return result.model_dump(mode="json")


@mcp.tool
async def list_dependency_update_offers(project_id: str) -> list[dict]:
    """List pending cross-artefact dependency update offers for review."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        offers = await enrich_dependency_offers(
            session,
            project=authorization.project,
            owner_user_id=authorization.project.owner_user_id,
        )
        return [item.model_dump(mode="json") for item in offers]


@mcp.tool
async def accept_dependency_update_offer(
    project_id: str,
    offer_id: str,
    artefact_types: list[str],
) -> dict:
    """Accept selected dependency update offer artefacts; never overwrites protected facts."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
            result = await accept_dependency_offer(
                session,
                project=authorization.project,
                offer_id=offer_id,
                artefact_types=artefact_types,
                author_user_id=authorization.project.owner_user_id,
            )
            await session.commit()
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        except LookupError as exc:
            raise ToolError(str(exc)) from exc
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        return result.model_dump(mode="json")


@mcp.tool
async def reject_dependency_update_offer(
    project_id: str,
    offer_id: str,
    artefact_types: list[str] | None = None,
) -> dict:
    """Reject/dismiss dependency update offer entries without changing artefacts."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
            reject_dependency_offer_entries(
                authorization.project,
                offer_id=offer_id,
                artefact_types=artefact_types,
            )
            await session.commit()
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        except LookupError as exc:
            raise ToolError(str(exc)) from exc
        return {"status": "rejected", "offer_id": offer_id}


_MCP_WORKFLOW_CAPABILITIES = {
    "create_project_plan": "create_pmp",
    "refresh_project_plan": "update_pmp",
    "create_cost_plan": "create_cost_plan",
    "refresh_cost_plan": "refresh_cost_plan",
    "process_invoices": "refresh_cost_plan",
    "consultant_procurement": "consultant_procurement",
    "contractor_eoi": "contractor_eoi",
    "trade_procurement": "trade_procurement",
    TRANSMITTAL_WORKFLOW_TYPE: TRANSMITTAL,
}

_ARTEFACT_WORKFLOW_FOR_LAUNCH = {
    "refresh_project_plan": "create_pmp",
    "refresh_cost_plan": "create_cost_plan",
    "process_invoices": "create_cost_plan",
}


def _current_artefact_version(snapshot: object, workflow_type: str) -> int | None:
    artefact_workflow = _ARTEFACT_WORKFLOW_FOR_LAUNCH.get(workflow_type)
    if artefact_workflow is None:
        return None
    artefacts = getattr(snapshot, "latest_artefacts", None) or []
    for artefact in artefacts:
        if getattr(artefact, "workflow_type", None) == artefact_workflow:
            version = getattr(artefact, "version", None)
            if isinstance(version, int) and version >= 1:
                return version
    return None


def _normalise_optional_workflow_text(
    value: str | None,
    *,
    field: str,
    maximum: int,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ToolError(f"{field} must be text")
    normalised = " ".join(value.split())
    if not normalised:
        return None
    if len(normalised) > maximum:
        raise ToolError(f"{field} must be {maximum} characters or fewer")
    return normalised


async def _start_mcp_workflow(
    *,
    project_id: str,
    workflow_type: str,
    idempotency_key: str,
    expected_snapshot_fingerprint: str,
    expected_profile_revision: int,
    expected_decision_set_revision: int,
    expected_artefact_version: int | None = None,
    chat_model: str | None = None,
    parameters: dict | None = None,
) -> dict:
    pid = uuid.UUID(project_id)
    snapshot_refreshed = False
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            snapshot = await read_project_snapshot(
                session,
                project_id=pid,
                owner_user_id=authorization.project.owner_user_id,
            )
            capability_name = _MCP_WORKFLOW_CAPABILITIES.get(workflow_type)
            if capability_name is not None:
                message = capability_block_message(snapshot, capability_name)
                if message:
                    raise WorkflowRunCapabilityConflict(message)

            async def _persist(
                current_snapshot,
                *,
                fingerprint,
                profile,
                decisions,
                artefact_version,
            ):
                request = WorkflowRunStartRequest(
                    idempotency_key=idempotency_key,
                    expected_snapshot_fingerprint=fingerprint,
                    expected_profile_revision=profile,
                    expected_decision_set_revision=decisions,
                    expected_artefact_version=artefact_version,
                    turn_id=authorization.claims.turn_id,
                    chat_model=chat_model,
                    parameters=parameters or {},
                )
                return await persist_workflow_run(
                    session,
                    project=authorization.project,
                    user_id=authorization.claims.user_id,
                    workflow_type=workflow_type,
                    request=request,
                    snapshot=current_snapshot,
                )

            try:
                run, _created = await _persist(
                    snapshot,
                    fingerprint=expected_snapshot_fingerprint,
                    profile=expected_profile_revision,
                    decisions=expected_decision_set_revision,
                    artefact_version=expected_artefact_version,
                )
            except WorkflowRunCapabilityConflict:
                # The agent froze its expectations when the turn began. A turn
                # that mutates the profile — accepting a proposal, then queueing
                # the artefact the user just asked for — invalidates its own
                # expectations before it gets to launch. Re-read once and retry
                # rather than dead-ending the user's request; a second conflict
                # means something outside this turn is writing, which the user
                # does need to hear about.
                snapshot = await read_project_snapshot(
                    session,
                    project_id=pid,
                    owner_user_id=authorization.project.owner_user_id,
                )
                snapshot_refreshed = True
                current_artefact_version = _current_artefact_version(
                    snapshot, workflow_type
                )
                run, _created = await _persist(
                    snapshot,
                    fingerprint=snapshot.content_fingerprint,
                    profile=snapshot.profile.profile_revision,
                    decisions=snapshot.decisions.set_revision,
                    artefact_version=(
                        current_artefact_version
                        if current_artefact_version is not None
                        else expected_artefact_version
                    ),
                )
            await session.commit()
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        except (
            ValidationError,
            WorkflowRunConflict,
            WorkflowRunCapabilityConflict,
        ) as exc:
            raise ToolError(f"workflow_run_conflict: {exc}") from exc
    await agent_turn_status_bus.publish(
        _turn_id(authorization),
        kind="resource",
        message="Workflow queued",
        projectId=str(pid),
        resourceType="workflow_run",
        resourceId=str(run.id),
        action="queued",
        workflowType=workflow_type,
    )
    payload = WorkflowRunView.model_validate(run).model_dump(mode="json")
    payload["snapshot_refreshed"] = snapshot_refreshed
    return payload


@mcp.tool
async def start_project_plan(
    project_id: str,
    idempotency_key: str,
    expected_snapshot_fingerprint: str,
    expected_profile_revision: int,
    expected_decision_set_revision: int,
    chat_model: str | None = None,
) -> dict:
    """Queue Project Plan creation from an exact frozen project snapshot."""
    return await _start_mcp_workflow(
        project_id=project_id,
        workflow_type="create_project_plan",
        idempotency_key=idempotency_key,
        expected_snapshot_fingerprint=expected_snapshot_fingerprint,
        expected_profile_revision=expected_profile_revision,
        expected_decision_set_revision=expected_decision_set_revision,
        chat_model=chat_model,
    )


@mcp.tool
async def refresh_project_plan(
    project_id: str,
    idempotency_key: str,
    expected_snapshot_fingerprint: str,
    expected_profile_revision: int,
    expected_decision_set_revision: int,
    expected_artefact_version: int,
    chat_model: str | None = None,
) -> dict:
    """Queue a Project Plan refresh against an exact base artefact version."""
    return await _start_mcp_workflow(
        project_id=project_id,
        workflow_type="refresh_project_plan",
        idempotency_key=idempotency_key,
        expected_snapshot_fingerprint=expected_snapshot_fingerprint,
        expected_profile_revision=expected_profile_revision,
        expected_decision_set_revision=expected_decision_set_revision,
        expected_artefact_version=expected_artefact_version,
        chat_model=chat_model,
    )


@mcp.tool
async def start_cost_plan(
    project_id: str,
    idempotency_key: str,
    expected_snapshot_fingerprint: str,
    expected_profile_revision: int,
    expected_decision_set_revision: int,
    chat_model: str | None = None,
) -> dict:
    """Queue Cost Plan creation from an exact frozen project snapshot."""
    return await _start_mcp_workflow(
        project_id=project_id,
        workflow_type="create_cost_plan",
        idempotency_key=idempotency_key,
        expected_snapshot_fingerprint=expected_snapshot_fingerprint,
        expected_profile_revision=expected_profile_revision,
        expected_decision_set_revision=expected_decision_set_revision,
        chat_model=chat_model,
    )


@mcp.tool
async def refresh_cost_plan(
    project_id: str,
    idempotency_key: str,
    expected_snapshot_fingerprint: str,
    expected_profile_revision: int,
    expected_decision_set_revision: int,
    expected_artefact_version: int,
    proposed_items: list[dict],
    reconcile_evidence: bool = True,
) -> dict:
    """Refresh a typed Cost Plan from received proposals plus any explicit items.

    With reconcile_evidence enabled, the durable worker reads ingested fee and
    main-works proposals, verifies their stated totals, maps them to typed rows,
    and publishes a reviewable proposed revision. Locked/manual rows are
    preserved as explicit conflicts; an empty evidence result cannot publish a
    misleading no-op revision.
    """
    validated_items = [
        CostItemInput.model_validate(item).model_dump(mode="json")
        for item in proposed_items
    ]
    return await _start_mcp_workflow(
        project_id=project_id,
        workflow_type="refresh_cost_plan",
        idempotency_key=idempotency_key,
        expected_snapshot_fingerprint=expected_snapshot_fingerprint,
        expected_profile_revision=expected_profile_revision,
        expected_decision_set_revision=expected_decision_set_revision,
        expected_artefact_version=expected_artefact_version,
        parameters={
            "proposed_items": validated_items,
            "reconcile_evidence": reconcile_evidence,
        },
    )


@mcp.tool
async def process_invoices(
    project_id: str,
    idempotency_key: str,
    expected_snapshot_fingerprint: str,
    expected_profile_revision: int,
    expected_decision_set_revision: int,
    expected_artefact_version: int,
    source_document_ids: list[str] | None = None,
) -> dict:
    """Book named or all ingested invoices into the canonical Cost Plan ledger.

    Omit source_document_ids to process every eligible project invoice. The
    worker validates arithmetic in Python, skips exact duplicates, withholds
    ambiguous allocations for review, and republishes the existing workbook
    layout without changing budget or approved-contract values.
    """
    try:
        normalized_source_ids = (
            [str(uuid.UUID(value)) for value in source_document_ids]
            if source_document_ids is not None
            else None
        )
    except ValueError as exc:
        raise ToolError("source_document_ids must contain UUIDs") from exc
    return await _start_mcp_workflow(
        project_id=project_id,
        workflow_type="process_invoices",
        idempotency_key=idempotency_key,
        expected_snapshot_fingerprint=expected_snapshot_fingerprint,
        expected_profile_revision=expected_profile_revision,
        expected_decision_set_revision=expected_decision_set_revision,
        expected_artefact_version=expected_artefact_version,
        parameters={"source_document_ids": normalized_source_ids},
    )


@mcp.tool
async def get_cost_plan(project_id: str, version: int | None = None) -> dict:
    """Read one canonical typed Cost Plan version for the authorized project."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            state = await read_typed_cost_plan(
                session,
                project_id=pid,
                owner_user_id=authorization.project.owner_user_id,
                version=version,
            )
        except (ToolAuthError, ValueError, LookupError) as exc:
            raise ToolError(str(exc)) from exc
    return state.model_dump(mode="json")


@mcp.tool
async def get_programme(project_id: str) -> dict:
    """Read the current typed Programme version for the authorized project."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            state = await read_programme(session, project_id=pid)
        except (ToolAuthError, ValueError, LookupError) as exc:
            raise ToolError(str(exc)) from exc
    return state.model_dump(mode="json")


@mcp.tool
async def ensure_programme(project_id: str) -> dict:
    """Create the default three-stage Programme if the project has none."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            state = await persist_ensure_programme(
                session,
                project=authorization.project,
                author_user_id=authorization.claims.user_id,
            )
            await session.commit()
        except (ToolAuthError, ValueError, LookupError) as exc:
            raise ToolError(str(exc)) from exc
    return state.model_dump(mode="json")


@mcp.tool
async def apply_programme_operations(
    project_id: str,
    expected_base_version: int,
    operations: list[ProgrammeOperation],
) -> dict:
    """Apply up to 80 structured Programme operations in one revision.

    Each item is ADD/UPDATE/DELETE/MOVE with target_type stage|activity|milestone.
    Put name, parent_key, start_date, duration_days, and optional predecessor_key
    inside values, not at the top level. Example ADD:
    {"operation":"ADD","target_type":"activity","values":{"name":"Concept design","parent_key":"planning","start_date":"2026-08-16","duration_days":42}}.
    Seeded stages are planning, procurement, and delivery. Sequential
    activities in a stage must set predecessor_key to the previous activity
    so Python can chain finish-to-start dates. Omit the link only for
    genuinely concurrent work. Do not invent calendar finish dates.
    """
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
            state = await persist_programme_operations(
                session,
                project=authorization.project,
                author_user_id=authorization.claims.user_id,
                expected_base_version=expected_base_version,
                operations=operations,
            )
            await session.commit()
        except (
            ToolAuthError,
            ValidationError,
            ValueError,
            LookupError,
            ProgrammeNotFound,
            ProgrammeRevisionConflict,
        ) as exc:
            raise ToolError(str(exc)) from exc
    return {"kind": "programme_operations_applied", "state": state.model_dump(mode="json")}


@mcp.tool
async def set_programme_view(
    project_id: str,
    expected_base_version: int,
    view_scale: str | None = None,
    pmp_embed_visible: bool | None = None,
) -> dict:
    """Update the Programme Gantt scale or whether it appears in the PMP."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            state = await persist_programme_view(
                session,
                project=authorization.project,
                author_user_id=authorization.claims.user_id,
                expected_base_version=expected_base_version,
                update=ProgrammeViewUpdate(
                    view_scale=view_scale,  # type: ignore[arg-type]
                    pmp_embed_visible=pmp_embed_visible,
                ),
            )
            await session.commit()
        except (
            ToolAuthError,
            ValidationError,
            ValueError,
            LookupError,
            ProgrammeNotFound,
            ProgrammeRevisionConflict,
        ) as exc:
            raise ToolError(str(exc)) from exc
    return state.model_dump(mode="json")


@mcp.tool
async def upsert_cost_item(
    project_id: str,
    expected_base_version: int,
    item: dict,
) -> dict:
    """Create a proposed revision changing only one validated typed cost item."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            snapshot = await read_project_snapshot(
                session,
                project_id=pid,
                owner_user_id=authorization.project.owner_user_id,
            )
            result = await persist_cost_item(
                session,
                project=authorization.project,
                author_user_id=authorization.claims.user_id,
                expected_base_version=expected_base_version,
                item=CostItemInput.model_validate(item),
                current_snapshot=snapshot,
            )
            await session.commit()
            workbook_metadata = schedule_cost_plan_workbook_rebuild(
                authorization.project.id, result.state.version
            )
        except (
            ToolAuthError,
            ValidationError,
            ValueError,
            RuntimeError,
            LookupError,
        ) as exc:
            raise ToolError(str(exc)) from exc
    return {**result.model_dump(mode="json"), "workbook": workbook_metadata}


@mcp.tool
async def set_contingency(
    project_id: str,
    expected_base_version: int,
    percent: str,
) -> dict:
    """Create a proposed revision with a new deterministic contingency percentage."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            snapshot = await read_project_snapshot(
                session,
                project_id=pid,
                owner_user_id=authorization.project.owner_user_id,
            )
            result = await persist_cost_contingency(
                session,
                project=authorization.project,
                author_user_id=authorization.claims.user_id,
                expected_base_version=expected_base_version,
                percent=Decimal(percent),
                current_snapshot=snapshot,
            )
            await session.commit()
            workbook_metadata = schedule_cost_plan_workbook_rebuild(
                authorization.project.id, result.state.version
            )
        except (ToolAuthError, ValueError, RuntimeError, LookupError) as exc:
            raise ToolError(str(exc)) from exc
    return {**result.model_dump(mode="json"), "workbook": workbook_metadata}


@mcp.tool
async def set_cost_plan_assumption(
    project_id: str,
    expected_base_version: int,
    key: str,
    value: str,
) -> dict:
    """Create a proposed revision changing one explicit Cost Plan assumption."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            snapshot = await read_project_snapshot(
                session,
                project_id=pid,
                owner_user_id=authorization.project.owner_user_id,
            )
            result = await persist_cost_assumption(
                session,
                project=authorization.project,
                author_user_id=authorization.claims.user_id,
                expected_base_version=expected_base_version,
                key=key,
                value=value,
                current_snapshot=snapshot,
            )
            await session.commit()
            workbook_metadata = schedule_cost_plan_workbook_rebuild(
                authorization.project.id, result.state.version
            )
        except (ToolAuthError, ValueError, RuntimeError, LookupError) as exc:
            raise ToolError(str(exc)) from exc
    return {**result.model_dump(mode="json"), "workbook": workbook_metadata}


@mcp.tool
async def get_artefact_blocks(
    project_id: str,
    draft_id: str | None = None,
) -> dict:
    """Bounded read of addressable blocks for apply_artefact_operations.

    Returns project/draft ids, revision, and each block's id, type, content, and
    protection flag. When draft_id is omitted, resolves the latest create_pmp
    draft for the project. Use this instead of rewriting whole-document Markdown.
    """
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
            if draft_id:
                draft = await get_draft_artifact(session, uuid.UUID(draft_id))
            else:
                draft = await get_latest_draft_artifact(
                    session,
                    project_id=pid,
                    workflow_type="create_pmp",
                )
            if draft is None or draft.project_id != authorization.project.id:
                raise ToolError("Draft not found")
            metadata = (draft.provenance_metadata or {}).get("blocks") or {}
            blocks = []
            for block in markdown_blocks(
                normalize_draft_markdown(draft.content_markdown)
            ):
                if block.id is None:
                    continue
                provenance = metadata.get(block.id) or {}
                blocks.append(
                    {
                        "id": block.id,
                        "type": block.type,
                        "content": block.content,
                        "user_protected": bool(provenance.get("user_protected", False)),
                    }
                )
        except ToolError:
            raise
        except (ToolAuthError, ValueError, LookupError) as exc:
            raise ToolError(str(exc)) from exc
    return {
        "project_id": str(pid),
        "draft_id": str(draft.id),
        "version": draft.version,
        "workflow_type": draft.workflow_type,
        "blocks": blocks,
    }


@mcp.tool
async def appoint_consultant(
    project_id: str,
    source_document_id: str | None = None,
    firm: str | None = None,
    discipline: str | None = None,
    nominated_fee_ex_gst: str | None = None,
) -> dict:
    """Adopt a fee proposal and write the awarded contract sum.

    Use this when the user accepts a recommendation, appoints a consultant, or
    nominates an engagement sum. Do not inspect Cost Plan or PMP schema first.
    The fee proposal's classified discipline selects the row. The tool writes
    Approved Contract (committed) on the Cost Plan and marks the PMP
    Consultants register Appointed.

    Prefer source_document_id from the selected-document-register or evidence
    tools. If the user names a firm and sum without a file, pass firm,
    discipline, and nominated_fee_ex_gst. The write rebases a Cost Plan that
    is stale only because fee proposals were added; do not refresh first.
    """
    pid = uuid.UUID(project_id)
    nominated: Decimal | None = None
    if nominated_fee_ex_gst:
        try:
            nominated = Decimal(nominated_fee_ex_gst.replace(",", "").replace("$", ""))
        except Exception as exc:
            raise ToolError("nominated_fee_ex_gst must be a valid amount") from exc
    document_id = uuid.UUID(source_document_id) if source_document_id else None
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            turn = await session.get(AgentTurn, authorization.claims.turn_id)
            selected = documents_from_turn_context(
                turn.input_context if turn is not None else None
            )
            selected_ids = [
                document.source_document_id
                for document in selected
                if document.source_document_id is not None
            ]
            async with _tool_status(
                _turn_id(authorization),
                tool="appoint_consultant",
                running="Appointing the consultant",
                done="Appointed the consultant",
                error="Consultant appointment failed",
            ):
                result = await persist_consultant_appointment(
                    session,
                    project=authorization.project,
                    author_user_id=authorization.claims.user_id,
                    source_document_id=document_id,
                    firm=firm,
                    discipline=discipline,
                    nominated_fee_ex_gst=nominated,
                    selected_source_document_ids=selected_ids or None,
                )
                await session.commit()
        except ToolError:
            raise
        except (
            ToolAuthError,
            ConsultantAppointmentError,
            ValidationError,
            ValueError,
            RuntimeError,
            LookupError,
            ArtefactPolicyViolation,
            ArtefactRevisionConflict,
        ) as exc:
            raise ToolError(str(exc)) from exc
    return {
        "kind": "consultant_appointed",
        "discipline": result.discipline,
        "firm": result.firm,
        "fee_ex_gst": str(result.fee_ex_gst),
        "fee_source": result.fee_source,
        "proposal_reference": result.proposal_reference,
        "approved_contract": str(result.approved_contract),
        "cost_plan_item_key": result.cost_plan_item_key,
        "cost_plan_version": result.cost_plan_version,
        "pmp_updated": result.pmp_updated,
        "pmp_version": result.pmp_version,
        "source_document_id": (
            str(result.source_document_id) if result.source_document_id else None
        ),
        "message": (
            f"Appointed {result.firm} as {result.discipline} for "
            f"${result.fee_ex_gst:,.2f} ex GST. Cost Plan v{result.cost_plan_version} "
            "Approved Contract updated"
            + (
                f"; PMP Consultants register updated to v{result.pmp_version}."
                if result.pmp_updated
                else "."
            )
        ),
    }


@mcp.tool
async def apply_cost_plan_operations(
    project_id: str,
    expected_base_version: int,
    operations: list[dict],
) -> dict:
    """Apply up to 50 structured Cost Plan operations in one revision.

    Interpret natural language into ADD/UPDATE/DELETE/MOVE/DUPLICATE operations;
    deterministic application code validates dependencies and recalculates totals.
    The workbook is queued separately and is never edited as text.
    """
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
            parsed = [CostPlanOperation.model_validate(item) for item in operations]
            result = await persist_cost_operations(
                session,
                project=authorization.project,
                author_user_id=authorization.claims.user_id,
                expected_base_version=expected_base_version,
                operations=parsed,
                actor_source="ai_cost_plan_operation",
            )
            await session.commit()
            workbook = schedule_cost_plan_workbook_rebuild(
                authorization.project.id, result.state.version
            )
        except (
            ToolAuthError,
            ValidationError,
            ValueError,
            RuntimeError,
            LookupError,
            ArtefactPolicyViolation,
            ArtefactRevisionConflict,
        ) as exc:
            raise ToolError(str(exc)) from exc
    return {
        "kind": "cost_plan_operations_applied",
        "delta": result.delta.model_dump(mode="json"),
        "workbook": workbook,
    }


@mcp.tool
async def apply_artefact_operations(
    project_id: str,
    draft_id: str,
    expected_base_version: int,
    operations: list[dict],
) -> dict:
    """Apply validated ADD/UPDATE/DELETE/MOVE/DUPLICATE Markdown block operations.

    Use this after interpreting a narrowly scoped PMP, RFP, or RFT request. The
    application performs the mutation; do not rewrite the whole artefact.
    """
    if not 1 <= len(operations) <= 50:
        raise ToolError("operations must contain between 1 and 50 items")
    pid = uuid.UUID(project_id)
    did = uuid.UUID(draft_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
            draft = await get_draft_artifact(session, did)
            if draft is None or draft.project_id != pid:
                raise ToolError("Draft not found")
            parsed = [
                ArtefactBlockOperation.model_validate(item) for item in operations
            ]
            mutation = apply_block_operations(
                normalize_draft_markdown(draft.content_markdown),
                parsed,
                existing_metadata=(draft.provenance_metadata or {}).get("blocks"),
                actor_source="ai",
            )
            updated = await revise_workflow_artefact(
                session,
                project=authorization.project,
                draft=draft,
                expected_base_version=expected_base_version,
                author_user_id=authorization.claims.user_id,
                content_markdown=mutation.markdown,
                actor_source="ai_block_operation",
            )
            provenance = dict(updated.provenance_metadata or {})
            provenance.update(
                {
                    "blocks": mutation.metadata,
                    "changed_block_ids": list(mutation.changed_block_ids),
                    "block_operations": [
                        operation.model_dump(mode="json") for operation in parsed
                    ],
                }
            )
            updated.provenance_metadata = provenance
            await session.commit()
        except ToolError:
            raise
        except (
            ToolAuthError,
            ValidationError,
            ValueError,
            ArtefactRevisionConflict,
            ArtefactPolicyViolation,
        ) as exc:
            raise ToolError(str(exc)) from exc
    return {
        "kind": "artefact_operations_applied",
        "draft_id": str(updated.id),
        "version": updated.version,
        "changed_block_ids": list(mutation.changed_block_ids),
    }


@mcp.tool
async def apply_approved_tender_to_cost_plan(
    project_id: str,
    comparison_id: str,
    selected_quote_id: str,
    package_scope: str,
    expected_base_version: int,
    confirm_apply_as_proposal: bool,
) -> dict:
    """Apply an explicitly selected, R3-approved Tender as a proposed Cost revision."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            handoff = await approved_tender_cost_handoff(
                session,
                comparison_id=uuid.UUID(comparison_id),
                selected_quote_id=uuid.UUID(selected_quote_id),
                package_scope=package_scope,
                operator_user_id=authorization.claims.user_id,
            )
            proposal = map_tender_handoff(handoff)
            snapshot = await read_project_snapshot(
                session,
                project_id=pid,
                owner_user_id=authorization.project.owner_user_id,
            )
            state = await apply_external_proposal(
                session,
                project=authorization.project,
                author_user_id=authorization.claims.user_id,
                expected_base_version=expected_base_version,
                proposal=proposal,
                confirmed=confirm_apply_as_proposal,
                dependency_snapshot=cost_dependency_snapshot(
                    snapshot,
                    upstream_artefacts=[
                        {
                            "id": str(handoff.report_id),
                            "version": handoff.report_version,
                            "type": "tender_report",
                        }
                    ],
                    runtime_version="clerk-tender-cost-handoff-v1",
                ),
            )
            await session.commit()
            workbook_metadata = schedule_cost_plan_workbook_rebuild(
                authorization.project.id,
                state.version,
            )
        except (
            ToolAuthError,
            TenderCostHandoffError,
            ValidationError,
            ValueError,
            RuntimeError,
            LookupError,
        ) as exc:
            raise ToolError(str(exc)) from exc
    return {**state.model_dump(mode="json"), "workbook": workbook_metadata}


@mcp.tool
async def sort_project_files(
    project_id: str,
    idempotency_key: str,
    expected_snapshot_fingerprint: str,
    expected_profile_revision: int,
    expected_decision_set_revision: int,
) -> dict:
    """Queue durable project-file classification and sorting."""
    return await _start_mcp_workflow(
        project_id=project_id,
        workflow_type="sort_project_files",
        idempotency_key=idempotency_key,
        expected_snapshot_fingerprint=expected_snapshot_fingerprint,
        expected_profile_revision=expected_profile_revision,
        expected_decision_set_revision=expected_decision_set_revision,
    )


@mcp.tool
async def start_transmittal(
    project_id: str,
    idempotency_key: str,
    expected_snapshot_fingerprint: str,
    expected_profile_revision: int,
    expected_decision_set_revision: int,
    recipient: str | None = None,
    purpose: str | None = None,
) -> dict:
    """Queue an unissued transmittal from the current turn's selected documents.

    The model cannot supply document ids to this tool. The selection is resolved
    by the API before the turn starts and read back here from the authenticated
    durable turn, preventing a prompt from broadening or changing the issue set.
    """
    pid = uuid.UUID(project_id)
    recipient = _normalise_optional_workflow_text(
        recipient, field="recipient", maximum=512
    )
    purpose = _normalise_optional_workflow_text(purpose, field="purpose", maximum=1024)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            turn = await session.get(AgentTurn, authorization.claims.turn_id)
            documents = documents_from_turn_context(
                turn.input_context if turn is not None else None
            )
            if not documents:
                raise ToolError(
                    "Select one or more project documents in the document register "
                    "before creating a transmittal."
                )
            snapshot = await read_project_snapshot(
                session,
                project_id=pid,
                owner_user_id=authorization.project.owner_user_id,
            )
            message = capability_block_message(snapshot, TRANSMITTAL)
            if message:
                raise WorkflowRunCapabilityConflict(message)
            request = WorkflowRunStartRequest(
                idempotency_key=idempotency_key,
                expected_snapshot_fingerprint=expected_snapshot_fingerprint,
                expected_profile_revision=expected_profile_revision,
                expected_decision_set_revision=expected_decision_set_revision,
                turn_id=authorization.claims.turn_id,
                parameters={
                    "selected_documents": [
                        document.model_dump(mode="json") for document in documents
                    ],
                    "recipient": recipient,
                    "purpose": purpose,
                },
            )
            run, created = await persist_workflow_run(
                session,
                project=authorization.project,
                user_id=authorization.claims.user_id,
                workflow_type=TRANSMITTAL_WORKFLOW_TYPE,
                request=request,
                snapshot=snapshot,
            )
            if created:
                await lock_workflow_inputs(
                    session,
                    project_id=pid,
                    workflow_type=TRANSMITTAL_WORKFLOW_TYPE,
                    workflow_id=run.id,
                    workspace_file_ids=[
                        document.workspace_file_id for document in documents
                    ],
                )
            await session.commit()
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        except ToolError:
            raise
        except (
            ValidationError,
            ValueError,
            WorkflowRunConflict,
            WorkflowRunCapabilityConflict,
        ) as exc:
            raise ToolError(f"workflow_run_conflict: {exc}") from exc
    await agent_turn_status_bus.publish(
        _turn_id(authorization),
        kind="resource",
        message="Transmittal draft queued",
        projectId=str(pid),
        resourceType="workflow_run",
        resourceId=str(run.id),
        action="queued",
        workflowType=TRANSMITTAL_WORKFLOW_TYPE,
    )
    return WorkflowRunView.model_validate(run).model_dump(mode="json")


@mcp.tool
async def start_consultant_procurement(
    project_id: str,
    discipline: str,
    idempotency_key: str,
    expected_snapshot_fingerprint: str,
    expected_profile_revision: int,
    expected_decision_set_revision: int,
    max_pages: int = 3,
    instructions: str | None = None,
) -> dict:
    """Queue consultant-service content for an external Request for Tender."""
    try:
        _normalise_consultant_discipline(discipline)
    except NonConsultantDiscipline as exc:
        return {
            "kind": "blocked",
            "reason": str(exc),
            "redirect": "start_trade_procurement",
        }
    return await _start_mcp_workflow(
        project_id=project_id,
        workflow_type="consultant_procurement",
        idempotency_key=idempotency_key,
        expected_snapshot_fingerprint=expected_snapshot_fingerprint,
        expected_profile_revision=expected_profile_revision,
        expected_decision_set_revision=expected_decision_set_revision,
        parameters={
            "discipline": discipline,
            "max_pages": max_pages,
            "instructions": instructions,
        },
    )


@mcp.tool
async def start_contractor_eoi(
    project_id: str,
    idempotency_key: str,
    expected_snapshot_fingerprint: str,
    expected_profile_revision: int,
    expected_decision_set_revision: int,
    package: str = "Main Works",
    max_pages: int = 1,
    instructions: str | None = None,
) -> dict:
    """Queue a durable client-issued head-contractor Expression of Interest."""
    return await _start_mcp_workflow(
        project_id=project_id,
        workflow_type="contractor_eoi",
        idempotency_key=idempotency_key,
        expected_snapshot_fingerprint=expected_snapshot_fingerprint,
        expected_profile_revision=expected_profile_revision,
        expected_decision_set_revision=expected_decision_set_revision,
        parameters={
            "package": package,
            "max_pages": max_pages,
            "instructions": instructions,
        },
    )


@mcp.tool
async def start_trade_procurement(
    project_id: str,
    package: str,
    kind: str,
    idempotency_key: str,
    expected_snapshot_fingerprint: str,
    expected_profile_revision: int,
    expected_decision_set_revision: int,
    max_pages: int = 3,
    instructions: str | None = None,
) -> dict:
    """Queue a durable client-issued Request for Tender/Quotation artefact."""
    if kind not in {"rft", "rfq"}:
        raise ToolError("kind must be rft or rfq")
    try:
        normalise_trade_target(package)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    return await _start_mcp_workflow(
        project_id=project_id,
        workflow_type="trade_procurement",
        idempotency_key=idempotency_key,
        expected_snapshot_fingerprint=expected_snapshot_fingerprint,
        expected_profile_revision=expected_profile_revision,
        expected_decision_set_revision=expected_decision_set_revision,
        parameters={
            "package": package,
            "kind": kind,
            "max_pages": max(1, max_pages),
            "instructions": instructions,
        },
    )


@mcp.tool
async def get_project_workflow_status(project_id: str, run_id: str) -> dict:
    """Read durable workflow state and progress for one project-scoped run."""
    pid = uuid.UUID(project_id)
    rid = uuid.UUID(run_id)
    async with get_session_factory()() as session:
        try:
            await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            run = await read_workflow_run(session, project_id=pid, run_id=rid)
        except (ToolAuthError, WorkflowRunNotFound) as exc:
            raise ToolError(str(exc)) from exc
        return WorkflowRunView.model_validate(run).model_dump(mode="json")


@mcp.tool
async def get_project_workflow_result(project_id: str, run_id: str) -> dict:
    """Read the typed result of one durable project workflow run."""
    pid = uuid.UUID(project_id)
    rid = uuid.UUID(run_id)
    async with get_session_factory()() as session:
        try:
            await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            run = await read_workflow_run(session, project_id=pid, run_id=rid)
        except (ToolAuthError, WorkflowRunNotFound) as exc:
            raise ToolError(str(exc)) from exc
        return {
            "run": WorkflowRunView.model_validate(run).model_dump(mode="json"),
            "result": run.result,
        }


@mcp.tool
async def cancel_project_workflow(project_id: str, run_id: str) -> dict:
    """Request cooperative cancellation of one durable project workflow run."""
    pid = uuid.UUID(project_id)
    rid = uuid.UUID(run_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            run = await persist_workflow_cancellation(
                session, project_id=pid, run_id=rid
            )
            await session.commit()
        except (ToolAuthError, WorkflowRunNotFound) as exc:
            raise ToolError(str(exc)) from exc
    await agent_turn_status_bus.publish(
        _turn_id(authorization),
        kind="resource",
        message="Workflow cancellation requested",
        projectId=str(pid),
        resourceType="workflow_run",
        resourceId=str(rid),
        action="cancel_requested",
    )
    return WorkflowRunView.model_validate(run).model_dump(mode="json")


def _decision_payload(row, set_revision: int) -> dict:
    return {
        "id": str(row.id),
        "project_id": str(row.project_id),
        "decision_id": row.decision_id,
        "section": row.section,
        "label": row.label,
        "options": row.options,
        "selected": row.selected,
        "source": row.source,
        "workflow_type": row.workflow_type,
        "revision": row.revision,
        "set_revision": set_revision,
        "locked": row.locked,
        "evidence_conflict": row.evidence_conflict,
        "agent_suggestion": row.agent_suggestion,
        "provenance": row.provenance,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _decision_tool_error(exc: Exception) -> ToolError:
    if isinstance(exc, DecisionNotFound):
        return ToolError("project decision not found")
    if isinstance(exc, (DecisionRevisionConflict, DecisionSetRevisionConflict)):
        return ToolError(f"project_decision_revision_conflict: {exc}")
    if isinstance(exc, DecisionLockedConflict):
        return ToolError(f"project_decision_locked: {exc}")
    if isinstance(exc, DecisionValidationError):
        return ToolError(f"invalid project decision: {exc}")
    return ToolError(str(exc))


@mcp.tool
async def list_project_decisions(project_id: str) -> dict:
    """List the revisioned Project Decisions for the active project."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            rows, set_revision = await read_project_decisions(session, project_id=pid)
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        except DecisionNotFound as exc:
            raise _decision_tool_error(exc) from exc
        return {
            "set_revision": set_revision,
            "decisions": [_decision_payload(row, set_revision) for row in rows],
        }


@mcp.tool
async def get_project_decision(project_id: str, decision_id: str) -> dict:
    """Read one Project Decision, including lock, conflict, and revision state."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            row, set_revision = await read_project_decision(
                session, project_id=pid, decision_id=decision_id
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        except DecisionNotFound as exc:
            raise _decision_tool_error(exc) from exc
        return _decision_payload(row, set_revision)


async def _mutate_project_decision(
    *,
    operation,
    project_id: str,
    decision_id: str,
    expected_revision: int,
    expected_set_revision: int,
    selected: str | None = None,
) -> dict:
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            kwargs = {
                "project_id": pid,
                "decision_id": decision_id,
                "expected_revision": expected_revision,
                "expected_set_revision": expected_set_revision,
                "actor_source": "agent",
            }
            if selected is not None:
                kwargs["selected"] = selected
                kwargs["provenance"] = {"interface": "mcp"}
            row, set_revision = await operation(session, **kwargs)
            await session.commit()
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        except (
            DecisionLockedConflict,
            DecisionNotFound,
            DecisionRevisionConflict,
            DecisionSetRevisionConflict,
            DecisionValidationError,
        ) as exc:
            raise _decision_tool_error(exc) from exc
        return _decision_payload(row, set_revision)


@mcp.tool
async def update_project_decision(
    project_id: str,
    decision_id: str,
    selected: str,
    expected_revision: int,
    expected_set_revision: int,
) -> dict:
    """Update a decision using optimistic decision and set revisions."""
    return await _mutate_project_decision(
        operation=persist_decision_update,
        project_id=project_id,
        decision_id=decision_id,
        selected=selected,
        expected_revision=expected_revision,
        expected_set_revision=expected_set_revision,
    )


@mcp.tool
async def lock_project_decision(
    project_id: str,
    decision_id: str,
    expected_revision: int,
    expected_set_revision: int,
) -> dict:
    """Lock a decision so generated evidence cannot overwrite its selection."""
    return await _mutate_project_decision(
        operation=persist_decision_lock,
        project_id=project_id,
        decision_id=decision_id,
        expected_revision=expected_revision,
        expected_set_revision=expected_set_revision,
    )


@mcp.tool
async def unlock_project_decision(
    project_id: str,
    decision_id: str,
    expected_revision: int,
    expected_set_revision: int,
) -> dict:
    """Unlock a decision so later evidence can update its selection."""
    return await _mutate_project_decision(
        operation=persist_decision_unlock,
        project_id=project_id,
        decision_id=decision_id,
        expected_revision=expected_revision,
        expected_set_revision=expected_set_revision,
    )


@mcp.tool
async def update_project_profile(
    project_id: str,
    expected_revision: int,
    changes: dict | str,
    clear_incompatible: bool = False,
) -> dict:
    """Apply user-authorized or enrichment-backed profile values."""
    pid = uuid.UUID(project_id)
    changes = _coerce_json_object(changes, field_name="changes")
    reserved_fields = {"expected_revision", "clear_incompatible"} & set(changes)
    if reserved_fields:
        raise ToolError(
            "changes cannot contain reserved fields: "
            + ", ".join(sorted(reserved_fields))
        )
    try:
        patch = ProjectProfilePatch(
            expected_revision=expected_revision,
            clear_incompatible=clear_incompatible,
            **changes,
        )
    except ValidationError as exc:
        raise _profile_tool_error(exc) from exc
    requested_fields = patch.model_fields_set - {
        "expected_revision",
        "clear_incompatible",
    }
    requested_patch = patch.model_dump(mode="json", include=requested_fields)
    if clear_incompatible:
        requested_patch["clear_incompatible"] = True
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
                required_scope=PROFILE_MUTATION_SCOPE,
                requested_profile_patch=requested_patch,
            )
            change = await apply_profile_patch(
                session,
                project=authorization.project,
                patch=patch,
                actor_source="agent",
            )
            await session.commit()
            await agent_turn_status_bus.publish(
                _turn_id(authorization),
                kind="resource",
                message="Updated project profile",
                projectId=str(pid),
                resourceType="project_profile",
                resourceId=str(pid),
                action="updated",
                revision=change.new_revision,
                changedFields=list(change.changed_fields),
                clearedFields=list(change.cleared_fields),
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        except (
            ProfileDependencyConflict,
            ProfileRevisionConflict,
            ProfileValidationError,
        ) as exc:
            raise _profile_tool_error(exc) from exc
        return change.model_dump(mode="json")


@mcp.tool
async def propose_project_profile_change(
    project_id: str,
    proposed_values: dict | str,
    evidence_references: list[dict] | str | None = None,
    confidence: float | None = None,
) -> dict:
    """Persist evidence-derived profile facts, auto-filling missing identity values."""
    pid = uuid.UUID(project_id)
    proposed_values = _coerce_json_object(proposed_values, field_name="proposed_values")
    try:
        references = [
            ProfileEvidenceReference.model_validate(reference)
            for reference in _coerce_json_object_list(
                evidence_references, field_name="evidence_references"
            )
        ]
    except ValidationError as exc:
        raise _profile_tool_error(exc) from exc
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
            proposal = await persist_profile_proposal(
                session,
                project=authorization.project,
                proposed_values=proposed_values,
                evidence_references=references,
                confidence=confidence,
                proposer="agent",
            )
            resolution = None
            if should_auto_apply_proposal(
                proposal,
                authorization.project,
                evidence_derived=bool(references),
            ):
                resolution = await accept_profile_proposal(
                    session=session,
                    project=authorization.project,
                    proposal_id=proposal.id,
                    expected_profile_revision=proposal.profile_revision,
                    actor_source="agent",
                )
                proposal = resolution.proposal
            await session.commit()
            if resolution is not None and resolution.profile_change is not None:
                change = resolution.profile_change
                await agent_turn_status_bus.publish(
                    _turn_id(authorization),
                    kind="resource",
                    message="Updated project profile",
                    projectId=str(pid),
                    resourceType="project_profile",
                    resourceId=str(pid),
                    action="updated",
                    revision=change.new_revision,
                    changedFields=list(change.changed_fields),
                    clearedFields=list(change.cleared_fields),
                )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        except (ProfileValidationError, ValidationError) as exc:
            raise _profile_tool_error(exc) from exc
        return proposal.model_dump(mode="json")


@mcp.tool
async def accept_project_profile_proposal(
    project_id: str,
    proposal_id: str,
    expected_revision: int,
) -> dict:
    """Accept a persisted profile proposal after explicit user confirmation."""
    pid = uuid.UUID(project_id)
    proposal_uuid = uuid.UUID(proposal_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
            resolution = await accept_profile_proposal(
                session,
                project=authorization.project,
                proposal_id=proposal_uuid,
                expected_profile_revision=expected_revision,
                actor_source="agent",
            )
            await session.commit()
            if resolution.profile_change is not None:
                change = resolution.profile_change
                await agent_turn_status_bus.publish(
                    _turn_id(authorization),
                    kind="resource",
                    message="Updated project profile",
                    projectId=str(pid),
                    resourceType="project_profile",
                    resourceId=str(pid),
                    action="updated",
                    revision=change.new_revision,
                    changedFields=list(change.changed_fields),
                    clearedFields=list(change.cleared_fields),
                )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        except (
            ProfileDependencyConflict,
            ProfileProposalNotFound,
            ProfileProposalRevisionConflict,
            ProfileProposalStateConflict,
            ProfileRevisionConflict,
            ProfileValidationError,
        ) as exc:
            raise _profile_tool_error(exc) from exc
        return resolution.model_dump(mode="json")


@mcp.tool
async def reject_project_profile_proposal(
    project_id: str,
    proposal_id: str,
    expected_revision: int,
) -> dict:
    """Reject a persisted profile proposal after explicit user confirmation."""
    pid = uuid.UUID(project_id)
    proposal_uuid = uuid.UUID(proposal_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
            resolution = await reject_profile_proposal(
                session,
                project=authorization.project,
                proposal_id=proposal_uuid,
                expected_profile_revision=expected_revision,
                actor_source="agent",
            )
            await session.commit()
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        except (
            ProfileProposalNotFound,
            ProfileProposalRevisionConflict,
            ProfileProposalStateConflict,
        ) as exc:
            raise _profile_tool_error(exc) from exc
        return resolution.model_dump(mode="json")


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
    expected_profile_revision: int,
    expected_selection_revision: int,
    context_overrides: dict | None = None,
) -> dict:
    """Atomically start Tender from the exact saved quote selection and profile revision."""
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
            try:
                result = await tender_intake.create_immutable_intake(
                    session,
                    request=TenderIntakeRequest(
                        project_id=pid,
                        expected_profile_revision=expected_profile_revision,
                        expected_selection_revision=expected_selection_revision,
                        context_overrides=context_overrides or {},
                        turn_id=_turn_id(authorization) or str(uuid.uuid4()),
                    ),
                    owner_user_id=project.owner_user_id,
                )
                await session.commit()
            except (
                ContextRevisionConflict,
                ContextValidationError,
                tender_intake.TenderIntakeNotReady,
                tender_intake.TenderIdempotencyConflict,
            ) as exc:
                await session.rollback()
                raise ToolError(str(exc)) from exc
        return result.model_dump(mode="json")


@mcp.tool
async def prepare_tender_comparison(
    project_id: str,
    expected_profile_revision: int,
    expected_selection_revision: int,
    context_overrides: dict | None = None,
) -> dict:
    """Read Tender readiness without creating or changing any records."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            prepared = await ProjectContextAdapter().prepare(
                session,
                project_id=pid,
                owner_user_id=authorization.project.owner_user_id,
                expected_profile_revision=expected_profile_revision,
                expected_selection_revision=expected_selection_revision,
                overrides=context_overrides or {},
            )
        except (ToolAuthError, ContextRevisionConflict, ContextValidationError) as exc:
            raise ToolError(str(exc)) from exc
        return prepared.model_dump(mode="json")


@mcp.tool
async def find_candidate_tender_documents(project_id: str) -> list[dict]:
    """Return candidate tender PDFs from the project workspace.

    SiteWise does not yet persist a backend document-selection model. This tool
    therefore returns likely tender/quote PDFs so Pi can ask the user to
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
            tool="find_candidate_tender_documents",
            running="Finding candidate tender documents",
            done="Found candidate tender documents",
            error="Candidate document lookup failed",
        ):
            records = await list_workspace_files_for_project(session, project_id=pid)
        return _candidate_documents(records)


@mcp.tool
async def get_tender_quote_selection(
    project_id: str, revision: int | None = None
) -> dict:
    """Return the exact ordered, revisioned Tender quote-group selection."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            selection = await read_document_selection(
                session, project_id=pid, revision=revision
            )
        except (ToolAuthError, SelectionValidationError) as exc:
            raise ToolError(str(exc)) from exc
        return selection.model_dump(mode="json")


@mcp.tool
async def replace_tender_quote_selection(
    project_id: str,
    expected_revision: int,
    quote_candidates: list[dict],
) -> dict:
    """Replace the ordered Tender quote groups using optimistic concurrency."""
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            candidates = [
                QuoteCandidateInput.model_validate(value) for value in quote_candidates
            ]
            selection = await persist_document_selection(
                session,
                project_id=pid,
                selected_by=authorization.project.owner_user_id,
                expected_revision=expected_revision,
                quote_candidates=candidates,
                actor_source="agent",
            )
            await session.commit()
        except (
            ToolAuthError,
            SelectionRevisionConflict,
            SelectionValidationError,
            ValidationError,
        ) as exc:
            raise ToolError(str(exc)) from exc
        return selection.model_dump(mode="json")


@mcp.tool
async def list_document_register(
    project_id: str,
    query: str | None = None,
    query_field: str = "any",
    document_number_greater_than: int | None = None,
    max_results: int = 200,
) -> list[dict]:
    """List selectable document-register rows with structured metadata.

    Use query with query_field="title" for requests such as files with
    "Basement" in the title. Supported fields are any, document_number, title,
    revision, category, filename, and path. Use document_number_greater_than for
    numeric comparisons; non-numeric document numbers do not match that filter.
    """
    pid = uuid.UUID(project_id)
    query_text = query.strip() if query and query.strip() else None
    normalized_query_field = query_field.strip().lower()
    if normalized_query_field not in {
        "any",
        "document_number",
        "title",
        "revision",
        "category",
        "filename",
        "path",
    }:
        raise ToolError(
            "query_field must be any, document_number, title, revision, category, "
            "filename, or path"
        )
    result_limit = max(1, min(max_results, 500))
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        async with _tool_status(
            _turn_id(authorization),
            tool="list_document_register",
            running="Searching the document register",
            done="Searched the document register",
            error="Document register search failed",
        ):
            rows = await list_document_register_rows(session, project_id=pid)
            matches = search_document_register_rows(
                rows,
                query=query_text,
                query_field=normalized_query_field,
                document_number_greater_than=document_number_greater_than,
                limit=result_limit,
            )
    return [_document_register_summary(row) for row in matches]


@mcp.tool
async def select_document_register_files(
    project_id: str,
    document_ids: list[str] | None = None,
    action: str = "replace",
) -> dict:
    """Select exact project document-register rows in the user's current UI.

    First call list_document_register and pass only ids returned by it. Action
    may be replace, add, remove, or clear. The server validates project
    ownership and stores the resulting set on this active agent turn, so a
    later workflow call in the same turn uses exactly the files shown selected.
    """
    pid = uuid.UUID(project_id)
    normalized_action = action.strip().lower()
    if normalized_action not in {"replace", "add", "remove", "clear"}:
        raise ToolError("action must be replace, add, remove, or clear")
    requested_ids = _document_register_ids(document_ids)
    if normalized_action == "clear" and requested_ids:
        raise ToolError("clear does not accept document ids")

    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session,
                authorization_header=_auth_header(),
                project_id=pid,
            )
            turn = await _active_selection_turn(session, authorization)
            rows = await list_document_register_rows(session, project_id=pid)
            row_by_id = {row.id: row for row in rows}
            missing_ids = [item for item in requested_ids if item not in row_by_id]
            if missing_ids:
                raise ToolError(
                    "One or more document ids are not selectable in this project's "
                    "current register. List the document register again."
                )

            current_documents = documents_from_turn_context(turn.input_context)
            current_ids = [
                document.source_document_id or document.workspace_file_id
                for document in current_documents
            ]
            current_ids = [item for item in current_ids if item in row_by_id]
            if normalized_action == "replace":
                selected_ids = requested_ids
            elif normalized_action == "add":
                selected_ids = list(dict.fromkeys([*current_ids, *requested_ids]))
            elif normalized_action == "remove":
                removed = set(requested_ids)
                selected_ids = [item for item in current_ids if item not in removed]
            else:
                selected_ids = []

            selected_documents = await resolve_selected_turn_documents(
                session,
                project_id=pid,
                document_ids=selected_ids,
            )
            input_context = (
                dict(turn.input_context) if isinstance(turn.input_context, dict) else {}
            )
            input_context["selected_documents"] = [
                document.model_dump(mode="json") for document in selected_documents
            ]
            turn.input_context = input_context
            await session.commit()
        except (ToolAuthError, SelectedDocumentContextError) as exc:
            raise ToolError(str(exc)) from exc

    selected_id_strings = [str(item) for item in selected_ids]
    message = (
        "Cleared the document selection"
        if not selected_ids
        else f"Selected {len(selected_ids)} document"
        + ("" if len(selected_ids) == 1 else "s")
    )
    await agent_turn_status_bus.publish(
        _turn_id(authorization),
        kind="document_selection",
        message=message,
        projectId=str(pid),
        action="clear" if not selected_ids else "replace",
        requestedAction=normalized_action,
        documentIds=selected_id_strings,
    )
    return {
        "project_id": str(pid),
        "action": normalized_action,
        "selected_count": len(selected_ids),
        "selected_documents": [
            _document_register_summary(row_by_id[item]) for item in selected_ids
        ],
    }


@mcp.tool
async def list_project_files(
    project_id: str,
    query: str | None = None,
    path_prefix: str | None = None,
    max_results: int = 50,
) -> list[dict]:
    """List stored SiteWise project files, including generated drafts and workbooks.

    Use this when the user names a file or artefact that may not be an ingested
    source document. Generated files are project artefacts; they are not
    independent evidence unless their source_document_id points to an ingested
    document.
    """
    pid = uuid.UUID(project_id)
    query_text = query.strip().lower() if query and query.strip() else None
    prefix = (
        _tool_workspace_path(path_prefix)
        if path_prefix and path_prefix.strip()
        else None
    )
    if prefix == ".":
        prefix = None
    result_limit = max(1, min(max_results, 200))
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
            records = await search_workspace_files_for_project(
                session,
                project_id=pid,
                query=query_text,
                path_prefix=prefix,
                limit=result_limit,
            )
    return [
        _project_file_summary(record)
        for record in records
        if not _is_cost_plan_markdown_workspace_file(record)
    ]


@mcp.tool
async def read_project_workbook(
    project_id: str,
    path: str,
    max_rows: int = 80,
) -> dict:
    """Read an Excel workbook stored in SiteWise project files as sheet rows.

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
            try:
                updated = await revise_workflow_artefact(
                    session,
                    project=authorization.project,
                    draft=draft,
                    expected_base_version=draft.version,
                    author_user_id=authorization.claims.user_id,
                    content_markdown=forecast.updated_markdown,
                    actor_source="agent_consultant_fee_forecast",
                )
            except (ArtefactRevisionConflict, ArtefactPolicyViolation) as exc:
                raise ToolError(str(exc)) from exc
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
async def apply_cost_plan_budget_forecast(
    project_id: str,
    construction_budget_ex_gst: str,
    cost_plan_path: str | None = None,
) -> dict:
    """Adopt a user-supplied construction budget and populate the current Cost Plan.

    Construction plus PC allowance rows reconcile exactly to the adopted ex-GST
    envelope. Owner-side fees, consultants, and contingency are deterministic
    planning allowances outside that envelope. The action refreshes stale
    dependencies and publishes a complete typed Cost Plan and workbook revision.
    """
    pid = uuid.UUID(project_id)
    try:
        adopted_budget = Decimal(construction_budget_ex_gst.replace(",", ""))
    except Exception as exc:
        raise ToolError("construction_budget_ex_gst must be a valid amount") from exc

    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        async with _tool_status(
            _turn_id(authorization),
            tool="apply_cost_plan_budget_forecast",
            running="Allocating the adopted Cost Plan budget",
            done="Updated the Cost Plan budget allowances",
            error="Cost Plan budget allocation failed",
        ):
            draft = await _load_cost_plan_draft(
                session,
                project_id=pid,
                path=cost_plan_path,
            )
            try:
                base_state = await read_typed_cost_plan(
                    session,
                    project_id=pid,
                    owner_user_id=authorization.project.owner_user_id,
                )
                if base_state.version != draft.version:
                    raise ToolError(
                        "Cost Plan draft and canonical state versions do not agree; "
                        "refresh the project before applying an adopted budget"
                    )
                snapshot = await read_project_snapshot(
                    session,
                    project_id=pid,
                    owner_user_id=authorization.project.owner_user_id,
                )
                forecast = build_adopted_budget_forecast(
                    draft.content_markdown,
                    construction_budget=adopted_budget,
                    work_type=snapshot.profile.work_type,
                    source_ref=f"chat_turn:{authorization.claims.turn_id}",
                )
                proposed_items = align_forecast_items_to_existing(
                    forecast.items,
                    base_state.items,
                )
                result = await persist_cost_refresh(
                    session,
                    project=authorization.project,
                    author_user_id=authorization.claims.user_id,
                    expected_base_version=base_state.version,
                    current_snapshot=snapshot,
                    proposed_items=proposed_items,
                    dependency_snapshot=cost_dependency_snapshot(
                        snapshot,
                        model_version=base_state.dependency_snapshot.model_version,
                        prompt_version="adopted-budget-allocation-v1",
                        runtime_version="clerk-adopted-budget-allocation-v1",
                    ),
                    assumptions=forecast.assumptions,
                    contingency_percent=Decimal("0"),
                    escalation_percent=Decimal("0"),
                )
                updated = await get_draft_artifact(
                    session, result.state.artefact_revision_id
                )
                if updated is None:
                    raise ToolError("updated Cost Plan revision was not found")
                workbook_metadata = await sync_cost_plan_revision_artifacts(
                    session,
                    project=authorization.project,
                    draft=updated,
                    markdown=updated.content_markdown,
                    typed_state=result.state,
                    provenance_updates={
                        "adopted_budget_forecast": forecast.to_payload(),
                    },
                )
                await session.commit()
            except (
                AdoptedBudgetForecastError,
                ArtefactRevisionConflict,
                ArtefactPolicyViolation,
                ValueError,
                RuntimeError,
                LookupError,
            ) as exc:
                raise ToolError(str(exc)) from exc

    return {
        "kind": "cost_plan_budget_forecast_applied",
        "source_draft_id": str(draft.id),
        "draft_id": str(updated.id),
        "version": updated.version,
        "workspace_path": updated.workspace_path,
        "workbook": workbook_metadata,
        "changed_item_keys": result.changed_item_keys,
        "conflicts": result.conflicts,
        "forecast": forecast.to_payload(),
        "message": (
            f"Cost Plan v{updated.version} now carries the adopted "
            f"${forecast.construction_budget:,.2f} ex-GST construction envelope "
            f"across {len(forecast.items)} rows. Total planning budget is "
            f"${forecast.total_excluding_gst:,.2f} ex GST. Unconfirmed figures "
            "are planning allowances, not quotations."
        ),
    }


@mcp.tool
async def draft_consultant_procurement_artifact(
    project_id: str,
    discipline: str,
    max_pages: int = 3,
    instructions: str | None = None,
) -> dict:
    """Create consultant content for a saved, externally titled Request for Tender.

    Use this for natural-language requests such as "draft a request for fee
    proposal", "draft consultant procurement", "prepare an RFP for the
    structural engineer", or "prepare scope for BASIX assessor". The output is
    always a client-issued Request for Tender, not a consultant-issued fee proposal.
    """
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        snapshot = await read_project_snapshot(
            session,
            project_id=pid,
            owner_user_id=authorization.project.owner_user_id,
        )
        capability_message = capability_block_message(
            snapshot,
            CONSULTANT_PROCUREMENT,
        )
        if capability_message:
            raise ToolError(capability_message)
        turn_id = _turn_id(authorization)
        async with _tool_status(
            turn_id,
            tool="draft_consultant_procurement_artifact",
            running=f"Drafting Request for Tender: {discipline}",
            done="Created consultant procurement draft",
            error="Consultant procurement draft failed",
        ) as extra:
            try:
                result = await run_consultant_procurement_artifact(
                    session,
                    project=authorization.project,
                    user_id=authorization.claims.user_id,
                    discipline=discipline,
                    max_pages=max_pages,
                    instructions=instructions,
                    generation_context=resolve_project_generation_context(snapshot),
                )
            except (ModelAPIError, UnexpectedModelBehavior, OpenAIError) as exc:
                raise ToolError(
                    _upstream_failure_message(
                        exc,
                        operation="draft the consultant tender",
                        workflow_name="Request for Tender drafting",
                    )
                ) from exc
            extra.update(_consultant_procurement_status_metadata(result.source_trace))
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
async def search_web(
    project_id: str,
    query: str,
    jurisdiction: str | None = None,
    max_results: int = 6,
) -> list[dict]:
    """Search configured official government sources for current external information.

    Search results are discovery candidates only. Call read_web_source on the
    selected official pages before relying on them in an answer.
    """
    pid = uuid.UUID(project_id)
    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_access_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc

        normalized_jurisdiction = jurisdiction.upper() if jurisdiction else None
        if normalized_jurisdiction and normalized_jurisdiction not in {
            "CTH",
            "ACT",
            "NSW",
            "NT",
            "QLD",
            "SA",
            "TAS",
            "VIC",
            "WA",
        }:
            raise ToolError(
                "jurisdiction must be an Australian state, territory, or CTH"
            )
        result_limit = max(1, min(max_results, settings.web_search_max_results))
        running_subject = f"\u201c{_clip_status_text(query, max_len=48)}\u201d"
        async with _tool_status(
            _turn_id(authorization),
            tool="search_web",
            running=_activity_message(
                "Searching official sources", subject=running_subject
            ),
            done="Searched official sources",
            error="Official source search failed",
        ) as extra:
            try:
                results = await get_web_research_service().search(
                    query,
                    jurisdiction=normalized_jurisdiction,
                    max_results=result_limit,
                )
            except (ValueError, WebResearchDisabled, WebSearchProviderError) as exc:
                raise ToolError(str(exc)) from exc
            extra["query"] = _clip_status_text(query, max_len=120)
            extra["jurisdiction"] = normalized_jurisdiction
            extra["result_count"] = len(results)
            return [asdict(result) for result in results]


@mcp.tool
async def read_web_source(
    project_id: str,
    url: str,
    section_hint: str | None = None,
    refresh: bool = False,
) -> dict:
    """Read an official Australian government page selected by search_web.

    Returns a bounded excerpt plus provenance and currentness metadata. Treat
    the result as an external reference, never as evidence from the project.
    Successful reads are stored as a per-project official attachment.
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
            tool="read_web_source",
            running=_activity_message("Reading an official web source"),
            done="Read official web source",
            error="Official web source read failed",
        ) as extra:
            source = None
            if not refresh:
                snapshot = await find_official_attachment(
                    session, project_id=pid, url=url
                )
                if snapshot is not None:
                    source = web_source_from_attachment(
                        snapshot, section_hint=section_hint
                    )
            if source is None:
                try:
                    source = await get_web_research_service().read(
                        url,
                        section_hint=section_hint,
                    )
                except (ValueError, WebResearchDisabled, WebFetchError) as exc:
                    raise ToolError(str(exc)) from exc
                await persist_official_attachment(
                    session,
                    project_id=pid,
                    project_slug=authorization.project.slug,
                    source=source,
                    text=source.excerpt,
                )
                await session.commit()
            source_data = asdict(source)
            extra["message"] = _activity_message(
                "Read official web source",
                subject=source.title,
            )
            extra["web_source"] = {
                key: value for key, value in source_data.items() if key != "excerpt"
            }
            extra["web_source"]["excerpt"] = source.excerpt[:2000]
            return source_data


@mcp.tool
async def attach_official_instrument(
    project_id: str,
    instrument_id: str | None = None,
    url: str | None = None,
    document_id: str | None = None,
    section_hint: str | None = None,
    refresh: bool = False,
) -> dict:
    """Attach an official planning instrument to this project.

    Provide exactly one of instrument_id (NSW legislation), url (official
    government page or PDF), or document_id (an already-uploaded file).
    The attachment is an official reference, never project evidence.
    """
    provided = [value for value in (instrument_id, url, document_id) if value]
    if len(provided) != 1:
        raise ToolError("provide exactly one of instrument_id, url, or document_id")

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
            tool="attach_official_instrument",
            running=_activity_message("Attaching official instrument"),
            done="Attached official instrument",
            error="Official instrument attach failed",
        ) as extra:
            if document_id:
                document = await _load_project_source_document(
                    session,
                    project_id=pid,
                    document_id=uuid.UUID(document_id),
                )
                if document is None:
                    raise ToolError("uploaded document was not found in this project")
                metadata = dict(document.document_metadata or {})
                metadata.update(
                    {
                        "knowledge_scope": "official",
                        "official_url": metadata.get("official_url") or "",
                        "source_type": "web_reference",
                        "authority_class": metadata.get("authority_class")
                        or "government_guidance",
                        "retrieved_at": datetime.now(UTC).isoformat(),
                    }
                )
                document.source_type = "reference"
                document.document_class = "statutory_instrument"
                document.document_metadata = metadata
                await session.commit()
                source = web_source_from_attachment(
                    document, section_hint=section_hint
                )
                extra["message"] = _activity_message(
                    "Attached official instrument",
                    subject=document.filename,
                )
                extra["web_source"] = {
                    key: value
                    for key, value in asdict(source).items()
                    if key != "excerpt"
                }
                return {
                    **asdict(source),
                    "title": document.filename,
                    "document_id": str(document.id),
                    "relative_path": document.relative_path,
                    "knowledge_scope": "official",
                }

            resolved_url = url
            if instrument_id:
                if instrument_id_from_url(instrument_id) != instrument_id.casefold():
                    raise ToolError("instrument_id must be a NSW legislation id")
                resolved_url = html_view_url(instrument_id.casefold())
            assert resolved_url is not None
            if _source_authority(resolved_url) is None:
                raise ToolError("url must be an official Australian government URL")

            source = None
            if not refresh:
                snapshot = await find_official_attachment(
                    session, project_id=pid, url=resolved_url
                )
                if snapshot is not None:
                    source = web_source_from_attachment(
                        snapshot, section_hint=section_hint
                    )
                    document = snapshot
            if source is None:
                try:
                    source = await get_web_research_service().read(
                        resolved_url,
                        section_hint=section_hint,
                    )
                except (ValueError, WebResearchDisabled, WebFetchError) as exc:
                    raise ToolError(str(exc)) from exc
                document = await persist_official_attachment(
                    session,
                    project_id=pid,
                    project_slug=authorization.project.slug,
                    source=source,
                    text=source.excerpt,
                )
                await session.commit()
            extra["message"] = _activity_message(
                "Attached official instrument",
                subject=source.title,
            )
            extra["web_source"] = {
                key: value for key, value in asdict(source).items() if key != "excerpt"
            }
            extra["web_source"]["excerpt"] = source.excerpt[:2000]
            return {
                **asdict(source),
                "document_id": str(document.id),
                "relative_path": document.relative_path,
                "knowledge_scope": "official",
            }


@mcp.tool
async def set_document_classification(
    project_id: str,
    document_id: str,
    document_class: str,
    document_subject: str | None = None,
    reason: str | None = None,
) -> dict:
    """Record a human correction of a document's class and subject.

    Use when the user corrects classification, for example: "That heritage
    report is actually a planning certificate." The correction is permanent
    (basis=user, confidence=1.0) and survives re-ingest.
    """
    from typing import get_args

    from ingest.categories import canonical_category
    from ingest.types import DocumentClass

    try:
        pid = uuid.UUID(project_id)
    except ValueError as exc:
        raise ToolError("project_id must be a UUID") from exc
    try:
        parsed_document_id = uuid.UUID(document_id)
    except ValueError as exc:
        raise ToolError("document_id must be a UUID") from exc
    if document_class not in get_args(DocumentClass):
        raise ToolError("document_class is not a canonical class")
    subject = None if document_subject is None else canonical_category(document_subject)
    if (
        document_subject
        and subject == "none"
        and document_subject.strip().lower() not in {"none", "unassigned"}
    ):
        raise ToolError("document_subject is not a canonical subject")

    async with get_session_factory()() as session:
        try:
            authorization = await authorize_project_mutation_with_claims(
                session, authorization_header=_auth_header(), project_id=pid
            )
            document = await set_document_classification_service(
                session,
                project_id=authorization.project.id,
                document_id=parsed_document_id,
                document_class=document_class,
                document_subject=subject,
                actor_id=authorization.claims.user_id,
                reason=reason,
            )
            await session.commit()
        except ToolAuthError as exc:
            raise ToolError(str(exc)) from exc
        except DocumentClassificationNotFound as exc:
            raise ToolError("Document not found") from exc
        except DocumentClassificationInvalid as exc:
            raise ToolError(str(exc)) from exc

    metadata = document.document_metadata if isinstance(document.document_metadata, dict) else {}
    return {
        "document_id": str(document.id),
        "document_class": document.document_class,
        "document_subject": metadata.get("subject"),
        "basis": metadata.get("basis", "user"),
        "confidence": metadata.get("confidence", "1.0"),
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
        running_subject = (
            Path(_tool_workspace_path(workspace_path)).name if workspace_path else None
        )
        async with _tool_status(
            _turn_id(authorization),
            tool="get_document",
            running=_activity_message("Reading", subject=running_subject),
            done="Read document",
            error="Document read failed",
        ) as extra:
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
            filename = document.filename or running_subject
            if filename:
                extra["documents"] = [filename]
                extra["message"] = _activity_message("Read", subject=filename)
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
        hint = (
            filename_hint.strip() if filename_hint and filename_hint.strip() else None
        )
        running_subject = hint or f"“{_clip_status_text(query, max_len=48)}”"
        async with _tool_status(
            _turn_id(authorization),
            tool="find_document_text",
            running=_activity_message("Searching", subject=running_subject),
            done="Searched documents",
            error="Ingested document text search failed",
        ) as extra:
            content_filters = [
                func.lower(SourceDocument.normalized_content).contains(term)
                for term in terms
            ]
            filters = [SourceDocument.project_id == project.id, or_(*content_filters)]
            if hint:
                hint_lower = hint.lower()
                filters.append(
                    or_(
                        func.lower(SourceDocument.filename).contains(hint_lower),
                        func.lower(SourceDocument.relative_path).contains(hint_lower),
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
                        "source_type": getattr(document, "source_type", None),
                        "knowledge_scope": (
                            getattr(document, "document_metadata", None) or {}
                        ).get("knowledge_scope"),
                        "content_chars": len(document.normalized_content or ""),
                        "snippets": snippets,
                    }
                )
                if len(matches) >= result_limit:
                    break

            filenames = [
                match["filename"]
                for match in matches
                if isinstance(match.get("filename"), str) and match["filename"]
            ]
            subject = _document_list_subject(filenames) or running_subject
            extra["query"] = _clip_status_text(query, max_len=120)
            if filenames:
                extra["documents"] = filenames
            extra["message"] = _activity_message("Searched", subject=subject)
            return matches


@mcp.tool
async def write_workspace_file(project_id: str, path: str, content: str) -> dict:
    """Write a UTF-8 scratch file under the project workspace.

    Editable draft artefacts must use ``apply_artefact_operations`` (or Cost Plan
    batch operations). Whole-document Markdown rewrites are rejected.
    """
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
                raise ToolError(
                    "draft artefacts require apply_artefact_operations; "
                    "whole-document Markdown writes are not supported"
                )

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
        running_subject = f"“{_clip_status_text(query, max_len=48)}”"
        async with _tool_status(
            _turn_id(authorization),
            tool="search_documents",
            running=_activity_message("Searching", subject=running_subject),
            done="Searched project documents",
            error="Project document search failed",
        ) as extra:
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
            filenames: list[str] = []
            seen_names: set[str] = set()
            for passage in passages:
                name = passage.filename
                if not name or name in seen_names:
                    continue
                seen_names.add(name)
                filenames.append(name)
            subject = _document_list_subject(filenames) or running_subject
            extra["query"] = _clip_status_text(query, max_len=120)
            if filenames:
                extra["documents"] = filenames
            extra["message"] = _activity_message("Searched", subject=subject)
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
async def list_platform_knowledge(
    project_id: str, topics: list[str] | None = None
) -> dict:
    """Catalog SiteWise platform knowledge (doctrine + seed guides) for this project.

    Applies the overlay gate: if the project has not declared its taxonomy
    (class/work type) and state, no knowledge is listed — resolve the gate with
    the user first. When the gate passes, returns the mandatory reading list per
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
                **_platform_overlay_kwargs(project),
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
                    format_overlay_failure(status, workflow="Platform knowledge search")
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
            # Agent analog of the deterministic workflows' seed_consulted
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
