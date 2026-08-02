"""Bounded LLM narrative slice for evidence-grounded consultant RFPs."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.assistant.run_agent import run_agent_with_retry
from app.config import settings
from app.database.project import Project
from app.sitewise.pmp_citations import CitationIndex
from app.sitewise.pmp_taxonomy_context import pmp_taxonomy_context

if TYPE_CHECKING:
    from app.workflows.consultant_procurement import DisciplineProfile


_INSTRUCTIONS_PATH = Path(__file__).with_name("rfp_narrative_instructions.md")


class RfpNarrativeOutput(BaseModel):
    background: str = Field(min_length=1)
    requested_services: list[str] = Field(default_factory=list)
    programme: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


def _load_instructions() -> str:
    return _INSTRUCTIONS_PATH.read_text(encoding="utf-8")


rfp_narrative_agent = Agent(
    f"openai-responses:{settings.pmp_model}",
    output_type=RfpNarrativeOutput,
    instructions=_load_instructions(),
    defer_model_check=True,
)


def build_rfp_narrative_prompt(
    *,
    project: Project,
    target: DisciplineProfile,
    project_evidence: list[dict[str, Any]],
    platform_knowledge: list[dict[str, Any]],
    citation_index: CitationIndex,
    validation_feedback: str | None = None,
) -> str:
    """Build the narrow RFP narrative prompt with fixed evidence citations."""
    parts = [
        f"Project: {project.title}",
        f"Consultant discipline: {target.name}",
        "Project profile:",
        _format_project_profile(project),
        "Relevant taxonomy emphasis:",
        _format_taxonomy_emphasis(project),
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
        "Platform knowledge (guidance only, not project evidence):",
        _format_platform_knowledge(platform_knowledge),
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
    project_evidence: list[dict[str, Any]],
    platform_knowledge: list[dict[str, Any]],
    citation_index: CitationIndex,
    validation_feedback: str | None = None,
) -> RfpNarrativeOutput:
    """Run the bounded RFP narrative agent with citation-labelled evidence."""
    prompt = build_rfp_narrative_prompt(
        project=project,
        target=target,
        project_evidence=project_evidence,
        platform_knowledge=platform_knowledge,
        citation_index=citation_index,
        validation_feedback=validation_feedback,
    )
    result = await run_agent_with_retry(
        rfp_narrative_agent,
        prompt,
        model=settings.pmp_model,
    )
    return result.output


def _format_project_evidence(
    project_evidence: list[dict[str, Any]], citation_index: CitationIndex
) -> str:
    if not project_evidence:
        return "- No project evidence was retrieved. Do not make project-specific claims."
    lines: list[str] = []
    for item in project_evidence:
        path = str(item.get("relative_path") or item.get("filename") or "")
        token = citation_index.token_for(path)
        filename = str(item.get("filename") or path or "Unknown document")
        snippet = " ".join(str(item.get("snippet") or "").split()) or "No extract available."
        lines.append(f"- {token} {filename}: {snippet}")
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
