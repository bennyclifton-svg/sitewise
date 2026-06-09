"""Merge deterministic PMP scaffold with narrative LLM output."""

from __future__ import annotations

import re
from typing import Any

from app.sitewise.pmp_evidence_validation import _markdown_section, _replace_markdown_section
from app.sitewise.pmp_renderer import NARRATIVE_PLACEHOLDER
from app.workflows.pmp_narrative import (
    PmpNarrativeOutput,
    format_internal_audit_narrative,
    format_risk_rows_table,
)

_REGISTERS_FOOTER = (
    "Registers to open: action, decision, risk, authority approvals, consultant appointment."
)


def _strip_narrative_placeholder(text: str) -> str:
    lines = [
        line
        for line in text.splitlines()
        if NARRATIVE_PLACEHOLDER not in line and "Risk wording and owner decision due dates:" not in line
    ]
    return "\n".join(lines).strip()


def _merge_internal_audit(scaffold: str, narrative: PmpNarrativeOutput) -> str:
    section = _markdown_section(scaffold, "Internal audit layer")
    parts = re.split(r"(?=\n- \*\*Judgements\*\*)", section, maxsplit=1)
    preserved = parts[0].rstrip() if parts else section.rstrip()
    merged_body = f"{preserved}\n{format_internal_audit_narrative(narrative)}"
    return _replace_markdown_section(scaffold, "Internal audit layer", merged_body)


def _strip_registers_footer(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip() != _REGISTERS_FOOTER]
    return "\n".join(lines).strip()


def _merge_risks_section(scaffold: str, narrative: PmpNarrativeOutput) -> str:
    section = _markdown_section(scaffold, "Risks, decisions and next actions")
    if narrative.risk_rows:
        body = format_risk_rows_table(narrative.risk_rows)
    else:
        body = _strip_registers_footer(_strip_narrative_placeholder(section))
    replacement = f"{body}\n\n{_REGISTERS_FOOTER}"
    return _replace_markdown_section(scaffold, "Risks, decisions and next actions", replacement)


def assemble_pmp_markdown(
    scaffold: str,
    narrative: PmpNarrativeOutput,
    provenance: dict[str, Any] | None = None,
) -> str:
    """Combine scaffold and narrative slices into a single PMP markdown draft."""
    _ = provenance
    markdown = _merge_internal_audit(scaffold, narrative)
    markdown = _merge_risks_section(markdown, narrative)
    return markdown.rstrip() + "\n"
