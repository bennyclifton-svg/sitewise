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

if TYPE_CHECKING:
    from app.workflows.consultant_procurement import DisciplineProfile


_INSTRUCTIONS_PATH = Path(__file__).with_name("rfp_narrative_instructions.md")


class RfpNarrativeOutput(BaseModel):
    background: str = Field(min_length=1)
    information_to_review: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


def _load_instructions() -> str:
    return _INSTRUCTIONS_PATH.read_text(encoding="utf-8")


rfp_narrative_agent = Agent(
    f"openai-chat:{settings.pmp_model}",
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
        "Write only the Background and Information to review narrative slots.",
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
