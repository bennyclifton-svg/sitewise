"""Bounded LLM narrative slice for evidence-grounded consultant RFPs."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.assistant.run_agent import run_agent_with_retry
from app.config import settings
from app.database.project import Project
from app.projects.artefact_context import (
    RfpContext,
    RftContext,
    format_artefact_context,
)
from app.projects.generation_brief import (
    ArtefactGenerationBrief,
    format_generation_brief,
)
from app.sitewise.pmp_citations import CitationIndex
from app.sitewise.pmp_taxonomy_context import pmp_taxonomy_context
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.generation_consistency import (
    ConsistencyResolver,
    ConsistencySection,
    format_consistency_failures,
    run_generation_consistency_gate,
)
from app.workflows.generation_consistency_agent import resolve_consistency_candidates
from app.workflows.section_generation import (
    SectionGenerationJob,
    SectionProgressPublisher,
    run_section_generation,
)

if TYPE_CHECKING:
    from app.workflows.consultant_procurement import DisciplineProfile


_INSTRUCTIONS_PATH = Path(__file__).with_name("rfp_narrative_instructions.md")


class ProcurementNarrativeOutput(BaseModel):
    background: str = Field(min_length=1)
    requested_services: list[str] = Field(default_factory=list)
    programme: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    consistency_ai_call_count: int = Field(default=0, ge=0, exclude=True)


# Preserve the established public name while allowing trade procurement to use
# the same bounded output contract.
RfpNarrativeOutput = ProcurementNarrativeOutput


class _BackgroundOutput(BaseModel):
    background: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class _RequestedServicesOutput(BaseModel):
    requested_services: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class _ProgrammeOutput(BaseModel):
    programme: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


def _load_instructions() -> str:
    return _INSTRUCTIONS_PATH.read_text(encoding="utf-8")


def build_rfp_narrative_prompt(
    *,
    project: Project,
    target: DisciplineProfile,
    rfp_context: RfpContext | None = None,
    generation_brief: ArtefactGenerationBrief | None = None,
    project_evidence: list[dict[str, Any]],
    platform_knowledge: list[dict[str, Any]],
    citation_index: CitationIndex,
    validation_feedback: str | None = None,
) -> str:
    """Build the narrow RFP narrative prompt with fixed evidence citations."""
    parts = [
        f"Project: {project.title}",
        f"Consultant discipline: {target.name}",
        *(
            [format_generation_brief(generation_brief)]
            if generation_brief is not None
            else [format_artefact_context(rfp_context)]
            if rfp_context is not None
            else [
                "Project profile:",
                _format_project_profile(project),
                "Relevant taxonomy emphasis:",
                _format_taxonomy_emphasis(project),
            ]
        ),
        (
            "Evidence hierarchy: use SiteWise platform guidance to frame the appointment, "
            "then use the PPR/project brief for overarching project intent, and use detailed "
            "design documents only for supporting project facts. Do not let an isolated "
            "discipline drawing redefine the whole request."
        ),
        "Platform knowledge (guidance only, not project evidence):",
        _format_platform_knowledge(platform_knowledge),
        (
            "Requested services is the highest-priority RFP section. Give it the most "
            "project-specific detail and cut generic or inapplicable template language first."
        ),
        "Baseline requested services to tailor:",
        "\n".join(f"- {item}" for item in target.requested_services),
        (
            "Write only the Background, Requested services, and Programme narrative slots."
        ),
        "Project evidence (use the assigned token exactly; do not invent citations):",
        _format_project_evidence(project_evidence, citation_index),
    ]
    if validation_feedback:
        parts.append(
            "REVISION REQUIRED — previous narrative failed validation:\n"
            f"{validation_feedback}\n"
            "Regenerate the narrative output fixing every issue."
        )
    return "\n\n".join(parts)


def build_procurement_narrative_prompt(
    *,
    project: Project,
    target_name: str,
    target_label: str,
    rft_context: RftContext | None = None,
    generation_brief: ArtefactGenerationBrief | None = None,
    baseline_scope: tuple[str, ...],
    project_evidence: list[dict[str, Any]],
    platform_knowledge: list[dict[str, Any]],
    citation_index: CitationIndex,
    validation_feedback: str | None = None,
) -> str:
    """Build the shared narrow prompt for a non-consultant procurement target."""
    parts = [
        f"Project: {project.title}",
        f"{target_label}: {target_name}",
        *(
            [format_generation_brief(generation_brief)]
            if generation_brief is not None
            else [format_artefact_context(rft_context)]
            if rft_context is not None
            else [
                "Project profile:",
                _format_project_profile(project),
                "Relevant taxonomy emphasis:",
                _format_taxonomy_emphasis(project),
            ]
        ),
        (
            "Evidence hierarchy: use SiteWise procurement, tendering, and cost guidance "
            "to frame the request; use the PPR/project brief for overarching project intent; "
            "and use detailed design documents only for supporting facts. Do not let one "
            "services document drive the whole package."
        ),
        (
            "For a whole-of-project Main Works request, keep the background and scope at "
            "head-contractor level. Do not describe the PPR's document composition, drawing "
            "schedule, or individual electrical, hydraulic, mechanical, or other trade "
            "requirements. Mention a detailed-design fact only when it identifies a material "
            "whole-project interface, approval, programme constraint, or delivery risk."
        ),
        "Platform knowledge (guidance only, not project evidence):",
        _format_platform_knowledge(platform_knowledge),
        "Baseline scope items to tailor:",
        "\n".join(f"- {item}" for item in baseline_scope),
        "Write only the Background, Requested services, and Programme narrative slots.",
        "Project evidence (use the assigned token exactly; do not invent citations):",
        _format_project_evidence(project_evidence, citation_index),
    ]
    if validation_feedback:
        parts.append(
            "REVISION REQUIRED — previous narrative failed validation:\n"
            f"{validation_feedback}\n"
            "Regenerate the narrative output fixing every issue."
        )
    return "\n\n".join(parts)


async def run_rfp_narrative_model(
    *,
    project: Project,
    target: DisciplineProfile,
    rfp_context: RfpContext | None = None,
    generation_brief: ArtefactGenerationBrief | None = None,
    project_evidence: list[dict[str, Any]],
    platform_knowledge: list[dict[str, Any]],
    citation_index: CitationIndex,
    validation_feedback: str | None = None,
    on_progress: SectionProgressPublisher | None = None,
    run_date: date | None = None,
    consistency_resolver: ConsistencyResolver | None = None,
) -> RfpNarrativeOutput:
    """Run the bounded RFP narrative agent with citation-labelled evidence."""
    prompt = build_rfp_narrative_prompt(
        project=project,
        target=target,
        rfp_context=rfp_context,
        generation_brief=generation_brief,
        project_evidence=project_evidence,
        platform_knowledge=platform_knowledge,
        citation_index=citation_index,
        validation_feedback=validation_feedback,
    )
    return await _run_narrative_sections(
        prompt=prompt,
        instructions=_load_instructions(),
        model=settings.pmp_model,
        on_progress=on_progress,
        generation_brief=generation_brief,
        run_date=run_date,
        consistency_resolver=consistency_resolver,
    )


async def run_procurement_narrative_model(
    *,
    project: Project,
    target_name: str,
    target_label: str,
    rft_context: RftContext | None = None,
    generation_brief: ArtefactGenerationBrief | None = None,
    baseline_scope: tuple[str, ...],
    project_evidence: list[dict[str, Any]],
    platform_knowledge: list[dict[str, Any]],
    citation_index: CitationIndex,
    instructions_path: Path,
    validation_feedback: str | None = None,
    on_progress: SectionProgressPublisher | None = None,
    run_date: date | None = None,
    consistency_resolver: ConsistencyResolver | None = None,
) -> ProcurementNarrativeOutput:
    """Run the shared bounded narrative with variant-specific instructions."""
    prompt = build_procurement_narrative_prompt(
        project=project,
        target_name=target_name,
        target_label=target_label,
        rft_context=rft_context,
        generation_brief=generation_brief,
        baseline_scope=baseline_scope,
        project_evidence=project_evidence,
        platform_knowledge=platform_knowledge,
        citation_index=citation_index,
        validation_feedback=validation_feedback,
    )
    return await _run_narrative_sections(
        prompt=prompt,
        instructions=instructions_path.read_text(encoding="utf-8"),
        model=settings.pmp_model,
        on_progress=on_progress,
        generation_brief=generation_brief,
        run_date=run_date,
        consistency_resolver=consistency_resolver,
    )


async def _run_narrative_sections(
    *,
    prompt: str,
    instructions: str,
    model: str,
    on_progress: SectionProgressPublisher | None,
    generation_brief: ArtefactGenerationBrief | None,
    consistency_resolver: ConsistencyResolver | None,
    run_date: date | None = None,
) -> ProcurementNarrativeOutput:
    async def run_section(output_type: type[BaseModel], task: str):
        agent = Agent(
            f"openai-responses:{model}",
            output_type=output_type,
            instructions=f"{instructions}\nReturn only the requested section payload.",
            defer_model_check=True,
        )
        return await run_agent_with_retry(
            agent,
            f"{prompt}\n\nSECTION JOB:\n{task}",
            model=model,
        )

    results = await run_section_generation(
        (
            SectionGenerationJob(
                key="background",
                label="Background",
                run=lambda: run_section(
                    _BackgroundOutput,
                    "Write the project/package background only.",
                ),
            ),
            SectionGenerationJob(
                key="requested_services",
                label="Scope and services",
                run=lambda: run_section(
                    _RequestedServicesOutput,
                    "Write the requested services or scope items only.",
                ),
            ),
            SectionGenerationJob(
                key="programme",
                label="Programme requirements",
                run=lambda: run_section(
                    _ProgrammeOutput,
                    "Write the programme and submission timing items only.",
                ),
            ),
        ),
        max_concurrency=3,
        on_progress=on_progress,
    )
    background = results["background"].output
    services = results["requested_services"].output
    programme = results["programme"].output
    output = ProcurementNarrativeOutput(
        background=background.background,
        requested_services=services.requested_services,
        programme=programme.programme,
        evidence_refs=list(
            dict.fromkeys(
                [
                    *background.evidence_refs,
                    *services.evidence_refs,
                    *programme.evidence_refs,
                ]
            )
        ),
    )
    if generation_brief is not None:
        report = await run_generation_consistency_gate(
            generation_brief,
            (
                ConsistencySection(
                    key="background",
                    text=_consistency_lines(output.background),
                ),
                ConsistencySection(
                    key="requested_services",
                    text=_consistency_lines(*output.requested_services),
                    scope_items=tuple(output.requested_services),
                ),
                ConsistencySection(
                    key="programme",
                    text=_consistency_lines(*output.programme),
                ),
            ),
            run_date=run_date,
            resolver=consistency_resolver or resolve_consistency_candidates,
        )
        if on_progress is not None:
            await on_progress(
                {
                    "stage": "consistency_complete",
                    "ai_call_count": report.ai_call_count,
                }
            )
        if not report.is_consistent:
            raise WorkflowValidationError(
                "Procurement narrative consistency failed: "
                + format_consistency_failures(report),
                consistency_ai_call_count=report.ai_call_count,
            )
        output = output.model_copy(
            update={"consistency_ai_call_count": report.ai_call_count}
        )
    return output


def _consistency_lines(*values: object) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for value in values
        for line in str(value).splitlines()
        if line.strip()
    )


def _format_project_evidence(
    project_evidence: list[dict[str, Any]], citation_index: CitationIndex
) -> str:
    if not project_evidence:
        return (
            "- No project evidence was retrieved. Do not make project-specific claims."
        )
    lines: list[str] = []
    for item in project_evidence:
        path = str(item.get("relative_path") or item.get("filename") or "")
        token = citation_index.token_for(path)
        filename = str(item.get("filename") or path or "Unknown document")
        snippet = (
            " ".join(str(item.get("snippet") or "").split()) or "No extract available."
        )
        role = str(item.get("role_label") or item.get("role") or "Project evidence")
        lines.append(f"- {role} — {token} {filename}: {snippet}")
    return "\n".join(lines)


def _format_platform_knowledge(platform_knowledge: list[dict[str, Any]]) -> str:
    if not platform_knowledge:
        return "- None retrieved."
    lines: list[str] = []
    for item in platform_knowledge:
        title = str(item.get("title") or item.get("path") or "Platform guidance")
        snippet = " ".join(str(item.get("snippet") or "").split())
        lines.append(f"- {title}: {snippet or 'No extract available.'}")
    return "\n".join(lines)


def _format_project_profile(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        return "- Taxonomy profile unavailable; rely on cited project evidence."
    parts = [context.building_class, context.work_type or "TBC", *context.subclasses]
    gfa = context.scale.get("gfa_sqm")
    if isinstance(gfa, (int, float)):
        parts.append(f"{gfa:g} m² GFA")
    office = context.scale.get("office_percent")
    if isinstance(office, (int, float)):
        parts.append(f"office {office:g}%")
    return f"- {' / '.join(parts)}"


def _format_taxonomy_emphasis(project: Project) -> str:
    context = pmp_taxonomy_context(project)
    if context is None:
        return "- No emphasis profile available."
    relevant = (
        "scope-client-requirements",
        "consultants",
        "compliance-approvals",
    )
    weights = ", ".join(
        f"{section}={context.section_weights.get(section, 0):.0%}"
        for section in relevant
    )
    return (
        f"- {weights}. Carry the profile's strongest applicable scope and compliance "
        "signals into the requested services."
    )
