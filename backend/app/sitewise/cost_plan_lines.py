"""Structured cost-plan lines for a project's coverage family.

Owns the family taxonomies and the row-building rules that used to live inside
the Markdown renderer, so the renderer, the workbook and the typed importer can
all read the same lines instead of parsing a table out of prose.

This module must not import the renderer or the workbook — they import it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.database.project import Project
from app.sitewise.archetype_bridge import effective_taxonomy, effective_work_scopes
from app.sitewise.cost_plan_coverage import (
    CoverageFamily,
    coverage_spec,
    resolve_cost_plan_coverage,
)
from app.sitewise.cost_plan_evidence import CostPlanEvidencePack
from app.sitewise.mobilisation_evidence import GAP_CERTIFIER, pack_has_gap


def _no_rate_pack_disclosure(family: CoverageFamily) -> str:
    if family == "industrial_warehouse":
        return (
            "No NSW industrial rate pack exists yet — this is a structure-only "
            "scaffold; every construction line is a lump-sum TBC pending "
            "head-builder tender."
        )
    subject = {
        "residential_class1_refurb": "Class 1 refurbishment/extension",
        "multi_residential": "multi-residential",
        "commercial_fitout": "commercial fit-out",
        "commercial_base_building": "commercial base-building",
        "building_remediation": "building remediation",
        "industrial_warehouse": "industrial warehouse",
        "industrial_process": "industrial process-facility",
        "industrial_cold_chain": "industrial cold-chain",
        "data_centre": "data-centre",
        "residential_class1_new": "Class 1 residential",
    }[family]
    return (
        f"No NSW {subject} rate pack exists yet — this is a structure-only "
        "scaffold; every construction line is a lump-sum TBC pending QS or "
        "head-builder pricing."
    )

_RESIDENTIAL_FEE_ROWS: tuple[tuple[str, str], ...] = (
    ("2", "DA and CC authority fees"),
    ("3", "BASIX certificate fee"),
    ("4", "Sydney Water / infrastructure"),
    ("5", "Levies and statutory"),
)

_RESIDENTIAL_CONSULTANT_ROWS: tuple[tuple[str, str], ...] = (
    ("6", "Structural engineer"),
    ("7", "Geotechnical engineer"),
    ("8", "Surveyor"),
    ("9", "Hydraulic / wastewater"),
    ("10", "BASIX / energy assessor"),
    ("11", "Principal certifier"),
)

_RESIDENTIAL_CONSTRUCTION_ROWS: tuple[tuple[str, str], ...] = (
    ("12", "Preliminaries"),
    ("13", "Siteworks and demolition"),
    ("14", "Footings and slab"),
    ("15", "Framing and roof"),
    ("16", "External envelope and lockup"),
    ("17", "Internal linings and joinery"),
    ("18", "Kitchen and bathrooms"),
    ("19", "Building services"),
    ("20", "Finishes and external works"),
)

# Practice-benchmark elemental split (Assumption — not market-rate advice).
# Labels MUST match _RESIDENTIAL_CONSTRUCTION_ROWS; integer percents sum to 100.
_RESIDENTIAL_CONSTRUCTION_BENCHMARK_PCT: tuple[tuple[str, int], ...] = (
    ("Preliminaries", 8),
    ("Siteworks and demolition", 7),
    ("Footings and slab", 12),
    ("Framing and roof", 18),
    ("External envelope and lockup", 15),
    ("Internal linings and joinery", 14),
    ("Kitchen and bathrooms", 9),
    ("Building services", 10),
    ("Finishes and external works", 7),
)

_RESIDENTIAL_PC_ALLOWANCE_ROWS: tuple[tuple[str, str], ...] = (
    ("21", "Kitchen joinery PC"),
    ("22", "Wet area / sanitary PC"),
    ("23", "Floor coverings PC"),
    ("24", "Lighting fittings PC"),
)

_RESIDENTIAL_CONTINGENCY_CODE = "25"

# NSW Class 5 office / serviced-office commercial fit-out taxonomy. It keeps tenant,
# landlord and client-direct interfaces visible and carries no benchmark percentage
# split; see nsw-commercial-fitout-cost-breakdown-reference.md.
_COMMERCIAL_FITOUT_FEE_ROWS: tuple[tuple[str, str], ...] = (
    ("2", "Approval, certification and landlord review fees"),
    ("3", "Levies, utility and statutory charges"),
    ("4", "Landlord bonds and refundable deposits"),
)

_COMMERCIAL_FITOUT_CONSULTANT_ROWS: tuple[tuple[str, str], ...] = (
    ("5", "Architect / interior designer"),
    ("6", "Project manager / contract administrator"),
    ("7", "Building services engineers"),
    ("8", "Fire engineer and certifier"),
    ("9", "Structural engineer"),
    ("10", "Acoustic, access, ICT / AV and specialist consultants"),
)

_COMMERCIAL_FITOUT_CONSTRUCTION_ROWS: tuple[tuple[str, str], ...] = (
    ("11", "Preliminaries and occupied-building controls"),
    ("12", "Investigations, approvals and make-safe"),
    ("13", "Strip-out and demolition"),
    ("14", "Structural and builder's work"),
    ("15", "Partitions, doors and glazing"),
    ("16", "Ceilings and acoustic treatments"),
    ("17", "Joinery and fixtures"),
    ("18", "Finishes"),
    ("19", "Mechanical services"),
    ("20", "Electrical, lighting and controls"),
    ("21", "Hydraulic services"),
    ("22", "Fire and life-safety services"),
    ("23", "ICT, AV and security"),
    ("24", "Signage and wayfinding"),
    ("25", "Testing, commissioning and handover"),
    ("26", "Specialist tenant systems — scope gap"),
    ("27", "Landlord / base-building interface works — allocation gap"),
)

_COMMERCIAL_FITOUT_PC_ALLOWANCE_ROWS: tuple[tuple[str, str], ...] = (
    ("28", "Client-direct furniture, IT and equipment allowance"),
)

_COMMERCIAL_FITOUT_CONTINGENCY_CODE = "29"

# NSW industrial warehouse/logistics (Class 7b) taxonomy — no BASIX or residential
# kitchen/joinery language; see nsw-industrial-warehouse-cost-breakdown-reference.md.
_INDUSTRIAL_FEE_ROWS: tuple[tuple[str, str], ...] = (
    ("2", "DA and CC authority fees"),
    ("3", "Sydney Water / infrastructure"),
    ("4", "Levies and statutory"),
)

_INDUSTRIAL_CONSULTANT_ROWS: tuple[tuple[str, str], ...] = (
    ("5", "Structural engineer"),
    ("6", "Geotechnical engineer"),
    ("7", "Surveyor"),
    ("8", "Civil engineer"),
    ("9", "Fire engineer"),
    ("10", "Principal certifier"),
)

# No benchmark split exists for this family; every row, including the
# specialist-systems scope gap, remains a lump-sum TBC.
_INDUSTRIAL_CONSTRUCTION_ROWS: tuple[tuple[str, str], ...] = (
    ("11", "Preliminaries"),
    ("12", "Siteworks and earthworks"),
    ("13", "Substructure and slabs"),
    ("14", "Structural steel and frame"),
    ("15", "Roof cladding and envelope"),
    ("16", "Dock hardstand and yard"),
    ("17", "Office fitout (ancillary)"),
    ("18", "Building services"),
    ("19", "External works and stormwater"),
    ("20", "Specialist systems (racking, cool rooms, dock automation) — scope gap"),
)

# Industrial has no PC-allowance workbook group (see reference doc's Workbook-Ready
# Groups); the specialist-systems gap row above stands in for it.
_INDUSTRIAL_PC_ALLOWANCE_ROWS: tuple[tuple[str, str], ...] = ()

_INDUSTRIAL_CONTINGENCY_CODE = "21"

_RESIDENTIAL_REFURB_CONSTRUCTION_ROWS: tuple[tuple[str, str], ...] = (
    ("12", "Investigations, surveys and opening-up"),
    ("13", "Preliminaries, protection and temporary works"),
    ("14", "Hazardous-material controls and demolition"),
    ("15", "Existing-structure repair and new structural work"),
    ("16", "Envelope, roofing and old-to-new weatherproofing"),
    ("17", "Partitions, linings, doors and joinery"),
    ("18", "Kitchen, bathrooms and fittings"),
    ("19", "Building-services alterations and upgrades"),
    ("20", "Finishes, external works and making good"),
)

_MULTI_RESIDENTIAL_FEE_ROWS: tuple[tuple[str, str], ...] = (
    ("2", "Planning, certification and authority fees"),
    ("3", "Infrastructure and utility charges"),
    ("4", "Levies and statutory charges"),
)
_MULTI_RESIDENTIAL_CONSULTANT_ROWS: tuple[tuple[str, str], ...] = (
    ("5", "Architect and project manager"),
    ("6", "Quantity surveyor"),
    ("7", "Planning, survey and geotechnical"),
    ("8", "Structural and civil engineers"),
    ("9", "Facade and waterproofing consultants"),
    ("10", "Mechanical, electrical and hydraulic engineers"),
    ("11", "Fire engineer and certifier"),
    ("12", "Access, acoustic and sustainability consultants"),
)
_MULTI_RESIDENTIAL_CONSTRUCTION_ROWS: tuple[tuple[str, str], ...] = (
    ("13", "Preliminaries, logistics and temporary works"),
    ("14", "Demolition, remediation and enabling works"),
    ("15", "Earthworks, substructure and basement"),
    ("16", "Superstructure"),
    ("17", "Facade, windows, roofing and waterproofing"),
    ("18", "Internal walls, doors and finishes"),
    ("19", "Joinery, appliances, fixtures and equipment"),
    ("20", "Vertical transport"),
    ("21", "Mechanical services"),
    ("22", "Electrical, communications and security"),
    ("23", "Hydraulic services"),
    ("24", "Fire and life-safety systems"),
    ("25", "External works, landscape and utility connections"),
    ("26", "Testing, commissioning and handover"),
    ("27", "Specialist tenure/operational requirements â€” scope gap"),
)
_MULTI_RESIDENTIAL_PC_ALLOWANCE_ROWS: tuple[tuple[str, str], ...] = (
    ("28", "Client/operator equipment and loose-furniture allowance"),
)
_MULTI_RESIDENTIAL_CONTINGENCY_CODE = "29"

_COMMERCIAL_BASE_FEE_ROWS: tuple[tuple[str, str], ...] = (
    ("2", "Planning, certification and authority fees"),
    ("3", "Infrastructure, utility and statutory charges"),
    ("4", "Levies and approval-related contributions"),
)
_COMMERCIAL_BASE_CONSULTANT_ROWS: tuple[tuple[str, str], ...] = (
    ("5", "Architect and project manager"),
    ("6", "Quantity surveyor"),
    ("7", "Planning, survey and geotechnical"),
    ("8", "Structural and civil engineers"),
    ("9", "Facade consultant"),
    ("10", "Building-services engineers"),
    ("11", "Fire engineer, certifier, access and acoustic consultants"),
)
_COMMERCIAL_BASE_CONSTRUCTION_ROWS: tuple[tuple[str, str], ...] = (
    ("12", "Preliminaries, logistics and temporary works"),
    ("13", "Demolition, remediation and enabling works"),
    ("14", "Earthworks and substructure"),
    ("15", "Superstructure"),
    ("16", "Facade, windows, roofing and waterproofing"),
    ("17", "Core, common-area and back-of-house fitout"),
    ("18", "Vertical transport"),
    ("19", "Mechanical services"),
    ("20", "Electrical, lighting and controls"),
    ("21", "Hydraulic services"),
    ("22", "Fire and life-safety services"),
    ("23", "ICT, security and building-management systems"),
    ("24", "External works, landscape and utility connections"),
    ("25", "Testing, commissioning and handover"),
    ("26", "Tenant, anchor and operator interfaces â€” scope gap"),
)
_COMMERCIAL_BASE_PC_ALLOWANCE_ROWS: tuple[tuple[str, str], ...] = ()
_COMMERCIAL_BASE_CONTINGENCY_CODE = "27"

_REMEDIATION_FEE_ROWS: tuple[tuple[str, str], ...] = (
    ("2", "Investigation, approval and certification fees"),
    ("3", "Access, permit, authority and statutory charges"),
)
_REMEDIATION_CONSULTANT_ROWS: tuple[tuple[str, str], ...] = (
    ("4", "Lead building/remediation consultant"),
    ("5", "Project manager and quantity surveyor"),
    ("6", "Structural, facade and waterproofing consultants"),
    ("7", "Fire engineer and certifier"),
    ("8", "Building-services engineers"),
    ("9", "Access, hazardous-material and specialist testing consultants"),
)
_REMEDIATION_CONSTRUCTION_ROWS: tuple[tuple[str, str], ...] = (
    ("10", "Investigations, probes, testing and monitoring"),
    ("11", "Preliminaries, access, protection and occupied-building controls"),
    ("12", "Temporary works, make-safe and enabling works"),
    ("13", "Demolition, removal and hazardous-material controls"),
    ("14", "Substrate and structural repairs"),
    ("15", "Waterproofing and weatherproofing rectification"),
    ("16", "Facade and cladding rectification"),
    ("17", "Fire and life-safety rectification"),
    ("18", "Building-services modifications and reinstatement"),
    ("19", "Internal finishes, external works and making good"),
    ("20", "Testing, validation, certification and handover"),
    ("21", "Access, decanting and occupant-interface works â€” scope gap"),
)
_REMEDIATION_PC_ALLOWANCE_ROWS: tuple[tuple[str, str], ...] = (
    ("22", "Owner/strata direct relocation and access allowance"),
)
_REMEDIATION_CONTINGENCY_CODE = "23"

_INDUSTRIAL_PROCESS_CONSULTANT_ROWS: tuple[tuple[str, str], ...] = (
    ("5", "Architect, project manager and quantity surveyor"),
    ("6", "Survey, geotechnical, civil and structural engineers"),
    ("7", "Process, mechanical, electrical and hydraulic engineers"),
    ("8", "Fire engineer, dangerous-goods and hazardous-area specialists"),
    ("9", "Planning, environmental, traffic and certifier"),
    ("10", "Controls, commissioning and operational-readiness specialists"),
)
_INDUSTRIAL_PROCESS_CONSTRUCTION_ROWS: tuple[tuple[str, str], ...] = (
    ("11", "Preliminaries, logistics and temporary works"),
    ("12", "Earthworks, civil works and utility infrastructure"),
    ("13", "Substructure, slabs and equipment foundations"),
    ("14", "Structural frame, envelope and roofing"),
    ("15", "Internal fitout and controlled operational areas"),
    ("16", "Process plant and production equipment â€” allocation gap"),
    ("17", "Process piping, gases and specialist utilities"),
    ("18", "Mechanical and ventilation systems"),
    ("19", "Electrical distribution, generation and controls"),
    ("20", "Hydraulic, trade-waste and fire services"),
    ("21", "External works, loading, storage and security"),
    ("22", "Integrated testing, commissioning and operational readiness"),
)
_INDUSTRIAL_PROCESS_CONTINGENCY_CODE = "23"

_COLD_CHAIN_CONSTRUCTION_ROWS: tuple[tuple[str, str], ...] = (
    ("11", "Preliminaries, logistics and temporary works"),
    ("12", "Earthworks, civil works and utility infrastructure"),
    ("13", "Substructure, insulated slabs and vapour barriers"),
    ("14", "Structural frame, insulated envelope and roofing"),
    ("15", "Temperature-controlled rooms, doors and docks"),
    ("16", "Refrigeration plant and distribution"),
    ("17", "Electrical distribution, generation and controls"),
    ("18", "Hydraulic, trade-waste and fire services"),
    ("19", "Food-safety/process fitout â€” allocation gap"),
    ("20", "External works, yards, loading and security"),
    ("21", "Integrated testing, commissioning and temperature validation"),
)
_COLD_CHAIN_CONTINGENCY_CODE = "22"

_DATA_CENTRE_CONSULTANT_ROWS: tuple[tuple[str, str], ...] = (
    ("5", "Architect, project manager and quantity surveyor"),
    ("6", "Survey, geotechnical, civil and structural engineers"),
    ("7", "Mission-critical mechanical and electrical engineers"),
    ("8", "Fire, security, ICT and controls consultants"),
    ("9", "Planning, environmental, acoustic and certifier"),
    ("10", "Commissioning authority and operational-readiness specialists"),
)
_DATA_CENTRE_CONSTRUCTION_ROWS: tuple[tuple[str, str], ...] = (
    ("11", "Preliminaries, logistics and temporary works"),
    ("12", "Earthworks, civil works and utility infrastructure"),
    ("13", "Substructure, slabs and structural frame"),
    ("14", "Envelope, roofing and physical-security construction"),
    ("15", "White-space, support-space and office fitout"),
    ("16", "Utility intake, substations and high-voltage distribution"),
    ("17", "Generators, UPS, energy storage and low-voltage distribution"),
    ("18", "Cooling, ventilation and heat-rejection systems"),
    ("19", "Fire detection, suppression and life-safety systems"),
    ("20", "ICT pathways, security, BMS and DCIM controls"),
    ("21", "External works, fuel systems and service yards"),
    ("22", "Integrated systems testing and staged commissioning"),
    ("23", "Client IT equipment and carrier services â€” allocation gap"),
)
_DATA_CENTRE_PC_ALLOWANCE_ROWS: tuple[tuple[str, str], ...] = (
    ("24", "Client-direct IT and network equipment allowance"),
)
_DATA_CENTRE_CONTINGENCY_CODE = "25"

_FEE_ROWS_BY_FAMILY: dict[CoverageFamily, tuple[tuple[str, str], ...]] = {
    "residential_class1_new": _RESIDENTIAL_FEE_ROWS,
    "residential_class1_refurb": _RESIDENTIAL_FEE_ROWS,
    "multi_residential": _MULTI_RESIDENTIAL_FEE_ROWS,
    "commercial_fitout": _COMMERCIAL_FITOUT_FEE_ROWS,
    "commercial_base_building": _COMMERCIAL_BASE_FEE_ROWS,
    "building_remediation": _REMEDIATION_FEE_ROWS,
    "industrial_warehouse": _INDUSTRIAL_FEE_ROWS,
    "industrial_process": _INDUSTRIAL_FEE_ROWS,
    "industrial_cold_chain": _INDUSTRIAL_FEE_ROWS,
    "data_centre": _INDUSTRIAL_FEE_ROWS,
}
_CONSULTANT_ROWS_BY_FAMILY: dict[CoverageFamily, tuple[tuple[str, str], ...]] = {
    "residential_class1_new": _RESIDENTIAL_CONSULTANT_ROWS,
    "residential_class1_refurb": _RESIDENTIAL_CONSULTANT_ROWS,
    "multi_residential": _MULTI_RESIDENTIAL_CONSULTANT_ROWS,
    "commercial_fitout": _COMMERCIAL_FITOUT_CONSULTANT_ROWS,
    "commercial_base_building": _COMMERCIAL_BASE_CONSULTANT_ROWS,
    "building_remediation": _REMEDIATION_CONSULTANT_ROWS,
    "industrial_warehouse": _INDUSTRIAL_CONSULTANT_ROWS,
    "industrial_process": _INDUSTRIAL_PROCESS_CONSULTANT_ROWS,
    "industrial_cold_chain": _INDUSTRIAL_PROCESS_CONSULTANT_ROWS,
    "data_centre": _DATA_CENTRE_CONSULTANT_ROWS,
}
_CONSTRUCTION_ROWS_BY_FAMILY: dict[CoverageFamily, tuple[tuple[str, str], ...]] = {
    "residential_class1_new": _RESIDENTIAL_CONSTRUCTION_ROWS,
    "residential_class1_refurb": _RESIDENTIAL_REFURB_CONSTRUCTION_ROWS,
    "multi_residential": _MULTI_RESIDENTIAL_CONSTRUCTION_ROWS,
    "commercial_fitout": _COMMERCIAL_FITOUT_CONSTRUCTION_ROWS,
    "commercial_base_building": _COMMERCIAL_BASE_CONSTRUCTION_ROWS,
    "building_remediation": _REMEDIATION_CONSTRUCTION_ROWS,
    "industrial_warehouse": _INDUSTRIAL_CONSTRUCTION_ROWS,
    "industrial_process": _INDUSTRIAL_PROCESS_CONSTRUCTION_ROWS,
    "industrial_cold_chain": _COLD_CHAIN_CONSTRUCTION_ROWS,
    "data_centre": _DATA_CENTRE_CONSTRUCTION_ROWS,
}
# Only residential has a benchmark % split; other families are TBC-only.
_CONSTRUCTION_BENCHMARK_PCT_BY_FAMILY: dict[CoverageFamily, tuple[tuple[str, int], ...] | None] = {
    "residential_class1_new": _RESIDENTIAL_CONSTRUCTION_BENCHMARK_PCT,
    "residential_class1_refurb": None,
    "multi_residential": None,
    "commercial_fitout": None,
    "commercial_base_building": None,
    "building_remediation": None,
    "industrial_warehouse": None,
    "industrial_process": None,
    "industrial_cold_chain": None,
    "data_centre": None,
}
_PC_ALLOWANCE_ROWS_BY_FAMILY: dict[CoverageFamily, tuple[tuple[str, str], ...]] = {
    "residential_class1_new": _RESIDENTIAL_PC_ALLOWANCE_ROWS,
    "residential_class1_refurb": _RESIDENTIAL_PC_ALLOWANCE_ROWS,
    "multi_residential": _MULTI_RESIDENTIAL_PC_ALLOWANCE_ROWS,
    "commercial_fitout": _COMMERCIAL_FITOUT_PC_ALLOWANCE_ROWS,
    "commercial_base_building": _COMMERCIAL_BASE_PC_ALLOWANCE_ROWS,
    "building_remediation": _REMEDIATION_PC_ALLOWANCE_ROWS,
    "industrial_warehouse": _INDUSTRIAL_PC_ALLOWANCE_ROWS,
    "industrial_process": (),
    "industrial_cold_chain": (),
    "data_centre": _DATA_CENTRE_PC_ALLOWANCE_ROWS,
}
_CONTINGENCY_CODE_BY_FAMILY: dict[CoverageFamily, str] = {
    "residential_class1_new": _RESIDENTIAL_CONTINGENCY_CODE,
    "residential_class1_refurb": _RESIDENTIAL_CONTINGENCY_CODE,
    "multi_residential": _MULTI_RESIDENTIAL_CONTINGENCY_CODE,
    "commercial_fitout": _COMMERCIAL_FITOUT_CONTINGENCY_CODE,
    "commercial_base_building": _COMMERCIAL_BASE_CONTINGENCY_CODE,
    "building_remediation": _REMEDIATION_CONTINGENCY_CODE,
    "industrial_warehouse": _INDUSTRIAL_CONTINGENCY_CODE,
    "industrial_process": _INDUSTRIAL_PROCESS_CONTINGENCY_CODE,
    "industrial_cold_chain": _COLD_CHAIN_CONTINGENCY_CODE,
    "data_centre": _DATA_CENTRE_CONTINGENCY_CODE,
}


def _coverage_family(project: Project) -> CoverageFamily:
    """Resolve the same exact taxonomy family used by workflow capability gating."""
    taxonomy = effective_taxonomy(project)
    coverage = resolve_cost_plan_coverage(
        building_class=taxonomy.building_class,
        work_type=taxonomy.work_type,
        subclasses=taxonomy.subclasses,
        work_scopes=effective_work_scopes(project),
    )
    if coverage is None:
        raise ValueError(
            "Project taxonomy is outside the supported Cost Plan coverage matrix."
        )
    return coverage.family


def _money(raw: str | None) -> str:
    if not raw:
        return "TBC"
    cleaned = raw.replace("$", "").replace(",", "").strip()
    if cleaned.isdigit():
        return f"${int(cleaned):,}"
    return raw if raw.startswith("$") else f"${raw}"


def _parse_amount(raw: str | None) -> int | None:
    if not raw:
        return None
    cleaned = raw.replace("$", "").replace(",", "").strip()
    return int(cleaned) if cleaned.isdigit() else None


def _appointee_label(pack: CostPlanEvidencePack) -> str:
    return pack.mobilisation.appointee or "Architect-PM"


@dataclass(frozen=True, slots=True)
class CostPlanLine:
    cost_code: str
    category: str
    cost_item: str
    budget: float | None
    approved_contract: float | None
    status: str
    basis: str
    basis_key: int = 0


@dataclass(frozen=True, slots=True)
class BasisKeyEntry:
    number: int
    status: str
    basis: str


@dataclass(frozen=True, slots=True)
class CostPlanLineSet:
    lines: tuple[CostPlanLine, ...]
    basis_key: tuple[BasisKeyEntry, ...]


def _budget_amount(raw: str | None) -> float | None:
    amount = _parse_amount(raw)
    return None if amount is None else float(amount)


def _build_rows(project: Project, pack: CostPlanEvidencePack) -> list[CostPlanLine]:
    family = _coverage_family(project)
    is_commercial_fitout = family == "commercial_fitout"
    is_structure_only = coverage_spec(family).structure_only
    fee_rows = _FEE_ROWS_BY_FAMILY[family]
    consultant_rows = _CONSULTANT_ROWS_BY_FAMILY[family]
    construction_rows = _CONSTRUCTION_ROWS_BY_FAMILY[family]
    benchmark_pct = _CONSTRUCTION_BENCHMARK_PCT_BY_FAMILY[family]
    pc_allowance_rows = _PC_ALLOWANCE_ROWS_BY_FAMILY[family]
    contingency_code = _CONTINGENCY_CODE_BY_FAMILY[family]

    mob = pack.mobilisation
    rows = [
        CostPlanLine(
            cost_code="1",
            category="Fees and charges",
            cost_item=f"{_appointee_label(pack)} architect / PM fee",
            budget=_budget_amount(mob.fee_total_ex_gst),
            approved_contract=None,
            status="Approved",
            basis="Engagement letter",
        )
    ]
    for code, label in fee_rows:
        rows.append(
            CostPlanLine(
                cost_code=code,
                category="Fees and charges",
                cost_item=label,
                budget=None,
                approved_contract=None,
                status="Assumption",
                basis="Benchmark",
            )
        )
    for code, label in consultant_rows:
        if label == "Principal certifier" and not pack_has_gap(pack.mobilisation, GAP_CERTIFIER):
            name = pack.certifier_name or "appointed"
            rows.append(
                CostPlanLine(
                    cost_code=code,
                    category="Consultants",
                    cost_item=label,
                    budget=_budget_amount(pack.certifier_fee_ex_gst),
                    approved_contract=None,
                    status="Grounded",
                    basis=f"Appointed ({name}); owner-direct fee",
                )
            )
            continue
        rows.append(
            CostPlanLine(
                cost_code=code,
                category="Consultants",
                cost_item=label,
                budget=None,
                approved_contract=None,
                status="Assumption",
                basis="Not yet appointed",
            )
        )
    ceiling = _parse_amount(pack.construction_budget_ceiling)
    if benchmark_pct is not None and ceiling is not None:
        pct_by_label = dict(benchmark_pct)
        running = 0
        last_index = len(construction_rows) - 1
        for index, (code, label) in enumerate(construction_rows):
            if index == last_index:
                amount = ceiling - running
            else:
                amount = round(ceiling * pct_by_label[label] / 100)
                running += amount
            rows.append(
                CostPlanLine(
                    cost_code=code,
                    category="Construction",
                    cost_item=label,
                    budget=float(amount),
                    approved_contract=None,
                    status="Assumption",
                    basis="Benchmark % of ceiling",
                )
            )
    else:
        # Structure-only families have no benchmark percentage split, so every row
        # stays a lump-sum TBC even when a construction ceiling is evidenced.
        construction_basis = (
            "Structure only — no rate pack; pending head-builder tender"
            if is_structure_only
            else "Pending head-builder tender"
        )
        for code, label in construction_rows:
            rows.append(
                CostPlanLine(
                    cost_code=code,
                    category="Construction",
                    cost_item=label,
                    budget=None,
                    approved_contract=None,
                    status="Assumption",
                    basis=construction_basis,
                )
            )
    allowance_category = (
        "Client-direct and landlord works"
        if is_commercial_fitout
        else "PC allowances"
    )
    allowance_basis = (
        "Allocation and procurement pending"
        if is_commercial_fitout
        else "Selection pending — contract PC schedule"
    )
    for code, label in pc_allowance_rows:
        rows.append(
            CostPlanLine(
                cost_code=code,
                category=allowance_category,
                cost_item=label,
                budget=None,
                approved_contract=None,
                status="Assumption",
                basis=allowance_basis,
            )
        )
    pct = pack.contingency_percent or "5–10"
    rows.append(
        CostPlanLine(
            cost_code=contingency_code,
            category="Contingency / allowances",
            cost_item="Owner-held contingency",
            budget=_budget_amount(pack.contingency_amount),
            approved_contract=None,
            status="Evidenced" if pack.contingency_amount else "Assumption",
            basis=(
                f"{pct}% owner-held (owner brief)"
                if pack.contingency_amount
                else f"{pct}% construction (benchmark)"
            ),
        )
    )
    return _overlay_received_proposal_rows(rows, pack)


def _overlay_received_proposal_rows(
    rows: list[CostPlanLine], pack: CostPlanEvidencePack
) -> list[CostPlanLine]:
    """Replace scaffold allowances with reconciled, still-uncommitted proposal values."""
    if not pack.reconciled_items:
        return rows

    by_code = {row.cost_code: row for row in rows}
    for item in pack.reconciled_items:
        if item.budget is None:
            continue
        by_code[item.cost_code] = CostPlanLine(
            cost_code=item.cost_code,
            category=item.category,
            cost_item=item.item,
            budget=float(item.budget),
            approved_contract=None,
            status="Proposed",
            basis=item.basis,
        )

    def sort_key(row: CostPlanLine) -> tuple[int, str]:
        first = row.cost_code.split(".", 1)[0]
        return (int(first) if first.isdigit() else 999, row.cost_code.lower())

    return sorted(by_code.values(), key=sort_key)


def _assign_basis_keys(
    rows: list[CostPlanLine],
) -> tuple[tuple[CostPlanLine, ...], tuple[BasisKeyEntry, ...]]:
    """Number each distinct (status, basis) pair in first-appearance order."""
    numbers: dict[tuple[str, str], int] = {}
    entries: list[BasisKeyEntry] = []
    keyed: list[CostPlanLine] = []
    for row in rows:
        pair = (row.status, row.basis)
        number = numbers.get(pair)
        if number is None:
            number = len(numbers) + 1
            numbers[pair] = number
            entries.append(BasisKeyEntry(number=number, status=row.status, basis=row.basis))
        keyed.append(replace(row, basis_key=number))
    return tuple(keyed), tuple(entries)


def cost_plan_lines(project: Project, pack: CostPlanEvidencePack) -> CostPlanLineSet:
    """Return every cost line for the project's coverage family, priced or not."""
    rows = _build_rows(project, pack)
    lines, basis_key = _assign_basis_keys(rows)
    return CostPlanLineSet(lines=lines, basis_key=basis_key)
