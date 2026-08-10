"""Deterministic consultant content for externally titled RFTs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.database.project import Project
from app.projects.identity import classification_summary, resolve_project_identity
from app.sitewise.pmp_citations import (
    CitationIndex,
    build_citation_index,
)
from app.sitewise.pmp_renderer import render_project_summary_table

if TYPE_CHECKING:
    from app.workflows.consultant_procurement import DisciplineProfile


BACKGROUND_PLACEHOLDER = "{{BACKGROUND}}"
REQUESTED_SERVICES_PLACEHOLDER = "{{REQUESTED_SERVICES}}"
PROGRAMME_PLACEHOLDER = "{{PROGRAMME}}"


def build_rfp_citation_index(project_evidence: list[dict[str, Any]]) -> CitationIndex:
    """Build a stable citation index from the retrieved project documents."""
    documents = [
        (path, "on file") for item in project_evidence if (path := _evidence_path(item))
    ]
    return build_citation_index(documents)


def render_procurement_project_summary(
    *,
    project: Project,
    citation_index: CitationIndex,
    forecast: dict[str, Any],
    project_evidence: list[dict[str, Any]],
) -> str:
    """Render the shared Project Summary used by procurement artefacts."""
    identity = resolve_project_identity(project, evidence=project_evidence)
    classification = classification_summary(project)
    site_citation = _identity_citation(
        identity.get("site_address"),
        project_evidence,
        citation_index,
        field="site_address",
    )
    client_citation = _identity_citation(
        identity.get("client"),
        project_evidence,
        citation_index,
        field="client",
    )
    project_lines = [
        f"- Project: {project.title}",
        f"- Site address: {identity.get('site_address') or 'TBC'}",
        f"- Client / owners: {identity.get('client') or 'TBC'}",
        f"- State / phase: {getattr(project, 'state', None) or 'TBC'} / "
        f"{getattr(project, 'phase', None) or 'TBC'}",
    ]
    if classification:
        project_lines.append(f"- Project type: {classification}")

    try:
        project_title, project_title_source = _project_title(
            project,
            project_evidence,
            citation_index,
        )
        budget, budget_source = _construction_budget_summary(forecast)
        return _omit_placeholder_rows(
            render_project_summary_table(
                project,
                project_title=project_title,
                project_title_source=project_title_source,
                site_address=identity.get("site_address"),
                client=identity.get("client"),
                site_address_status=(
                    "Profile" if site_citation != "—" else "Profile / Not evidenced"
                ),
                site_address_citation=site_citation,
                client_status=(
                    "Profile" if client_citation != "—" else "Profile / Not evidenced"
                ),
                client_citation=client_citation,
                budget=budget,
                budget_source=budget_source,
                compact_sources=False,
            )
        )
    except ValueError:
        return "\n".join(line for line in project_lines if "TBC" not in line)


def render_rfp_scaffold(
    *,
    project: Project,
    target: DisciplineProfile,
    citation_index: CitationIndex,
    forecast: dict[str, Any],
    max_pages: int,
    project_evidence: list[dict[str, Any]] | None = None,
    issued_documents: list[dict[str, Any]] | None = None,
    assumptions: list[str] | None = None,
    missing_inputs: list[str] | None = None,
    instructions: str | None = None,
) -> str:
    """Render the deterministic consultant Request for Proposal scaffold."""
    del max_pages
    project_summary = render_procurement_project_summary(
        project=project,
        citation_index=citation_index,
        forecast=forecast,
        project_evidence=project_evidence or [],
    )
    register_documents = (
        issued_documents if issued_documents is not None else project_evidence or []
    )

    sections = [
        f"# Request for Proposal - {target.name}",
        "",
        "## Proposal particulars",
        project_summary,
        "",
        f"- Services package: {target.name}",
        *(
            [f"- Client instruction: {' '.join(instructions.split())}"]
            if instructions and instructions.strip()
            else []
        ),
        "",
        "## Background",
        BACKGROUND_PLACEHOLDER,
        "",
        "## Services and deliverables",
        (
            "Provide a concise return brief with the tender response, identifying "
            "amendments, qualifications, omissions and additional services."
        ),
        "",
        REQUESTED_SERVICES_PLACEHOLDER,
        "",
        "**Required deliverables**",
        *_bullets(target.deliverables),
        "",
        "## Programme and submission",
        PROGRAMME_PLACEHOLDER,
        "- State earliest availability, stage durations and programme dependencies.",
        "- Submit one PDF response with company details, insurances, proposed personnel and proposed terms.",
        "",
        "## Fee response",
        "- Submit a lump-sum fee excluding GST, with GST shown separately.",
        (
            "- Use the indicative breakdown below (mark stages N/A where not "
            "applicable), or an equivalent schedule that preserves these stages, "
            "to support like-for-like fee comparison."
        ),
        "",
        *_fee_breakdown_table(),
        "",
        "**Qualifications and commercial basis**",
        "",
        "- State assumptions, exclusions, client inputs, authority fees, validity, optional services, disbursements and hourly rates.",
        "- Separate consultant, client, authority, other-consultant and contractor responsibilities.",
        "- Identify allowances for investigations, surveys, meetings, site visits, tender support, construction support, inspections, testing and handover.",
        "- Submit clarification questions before pricing.",
        "",
        "## Proposal conditions and RFI process",
        "- Submit clarification questions by the stated RFI cutoff through the nominated contact. Responses and addenda will be issued consistently to invited proponents.",
        "- Acknowledge all addenda and identify every qualification, exclusion, departure, alternate proposal, and requested client input.",
        "- State the proposal validity period. The client may accept none of the proposals and proponents bear their own preparation costs.",
        "",
        _information_to_review_heading(register_documents),
        _information_to_review_table(register_documents),
        "",
        "## Trace & QA",
        _trace_qa_block(assumptions or [], missing_inputs or []),
    ]
    return "\n".join(sections).rstrip() + "\n"


def _evidence_path(item: dict[str, Any]) -> str:
    path = item.get("relative_path") or item.get("filename")
    return str(path).strip() if path else ""


def _construction_budget_summary(
    forecast: dict[str, Any],
) -> tuple[str | None, str | None]:
    value = forecast.get("construction_budget")
    if not isinstance(value, (int, float)) or value <= 0:
        return None, None
    source_path = str(forecast.get("source_path") or "")
    match = re.search(r"cost_plan_v(\d+)", source_path, flags=re.IGNORECASE)
    source = (
        f"Current Cost Plan v{int(match.group(1))}" if match else "Current Cost Plan"
    )
    if forecast.get("construction_budget_basis") == "user_adopted":
        source += " (user-adopted)"
    return f"${value:,.0f} ex GST", source


def render_information_to_review_table(evidence: list[dict[str, Any]]) -> str:
    rows: list[tuple[str, str, str, str]] = []
    seen_paths: set[str] = set()
    for item in evidence:
        path = _evidence_path(item)
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)
        metadata = item.get("document_metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        filename = str(item.get("filename") or Path(path).name)
        rows.append(
            (
                _table_value(metadata.get("document_number")),
                _table_value(metadata.get("title") or Path(filename).stem),
                _table_value(metadata.get("revision")),
                _table_value(metadata.get("discipline") or metadata.get("category")),
            )
        )
    rows.sort(key=lambda row: (_natural_key(row[0]), row[1].casefold()))
    lines = [
        "| Document number | Title | Rev | Category |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(f"| {' | '.join(row)} |" for row in rows)
    if not rows:
        lines.append("| — | No source documents currently issued | — | — |")
    return "\n".join(lines)


# Retained as a private compatibility alias while internal consultant callers migrate.
_information_to_review_table = render_information_to_review_table


def _information_to_review_heading(evidence: list[dict[str, Any]]) -> str:
    count = len({_evidence_path(item) for item in evidence if _evidence_path(item)})
    noun = "document" if count == 1 else "documents"
    return f"## Project Documents ({count} {noun})"


def _fee_breakdown_table() -> list[str]:
    return [
        "| Indicative fee stage | Scope / allowance to identify | Fee ex GST |",
        "| --- | --- | ---: |",
        "| Information review, site visit and design basis | Inputs, investigations and initial advice | — |",
        "| Concept design | Options, design criteria and concept coordination | — |",
        "| Detailed design and documentation | Calculations, drawings, specifications and coordination | — |",
        "| Approval and tender support | Certification / authority inputs, tender queries and addenda | — |",
        "| Construction phase | RFIs, submittal reviews, inspections and site attendance allowances | — |",
        "| Completion and handover | Defects, completion statements and close-out deliverables | — |",
        "| Optional / additional services | Separately identify scope, rates and trigger | — |",
        "| Hourly rates | Identify rates by proposed personnel / role | — |",
        "| Disbursements | Separately identify estimated expenses | — |",
        "| **Total lump sum** | Excluding GST | **—** |",
    ]


def _table_value(value: Any) -> str:
    if value is None or not str(value).strip():
        return "—"
    return " ".join(str(value).split()).replace("|", "\\|")


def _natural_key(value: str) -> tuple[tuple[int, int | str], ...]:
    if value == "—":
        return ((2, ""),)
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.findall(r"\d+|\D+", value)
    )


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
    return str(project.title), ""


def _bullets(items: tuple[str, ...]) -> list[str]:
    return [f"- {item}" for item in items]


def _omit_placeholder_rows(markdown_table: str) -> str:
    """Keep unresolved identity fields out of the issue-facing summary."""
    lines: list[str] = []
    for line in markdown_table.splitlines():
        if not line.startswith("|") or "TBC" not in line:
            lines.append(line.replace("| Confirm |", "| — |"))
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        cleaned_cells = [_without_placeholder_fragments(cell) for cell in cells]
        if len(cleaned_cells) > 1 and cleaned_cells[1] == "—":
            continue
        lines.append(f"| {' | '.join(cleaned_cells)} |")
    return "\n".join(lines)


def _without_placeholder_fragments(value: str) -> str:
    parts = re.split(r"\s*(?:;|\s/\s)\s*", value)
    kept = [part for part in parts if "TBC" not in part]
    return "; ".join(kept) if kept else "—"


def _trace_qa_block(assumptions: list[str], missing_inputs: list[str]) -> str:
    lines = ["This review-only section is excluded from Word and PDF exports."]
    if missing_inputs:
        lines.extend(["", "**Inputs to resolve**"])
        lines.extend(f"- {item}" for item in missing_inputs)
    if assumptions:
        lines.extend(["", "**Working basis**"])
        lines.extend(f"- {item}" for item in assumptions)
    if not missing_inputs and not assumptions:
        lines.extend(["", "- No unresolved generation inputs recorded."])
    return "\n".join(lines)
