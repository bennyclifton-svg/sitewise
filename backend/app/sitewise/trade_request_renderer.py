"""Deterministic RFT and RFQ structure for trade procurement."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.database.project import Project
from app.sitewise.pmp_citations import CitationIndex
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
    "information_to_review",
    "programme",
    "price_schedule",
    "returnables",
    "qualifications",
    "submission",
    "tender_conditions",
)
RFQ_SECTION_KEYS = (
    "project_summary",
    "package_basis",
    "background",
    "scope_interfaces",
    "information_to_review",
    "programme",
    "price_schedule",
    "returnables",
    "qualifications",
    "submission",
    "quotation_conditions",
)


def render_trade_request_scaffold(
    *,
    kind: str,
    project: Project,
    target: TradeProfile,
    citation_index: CitationIndex,
    forecast: dict[str, Any],
    project_evidence: list[dict[str, Any]],
    assumptions: list[str],
    missing_inputs: list[str],
    instructions: str | None,
) -> str:
    """Render common RFT/RFQ controls without model judgement or arithmetic."""
    if kind not in {"rft", "rfq"}:
        raise ValueError("kind must be rft or rfq")
    title = "Request for Tender" if kind == "rft" else "Request for Quotation"
    project_summary = render_procurement_project_summary(
        project=project,
        target_label=f"- Procurement package: {target.name}",
        citation_index=citation_index,
        forecast=forecast,
        project_evidence=project_evidence,
    )
    conditions_heading = (
        "## Tender conditions and RFI process"
        if kind == "rft"
        else "## Quotation conditions"
    )
    conditions = (
        [
            "- Submit clarification questions before pricing. Responses and any addenda will be issued to all invitees.",
            "- State all departures from the issued documents and proposed alternatives separately.",
            "- This request is not an offer, and the client may accept none of the submissions.",
        ]
        if kind == "rft"
        else [
            "- State all exclusions, qualifications, substitutions, and assumptions separately.",
            "- This quotation request is not an offer, and the client may accept none of the submissions.",
        ]
    )
    additional_instruction = (
        f"- Additional client instruction: {' '.join(instructions.split())}"
        if instructions and instructions.strip()
        else None
    )
    sections = [
        f"# {title} - {target.name}",
        "",
        "## Project Summary",
        project_summary,
        "",
        "## Package basis",
        f"- Package: {target.name}",
        "- Delivery basis: TBC by client before issue (supply only, install only, supply and install, or design and supply/install).",
        "- Contract basis and design responsibility: TBC by client before issue.",
        "",
        "## Background",
        BACKGROUND_PLACEHOLDER,
        "",
        "## Scope and interfaces",
        REQUESTED_SERVICES_PLACEHOLDER,
        "",
        "## Information to review",
        render_information_to_review_table(project_evidence, citation_index),
        "",
        "## Programme and tender timetable",
        PROGRAMME_PLACEHOLDER,
        "- Tender or quotation close date/time: TBC by client before issue.",
        "- Required-on-site date, lead-time assumptions, and programme interfaces: TBC by client before issue.",
        "",
        "## Price schedule",
        "- Complete the following schedule or provide an equivalent schedule that preserves the same commercial breakdown.",
        "",
        *_price_schedule(target),
        "",
        "## Returnables",
        *(f"- {item}" for item in target.returnables),
        "",
        "## Qualifications, exclusions, and assumptions",
        "- Identify exclusions, qualifications, provisional sums, allowances, options, rates, and alternates separately.",
        "- State GST treatment, validity period, proposed substitutions, and matters requiring client direction.",
        "",
        "## Submission",
        "- Submit the completed response, price schedule, programme/lead-time information, and returnables to the client-nominated contact.",
        "- Lodgement method and contact: TBC by client before issue.",
        "",
        conditions_heading,
        *conditions,
        "",
        "## Review items before issue",
        *(f"- TBC: {item}" for item in missing_inputs),
    ]
    if additional_instruction:
        index = sections.index("## Review items before issue")
        sections[index:index] = [additional_instruction, ""]
    return "\n".join(sections).rstrip() + "\n"


def _price_schedule(target: TradeProfile) -> list[str]:
    rows = [
        "| Price item | Scope / allowance | Amount ex GST | GST | Total inc GST |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    rows.extend(
        f"| {item} | Confirm inclusions, exclusions, and interface | TBC | TBC | TBC |"
        for item in target.price_rows
    )
    rows.extend(
        [
            "| Options / alternates | Separately identify each option | TBC | TBC | TBC |",
            "| Rates / provisional allowances | State unit, quantity assumption, and trigger | TBC | TBC | TBC |",
            "| **Tender / quotation total** | Subject to stated qualifications | **TBC** | **TBC** | **TBC** |",
        ]
    )
    return rows
