"""Single source of truth for supported NSW Cost Plan taxonomy families."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

CoverageFamily = Literal[
    "residential_class1_new",
    "residential_class1_refurb",
    "multi_residential",
    "commercial_fitout",
    "commercial_base_building",
    "building_remediation",
    "industrial_warehouse",
    "industrial_process",
    "industrial_cold_chain",
    "data_centre",
]


@dataclass(frozen=True, slots=True)
class CostPlanCoverage:
    family: CoverageFamily
    reference_path: str
    label: str
    structure_only: bool


_COVERAGE: dict[CoverageFamily, CostPlanCoverage] = {
    "residential_class1_new": CostPlanCoverage(
        family="residential_class1_new",
        reference_path="skills/reference/nsw-residential-cost-breakdown-reference.md",
        label="NSW Class 1 house/townhouse new-build reference set",
        structure_only=False,
    ),
    "residential_class1_refurb": CostPlanCoverage(
        family="residential_class1_refurb",
        reference_path="skills/reference/nsw-residential-cost-breakdown-reference.md",
        label=(
            "NSW Class 1 house/townhouse refurbishment/extension scaffold set "
            "(structure only; no rate pack)"
        ),
        structure_only=True,
    ),
    "multi_residential": CostPlanCoverage(
        family="multi_residential",
        reference_path=(
            "skills/reference/nsw-multi-residential-cost-breakdown-reference.md"
        ),
        label=(
            "NSW apartment/BTR/student/social-affordable multi-residential "
            "scaffold set (structure only; no rate pack)"
        ),
        structure_only=True,
    ),
    "commercial_fitout": CostPlanCoverage(
        family="commercial_fitout",
        reference_path=(
            "skills/reference/nsw-commercial-fitout-cost-breakdown-reference.md"
        ),
        label=(
            "NSW Class 5 office/serviced-office commercial fit-out scaffold set "
            "(structure only; no rate pack)"
        ),
        structure_only=True,
    ),
    "commercial_base_building": CostPlanCoverage(
        family="commercial_base_building",
        reference_path=(
            "skills/reference/nsw-commercial-base-building-cost-breakdown-reference.md"
        ),
        label=(
            "NSW office/retail commercial base-building scaffold set "
            "(structure only; no rate pack)"
        ),
        structure_only=True,
    ),
    "building_remediation": CostPlanCoverage(
        family="building_remediation",
        reference_path=(
            "skills/reference/nsw-building-remediation-cost-breakdown-reference.md"
        ),
        label=(
            "NSW building rectification/remediation scaffold set "
            "(structure only; no rate pack)"
        ),
        structure_only=True,
    ),
    "industrial_warehouse": CostPlanCoverage(
        family="industrial_warehouse",
        reference_path=(
            "skills/reference/nsw-industrial-warehouse-cost-breakdown-reference.md"
        ),
        label=(
            "NSW industrial warehouse/logistics Class 7b scaffold set "
            "(structure only; no rate pack)"
        ),
        structure_only=True,
    ),
    "industrial_process": CostPlanCoverage(
        family="industrial_process",
        reference_path=(
            "skills/reference/nsw-industrial-process-facility-cost-breakdown-reference.md"
        ),
        label=(
            "NSW manufacturing/process-facility scaffold set "
            "(structure only; no rate pack)"
        ),
        structure_only=True,
    ),
    "industrial_cold_chain": CostPlanCoverage(
        family="industrial_cold_chain",
        reference_path=(
            "skills/reference/nsw-industrial-cold-chain-cost-breakdown-reference.md"
        ),
        label=(
            "NSW cold-storage/food-processing scaffold set "
            "(structure only; no rate pack)"
        ),
        structure_only=True,
    ),
    "data_centre": CostPlanCoverage(
        family="data_centre",
        reference_path="skills/reference/nsw-data-centre-cost-breakdown-reference.md",
        label="NSW data-centre scaffold set (structure only; no rate pack)",
        structure_only=True,
    ),
}

_CLASS_1 = frozenset({"house", "townhouses"})
_MULTI_RESIDENTIAL = frozenset(
    {"apartments", "btr", "student_housing", "social_affordable_housing"}
)
_COMMERCIAL_BASE = frozenset(
    {"office", "retail_shopping_centre", "retail_standalone"}
)
_COMMERCIAL_FITOUT = frozenset({"office", "serviced_office_coworking"})
_WAREHOUSE = frozenset({"warehouse", "logistics_ecommerce"})
_PROCESS = frozenset({"manufacturing", "heavy_manufacturing"})
_COLD_CHAIN = frozenset({"cold_storage", "food_processing"})
_BUILDING_REMEDIATION_SCOPES = frozenset(
    {"waterproofing_rectification", "fire_safety_orders", "facade_cladding"}
)
_CONSTRUCTION_WORK_TYPES = frozenset({"new", "refurb", "extend"})


def resolve_cost_plan_coverage(
    *,
    building_class: str | None,
    work_type: str | None,
    subclasses: Iterable[str] = (),
    work_scopes: Iterable[str] = (),
) -> CostPlanCoverage | None:
    """Resolve an exact supported family; return ``None`` for intentional gaps."""
    subclass_values = frozenset(subclasses)
    scope_values = frozenset(work_scopes)

    if work_type == "remediation":
        if scope_values & _BUILDING_REMEDIATION_SCOPES:
            return _COVERAGE["building_remediation"]
        return None
    if work_type not in _CONSTRUCTION_WORK_TYPES:
        return None

    if building_class == "residential":
        if subclass_values & _CLASS_1:
            family: CoverageFamily = (
                "residential_class1_new"
                if work_type == "new"
                else "residential_class1_refurb"
            )
            return _COVERAGE[family]
        if work_type in {"new", "extend"} and subclass_values & _MULTI_RESIDENTIAL:
            return _COVERAGE["multi_residential"]
        return None

    if building_class == "commercial":
        if work_type == "refurb" and subclass_values & _COMMERCIAL_FITOUT:
            return _COVERAGE["commercial_fitout"]
        if work_type in {"new", "extend"} and subclass_values & _COMMERCIAL_BASE:
            return _COVERAGE["commercial_base_building"]
        return None

    if building_class == "industrial":
        if subclass_values & _WAREHOUSE:
            return _COVERAGE["industrial_warehouse"]
        if subclass_values & _PROCESS:
            return _COVERAGE["industrial_process"]
        if subclass_values & _COLD_CHAIN:
            return _COVERAGE["industrial_cold_chain"]
        if "data_centre" in subclass_values:
            return _COVERAGE["data_centre"]
    return None


def unsupported_coverage_reason(
    *,
    building_class: str | None,
    work_type: str | None,
) -> str:
    if work_type == "advisory":
        return (
            "Advisory work uses fee and deliverable planning, not a construction "
            "Cost Plan scaffold."
        )
    if work_type == "remediation":
        return (
            "Cost Plan remediation coverage currently requires a confirmed building "
            "rectification scope: waterproofing, fire-safety orders, or facade/cladding. "
            "Contaminated-land remediation needs a dedicated cost reference."
        )
    if building_class == "residential":
        return (
            "Cost Plan residential coverage currently includes NSW Class 1 houses/"
            "townhouses and selected apartment, BTR, student-housing and social/"
            "affordable-housing projects."
        )
    if building_class == "commercial":
        return (
            "Cost Plan commercial coverage currently includes NSW office/coworking "
            "fit-outs and office/retail base-building new works or extensions."
        )
    if building_class == "industrial":
        return (
            "Cost Plan industrial coverage currently includes NSW warehouse/logistics, "
            "manufacturing/process, cold-chain and data-centre projects. Dangerous "
            "goods, GMP, cleanroom, battery and waste-to-energy work remains specialist."
        )
    return (
        "Cost Plan coverage is currently limited to supported NSW residential, "
        "commercial and industrial reference families."
    )


def coverage_spec(family: CoverageFamily) -> CostPlanCoverage:
    return _COVERAGE[family]
