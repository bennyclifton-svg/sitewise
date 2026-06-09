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
from app.schemas.projects import CreatePmpResponse, DraftArtifactResponse, WorkflowTraceEvent
from app.sitewise.gate import format_overlay_failure, overlay_status
from app.sitewise.pmp_evidence_validation import (
    evidence_grounded_violations,
    markdown_is_evidence_grounded,
    sanitize_evidence_grounded_markdown,
    sync_document_control_version,
)
from app.sitewise.pmp_sources import document_title_for_role, required_platform_paths
from app.sitewise.pmp_greenfield_brief import greenfield_structure_violations
from app.sitewise.pmp_sources import seed_consulted_includes_required
from app.workflows.create_pmp import (
    WORKFLOW_TYPE,
    PmpDraftOutput,
    WorkflowValidationError,
    _format_mandatory_seeds,
    _format_sources,
    _is_platform_passage,
    _project_source_texts,
    _trace,
    create_pmp_agent,
    markdown_section_headings,
    normalize_pmp_markdown,
    retrieve_create_pmp_sources,
    retrieve_project_evidence_delta,
)

UPDATE_RUNTIME_NAME = "clerk-sitewise-update-pmp"


def validate_update_pmp_output(
    output: PmpDraftOutput,
    *,
    baseline_markdown: str,
    archetype: str,
    user_role: str,
    has_evidence_delta: bool,
    source_texts: list[str] | None = None,
) -> None:
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
) -> PmpDraftOutput:
    user_role = project.user_role or ""
    mandatory_paths = required_platform_paths(
        archetype=project.archetype or "",
        user_role=user_role,
    )
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
        f"Required document title: {document_title_for_role(user_role)}",
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
    if delta_passages:
        prompt_parts.append(
            "New or updated project evidence since the baseline revision "
            f"(since {baseline.created_at.isoformat()}):"
        )
        prompt_parts.append(_format_sources(delta_passages))
    else:
        prompt_parts.append(
            "No new project documents were ingested since the baseline revision. "
            "Return the baseline with only minor consistency fixes if needed; do not "
            "rewrite unrelated sections."
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

    delta_passages = await retrieve_project_evidence_delta(
        session,
        project_slug=project.slug,
        since=baseline.created_at,
    )
    platform_passages = [passage for passage in _passages if _is_platform_passage(passage)]
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
            )
            output.markdown = normalize_pmp_markdown(output.markdown)
            if markdown_is_evidence_grounded(output.markdown, output.evidence_refs):
                output.markdown = sanitize_evidence_grounded_markdown(
                    output.markdown,
                    output.evidence_refs,
                    source_texts=sanitize_source_texts,
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
                    source_texts=delta_source_texts,
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

    from app.workflows.create_pmp import draft_workspace_path, _next_version_hint

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
            "seed_consulted": output.seed_consulted,
            "evidence_refs": output.evidence_refs,
            "context_refs": output.context_refs,
            "trace": [event.model_dump() for event in trace],
        },
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
