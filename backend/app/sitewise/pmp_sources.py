"""Mandatory platform sources and section contracts for the Create PMP workflow."""

from __future__ import annotations

from typing import Literal

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


def required_platform_paths(*, archetype: str, user_role: str) -> list[str]:
    """Return the mandatory doctrine + overlay + cross-cutting paths for Create PMP."""
    archetype_path = ARCHETYPE_SEED_PATHS.get(archetype)
    role_path = ROLE_SEED_PATHS.get(user_role)
    if archetype_path is None or role_path is None:
        msg = f"Unsupported overlay combination: archetype={archetype!r}, user_role={user_role!r}"
        raise ValueError(msg)

    paths = [DOCTRINE_PATH, archetype_path, role_path, *PMP_CROSS_CUTTING_SEED_PATHS]
    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered


def required_section_headings(user_role: str) -> tuple[str, ...]:
    headings = ROLE_SECTION_HEADINGS.get(user_role)
    if headings is None:
        msg = f"Unsupported user_role for Create PMP: {user_role!r}"
        raise ValueError(msg)
    return headings


def document_title_for_role(user_role: str) -> str:
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
