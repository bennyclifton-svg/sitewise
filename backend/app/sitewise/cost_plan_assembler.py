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
    section = _markdown_section(scaffold, "Internal audit layer")
    parts = re.split(r"(?=\n- \*\*Judgements\*\*)", section, maxsplit=1)
    preserved = parts[0].rstrip() if parts else section.rstrip()
    narrative_block = "\n".join(
        [
            "- **Judgements**",
            *[f"  - {item}" for item in narrative.judgements],
            "- **Recommendations**",
            *[f"  - {item}" for item in narrative.recommendations],
        ]
    )
    tail = parts[1] if len(parts) > 1 else ""
    if "**Cost evidence conflicts**" in tail:
        conflict = tail[tail.index("- **Cost evidence conflicts**") :]
        merged_body = f"{preserved}\n{narrative_block}\n{conflict.rstrip()}"
    else:
        merged_body = f"{preserved}\n{narrative_block}"
    return _replace_markdown_section_body(scaffold, "Internal audit layer", merged_body)


def _merge_risks_section(scaffold: str, narrative: CostPlanNarrativeOutput) -> str:
    section = _markdown_section(scaffold, "Risks and review questions")
    if narrative.risk_rows:
        body = format_risk_rows_table(narrative.risk_rows)
    else:
        body = _strip_narrative_placeholder(section)
    return _replace_markdown_section_body(scaffold, "Risks and review questions", body)


def _normalize_next_step(step: str) -> str:
    return re.sub(r"^\d+\.\s*", "", step.strip())


def _merge_recommended_next_steps(scaffold: str, narrative: CostPlanNarrativeOutput) -> str:
    lines = [
        f"{index}. {_normalize_next_step(step)}"
        for index, step in enumerate(narrative.next_steps, start=1)
    ]
    body = "\n".join(lines)
    return _replace_markdown_section_body(scaffold, "Recommended next steps", body)


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
