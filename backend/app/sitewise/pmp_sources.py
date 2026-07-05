"""Mandatory platform sources and section contracts for the Create PMP workflow."""

from __future__ import annotations

from typing import Literal

from app.sitewise.section_contracts import (
    document_title,
    pmp_section_headings,
)

UserRole = Literal["owner-builder", "architect-pm", "builder", "d-and-c"]
Archetype = Literal[
    "new-dwelling",
    "renovation",
    "multi-dwelling",
    "ancillary",
    "small-commercial",
]

DOCTRINE_PATH = "docs/clerk-brief.md"

ARCHETYPE_SEED_PATHS: dict[str, str] = {
    "new-dwelling": "seed/new-dwelling-guide.md",
    "renovation": "seed/renovation-guide.md",
    "multi-dwelling": "seed/multi-dwelling-guide.md",
    "ancillary": "seed/ancillary-guide.md",
    "small-commercial": "seed/small-commercial-guide.md",
}

ROLE_SEED_PATHS: dict[str, str] = {
    "owner-builder": "seed/role-owner-builder.md",
    "architect-pm": "seed/role-architect-pm.md",
    "builder": "seed/role-builder.md",
    "d-and-c": "seed/role-d-and-c.md",
}

# Cross-cutting seeds required for Create PMP / mobilisation drafting.
PMP_CROSS_CUTTING_SEED_PATHS: tuple[str, ...] = (
    "seed/setup-and-commission-guide.md",
    "seed/contract-administration-guide.md",
    "seed/cost-management-principles.md",
    "seed/program-scheduling-guide.md",
    "seed/procurement-quoting-guide.md",
)

ARCHITECT_PM_PMP_SECTIONS: tuple[str, ...] = (
    "Evidence basis and document control",
    "Project overview",
    "Architect-PM role and appointment",
    "Two-brief discipline",
    "Governance and decisions",
    "Communications protocol",
    "Fee, services and programme relationship",
    "Scope and change control",
    "Approvals and compliance",
    "Programme and staging regime",
    "Cost, programme and procurement posture",
    "Consultant coordination",
    "Risks, decisions and next actions",
    "Internal audit layer",
)

OWNER_BUILDER_MOBILISATION_SECTIONS: tuple[str, ...] = (
    "Evidence basis and document control",
    "Project overview",
    "Owner-builder role and statutory posture",
    "Project scope and self-defined brief",
    "Planning and approvals pathway",
    "Programme and staging regime",
    "Cost and contingency posture",
    "Trade procurement posture",
    "Risks, decisions and next actions",
    "Internal audit layer",
)

BUILDER_MOBILISATION_SECTIONS: tuple[str, ...] = (
    "Evidence basis and document control",
    "Project overview",
    "Builder role and contract basis",
    "Statutory instruments and insurance",
    "Planning and approvals pathway",
    "Programme and staging regime",
    "Procurement and subcontractor posture",
    "Risks, decisions and next actions",
    "Internal audit layer",
)

D_AND_C_MOBILISATION_SECTIONS: tuple[str, ...] = (
    "Evidence basis and document control",
    "Project overview",
    "D&C role, design responsibility and contract basis",
    "Statutory instruments and insurance",
    "Design pack and consultant coordination",
    "Planning and approvals pathway",
    "Programme and staging regime",
    "Procurement posture",
    "Risks, decisions and next actions",
    "Internal audit layer",
)

ROLE_SECTION_HEADINGS: dict[str, tuple[str, ...]] = {
    "architect-pm": ARCHITECT_PM_PMP_SECTIONS,
    "owner-builder": OWNER_BUILDER_MOBILISATION_SECTIONS,
    "builder": BUILDER_MOBILISATION_SECTIONS,
    "d-and-c": D_AND_C_MOBILISATION_SECTIONS,
}

ROLE_DOCUMENT_TITLES: dict[str, str] = {
    "architect-pm": "Project Management Plan",
    "owner-builder": "Owner-Builder Mobilisation Plan",
    "builder": "Builder Mobilisation Plan",
    "d-and-c": "D&C Mobilisation Plan",
}


def _project_taxonomy_kwargs(project: object | None) -> dict[str, str | None]:
    if project is None or getattr(project, "building_class", None) is None:
        return {}

    from app.sitewise.archetype_bridge import effective_taxonomy

    taxonomy = effective_taxonomy(project)
    return {
        "building_class": taxonomy.building_class,
        "work_type": taxonomy.work_type,
    }


def required_platform_paths(
    *,
    archetype: str,
    user_role: str,
    project: object | None = None,
    building_class: str | None = None,
    work_type: str | None = None,
) -> list[str]:
    """Return the mandatory doctrine + overlay + cross-cutting paths for Create PMP.

    Delegates to the platform knowledge catalog (seed frontmatter is the
    source of truth); tests/sitewise/test_catalog_parity.py pins the output
    to the frozen constants above.
    """
    from app.sitewise.knowledge_catalog import select_required_paths

    taxonomy_kwargs = _project_taxonomy_kwargs(project)
    if building_class is not None:
        taxonomy_kwargs["building_class"] = building_class
    if work_type is not None:
        taxonomy_kwargs["work_type"] = work_type
    return select_required_paths(
        workflow="create-pmp",
        archetype=archetype,
        user_role=user_role,
        **taxonomy_kwargs,
    )


def required_section_headings(
    user_role: str,
    *,
    project: object | None = None,
    building_class: str | None = None,
    work_type: str | None = None,
) -> tuple[str, ...]:
    taxonomy_kwargs = _project_taxonomy_kwargs(project)
    if building_class is not None:
        taxonomy_kwargs["building_class"] = building_class
    if work_type is not None:
        taxonomy_kwargs["work_type"] = work_type
    if taxonomy_kwargs.get("building_class") is not None:
        return pmp_section_headings(work_type=taxonomy_kwargs.get("work_type"))

    headings = ROLE_SECTION_HEADINGS.get(user_role)
    if headings is None:
        msg = f"Unsupported user_role for Create PMP: {user_role!r}"
        raise ValueError(msg)
    return headings


def document_title_for_role(
    user_role: str,
    *,
    project: object | None = None,
    building_class: str | None = None,
    work_type: str | None = None,
) -> str:
    taxonomy_kwargs = _project_taxonomy_kwargs(project)
    if building_class is not None:
        taxonomy_kwargs["building_class"] = building_class
    if work_type is not None:
        taxonomy_kwargs["work_type"] = work_type
    if taxonomy_kwargs.get("building_class") is not None:
        return document_title(user_role, taxonomy_kwargs.get("work_type"))

    title = ROLE_DOCUMENT_TITLES.get(user_role)
    if title is None:
        msg = f"Unsupported user_role for Create PMP: {user_role!r}"
        raise ValueError(msg)
    return title


def seed_consulted_includes_required(
    seed_consulted: list[str],
    *,
    archetype: str,
    user_role: str,
    project: object | None = None,
    building_class: str | None = None,
    work_type: str | None = None,
) -> list[str]:
    """Return mandatory seed paths missing from the model's seed_consulted list."""
    required = [
        path
        for path in required_platform_paths(
            archetype=archetype,
            user_role=user_role,
            project=project,
            building_class=building_class,
            work_type=work_type,
        )
        if path != DOCTRINE_PATH
    ]
    normalized = {entry.strip().lower() for entry in seed_consulted}
    missing: list[str] = []
    for path in required:
        filename = path.split("/")[-1].lower()
        if not any(filename in entry for entry in normalized):
            missing.append(path)
    return missing
