from __future__ import annotations

import asyncio
import inspect
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.draft_artifact import DraftArtifact
from app.database.draft_artifacts import create_draft_artifact, next_draft_version
from app.database.project import Project
from app.database.workspace_files import upsert_workspace_file
from app.inbox.paths import build_storage_key
from app.projects.artefact_context import ProcurementArtefactContext
from app.projects.generation_brief import (
    ArtefactGenerationBrief,
    build_generation_brief,
)
from app.projects.generation_audit import build_generation_manifest
from app.projects.artefact_blocks import materialize_block_identity
from app.projects.generation_context import ProjectGenerationContext
from app.retrieval.generation import (
    EvidencePoolStats,
    GenerationEvidenceInput,
    GenerationEvidencePool,
    GenerationRetrievalRequest,
    RetrievalBudget,
    RetrievalLevel,
    retrieve_generation_evidence,
    select_retrieval_level,
)
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters, SourcePassage
from app.sitewise.knowledge_catalog import (
    catalog_entry_for_path,
    load_sections,
)
from app.sitewise.seed_routing import (
    ArtefactType,
    SeedKnowledgeSelection,
    select_seed_knowledge,
    select_seed_knowledge_for_project,
)
from app.storage.project_files import upload_project_file
from ingest.hashing import bytes_content_hash


CORE_PROCUREMENT_GUIDANCE_PATHS = (
    "seed/procurement-tendering-guide.md",
    "seed/cost-management-principles.md",
)
PROCUREMENT_RETRIEVAL_BUDGET = RetrievalBudget(
    max_searches=12,
    max_chunks=24,
    max_documents=16,
    max_tokens=9_000,
    max_chars=36_000,
    max_concurrency=4,
)
PROCUREMENT_REQUIRED_GUIDANCE_MAX_CHARS = 6_000


@dataclass(frozen=True, slots=True)
class EvidenceQuery:
    key: str
    label: str
    query: str


@runtime_checkable
class ProcurementTarget(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def slug(self) -> str: ...


@dataclass(frozen=True, slots=True)
class ProcurementRequestResult:
    draft: DraftArtifact
    target_name: str
    source_trace: dict[str, Any]


class ProcurementDocument(ABC):
    document_key: str
    workspace_subfolder: str
    filename_stem: str
    knowledge_workflow: str
    runtime_name: str
    provenance_target_key = "target"
    trace_tool_name: str
    trace_generation_purpose: str
    trace_evidence_purpose: str
    trace_guidance_purpose: str
    load_required_seed_content = False
    seed_artefact_type: ArtefactType

    def provenance_metadata(self, target: ProcurementTarget) -> dict[str, Any]:
        """Return document-specific metadata without duplicating publication."""
        return {}

    def build_context(
        self,
        project_context: ProjectGenerationContext,
        target: ProcurementTarget,
    ) -> ProcurementArtefactContext | None:
        """Build a target-specific lens when this document consumes one."""
        del project_context, target
        return None

    @abstractmethod
    def resolve_target(self, raw: str) -> ProcurementTarget: ...

    @abstractmethod
    def title(self, target: ProcurementTarget) -> str: ...

    @abstractmethod
    def evidence_queries(
        self, target: ProcurementTarget
    ) -> tuple[EvidenceQuery, ...]: ...

    @abstractmethod
    def platform_query(self, target: ProcurementTarget) -> str: ...

    def platform_guidance_paths(self, target: ProcurementTarget) -> tuple[str, ...]:
        """Return target-specific platform guidance that must be consulted."""
        return CORE_PROCUREMENT_GUIDANCE_PATHS

    def filter_platform_knowledge(
        self,
        knowledge: list[dict[str, Any]],
        target: ProcurementTarget,
    ) -> list[dict[str, Any]]:
        """Apply document-specific relevance rules after taxonomy filtering."""
        return knowledge

    async def supplemental_project_evidence(
        self,
        session: AsyncSession,
        *,
        project: Project,
        target: ProcurementTarget,
    ) -> list[dict[str, Any]]:
        """Return complete structured inputs that semantic passage search can miss."""
        del session, project, target
        return []

    def filter_project_evidence(
        self,
        evidence: list[dict[str, Any]],
        target: ProcurementTarget,
    ) -> list[dict[str, Any]]:
        """Remove false-positive retrieval hits before drafting the narrative."""
        del target
        return evidence

    async def issued_documents(
        self,
        session: AsyncSession,
        *,
        project: Project,
        target: ProcurementTarget,
        narrative_evidence: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return the deterministic outbound register, separate from grounding."""
        del session, project, target
        return list(narrative_evidence)

    @abstractmethod
    async def forecast(
        self,
        session: AsyncSession,
        *,
        project_id: uuid.UUID,
        target: ProcurementTarget,
    ) -> dict[str, Any]: ...

    def reconcile_forecast(
        self,
        forecast: dict[str, Any],
        evidence: list[dict[str, Any]],
        target: ProcurementTarget,
    ) -> dict[str, Any]:
        return forecast

    @abstractmethod
    def assumptions_and_missing(
        self,
        *,
        project: Project,
        evidence: list[dict[str, Any]],
        forecast: dict[str, Any],
        target: ProcurementTarget,
    ) -> tuple[list[str], list[str]]: ...

    @abstractmethod
    def render(
        self,
        *,
        project: Project,
        target: ProcurementTarget,
        project_evidence: list[dict[str, Any]],
        issued_documents: list[dict[str, Any]],
        platform_knowledge: list[dict[str, Any]],
        forecast: dict[str, Any],
        assumptions: list[str],
        missing_inputs: list[str],
        max_pages: int,
        instructions: str | None,
        artefact_context: ProcurementArtefactContext | None,
        generation_brief: ArtefactGenerationBrief | None,
        on_progress: ProgressPublisher | None,
    ) -> str | Awaitable[str]: ...


RetrieverFactory = Callable[[AsyncSession], DocumentRetriever]
NextVersion = Callable[..., Awaitable[int]]
CreateDraft = Callable[..., Awaitable[DraftArtifact]]
SyncWorkspace = Callable[..., Awaitable[str]]
ProgressPublisher = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class _ProcurementProgressCapture:
    downstream: ProgressPublisher | None
    consistency_ai_call_count: int = 0

    async def publish(self, progress: dict[str, Any]) -> None:
        if progress.get("stage") == "consistency_complete":
            call_count = progress.get("ai_call_count")
            if isinstance(call_count, int) and not isinstance(call_count, bool):
                self.consistency_ai_call_count += max(0, call_count)
        await publish_procurement_progress(self.downstream, progress)


async def publish_procurement_progress(
    on_progress: ProgressPublisher | None,
    progress: dict[str, Any],
) -> None:
    if on_progress is None:
        return
    try:
        await on_progress(progress)
    except Exception:
        # Progress is advisory and must never invalidate a generated artefact.
        return


def workflow_type_for(document: ProcurementDocument, target: ProcurementTarget) -> str:
    return f"{document.document_key}_{target.slug}"


def workspace_path_for(
    project: Project,
    document: ProcurementDocument,
    *,
    target_slug: str,
    version: int,
) -> str:
    root = project.workspace_path.rstrip("/")
    return (
        f"{root}/{document.workspace_subfolder}/"
        f"{document.filename_stem}_{target_slug}_v{version:02d}.draft.md"
    )


async def draft_procurement_request(
    session: AsyncSession,
    *,
    project: Project,
    user_id: uuid.UUID,
    document: ProcurementDocument,
    raw_target: str,
    max_pages: int = 1,
    instructions: str | None = None,
    generation_context: ProjectGenerationContext | None = None,
    auto_commit: bool = True,
    retriever_factory: RetrieverFactory | None = None,
    next_version: NextVersion | None = None,
    create_draft: CreateDraft | None = None,
    sync_workspace: SyncWorkspace | None = None,
    on_progress: ProgressPublisher | None = None,
) -> ProcurementRequestResult:
    target = document.resolve_target(raw_target)
    artefact_context = (
        document.build_context(generation_context, target)
        if generation_context is not None
        else None
    )
    await publish_procurement_progress(on_progress, {"stage": "context_ready"})
    # A page target guides the bounded narrative prompt. It must not cause a
    # complete procurement document to fail or be truncated at an arbitrary cap.
    pages = max(1, max_pages)
    retriever = (retriever_factory or DocumentRetriever)(session)
    seed_selection = _select_procurement_seed_knowledge(
        document=document,
        project=project,
        target=target,
        generation_context=generation_context,
    )
    evidence_queries = document.evidence_queries(target)
    evidence_pool, supplemental_evidence = await asyncio.gather(
        _retrieve_procurement_evidence_pool(
            retriever,
            project=project,
            project_queries=evidence_queries,
            platform_query=document.platform_query(target),
            artefact_context=artefact_context,
        ),
        document.supplemental_project_evidence(
            session,
            project=project,
            target=target,
        ),
    )
    project_evidence = _project_evidence_from_pool(evidence_pool, evidence_queries)
    project_evidence = _merge_project_evidence(
        project_evidence,
        supplemental_evidence,
    )
    project_evidence = document.filter_project_evidence(project_evidence, target)
    platform_knowledge = _platform_knowledge_from_pool(
        evidence_pool,
        allowed_paths=set(seed_selection.applicable_paths),
    )
    platform_knowledge = document.filter_platform_knowledge(
        platform_knowledge,
        target,
    )
    platform_knowledge = await _merge_required_guidance(
        session,
        platform_knowledge,
        selection=seed_selection,
        load_required_seed_content=document.load_required_seed_content,
    )
    retrieval_level = (
        evidence_pool.stats.level
        if evidence_pool.stats is not None
        else RetrievalLevel.TARGETED_PROJECT
    )
    (
        project_evidence,
        platform_knowledge,
        final_retrieval_stats,
    ) = await _bound_procurement_inputs(
        retriever,
        project_evidence=project_evidence,
        platform_knowledge=platform_knowledge,
        level=retrieval_level,
        budget=PROCUREMENT_RETRIEVAL_BUDGET,
    )
    issued_documents = await document.issued_documents(
        session,
        project=project,
        target=target,
        narrative_evidence=project_evidence,
    )
    if not issued_documents:
        issued_documents = list(project_evidence)
    await publish_procurement_progress(
        on_progress,
        {
            "stage": "retrieval_complete",
            "project_evidence_count": len(project_evidence),
            "platform_guidance_count": len(platform_knowledge),
        },
    )
    forecast = await document.forecast(
        session,
        project_id=project.id,
        target=target,
    )
    forecast = document.reconcile_forecast(forecast, project_evidence, target)
    assumptions, missing_inputs = document.assumptions_and_missing(
        project=project,
        evidence=project_evidence,
        forecast=forecast,
        target=target,
    )
    source_trace = _source_trace(
        document=document,
        project_evidence=project_evidence,
        issued_documents=issued_documents,
        platform_knowledge=platform_knowledge,
        forecast=forecast,
        assumptions=assumptions,
        missing_inputs=missing_inputs,
    )
    search_stats = evidence_pool.stats or final_retrieval_stats
    source_trace["retrieval"] = {
        "level": search_stats.level.name.casefold(),
        "requested_searches": search_stats.requested_searches,
        "executed_searches": search_stats.executed_searches,
        "selected_chunks": final_retrieval_stats.selected_chunks,
        "selected_documents": final_retrieval_stats.selected_documents,
        "selected_tokens": final_retrieval_stats.selected_tokens,
        "selected_chars": final_retrieval_stats.selected_chars,
    }
    generation_brief = (
        build_generation_brief(
            artefact_context,
            evidence_refs=_unique_paths(
                [*project_evidence, *issued_documents],
                key="relative_path",
            ),
            seed_refs=_unique_paths(platform_knowledge, key="path"),
            constraints=[
                f"Maximum narrative target: {pages} page(s).",
                *(
                    [instructions.strip()]
                    if instructions and instructions.strip()
                    else []
                ),
            ],
        )
        if artefact_context is not None
        else None
    )
    progress_capture = _ProcurementProgressCapture(on_progress)
    rendered = document.render(
        project=project,
        target=target,
        project_evidence=project_evidence,
        issued_documents=issued_documents,
        platform_knowledge=platform_knowledge,
        forecast=forecast,
        assumptions=assumptions,
        missing_inputs=missing_inputs,
        max_pages=pages,
        instructions=instructions,
        artefact_context=artefact_context,
        generation_brief=generation_brief,
        on_progress=progress_capture.publish,
    )
    markdown = await rendered if inspect.isawaitable(rendered) else rendered
    source_trace["consistency_ai_call_count"] = (
        progress_capture.consistency_ai_call_count
    )
    block_identity = materialize_block_identity(
        markdown,
        actor_source="ai"
        if document.seed_artefact_type in {"rfp", "rft"}
        else "system",
        generation_input_hash=(
            generation_brief.input_fingerprint if generation_brief is not None else None
        ),
        generation_version=document.runtime_name,
    )
    markdown = block_identity.markdown

    await publish_procurement_progress(on_progress, {"stage": "saving"})
    workflow_type = workflow_type_for(document, target)
    version_hint = await (next_version or next_draft_version)(
        session,
        project_id=project.id,
        workflow_type=workflow_type,
    )
    draft = await (create_draft or create_draft_artifact)(
        session,
        project_id=project.id,
        workflow_type=workflow_type,
        title=document.title(target),
        workspace_path=workspace_path_for(
            project,
            document,
            target_slug=target.slug,
            version=version_hint,
        ),
        author_user_id=user_id,
        content_markdown=markdown,
        model=None,
        runtime=document.runtime_name,
        expected_base_version=version_hint - 1,
        actor_source=f"{document.document_key}_workflow",
        provenance_metadata={
            "workflow": document.document_key,
            document.provenance_target_key: target.name,
            "max_pages": pages,
            "instructions": instructions,
            "source_trace": source_trace,
            **(
                {
                    "artefact_context": artefact_context.model_dump(mode="json"),
                }
                if artefact_context is not None
                else {}
            ),
            **(
                {"generation_brief": generation_brief.model_dump(mode="json")}
                if generation_brief is not None
                else {}
            ),
            "blocks": block_identity.metadata,
            **(
                {
                    "generation_manifest": build_generation_manifest(
                        generation_brief
                    ).model_dump(mode="json")
                }
                if generation_brief is not None
                else {}
            ),
            **document.provenance_metadata(target),
            **_provenance_references(project_evidence, platform_knowledge),
            "issued_document_refs": _unique_paths(
                issued_documents,
                key="relative_path",
            ),
        },
    )
    sync = sync_workspace or _sync_draft_workspace
    await sync(
        session,
        project=project,
        document=document,
        draft=draft,
        markdown=markdown,
    )
    if auto_commit:
        await session.commit()
    await publish_procurement_progress(on_progress, {"stage": "artefact_ready"})
    return ProcurementRequestResult(
        draft=draft,
        target_name=target.name,
        source_trace=source_trace,
    )


async def _retrieve_procurement_evidence_pool(
    retriever: DocumentRetriever,
    *,
    project: Project,
    project_queries: tuple[EvidenceQuery, ...],
    platform_query: str,
    artefact_context: ProcurementArtefactContext | None,
) -> GenerationEvidencePool:
    project_filters = RetrievalFilters(
        active_project_id=project.id,
        include_platform_knowledge=False,
    )
    requests = [
        GenerationRetrievalRequest(
            key=f"project:{index}:{query.key}",
            category=query.key,
            query=query.query,
            filters=project_filters,
            limit=3,
        )
        for index, query in enumerate(project_queries)
    ]
    requests.append(
        GenerationRetrievalRequest(
            key="platform:guidance",
            category="platform_guidance",
            query=platform_query,
            filters=RetrievalFilters(
                platform_knowledge_only=True,
                phase="reference",
            ),
            limit=5,
        )
    )
    retrieval_level = select_retrieval_level(
        structured_context_available=artefact_context is not None,
        current_artefact_available=False,
        project_evidence_required=(
            artefact_context is None or bool(artefact_context.critical_unknowns)
        ),
    )
    return await retrieve_generation_evidence(
        retriever,
        requests,
        level=retrieval_level,
        budget=PROCUREMENT_RETRIEVAL_BUDGET,
    )


async def _bound_procurement_inputs(
    retriever: DocumentRetriever,
    *,
    project_evidence: list[dict[str, Any]],
    platform_knowledge: list[dict[str, Any]],
    level: RetrievalLevel,
    budget: RetrievalBudget,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], EvidencePoolStats]:
    """Apply one final budget to every narrative input, including required seeds."""
    records: dict[uuid.UUID, dict[str, Any]] = {}

    def passages_for(
        items: list[dict[str, Any]],
        *,
        category: str,
        path_key: str,
    ) -> tuple[SourcePassage, ...]:
        passages: list[SourcePassage] = []
        for index, item in enumerate(items):
            path = str(item.get(path_key) or "").strip()
            document_key = str(item.get("document_id") or path or index)
            chunk_key = str(
                item.get("chunk_id")
                or f"{path}:{item.get('page_or_section') or item.get('section') or index}"
            )
            document_id = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"clerk:procurement:document:{document_key}",
            )
            chunk_id = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"clerk:procurement:chunk:{category}:{chunk_key}",
            )
            records[chunk_id] = item
            passages.append(
                SourcePassage(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    chunk_index=index,
                    content=str(item.get("snippet") or ""),
                    page_or_section=(
                        item.get("page_or_section") or item.get("section")
                    ),
                    project="active-project" if category == "project" else "sitewise",
                    project_id=None,
                    phase="project" if category == "project" else "reference",
                    source_type=str(item.get("source_type") or category),
                    document_class=str(item.get("document_class") or category),
                    filename=str(
                        item.get("filename")
                        or item.get("title")
                        or path.rsplit("/", maxsplit=1)[-1]
                        or "source"
                    ),
                    relative_path=path,
                    document_metadata=(
                        item.get("document_metadata")
                        if isinstance(item.get("document_metadata"), dict)
                        else None
                    ),
                    score=float(item.get("score") or 0.0),
                )
            )
        return tuple(passages)

    pool = await retrieve_generation_evidence(
        retriever,
        (),
        preloaded=(
            GenerationEvidenceInput(
                key="final:platform",
                category="platform",
                passages=passages_for(
                    platform_knowledge,
                    category="platform",
                    path_key="path",
                ),
            ),
            GenerationEvidenceInput(
                key="final:project",
                category="project",
                passages=passages_for(
                    project_evidence,
                    category="project",
                    path_key="relative_path",
                ),
            ),
        ),
        level=level,
        budget=budget,
    )

    def restore(key: str) -> list[dict[str, Any]]:
        return [
            {**records[passage.chunk_id], "snippet": passage.content}
            for passage in pool.passages_for(key)
        ]

    if pool.stats is None:  # pragma: no cover - the shared contract always sets it
        raise RuntimeError("Procurement retrieval did not publish budget statistics")
    return restore("final:project"), restore("final:platform"), pool.stats


def _project_evidence_from_pool(
    pool: GenerationEvidencePool,
    queries: tuple[EvidenceQuery, ...],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for index, query in enumerate(queries):
        for passage in pool.passages_for(f"project:{index}:{query.key}"):
            evidence.append(_project_evidence_item(query, passage))
    return evidence


def _select_procurement_seed_knowledge(
    *,
    document: ProcurementDocument,
    project: Project,
    target: ProcurementTarget,
    generation_context: ProjectGenerationContext | None,
) -> SeedKnowledgeSelection:
    artefact_type = document.seed_artefact_type
    target_kwargs = (
        {"discipline": target.name}
        if artefact_type == "rfp"
        else {"package": target.name}
    )
    kwargs = {
        **target_kwargs,
        "required_paths": document.platform_guidance_paths(target),
        "workflow": document.knowledge_workflow,
    }
    if generation_context is not None:
        return select_seed_knowledge(
            artefact_type,
            generation_context,
            **kwargs,
        )
    return select_seed_knowledge_for_project(
        artefact_type,
        project,
        **kwargs,
    )


def _artefact_type_for_workflow(workflow: str) -> ArtefactType:
    return "rfp" if workflow == "consultant-procurement" else "rft"


def _merge_project_evidence(
    retrieved: list[dict[str, Any]],
    supplemental: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge complete document registers without duplicating retrieved passages."""
    merged = list(retrieved)
    index_by_path = {
        str(item.get("relative_path") or "").strip(): index
        for index, item in enumerate(merged)
        if str(item.get("relative_path") or "").strip()
    }
    for item in supplemental:
        path = str(item.get("relative_path") or "").strip()
        existing_index = index_by_path.get(path) if path else None
        if existing_index is None:
            if path:
                index_by_path[path] = len(merged)
            merged.append(item)
            continue

        existing = merged[existing_index]
        existing_metadata = existing.get("document_metadata")
        supplemental_metadata = item.get("document_metadata")
        merged[existing_index] = {
            **item,
            **existing,
            "document_metadata": {
                **(existing_metadata if isinstance(existing_metadata, dict) else {}),
                **(
                    supplemental_metadata
                    if isinstance(supplemental_metadata, dict)
                    else {}
                ),
            },
        }
    return merged


def _platform_knowledge_from_pool(
    pool: GenerationEvidencePool,
    *,
    allowed_paths: set[str],
) -> list[dict[str, Any]]:
    knowledge: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for passage in pool.passages_for("platform:guidance"):
        path = str(_attr(passage, "relative_path", ""))
        if path and path in seen_paths:
            continue
        if (
            path
            and catalog_entry_for_path(path) is not None
            and path not in allowed_paths
        ):
            continue
        if path:
            seen_paths.add(path)
        knowledge.append(_platform_knowledge_item(passage))
    return knowledge


def _required_guidance_paths(
    project: Project,
    *,
    knowledge_workflow: str,
) -> list[str]:
    try:
        selection = select_seed_knowledge_for_project(
            _artefact_type_for_workflow(knowledge_workflow),
            project,
            workflow=knowledge_workflow,
        )
    except ValueError:
        return []
    return list(selection.workflow_paths)


async def _merge_required_guidance(
    session: AsyncSession,
    knowledge: list[dict[str, Any]],
    *,
    selection: SeedKnowledgeSelection,
    load_required_seed_content: bool,
) -> list[dict[str, Any]]:
    existing = {str(item.get("path")): index for index, item in enumerate(knowledge)}
    required_paths = set(selection.workflow_paths)
    paths = list(selection.guidance_paths)
    for path in paths:
        entry = catalog_entry_for_path(path)
        loaded = None
        if load_required_seed_content:
            loaded = await load_sections(
                session,
                path,
                None,
                max_chars=min(
                    settings.whole_document_content_chars,
                    PROCUREMENT_REQUIRED_GUIDANCE_MAX_CHARS,
                ),
            )
        if loaded is not None and loaded.passage is not None:
            item = {
                "path": path,
                "title": entry.title
                if entry is not None
                else path.rsplit("/", maxsplit=1)[-1],
                "section": None,
                "snippet": loaded.passage.content,
                "score": None,
                "source_type": (
                    "required-doctrine"
                    if path in required_paths
                    else "discipline-guidance"
                ),
            }
        else:
            item = {
                "path": path,
                "title": entry.title
                if entry is not None
                else path.rsplit("/", maxsplit=1)[-1],
                "section": None,
                "snippet": entry.summary if entry is not None else "",
                "score": None,
                "source_type": (
                    "required-doctrine"
                    if path in required_paths
                    else "discipline-guidance"
                ),
            }
        if path in existing:
            knowledge[existing[path]] = item
        else:
            existing[path] = len(knowledge)
            knowledge.append(item)
    priority = {path: index for index, path in enumerate(paths)}
    return sorted(
        knowledge,
        key=lambda item: (
            priority.get(str(item.get("path") or ""), len(priority)),
            str(item.get("title") or "").casefold(),
        ),
    )


def _project_evidence_item(query: EvidenceQuery, passage: Any) -> dict[str, Any]:
    metadata = _attr(passage, "document_metadata", None)
    return {
        "role": query.key,
        "role_label": query.label,
        "document_id": str(_attr(passage, "document_id", "")),
        "chunk_id": str(_attr(passage, "chunk_id", "")),
        "filename": _attr(passage, "filename", "Unknown document"),
        "relative_path": _attr(passage, "relative_path", ""),
        "page_or_section": _attr(passage, "page_or_section", None),
        "snippet": _compact(_attr(passage, "content", ""), limit=260),
        "score": _attr(passage, "score", None),
        "document_metadata": metadata if isinstance(metadata, dict) else {},
    }


def _platform_knowledge_item(passage: Any) -> dict[str, Any]:
    metadata = _attr(passage, "document_metadata", None) or {}
    return {
        "path": _attr(passage, "relative_path", ""),
        "title": _platform_title(passage, metadata),
        "section": _attr(passage, "page_or_section", None),
        "snippet": _compact(_attr(passage, "content", ""), limit=260),
        "score": _attr(passage, "score", None),
        "source_type": _attr(passage, "source_type", None),
    }


def _source_trace(
    *,
    document: ProcurementDocument,
    project_evidence: list[dict[str, Any]],
    issued_documents: list[dict[str, Any]],
    platform_knowledge: list[dict[str, Any]],
    forecast: dict[str, Any],
    assumptions: list[str],
    missing_inputs: list[str],
) -> dict[str, Any]:
    tools = [
        {
            "name": document.trace_tool_name,
            "purpose": document.trace_generation_purpose,
        },
        {"name": "search_documents", "purpose": document.trace_evidence_purpose},
        {
            "name": "search_platform_knowledge",
            "purpose": document.trace_guidance_purpose,
        },
    ]
    if forecast.get("used") and forecast.get("tool"):
        tools.append(
            {
                "name": forecast["tool"],
                "purpose": "Added an internal judgement allowance for budget context.",
            }
        )
    return {
        "project_documents": project_evidence,
        "issued_documents": issued_documents,
        "platform_knowledge": platform_knowledge,
        "forecast": forecast,
        "assumptions": assumptions,
        "missing_inputs": missing_inputs,
        "tools": tools,
    }


def _provenance_references(
    project_evidence: list[dict[str, Any]], platform_knowledge: list[dict[str, Any]]
) -> dict[str, list[str]]:
    """Match the PMP review contract with deterministic refs from retrieved inputs."""
    evidence_refs = _unique_paths(project_evidence, key="relative_path")
    context_refs = _unique_paths(platform_knowledge, key="path")
    seed_consulted = [ref for ref in context_refs if ref.startswith("seed/")]
    return {
        "seed_consulted": seed_consulted,
        "evidence_refs": evidence_refs,
        "context_refs": context_refs,
    }


def _unique_paths(items: list[dict[str, Any]], *, key: str) -> list[str]:
    return list(
        dict.fromkeys(
            str(item.get(key)).strip()
            for item in items
            if str(item.get(key) or "").strip()
        )
    )


async def _sync_draft_workspace(
    session: AsyncSession,
    *,
    project: Project,
    document: ProcurementDocument,
    draft: DraftArtifact,
    markdown: str,
) -> str:
    canonical_path = workspace_path_for(
        project,
        document,
        target_slug=draft.workflow_type.removeprefix(f"{document.document_key}_"),
        version=draft.version,
    )
    if draft.workspace_path != canonical_path:
        draft.workspace_path = canonical_path
        await session.flush()
        await session.refresh(draft)

    filename = Path(canonical_path).name
    content = markdown.encode("utf-8")
    storage_key = build_storage_key(str(project.id), canonical_path)
    content_hash = bytes_content_hash(content)
    await asyncio.to_thread(
        upload_project_file,
        storage_key=storage_key,
        content=content,
        filename=filename,
    )
    await upsert_workspace_file(
        session,
        project_id=project.id,
        workspace_path=canonical_path,
        filename=filename,
        storage_bucket=settings.supabase_storage_bucket,
        storage_key=storage_key,
        content_hash=content_hash,
        size_bytes=len(content),
        ingest_status="generated",
        ingest_error=None,
        source_document_id=None,
    )
    from app.projects.artefact_revisions import set_export_result_for_path

    await set_export_result_for_path(
        session,
        revision=draft,
        workspace_path=canonical_path,
        content_hash=content_hash,
    )
    return canonical_path


async def sync_procurement_draft_workspace(
    session: AsyncSession,
    *,
    project: Project,
    document: ProcurementDocument,
    draft: DraftArtifact,
    markdown: str | None = None,
) -> str:
    """Republish a standard procurement artefact after review or acceptance."""
    return await _sync_draft_workspace(
        session,
        project=project,
        document=document,
        draft=draft,
        markdown=markdown or draft.content_markdown,
    )


def _platform_title(passage: Any, metadata: dict[str, Any]) -> str:
    frontmatter = metadata.get("frontmatter") if isinstance(metadata, dict) else None
    if isinstance(frontmatter, dict) and isinstance(frontmatter.get("title"), str):
        return frontmatter["title"]
    filename = str(_attr(passage, "filename", "Platform knowledge"))
    return filename.rsplit("/", maxsplit=1)[-1]


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


def _compact(value: str, *, limit: int) -> str:
    cleaned = " ".join(str(value).split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "..."
