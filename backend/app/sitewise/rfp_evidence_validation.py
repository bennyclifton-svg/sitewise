"""Citation validation for the bounded consultant RFP narrative."""

from __future__ import annotations

import re

from app.sitewise.pmp_citations import CitationIndex
from app.sitewise.rfp_renderer import PROJECT_PROFILE_CITATION_LABEL
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
    has_project_evidence = _has_project_documents(citation_index)
    narrative_parts = [
        output.background,
        *output.requested_services,
        *output.programme,
    ]

    if not output.background.strip():
        issues.append("background must not be empty")
    elif has_project_evidence and not _cites_project_document(
        output.background, citation_index
    ):
        issues.append("background must include at least one project-evidence citation")

    if has_project_evidence and not output.requested_services:
        issues.append(f"{scope_label} must not be empty when project evidence exists")
    elif has_project_evidence and not any(
        _cites_project_document(item, citation_index)
        for item in output.requested_services
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


def _has_project_documents(citation_index: CitationIndex) -> bool:
    return any(
        path != PROJECT_PROFILE_CITATION_LABEL for path, _ in citation_index.documents
    )


def _cites_project_document(text: str, citation_index: CitationIndex) -> bool:
    profile_number = citation_index.number_for(PROJECT_PROFILE_CITATION_LABEL)
    for match in _CITATION_PATTERN.finditer(text):
        number = int(match.group(1))
        if number == profile_number:
            continue
        if 1 <= number <= len(citation_index.documents):
            return True
    return False


def validate_rfp_output(
    output: RfpNarrativeOutput, *, citation_index: CitationIndex
) -> None:
    """Validate the consultant RFP through the shared procurement contract."""
    validate_procurement_output(output, citation_index=citation_index)
