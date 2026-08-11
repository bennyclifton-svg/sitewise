"""Assemble bounded progressive previews from completed narrative sections."""

from __future__ import annotations

from typing import Any

from app.sitewise.cost_plan_assembler import assemble_cost_plan_markdown
from app.sitewise.pmp_assembler import assemble_pmp_markdown
from app.sitewise.rfp_renderer import (
    BACKGROUND_PLACEHOLDER,
    PROGRAMME_PLACEHOLDER,
    REQUESTED_SERVICES_PLACEHOLDER,
)
from app.workflows.cost_plan_narrative import CostPlanNarrativeOutput
from app.workflows.pmp_narrative import PmpNarrativeOutput


def assemble_pmp_progressive_preview(
    scaffold: str, completed: dict[str, Any]
) -> str:
    """Merge whatever PMP narrative sections have finished into the scaffold."""
    assessment = _section_output(completed.get("assessment"))
    actions = _section_output(completed.get("actions"))
    risks = _section_output(completed.get("risks"))
    narrative = PmpNarrativeOutput.model_construct(
        judgements=list(getattr(assessment, "judgements", []) or []),
        workflow_warnings=list(getattr(assessment, "workflow_warnings", []) or []),
        recommendations=list(getattr(actions, "recommendations", []) or []),
        register_rows=list(getattr(actions, "register_rows", []) or []),
        risk_rows=list(getattr(risks, "risk_rows", []) or []),
    )
    return assemble_pmp_markdown(scaffold, narrative)


def assemble_cost_plan_progressive_preview(
    scaffold: str, completed: dict[str, Any]
) -> str:
    """Merge finished Cost Plan narrative sections into the scaffold."""
    assessment = _section_output(completed.get("assessment"))
    actions = _section_output(completed.get("actions"))
    risks = _section_output(completed.get("risks"))
    narrative = CostPlanNarrativeOutput.model_construct(
        judgements=list(getattr(assessment, "judgements", []) or []),
        recommendations=list(getattr(actions, "recommendations", []) or []),
        next_steps=list(getattr(actions, "next_steps", []) or []),
        risk_rows=list(getattr(risks, "risk_rows", []) or []),
    )
    return assemble_cost_plan_markdown(scaffold, narrative)


def assemble_procurement_progressive_preview(
    scaffold: str, completed: dict[str, Any]
) -> str:
    """Replace procurement placeholders as their narrative sections complete."""
    markdown = scaffold
    background = _section_output(completed.get("background"))
    services = _section_output(completed.get("requested_services"))
    programme = _section_output(completed.get("programme"))
    if background is not None and getattr(background, "background", None):
        markdown = markdown.replace(
            BACKGROUND_PLACEHOLDER, str(background.background).strip()
        )
    if services is not None:
        items = list(getattr(services, "requested_services", []) or [])
        if items:
            body = "\n".join(
                f"{index}. {str(item).strip()}" for index, item in enumerate(items, start=1)
            )
            markdown = markdown.replace(REQUESTED_SERVICES_PLACEHOLDER, body)
    if programme is not None:
        items = list(getattr(programme, "programme", []) or [])
        if items:
            body = "\n".join(f"- {str(item).strip()}" for item in items)
            markdown = markdown.replace(PROGRAMME_PLACEHOLDER, body)
    return markdown


def _section_output(value: Any) -> Any:
    if value is None:
        return None
    return getattr(value, "output", value)
