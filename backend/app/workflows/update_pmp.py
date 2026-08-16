import time
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.pmp_models import (
    pmp_model_metadata,
    resolve_pmp_model,
)
from app.assistant.run_agent import run_agent_with_retry
from app.config import settings
from app.database.activity_events import record_activity_events
from app.database.chats import create_message
from app.database.draft_artifact import DraftArtifact
from app.database.draft_artifacts import (
    create_draft_artifact,
    get_latest_draft_artifact,
)
from app.database.project import Project
from app.projects.artefact_context import (
    PmpContext,
    build_pmp_context,
    format_artefact_context,
)
from app.projects.selective_refresh import (
    apply_document_refresh,
    build_incremental_audit,
    plan_selective_refresh,
)
from app.projects.decisions import locked_selections, sync_decisions_from_markdown
from app.projects.generation_audit import generation_audit_provenance
from app.projects.generation_brief import (
    ArtefactGenerationBrief,
    build_generation_brief,
    format_generation_brief,
)
from app.projects.generation_context import (
    ProjectGenerationContext,
    resolve_project_generation_context,
)
from app.projects.workflow_capabilities import UPDATE_PMP, capability_block_message
from app.retrieval.generation import (
    GenerationEvidenceInput,
    RetrievalBudget,
    RetrievalLevel,
    retrieve_generation_evidence,
)
from app.retrieval.retriever import DocumentRetriever
from app.schemas.projects import (
    CreatePmpResponse,
    DraftArtifactResponse,
    WorkflowTraceEvent,
)
from app.schemas.project_snapshot import ProjectSnapshot
from app.sitewise.gate import format_overlay_failure, overlay_status
from app.sitewise.seed_routing import select_seed_knowledge_for_project
from app.sitewise.pmp_evidence_validation import (
    evidence_grounded_violations,
    markdown_is_evidence_grounded,
    sanitize_evidence_grounded_markdown,
    sync_document_control_version,
    taxonomy_provenance_violations,
)
from app.sitewise.pmp_coverage import (
    backfill_corpus_coverage,
    format_corpus_coverage_requirements,
)
from app.sitewise.pmp_length import length_violations, pmp_word_count
from app.sitewise.artifact_presentation import prepare_issue_markdown
from app.sitewise.pmp_evidence_ledger import (
    build_evidence_ledger,
    conflict_summary_violations,
    format_evidence_ledger,
)
from app.sitewise.pmp_claim_support import (
    citation_claim_support_violations,
    exclusion_citation_violations,
)
from app.sitewise.pmp_decisions import (
    decision_violations,
    format_decision_option_sets,
    format_locked_decisions,
    missing_locked_decisions,
)
from app.sitewise.pmp_sources import document_title, required_platform_paths
from app.sitewise.pmp_greenfield_brief import greenfield_structure_violations
from app.sitewise.pmp_sources import seed_consulted_includes_required
from app.sitewise.pmp_taxonomy_context import pmp_taxonomy_context, project_has_taxonomy
from app.sitewise.pmp_corpus import list_current_pmp_corpus_documents
from app.sitewise.pmp_sweep import (
    apply_sweep_downgrades,
    compute_evidence_changed,
    compute_sections_changed,
    sweep_current_pmp_corpus,
)
from app.sitewise.consultant_register import consultant_fact_constraints
from app.workflows.create_pmp import (
    WORKFLOW_TYPE,
    PmpDraftOutput,
    PreviewPublisher,
    WorkflowValidationError,
    _apply_accommodation_facts_to_markdown,
    _apply_consultant_facts_to_markdown,
    _apply_locked_decisions,
    _context_refs_from_passages,
    _format_mandatory_seeds,
    _format_project_taxonomy,
    _format_section_budgets,
    _format_sources,
    _format_loaded_seed_sections,
    _is_platform_passage,
    _project_source_texts,
    _publish_preview,
    _publish_progress,
    _reconcile_consultant_facts_for_pmp,
    _seed_section_refs_by_section,
    _source_ref,
    _trace,
    create_pmp_agent,
    markdown_section_headings,
    normalize_pmp_markdown,
    retrieve_create_pmp_sources,
)

UPDATE_RUNTIME_NAME = "clerk-sitewise-update-pmp"
UPDATE_WORKFLOW_TYPE = "update_pmp"
UPDATE_PMP_RETRIEVAL_BUDGET = RetrievalBudget(
    max_searches=1,
    max_chunks=32,
    max_documents=24,
    max_tokens=48_000,
    max_chars=192_000,
    max_concurrency=1,
)


def validate_update_pmp_output(
    output: PmpDraftOutput,
    *,
    baseline_markdown: str,
    archetype: str,
    has_evidence_delta: bool,
    project: Project | None = None,
    source_texts: list[str] | None = None,
    source_labels: list[str] | None = None,
    locked_ids: set[str] | None = None,
) -> None:
    taxonomy_context = pmp_taxonomy_context(project) if project is not None else None
    if not output.seed_consulted:
        raise WorkflowValidationError(
            "Update PMP output did not identify seed consulted."
        )
    if not output.context_refs:
        raise WorkflowValidationError(
            "Update PMP output did not identify doctrine or seed context references."
        )
    if has_evidence_delta and not output.evidence_refs:
        raise WorkflowValidationError(
            "Update PMP output did not identify evidence references."
        )
    if "# " not in output.markdown and "## " not in output.markdown:
        raise WorkflowValidationError(
            "Update PMP output is not structured as Markdown."
        )

    missing_seeds = seed_consulted_includes_required(
        output.seed_consulted,
        archetype=archetype,
        project=project,
    )
    if missing_seeds:
        joined = ", ".join(missing_seeds)
        raise WorkflowValidationError(
            f"Update PMP output did not record mandatory seeds in seed_consulted: {joined}"
        )

    structure_issues = greenfield_structure_violations(
        output.markdown,
        archetype=archetype,
    )
    if structure_issues:
        joined = "; ".join(structure_issues)
        raise WorkflowValidationError(f"Update PMP draft structural issues: {joined}")

    if taxonomy_context is not None:
        provenance_issues = taxonomy_provenance_violations(
            output.markdown,
            draft_mode="evidence_grounded"
            if has_evidence_delta
            else "baseline_refresh",
        )
        if provenance_issues:
            joined = "; ".join(provenance_issues)
            raise WorkflowValidationError(
                f"Update PMP taxonomy provenance issues: {joined}"
            )
        if has_evidence_delta:
            lowered_markdown = output.markdown.casefold()
            if (
                "no taxonomy work-scope items selected" in lowered_markdown
                or "no work-scope items selected" in lowered_markdown
            ):
                raise WorkflowValidationError(
                    "Update PMP exposes an empty fallback work-scope row even though "
                    "the evidence-grounded brief must carry document scope instead."
                )
            conflict_issues = conflict_summary_violations(
                output.markdown,
                build_evidence_ledger(
                    source_texts or [],
                    source_labels or [],
                ),
            )
            if conflict_issues:
                raise WorkflowValidationError(
                    "Update PMP has unresolved evidence conflicts missing from the "
                    "Project Summary: " + "; ".join(conflict_issues)
                )

    baseline_headings = markdown_section_headings(baseline_markdown)
    output_headings = {
        heading.lower() for heading in markdown_section_headings(output.markdown)
    }
    missing = [
        heading
        for heading in baseline_headings
        if heading.lower() not in output_headings
    ]
    if missing:
        joined = ", ".join(missing)
        raise WorkflowValidationError(
            f"Update PMP removed baseline sections that must be preserved: {joined}"
        )

    if locked_ids:
        missing_locked = missing_locked_decisions(output.markdown, locked_ids)
        if missing_locked:
            joined = ", ".join(missing_locked)
            raise WorkflowValidationError(
                "Update PMP removed user-locked decision blocks that must be preserved: "
                f"{joined}"
            )

    decision_issues = decision_violations(output.markdown)
    if decision_issues:
        joined = "; ".join(decision_issues)
        raise WorkflowValidationError(f"Update PMP decision block issues: {joined}")

    if has_evidence_delta or markdown_is_evidence_grounded(
        output.markdown, output.evidence_refs
    ):
        evidence_issues = evidence_grounded_violations(
            output.markdown,
            output.evidence_refs,
            source_texts=source_texts,
        )
        if evidence_issues:
            joined = "; ".join(evidence_issues)
            raise WorkflowValidationError(
                f"Update PMP evidence_grounded fidelity issues: {joined}"
            )
        claim_issues = citation_claim_support_violations(
            output.markdown,
            source_texts=source_texts or [],
            source_labels=source_labels or [],
        )
        if claim_issues:
            joined = "; ".join(claim_issues)
            raise WorkflowValidationError(
                f"Update PMP citation support issues: {joined}"
            )
        if taxonomy_context is not None:
            exclusion_issues = exclusion_citation_violations(output.markdown)
            if exclusion_issues:
                raise WorkflowValidationError(
                    "Update PMP exclusion evidence issues: "
                    + "; ".join(exclusion_issues)
                )


def build_update_pmp_prompt(
    *,
    project: Project,
    baseline: DraftArtifact,
    delta_passages: list,
    platform_passages: list,
    run_date: date,
    validation_feedback: str | None = None,
    locked_decisions: dict[str, str] | None = None,
    coverage_requirements: str | None = None,
    pmp_context: PmpContext | None = None,
    generation_brief: ArtefactGenerationBrief | None = None,
) -> str:
    """Assemble the Update PMP prompt with cache-friendly ordering.

    Static platform knowledge leads, stable per-project framing follows, and
    per-run volatile content (locked decisions, run date, baseline markdown,
    coverage list, evidence snapshot, retry feedback) trails — so OpenAI
    prefix caching hits the heavy static prefix across runs and retries.
    """
    mandatory_paths = required_platform_paths(
        archetype=project.archetype or "",
        project=project,
    )
    taxonomy_context = pmp_taxonomy_context(project)
    baseline_headings = markdown_section_headings(baseline.content_markdown)
    heading_list = "\n".join(f"- {heading}" for heading in baseline_headings)

    prompt_parts = [
        "Sources (platform doctrine and seed context, for framing only):\n"
        + _format_sources(platform_passages),
        f"Project: {project.title}",
        f"Workspace path: {project.workspace_path}",
        *(
            []
            if generation_brief is not None or pmp_context is not None
            else [f"Overlays: archetype={project.archetype}, state={project.state}"]
        ),
        "Workflow: update_pmp",
        f"Required document title: {document_title(project=project)}",
        (
            "Revise the baseline PMP below using new project evidence. Preserve every "
            "## section heading from the baseline exactly (including user-added custom "
            "sections). Do not restore sections the user removed. Do not collapse the "
            "document into a summary. Upgrade Assumption rows to Fact where new evidence "
            "supports it; leave other scaffold rows as Assumption. "
            "Update the indexed evidence list and the evidence map table (never write "
            "'Evidence on file' — citations carry that signal); reconcile Internal audit "
            "Facts and workflow warnings with evidence_refs — never claim documents are "
            "missing when they appear in Sources."
        ),
        "Mandatory seed paths (must all appear in seed_consulted):",
        _format_mandatory_seeds(mandatory_paths),
    ]
    if (
        generation_brief is not None
        or pmp_context is not None
        or taxonomy_context is not None
    ):
        prompt_parts.extend(
            [
                format_generation_brief(generation_brief)
                if generation_brief is not None
                else format_artefact_context(pmp_context)
                if pmp_context is not None
                else _format_project_taxonomy(project),
                _format_section_budgets(project, pmp_context=pmp_context),
                _format_loaded_seed_sections(platform_passages),
                format_decision_option_sets(project),
                (
                    "Taxonomy update rule: keep the primary PMP inside the 2-4 page "
                    "band, preserve baseline headings, keep condensed risks/actions, "
                    "and cut generic prose before project-specific facts. Rewrite "
                    "Project Summary as one compact identity table with no column-label "
                    "header whose first rows are Project, Address, Owner, and Description. "
                    "Project must be the literal project name (never Confirmed); Address then "
                    "Owner are separate rows; table only — no bridge paragraph; work-scope "
                    "wording belongs in Description; Citation is [n] when evidenced else blank; "
                    "never write Conflict or requiring resolution in cells. Remove any Critical "
                    "current position block or row; route its unresolved controls to the "
                    "relevant section or Trace & QA. Remove any owner-side review/governance "
                    "disclaimer from the issued body."
                ),
            ]
        )

    # Volatile tail: everything below changes per run/version; keep it after
    # the cacheable prefix above.
    if (
        generation_brief is not None
        or pmp_context is not None
        or taxonomy_context is not None
    ):
        prompt_parts.append(format_locked_decisions(locked_decisions or {}))
    prompt_parts.extend(
        [
            f"Mobilisation run date: {run_date.isoformat()}",
            f"Baseline revision: v{baseline.version} (id {baseline.id})",
            "Baseline section headings that MUST remain:",
            heading_list,
            (
                "Preserve every <!-- clerk:block id=... --> marker beside the same "
                "logical block. Never invent, rewrite, or remove an existing block ID."
            ),
            "Baseline PMP markdown (preserve structure):",
            baseline.content_markdown,
        ]
    )
    if coverage_requirements:
        prompt_parts.extend(
            [
                "Mandatory current-corpus coverage (carry each item into the relevant section):",
                coverage_requirements,
                (
                    "Carry each listed date, value, quantity, scope item, and constraint "
                    "forward from the current active corpus. Do not drop previously "
                    "evidenced scope detail during refresh."
                ),
            ]
        )
    if delta_passages:
        evidence_ledger = build_evidence_ledger(
            [passage.content for passage in delta_passages],
            [passage.filename or passage.relative_path for passage in delta_passages],
        )
        prompt_parts.append(format_evidence_ledger(evidence_ledger))
        prompt_parts.append(
            "Current active project evidence corpus snapshot "
            f"({len(delta_passages)} document(s)):"
        )
        prompt_parts.append(_format_sources(delta_passages))
    else:
        prompt_parts.append(
            "The active project evidence corpus is empty. Preserve the baseline scaffold, "
            "downgrade formerly grounded rows to Not evidenced or Assumption, and keep "
            "current project-profile facts as ordinary information without a provenance label "
            "or citation."
        )
    if validation_feedback:
        prompt_parts.append(
            "REVISION REQUIRED — your previous update failed validation:\n"
            f"{validation_feedback}\n"
            "Regenerate the full updated PMP fixing every issue."
        )
    return "\n\n".join(prompt_parts)


async def run_update_pmp_model(
    *,
    project: Project,
    baseline: DraftArtifact,
    delta_passages: list,
    platform_passages: list,
    validation_feedback: str | None = None,
    chat_model: str | None = None,
    locked_decisions: dict[str, str] | None = None,
    coverage_requirements: str | None = None,
    pmp_context: PmpContext | None = None,
    generation_brief: ArtefactGenerationBrief | None = None,
) -> PmpDraftOutput:
    prompt = build_update_pmp_prompt(
        project=project,
        baseline=baseline,
        delta_passages=delta_passages,
        platform_passages=platform_passages,
        run_date=date.today(),
        validation_feedback=validation_feedback,
        locked_decisions=locked_decisions,
        coverage_requirements=coverage_requirements,
        pmp_context=pmp_context,
        generation_brief=generation_brief,
    )
    resolved_model = (
        chat_model.strip() if chat_model else resolve_pmp_model().execution_id
    )
    result = await run_agent_with_retry(create_pmp_agent, prompt, model=resolved_model)
    return result.output


async def run_update_pmp_workflow(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    project: Project,
    thread_id: uuid.UUID | None,
    chat_model: str | None = None,
    snapshot: ProjectSnapshot | None = None,
    generation_context: ProjectGenerationContext | None = None,
    on_preview: PreviewPublisher | None = None,
    affected_section_ids: tuple[str, ...] | list[str] | None = None,
) -> CreatePmpResponse:
    trace: list[WorkflowTraceEvent] = []
    run_id = uuid.uuid4()
    context_started = time.perf_counter()
    fact_count = await _reconcile_consultant_facts_for_pmp(session, project=project)
    if fact_count:
        trace.append(
            _trace(
                "consultant_facts",
                "complete",
                f"Reconciled {fact_count} evidence-derived consultant firm fact(s).",
                fact_count=fact_count,
            )
        )
    canonical_context = generation_context or (
        resolve_project_generation_context(snapshot, project=project)
        if snapshot is not None
        else None
    )
    pmp_context = (
        build_pmp_context(canonical_context) if canonical_context is not None else None
    )
    await _publish_progress(
        on_preview,
        {
            "stage": "context_ready",
            "context_version": canonical_context.context_version
            if canonical_context is not None
            else None,
        },
    )
    context_duration_ms = int((time.perf_counter() - context_started) * 1000)
    model_spec = resolve_pmp_model(chat_model)
    resolved_model = model_spec.execution_id
    model_metadata = pmp_model_metadata(model_spec)
    if snapshot is not None:
        trace.append(
            _trace(
                "project_snapshot",
                "complete",
                "Loaded deterministic Project Snapshot v1.",
                schema_version=snapshot.schema_version,
                content_fingerprint=snapshot.content_fingerprint,
            )
        )
        trace.append(
            _trace(
                "context_ready",
                "complete",
                "Built the PMP context lens from canonical project context.",
                context_version=snapshot.context_version,
                critical_unknown_count=len(pmp_context.critical_unknowns)
                if pmp_context is not None
                else 0,
                artefact_type="pmp",
                duration_ms=context_duration_ms,
            )
        )
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
        return CreatePmpResponse(
            status="blocked", gate=gate, trace=trace, message=message
        )

    capability_message = (
        capability_block_message(snapshot, UPDATE_PMP) if snapshot is not None else None
    )
    if capability_message:
        trace.append(_trace("capability", "blocked", capability_message))
        await _persist_trace_message(
            session,
            project_id=project.id,
            run_id=run_id,
            thread_id=thread_id,
            content=capability_message,
            trace=trace,
            status="blocked",
        )
        return CreatePmpResponse(
            status="blocked", gate=gate, trace=trace, message=capability_message
        )

    trace.append(_trace("gate", "passed", "SiteWise three-overlay gate passed."))
    locked_decisions = await locked_selections(session, project_id=project.id)
    locked_ids = set(locked_decisions)

    baseline = await get_latest_draft_artifact(
        session,
        project_id=project.id,
        workflow_type=WORKFLOW_TYPE,
    )
    if baseline is None:
        message = "Update PMP requires an existing PMP revision. Run Create PMP first."
        trace.append(_trace("baseline", "failed", message))
        await _persist_trace_message(
            session,
            project_id=project.id,
            run_id=run_id,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreatePmpResponse(
            status="failed", gate=gate, trace=trace, message=message
        )

    trace.append(
        _trace(
            "baseline",
            "loaded",
            f"Loaded baseline PMP v{baseline.version} for incremental update.",
            baseline_draft_id=str(baseline.id),
            baseline_version=baseline.version,
            baseline_status=baseline.status,
        )
    )
    await _publish_preview(
        on_preview,
        stage="scaffold_ready",
        markdown=baseline.content_markdown,
    )

    baseline_provenance = (
        baseline.provenance_metadata
        if isinstance(baseline.provenance_metadata, dict)
        else {}
    )
    refresh_context_version = (
        snapshot.context_version
        if snapshot is not None
        else project.project_context_version or 1
    )
    refresh_source_version = (
        snapshot.content_fingerprint
        if snapshot is not None
        else "no-project-evidence"
    )
    try:
        seed_selection = select_seed_knowledge_for_project("pmp", project)
        refresh_seed_version = (
            "|".join(seed_selection.applicable_paths) or "no-seed-guidance"
        )
    except ValueError:
        # Gate/readiness already covers unsupported overlays; skip planning still
        # needs a stable seed token when taxonomy is incomplete in tests.
        refresh_seed_version = "no-seed-guidance"
    section_ids = tuple(affected_section_ids or ())
    refresh_plan = plan_selective_refresh(
        baseline_provenance,
        context_version=refresh_context_version,
        source_version=refresh_source_version,
        seed_version=refresh_seed_version,
        artefact_type="pmp",
        affected_section_ids=section_ids,
    )
    if refresh_plan.skip:
        listing = await list_current_pmp_corpus_documents(
            session, project_id=project.id
        )
        stamped = _apply_accommodation_facts_to_markdown(
            baseline.content_markdown,
            project,
            documents=listing.documents,
        )
        if stamped != baseline.content_markdown:
            return await _save_stamp_only_update(
                session,
                user_id=user_id,
                project=project,
                baseline=baseline,
                markdown=stamped,
                gate=gate,
                trace=trace,
                run_id=run_id,
                thread_id=thread_id,
                on_preview=on_preview,
                model_spec=model_spec,
                resolved_model=resolved_model,
                model_metadata=model_metadata,
                locked_decisions=locked_decisions,
                refresh_input_hash=refresh_plan.refresh_input_hash,
            )
        trace.append(
            _trace(
                "selective_refresh",
                "skipped",
                "Refresh inputs unchanged; skipped retrieval and narrative generation.",
                input_hash=refresh_plan.refresh_input_hash,
                affected_sections=list(section_ids),
            )
        )
        content = (
            f"Update PMP skipped; draft v{baseline.version} already matches "
            "current project inputs."
        )
        await _persist_trace_message(
            session,
            project_id=project.id,
            run_id=run_id,
            thread_id=thread_id,
            content=content,
            trace=trace,
            status="complete",
            draft_id=baseline.id,
        )
        await _publish_progress(on_preview, {"stage": "artefact_ready"})
        return CreatePmpResponse(
            status="complete",
            gate=gate,
            trace=trace,
            draft=DraftArtifactResponse.model_validate(baseline),
            message=content,
        )

    try:
        (
            _passages,
            _project_count,
            platform_count,
            _draft_mode,
            missing_paths,
        ) = await retrieve_create_pmp_sources(
            session,
            project=project,
            generation_context=canonical_context,
        )
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
        return CreatePmpResponse(
            status="failed", gate=gate, trace=trace, message=message
        )

    if missing_paths:
        message = "Update PMP could not load mandatory platform sources: " + ", ".join(
            missing_paths
        )
        trace.append(
            _trace("retrieval", "failed", message, missing_paths=missing_paths)
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
        return CreatePmpResponse(
            status="failed", gate=gate, trace=trace, message=message
        )

    previous_evidence_refs = [
        ref
        for ref in baseline_provenance.get("evidence_refs", [])
        if isinstance(ref, str)
    ]
    use_corpus_sweep = project_has_taxonomy(project)
    sweep_result = None
    if use_corpus_sweep:
        sweep_result = await sweep_current_pmp_corpus(
            session,
            project=project,
            previous_evidence_refs=previous_evidence_refs,
        )
        for event in sweep_result.trace_events:
            trace.append(event)
        delta_passages = list(sweep_result.passages)
        has_delta = len(delta_passages) > 0
        trace.append(
            _trace(
                "retrieval",
                "complete",
                (
                    "Swept current active project corpus for taxonomy update."
                    if has_delta
                    else "Active corpus empty; refresh will preserve scaffold and downgrade removed evidence."
                ),
                active_corpus_documents=len(sweep_result.listing.documents),
                total_indexed_documents=sweep_result.listing.total_indexed,
                skipped_superseded=sweep_result.listing.skipped_superseded,
                skipped_revision_duplicates=sweep_result.listing.skipped_revision_duplicate,
                sweep_capped=sweep_result.listing.capped,
                platform_passages=platform_count,
                baseline_version=baseline.version,
            )
        )
    else:
        from app.workflows.create_pmp import retrieve_project_evidence_delta

        delta_passages = await retrieve_project_evidence_delta(
            session,
            project_id=project.id,
            since=baseline.created_at,
        )
        has_delta = len(delta_passages) > 0
        trace.append(
            _trace(
                "retrieval",
                "complete",
                "Loaded baseline, evidence delta, and platform sources for update.",
                evidence_delta_documents=len(delta_passages),
                platform_passages=platform_count,
                baseline_version=baseline.version,
            )
        )

    platform_passages = [
        passage for passage in _passages if _is_platform_passage(passage)
    ]
    bounded_evidence = await retrieve_generation_evidence(
        DocumentRetriever(session),
        (),
        preloaded=(
            GenerationEvidenceInput(
                key="update_pmp:platform_documents",
                category="platform_guidance",
                passages=tuple(platform_passages),
            ),
            GenerationEvidenceInput(
                key="update_pmp:project_documents",
                category="project_evidence",
                passages=tuple(delta_passages),
            ),
        ),
        level=RetrievalLevel.STRUCTURED_FACTS,
        budget=UPDATE_PMP_RETRIEVAL_BUDGET,
    )
    delta_passages = bounded_evidence.category("project_evidence")
    platform_passages = bounded_evidence.category("platform_guidance")
    has_delta = bool(delta_passages)
    await _publish_progress(
        on_preview,
        {
            "stage": "retrieval_complete",
            "evidence_delta_documents": len(delta_passages),
            "platform_passages": len(platform_passages),
        },
    )

    delta_source_texts = (
        [passage.content for passage in delta_passages if passage.content.strip()]
        if has_delta
        else None
    )
    delta_source_labels = (
        [
            passage.filename or passage.relative_path
            for passage in delta_passages
            if passage.content.strip()
        ]
        if has_delta
        else None
    )
    evidence_ledger = build_evidence_ledger(
        delta_source_texts or [],
        delta_source_labels or [],
    )
    if delta_source_texts:
        trace.append(
            _trace(
                "evidence_ledger",
                "complete",
                (
                    "Prioritised high-consequence evidence and surfaced "
                    f"{len(evidence_ledger.conflicts)} unresolved conflict(s)."
                ),
                critical_fact_count=len(evidence_ledger.critical_facts),
                conflict_count=len(evidence_ledger.conflicts),
                conflicts=[
                    {
                        "subject": conflict.subject,
                        "values": list(conflict.values),
                        "sources": list(conflict.sources),
                    }
                    for conflict in evidence_ledger.conflicts
                ],
            )
        )
    selected_evidence_refs = [_source_ref(passage) for passage in delta_passages]
    required_evidence_refs = list(selected_evidence_refs)
    active_corpus_evidence_refs = (
        list(sweep_result.evidence_refs)
        if use_corpus_sweep and sweep_result is not None
        else None
    )
    coverage_requirements = (
        format_corpus_coverage_requirements(
            delta_source_texts,
            delta_source_labels,
        )
        if delta_source_texts and required_evidence_refs
        else None
    )
    generation_brief = (
        build_generation_brief(
            pmp_context,
            evidence_refs=selected_evidence_refs,
            seed_refs=_context_refs_from_passages(platform_passages),
            constraints=tuple(
                dict.fromkeys(
                    (
                        "Preserve human-controlled blocks during refresh.",
                        *consultant_fact_constraints(project),
                    )
                )
            ),
        )
        if pmp_context is not None
        else None
    )
    sanitize_source_texts = delta_source_texts or _project_source_texts(
        _passages,
        project_id=project.id,
    )
    validation_feedback: str | None = None
    max_attempts = 3
    await _publish_progress(
        on_preview,
        {
            "stage": "section_started",
            "active_section": "refresh",
            "completed_sections": 0,
            "total_sections": 1,
            "sections": [
                {
                    "id": "refresh",
                    "label": "Project plan refresh",
                    "status": "generating",
                }
            ],
        },
    )
    try:
        for attempt in range(max_attempts):
            output = await run_update_pmp_model(
                project=project,
                baseline=baseline,
                delta_passages=delta_passages,
                platform_passages=platform_passages,
                validation_feedback=validation_feedback,
                chat_model=resolved_model,
                locked_decisions=locked_decisions,
                coverage_requirements=coverage_requirements,
                pmp_context=pmp_context,
                generation_brief=generation_brief,
            )
            output.markdown = normalize_pmp_markdown(output.markdown)
            if markdown_is_evidence_grounded(output.markdown, output.evidence_refs):
                output.markdown = sanitize_evidence_grounded_markdown(
                    output.markdown,
                    output.evidence_refs,
                    source_texts=sanitize_source_texts,
                )
            output = _apply_locked_decisions(output, locked_decisions)
            if use_corpus_sweep and sweep_result is not None:
                downgraded_markdown, downgrade_meta = apply_sweep_downgrades(
                    output.markdown,
                    previous_evidence_refs=previous_evidence_refs,
                    current_evidence_refs=active_corpus_evidence_refs or [],
                    current_source_texts=(
                        delta_source_texts if delta_source_texts is not None else []
                    ),
                )
                output = output.model_copy(update={"markdown": downgraded_markdown})
                sweep_result = sweep_result.__class__(
                    passages=sweep_result.passages,
                    merged_pack=sweep_result.merged_pack,
                    evidence_refs=sweep_result.evidence_refs,
                    listing=sweep_result.listing,
                    evidence_changed=compute_evidence_changed(
                        previous_refs=previous_evidence_refs,
                        current_refs=active_corpus_evidence_refs or [],
                        downgraded_sections=downgrade_meta.get("downgraded"),
                        conflicted_sections=downgrade_meta.get("conflicted"),
                    ),
                    trace_events=sweep_result.trace_events,
                )
            trace.append(
                _trace(
                    "model",
                    "complete",
                    "Update PMP model run returned a typed draft output.",
                    **model_metadata,
                    attempt=attempt + 1,
                )
            )
            await _publish_preview(
                on_preview,
                stage="section_completed",
                markdown=output.markdown,
            )
            await _publish_progress(
                on_preview,
                {
                    "stage": "validation_started",
                    "active_section": "refresh",
                    "completed_sections": 1,
                    "total_sections": 1,
                    "sections": [
                        {
                            "id": "refresh",
                            "label": "Project plan refresh",
                            "status": "complete",
                        }
                    ],
                },
            )
            try:
                validate_update_pmp_output(
                    output,
                    baseline_markdown=baseline.content_markdown,
                    archetype=project.archetype or "",
                    has_evidence_delta=has_delta,
                    project=project,
                    source_texts=delta_source_texts,
                    source_labels=delta_source_labels,
                    locked_ids=locked_ids,
                )
                break
            except WorkflowValidationError as exc:
                if attempt < max_attempts - 1:
                    validation_feedback = str(exc)
                    trace.append(
                        _trace(
                            "validation",
                            "retry",
                            f"Update PMP validation failed — retrying model: {validation_feedback}",
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
        return CreatePmpResponse(
            status="failed", gate=gate, trace=trace, message=message
        )

    trace.append(_trace("validation", "passed", "Update PMP output passed validation."))

    if required_evidence_refs:
        coverage_backfill = backfill_corpus_coverage(
            output.markdown,
            output_evidence_refs=output.evidence_refs,
            required_evidence_refs=required_evidence_refs,
            source_texts=delta_source_texts or [],
            source_labels=delta_source_labels,
        )
        if coverage_backfill.backfilled_facts or coverage_backfill.added_evidence_refs:
            output.markdown = coverage_backfill.markdown
            output.evidence_refs = list(coverage_backfill.evidence_refs)
            trace.append(
                _trace(
                    "coverage",
                    "advisory",
                    (
                        "Coverage advisory (not enforced): "
                        f"{len(coverage_backfill.backfilled_facts)} evidence fact(s) "
                        "remain outside the narrative body; merged "
                        f"{len(coverage_backfill.added_evidence_refs)} missing evidence ref(s)."
                    ),
                    backfilled_facts=[
                        f"{req.source}: {req.fact}"
                        for req in coverage_backfill.backfilled_facts
                    ],
                    added_evidence_refs=list(coverage_backfill.added_evidence_refs),
                )
            )

    taxonomy_context = pmp_taxonomy_context(project)
    length_weights = (
        pmp_context.section_weights
        if pmp_context is not None
        else taxonomy_context.section_weights
        if taxonomy_context is not None
        else None
    )
    if length_weights is not None:
        length_advisories = length_violations(
            output.markdown,
            weights=length_weights,
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

    evidence_changed = (
        sweep_result.evidence_changed
        if sweep_result is not None
        else compute_evidence_changed(
            previous_refs=previous_evidence_refs,
            current_refs=output.evidence_refs,
        )
    )
    seed_section_refs = [
        ref
        for values in _seed_section_refs_by_section(platform_passages).values()
        for ref in values
    ]

    from app.workflows.create_pmp import (
        _next_version_hint,
        draft_workspace_path,
        sync_pmp_draft_workspace,
    )

    patched_consultants = _apply_consultant_facts_to_markdown(
        output.markdown, project
    )
    if patched_consultants != output.markdown:
        output.markdown = patched_consultants
        trace.append(
            _trace(
                "consultant_register",
                "complete",
                "Applied evidence-derived consultant firms to the Consultants register.",
            )
        )
    patched_accommodation = _apply_accommodation_facts_to_markdown(
        output.markdown,
        project,
        delta_source_texts,
        documents=(
            sweep_result.listing.documents if sweep_result is not None else None
        ),
    )
    if patched_accommodation != output.markdown:
        output.markdown = patched_accommodation
        trace.append(
            _trace(
                "accommodation_schedule",
                "complete",
                "Applied brief-table spaces to the Accommodation Schedule.",
            )
        )

    await _publish_progress(on_preview, {"stage": "saving"})
    next_version = await _next_version_hint(session, project.id, WORKFLOW_TYPE)
    output.markdown = prepare_issue_markdown(
        output.markdown, project_title=project.title
    )
    output.markdown = sync_document_control_version(output.markdown, next_version)
    incremental = apply_document_refresh(
        baseline.content_markdown,
        (
            baseline_provenance["blocks"]
            if isinstance(baseline_provenance.get("blocks"), dict)
            else {}
        ),
        output.markdown,
        context_version=refresh_context_version,
        source_version=refresh_source_version,
        seed_version=refresh_seed_version,
        artefact_type="pmp",
        generation_version=f"{UPDATE_RUNTIME_NAME}:{next_version}",
        affected_section_ids=section_ids,
        work_type=project.work_type,
    )
    output.markdown = incremental.markdown
    incremental_audit = build_incremental_audit(
        incremental,
        refresh_input_hash=refresh_plan.refresh_input_hash,
    )
    sections_changed = compute_sections_changed(
        baseline.content_markdown,
        output.markdown,
    )
    draft = await create_draft_artifact(
        session,
        project_id=project.id,
        workflow_type=WORKFLOW_TYPE,
        title=output.title,
        workspace_path=draft_workspace_path(project, next_version),
        author_user_id=user_id,
        content_markdown=output.markdown,
        model=resolved_model,
        runtime=UPDATE_RUNTIME_NAME,
        expected_base_version=next_version - 1,
        actor_source="project_plan_workflow",
        provenance_metadata={
            "workflow": "update_pmp",
            "draft_mode": "evidence_grounded" if has_delta else "baseline_refresh",
            "model": resolved_model,
            "model_label": model_spec.label,
            "model_provider": model_spec.provider,
            "model_config_id": model_spec.configured_id,
            "model_source": model_spec.source,
            "model_execution_provider": model_spec.execution_provider,
            "model_execution_id": model_spec.execution_id,
            "project_snapshot": (
                {
                    "schema_version": snapshot.schema_version,
                    "content_fingerprint": snapshot.content_fingerprint,
                    "context_version": snapshot.context_version,
                }
                if snapshot is not None
                else None
            ),
            "based_on_draft_id": str(baseline.id),
            "based_on_version": baseline.version,
            "evidence_delta_count": len(delta_passages),
            "active_corpus_documents": (
                len(sweep_result.listing.documents)
                if sweep_result is not None
                else None
            ),
            "active_corpus_evidence_refs": active_corpus_evidence_refs,
            "sections_changed": sections_changed,
            "evidence_changed": evidence_changed,
            "seed_section_refs": seed_section_refs,
            "seed_consulted": output.seed_consulted,
            "evidence_refs": output.evidence_refs,
            "context_refs": output.context_refs,
            "generation_brief": (
                generation_brief.model_dump(mode="json")
                if generation_brief is not None
                else None
            ),
            "blocks": incremental.metadata,
            "incremental_update": incremental_audit,
            **generation_audit_provenance(
                baseline.provenance_metadata if baseline is not None else None,
                generation_brief,
                mutation={
                    "kind": "selective_refresh",
                    "actor_source": "update_pmp",
                    "based_on_version": baseline.version if baseline is not None else None,
                },
            ),
            "trace": [event.model_dump() for event in trace],
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
            "Saved Update PMP as a new versioned draft artefact.",
            draft_id=str(draft.id),
            version=draft.version,
            **model_metadata,
        )
    )

    content = f"Update PMP completed. Draft v{draft.version} is ready for review: {draft.title}"
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
    await _publish_progress(on_preview, {"stage": "artefact_ready"})
    return CreatePmpResponse(
        status="complete",
        gate=gate,
        trace=trace,
        draft=DraftArtifactResponse.model_validate(draft),
        message=content,
    )


async def _save_stamp_only_update(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    project: Project,
    baseline: DraftArtifact,
    markdown: str,
    gate,
    trace: list[WorkflowTraceEvent],
    run_id: uuid.UUID,
    thread_id: uuid.UUID | None,
    on_preview: PreviewPublisher | None,
    model_spec,
    resolved_model: str,
    model_metadata: dict,
    locked_decisions: dict[str, str],
    refresh_input_hash: str,
) -> CreatePmpResponse:
    from app.workflows.create_pmp import (
        _next_version_hint,
        draft_workspace_path,
        sync_pmp_draft_workspace,
    )

    trace.append(
        _trace(
            "accommodation_schedule",
            "complete",
            "Applied brief-table spaces to the Accommodation Schedule.",
        )
    )
    await _publish_progress(on_preview, {"stage": "saving"})
    next_version = await _next_version_hint(session, project.id, WORKFLOW_TYPE)
    markdown = prepare_issue_markdown(markdown, project_title=project.title)
    markdown = sync_document_control_version(markdown, next_version)
    draft = await create_draft_artifact(
        session,
        project_id=project.id,
        workflow_type=WORKFLOW_TYPE,
        title=baseline.title or document_title(project=project),
        workspace_path=draft_workspace_path(project, next_version),
        author_user_id=user_id,
        content_markdown=markdown,
        model=resolved_model,
        runtime=UPDATE_RUNTIME_NAME,
        expected_base_version=next_version - 1,
        actor_source="project_plan_workflow",
        provenance_metadata={
            "workflow": "update_pmp",
            "draft_mode": "stamp_only",
            "model": resolved_model,
            "model_label": model_spec.label,
            "model_provider": model_spec.provider,
            "based_on_draft_id": str(baseline.id),
            "based_on_version": baseline.version,
            "incremental_update": {
                "input_hash": refresh_input_hash,
                "updated": ["accommodation-schedule"],
                "preserved": [],
                "conflicts": [],
                "proposed_delete": [],
            },
            "trace": [event.model_dump() for event in trace],
        },
    )
    await sync_pmp_draft_workspace(
        session,
        project=project,
        draft=draft,
        markdown=markdown,
    )
    await sync_decisions_from_markdown(
        session,
        project_id=project.id,
        markdown=markdown,
        workflow_type=WORKFLOW_TYPE,
        locked=locked_decisions,
    )
    trace.append(
        _trace(
            "draft_save",
            "complete",
            "Saved Update PMP as a new versioned draft artefact.",
            draft_id=str(draft.id),
            version=draft.version,
            **model_metadata,
        )
    )
    content = (
        f"Update PMP completed. Draft v{draft.version} is ready for review: "
        f"{draft.title}"
    )
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
    await _publish_progress(on_preview, {"stage": "artefact_ready"})
    return CreatePmpResponse(
        status="complete",
        gate=gate,
        trace=trace,
        draft=DraftArtifactResponse.model_validate(draft),
        message=content,
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
        source=UPDATE_WORKFLOW_TYPE,
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
            "workflowType": UPDATE_WORKFLOW_TYPE,
            "workflowStatus": status,
            "workflowTrace": [event.model_dump() for event in trace],
            "draftId": str(draft_id) if draft_id else None,
        },
    )
