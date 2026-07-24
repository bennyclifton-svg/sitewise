"""Universal PMP 2.0 section contracts for taxonomy-backed projects."""

from __future__ import annotations

from app.sitewise.taxonomy import PMP_CORE_SECTIONS

PMP_SECTION_HEADINGS: dict[str, str] = {
    "snapshot": "Project Summary",
    "scope-client-requirements": "Brief",
    "consultants": "Consultants",
    "compliance-approvals": "Planning and Compliance",
    "programme": "Programme",
    "cost-budget": "Cost Planning",
    "procurement-delivery": "Procurement and Delivery",
    "risks": "Risks and mitigations",
    "actions-decisions": "Actions and decisions",
    "citation-key": "Citation key",
}

WORK_TYPE_HEADING_VARIANTS: dict[str, dict[str, str]] = {
    "advisory": {
        "procurement-delivery": "Services and deliverables",
        "programme": "Programme of services",
    },
}

def pmp_section_headings(*, work_type: str | None) -> tuple[str, ...]:
    """Return the universal section headings in emphasis-profile order."""
    variants = WORK_TYPE_HEADING_VARIANTS.get(work_type or "", {})
    return tuple(
        variants.get(section_id, PMP_SECTION_HEADINGS[section_id])
        for section_id in PMP_CORE_SECTIONS
    )


def heading_for_section_id(section_id: str, *, work_type: str | None) -> str:
    """Return the display heading for an emphasis-profile section id."""
    variants = WORK_TYPE_HEADING_VARIANTS.get(work_type or "", {})
    return variants.get(section_id, PMP_SECTION_HEADINGS[section_id])


def section_id_for_heading(heading: str, *, work_type: str | None) -> str | None:
    """Resolve a display heading back to its canonical section id."""
    normalized = heading.strip().lower()
    for section_id in PMP_CORE_SECTIONS:
        if heading_for_section_id(section_id, work_type=work_type).lower() == normalized:
            return section_id
    return None


def document_title(work_type: str | None) -> str:
    """Return the PMP title for the work-type contract."""
    if work_type == "advisory":
        return "Advisory Services Plan"
    return "Project Management Plan"
