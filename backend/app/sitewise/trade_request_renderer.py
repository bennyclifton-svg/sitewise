"""Deterministic universal RFT structure for trade procurement."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.database.project import Project
from app.sitewise.pmp_citations import CitationIndex, format_citation_key_lines
from app.sitewise.rfp_renderer import (
    BACKGROUND_PLACEHOLDER,
    PROGRAMME_PLACEHOLDER,
    REQUESTED_SERVICES_PLACEHOLDER,
    render_information_to_review_table,
    render_procurement_project_summary,
)

if TYPE_CHECKING:
    from app.workflows.trade_procurement import TradeProfile


RFT_SECTION_KEYS = (
    "project_summary",
    "package_basis",
    "background",
    "scope_interfaces",
    "programme",
    "price_schedule",
    "returnables",
    "qualifications",
    "submission",
    "tender_conditions",
    "information_to_review",
)
RFQ_SECTION_KEYS = (
    "project_summary",
    "package_basis",
    "background",
    "scope_interfaces",
    "programme",
    "price_schedule",
    "returnables",
    "qualifications",
    "submission",
    "quotation_conditions",
    "information_to_review",
)


def render_trade_request_scaffold(
    *,
    kind: str,
    project: Project,
    target: TradeProfile,
    citation_index: CitationIndex,
    forecast: dict[str, Any],
    project_evidence: list[dict[str, Any]],
    issued_documents: list[dict[str, Any]],
    assumptions: list[str],
    missing_inputs: list[str],
    instructions: str | None,
) -> str:
    """Render the universal external RFT controls without model judgement."""
    if kind not in {"rft", "rfq"}:
        raise ValueError("kind must be rft or rfq")
    project_summary = render_procurement_project_summary(
        project=project,
        citation_index=citation_index,
        forecast=forecast,
        project_evidence=project_evidence,
    )
    sections = [
        f"# {'Request for Tender' if kind == 'rft' else 'Request for Quotation'} - {target.name}",
        "",
        "## Tender particulars",
        project_summary,
        "",
        f"- Package: {target.name}",
        *(
            [f"- Client instruction: {' '.join(instructions.split())}"]
            if instructions and instructions.strip()
            else []
        ),
        "",
        "## Background",
        BACKGROUND_PLACEHOLDER,
        "",
        "## Scope and interfaces",
        REQUESTED_SERVICES_PLACEHOLDER,
        "",
        "## Programme and submission",
        PROGRAMME_PLACEHOLDER,
        "- State lead times, required access, programme dependencies and earliest mobilisation.",
        "- Submit one complete tender response with the price schedule and returnables.",
        "",
        "## Price schedule",
        "- Complete the following schedule or provide an equivalent schedule that preserves the same commercial breakdown.",
        "",
        *_price_schedule(target),
        "",
        "## Tender return and conditions",
        "**Returnables**",
        *(f"- {item}" for item in target.returnables),
        "",
        "**Qualifications and commercial basis**",
        "- Identify exclusions, qualifications, provisional sums, allowances, options, rates, and alternates separately.",
        "- State GST treatment, validity period, proposed substitutions, and matters requiring client direction.",
        "",
        f"**{'Tender' if kind == 'rft' else 'Quotation'} conditions and RFI process**",
        "- Submit RFIs through the nominated contact by the stated cutoff. Responses and addenda will be issued consistently to invitees.",
        "- Acknowledge every addendum and state all departures, substitutions, non-conformances, and alternatives separately.",
        "- Base the submission on the complete issued information and identify any document discrepancy or precedence query before pricing.",
        "- State the submission validity period and whether a conforming submission accompanies each alternative.",
        "- Allow for any stated site inspection, confidentiality, probity, and submission requirements. Respondents bear their own preparation costs.",
        "- This request is not an offer. The client may clarify, negotiate, accept none of the submissions, or discontinue the process.",
        "",
        _project_documents_heading(issued_documents),
        render_information_to_review_table(issued_documents),
        "",
        "## Citation key",
        *format_citation_key_lines(citation_index),
        "",
        "## Trace & QA",
        _trace_qa_block(assumptions, missing_inputs),
    ]
    return "\n".join(sections).rstrip() + "\n"


def _project_documents_heading(evidence: list[dict[str, Any]]) -> str:
    paths = {
        str(item.get("relative_path") or item.get("filename") or "").strip()
        for item in evidence
    }
    count = len(paths - {""})
    noun = "document" if count == 1 else "documents"
    return f"## Transmittal ({count} {noun})"


def _price_schedule(target: TradeProfile) -> list[str]:
    rows = [
        "| Price item | Scope / allowance | Amount ex GST | GST | Total inc GST |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    rows.extend(
        f"| {item} | State inclusions, exclusions and interfaces | — | — | — |"
        for item in target.price_rows
    )
    rows.extend(
        [
            "| Options / alternates | Separately identify each option | — | — | — |",
            "| Rates / provisional allowances | State unit, quantity assumption and trigger | — | — | — |",
            "| **Tender total** | Subject to stated qualifications | **—** | **—** | **—** |",
        ]
    )
    return rows


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
