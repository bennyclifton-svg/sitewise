"""Citation validation for the bounded consultant RFP narrative."""

from __future__ import annotations

import re

from app.sitewise.pmp_citations import CitationIndex
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.rfp_narrative import ProcurementNarrativeOutput, RfpNarrativeOutput

_CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def validate_procurement_output(
    output: ProcurementNarrativeOutput,
    *,
    citation_index: CitationIndex,
    scope_label: str = "requested_services",
) -> None:
    """Reject uncited, unresolvable, or incomplete procurement narrative prose."""
    issues: list[str] = []
    has_project_evidence = bool(citation_index.documents)
    narrative_parts = [
        output.background,
        *output.requested_services,
        *output.programme,
    ]

    if not output.background.strip():
        issues.append("background must not be empty")
    elif has_project_evidence and not _CITATION_PATTERN.search(output.background):
        issues.append("background must include at least one project-evidence citation")

    if has_project_evidence and not output.requested_services:
        issues.append(f"{scope_label} must not be empty when project evidence exists")
    elif has_project_evidence and not any(
        _CITATION_PATTERN.search(item) for item in output.requested_services
    ):
        issues.append(
            f"{scope_label} must include at least one project-evidence citation"
        )

    invalid_tokens = sorted(
        {
            int(match.group(1))
            for part in narrative_parts
            for match in _CITATION_PATTERN.finditer(part)
            if not 1 <= int(match.group(1)) <= len(citation_index.documents)
        }
    )
    if invalid_tokens:
        tokens = ", ".join(f"[{token}]" for token in invalid_tokens)
        issues.append(f"citations do not resolve against the citation key: {tokens}")

    if issues:
        raise WorkflowValidationError(
            f"Procurement narrative validation failed: {'; '.join(issues)}"
        )


def validate_rfp_output(
    output: RfpNarrativeOutput, *, citation_index: CitationIndex
) -> None:
    """Validate the consultant RFP through the shared procurement contract."""
    validate_procurement_output(output, citation_index=citation_index)
