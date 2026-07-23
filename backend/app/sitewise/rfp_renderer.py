"""Deterministic structure for evidence-grounded consultant RFPs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.database.project import Project
from app.projects.identity import classification_summary, resolve_project_identity
from app.sitewise.pmp_citations import (
    CitationIndex,
    build_citation_index,
    format_citation_key_lines,
)
from app.sitewise.pmp_renderer import render_project_summary_table

if TYPE_CHECKING:
    from app.workflows.consultant_procurement import DisciplineProfile


BACKGROUND_PLACEHOLDER = "{{BACKGROUND}}"
INFORMATION_TO_REVIEW_PLACEHOLDER = "{{INFORMATION_TO_REVIEW}}"


def build_rfp_citation_index(project_evidence: list[dict[str, Any]]) -> CitationIndex:
    """Build a stable citation index from the retrieved project documents."""
    documents = [
        (path, "on file")
        for item in project_evidence
        if (path := _evidence_path(item))
    ]
    return build_citation_index(documents)


def render_rfp_scaffold(
    *,
    project: Project,
    target: DisciplineProfile,
    citation_index: CitationIndex,
    forecast: dict[str, Any],
    max_pages: int,
    project_evidence: list[dict[str, Any]] | None = None,
    assumptions: list[str] | None = None,
    instructions: str | None = None,
) -> str:
    """Render the RFP sections that do not require language-model judgement."""
    service_limit = 4 if max_pages == 1 else 8
    deliverable_limit = 4 if max_pages == 1 else 8
    identity = resolve_project_identity(project, evidence=project_evidence or [])
    classification = classification_summary(project)
    project_lines = [
        f"- Project: {project.title}",
        f"- Site address: {identity.get('site_address') or 'TBC'}",
        f"- Client / owners: {identity.get('client') or 'TBC'}",
        f"- State / phase: {getattr(project, 'state', None) or 'TBC'} / "
        f"{getattr(project, 'phase', None) or 'TBC'}",
        f"- Consultant discipline: {target.name}",
    ]
    if classification:
        project_lines.append(f"- Project type: {classification}")
    if getattr(project, "user_role", None):
        issuer = str(project.user_role).replace("-", " ").replace("_", " ")
        project_lines.append(f"- Issued by: {issuer}")

    assumption_lines = assumptions if assumptions is not None else [
        "This is a client-issued request for fee proposal, not a consultant-issued fee proposal.",
        "The consultant must confirm scope, exclusions, programme, and fee basis before appointment.",
    ]
    try:
        project_summary = render_project_summary_table(
            project,
            site_address=identity.get("site_address"),
            client=identity.get("client"),
        )
    except ValueError:
        project_summary = "\n".join(project_lines)

    sections = [
        f"# Request for Fee Proposal - {target.name}",
        "",
        "## Project Summary",
        project_summary,
        "",
        f"- Consultant discipline: {target.name}",
        "",
        "## Background",
        BACKGROUND_PLACEHOLDER,
        "",
        "## Requested services",
        *_bullets(target.requested_services[:service_limit]),
        "",
        "## Information to review",
        INFORMATION_TO_REVIEW_PLACEHOLDER,
        "",
        "## Required deliverables",
        *_bullets(target.deliverables[:deliverable_limit]),
        "",
        "## Programme / response date",
        "- Provide earliest availability, key programme assumptions, and duration for each stage.",
        "- Fee response date: TBC by client before issue.",
        "",
        "## Fee response requirements",
        "- Submit a lump-sum fee excluding GST, with GST shown separately.",
        "- Break the fee down by project stage and identify optional services, disbursements, and hourly rates.",
        "- State assumptions, exclusions, client inputs, authority fees, and validity period.",
        *_forecast_lines(forecast),
        "",
        "## Exclusions / assumptions",
        *_bullets((*assumption_lines[:4], *_instruction_lines(instructions))),
        "",
        "## Site visit / clarifications",
        "- Confirm whether a site visit is required and list any preconditions for attendance.",
        "- Submit clarification questions before pricing where information is incomplete.",
        "",
        "## Submission instructions",
        "- Submit the fee proposal to the client-nominated contact in PDF format.",
        "- Include company details, insurances, proposed personnel, and any terms requiring acceptance.",
        "",
        "## Citation key",
        *format_citation_key_lines(citation_index),
    ]
    return "\n".join(sections).rstrip() + "\n"


def _evidence_path(item: dict[str, Any]) -> str:
    path = item.get("relative_path") or item.get("filename")
    return str(path).strip() if path else ""


def _forecast_lines(forecast: dict[str, Any]) -> list[str]:
    if forecast.get("used"):
        lines = [f"- Internal benchmark: {forecast['label']}"]
    else:
        lines = ["- No internal fee benchmark is available for issue; consultant to price from scope."]
    if forecast.get("received_proposal_on_file"):
        amount = forecast.get("received_proposal_amount")
        amount_text = f" ({_money(amount)} ex GST)" if amount else ""
        lines.append(
            "- Note: a received consultant fee proposal is on file"
            f"{amount_text}; reconcile the internal benchmark against it before relying on it."
        )
    return lines


def _bullets(items: tuple[str, ...]) -> list[str]:
    return [f"- {item}" for item in items]


def _instruction_lines(instructions: str | None) -> list[str]:
    if not instructions or not instructions.strip():
        return []
    return [f"Additional instruction: {' '.join(instructions.split())}"]


def _money(value: int | None) -> str:
    return f"${value:,.0f}" if value is not None else "TBC"
