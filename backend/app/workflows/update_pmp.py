import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.chat_models import resolve_chat_model
from app.assistant.run_agent import run_agent_with_retry
from app.config import settings
from app.database.chats import create_message
from app.database.draft_artifact import DraftArtifact
from app.database.draft_artifacts import create_draft_artifact, get_latest_draft_artifact
from app.database.project import Project
from app.database.project_decisions import locked_selections, sync_decisions_from_markdown
from app.schemas.projects import CreatePmpResponse, DraftArtifactResponse, WorkflowTraceEvent
from app.sitewise.gate import format_overlay_failure, overlay_status
from app.sitewise.pmp_evidence_validation import (
    evidence_grounded_violations,
    markdown_is_evidence_grounded,
    sanitize_evidence_grounded_markdown,
    sync_document_control_version,
    taxonomy_provenance_violations,
)
from app.sitewise.pmp_length import length_violations
from app.sitewise.pmp_decisions import (
    decision_violations,
    format_decision_option_sets,
    format_locked_decisions,
    missing_locked_decisions,
)
from app.sitewise.pmp_sources import document_title_for_role, required_platform_paths
from app.sitewise.pmp_greenfield_brief import greenfield_structure_violations
from app.sitewise.pmp_sources import seed_consulted_includes_required
from app.sitewise.pmp_taxonomy_context import pmp_taxonomy_context, project_has_taxonomy
from app.sitewise.pmp_sweep import (
    apply_sweep_downgrades,
    compute_evidence_changed,
    compute_sections_changed,
    sweep_current_pmp_corpus,
)
from app.workflows.create_pmp import (
    WORKFLOW_TYPE,
    PmpDraftOutput,
    WorkflowValidationError,
    _apply_locked_decisions,
    _format_mandatory_seeds,
    _format_project_taxonomy,
    _format_section_budgets,
    _format_sources,
    _format_loaded_seed_sections,
    _is_platform_passage,
    _project_source_texts,
    _seed_section_refs_by_section,
    _trace,
    create_pmp_agent,
    markdown_section_headings,
    normalize_pmp_markdown,
    retrieve_create_pmp_sources,
)

UPDATE_RUNTIME_NAME = "clerk-sitewise-update-pmp"


def validate_update_pmp_output(
    output: PmpDraftOutput,
    *,
    baseline_markdown: str,
    archetype: str,
    user_role: str,
    has_evidence_delta: bool,
    project: Project | None = None,
    source_texts: list[str] | None = None,
    locked_ids: set[str] | None = None,
) -> None:
    taxonomy_context = pmp_taxonomy_context(project) if project is not None else None
    if not output.seed_consulted:
        raise WorkflowValidationError("Update PMP output did not identify seed consulted.")
    if not output.context_refs:
        raise WorkflowValidationError(
            "Update PMP output did not identify doctrine or seed context references."
        )
    if has_evidence_delta and not output.evidence_refs:
        raise WorkflowValidationError("Update PMP output did not identify evidence references.")
    if "# " not in output.markdown and "## " not in output.markdown:
        raise WorkflowValidationError("Update PMP output is not structured as Markdown.")

    missing_seeds = seed_consulted_includes_required(
        output.seed_consulted,
        archetype=archetype,
        user_role=user_role,
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
        user_role=user_role,
    )
    if structure_issues:
        joined = "; ".join(structure_issues)
        raise WorkflowValidationError(f"Update PMP draft structural issues: {joined}")

    if taxonomy_context is not None:
        provenance_issues = taxonomy_provenance_violations(
            output.markdown,
            draft_mode="evidence_grounded" if has_evidence_delta else "baseline_refresh",
        )
        if provenance_issues:
            joined = "; ".join(provenance_issues)
            raise WorkflowValidationError(f"Update PMP taxonomy provenance issues: {joined}")
        length_issues = length_violations(
            output.markdown,
            weights=taxonomy_context.section_weights,
            min_words=settings.pmp_min_words,
            max_words=settings.pmp_max_words,
        )
        if length_issues:
            joined = "; ".join(length_issues)
            raise WorkflowValidationError(f"Update PMP length issues: {joined}")

    baseline_headings = markdown_section_headings(baseline_markdown)
    output_headings = {heading.lower() for heading in markdown_section_headings(output.markdown)}
    missing = [
        heading
        for heading in baseline_headings
        if heading.lower() not in output_headings
    ]
    if missing:
        joined = ", ".join(missing)
        raise WorkflowValidationError(
            "Update PMP removed baseline sections that must be preserved: "
            f"{joined}"
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


async def run_update_pmp_model(
    *,
    project: Project,
    baseline: DraftArtifact,
    delta_passages: list,
    platform_passages: list,
    validation_feedback: str | None = None,
    chat_model: str | None = None,
    locked_decisions: dict[str, str] | None = None,
) -> PmpDraftOutput:
    user_role = project.user_role or ""
    mandatory_paths = required_platform_paths(
        archetype=project.archetype or "",
        user_role=user_role,
        project=project,
    )
    taxonomy_context = pmp_taxonomy_context(project)
    baseline_headings = markdown_section_headings(baseline.content_markdown)
    heading_list = "\n".join(f"- {heading}" for heading in baseline_headings)

    prompt_parts = [
        f"Project: {project.title}",
        f"Workspace path: {project.workspace_path}",
        (
            "Overlays: "
            f"archetype={project.archetype}, "
            f"user_role={project.user_role}, "
            f"state={project.state}"
        ),
        f"Mobilisation run date: {date.today().isoformat()}",
        "Workflow: update_pmp",
        f"Required document title: {document_title_for_role(user_role, project=project)}",
        f"Baseline revision: v{baseline.version} (id {baseline.id})",
        (
            "Revise the baseline PMP below using new project evidence. Preserve every "
            "## section heading from the baseline exactly (including user-added custom "
            "sections). Do not restore sections the user removed. Do not collapse the "
            "document into a summary. Upgrade Assumption rows to Fact where new evidence "
            "supports it; leave other scaffold rows as Assumption. "
            "Update Evidence on file and the evidence map table; reconcile Internal audit "
            "Facts and workflow warnings with evidence_refs — never claim documents are "
            "missing when they appear in Sources."
        ),
        "Baseline section headings that MUST remain:",
        heading_list,
        "Mandatory seed paths (must all appear in seed_consulted):",
        _format_mandatory_seeds(mandatory_paths),
        "Baseline PMP markdown (preserve structure):",
        baseline.content_markdown,
    ]
    if taxonomy_context is not None:
        prompt_parts.extend(
            [
                _format_project_taxonomy(project),
                _format_section_budgets(project),
                _format_loaded_seed_sections(platform_passages),
                format_decision_option_sets(project),
                format_locked_decisions(locked_decisions or {}),
                (
                    "Taxonomy update rule: keep the primary PMP inside the 2-4 page "
                    "band, preserve baseline headings, keep condensed risks/actions, "
                    "and cut generic prose before project-specific facts."
                ),
            ]
        )
    if delta_passages:
        prompt_parts.append(
            "Current active project evidence corpus snapshot "
            f"({len(delta_passages)} document(s)):"
        )
        prompt_parts.append(_format_sources(delta_passages))
    else:
        prompt_parts.append(
            "The active project evidence corpus is empty. Preserve the baseline scaffold, "
            "downgrade formerly grounded rows to Not evidenced or Assumption, and keep "
            "user-provided setup facts labelled User provided."
        )
    prompt_parts.append(
        "Platform doctrine and seed context (for framing only):\n"
        + _format_sources(platform_passages)
    )
    if validation_feedback:
        prompt_parts.append(
            "REVISION REQUIRED — your previous update failed validation:\n"
            f"{validation_feedback}\n"
            "Regenerate the full updated PMP fixing every issue."
        )
    prompt = "\n\n".join(prompt_parts)
    resolved_model = resolve_chat_model(chat_model)
    result = await run_agent_with_retry(create_pmp_agent, prompt, model=resolved_model)
    return result.output


async def run_update_pmp_workflow(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    project: Project,
    thread_id: uuid.UUID | None,
    chat_model: str | None = None,
) -> CreatePmpResponse:
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
        return CreatePmpResponse(status="blocked", gate=gate, trace=trace, message=message)

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
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreatePmpResponse(status="failed", gate=gate, trace=trace, message=message)

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

    try:
        (
            _passages,
            _project_count,
            platform_count,
            _draft_mode,
            missing_paths,
        ) = await retrieve_create_pmp_sources(session, project=project)
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
        return CreatePmpResponse(status="failed", gate=gate, trace=trace, message=message)

    if missing_paths:
        message = (
            "Update PMP could not load mandatory platform sources: "
            + ", ".join(missing_paths)
        )
        trace.append(_trace("retrieval", "failed", message, missing_paths=missing_paths))
        await _persist_trace_message(
            session,
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreatePmpResponse(status="failed", gate=gate, trace=trace, message=message)

    baseline_provenance = baseline.provenance_metadata if isinstance(
        baseline.provenance_metadata, dict
    ) else {}
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
            project_slug=project.slug,
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

    platform_passages = [passage for passage in _passages if _is_platform_passage(passage)]

    delta_source_texts = (
        [passage.content for passage in delta_passages if passage.content.strip()]
        if has_delta
        else None
    )
    sanitize_source_texts = delta_source_texts or _project_source_texts(
        _passages,
        project_slug=project.slug,
    )
    validation_feedback: str | None = None
    max_attempts = 3
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
                    current_evidence_refs=list(sweep_result.evidence_refs),
                    current_source_texts=(
                        delta_source_texts if delta_source_texts is not None else []
                    ),
                )
                output = output.model_copy(update={"markdown": downgraded_markdown})
                if sweep_result.evidence_refs:
                    output = output.model_copy(
                        update={"evidence_refs": list(sweep_result.evidence_refs)}
                    )
                sweep_result = sweep_result.__class__(
                    passages=sweep_result.passages,
                    merged_pack=sweep_result.merged_pack,
                    evidence_refs=sweep_result.evidence_refs,
                    listing=sweep_result.listing,
                    evidence_changed=compute_evidence_changed(
                        previous_refs=previous_evidence_refs,
                        current_refs=list(output.evidence_refs),
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
                    model=resolved_model,
                    attempt=attempt + 1,
                )
            )
            try:
                validate_update_pmp_output(
                    output,
                    baseline_markdown=baseline.content_markdown,
                    archetype=project.archetype or "",
                    user_role=project.user_role or "",
                    has_evidence_delta=has_delta,
                    project=project,
                    source_texts=delta_source_texts,
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
            thread_id=thread_id,
            content=message,
            trace=trace,
            status="failed",
        )
        return CreatePmpResponse(status="failed", gate=gate, trace=trace, message=message)

    trace.append(_trace("validation", "passed", "Update PMP output passed validation."))

    sections_changed = compute_sections_changed(
        baseline.content_markdown,
        output.markdown,
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

    next_version = await _next_version_hint(session, project.id, WORKFLOW_TYPE)
    output.markdown = sync_document_control_version(output.markdown, next_version)
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
        provenance_metadata={
            "workflow": "update_pmp",
            "draft_mode": "evidence_grounded" if has_delta else "baseline_refresh",
            "based_on_draft_id": str(baseline.id),
            "based_on_version": baseline.version,
            "evidence_delta_count": len(delta_passages),
            "active_corpus_documents": (
                len(sweep_result.listing.documents) if sweep_result is not None else None
            ),
            "sections_changed": sections_changed,
            "evidence_changed": evidence_changed,
            "seed_section_refs": seed_section_refs,
            "seed_consulted": output.seed_consulted,
            "evidence_refs": output.evidence_refs,
            "context_refs": output.context_refs,
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
        )
    )

    content = (
        f"Update PMP completed. Draft v{draft.version} is ready for review: {draft.title}"
    )
    await _persist_trace_message(
        session,
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
            "workflowType": "update_pmp",
            "workflowStatus": status,
            "workflowTrace": [event.model_dump() for event in trace],
            "draftId": str(draft_id) if draft_id else None,
        },
    )
