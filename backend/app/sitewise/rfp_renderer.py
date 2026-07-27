"""Deterministic structure for evidence-grounded consultant RFPs."""

from __future__ import annotations

import re
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
REQUESTED_SERVICES_PLACEHOLDER = "{{REQUESTED_SERVICES}}"
INFORMATION_TO_REVIEW_PLACEHOLDER = "{{INFORMATION_TO_REVIEW}}"
PROGRAMME_PLACEHOLDER = "{{PROGRAMME}}"


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
    del max_pages, forecast, assumptions, instructions
    # Consultant RFP scope is not truncated to a page target. Assumptions and
    # user instructions remain internal provenance, never issue-document copy.
    identity = resolve_project_identity(project, evidence=project_evidence or [])
    classification = classification_summary(project)
    site_citation = _identity_citation(
        identity.get("site_address"),
        project_evidence or [],
        citation_index,
        field="site_address",
    )
    client_citation = _identity_citation(
        identity.get("client"),
        project_evidence or [],
        citation_index,
        field="client",
    )
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

    try:
        project_title, project_title_source = _project_title(
            project,
            project_evidence or [],
            citation_index,
        )
        project_summary = render_project_summary_table(
            project,
            project_title=project_title,
            project_title_source=project_title_source,
            site_address=identity.get("site_address"),
            client=identity.get("client"),
            site_address_status=(
                "User provided / Evidence on file"
                if site_citation != "—"
                else "User provided / Not evidenced"
            ),
            site_address_citation=site_citation,
            client_status=(
                "User provided / Evidence on file"
                if client_citation != "—"
                else "User provided / Not evidenced"
            ),
            client_citation=client_citation,
            compact_sources=True,
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
        REQUESTED_SERVICES_PLACEHOLDER,
        "",
        "## Information to review",
        INFORMATION_TO_REVIEW_PLACEHOLDER,
        "",
        "## Required deliverables",
        *_bullets(target.deliverables),
        "",
        "## Programme / response date",
        PROGRAMME_PLACEHOLDER,
        "- Provide earliest availability, key programme assumptions, and duration for each stage.",
        "- Fee response date: TBC by client before issue.",
        "",
        "## Fee response requirements",
        "- Submit a lump-sum fee excluding GST, with GST shown separately.",
        "- Break the fee down by project stage and identify optional services, disbursements, and hourly rates.",
        "- State assumptions, exclusions, client inputs, authority fees, and validity period.",
        "",
        "## Scope assumptions / exclusions to state",
        "- Identify every scope assumption, exclusion, optional service, reliance, and required client input in the fee proposal.",
        "- Separate consultant, client, landlord, authority, other-consultant, and contractor responsibilities.",
        "- State investigation, survey, authority-fee, meeting, site-visit, tender-support, construction-support, testing, and handover allowances.",
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


_IDENTITY_STOPWORDS = frozenset(
    {
        "and",
        "client",
        "company",
        "limited",
        "ltd",
        "nsw",
        "owners",
        "project",
        "proprietary",
        "pty",
        "street",
        "road",
        "the",
    }
)


def _identity_citation(
    value: Any,
    evidence: list[dict[str, Any]],
    citation_index: CitationIndex,
    *,
    field: str,
) -> str:
    """Return the strongest source token corroborating a profile identity value."""
    if not isinstance(value, str) or not value.strip():
        return "—"
    value_text = _normalise_identity(value)
    value_tokens = _identity_tokens(value)
    best: tuple[float, str] | None = None
    for item in evidence:
        snippet = str(item.get("snippet") or item.get("content") or "")
        if not snippet.strip():
            continue
        snippet_text = _normalise_identity(snippet)
        snippet_tokens = _identity_tokens(snippet)
        overlap = value_tokens & snippet_tokens
        score = len(overlap) / max(len(value_tokens), 1)
        if value_text and value_text in snippet_text:
            score = 1.0
        if field == "site_address":
            address_numbers = {
                token for token in value_tokens if any(char.isdigit() for char in token)
            }
            if not address_numbers.intersection(snippet_tokens):
                continue
            matched = score >= 0.45
        else:
            matched = len(overlap) >= 2 and score >= 0.45
        path = _evidence_path(item)
        token = citation_index.token_for(path)
        if matched and token != "—" and (best is None or score > best[0]):
            best = (score, token)
    return best[1] if best else "—"


def _identity_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", value.casefold())
        if len(token) >= 3 and token not in _IDENTITY_STOPWORDS
    }


def _normalise_identity(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


_PROJECT_LABEL_RE = re.compile(
    r"\bproject\s*:\s*(.+?)(?=,\s*(?:levels?|located|at)\b|\s+(?:date|ref|client)\s*:|$)",
    re.I,
)


def _project_title(
    project: Project,
    evidence: list[dict[str, Any]],
    citation_index: CitationIndex,
) -> tuple[str, str]:
    for item in evidence:
        snippet = str(item.get("snippet") or item.get("content") or "")
        match = _PROJECT_LABEL_RE.search(snippet)
        if match is None:
            continue
        candidate = re.sub(r"[*_#]+", "", match.group(1)).strip(" -–—")
        if 3 <= len(candidate) <= 120:
            return candidate, citation_index.token_for(_evidence_path(item))
    return str(project.title), "Profile"


def _bullets(items: tuple[str, ...]) -> list[str]:
    return [f"- {item}" for item in items]
