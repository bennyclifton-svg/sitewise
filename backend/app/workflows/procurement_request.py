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
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters
from app.sitewise.knowledge_catalog import (
    DOCTRINE_PATH,
    applicable_platform_paths,
    catalog_entry_for_path,
    load_sections,
    select_required_paths,
)
from app.storage.project_files import upload_project_file
from ingest.hashing import bytes_content_hash


CORE_PROCUREMENT_GUIDANCE_PATHS = (
    "seed/procurement-tendering-guide.md",
    "seed/cost-management-principles.md",
)


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

    def provenance_metadata(self, target: ProcurementTarget) -> dict[str, Any]:
        """Return document-specific metadata without duplicating publication."""
        return {}

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
    ) -> str | Awaitable[str]: ...


RetrieverFactory = Callable[[AsyncSession], DocumentRetriever]
NextVersion = Callable[..., Awaitable[int]]
CreateDraft = Callable[..., Awaitable[DraftArtifact]]
SyncWorkspace = Callable[..., Awaitable[str]]


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
    auto_commit: bool = True,
    retriever_factory: RetrieverFactory | None = None,
    next_version: NextVersion | None = None,
    create_draft: CreateDraft | None = None,
    sync_workspace: SyncWorkspace | None = None,
) -> ProcurementRequestResult:
    target = document.resolve_target(raw_target)
    # A page target guides the bounded narrative prompt. It must not cause a
    # complete procurement document to fail or be truncated at an arbitrary cap.
    pages = max(1, max_pages)
    retriever = (retriever_factory or DocumentRetriever)(session)

    project_evidence = await _retrieve_project_evidence(
        retriever,
        project=project,
        queries=document.evidence_queries(target),
    )
    project_evidence = _merge_project_evidence(
        project_evidence,
        await document.supplemental_project_evidence(
            session,
            project=project,
            target=target,
        ),
    )
    project_evidence = document.filter_project_evidence(project_evidence, target)
    issued_documents = await document.issued_documents(
        session,
        project=project,
        target=target,
        narrative_evidence=project_evidence,
    )
    if not issued_documents:
        issued_documents = list(project_evidence)
    platform_knowledge = await _retrieve_platform_knowledge(
        retriever,
        query=document.platform_query(target),
        project=project,
    )
    platform_knowledge = document.filter_platform_knowledge(
        platform_knowledge,
        target,
    )
    platform_knowledge = await _merge_required_guidance(
        session,
        platform_knowledge,
        project,
        knowledge_workflow=document.knowledge_workflow,
        load_required_seed_content=document.load_required_seed_content,
        target_guidance_paths=document.platform_guidance_paths(target),
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
    )
    markdown = await rendered if inspect.isawaitable(rendered) else rendered

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
    return ProcurementRequestResult(
        draft=draft,
        target_name=target.name,
        source_trace=source_trace,
    )


async def _retrieve_project_evidence(
    retriever: DocumentRetriever,
    *,
    project: Project,
    queries: tuple[EvidenceQuery, ...],
) -> list[dict[str, Any]]:
    filters = RetrievalFilters(
        active_project_id=project.id,
        include_platform_knowledge=False,
    )
    evidence: list[dict[str, Any]] = []
    seen_chunks: set[str] = set()
    for query in queries:
        passages = await retriever.retrieve(
            query.query,
            filters=filters,
            limit=3,
            include_neighbours=False,
        )
        for passage in passages:
            chunk_key = str(_attr(passage, "chunk_id", ""))
            if chunk_key and chunk_key in seen_chunks:
                continue
            if chunk_key:
                seen_chunks.add(chunk_key)
            evidence.append(_project_evidence_item(query, passage))
    return evidence


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


async def _retrieve_platform_knowledge(
    retriever: DocumentRetriever,
    *,
    query: str,
    project: Project,
) -> list[dict[str, Any]]:
    from app.sitewise.archetype_bridge import (
        effective_taxonomy,
        effective_work_scopes,
    )

    taxonomy = effective_taxonomy(project)
    passages = await retriever.retrieve(
        query,
        filters=RetrievalFilters(platform_knowledge_only=True, phase="reference"),
        limit=5,
        include_neighbours=False,
    )
    knowledge: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    applicable_paths = applicable_platform_paths(
        archetype=getattr(project, "archetype", None),
        building_class=taxonomy.building_class,
        work_type=taxonomy.work_type,
        subclasses=taxonomy.subclasses,
        work_scopes=effective_work_scopes(project),
        include_required=False,
    )
    for passage in passages:
        path = str(_attr(passage, "relative_path", ""))
        if path and path in seen_paths:
            continue
        if (
            path
            and catalog_entry_for_path(path) is not None
            and path not in applicable_paths
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
    from app.sitewise.archetype_bridge import (
        effective_taxonomy,
        effective_work_scopes,
    )

    archetype = getattr(project, "archetype", None)
    taxonomy = effective_taxonomy(project)
    building_class = taxonomy.building_class
    work_type = taxonomy.work_type
    if not archetype and not building_class:
        return []
    try:
        resolved = select_required_paths(
            workflow=knowledge_workflow,
            archetype=archetype or "",
            building_class=building_class,
            work_type=work_type,
            subclasses=taxonomy.subclasses,
            work_scopes=effective_work_scopes(project),
        )
    except ValueError:
        return []
    guidance: list[str] = []
    for path in resolved:
        if path == DOCTRINE_PATH:
            continue
        entry = catalog_entry_for_path(path)
        if entry is not None and knowledge_workflow in entry.required_by:
            guidance.append(path)
    return guidance


async def _merge_required_guidance(
    session: AsyncSession,
    knowledge: list[dict[str, Any]],
    project: Project,
    *,
    knowledge_workflow: str,
    load_required_seed_content: bool,
    target_guidance_paths: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    existing = {str(item.get("path")): index for index, item in enumerate(knowledge)}
    required_paths = _required_guidance_paths(
        project,
        knowledge_workflow=knowledge_workflow,
    )
    paths = list(dict.fromkeys((*target_guidance_paths, *required_paths)))
    for path in paths:
        entry = catalog_entry_for_path(path)
        loaded = None
        if load_required_seed_content:
            loaded = await load_sections(
                session,
                path,
                None,
                max_chars=settings.whole_document_content_chars,
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
