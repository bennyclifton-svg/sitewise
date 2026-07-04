"""Mandatory platform sources and section contracts for the Create Cost Plan workflow."""

from __future__ import annotations

from app.sitewise.pmp_sources import (
    ARCHETYPE_SEED_PATHS,
    DOCTRINE_PATH,
    ROLE_SEED_PATHS,
)

RESIDENTIAL_ARCHETYPES: frozenset[str] = frozenset(
    {"new-dwelling", "renovation", "multi-dwelling", "ancillary"}
)

NSW_RESIDENTIAL_COST_REFERENCE = "skills/reference/nsw-residential-cost-breakdown-reference.md"

COST_PLAN_MANDATORY_SEED = "seed/cost-management-principles.md"

COST_PLAN_SECTIONS: tuple[str, ...] = (
    "Project name and location",
    "Source evidence used",
    "Budget reconciliation and control decision",
    "Total approved or indicative budget",
    "GST basis",
    "Cost breakdown by category",
    "Known locked contract and appointment values",
    "Allowances and contingency",
    "PM fee treatment",
    "Assumptions and exclusions",
    "Risks and review questions",
    "Authority, compliance and procurement gates",
    "Recommended next steps",
    "Internal audit layer",
)

COST_PLAN_DOCUMENT_TITLE = "Project Cost Plan"


def required_platform_paths(*, archetype: str, user_role: str) -> list[str]:
    """Return mandatory doctrine, overlay, and cost-plan seeds.

    Delegates to the platform knowledge catalog (seed frontmatter is the
    source of truth); tests/sitewise/test_catalog_parity.py pins the output
    to the frozen constants above.
    """
    from app.sitewise.knowledge_catalog import select_required_paths

    return select_required_paths(
        workflow="create-cost-plan", archetype=archetype, user_role=user_role
    )


def required_section_headings(_user_role: str) -> tuple[str, ...]:
    return COST_PLAN_SECTIONS


def document_title_for_role(_user_role: str) -> str:
    return COST_PLAN_DOCUMENT_TITLE


def seed_consulted_includes_required(
    seed_consulted: list[str],
    *,
    archetype: str,
    user_role: str,
) -> list[str]:
    """Return mandatory seed paths missing from the model's seed_consulted list."""
    required = [
        path
        for path in required_platform_paths(archetype=archetype, user_role=user_role)
        if path != DOCTRINE_PATH
    ]
    normalized = {entry.strip().lower() for entry in seed_consulted}
    missing: list[str] = []
    for path in required:
        filename = path.split("/")[-1].lower()
        if not any(filename in entry for entry in normalized):
            missing.append(path)
    return missing
