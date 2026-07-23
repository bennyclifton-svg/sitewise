"""Merge deterministic cost plan scaffold with narrative LLM output."""

from __future__ import annotations

import re
from typing import Any

from app.sitewise.cost_plan_evidence_validation import (
    _markdown_section,
    _replace_markdown_section_body,
)
from app.sitewise.cost_plan_renderer import NARRATIVE_PLACEHOLDER
from app.workflows.cost_plan_narrative import CostPlanNarrativeOutput, format_risk_rows_table


def _strip_narrative_placeholder(text: str) -> str:
    lines = [
        line
        for line in text.splitlines()
        if NARRATIVE_PLACEHOLDER not in line and "Risk review questions and due dates:" not in line
    ]
    return "\n".join(lines).strip()


def _merge_internal_audit(scaffold: str, narrative: CostPlanNarrativeOutput) -> str:
    section = _markdown_section(scaffold, "Source evidence and audit trail")
    narrative_block = "\n".join(
        [
            "- **Judgements**",
            *[f"  - {item}" for item in narrative.judgements],
            "- **Recommendations**",
            *[f"  - {item}" for item in narrative.recommendations],
        ]
    )
    marker = "- **Cost evidence conflicts**"
    if marker in section:
        merged_body = section.replace(marker, f"{narrative_block}\n{marker}", 1)
    else:
        merged_body = f"{section.rstrip()}\n{narrative_block}"
    return _replace_markdown_section_body(
        scaffold, "Source evidence and audit trail", merged_body
    )


def _replace_subsection_body(section: str, heading: str, body: str) -> str:
    pattern = re.compile(
        rf"(^###\s+{re.escape(heading)}\s*$).*?(?=^###\s+|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    return pattern.sub(
        f"### {heading}\n\n{body.strip()}\n\n", section, count=1
    ).rstrip()


def _merge_risks_section(scaffold: str, narrative: CostPlanNarrativeOutput) -> str:
    section = _markdown_section(scaffold, "Risks, delivery gates and next actions")
    if narrative.risk_rows:
        body = _replace_subsection_body(
            section, "Risk register", format_risk_rows_table(narrative.risk_rows)
        )
    else:
        body = _strip_narrative_placeholder(section)
    return _replace_markdown_section_body(
        scaffold, "Risks, delivery gates and next actions", body
    )


def _normalize_next_step(step: str) -> str:
    return re.sub(r"^\d+\.\s*", "", step.strip())


def _merge_recommended_next_steps(scaffold: str, narrative: CostPlanNarrativeOutput) -> str:
    lines = [
        f"{index}. {_normalize_next_step(step)}"
        for index, step in enumerate(narrative.next_steps, start=1)
    ]
    section = _markdown_section(scaffold, "Risks, delivery gates and next actions")
    body = _replace_subsection_body(section, "Next actions", "\n".join(lines))
    return _replace_markdown_section_body(
        scaffold, "Risks, delivery gates and next actions", body
    )


def assemble_cost_plan_markdown(
    scaffold: str,
    narrative: CostPlanNarrativeOutput,
    provenance: dict[str, Any] | None = None,
) -> str:
    """Combine scaffold and narrative slices into a single cost plan markdown draft."""
    _ = provenance
    markdown = _merge_internal_audit(scaffold, narrative)
    markdown = _merge_risks_section(markdown, narrative)
    markdown = _merge_recommended_next_steps(markdown, narrative)
    return markdown.rstrip() + "\n"
