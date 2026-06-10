import asyncio
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.chat_models import resolve_chat_model
from app.assistant.run_agent import run_agent_with_retry
from app.config import settings
from app.database.chats import create_message
from app.database.draft_artifact import DraftArtifact
from app.database.draft_artifacts import create_draft_artifact
from app.database.project import Project
from app.database.source_document import SourceDocument
from app.database.workspace_files import upsert_workspace_file
from app.inbox.paths import build_storage_key
from app.storage.project_files import upload_project_file
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters, SourcePassage
from app.retrieval.whole_document import load_platform_documents_by_paths
from app.schemas.projects import CreateCostPlanResponse, DraftArtifactResponse, WorkflowTraceEvent
from app.sitewise.cost_plan_brief import (
    build_greenfield_brief,
    greenfield_markers_missing,
    greenfield_quality_markers,
    greenfield_structure_violations,
)
from app.sitewise.cost_plan_evidence_validation import (
    cost_plan_evidence_grounded_violations,
    ensure_evidence_grounded_cost_plan_scaffold,
)
from app.sitewise.cost_plan_workbook import build_cost_plan_workbook
from app.sitewise.cost_plan_sources import (
    document_title_for_role,
    required_platform_paths,
    required_section_headings,
    seed_consulted_includes_required,
)
from app.sitewise.gate import format_overlay_failure, overlay_status
from app.workflows.create_pmp import (
    WorkflowValidationError,
    _is_platform_passage,
    _is_project_passage,
    _source_ref,
    normalize_pmp_markdown,
)
from ingest.hashing import bytes_content_hash

WORKFLOW_TYPE = "create_cost_plan"
RUNTIME_NAME = "clerk-sitewise-create-cost-plan"
RUNTIME_HYBRID_NAME = "clerk-sitewise-create-cost-plan-hybrid"
HYBRID_NARRATIVE_MAX_ATTEMPTS = 3
CREATE_COST_PLAN_PROJECT_QUERY = (
    "cost plan budget contingency claims variations fee proposals tender "
    "contract sum schedule of values invoices progress payment"
)
CREATE_COST_PLAN_PLATFORM_CONTENT_CHARS = 10_000
CREATE_COST_PLAN_EVIDENCE_DOC_CHARS = 5_000
CREATE_COST_PLAN_MAX_EVIDENCE_DOCS = 12
CREATE_COST_PLAN_MIN_MARKER_PATHS_SKIP_SEMANTIC = 999
CREATE_COST_PLAN_SEMANTIC_LIMIT = 8

_PLATFORM_CORPUS_INGEST_HINT = (
    "Ingest from backend/: "
    "`uv run python -m ingest run --file docs/clerk-brief.md --execute`, "
    "`uv run python -m ingest run --folder seed --execute`, "
    "and `uv run python -m ingest run --folder skills --execute`."
)

COST_EVIDENCE_PATH_MARKERS: tuple[str, ...] = (
    "01-cost/",
    "01-cost\\",
    "engagement-letter",
    "engagement_letter",
    "fee-proposal",
    "fee_proposal",
    "owner-project-brief",
    "owner-brief",
    "project-brief",
    "planning-pathway",
    "planning_pathway",
    "02-consultant/",
    "02-consultant\\",
    "progress-claim",
    "progress_claim",
    "payment-claim",
    "payment_claim",
    "schedule-of-values",
    "schedule_of_values",
    "00-brief-pmp",
    "00-brief",
    "07-construction/05-progress-claims",
    "07-construction/06-variations",
    "07-construction/02-fioa-contract",
    "03-design/01-due-diligence",
    "03-design\\01-due-diligence",
    "geotechnical",
    "geotech",
    "06-geotechnical",
    "master-programme",
    "master_programme",
    "11-master-programme",
    "certifier-appointment",
    "certifier",
    "12-certifier",
    "04-authority",
    "04-planning-and-authorities",
    "survey-report",
    "05-survey",
)

_COST_DOC_PRIORITY: tuple[str, ...] = (
    "engagement-letter",
    "fee-proposal",
    "owner-project-brief",
    "owner-brief",
    "project-brief",
    "planning-pathway",
    "09-planning",
    "geotechnical",
    "geotech",
    "06-geotechnical",
    "master-programme",
    "11-master-programme",
    "certifier-appointment",
    "12-certifier",
    "certifier",
    "03-design/01-due-diligence",
    "04-authority",
    "04-planning-and-authorities",
    "00-brief-pmp",
    "01-cost/",
    "progress-claim",
    "schedule-of-values",
    "survey-report",
)

_COST_EVIDENCE_RESERVATIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("engagement", ("engagement-letter", "engagement_letter")),
    ("fee", ("fee-proposal", "fee_proposal")),
    (
        "brief",
        ("owner-project-brief", "owner_project_brief", "owner-brief", "project-brief", "03-owner-project-brief"),
    ),
    ("planning", ("planning-pathway", "planning_pathway", "09-planning-pathway", "09-planning")),
    ("geotech", ("geotechnical", "geotech", "06-geotechnical")),
    ("programme", ("master-programme", "master_programme", "11-master-programme")),
    ("certifier", ("certifier-appointment", "12-certifier", "certifier")),
)

_INSTRUCTIONS_PATH = Path(__file__).with_name("create_cost_plan_instructions.md")

DraftMode = Literal["evidence_grounded", "platform_seeded"]


class CostPlanDraftOutput(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    markdown: str = Field(min_length=200)
    seed_consulted: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    context_refs: list[str] = Field(default_factory=list)


def _load_agent_instructions() -> str:
    return _INSTRUCTIONS_PATH.read_text(encoding="utf-8")


create_cost_plan_agent = Agent(
    f"openai-chat:{settings.openai_chat_model}",
    output_type=CostPlanDraftOutput,
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


def _source_excerpt_chars(_passage: SourcePassage) -> int:
    return CREATE_COST_PLAN_EVIDENCE_DOC_CHARS


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


def _format_required_sections(user_role: str) -> str:
    return "\n".join(f"- {heading}" for heading in required_section_headings(user_role))


def _format_mandatory_seeds(paths: list[str]) -> str:
    return "\n".join(
        f"- {path}"
        for path in paths
        if path.startswith("seed/") or path.startswith("skills/")
    )


def _markdown_has_section(markdown: str, heading: str) -> bool:
    target = heading.strip().lower()
    for line in markdown.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("## ") and stripped[3:].strip() == target:
            return True
    return False


def _source_document_passage(doc: SourceDocument) -> SourcePassage:
    return SourcePassage(
        chunk_id=doc.id,
        document_id=doc.id,
        chunk_index=0,
        content=doc.normalized_content[:CREATE_COST_PLAN_EVIDENCE_DOC_CHARS],
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


def _cost_path_priority(relative_path: str) -> int:
    path_lower = relative_path.lower().replace("\\", "/")
    for index, marker in enumerate(_COST_DOC_PRIORITY):
        if marker.replace("\\", "/") in path_lower:
            return index
    return len(_COST_DOC_PRIORITY)


def _path_matches_cost_evidence(relative_path: str) -> bool:
    path_lower = relative_path.lower().replace("\\", "/")
    return any(marker.replace("\\", "/") in path_lower for marker in COST_EVIDENCE_PATH_MARKERS)


def select_cost_evidence_paths(relative_paths: list[str], *, limit: int) -> list[str]:
    """Pick cost-plan evidence paths, reserving one slot per mobilisation document class."""
    matching = [path for path in relative_paths if _path_matches_cost_evidence(path)]
    if not matching:
        return []

    normalized = [(path, path.lower().replace("\\", "/")) for path in matching]
    selected: list[str] = []
    used: set[str] = set()

    for _bucket, patterns in _COST_EVIDENCE_RESERVATIONS:
        for path, path_lower in normalized:
            if path in used:
                continue
            if any(pattern in path_lower for pattern in patterns):
                selected.append(path)
                used.add(path)
                break

    for path in sorted(matching, key=_cost_path_priority):
        if path in used:
            continue
        selected.append(path)
        used.add(path)
        if len(selected) >= limit:
            break

    return selected[:limit]


async def list_cost_evidence_paths(
    session: AsyncSession,
    *,
    project_slug: str,
    limit: int = CREATE_COST_PLAN_MAX_EVIDENCE_DOCS,
) -> list[str]:
    result = await session.execute(
        select(SourceDocument.relative_path).where(
            SourceDocument.project == project_slug,
        )
    )
    return select_cost_evidence_paths(list(result.scalars().all()), limit=limit)


async def load_cost_project_evidence_documents(
    session: AsyncSession,
    *,
    project_slug: str,
    semantic_relative_paths: list[str],
    marker_paths: list[str] | None = None,
) -> list[SourcePassage]:
    if marker_paths is None:
        marker_paths = await list_cost_evidence_paths(
            session,
            project_slug=project_slug,
        )
    merged_paths = list(
        dict.fromkeys(semantic_relative_paths + marker_paths)
    )[:CREATE_COST_PLAN_MAX_EVIDENCE_DOCS]
    if not merged_paths:
        return []

    result = await session.execute(
        select(SourceDocument).where(
            SourceDocument.project == project_slug,
            SourceDocument.relative_path.in_(merged_paths),
        )
    )
    return [_source_document_passage(doc) for doc in result.scalars().all()]


async def retrieve_create_cost_plan_sources(
    session: AsyncSession,
    *,
    project: Project,
) -> tuple[list[SourcePassage], int, int, DraftMode, list[str]]:
    mandatory_paths = required_platform_paths(
        archetype=project.archetype or "",
        user_role=project.user_role or "",
    )
    (
        (platform_passages, missing_paths),
        marker_paths,
    ) = await asyncio.gather(
        load_platform_documents_by_paths(
            session,
            mandatory_paths,
            content_chars=CREATE_COST_PLAN_PLATFORM_CONTENT_CHARS,
        ),
        list_cost_evidence_paths(session, project_slug=project.slug),
    )

    semantic_paths: list[str] = []
    if len(marker_paths) < CREATE_COST_PLAN_MIN_MARKER_PATHS_SKIP_SEMANTIC:
        retriever = DocumentRetriever(session)
        project_passages = await retriever.retrieve(
            CREATE_COST_PLAN_PROJECT_QUERY,
            filters=RetrievalFilters(
                active_project=project.slug,
                include_platform_knowledge=False,
            ),
            limit=CREATE_COST_PLAN_SEMANTIC_LIMIT,
            include_neighbours=False,
        )
        semantic_paths = list(
            dict.fromkeys(
                passage.relative_path
                for passage in project_passages
                if _is_project_passage(passage, project.slug)
            )
        )

    cost_passages = await load_cost_project_evidence_documents(
        session,
        project_slug=project.slug,
        semantic_relative_paths=semantic_paths,
        marker_paths=marker_paths,
    )
    if cost_passages:
        passages = cost_passages + platform_passages
        project_count = len(cost_passages)
    else:
        passages = platform_passages
        project_count = 0

    platform_count = sum(1 for passage in passages if _is_platform_passage(passage))
    draft_mode: DraftMode = (
        "evidence_grounded" if project_count > 0 else "platform_seeded"
    )
    return passages, project_count, platform_count, draft_mode, missing_paths


def _role_drafting_note(*, draft_mode: DraftMode, state: str) -> str:
    if draft_mode == "platform_seeded":
        evidence_note = (
            "No project cost evidence is available yet. Draft from mandatory doctrine and "
            "seed sources only. Follow the Greenfield content contract in full — include "
            "the cost breakdown scaffold with Assumption/TBC amounts. Leave evidence_refs empty."
        )
    else:
        evidence_note = (
            "Project cost evidence is available. Ground budget figures, appointments, and "
            "claim schedules from Sources. Include Evidence on file and the evidence map table "
            "in Source evidence used. Apply claim-first rule for progress claims and SOV. "
            "Do not collapse Construction to one line when claim evidence has trade rows."
        )

    state_note = (
        f"State is {state}. Apply NSW-deep-default guidance with inline non-NSW gap "
        "callouts where state-specific instruments differ."
        if state != "NSW"
        else "State is NSW (deep default in seeds)."
    )
    return "\n".join([evidence_note, state_note])


async def run_create_cost_plan_model(
    *,
    project: Project,
    passages: list[SourcePassage],
    draft_mode: DraftMode,
    validation_feedback: str | None = None,
    chat_model: str | None = None,
) -> CostPlanDraftOutput:
    user_role = project.user_role or ""
    mandatory_paths = required_platform_paths(
        archetype=project.archetype or "",
        user_role=user_role,
    )

    prompt_parts = [
        f"Project: {project.title}",
        f"Workspace path: {project.workspace_path}",
        (
            "Overlays: "
            f"archetype={project.archetype}, "
            f"user_role={project.user_role}, "
            f"state={project.state}"
        ),
        (
            f"Cost plan run date: {date.today().isoformat()} — use for recommendation "
            "due dates (2–4 weeks forward or relative phrasing; never past years)."
        ),
        f"Draft mode: {draft_mode}",
        f"Required document title: {document_title_for_role(user_role)}",
        _role_drafting_note(
            draft_mode=draft_mode,
            state=project.state or "NSW",
        ),
        "Required cost plan sections (use these exact ## headings):",
        _format_required_sections(user_role),
        "Mandatory seed paths (must all appear in seed_consulted):",
        _format_mandatory_seeds(mandatory_paths),
        build_greenfield_brief(
            archetype=project.archetype or "",
            user_role=user_role,
            state=project.state or "NSW",
            draft_mode=draft_mode,
        ),
    ]
    if draft_mode == "platform_seeded":
        depth_markers = greenfield_quality_markers(
            archetype=project.archetype or "",
            user_role=user_role,
        )
        marker_list = ", ".join(depth_markers)
        prompt_parts.append(
            "Required depth markers (each term MUST appear at least once in the markdown body, "
            f"case-insensitive): {marker_list}"
        )
    prompt_parts.extend(
        [
            (
                "Use the source refs exactly when filling evidence_refs/context_refs. "
                "Populate context_refs with doctrine and seed refs you used."
            ),
            f"Sources:\n{_format_sources(passages)}",
        ]
    )
    if validation_feedback:
        prompt_parts.append(
            "REVISION REQUIRED — your previous draft failed validation:\n"
            f"{validation_feedback}\n"
            "Regenerate the full draft fixing every issue."
        )
    prompt = "\n\n".join(prompt_parts)
    resolved_model = resolve_chat_model(chat_model)
    result = await run_agent_with_retry(create_cost_plan_agent, prompt, model=resolved_model)
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


def validate_cost_plan_output(
    output: CostPlanDraftOutput,
    draft_mode: DraftMode,
    *,
    archetype: str,
    user_role: str,
    source_texts: list[str] | None = None,
) -> None:
    if not output.seed_consulted:
        raise WorkflowValidationError("Create Cost Plan output did not identify seed consulted.")
    if not output.context_refs:
        raise WorkflowValidationError(
            "Create Cost Plan output did not identify doctrine or seed context references."
        )
    if draft_mode == "evidence_grounded" and not output.evidence_refs:
        raise WorkflowValidationError("Create Cost Plan output did not identify evidence references.")
    if "# " not in output.markdown and "## " not in output.markdown:
        raise WorkflowValidationError("Create Cost Plan output is not structured as Markdown.")

    missing_seeds = seed_consulted_includes_required(
        output.seed_consulted,
        archetype=archetype,
        user_role=user_role,
    )
    if missing_seeds:
        joined = ", ".join(missing_seeds)
        raise WorkflowValidationError(
            f"Create Cost Plan output did not record mandatory seeds in seed_consulted: {joined}"
        )

    missing_sections = [
        heading
        for heading in required_section_headings(user_role)
        if not _markdown_has_section(output.markdown, heading)
    ]
    if missing_sections:
        joined = ", ".join(missing_sections)
        raise WorkflowValidationError(
            f"Create Cost Plan output is missing required sections: {joined}"
        )

    if draft_mode == "platform_seeded":
        missing_markers = greenfield_markers_missing(
            output.markdown,
            archetype=archetype,
            user_role=user_role,
        )
        if missing_markers:
            joined = ", ".join(missing_markers)
            raise WorkflowValidationError(
                "Create Cost Plan greenfield draft lacks required depth markers: "
                f"{joined}"
            )

    structure_issues = greenfield_structure_violations(
        output.markdown,
        _archetype=archetype,
        _user_role=user_role,
    )
    if structure_issues:
        joined = "; ".join(structure_issues)
        raise WorkflowValidationError(
            f"Create Cost Plan draft structural issues: {joined}"
        )

    if draft_mode == "evidence_grounded":
        evidence_issues = cost_plan_evidence_grounded_violations(
            output.markdown,
            output.evidence_refs,
            source_texts=source_texts,
        )
        if evidence_issues:
            joined = "; ".join(evidence_issues)
            raise WorkflowValidationError(
                f"Create Cost Plan evidence_grounded fidelity issues: {joined}"
            )


def draft_workspace_path(project: Project, version: int) -> str:
    return f"{project.workspace_path}/01-cost/cost_plan_v{version:02d}.md"


def workbook_workspace_path(project: Project, version: int) -> str:
    return f"{project.workspace_path}/01-cost/Cost_Plan_v{version:02d}.draft.xlsx"


async def save_cost_plan_workbook_artifact(
    session: AsyncSession,
    *,
    project: Project,
    draft: DraftArtifact,
    markdown: str,
) -> dict:
    generated_at = datetime.now(UTC)
    workbook = build_cost_plan_workbook(
        project_title=project.title,
        markdown=markdown,
        version=draft.version,
        generated_at=generated_at,
    )
    workspace_path = workbook_workspace_path(project, draft.version)
    storage_key = build_storage_key(str(project.id), workspace_path)
    content_hash = bytes_content_hash(workbook.content)

    await asyncio.to_thread(
        upload_project_file,
        storage_key=storage_key,
        content=workbook.content,
        filename=workbook.filename,
    )
    await upsert_workspace_file(
        session,
        project_id=project.id,
        workspace_path=workspace_path,
        filename=workbook.filename,
        storage_bucket=settings.supabase_storage_bucket,
        storage_key=storage_key,
        content_hash=content_hash,
        size_bytes=len(workbook.content),
        ingest_status="generated",
        ingest_error=None,
        source_document_id=None,
    )
    return {
        "file_name": workbook.filename,
        "workspace_path": workspace_path,
        "version": draft.version,
        "content_hash": content_hash,
        "size_bytes": len(workbook.content),
        "row_count": workbook.row_count,
        "cost_item_lookup_count": workbook.cost_item_lookup_count,
        "warnings": list(workbook.warnings),
        "generated_at": generated_at.isoformat(),
    }


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
            seeds.append(passage.relative_path)
    return list(dict.fromkeys(seeds))


def _should_use_hybrid_compiler(project: Project, draft_mode: DraftMode) -> bool:
    return (
        settings.cost_plan_hybrid_compiler
        and draft_mode == "evidence_grounded"
        and (project.user_role or "") == "architect-pm"
    )


async def run_create_cost_plan_hybrid(
    *,
    project: Project,
    passages: list[SourcePassage],
    draft_mode: DraftMode,
    chat_model: str,
    project_source_texts: list[str],
    trace: list[WorkflowTraceEvent],
) -> CostPlanDraftOutput:
    """Hybrid compiler path: extract → render → narrate → assemble."""
    from app.sitewise.cost_plan_assembler import assemble_cost_plan_markdown
    from app.sitewise.cost_plan_evidence import extract_cost_plan_evidence_pack
    from app.sitewise.cost_plan_renderer import render_cost_plan_scaffold
    from app.workflows.cost_plan_narrative import run_cost_plan_narrative_model

    user_role = project.user_role or ""
    evidence_refs = _evidence_refs_from_passages(passages, project.slug)
    pack = extract_cost_plan_evidence_pack(project_source_texts, evidence_refs)
    trace.append(
        _trace(
            "extract",
            "complete",
            "Extracted cost plan evidence pack.",
            gap_count=len(pack.gaps),
            owner_brief_on_file=pack.owner_brief_on_file,
        )
    )

    scaffold = render_cost_plan_scaffold(project, pack, draft_mode)
    trace.append(
        _trace(
            "scaffold",
            "complete",
            "Rendered deterministic cost plan scaffold.",
        )
    )

    validation_feedback: str | None = None
    run_date = date.today()
    for attempt in range(HYBRID_NARRATIVE_MAX_ATTEMPTS):
        narrative = await run_cost_plan_narrative_model(
            project=project,
            pack=pack,
            run_date=run_date,
            validation_feedback=validation_feedback,
            chat_model=chat_model,
        )
        trace.append(
            _trace(
                "narrative",
                "complete",
                "Cost plan narrative model returned structured output.",
                attempt=attempt + 1,
            )
        )

        markdown = assemble_cost_plan_markdown(
            scaffold,
            narrative,
            provenance={"compiler": "hybrid", "draft_mode": draft_mode},
        )
        trace.append(
            _trace(
                "assemble",
                "complete",
                "Assembled hybrid cost plan markdown.",
                attempt=attempt + 1,
            )
        )

        output = CostPlanDraftOutput(
            title=document_title_for_role(user_role),
            markdown=markdown,
            seed_consulted=_seed_consulted_from_passages(passages),
            evidence_refs=evidence_refs,
            context_refs=_context_refs_from_passages(passages),
        )
        try:
            validate_cost_plan_output(
                output,
                draft_mode,
                archetype=project.archetype or "",
                user_role=user_role,
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
                        f"Hybrid cost plan validation failed — retrying narrative: {validation_feedback}",
                        attempt=attempt + 1,
                    )
                )
                continue
            raise

    msg = "Hybrid cost plan compiler exhausted narrative retries"
    raise RuntimeError(msg)


async def run_create_cost_plan_workflow(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    project: Project,
    thread_id: uuid.UUID | None,
    chat_model: str | None = None,
) -> CreateCostPlanResponse:
    trace: list[WorkflowTraceEvent] = []
    resolved_model = resolve_chat_model(chat_model)

    gate = overlay_status(
        archetype=project.archetype,
        user_role=project.user_role,
        state=project.state,
    )
    if not gate.ready:
        message = format_overlay_failure(gate)
        trace.append(_trace("gate", "blocked", message))
        await _persist_trace_message(
            session,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="blocked",
        )
        return CreateCostPlanResponse(status="blocked", gate=gate, trace=trace, message=message)

    trace.append(_trace("gate", "passed", "SiteWise three-overlay gate passed."))

    try:
        (
            passages,
            project_count,
            platform_count,
            draft_mode,
            missing_paths,
        ) = await retrieve_create_cost_plan_sources(session, project=project)
    except ValueError as exc:
        message = str(exc)
        trace.append(_trace("retrieval", "failed", message))
        await _persist_trace_message(
            session,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreateCostPlanResponse(status="failed", gate=gate, trace=trace, message=message)

    if missing_paths:
        message = (
            "Create Cost Plan needs mandatory platform seeds in the corpus. Missing: "
            + ", ".join(missing_paths)
            + ". "
            + _PLATFORM_CORPUS_INGEST_HINT
        )
        trace.append(_trace("retrieval", "failed", message, missing_paths=missing_paths))
        await _persist_trace_message(
            session,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreateCostPlanResponse(status="failed", gate=gate, trace=trace, message=message)

    retrieval_message = (
        f"Loaded {project_count} project cost evidence document(s) and "
        f"{platform_count} platform passage(s); draft_mode={draft_mode}."
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
            platform_retrieval="overlay_mandatory_paths",
            mandatory_seed_count=len(
                required_platform_paths(
                    archetype=project.archetype or "",
                    user_role=project.user_role or "",
                )
            ),
        )
    )

    if project_count == 0 and platform_count == 0:
        message = (
            "Create Cost Plan needs SiteWise doctrine and seed in the platform corpus, or project "
            "cost evidence after document intake. Ingest seed/ and docs/clerk-brief.md if the "
            "platform corpus is empty."
        )
        trace.append(_trace("validation", "failed", message))
        await _persist_trace_message(
            session,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreateCostPlanResponse(status="failed", gate=gate, trace=trace, message=message)

    project_source_texts = _project_source_texts(passages, project_slug=project.slug)
    use_hybrid = _should_use_hybrid_compiler(project, draft_mode)
    runtime_name = RUNTIME_HYBRID_NAME if use_hybrid else RUNTIME_NAME
    try:
        if use_hybrid:
            output = await run_create_cost_plan_hybrid(
                project=project,
                passages=passages,
                draft_mode=draft_mode,
                chat_model=resolved_model,
                project_source_texts=project_source_texts,
                trace=trace,
            )
            output.markdown = normalize_pmp_markdown(output.markdown)
        else:
            validation_feedback: str | None = None
            max_attempts = 3
            for attempt in range(max_attempts):
                output = await run_create_cost_plan_model(
                    project=project,
                    passages=passages,
                    draft_mode=draft_mode,
                    validation_feedback=validation_feedback,
                    chat_model=resolved_model,
                )
                output.markdown = normalize_pmp_markdown(output.markdown)
                if draft_mode == "evidence_grounded":
                    output.markdown = ensure_evidence_grounded_cost_plan_scaffold(
                        output.markdown,
                        output.evidence_refs,
                    )
                trace.append(
                    _trace(
                        "model",
                        "complete",
                        "Create Cost Plan model run returned a typed draft output.",
                        model=resolved_model,
                        draft_mode=draft_mode,
                        attempt=attempt + 1,
                    )
                )
                try:
                    validate_cost_plan_output(
                        output,
                        draft_mode,
                        archetype=project.archetype or "",
                        user_role=project.user_role or "",
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
                                f"Cost plan draft validation failed — retrying model: {validation_feedback}",
                            )
                        )
                        continue
                    raise
    except WorkflowValidationError as exc:
        message = str(exc)
        trace.append(_trace("validation", "failed", message))
        await _persist_trace_message(
            session,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreateCostPlanResponse(status="failed", gate=gate, trace=trace, message=message)

    trace.append(
        _trace(
            "validation",
            "passed",
            "Create Cost Plan output passed validation.",
            draft_mode=draft_mode,
        )
    )

    provenance_metadata = {
        "draft_mode": draft_mode,
        "compiler": "hybrid" if use_hybrid else "legacy",
        "seed_consulted": output.seed_consulted,
        "evidence_refs": output.evidence_refs,
        "context_refs": output.context_refs,
        "trace": [event.model_dump() for event in trace],
        "retrieval": {
            "project_passages": project_count,
            "platform_passages": platform_count,
            "platform_retrieval": "overlay_mandatory_paths",
        },
    }

    existing_version = await _next_version_hint(session, project.id, WORKFLOW_TYPE)
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
        provenance_metadata=provenance_metadata,
    )
    trace.append(
        _trace(
            "draft_save",
            "complete",
            "Saved Create Cost Plan as a versioned draft artefact.",
            draft_id=str(draft.id),
            version=draft.version,
        )
    )

    workbook_metadata = await save_cost_plan_workbook_artifact(
        session,
        project=project,
        draft=draft,
        markdown=output.markdown,
    )
    trace.append(
        _trace(
            "workbook_export",
            "complete",
            "Generated Create Cost Plan workbook.",
            workspace_path=workbook_metadata["workspace_path"],
            row_count=workbook_metadata["row_count"],
        )
    )
    draft.provenance_metadata = {
        **provenance_metadata,
        "workbook": workbook_metadata,
        "trace": [event.model_dump() for event in trace],
    }
    await session.flush()
    await session.refresh(draft)

    content = (
        f"Create Cost Plan completed. Draft v{draft.version} is ready for review: {draft.title}"
    )
    await _persist_trace_message(
        session,
        thread_id=thread_id,
        content=content,
        trace=trace,
        status="complete",
        draft_id=draft.id,
    )
    return CreateCostPlanResponse(
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
    thread_id: uuid.UUID | None,
    content: str,
    trace: list[WorkflowTraceEvent],
    status: str,
    draft_id: uuid.UUID | None = None,
) -> None:
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
