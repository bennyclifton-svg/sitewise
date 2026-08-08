"""Deterministic universal RFT structure for trade procurement."""

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
        f"# Request for Tender - {target.name}",
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
        "## Information issued and citations",
        render_information_to_review_table(project_evidence, citation_index),
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
        "**Tender conditions and RFI process**",
        "- Submit clarification questions before pricing. Responses and addenda will be issued to all invitees.",
        "- State all departures from the issued documents and proposed alternatives separately.",
        "- This request is not an offer, and the client may accept none of the submissions.",
        "",
        "## Trace & QA",
        _trace_qa_block(assumptions, missing_inputs),
    ]
    return "\n".join(sections).rstrip() + "\n"


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
