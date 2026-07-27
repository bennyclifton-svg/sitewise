"""Mandatory platform sources and section contracts for the Create Cost Plan workflow."""

from __future__ import annotations

from collections.abc import Sequence

from app.sitewise.cost_plan_coverage import coverage_spec
from app.sitewise.pmp_sources import DOCTRINE_PATH

RESIDENTIAL_ARCHETYPES: frozenset[str] = frozenset(
    {"new-dwelling", "renovation", "multi-dwelling", "ancillary"}
)

NSW_RESIDENTIAL_COST_REFERENCE = coverage_spec(
    "residential_class1_new"
).reference_path
NSW_MULTI_RESIDENTIAL_COST_REFERENCE = coverage_spec(
    "multi_residential"
).reference_path
NSW_COMMERCIAL_FITOUT_COST_REFERENCE = coverage_spec(
    "commercial_fitout"
).reference_path
NSW_COMMERCIAL_BASE_BUILDING_COST_REFERENCE = coverage_spec(
    "commercial_base_building"
).reference_path
NSW_BUILDING_REMEDIATION_COST_REFERENCE = coverage_spec(
    "building_remediation"
).reference_path
NSW_INDUSTRIAL_WAREHOUSE_COST_REFERENCE = coverage_spec(
    "industrial_warehouse"
).reference_path
NSW_INDUSTRIAL_PROCESS_COST_REFERENCE = coverage_spec(
    "industrial_process"
).reference_path
NSW_INDUSTRIAL_COLD_CHAIN_COST_REFERENCE = coverage_spec(
    "industrial_cold_chain"
).reference_path
NSW_DATA_CENTRE_COST_REFERENCE = coverage_spec("data_centre").reference_path

COST_PLAN_MANDATORY_SEED = "seed/cost-management-principles.md"

COST_PLAN_SECTIONS: tuple[str, ...] = (
    "Cost plan summary and control decision",
    "Budget reconciliation and cost breakdown",
    "Commitments, allowances and exclusions",
    "Risks, delivery gates and next actions",
    "Source evidence and audit trail",
)

COST_PLAN_DOCUMENT_TITLE = "Project Cost Plan"


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
    """Return mandatory doctrine, overlay, and cost-plan seeds.

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
    if subclasses is not None:
        taxonomy_kwargs["subclasses"] = subclasses
    if work_scopes is not None:
        taxonomy_kwargs["work_scopes"] = work_scopes
    return select_required_paths(
        workflow="create-cost-plan",
        archetype=archetype,
        **taxonomy_kwargs,
    )


def required_section_headings() -> tuple[str, ...]:
    return COST_PLAN_SECTIONS


def document_title() -> str:
    return COST_PLAN_DOCUMENT_TITLE


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
