"""Mandatory platform sources and section contracts for the Create PMP workflow."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from app.sitewise.section_contracts import (
    document_title as _section_document_title,
    pmp_section_headings,
)

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

# Role is collapsed to a single overlay. This is the only role seed the catalog
# resolves; the other three role overlays are retired.
ROLE_SEED_PATHS: dict[str, str] = {
    "architect-pm": "seed/role-architect-pm.md",
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
    "Architect role and appointment",
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

PMP_DOCUMENT_TITLE = "Project Management Plan"


def _project_taxonomy_kwargs(project: object | None) -> dict[str, object]:
    if project is None or getattr(project, "building_class", None) is None:
        return {}

    from app.sitewise.archetype_bridge import (
        effective_taxonomy,
        effective_work_scopes,
    )

    taxonomy = effective_taxonomy(project)
    return {
        "building_class": taxonomy.building_class,
        "work_type": taxonomy.work_type,
        "subclasses": taxonomy.subclasses,
        "work_scopes": effective_work_scopes(project),
    }


def required_platform_paths(
    *,
    archetype: str,
    project: object | None = None,
    building_class: str | None = None,
    work_type: str | None = None,
    subclasses: Sequence[str] | None = None,
    work_scopes: Sequence[str] | None = None,
) -> list[str]:
    """Return the mandatory doctrine + overlay + cross-cutting paths for Create PMP.

    Delegates to the platform knowledge catalog (seed frontmatter is the
    source of truth); tests/sitewise/test_catalog_parity.py pins the output
    to the frozen constants above.
    """
    from app.sitewise.seed_routing import select_seed_knowledge_for_taxonomy

    taxonomy_kwargs = _project_taxonomy_kwargs(project)
    if building_class is not None:
        taxonomy_kwargs["building_class"] = building_class
    if work_type is not None:
        taxonomy_kwargs["work_type"] = work_type
    if subclasses is not None:
        taxonomy_kwargs["subclasses"] = subclasses
    if work_scopes is not None:
        taxonomy_kwargs["work_scopes"] = work_scopes
    selection = select_seed_knowledge_for_taxonomy(
        "pmp",
        archetype=archetype,
        **taxonomy_kwargs,
    )
    return list(selection.required_paths)


def required_section_headings(
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
        # Narrow to the sections this project needs when a full taxonomy context
        # is resolvable; callers passing loose kwargs still get the full list.
        sections = None
        if project is not None:
            from app.sitewise.pmp_taxonomy_context import pmp_taxonomy_context

            context = pmp_taxonomy_context(project)
            if context is not None and context.sections:
                sections = context.sections
        return pmp_section_headings(
            work_type=taxonomy_kwargs.get("work_type"), sections=sections
        )
    return ARCHITECT_PM_PMP_SECTIONS


def document_title(
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
        return _section_document_title(taxonomy_kwargs.get("work_type"))
    return PMP_DOCUMENT_TITLE


def seed_consulted_includes_required(
    seed_consulted: list[str],
    *,
    archetype: str,
    project: object | None = None,
    building_class: str | None = None,
    work_type: str | None = None,
    subclasses: Sequence[str] | None = None,
    work_scopes: Sequence[str] | None = None,
) -> list[str]:
    """Return mandatory seed paths missing from the model's seed_consulted list."""
    required = [
        path
        for path in required_platform_paths(
            archetype=archetype,
            project=project,
            building_class=building_class,
            work_type=work_type,
            subclasses=subclasses,
            work_scopes=work_scopes,
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
