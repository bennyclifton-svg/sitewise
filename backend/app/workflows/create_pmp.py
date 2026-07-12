import asyncio
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from openai import OpenAIError
from sqlalchemy import select

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.pmp_models import (
    pmp_model_metadata,
    resolve_pmp_model,
)
from app.assistant.run_agent import run_agent_with_retry
from app.config import settings
from app.database.activity_events import record_activity_events
from app.database.chats import create_message
from app.database.draft_artifacts import create_draft_artifact
from app.database.project import Project
from app.database.project_decisions import locked_selections, sync_decisions_from_markdown
from app.database.workspace_files import upsert_workspace_file
from app.inbox.paths import build_storage_key
from app.storage.project_files import upload_project_file
from app.database.source_document import SourceDocument
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters, SourcePassage
from app.retrieval.whole_document import load_platform_documents_by_paths
from app.schemas.projects import CreatePmpResponse, DraftArtifactResponse, WorkflowTraceEvent
from app.sitewise.gate import format_overlay_failure, overlay_status
from app.sitewise.archetype_bridge import effective_taxonomy
from app.sitewise.pmp_greenfield_brief import (
    build_greenfield_brief,
    greenfield_markers_missing,
    greenfield_quality_markers,
    greenfield_structure_violations,
)
from app.sitewise.pmp_evidence_validation import (
    evidence_grounded_violations,
    sanitize_evidence_grounded_markdown,
    sync_document_control_version,
    taxonomy_provenance_violations,
)
from app.sitewise.pmp_coverage import (
    backfill_corpus_coverage,
    format_corpus_coverage_requirements,
)
from app.sitewise.pmp_length import length_violations, pmp_word_count
from app.sitewise.pmp_decisions import (
    decision_violations,
    format_decision_option_sets,
    format_locked_decisions,
    restamp_decisions,
)
from app.sitewise.pmp_sources import (
    document_title_for_role,
    required_platform_paths,
    required_section_headings,
    seed_consulted_includes_required,
)
from app.sitewise.pmp_seed_routing import load_pmp_seed_sections
from app.sitewise.pmp_sweep import sweep_current_pmp_corpus
from app.sitewise.pmp_taxonomy_context import pmp_taxonomy_context, project_has_taxonomy
from ingest.hashing import bytes_content_hash

WORKFLOW_TYPE = "create_pmp"
RUNTIME_NAME = "clerk-sitewise-create-pmp"
RUNTIME_HYBRID_NAME = "clerk-sitewise-create-pmp-hybrid"
RUNTIME_ADAPTIVE_SCAFFOLD_NAME = "clerk-sitewise-create-pmp-adaptive-scaffold"
HYBRID_NARRATIVE_MAX_ATTEMPTS = 3
CREATE_PMP_PROJECT_QUERY = (
    "project management plan brief scope risks programme cost authorities mobilisation"
)
CREATE_PMP_PLATFORM_CONTENT_CHARS = 16_000
CREATE_PMP_CHUNK_EXCERPT_CHARS = 1_200
CREATE_PMP_EVIDENCE_DOC_CHARS = 8_000
CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS = 8

MOBILISATION_EVIDENCE_PATH_MARKERS: tuple[str, ...] = (
    "engagement-letter",
    "engagement_letter",
    "fee-proposal",
    "fee_proposal",
    "00-brief",
    "owner-brief",
    "project-brief",
)
_INSTRUCTIONS_PATH = Path(__file__).with_name("create_pmp_instructions.md")

DraftMode = Literal["evidence_grounded", "platform_seeded"]


class PmpDraftOutput(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    markdown: str = Field(min_length=200)
    seed_consulted: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    context_refs: list[str] = Field(default_factory=list)


class WorkflowValidationError(Exception):
    """Raised when a workflow output is not safe to persist."""


def _upstream_failure_message(exc: Exception, *, operation: str) -> str:
    status_code = getattr(exc, "status_code", None)
    if status_code == 401:
        return (
            f"Create PMP could not {operation} because OpenAI authentication failed. "
            "Check OPENAI_API_KEY on the backend."
        )
    if status_code == 429:
        return (
            f"Create PMP could not {operation} because OpenAI rate limit or quota was reached. "
            "Wait a moment and try again."
        )
    if status_code in {500, 502, 503, 504}:
        return (
            f"Create PMP could not {operation} because OpenAI is temporarily unavailable. "
            "Try again shortly."
        )
    if status_code == 400:
        return (
            f"Create PMP could not {operation} because OpenAI rejected the request. "
            "Check the configured model and prompt size."
        )
    if isinstance(exc, UnexpectedModelBehavior):
        return (
            f"Create PMP could not {operation} because the language model returned an "
            "unexpected response. Try again, and check the configured chat model if it persists."
        )
    return (
        f"Create PMP could not {operation} because the OpenAI request failed. "
        "Check backend model configuration and network access."
    )


def _upstream_failure_metadata(exc: Exception, *, model: str | None = None) -> dict[str, object]:
    metadata: dict[str, object] = {"error_type": exc.__class__.__name__}
    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        metadata["status_code"] = status_code
    if model:
        metadata["model"] = model
    return metadata


def _load_agent_instructions() -> str:
    return _INSTRUCTIONS_PATH.read_text(encoding="utf-8")


create_pmp_agent = Agent(
    f"openai-chat:{settings.pmp_model}",
    output_type=PmpDraftOutput,
    instructions=_load_agent_instructions(),
    defer_model_check=True,
)


def _trace(step: str, status: str, message: str, **metadata) -> WorkflowTraceEvent:
    return WorkflowTraceEvent(
        step=step,
        status=status,
        message=message,
        metadata={key: value for key, value in metadata.items() if value is not None},
    )


def _source_ref(passage: SourcePassage) -> str:
    return f"{passage.source_type or 'source'}:{passage.relative_path}#chunk={passage.chunk_id}"


def _is_platform_passage(passage: SourcePassage) -> bool:
    if passage.source_type in ("doctrine", "reference"):
        return True
    metadata = passage.document_metadata or {}
    return metadata.get("knowledge_scope") == "platform"


def _is_project_passage(passage: SourcePassage, project_slug: str) -> bool:
    return passage.source_type == "project_evidence" and passage.project == project_slug


def _is_whole_document_passage(passage: SourcePassage) -> bool:
    metadata = passage.chunk_metadata or {}
    return bool(metadata.get("whole_document"))


def _source_excerpt_chars(passage: SourcePassage) -> int:
    if _is_project_passage(passage, passage.project or "") and _is_whole_document_passage(
        passage
    ):
        return CREATE_PMP_EVIDENCE_DOC_CHARS
    return CREATE_PMP_CHUNK_EXCERPT_CHARS


def _format_sources(passages: list[SourcePassage]) -> str:
    blocks = []
    for passage in passages:
        excerpt_limit = _source_excerpt_chars(passage)
        blocks.append(
            "\n".join(
                [
                    f"ref: {_source_ref(passage)}",
                    f"project: {passage.project}",
                    f"source_type: {passage.source_type}",
                    f"filename: {passage.filename}",
                    f"relative_path: {passage.relative_path}",
                    f"excerpt: {passage.content[:excerpt_limit]}",
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


def _format_required_sections(user_role: str, *, project: Project | None = None) -> str:
    return "\n".join(
        f"- {heading}" for heading in required_section_headings(user_role, project=project)
    )


def _format_mandatory_seeds(paths: list[str]) -> str:
    return "\n".join(f"- {path}" for path in paths if path.startswith("seed/"))


def _seed_section_refs_by_section(
    passages: list[SourcePassage],
) -> dict[str, tuple[str, ...]]:
    refs: dict[str, list[str]] = {}
    for passage in passages:
        metadata = passage.chunk_metadata or {}
        section_id = metadata.get("pmp_section")
        section_refs = metadata.get("seed_section_refs")
        if not isinstance(section_id, str) or not isinstance(section_refs, list):
            continue
        bucket = refs.setdefault(section_id, [])
        for ref in section_refs:
            if isinstance(ref, str) and ref not in bucket:
                bucket.append(ref)
    return {section: tuple(values) for section, values in refs.items()}


def _target_words() -> int:
    return (settings.pmp_min_words + settings.pmp_max_words) // 2


def _format_project_taxonomy(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        return "Project taxonomy: legacy archetype-only project."
    scale = ", ".join(f"{key}={value}" for key, value in context.scale.items()) or "TBC"
    complexity = (
        ", ".join(f"{key}={value}" for key, value in context.complexity.items())
        or "TBC"
    )
    return "\n".join(
        [
            "Project taxonomy:",
            f"- building_class: {context.building_class}",
            f"- work_type: {context.work_type or 'TBC'}",
            f"- subclasses: {', '.join(context.subclasses) or 'TBC'}",
            f"- scale: {scale}",
            f"- complexity: {complexity}",
            f"- work_scope: {', '.join(context.work_scope) or 'TBC'}",
            f"- derived_risk_flags: {', '.join(context.risk_flag_values) or 'none'}",
        ]
    )


def _format_section_budgets(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        return "Per-section word budgets: not applicable to legacy archetype draft."
    return "\n".join(
        [
            "Per-section word budgets:",
            *[
                f"- {section_id}: ~{int(weight * _target_words())} words"
                for section_id, weight in context.section_weights.items()
            ],
        ]
    )


def _format_loaded_seed_sections(passages: list[SourcePassage]) -> str:
    refs = [
        ref
        for values in _seed_section_refs_by_section(passages).values()
        for ref in values
    ]
    if not refs:
        return "Loaded seed sections: none routed at section level."
    return "\n".join(["Loaded seed sections:", *[f"- {ref}" for ref in refs]])


def normalize_pmp_markdown(markdown: str) -> str:
    """Fix common model formatting that breaks GFM table rendering."""
    fixed: list[str] = []
    for line in markdown.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("- |"):
            fixed.append(stripped[2:].lstrip())
        else:
            fixed.append(line)
    return "\n".join(fixed)


def _markdown_has_section(markdown: str, heading: str) -> bool:
    target = heading.strip().lower()
    for line in markdown.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("## ") and stripped[3:].strip() == target:
            return True
    return False


def markdown_section_headings(markdown: str) -> list[str]:
    headings: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            headings.append(stripped[3:].strip())
    return headings


def _source_document_passage(doc: SourceDocument) -> SourcePassage:
    return SourcePassage(
        chunk_id=doc.id,
        document_id=doc.id,
        chunk_index=0,
        content=doc.normalized_content[:CREATE_PMP_EVIDENCE_DOC_CHARS],
        page_or_section=None,
        project=doc.project,
        phase=doc.phase,
        source_type=doc.source_type or "project_evidence",
        document_class=doc.document_class,
        filename=doc.filename,
        relative_path=doc.relative_path,
        document_metadata=doc.document_metadata,
        chunk_metadata={"whole_document": True},
        score=1.0,
    )


async def list_mobilisation_evidence_paths(
    session: AsyncSession,
    *,
    project_slug: str,
    limit: int = CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS,
) -> list[str]:
    """Return relative paths for mobilisation-relevant project evidence."""
    result = await session.execute(
        select(SourceDocument.relative_path).where(
            SourceDocument.project == project_slug,
        )
    )
    paths: list[str] = []
    for relative_path in result.scalars().all():
        path_lower = relative_path.lower()
        if any(marker in path_lower for marker in MOBILISATION_EVIDENCE_PATH_MARKERS):
            paths.append(relative_path)
        if len(paths) >= limit:
            break
    return paths


async def load_mobilisation_project_evidence_documents(
    session: AsyncSession,
    *,
    project_slug: str,
    semantic_relative_paths: list[str],
) -> list[SourcePassage]:
    """Load whole mobilisation evidence docs (semantic hits + path-marked files)."""
    marker_paths = await list_mobilisation_evidence_paths(
        session,
        project_slug=project_slug,
    )
    merged_paths = list(
        dict.fromkeys(semantic_relative_paths + marker_paths)
    )[:CREATE_PMP_MAX_MOBILISATION_EVIDENCE_DOCS]
    if not merged_paths:
        return []
    return await load_project_evidence_whole_documents(
        session,
        project_slug=project_slug,
        relative_paths=merged_paths,
    )


async def load_project_evidence_whole_documents(
    session: AsyncSession,
    *,
    project_slug: str,
    relative_paths: list[str],
) -> list[SourcePassage]:
    """Replace chunk excerpts with whole-document passages for mobilisation evidence."""
    if not relative_paths:
        return []

    result = await session.execute(
        select(SourceDocument).where(
            SourceDocument.project == project_slug,
            SourceDocument.relative_path.in_(relative_paths),
        )
    )
    passages: list[SourcePassage] = []
    for doc in result.scalars().all():
        passages.append(_source_document_passage(doc))
    return passages


async def expand_project_passages_to_whole_documents(
    session: AsyncSession,
    *,
    project: Project,
    passages: list[SourcePassage],
) -> list[SourcePassage]:
    """Prefer whole mobilisation documents over semantic-search chunks."""
    project_paths = list(
        dict.fromkeys(
            passage.relative_path
            for passage in passages
            if _is_project_passage(passage, project.slug)
        )
    )
    if not project_paths:
        return passages

    whole_passages = await load_project_evidence_whole_documents(
        session,
        project_slug=project.slug,
        relative_paths=project_paths,
    )
    if not whole_passages:
        return passages

    whole_by_path = {passage.relative_path: passage for passage in whole_passages}
    merged: list[SourcePassage] = []
    seen_project_paths: set[str] = set()
    for passage in passages:
        if not _is_project_passage(passage, project.slug):
            merged.append(passage)
            continue
        if passage.relative_path in seen_project_paths:
            continue
        seen_project_paths.add(passage.relative_path)
        merged.append(whole_by_path.get(passage.relative_path, passage))
    return merged


def _taxonomy_metadata_values(project: Project, key: str) -> tuple[str, ...]:
    metadata = project.project_metadata
    if not isinstance(metadata, dict):
        return ()
    taxonomy = metadata.get("taxonomy")
    values = None
    if isinstance(taxonomy, dict):
        values = taxonomy.get(key)
    if values is None:
        values = metadata.get(key)
    if isinstance(values, str):
        return (values,) if values.strip() else ()
    if not isinstance(values, list):
        return ()

    result: list[str] = []
    for item in values:
        if isinstance(item, str) and item.strip():
            result.append(item)
        elif isinstance(item, dict):
            value = item.get("value")
            if isinstance(value, str) and value.strip():
                result.append(value)
    return tuple(result)


async def retrieve_create_pmp_sources(
    session: AsyncSession,
    *,
    project: Project,
) -> tuple[list[SourcePassage], int, int, DraftMode, list[str]]:
    """Load mandatory platform sources; load mobilisation project evidence whole documents."""
    mandatory_paths = required_platform_paths(
        archetype=project.archetype or "",
        user_role=project.user_role or "",
        project=project,
    )
    platform_passages, missing_paths = await load_platform_documents_by_paths(
        session,
        mandatory_paths,
        content_chars=CREATE_PMP_PLATFORM_CONTENT_CHARS,
    )
    if getattr(project, "building_class", None) is not None:
        taxonomy = effective_taxonomy(project)
        routed = await load_pmp_seed_sections(
            session,
            selected_paths=mandatory_paths,
            building_class=taxonomy.building_class,
            work_type=taxonomy.work_type,
            subclasses=taxonomy.subclasses,
            work_scope=_taxonomy_metadata_values(project, "work_scope"),
            risk_flags=_taxonomy_metadata_values(project, "risk_flags"),
            max_chars=CREATE_PMP_PLATFORM_CONTENT_CHARS,
        )
        platform_passages.extend(routed.passages)
        missing_paths.extend(routed.missing_required_refs)

    retriever = DocumentRetriever(session)
    project_passages = await retriever.retrieve(
        CREATE_PMP_PROJECT_QUERY,
        filters=RetrievalFilters(
            active_project=project.slug,
            include_platform_knowledge=False,
        ),
        limit=8,
        include_neighbours=False,
    )
    semantic_paths = list(
        dict.fromkeys(
            passage.relative_path
            for passage in project_passages
            if _is_project_passage(passage, project.slug)
        )
    )
    mobilisation_passages = await load_mobilisation_project_evidence_documents(
        session,
        project_slug=project.slug,
        semantic_relative_paths=semantic_paths,
    )
    if mobilisation_passages:
        passages = mobilisation_passages + platform_passages
        project_count = len(mobilisation_passages)
    else:
        passages = platform_passages
        project_count = 0

    platform_count = sum(1 for passage in passages if _is_platform_passage(passage))
    draft_mode: DraftMode = (
        "evidence_grounded" if project_count > 0 else "platform_seeded"
    )
    return passages, project_count, platform_count, draft_mode, missing_paths


async def retrieve_project_evidence_delta(
    session: AsyncSession,
    *,
    project_slug: str,
    since: datetime,
    limit: int = 8,
) -> list[SourcePassage]:
    """Load project documents created or updated after the baseline revision timestamp."""
    result = await session.execute(
        select(SourceDocument)
        .where(
            SourceDocument.project == project_slug,
            SourceDocument.updated_at > since,
        )
        .order_by(SourceDocument.updated_at.desc())
        .limit(limit)
    )
    passages: list[SourcePassage] = []
    for doc in result.scalars().all():
        content = doc.normalized_content[:CREATE_PMP_EVIDENCE_DOC_CHARS]
        passages.append(
            SourcePassage(
                chunk_id=doc.id,
                document_id=doc.id,
                chunk_index=0,
                content=content,
                page_or_section=None,
                project=doc.project,
                phase=doc.phase,
                source_type=doc.source_type or "project_evidence",
                document_class=doc.document_class,
                filename=doc.filename,
                relative_path=doc.relative_path,
                document_metadata=doc.document_metadata,
                chunk_metadata={"evidence_delta": True, "whole_document": True},
                score=1.0,
            )
        )
    return passages


def _role_drafting_note(
    *,
    user_role: str,
    draft_mode: DraftMode,
    state: str,
    project: Project | None = None,
) -> str:
    title = document_title_for_role(user_role, project=project)
    if draft_mode == "platform_seeded":
        evidence_note = (
            "No project evidence is available yet. Draft from the mandatory doctrine and "
            "seed sources only. Follow the Greenfield content contract in full — include "
            "archetype- and role-specific checklists, tables, and risks even when every "
            "value is Assumption. Leave evidence_refs empty."
        )
    else:
        evidence_note = (
            "Project evidence is available. Follow the full section scaffold below in full "
            "(tables, checklists, registers). Ground factual project statements in "
            "evidence_refs where evidence exists. Where evidence is silent, keep "
            "**Assumption**-labelled scaffold rows. Do NOT replace the PMP with an "
            "engagement summary or narrow consultant memo. "
            "If engagement letter or fee proposal appears in Sources, do NOT label them "
            "missing or 'not yet filed'. State Evidence on file in document control, "
            "include the evidence map table, upgrade Facts in the internal audit layer, "
            "and omit false workflow warnings (e.g. 'no engagement letter found'). "
            "Never write these phrases anywhere in Internal audit Assumptions or "
            "Workflow warnings when the document is in Sources: "
            "'no engagement letter', 'engagement instruments gap', "
            "'pre-brief / pre-engagement', 'project evidence (none yet)'. "
            "In **Evidence basis and document control**, include a line starting "
            "'Evidence on file:' and an evidence map table with columns "
            "'| Section | Evidence status | Ref |'. "
            "In **Internal audit layer**, list at least two **Facts** bullets "
            "grounded in Sources (not Assumptions). "
            "In **Project overview**, ground owner names, site address, and dwelling "
            "type from Sources — do not label them Assumption when the evidence states them."
        )

    if draft_mode == "platform_seeded" and project_has_taxonomy(project):
        evidence_note = (
            "No project evidence is available yet. Draft scaffold-first from project "
            "taxonomy, user setup fields, doctrine, and loaded seed sections only. "
            "Keep the primary document inside the 2-4 page band. Leave evidence_refs "
            "empty and do not write Grounded claims."
        )

    state_note = (
        f"State is {state}. Apply NSW-deep-default guidance with inline non-NSW gap "
        "callouts where state-specific instruments differ."
        if state != "NSW"
        else "State is NSW (deep default in seeds)."
    )

    if user_role == "architect-pm":
        role_note = (
            "Produce the Architect-PM PMP facet: owner-side governance plan with two-brief "
            "discipline, role declaration placeholders, builder evidence verification, and "
            "the baseline 3-stage programme regime unless evidence requires more detail."
        )
    else:
        role_note = (
            f"Produce a {title} using the loaded role overlay and setup-and-commission "
            "guide. This is mobilisation/setup framing for the declared role, not an "
            "architect-PM PMP unless user_role is architect-pm."
        )

    return "\n".join([evidence_note, state_note, role_note])


def build_create_pmp_prompt(
    *,
    project: Project,
    passages: list[SourcePassage],
    draft_mode: DraftMode,
    run_date: date,
    validation_feedback: str | None = None,
    locked_decisions: dict[str, str] | None = None,
    coverage_requirements: str | None = None,
) -> str:
    """Assemble the Create PMP prompt with cache-friendly ordering.

    Static platform knowledge leads, stable per-project framing follows, and
    per-run volatile content (locked decisions, run date, coverage list,
    project evidence, retry feedback) trails — so OpenAI prefix caching hits
    the heavy static prefix across runs and retries.
    """
    user_role = project.user_role or ""
    mandatory_paths = required_platform_paths(
        archetype=project.archetype or "",
        user_role=user_role,
        project=project,
    )
    taxonomy_context = pmp_taxonomy_context(project)
    seed_section_refs = _seed_section_refs_by_section(passages)
    platform_passages = [passage for passage in passages if _is_platform_passage(passage)]
    evidence_passages = [
        passage for passage in passages if not _is_platform_passage(passage)
    ]

    prompt_parts = [
        "Sources (platform doctrine and seed):\n" + _format_sources(platform_passages),
        f"Project: {project.title}",
        f"Workspace path: {project.workspace_path}",
        (
            "Overlays: "
            f"archetype={project.archetype}, "
            f"user_role={project.user_role}, "
            f"state={project.state}"
        ),
        f"Draft mode: {draft_mode}",
        f"Required document title: {document_title_for_role(user_role, project=project)}",
        _role_drafting_note(
            user_role=user_role,
            draft_mode=draft_mode,
            state=project.state or "NSW",
            project=project,
        ),
        "Required PM-facing sections (use these exact ## headings):",
        _format_required_sections(user_role, project=project),
        "Mandatory seed paths (must all appear in seed_consulted):",
        _format_mandatory_seeds(mandatory_paths),
    ]
    if taxonomy_context is not None:
        prompt_parts.extend(
            [
                _format_project_taxonomy(project),
                _format_section_budgets(project),
                _format_loaded_seed_sections(passages),
                format_decision_option_sets(project),
                (
                    "Decision grounding: for every required decision id, search Sources "
                    "before using default_hint. If evidence nominates a matching product "
                    "or system (e.g. Caesarstone/reconstituted stone → engineered_stone), "
                    "select that option with evidenced=true and cite it in rationale. "
                    "Use evidenced=false and placeholder language only when Sources are silent."
                ),
                (
                    "Taxonomy PMP rules: primary document is 2-4 A4 pages; use a compact "
                    "snapshot metadata table; cite specific AS/NCC refs from loaded seed "
                    "sections; keep risks and actions to top ~8 rows each; do not use "
                    "pretrained domain content where a required seed section is missing."
                ),
            ]
        )
    archetype = project.archetype or ""
    state = project.state or "NSW"
    prompt_parts.append(
        build_greenfield_brief(
            archetype=archetype,
            user_role=user_role,
            state=state,
            draft_mode=draft_mode,
            building_class=taxonomy_context.building_class if taxonomy_context else None,
            work_type=taxonomy_context.work_type if taxonomy_context else None,
            subclasses=taxonomy_context.subclasses if taxonomy_context else (),
            scale=taxonomy_context.scale if taxonomy_context else None,
            complexity=taxonomy_context.complexity if taxonomy_context else None,
            work_scope=taxonomy_context.work_scope if taxonomy_context else (),
            risk_flags=taxonomy_context.risk_flags if taxonomy_context else (),
            section_weights=taxonomy_context.section_weights if taxonomy_context else None,
            seed_section_refs=seed_section_refs,
            user_provided_fields=(
                taxonomy_context.user_provided_fields if taxonomy_context else None
            ),
            target_words=_target_words() if taxonomy_context else None,
        )
    )
    if draft_mode == "platform_seeded":
        depth_markers = greenfield_quality_markers(
            archetype=archetype,
            user_role=user_role,
        )
        marker_list = ", ".join(depth_markers)
        prompt_parts.append(
            "Required depth markers (each term MUST appear at least once in the markdown body, "
            f"case-insensitive): {marker_list}"
        )
    prompt_parts.append(
        "Use the source refs exactly when filling evidence_refs/context_refs. "
        "Populate context_refs with doctrine and seed refs you used."
    )

    # Volatile tail: everything below changes per run; keep it after the
    # cacheable prefix above.
    if taxonomy_context is not None:
        prompt_parts.append(format_locked_decisions(locked_decisions or {}))
    prompt_parts.append(
        f"Mobilisation run date: {run_date.isoformat()} — use for register "
        "due dates (2–4 weeks forward or relative phrasing; never past years)."
    )
    if coverage_requirements:
        prompt_parts.extend(
            [
                "Mandatory current-corpus coverage (carry each item into the relevant section):",
                coverage_requirements,
                (
                    "Do not collapse these into generic prose. Carry the dates, values, "
                    "quantities, scope items, and constraints into the relevant sections, "
                    "and include every active project document path in evidence_refs."
                ),
            ]
        )
    if evidence_passages:
        prompt_parts.append(
            "Sources (project evidence):\n" + _format_sources(evidence_passages)
        )
    if validation_feedback:
        prompt_parts.append(
            "REVISION REQUIRED — your previous draft failed validation:\n"
            f"{validation_feedback}\n"
            "Regenerate the full draft fixing every issue. Ensure all required depth markers "
            "appear in the markdown body."
        )
    return "\n\n".join(prompt_parts)


async def run_create_pmp_model(
    *,
    project: Project,
    passages: list[SourcePassage],
    draft_mode: DraftMode,
    validation_feedback: str | None = None,
    chat_model: str | None = None,
    locked_decisions: dict[str, str] | None = None,
    coverage_requirements: str | None = None,
) -> PmpDraftOutput:
    prompt = build_create_pmp_prompt(
        project=project,
        passages=passages,
        draft_mode=draft_mode,
        run_date=date.today(),
        validation_feedback=validation_feedback,
        locked_decisions=locked_decisions,
        coverage_requirements=coverage_requirements,
    )
    resolved_model = chat_model.strip() if chat_model else resolve_pmp_model().execution_id
    result = await run_agent_with_retry(create_pmp_agent, prompt, model=resolved_model)
    return result.output


def _project_source_texts(
    passages: list[SourcePassage],
    *,
    project_slug: str,
) -> list[str]:
    return [
        passage.content
        for passage in passages
        if _is_project_passage(passage, project_slug) and passage.content.strip()
    ]


def _project_source_labels(
    passages: list[SourcePassage],
    *,
    project_slug: str,
) -> list[str]:
    """Filenames parallel to _project_source_texts, for evidence attribution."""
    return [
        passage.filename or passage.relative_path
        for passage in passages
        if _is_project_passage(passage, project_slug) and passage.content.strip()
    ]


def _evidence_refs_from_passages(
    passages: list[SourcePassage],
    project_slug: str,
) -> list[str]:
    return [
        _source_ref(passage)
        for passage in passages
        if _is_project_passage(passage, project_slug)
    ]


def _context_refs_from_passages(passages: list[SourcePassage]) -> list[str]:
    return [_source_ref(passage) for passage in passages if _is_platform_passage(passage)]


def _seed_consulted_from_passages(passages: list[SourcePassage]) -> list[str]:
    seeds: list[str] = []
    for passage in passages:
        if not _is_platform_passage(passage):
            continue
        if passage.source_type == "reference":
            metadata = passage.chunk_metadata or {}
            section_refs = metadata.get("seed_section_refs")
            if isinstance(section_refs, list) and section_refs:
                seeds.extend(str(ref) for ref in section_refs)
            else:
                seeds.append(passage.relative_path)
    return list(dict.fromkeys(seeds))


def _should_use_hybrid_compiler(project: Project, draft_mode: DraftMode) -> bool:
    return (
        settings.pmp_hybrid_compiler
        and draft_mode == "evidence_grounded"
        and (project.user_role or "") == "architect-pm"
        and not project_has_taxonomy(project)
    )


async def run_create_pmp_hybrid(
    *,
    project: Project,
    passages: list[SourcePassage],
    draft_mode: DraftMode,
    chat_model: str,
    project_source_texts: list[str],
    trace: list[WorkflowTraceEvent],
    locked_decisions: dict[str, str] | None = None,
) -> PmpDraftOutput:
    """Hybrid compiler path: extract → render → narrate → assemble."""
    from app.sitewise.mobilisation_evidence import extract_mobilisation_evidence_pack
    from app.sitewise.pmp_assembler import assemble_pmp_markdown
    from app.sitewise.pmp_renderer import render_pmp_scaffold
    from app.workflows.pmp_narrative import run_pmp_narrative_model

    user_role = project.user_role or ""
    evidence_refs = _evidence_refs_from_passages(passages, project.slug)
    source_labels = _project_source_labels(passages, project_slug=project.slug)
    pack = extract_mobilisation_evidence_pack(
        project_source_texts, evidence_refs, source_labels
    )
    trace.append(
        _trace(
            "extract",
            "complete",
            "Extracted mobilisation evidence pack.",
            gap_count=len(pack.gaps),
        )
    )

    scaffold = render_pmp_scaffold(project, pack, draft_mode)
    trace.append(
        _trace(
            "scaffold",
            "complete",
            "Rendered deterministic PMP scaffold.",
        )
    )

    validation_feedback: str | None = None
    run_date = date.today()
    for attempt in range(HYBRID_NARRATIVE_MAX_ATTEMPTS):
        try:
            narrative = await run_pmp_narrative_model(
                project=project,
                pack=pack,
                run_date=run_date,
                validation_feedback=validation_feedback,
                chat_model=chat_model,
            )
        except WorkflowValidationError as exc:
            if attempt < HYBRID_NARRATIVE_MAX_ATTEMPTS - 1:
                validation_feedback = str(exc)
                trace.append(
                    _trace(
                        "validation",
                        "retry",
                        f"PMP narrative validation failed — retrying: {validation_feedback}",
                        attempt=attempt + 1,
                    )
                )
                continue
            raise
        trace.append(
            _trace(
            "narrative",
            "complete",
            "Narrative model returned structured output.",
            attempt=attempt + 1,
            model=chat_model,
        )
    )

        markdown = assemble_pmp_markdown(
            scaffold,
            narrative,
            provenance={
                "compiler": "hybrid",
                "draft_mode": draft_mode,
            },
        )
        trace.append(
            _trace(
                "assemble",
                "complete",
                "Assembled hybrid PMP markdown.",
                attempt=attempt + 1,
            )
        )

        output = PmpDraftOutput(
            title=document_title_for_role(user_role, project=project),
            markdown=markdown,
            seed_consulted=_seed_consulted_from_passages(passages),
            evidence_refs=evidence_refs,
            context_refs=_context_refs_from_passages(passages),
        )
        output = _apply_locked_decisions(output, locked_decisions or {})
        try:
            validate_pmp_output(
                output,
                draft_mode,
                archetype=project.archetype or "",
                user_role=user_role,
                project=project,
                source_texts=project_source_texts,
            )
            return output
        except WorkflowValidationError as exc:
            if attempt < HYBRID_NARRATIVE_MAX_ATTEMPTS - 1:
                validation_feedback = str(exc)
                trace.append(
                    _trace(
                        "validation",
                        "retry",
                        f"Hybrid draft validation failed — retrying narrative: {validation_feedback}",
                        attempt=attempt + 1,
                    )
                )
                continue
            raise

    msg = "Hybrid Create PMP exhausted narrative validation retries."
    raise WorkflowValidationError(msg)


def validate_pmp_output(
    output: PmpDraftOutput,
    draft_mode: DraftMode,
    *,
    archetype: str,
    user_role: str,
    project: Project | None = None,
    source_texts: list[str] | None = None,
) -> None:
    taxonomy_context = pmp_taxonomy_context(project) if project is not None else None
    if not output.seed_consulted:
        raise WorkflowValidationError("Create PMP output did not identify seed consulted.")
    if not output.context_refs:
        raise WorkflowValidationError(
            "Create PMP output did not identify doctrine or seed context references."
        )
    if draft_mode == "evidence_grounded" and not output.evidence_refs:
        raise WorkflowValidationError("Create PMP output did not identify evidence references.")
    if "# " not in output.markdown and "## " not in output.markdown:
        raise WorkflowValidationError("Create PMP output is not structured as Markdown.")

    missing_seeds = seed_consulted_includes_required(
        output.seed_consulted,
        archetype=archetype,
        user_role=user_role,
        project=project,
    )
    if missing_seeds:
        joined = ", ".join(missing_seeds)
        raise WorkflowValidationError(
            f"Create PMP output did not record mandatory seeds in seed_consulted: {joined}"
        )

    missing_sections = [
        heading
        for heading in required_section_headings(user_role, project=project)
        if not _markdown_has_section(output.markdown, heading)
    ]
    if missing_sections:
        joined = ", ".join(missing_sections)
        raise WorkflowValidationError(
            f"Create PMP output is missing required sections: {joined}"
        )

    if draft_mode == "platform_seeded" and taxonomy_context is None:
        missing_markers = greenfield_markers_missing(
            output.markdown,
            archetype=archetype,
            user_role=user_role,
        )
        if missing_markers:
            joined = ", ".join(missing_markers)
            raise WorkflowValidationError(
                "Create PMP greenfield draft lacks required archetype/role depth markers: "
                f"{joined}"
            )

    if taxonomy_context is not None:
        provenance_issues = taxonomy_provenance_violations(
            output.markdown,
            draft_mode=draft_mode,
        )
        if provenance_issues:
            joined = "; ".join(provenance_issues)
            raise WorkflowValidationError(
                f"Create PMP taxonomy provenance issues: {joined}"
            )

    structure_issues = greenfield_structure_violations(
        output.markdown,
        archetype=archetype,
        user_role=user_role,
    )
    if structure_issues:
        joined = "; ".join(structure_issues)
        raise WorkflowValidationError(
            f"Create PMP draft structural issues: {joined}"
        )

    if draft_mode == "evidence_grounded":
        evidence_issues = evidence_grounded_violations(
            output.markdown,
            output.evidence_refs,
            source_texts=source_texts,
        )
        if evidence_issues:
            joined = "; ".join(evidence_issues)
            raise WorkflowValidationError(
                f"Create PMP evidence_grounded fidelity issues: {joined}"
            )

    decision_issues = decision_violations(output.markdown)
    if decision_issues:
        joined = "; ".join(decision_issues)
        raise WorkflowValidationError(f"Create PMP decision block issues: {joined}")


def _apply_locked_decisions(output: PmpDraftOutput, locked: dict[str, str]) -> PmpDraftOutput:
    if not locked:
        return output
    return output.model_copy(
        update={"markdown": restamp_decisions(output.markdown, locked)}
    )


PMP_WORKSPACE_FILENAME = "PMP.md"
PMP_WORKFLOW_TYPES = frozenset({WORKFLOW_TYPE, "update_pmp"})


def is_pmp_workflow(workflow_type: str) -> bool:
    return workflow_type in PMP_WORKFLOW_TYPES


def canonical_pmp_workspace_path(workspace_path: str) -> str | None:
    normalised = workspace_path.replace("\\", "/")
    marker = "/00-brief-pmp/"
    index = normalised.lower().find(marker)
    if index < 0:
        return None
    folder = normalised[: index + len(marker.rstrip("/"))]
    return f"{folder}/{PMP_WORKSPACE_FILENAME}"


def draft_workspace_path(project: Project, version: int) -> str:
    _ = version
    return f"{project.workspace_path}/00-brief-pmp/{PMP_WORKSPACE_FILENAME}"


async def save_pmp_workspace_file(
    session: AsyncSession,
    *,
    project: Project,
    markdown: str,
) -> str:
    workspace_path = draft_workspace_path(project, version=0)
    content = markdown.encode("utf-8")
    storage_key = build_storage_key(str(project.id), workspace_path)
    content_hash = bytes_content_hash(content)

    await asyncio.to_thread(
        upload_project_file,
        storage_key=storage_key,
        content=content,
        filename=PMP_WORKSPACE_FILENAME,
    )
    await upsert_workspace_file(
        session,
        project_id=project.id,
        workspace_path=workspace_path,
        filename=PMP_WORKSPACE_FILENAME,
        storage_bucket=settings.supabase_storage_bucket,
        storage_key=storage_key,
        content_hash=content_hash,
        size_bytes=len(content),
        ingest_status="generated",
        ingest_error=None,
        source_document_id=None,
    )
    return workspace_path


async def sync_pmp_draft_workspace(
    session: AsyncSession,
    *,
    project: Project,
    draft,
    markdown: str | None = None,
) -> str:
    canonical_path = draft_workspace_path(project, draft.version)
    if draft.workspace_path != canonical_path:
        draft.workspace_path = canonical_path
        await session.flush()
        await session.refresh(draft)
    return await save_pmp_workspace_file(
        session,
        project=project,
        markdown=markdown if markdown is not None else draft.content_markdown,
    )


async def run_create_pmp_workflow(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    project: Project,
    thread_id: uuid.UUID | None,
    chat_model: str | None = None,
) -> CreatePmpResponse:
    trace: list[WorkflowTraceEvent] = []
    run_id = uuid.uuid4()
    model_spec = resolve_pmp_model(chat_model)
    resolved_model = model_spec.execution_id
    model_metadata = pmp_model_metadata(model_spec)
    trace.append(
        _trace(
            "model_config",
            "complete",
            (
                f"PMP workflow model resolved to {model_spec.label}; "
                f"typed runner will execute via {model_spec.execution_id}."
            ),
            **model_metadata,
        )
    )

    gate = overlay_status(
        archetype=project.archetype,
        user_role=project.user_role,
        state=project.state,
        building_class=project.building_class,
        work_type=project.work_type,
    )
    if not gate.ready:
        message = format_overlay_failure(gate)
        trace.append(_trace("gate", "blocked", message))
        await _persist_trace_message(
            session,
            project_id=project.id,
            run_id=run_id,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="blocked",
        )
        return CreatePmpResponse(status="blocked", gate=gate, trace=trace, message=message)

    trace.append(_trace("gate", "passed", "SiteWise three-overlay gate passed."))
    locked_decisions = await locked_selections(session, project_id=project.id)

    try:
        (
            passages,
            project_count,
            platform_count,
            draft_mode,
            missing_paths,
        ) = await retrieve_create_pmp_sources(session, project=project)
    except ValueError as exc:
        message = str(exc)
        trace.append(_trace("retrieval", "failed", message))
        await _persist_trace_message(
            session,
            project_id=project.id,
            run_id=run_id,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreatePmpResponse(status="failed", gate=gate, trace=trace, message=message)
    except OpenAIError as exc:
        message = _upstream_failure_message(exc, operation="retrieve project evidence")
        trace.append(
            _trace(
                "retrieval",
                "failed",
                message,
                **_upstream_failure_metadata(exc, model=settings.openai_embedding_model),
            )
        )
        await _persist_trace_message(
            session,
            project_id=project.id,
            run_id=run_id,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreatePmpResponse(status="failed", gate=gate, trace=trace, message=message)

    if missing_paths:
        message = (
            "Create PMP could not load mandatory platform sources: "
            + ", ".join(missing_paths)
            + ". Ingest seed/ and docs/clerk-brief.md into the platform corpus."
        )
        trace.append(
            _trace(
                "retrieval",
                "failed",
                message,
                missing_paths=missing_paths,
            )
        )
        await _persist_trace_message(
            session,
            project_id=project.id,
            run_id=run_id,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreatePmpResponse(status="failed", gate=gate, trace=trace, message=message)

    active_corpus_documents: int | None = None
    if project_has_taxonomy(project):
        platform_passages = [
            passage for passage in passages if _is_platform_passage(passage)
        ]
        sweep_result = await sweep_current_pmp_corpus(session, project=project)
        trace.extend(sweep_result.trace_events)
        active_corpus_documents = len(sweep_result.listing.documents)
        if sweep_result.passages:
            passages = list(sweep_result.passages) + platform_passages
            project_count = len(sweep_result.passages)
            draft_mode = "evidence_grounded"
        else:
            passages = platform_passages
            project_count = 0
            draft_mode = "platform_seeded"

    retrieval_message = (
        "Swept all active project evidence and loaded mandatory SiteWise platform sources."
        if active_corpus_documents is not None and project_count > 0
        else "Retrieved project evidence and mandatory SiteWise platform sources."
        if project_count > 0
        else "No project evidence yet. Loaded mandatory doctrine and seed sources by overlay."
    )
    trace.append(
        _trace(
            "retrieval",
            "complete",
            retrieval_message,
            project_passages=project_count,
            platform_passages=platform_count,
            total_passages=len(passages),
            draft_mode=draft_mode,
            active_corpus_documents=active_corpus_documents,
            platform_retrieval="overlay_mandatory_paths",
            mandatory_seed_count=len(required_platform_paths(
                archetype=project.archetype or "",
                user_role=project.user_role or "",
                project=project,
            )),
        )
    )

    if project_count == 0 and platform_count == 0:
        message = (
            "Create PMP needs SiteWise doctrine and seed in the platform corpus, or project "
            "evidence after document intake. Ingest seed/ and docs/clerk-brief.md if the "
            "platform corpus is empty."
        )
        trace.append(_trace("validation", "failed", message))
        await _persist_trace_message(
            session,
            project_id=project.id,
            run_id=run_id,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreatePmpResponse(status="failed", gate=gate, trace=trace, message=message)

    project_source_texts = _project_source_texts(passages, project_slug=project.slug)
    project_source_labels = _project_source_labels(passages, project_slug=project.slug)
    required_evidence_refs = _evidence_refs_from_passages(passages, project.slug)
    coverage_required_evidence_refs = (
        required_evidence_refs
        if project_has_taxonomy(project) and draft_mode == "evidence_grounded"
        else []
    )
    coverage_requirements = (
        format_corpus_coverage_requirements(project_source_texts, project_source_labels)
        if coverage_required_evidence_refs
        else None
    )
    taxonomy_context = pmp_taxonomy_context(project)
    use_scaffold = taxonomy_context is not None and draft_mode == "platform_seeded"
    use_hybrid = _should_use_hybrid_compiler(project, draft_mode)
    runtime_name = (
        RUNTIME_ADAPTIVE_SCAFFOLD_NAME
        if use_scaffold
        else RUNTIME_HYBRID_NAME
        if use_hybrid
        else RUNTIME_NAME
    )
    try:
        if use_scaffold:
            from app.sitewise.mobilisation_evidence import MobilisationEvidencePack
            from app.sitewise.pmp_renderer import render_pmp_scaffold

            output = PmpDraftOutput(
                title=document_title_for_role(project.user_role or "", project=project),
                markdown=render_pmp_scaffold(
                    project,
                    MobilisationEvidencePack(),
                    draft_mode,
                    seed_section_refs=_seed_section_refs_by_section(passages),
                ),
                seed_consulted=_seed_consulted_from_passages(passages),
                evidence_refs=[],
                context_refs=_context_refs_from_passages(passages),
            )
            output.markdown = normalize_pmp_markdown(output.markdown)
            output = _apply_locked_decisions(output, locked_decisions)
            validate_pmp_output(
                output,
                draft_mode,
                archetype=project.archetype or "",
                user_role=project.user_role or "",
                project=project,
                source_texts=project_source_texts,
            )
            trace.append(
                _trace(
                    "scaffold",
                    "complete",
                    "Rendered adaptive taxonomy PMP scaffold.",
                    word_count=pmp_word_count(output.markdown),
                    target_words=_target_words(),
                    **model_metadata,
                )
            )
        elif use_hybrid:
            output = await run_create_pmp_hybrid(
                project=project,
                passages=passages,
                draft_mode=draft_mode,
                chat_model=resolved_model,
                project_source_texts=project_source_texts,
                trace=trace,
                locked_decisions=locked_decisions,
            )
            output.markdown = normalize_pmp_markdown(output.markdown)
            output.markdown = sanitize_evidence_grounded_markdown(
                output.markdown,
                output.evidence_refs,
                source_texts=project_source_texts,
            )
        else:
            validation_feedback: str | None = None
            max_attempts = 3
            for attempt in range(max_attempts):
                output = await run_create_pmp_model(
                    project=project,
                    passages=passages,
                    draft_mode=draft_mode,
                    validation_feedback=validation_feedback,
                    chat_model=resolved_model,
                    locked_decisions=locked_decisions,
                    coverage_requirements=coverage_requirements,
                )
                output.markdown = normalize_pmp_markdown(output.markdown)
                if draft_mode == "evidence_grounded":
                    output.markdown = sanitize_evidence_grounded_markdown(
                        output.markdown,
                        output.evidence_refs,
                        source_texts=project_source_texts,
                    )
                output = _apply_locked_decisions(output, locked_decisions)
                trace.append(
                    _trace(
                        "model",
                        "complete",
                        "Create PMP model run returned a typed draft output.",
                        **model_metadata,
                        draft_mode=draft_mode,
                        attempt=attempt + 1,
                    )
                )
                try:
                    validate_pmp_output(
                        output,
                        draft_mode,
                        archetype=project.archetype or "",
                        user_role=project.user_role or "",
                        project=project,
                        source_texts=project_source_texts,
                    )
                    break
                except WorkflowValidationError as exc:
                    if attempt < max_attempts - 1:
                        validation_feedback = str(exc)
                        trace.append(
                            _trace(
                                "validation",
                                "retry",
                                f"Greenfield draft validation failed — retrying model: {validation_feedback}",
                            )
                        )
                        continue
                    raise
    except WorkflowValidationError as exc:
        message = str(exc)
        trace.append(_trace("validation", "failed", message))
        await _persist_trace_message(
            session,
            project_id=project.id,
            run_id=run_id,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreatePmpResponse(status="failed", gate=gate, trace=trace, message=message)
    except (ModelAPIError, UnexpectedModelBehavior, OpenAIError) as exc:
        message = _upstream_failure_message(exc, operation="generate the draft")
        trace.append(
            _trace(
                "model",
                "failed",
                message,
                **_upstream_failure_metadata(exc, model=resolved_model),
                model_label=model_spec.label,
                model_provider=model_spec.provider,
                model_config_id=model_spec.configured_id,
            )
        )
        await _persist_trace_message(
            session,
            project_id=project.id,
            run_id=run_id,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreatePmpResponse(status="failed", gate=gate, trace=trace, message=message)

    trace.append(
        _trace(
            "validation",
            "passed",
            "Create PMP output passed validation.",
            draft_mode=draft_mode,
        )
    )

    if coverage_required_evidence_refs:
        coverage_backfill = backfill_corpus_coverage(
            output.markdown,
            output_evidence_refs=output.evidence_refs,
            required_evidence_refs=coverage_required_evidence_refs,
            source_texts=project_source_texts,
            source_labels=project_source_labels,
        )
        if coverage_backfill.backfilled_facts or coverage_backfill.added_evidence_refs:
            output.markdown = coverage_backfill.markdown
            output.evidence_refs = list(coverage_backfill.evidence_refs)
            trace.append(
                _trace(
                    "coverage",
                    "advisory",
                    (
                        "Coverage advisory (not enforced): backfilled "
                        f"{len(coverage_backfill.backfilled_facts)} evidence fact(s) "
                        "into the Evidence coverage register and merged "
                        f"{len(coverage_backfill.added_evidence_refs)} missing evidence ref(s)."
                    ),
                    backfilled_facts=[
                        f"{req.source}: {req.fact}"
                        for req in coverage_backfill.backfilled_facts
                    ],
                    added_evidence_refs=list(coverage_backfill.added_evidence_refs),
                )
            )

    if taxonomy_context is not None:
        length_advisories = length_violations(
            output.markdown,
            weights=taxonomy_context.section_weights,
            min_words=settings.pmp_min_words,
            max_words=settings.pmp_max_words,
        )
        if length_advisories:
            trace.append(
                _trace(
                    "length",
                    "advisory",
                    "Length advisory (not enforced): " + "; ".join(length_advisories),
                    word_count=pmp_word_count(output.markdown),
                    max_words=settings.pmp_max_words,
                )
            )

    existing_version = await _next_version_hint(session, project.id, WORKFLOW_TYPE)
    output.markdown = sync_document_control_version(output.markdown, existing_version)
    draft = await create_draft_artifact(
        session,
        project_id=project.id,
        workflow_type=WORKFLOW_TYPE,
        title=output.title,
        workspace_path=draft_workspace_path(project, existing_version),
        author_user_id=user_id,
        content_markdown=output.markdown,
        model=resolved_model,
        runtime=runtime_name,
        provenance_metadata={
            "draft_mode": draft_mode,
            "compiler": "adaptive_scaffold" if use_scaffold else "hybrid" if use_hybrid else "legacy",
            "model": resolved_model,
            "model_label": model_spec.label,
            "model_provider": model_spec.provider,
            "model_config_id": model_spec.configured_id,
            "model_source": model_spec.source,
            "model_execution_provider": model_spec.execution_provider,
            "model_execution_id": model_spec.execution_id,
            "seed_consulted": output.seed_consulted,
            "evidence_refs": output.evidence_refs,
            "context_refs": output.context_refs,
            "word_count": pmp_word_count(output.markdown),
            "pmp_min_words": settings.pmp_min_words,
            "pmp_max_words": settings.pmp_max_words,
            "section_weights": (
                taxonomy_context.section_weights if taxonomy_context is not None else None
            ),
            "trace": [event.model_dump() for event in trace],
            "retrieval": {
                "project_passages": project_count,
                "platform_passages": platform_count,
                "platform_retrieval": "overlay_mandatory_paths",
            },
        },
    )
    await sync_pmp_draft_workspace(
        session,
        project=project,
        draft=draft,
        markdown=output.markdown,
    )
    await sync_decisions_from_markdown(
        session,
        project_id=project.id,
        markdown=output.markdown,
        workflow_type=WORKFLOW_TYPE,
        locked=locked_decisions,
    )
    trace.append(
        _trace(
            "draft_save",
            "complete",
            "Saved Create PMP as a versioned draft artefact.",
            draft_id=str(draft.id),
            version=draft.version,
            **model_metadata,
        )
    )

    content = f"Create PMP completed. Draft v{draft.version} is ready for review: {draft.title}"
    await _persist_trace_message(
        session,
        project_id=project.id,
        run_id=run_id,
        thread_id=thread_id,
        content=content,
        trace=trace,
        status="complete",
        draft_id=draft.id,
    )
    return CreatePmpResponse(
        status="complete",
        gate=gate,
        trace=trace,
        draft=DraftArtifactResponse.model_validate(draft),
        message=content,
    )


async def _next_version_hint(
    session: AsyncSession,
    project_id: uuid.UUID,
    workflow_type: str,
) -> int:
    from app.database.draft_artifacts import next_draft_version

    return await next_draft_version(
        session,
        project_id=project_id,
        workflow_type=workflow_type,
    )


async def _persist_trace_message(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    thread_id: uuid.UUID | None,
    content: str,
    trace: list[WorkflowTraceEvent],
    status: str,
    draft_id: uuid.UUID | None = None,
) -> None:
    await record_activity_events(
        session,
        project_id=project_id,
        source=WORKFLOW_TYPE,
        run_id=run_id,
        reference_type="draft_artifact" if draft_id else None,
        reference_id=draft_id,
        events=trace,
    )
    if thread_id is None:
        return
    await create_message(
        session,
        thread_id=thread_id,
        role="assistant",
        content=content,
        message_data={
            "workflowType": WORKFLOW_TYPE,
            "workflowStatus": status,
            "workflowTrace": [event.model_dump() for event in trace],
            "draftId": str(draft_id) if draft_id else None,
        },
    )
