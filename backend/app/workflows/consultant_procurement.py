from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.draft_artifact import DraftArtifact
from app.database.draft_artifacts import (
    create_draft_artifact,
    get_latest_draft_artifact,
    next_draft_version,
)
from app.database.project import Project
from app.database.workspace_files import upsert_workspace_file
from app.inbox.paths import build_storage_key
from app.projects.artefact_context import (
    ProcurementArtefactContext,
    RfpContext,
    build_rfp_context,
)
from app.projects.generation_context import ProjectGenerationContext
from app.projects.generation_brief import ArtefactGenerationBrief
from app.storage.project_files import upload_project_file
from ingest.hashing import bytes_content_hash
from app.retrieval.retriever import DocumentRetriever
from app.sitewise.artifact_presentation import clean_issue_language
from app.sitewise.cost_plan_consultant_forecast import (
    FORECAST_BASIS,
    FORECAST_STATUS,
    forecast_consultant_fees_for_markdown,
)
from app.sitewise.pmp_citations import CitationIndex
from app.sitewise.rfp_evidence_validation import validate_rfp_output
from app.sitewise.rfp_renderer import (
    BACKGROUND_PLACEHOLDER,
    PROGRAMME_PLACEHOLDER,
    REQUESTED_SERVICES_PLACEHOLDER,
    build_rfp_citation_index,
    render_rfp_scaffold,
)
from app.projects.identity import resolve_project_identity
from app.workflows.create_cost_plan import (
    WORKFLOW_TYPE as CREATE_COST_PLAN_WORKFLOW_TYPE,
)
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.procurement_request import (
    EvidenceQuery,
    ProgressPublisher,
    ProcurementDocument,
    ProcurementTarget,
    draft_procurement_request,
    publish_procurement_progress,
)
from app.workflows.procurement_register import load_procurement_document_register
from app.workflows.rfp_narrative import RfpNarrativeOutput, run_rfp_narrative_model

WORKFLOW_TYPE_PREFIX = "consultant_procurement"
RUNTIME_NAME = "clerk-consultant-procurement"
# Knowledge-catalog workflow key: seeds opt in via `required_by: {consultant-procurement: N}`.
KNOWLEDGE_WORKFLOW = "consultant-procurement"
RFP_NARRATIVE_MAX_ATTEMPTS = 3


@dataclass(frozen=True, slots=True)
class DisciplineProfile:
    discipline_code: str | None
    name: str
    slug: str
    benchmark_terms: tuple[str, ...]
    requested_services: tuple[str, ...]
    deliverables: tuple[str, ...]
    knowledge_paths: tuple[str, ...]
    knowledge_query_terms: tuple[str, ...]
    evidence_query_terms: tuple[str, ...]
    fee_stages: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ConsultantProcurementResult:
    draft: DraftArtifact
    discipline: str
    source_trace: dict[str, Any]


def _normalise_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "consultant"


def _profile(
    name: str,
    *,
    discipline_code: str | None = None,
    slug: str | None = None,
    benchmark_terms: tuple[str, ...] = (),
    requested_services: tuple[str, ...],
    deliverables: tuple[str, ...],
    knowledge_paths: tuple[str, ...] = (),
    knowledge_query_terms: tuple[str, ...] = (),
    evidence_query_terms: tuple[str, ...] = (),
    fee_stages: tuple[tuple[str, str], ...] = (),
) -> DisciplineProfile:
    return DisciplineProfile(
        discipline_code=discipline_code,
        name=name,
        slug=_slugify(slug or name),
        benchmark_terms=benchmark_terms,
        requested_services=requested_services,
        deliverables=deliverables,
        knowledge_paths=knowledge_paths,
        knowledge_query_terms=knowledge_query_terms,
        evidence_query_terms=evidence_query_terms,
        fee_stages=fee_stages,
    )


DISCIPLINE_PROFILES: dict[str, DisciplineProfile] = {
    _normalise_key("architect"): _profile(
        "Architect",
        discipline_code="consultant.architect",
        requested_services=(
            "Review the project brief, planning pathway, design status, and client objectives.",
            "Define architectural design scope, consultant coordination role, and approval support.",
            "Identify design documentation, tender support, and construction-stage services required.",
        ),
        deliverables=(
            "Fee proposal with staged architectural services and exclusions.",
            "Scope schedule by phase, including coordination and authority support.",
            "Key assumptions, information required from the client, and programme dependencies.",
        ),
    ),
    _normalise_key("structural engineer"): _profile(
        "Structural engineer",
        discipline_code="consultant.structural",
        benchmark_terms=("structural",),
        knowledge_paths=("seed/as-standards-reference.md",),
        knowledge_query_terms=(
            "structural engineer",
            "structural design",
            "footings",
            "framing",
            "retention",
            "temporary works",
            "AS 1170",
            "AS 3600",
        ),
        requested_services=(
            "Review the project brief, architectural drawings, survey, available geotechnical advice, existing-structure information, and site constraints; identify missing investigations or design inputs.",
            "Prepare the structural design basis and advise on framing, stability, footing, slab, retained-structure, demolition, temporary-support, and new-to-existing interface requirements applicable to the project.",
            "Provide coordinated structural design, calculations, drawings, details, specifications, schedules, and certification inputs for the agreed design and approval stages.",
            "Coordinate structural grids, levels, openings, penetrations, loads, movements, tolerances, buildability, and design responsibilities with the architect and relevant consultants.",
            "Support procurement through tender queries, scope clarifications, addenda, and review of structural alternatives or contractor proposals where included.",
            "Define construction-phase allowances for RFIs, shop drawings and technical submittals, site inspections, defects, completion statements, and close-out advice.",
            "State exclusions and responsibility boundaries for geotechnical design, surveying, temporary works, shop detailing, proprietary systems, demolition methodology, waterproofing, bushfire/fire advice, and contractor design.",
        ),
        deliverables=(
            "Structural fee proposal with design, documentation, certification, and site-phase allowances.",
            "List of required inputs, exclusions, and assumptions.",
            "Hourly rates for variations, meetings, inspections, and additional design work.",
        ),
    ),
    _normalise_key("hydraulic engineer"): _profile(
        "Hydraulic engineer",
        discipline_code="consultant.hydraulic",
        benchmark_terms=("hydraulic", "wastewater"),
        knowledge_paths=("seed/hydraulic-services-guide.md",),
        knowledge_query_terms=(
            "hydraulic services",
            "potable water",
            "sanitary drainage",
            "hot water",
            "trade waste",
            "landlord interfaces",
            "testing",
            "commissioning",
        ),
        evidence_query_terms=(
            "hydraulic plumbing sanitary drainage water hot water fixtures kitchenette amenities",
            "existing services riser stack capacity connection metering isolation landlord shutdown",
            "trade waste gas stormwater fire water penetrations waterproofing commissioning",
        ),
        requested_services=(
            "Review the brief, layouts, existing-services records, landlord information, approval pathway, and affected hydraulic systems; identify missing investigations before accepting the design basis.",
            "Define potable water, sanitary drainage, hot-water, fixture, metering, isolation, connection, capacity, access, shutdown, and tenant/landlord requirements applicable to the evidenced scope.",
            "Treat stormwater, trade waste, gas, fire-water, and whole-building infrastructure as conditional scope, and state their inclusion, exclusion, or coordination boundary explicitly.",
            "Coordinate hydraulic layouts, equipment, risers, ceiling zones, penetrations, fire stopping, waterproofing, structure, fire, mechanical, electrical, civil, and architectural interfaces.",
            "Define approval, landlord-review, authority, certification, inspection, tender, construction-support, testing, commissioning, and handover responsibilities by project stage.",
            "State design responsibility boundaries, required client inputs, assumptions, exclusions, optional services, programme, meetings, site visits, fee stages, rates, and disbursements.",
        ),
        deliverables=(
            "Existing-services due-diligence and hydraulic design-basis report identifying affected systems, investigations, capacity assumptions, criteria, interfaces, and unresolved decisions.",
            "Responsibility schedule separating tenant, landlord, base-building, fire-services, civil, contractor-designed, authority, and client-direct scope.",
            "Calculations, coordinated drawings, schematics, details, specifications, fixture/equipment schedules, penetration information, and certification inputs appropriate to each agreed stage.",
            "Landlord, certifier, and authority submission material, responses, inspections, declarations, and completion records applicable to the confirmed pathway.",
            "Tender and construction support including tender queries, addenda, RFIs, submittal/shop-drawing reviews, site inspections, defects, and revision registers.",
            "Testing and commissioning requirements, witness records, as-built and O&M review, training, handover inputs, and outstanding-items schedule.",
            "Fee breakdown by stage with personnel, meetings, investigations, site visits, disbursements, hourly rates, programme, exclusions, optional services, and required client inputs.",
        ),
    ),
    _normalise_key("electrical services engineer"): _profile(
        "Electrical Services Engineer",
        discipline_code="consultant.electrical",
        slug="electrical_engineer",
        benchmark_terms=("electrical", "lighting", "power"),
        knowledge_paths=("seed/electrical-services-guide.md",),
        knowledge_query_terms=(
            "electrical services",
            "utility supply",
            "distribution",
            "lighting",
            "emergency power",
            "metering",
            "controls",
            "commissioning",
        ),
        evidence_query_terms=(
            "electrical power supply switchboard distribution lighting metering",
            "existing services capacity utility landlord riser generator UPS",
            "emergency lighting controls security ICT fire interfaces commissioning",
        ),
        requested_services=(
            "Review the brief, available electrical records, utility and landlord information, approval pathway, and the affected electrical systems.",
            "Establish supply, demand, distribution, lighting, emergency-power, metering, controls and resilience design criteria appropriate to the confirmed project scope.",
            "Coordinate spatial, structural, fire, mechanical, hydraulic, ICT, security, controls, utility, shutdown and builder's-work interfaces.",
            "Define staged design, approval, tender, construction support, testing, commissioning, certification and handover services, including optional and excluded scope.",
        ),
        deliverables=(
            "Electrical design-basis and existing-services due-diligence report with unresolved capacity and interface decisions.",
            "Coordinated calculations, drawings, schematics, specifications, schedules and builder's-work requirements appropriate to each stage.",
            "Utility, landlord, certifier and authority submission inputs, tender and construction support, inspection and defect allowances.",
            "Testing, commissioning, witness, training, O&M, as-built and completion evidence requirements.",
            "Fee breakdown by stage with assumptions, exclusions, optional services, meetings, site visits, disbursements and variation rates.",
        ),
    ),
    _normalise_key("mechanical services engineer"): _profile(
        "Mechanical Services Engineer",
        discipline_code="consultant.mechanical",
        slug="mechanical_engineer",
        benchmark_terms=("mechanical", "hvac", "mechanical services"),
        knowledge_paths=("seed/mechanical-services-guide.md",),
        knowledge_query_terms=(
            "mechanical services",
            "HVAC",
            "ventilation",
            "exhaust",
            "controls",
            "commissioning",
        ),
        evidence_query_terms=(
            "mechanical HVAC ventilation exhaust air conditioning design criteria",
            "car park ventilation smoke control fire mode acoustic plant condenser",
            "BASIX NatHERS Section J controls commissioning regulated design",
        ),
        requested_services=(
            "Review the project brief, project profile, architectural design, approval pathway, and available fire, acoustic, energy, electrical, hydraulic, and structural information.",
            "Establish the mechanical design basis, system options, zoning, performance criteria, spatial allowances, maintainability requirements, and design-stage programme.",
            "Design heating, cooling, outdoor-air, transfer-air, and local-exhaust systems applicable to dwellings, common areas, car parking, plant rooms, and any commercial or specialist spaces.",
            "Coordinate plant locations, risers, ducts, louvres, penetrations, access zones, condensate, power, controls, fire and smoke modes, acoustics, facade interfaces, and builders' work.",
            "Address applicable energy-efficiency, ventilation, indoor-air-quality, acoustic, fire-safety, authority, and regulated-design requirements, identifying any performance solutions or specialist inputs.",
            "Provide staged design and documentation for concept, planning, detailed design, approval, tender, construction, commissioning, and handover as required by the agreed appointment.",
            "Allow for design meetings, coordination reviews, tender queries, construction RFIs, shop-drawing and technical-submittal review, inspections, witness testing, defects, and close-out.",
            "Define assumptions, exclusions, optional services, client-supplied information, design responsibility, certification responsibility, programme dependencies, and variation rates.",
        ),
        deliverables=(
            "Staged fee proposal and responsibility schedule covering design, documentation, approval, procurement, construction, commissioning, and handover services.",
            "Mechanical design-basis report recording systems, design criteria, assumptions, applicable requirements, interfaces, and unresolved decisions.",
            "Calculations and assessments appropriate to the agreed scope, including loads, ventilation, pressure relationships, equipment duties, energy, controls, and acoustic inputs.",
            "Coordinated drawings, schematics, details, specifications, equipment and controls schedules, penetration and builders'-work requirements, and tender/construction issue registers.",
            "Compliance matrix, regulated-design and professional-engineering deliverables where applicable, certification inputs, and a schedule of required third-party advice.",
            "Design-review, coordination, tender-query, RFI, shop-drawing, technical-submittal, inspection, and defect-response allowances.",
            "Commissioning plan and records, testing and balancing requirements, functional performance verification, training, O&M, warranties, and as-built review where included.",
            "Fee breakdown by stage with personnel, meetings, site visits, disbursements, hourly rates, programme, exclusions, optional services, and required client inputs.",
        ),
    ),
    _normalise_key("geotechnical engineer"): _profile(
        "Geotechnical engineer",
        discipline_code="consultant.geotechnical",
        benchmark_terms=("geotechnical", "geotech"),
        requested_services=(
            "Review project location, site constraints, proposed works, and available design information.",
            "Price site investigation, boreholes or test pits, soil classification, and foundation advice.",
            "Identify reporting, contamination observations, and construction-phase support assumptions.",
        ),
        deliverables=(
            "Geotechnical investigation and report fee proposal.",
            "Investigation methodology, access requirements, programme, and exclusions.",
            "Schedule of rates for additional testing or site attendance.",
        ),
    ),
    _normalise_key("surveyor"): _profile(
        "Surveyor",
        discipline_code="consultant.surveyor",
        benchmark_terms=("surveyor", "survey"),
        requested_services=(
            "Review site address, title/boundary information, planning pathway, and design requirements.",
            "Price detail, level, boundary, identification, set-out, or as-built survey services as required.",
            "Nominate site access, title search, control mark, and council information assumptions.",
        ),
        deliverables=(
            "Survey fee proposal with survey type, inclusions, exclusions, and deliverable format.",
            "Programme for fieldwork and issue of survey files.",
            "Disbursements, title/council search costs, and hourly rates for additional attendance.",
        ),
    ),
    _normalise_key("BASIX / energy assessor"): _profile(
        "BASIX / energy assessor",
        discipline_code="consultant.basix",
        benchmark_terms=("basix", "energy", "nathers"),
        knowledge_paths=("seed/sustainability-energy-guide.md",),
        requested_services=(
            "Review the project brief, plans, building fabric assumptions, and planning approval pathway.",
            "Price BASIX, NatHERS, energy modelling, sustainability advice, and certificate updates as required.",
            "Coordinate assumptions with architectural documentation and authority lodgement requirements.",
        ),
        deliverables=(
            "BASIX / energy assessment fee proposal with certificate and update allowances.",
            "List of modelling assumptions and inputs required from the design team.",
            "Exclusions, lodgement assumptions, and hourly rates for revisions.",
        ),
    ),
    _normalise_key("certifier"): _profile(
        "Certifier",
        discipline_code="consultant.certifier",
        benchmark_terms=("certifier", "principal certifier", "pca"),
        knowledge_paths=("seed/setup-and-commission-guide.md",),
        knowledge_query_terms=(
            "principal certifier",
            "PCA",
            "certifying authority",
            "construction certificate",
            "occupation certificate",
            "critical stage inspections",
            "statutory notifications",
            "consultant procurement",
        ),
        evidence_query_terms=(
            "development consent DA CDC CC conditions of consent BASIX",
            "fire safety schedule principal certifier appointment",
            "critical stage inspection occupation certificate",
        ),
        requested_services=(
            "Confirm the applicable planning/building approval pathway, current approval status, and principal certifier appointment requirements; state pathway assumptions where records are incomplete.",
            "Review design status, performance solutions and required certification evidence before construction approval.",
            "Provide construction approval support, including document review, approval issue, statutory notices and authority liaison; separately identify statutory and authority fees.",
            "Develop and administer the statutory inspection regime, including hold points, notices, records, non-conformance escalation and completion evidence.",
            "Coordinate certification interfaces with the design team and contractor, and identify consultant certificates, producer statements and evidence excluded from the certifier appointment.",
            "Provide occupation-stage certification services, including completion evidence review, inspection close-out, conditions-of-consent compliance and occupation certificate inputs.",
            "State inclusions, exclusions, inspection allowances, disbursements, authority fees, client-side obligations, third-party certificate reliance, response times and variation rates.",
        ),
        deliverables=(
            "Certification fee proposal with statutory role, inspections, and approval deliverables.",
            "Schedule of required certificates, documents, and owner/consultant inputs.",
            "Exclusions, statutory fees, disbursements, and additional hourly rates.",
        ),
        fee_stages=(
            (
                "Information review and pathway confirmation",
                "Inputs review, appointment advice and approval-pathway confirmation",
            ),
            (
                "Construction approval support",
                "CC/CDC or equivalent document review, approval issue and authority liaison",
            ),
            (
                "Statutory notifications and appointment administration",
                "Owner appointment notices, commencement notices and register administration",
            ),
            (
                "Critical-stage inspection regime",
                "Mandatory inspections, records and hold-point administration",
            ),
            (
                "Re-inspection / non-conformance allowances",
                "Separate allowance or rates for failed inspections and rework verification",
            ),
            (
                "Occupation certificate / completion",
                "Completion evidence review, OC inputs and close-out deliverables",
            ),
            (
                "Optional / additional services",
                "Separately identify scope, rates and trigger",
            ),
            (
                "Hourly rates / disbursements / authority fees",
                "Pass-through authority fees and estimated expenses identified separately",
            ),
        ),
    ),
    _normalise_key("town planner"): _profile(
        "Town planner",
        discipline_code="consultant.town_planner",
        benchmark_terms=("town planning", "planning"),
        requested_services=(
            "Review the project brief, site constraints, zoning (LEP/DCP), and proposed works.",
            "Advise on permitted use, FSR, height, setbacks, and any merit-based variations required.",
            "State the planning pathway (CDC/DA) and any State-level (SEPP) referral requirements.",
        ),
        deliverables=(
            "Planning report / statement of environmental effects fee proposal.",
            "Assumptions on council pre-lodgement meetings and authority response timeframes.",
            "Hourly rates for RFIs, design changes, and section 4.55 modifications.",
        ),
    ),
    _normalise_key("heritage consultant"): _profile(
        "Heritage consultant",
        discipline_code="consultant.heritage",
        benchmark_terms=("heritage",),
        requested_services=(
            "Review heritage listing / conservation area status, existing fabric, and proposed works.",
            "Advise on heritage impact, sympathetic design responses, and the applicable approval pathway.",
            "Coordinate documentation with the design team and identify authority consultation needs.",
        ),
        deliverables=(
            "Heritage impact statement fee proposal.",
            "Assumptions on site access, archival recording, and photographic survey scope.",
            "Hourly rates for additional advice or authority responses.",
        ),
    ),
    _normalise_key("fire engineer"): _profile(
        "Fire engineer",
        discipline_code="consultant.fire_engineer",
        benchmark_terms=("fire engineering", "fire safety"),
        knowledge_paths=("seed/fire-life-safety-guide.md",),
        requested_services=(
            "Review the project brief, building classification, proposed works, and fire-safety constraints.",
            "Establish the fire and life-safety design basis, existing-system constraints, egress strategy, passive and active measures, smoke-control interfaces, and approval pathway.",
            "Define any performance-solution process, stakeholder consultation, analysis, peer review, authority and certifier inputs without assuming that a performance solution is required.",
            "Coordinate architecture, structure, facade, mechanical, electrical, hydraulic, controls, access, security, vertical-transport and builder's-work interfaces.",
            "Price staged design, documentation, tender support, construction verification, integrated testing, certification inputs and handover services separately.",
        ),
        deliverables=(
            "Fire and life-safety design-basis, compliance strategy and responsibility matrix.",
            "Reports, drawings, schedules, specifications, cause-and-effect inputs and certification deliverables appropriate to the agreed pathway.",
            "Design reviews, tender responses, submittal reviews, inspections, passive-fire evidence and integrated-testing requirements.",
            "Handover evidence schedule covering test records, defects, declarations, O&M, training and essential-safety-measure inputs.",
            "Fee breakdown by stage with assumptions, exclusions, options, meetings, site visits, authority engagement and variation rates.",
        ),
    ),
    _normalise_key("sustainability consultant"): _profile(
        "Sustainability Consultant",
        discipline_code="consultant.esd",
        benchmark_terms=("sustainability", "energy", "section j"),
        knowledge_paths=("seed/non-residential-sustainability-energy-guide.md",),
        knowledge_query_terms=(
            "non-residential sustainability",
            "energy efficiency",
            "Section J",
            "NABERS",
            "Green Star",
            "embodied carbon",
            "commissioning",
        ),
        evidence_query_terms=(
            "sustainability targets energy compliance Section J NABERS Green Star",
            "operational energy embodied carbon metering commissioning tuning",
            "planning conditions client brief landlord requirements reporting",
        ),
        requested_services=(
            "Review the client brief, planning conditions, building classification, design status and any rating or reporting commitments.",
            "Define the applicable compliance, operational-energy, embodied-carbon, rating, metering, commissioning and evidence pathways without assuming a target not stated in project evidence.",
            "Coordinate performance criteria and required inputs across architecture, facade, mechanical, electrical, hydraulic, fire, controls and cost planning.",
            "Price design-stage modelling, submissions, procurement support, construction reviews, commissioning verification, handover and post-occupancy services separately.",
        ),
        deliverables=(
            "Sustainability design-basis, commitments register and evidence matrix.",
            "Compliance and modelling reports, specifications, schedules and submission inputs appropriate to the agreed pathway.",
            "Design reviews, procurement clauses, submittal reviews, site verification and commissioning/tuning requirements.",
            "Fee breakdown by stage with assumptions, exclusions, optional services, programme, inputs and variation rates.",
        ),
    ),
    _normalise_key("ICT / AV / security consultant"): _profile(
        "ICT / AV / Security Consultant",
        discipline_code="consultant.ict",
        slug="ict_av_security_consultant",
        benchmark_terms=("ict", "av", "security"),
        knowledge_paths=("seed/ict-av-security-guide.md",),
        knowledge_query_terms=(
            "ICT",
            "structured cabling",
            "audiovisual",
            "security",
            "access control",
            "CCTV",
            "technology commissioning",
        ),
        evidence_query_terms=(
            "ICT AV security technology brief network structured cabling",
            "access control CCTV audiovisual rooms racks pathways power cooling",
            "landlord client IT standards commissioning training handover",
        ),
        requested_services=(
            "Review the operational brief, client technology standards, existing systems, landlord interfaces and cybersecurity or privacy constraints.",
            "Define ICT, structured-cabling, AV, security, access-control, CCTV, intercom, pathways, space, power, cooling and integration scope relevant to the project.",
            "Coordinate architecture, electrical, mechanical, fire, vertical transport, furniture, signage and client-direct equipment interfaces.",
            "Define design, procurement, construction support, testing, integrated commissioning, training and handover services with responsibility boundaries.",
        ),
        deliverables=(
            "Technology design-basis and responsibility matrix separating consultant, contractor, landlord, carrier and client-IT scope.",
            "Coordinated drawings, schematics, room data, equipment schedules, specifications and procurement packages.",
            "Tender support, submittal reviews, inspections, testing scripts, integrated commissioning records and defects support.",
            "Asset, configuration, warranty, training, O&M and as-built handover requirements.",
            "Fee breakdown by stage with assumptions, exclusions, options, programme, meetings, site visits and variation rates.",
        ),
    ),
    _normalise_key("acoustic consultant"): _profile(
        "Acoustic consultant",
        discipline_code="consultant.acoustic",
        benchmark_terms=("acoustic", "noise"),
        requested_services=(
            "Review the project brief, site context, planning conditions, and proposed building fabric.",
            "Advise on acoustic assessment, noise and vibration controls, and compliance requirements.",
            "Coordinate acoustic documentation with the design team and identify authority or testing requirements.",
        ),
        deliverables=(
            "Acoustic consultancy fee proposal with assessment, report, and documentation scope.",
            "Assumptions on site measurements, testing, authority requirements, and required inputs.",
            "Hourly rates for design revisions, meetings, additional testing, and construction-stage advice.",
        ),
    ),
    _normalise_key("landscape architect"): _profile(
        "Landscape architect",
        discipline_code="consultant.landscape",
        requested_services=(
            "Review the project brief, planning controls, site constraints, and architectural design intent.",
            "Price landscape concept, approval documentation, planting, finishes, and coordination services.",
            "Identify construction documentation, tender support, and site-phase services if required.",
        ),
        deliverables=(
            "Landscape architecture fee proposal by project phase.",
            "Drawing/report deliverables, assumptions, exclusions, and required inputs.",
            "Hourly rates and optional allowances for revisions or construction support.",
        ),
    ),
    _normalise_key("arborist"): _profile(
        "Arborist",
        discipline_code="consultant.arborist",
        requested_services=(
            "Review site information, tree constraints, planning pathway, and proposed works near trees.",
            "Price arboricultural assessment, impact report, protection specification, and site advice.",
            "Identify council requirements, site access assumptions, and construction-stage inspections.",
        ),
        deliverables=(
            "Arborist fee proposal with report, tree protection, and inspection allowances.",
            "Information required, exclusions, and council/authority assumptions.",
            "Hourly rates for additional advice or site attendance.",
        ),
    ),
    _normalise_key("bushfire consultant"): _profile(
        "Bushfire consultant",
        discipline_code="consultant.bushfire",
        requested_services=(
            "Review site location, planning pathway, bushfire overlays, building use, and design documents.",
            "Price bushfire assessment, BAL advice, planning report, and design coordination.",
            "Identify authority assumptions, required inputs, and any construction-stage advice.",
        ),
        deliverables=(
            "Bushfire consultancy fee proposal with assessment/report scope.",
            "BAL assumptions, compliance pathway, exclusions, and required client information.",
            "Hourly rates for design changes, authority responses, and extra site attendance.",
        ),
    ),
    _normalise_key("traffic consultant"): _profile(
        "Traffic consultant",
        discipline_code="consultant.traffic",
        requested_services=(
            "Review project brief, site access, parking/loading needs, planning pathway, and design documents.",
            "Price traffic, parking, access, swept-path, and authority-response advice as required.",
            "Identify survey/count assumptions, transport authority interfaces, and programme constraints.",
        ),
        deliverables=(
            "Traffic consultancy fee proposal with report and drawing/input scope.",
            "Required data, authority assumptions, exclusions, and optional services.",
            "Hourly rates for design revisions, meetings, and authority responses.",
        ),
    ),
    _normalise_key("civil / stormwater engineer"): _profile(
        "Civil / stormwater engineer",
        discipline_code="consultant.civil",
        requested_services=(
            "Review site levels, planning pathway, civil interfaces, architectural documents, and authority constraints.",
            "Price civil, stormwater, drainage, driveway, erosion/sediment, and external works advice as required.",
            "Coordinate documentation, authority submissions, and construction-phase clarifications.",
        ),
        deliverables=(
            "Civil / stormwater fee proposal with design, documentation, and authority support scope.",
            "Assumptions for site data, survey, hydraulic interfaces, and exclusions.",
            "Hourly rates for revisions, RFIs, and site-phase attendance.",
        ),
    ),
}

DISCIPLINE_ALIASES: dict[str, str] = {
    _normalise_key("basix assessor"): _normalise_key("BASIX / energy assessor"),
    _normalise_key("basix"): _normalise_key("BASIX / energy assessor"),
    _normalise_key("energy assessor"): _normalise_key("BASIX / energy assessor"),
    _normalise_key("nathers assessor"): _normalise_key("BASIX / energy assessor"),
    _normalise_key("principal certifier"): _normalise_key("certifier"),
    _normalise_key("pca"): _normalise_key("certifier"),
    _normalise_key("building certifier"): _normalise_key("certifier"),
    _normalise_key("building certifier / pca"): _normalise_key("certifier"),
    _normalise_key("building certifier pca"): _normalise_key("certifier"),
    _normalise_key("principal certifying authority"): _normalise_key("certifier"),
    _normalise_key("hydraulic consultant"): _normalise_key("hydraulic engineer"),
    _normalise_key("electrical engineer"): _normalise_key(
        "electrical services engineer"
    ),
    _normalise_key("electrical consultant"): _normalise_key(
        "electrical services engineer"
    ),
    _normalise_key("services engineer electrical"): _normalise_key(
        "electrical services engineer"
    ),
    _normalise_key("mechanical engineer"): _normalise_key(
        "mechanical services engineer"
    ),
    _normalise_key("mechanical services"): _normalise_key(
        "mechanical services engineer"
    ),
    _normalise_key("mechanical consultant"): _normalise_key(
        "mechanical services engineer"
    ),
    _normalise_key("hvac engineer"): _normalise_key("mechanical services engineer"),
    _normalise_key("services engineer mechanical"): _normalise_key(
        "mechanical services engineer"
    ),
    _normalise_key("civil engineer"): _normalise_key("civil / stormwater engineer"),
    _normalise_key("stormwater engineer"): _normalise_key(
        "civil / stormwater engineer"
    ),
    _normalise_key("stormwater consultant"): _normalise_key(
        "civil / stormwater engineer"
    ),
    _normalise_key("esd"): _normalise_key("sustainability consultant"),
    _normalise_key("esd consultant"): _normalise_key("sustainability consultant"),
    _normalise_key("ecologically sustainable design consultant"): _normalise_key(
        "sustainability consultant"
    ),
    _normalise_key("ict consultant"): _normalise_key("ICT / AV / security consultant"),
    _normalise_key("av consultant"): _normalise_key("ICT / AV / security consultant"),
    _normalise_key("security consultant"): _normalise_key(
        "ICT / AV / security consultant"
    ),
    _normalise_key("town planning"): _normalise_key("town planner"),
    _normalise_key("town planning consultant"): _normalise_key("town planner"),
    _normalise_key("planning consultant"): _normalise_key("town planner"),
    _normalise_key("structural"): _normalise_key("structural engineer"),
    _normalise_key("mechanical"): _normalise_key("mechanical services engineer"),
    _normalise_key("electrical"): _normalise_key("electrical services engineer"),
    _normalise_key("hydraulic"): _normalise_key("hydraulic engineer"),
    _normalise_key("civil"): _normalise_key("civil / stormwater engineer"),
    _normalise_key("civil stormwater"): _normalise_key("civil / stormwater engineer"),
    _normalise_key("landscape"): _normalise_key("landscape architect"),
    _normalise_key("heritage"): _normalise_key("heritage consultant"),
    _normalise_key("geotechnical"): _normalise_key("geotechnical engineer"),
    _normalise_key("acoustic"): _normalise_key("acoustic consultant"),
    _normalise_key("access"): _normalise_key("access consultant"),
    _normalise_key("facade"): _normalise_key("facade consultant"),
    _normalise_key("traffic"): _normalise_key("traffic consultant"),
}

_NON_CONSULTANT_TERMS = (
    "main contractor",
    "main works",
    "head contractor",
    "principal contractor",
    "builder",
    "design and construct",
    "d and c contractor",
    "subcontractor",
    "sub contractor",
    "trade contractor",
    "trade package",
)


class NonConsultantDiscipline(ValueError):
    """Raised when a procurement target is a contractor, not a consultant."""

    def __init__(self, discipline: str) -> None:
        self.discipline = discipline
        super().__init__(
            f"{discipline!r} is a construction contractor, not a consultant "
            "discipline. Use the head-contractor procurement path (EOI/RFT), not "
            "consultant procurement, which produces a consultant Request for Tender."
        )


def consultant_procurement_workflow_type(discipline: str) -> str:
    profile = normalise_discipline(discipline)
    return f"{WORKFLOW_TYPE_PREFIX}_{profile.slug}"


def consultant_procurement_workspace_path(
    project: Project,
    *,
    discipline_slug: str,
    version: int,
) -> str:
    root = project.workspace_path.rstrip("/")
    return f"{root}/02-consultant/consultant_procurement_{discipline_slug}_v{version:02d}.draft.md"


def is_consultant_procurement_workflow(workflow_type: str) -> bool:
    return workflow_type.startswith(f"{WORKFLOW_TYPE_PREFIX}_")


def consultant_procurement_discipline_slug(workflow_type: str) -> str:
    prefix = f"{WORKFLOW_TYPE_PREFIX}_"
    if not workflow_type.startswith(prefix):
        raise ValueError(f"not a consultant procurement workflow: {workflow_type}")
    return workflow_type[len(prefix) :]


async def save_consultant_procurement_workspace_file(
    session: AsyncSession,
    *,
    project: Project,
    draft: DraftArtifact,
    markdown: str,
) -> str:
    workspace_path = draft.workspace_path
    filename = Path(workspace_path).name
    content = markdown.encode("utf-8")
    storage_key = build_storage_key(str(project.id), workspace_path)
    content_hash = bytes_content_hash(content)

    await asyncio.to_thread(
        upload_project_file,
        storage_key=storage_key,
        content=content,
        filename=filename,
    )
    await upsert_workspace_file(
        session,
        project_id=project.id,
        workspace_path=workspace_path,
        filename=filename,
        storage_bucket=settings.supabase_storage_bucket,
        storage_key=storage_key,
        content_hash=content_hash,
        size_bytes=len(content),
        ingest_status="generated",
        ingest_error=None,
        source_document_id=None,
    )
    return workspace_path


async def sync_consultant_procurement_draft_workspace(
    session: AsyncSession,
    *,
    project: Project,
    draft: DraftArtifact,
    markdown: str | None = None,
) -> str:
    canonical_path = consultant_procurement_workspace_path(
        project,
        discipline_slug=consultant_procurement_discipline_slug(draft.workflow_type),
        version=draft.version,
    )
    if draft.workspace_path != canonical_path:
        draft.workspace_path = canonical_path
        await session.flush()
        await session.refresh(draft)
    saved_path = await save_consultant_procurement_workspace_file(
        session,
        project=project,
        draft=draft,
        markdown=markdown or draft.content_markdown,
    )
    from app.projects.artefact_revisions import set_export_result_for_path

    content = (markdown or draft.content_markdown).encode("utf-8")
    await set_export_result_for_path(
        session,
        revision=draft,
        workspace_path=saved_path,
        content_hash=bytes_content_hash(content),
    )
    return saved_path


def normalise_discipline(discipline: str) -> DisciplineProfile:
    cleaned = " ".join(discipline.strip().split())
    if not cleaned:
        raise ValueError("discipline is required")
    key = _normalise_key(cleaned)
    if any(term in key for term in _NON_CONSULTANT_TERMS):
        raise NonConsultantDiscipline(cleaned)
    aliased = DISCIPLINE_ALIASES.get(key, key)
    if aliased in DISCIPLINE_PROFILES:
        return DISCIPLINE_PROFILES[aliased]
    return _profile(
        cleaned,
        requested_services=(
            f"Review the project brief, available design information, and approval pathway for {cleaned} services.",
            "Set out the scope, assumptions, deliverables, programme, exclusions, and required client inputs.",
            "Identify coordination, authority, tender, and construction-stage services needed for the project.",
        ),
        deliverables=(
            f"{cleaned} fee proposal with staged scope and exclusions.",
            "Deliverables schedule, required inputs, assumptions, and programme.",
            "Hourly rates and disbursements for additional services.",
        ),
    )


async def run_validated_rfp_narrative(
    *,
    project: Project,
    target: DisciplineProfile,
    rfp_context: RfpContext | None = None,
    generation_brief: ArtefactGenerationBrief | None = None,
    run_date: date | None = None,
    project_evidence: list[dict[str, Any]],
    platform_knowledge: list[dict[str, Any]],
    citation_index: CitationIndex,
    on_progress: ProgressPublisher | None = None,
    on_section_complete=None,
) -> RfpNarrativeOutput:
    """Run and validate the bounded RFP narrative, retrying invalid output twice."""
    validation_feedback: str | None = None
    consistency_ai_call_count = 0
    resolved_run_date = run_date or date.today()
    for attempt in range(RFP_NARRATIVE_MAX_ATTEMPTS):
        try:
            output = await run_rfp_narrative_model(
                project=project,
                target=target,
                rfp_context=rfp_context,
                generation_brief=generation_brief,
                project_evidence=project_evidence,
                platform_knowledge=platform_knowledge,
                citation_index=citation_index,
                validation_feedback=validation_feedback,
                on_progress=on_progress,
                on_section_complete=on_section_complete,
                run_date=resolved_run_date,
            )
            consistency_ai_call_count += output.consistency_ai_call_count
            await publish_procurement_progress(
                on_progress,
                {"stage": "validation_started"},
            )
            validate_rfp_output(output, citation_index=citation_index)
            return output.model_copy(
                update={"consistency_ai_call_count": consistency_ai_call_count}
            )
        except WorkflowValidationError as exc:
            consistency_ai_call_count += int(
                getattr(exc, "consistency_ai_call_count", 0) or 0
            )
            if attempt == RFP_NARRATIVE_MAX_ATTEMPTS - 1:
                exc.consistency_ai_call_count = consistency_ai_call_count
                raise
            validation_feedback = str(exc)

    raise RuntimeError("RFP narrative retry loop exited unexpectedly")


class ConsultantDocument(ProcurementDocument):
    seed_artefact_type = "rfp"
    document_key = WORKFLOW_TYPE_PREFIX
    workspace_subfolder = "02-consultant"
    filename_stem = "consultant_procurement"
    knowledge_workflow = KNOWLEDGE_WORKFLOW
    runtime_name = RUNTIME_NAME
    provenance_target_key = "discipline"
    trace_tool_name = "draft_consultant_procurement_artifact"
    trace_generation_purpose = (
        "Generated and saved the consultant procurement artefact."
    )
    trace_evidence_purpose = (
        "Gathered active-project evidence for the consultant tender basis."
    )
    trace_guidance_purpose = "Gathered SiteWise consultant procurement guidance."
    load_required_seed_content = True

    def resolve_target(self, raw: str) -> ProcurementTarget:
        return normalise_discipline(raw)

    def title(self, target: ProcurementTarget) -> str:
        return f"Request for Proposal - {target.name}"

    def build_context(
        self,
        project_context: ProjectGenerationContext,
        target: ProcurementTarget,
    ) -> RfpContext:
        return build_rfp_context(project_context, target.name)

    def evidence_queries(self, target: ProcurementTarget) -> tuple[EvidenceQuery, ...]:
        return _evidence_queries(target)

    def platform_query(self, target: ProcurementTarget) -> str:
        terms = " ".join(getattr(target, "knowledge_query_terms", ()))
        query = (
            f"consultant procurement request for fee proposal {target.name} "
            "scope deliverables exclusions fee response programme"
        )
        return f"{query} {terms}".strip()

    def platform_guidance_paths(self, target: ProcurementTarget) -> tuple[str, ...]:
        return (
            *super().platform_guidance_paths(target),
            *tuple(getattr(target, "knowledge_paths", ())),
        )

    async def issued_documents(
        self,
        session: AsyncSession,
        *,
        project: Project,
        target: ProcurementTarget,
        narrative_evidence: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        del narrative_evidence
        documents = await load_procurement_document_register(
            session,
            project_id=project.id,
            target_name=target.name,
        )
        return _reviewable_evidence(documents, target)

    def filter_platform_knowledge(
        self,
        knowledge: list[dict[str, Any]],
        target: ProcurementTarget,
    ) -> list[dict[str, Any]]:
        from app.workflows.procurement_request import CONTRACTOR_TENDERING_GUIDANCE_PATH

        target_paths = set(getattr(target, "knowledge_paths", ()))
        discipline_paths = {
            path
            for profile in DISCIPLINE_PROFILES.values()
            for path in profile.knowledge_paths
        }
        return [
            item
            for item in knowledge
            if (path := str(item.get("path") or "")) != CONTRACTOR_TENDERING_GUIDANCE_PATH
            and (path not in discipline_paths or path in target_paths)
        ]

    async def forecast(
        self,
        session: AsyncSession,
        *,
        project_id: uuid.UUID,
        target: ProcurementTarget,
    ) -> dict[str, Any]:
        forecast = await _forecast_for_discipline(
            session,
            project_id=project_id,
            profile=target,
        )
        return forecast

    def reconcile_forecast(
        self,
        forecast: dict[str, Any],
        evidence: list[dict[str, Any]],
        target: ProcurementTarget,
    ) -> dict[str, Any]:
        return _reconcile_forecast_with_received(forecast, evidence, target)

    def assumptions_and_missing(
        self,
        *,
        project: Project,
        evidence: list[dict[str, Any]],
        forecast: dict[str, Any],
        target: ProcurementTarget,
    ) -> tuple[list[str], list[str]]:
        return _assumptions_and_missing_inputs(
            project=project,
            evidence=evidence,
            forecast=forecast,
            profile=target,
        )

    async def render(
        self,
        *,
        project: Project,
        target: ProcurementTarget,
        project_evidence: list[dict[str, Any]],
        issued_documents: list[dict[str, Any]],
        platform_knowledge: list[dict[str, Any]],
        forecast: dict[str, Any],
        assumptions: list[str],
        missing_inputs: list[str],
        max_pages: int,
        instructions: str | None,
        artefact_context: ProcurementArtefactContext | None,
        generation_brief: ArtefactGenerationBrief | None,
        on_progress: ProgressPublisher | None,
    ) -> str:
        rfp_context = (
            artefact_context if isinstance(artefact_context, RfpContext) else None
        )
        rfp_evidence = _reviewable_evidence(project_evidence, target)
        citation_index = build_rfp_citation_index(rfp_evidence)
        scaffold = render_rfp_scaffold(
            project=project,
            target=target,
            citation_index=citation_index,
            forecast=forecast,
            max_pages=max_pages,
            instructions=instructions,
            assumptions=assumptions,
            missing_inputs=missing_inputs,
            project_evidence=rfp_evidence,
            issued_documents=issued_documents,
        )
        await publish_procurement_progress(
            on_progress,
            {"stage": "scaffold_ready", "markdown": scaffold},
        )

        async def publish_progressive_preview(
            _key: str, _result: object, completed: dict[str, object]
        ) -> None:
            from app.workflows.progressive_preview import (
                assemble_procurement_progressive_preview,
            )

            await publish_procurement_progress(
                on_progress,
                {
                    "stage": "section_completed",
                    "markdown": assemble_procurement_progressive_preview(
                        scaffold, completed
                    ),
                },
            )

        narrative = await run_validated_rfp_narrative(
            project=project,
            target=target,
            rfp_context=rfp_context,
            generation_brief=generation_brief,
            project_evidence=rfp_evidence,
            platform_knowledge=platform_knowledge,
            citation_index=citation_index,
            on_progress=on_progress,
            on_section_complete=publish_progressive_preview,
        )
        requested_services = narrative.requested_services or list(
            target.requested_services
        )
        requested_services_markdown = "\n".join(
            f"{index}. {clean_issue_language(line)}"
            for index, line in enumerate(requested_services, start=1)
        )
        programme_markdown = "\n".join(
            f"- {clean_issue_language(line)}" for line in narrative.programme
        )
        return (
            scaffold.replace(
                BACKGROUND_PLACEHOLDER,
                clean_issue_language(narrative.background),
            )
            .replace(
                REQUESTED_SERVICES_PLACEHOLDER,
                requested_services_markdown,
            )
            .replace(PROGRAMME_PLACEHOLDER, programme_markdown)
        )


CONSULTANT_DOCUMENT = ConsultantDocument()


async def _sync_for_engine(session: AsyncSession, *, document, **kwargs) -> str:
    return await sync_consultant_procurement_draft_workspace(session, **kwargs)


async def draft_consultant_procurement_artifact(
    session: AsyncSession,
    *,
    project: Project,
    user_id: uuid.UUID,
    discipline: str,
    max_pages: int = 3,
    instructions: str | None = None,
    generation_context: ProjectGenerationContext | None = None,
    auto_commit: bool = True,
    on_progress: ProgressPublisher | None = None,
) -> ConsultantProcurementResult:
    result = await draft_procurement_request(
        session,
        project=project,
        user_id=user_id,
        document=CONSULTANT_DOCUMENT,
        raw_target=discipline,
        max_pages=max_pages,
        instructions=instructions,
        generation_context=generation_context,
        auto_commit=auto_commit,
        retriever_factory=DocumentRetriever,
        next_version=next_draft_version,
        create_draft=create_draft_artifact,
        sync_workspace=_sync_for_engine,
        on_progress=on_progress,
    )
    return ConsultantProcurementResult(
        draft=result.draft,
        discipline=result.target_name,
        source_trace=result.source_trace,
    )


async def _forecast_for_discipline(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    profile: DisciplineProfile,
) -> dict[str, Any]:
    draft = await get_latest_draft_artifact(
        session,
        project_id=project_id,
        workflow_type=CREATE_COST_PLAN_WORKFLOW_TYPE,
    )
    if draft is None:
        reason = (
            "No benchmark rule for this discipline."
            if not profile.benchmark_terms
            else "No cost plan draft was available."
        )
        return {"used": False, "reason": reason}

    forecast = forecast_consultant_fees_for_markdown(
        draft.content_markdown,
        source_path=draft.workspace_path,
    )
    adopted_budget = _adopted_construction_budget(draft.content_markdown)
    budget_context = {
        "source_path": draft.workspace_path,
        "construction_budget": adopted_budget or forecast.construction_base,
        "construction_budget_basis": (
            "user_adopted" if adopted_budget is not None else "cost_plan"
        ),
    }
    if not profile.benchmark_terms:
        return {
            **budget_context,
            "used": False,
            "reason": "No benchmark rule for this discipline.",
        }

    selected = _select_forecast_row(forecast.rows, profile.benchmark_terms)
    if selected is None:
        return {
            **budget_context,
            "used": False,
            "reason": "No matching consultant benchmark row was found in the current cost plan.",
        }
    row, bundled = selected
    if row.action != "forecasted" or row.forecast_budget is None:
        return {
            **budget_context,
            "used": False,
            "reason": "A matching consultant row exists, but it is already known or not forecasted.",
        }
    warnings = list(forecast.warnings)
    if bundled:
        warnings.append(
            f"Matched bundled cost-plan row '{row.cost_item}'; prefer a "
            f"{profile.name.lower()}-only allowance when available."
        )
    bundled_prefix = "bundled " if bundled else ""
    return {
        **budget_context,
        "used": True,
        "tool": "forecast_consultant_fees",
        "cost_item": row.cost_item,
        "forecast_budget": row.forecast_budget,
        "status": FORECAST_STATUS,
        "basis": FORECAST_BASIS,
        "bundled": bundled,
        "construction_base": forecast.construction_base,
        "warnings": warnings,
        "label": (
            f"{_money(row.forecast_budget)} ex GST {bundled_prefix}judgement "
            "allowance for internal budget checking only; not a received fee proposal."
        ),
    }


_OTHER_DISCIPLINE_MARKERS = (
    "fire engineer",
    "structural",
    "hydraulic",
    "mechanical",
    "electrical",
    "architect",
    "acoustic",
    "geotechnical",
    "surveyor",
    "sustainability",
    "access consultant",
)


def _select_forecast_row(
    rows: list[Any] | tuple[Any, ...],
    benchmark_terms: tuple[str, ...],
) -> tuple[Any, bool] | None:
    """Prefer discipline-specific cost-plan rows over bundled multi-discipline rows."""
    ranked: list[tuple[int, Any, bool]] = []
    for row in rows:
        label = _normalise_key(getattr(row, "cost_item", ""))
        matched_terms = [term for term in benchmark_terms if term in label]
        if not matched_terms:
            continue
        specificity = max(len(term) for term in matched_terms)
        foreign_markers = [
            marker
            for marker in _OTHER_DISCIPLINE_MARKERS
            if marker in label
            and not any(marker in term for term in benchmark_terms)
        ]
        bundled = bool(foreign_markers)
        rank = specificity * 10 - (20 if bundled else 0)
        ranked.append((rank, row, bundled))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    _, row, bundled = ranked[0]
    return row, bundled


_ADOPTED_CONSTRUCTION_BUDGET_RE = re.compile(
    r"adopted_construction_budget_ex_gst:\*\*\s*\$([\d,]+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)


def _adopted_construction_budget(markdown: str) -> int | None:
    """Read the user-adopted construction envelope from the current Cost Plan."""
    match = _ADOPTED_CONSTRUCTION_BUDGET_RE.search(markdown)
    if match is None:
        return None
    return round(float(match.group(1).replace(",", "")))


def _evidence_queries(profile: DisciplineProfile) -> tuple[EvidenceQuery, ...]:
    name = profile.name
    if profile.slug == "certifier":
        queries = [
            EvidenceQuery(
                "planning_pathway",
                "Planning pathway and approvals",
                (
                    "development consent DA CDC CC conditions of consent approval "
                    "pathway council principal certifier PCA construction certificate"
                ),
            ),
            EvidenceQuery(
                "project_brief",
                "PPR and project brief",
                (
                    "Principal's Project Requirements PPR project brief owner brief "
                    "site address building class scale procurement route"
                ),
            ),
            EvidenceQuery(
                "discipline_requirements",
                "Certifier / PCA requirements",
                " ".join(
                    profile.evidence_query_terms
                    or (
                        "principal certifier appointment critical stage inspections "
                        "occupation certificate BASIX fire safety schedule"
                    )
                ),
            ),
            EvidenceQuery(
                "design_docs",
                "Approved / certification design documents",
                (
                    "approved drawings architectural documentation fire engineering "
                    "performance solution BASIX certificate certification package"
                ),
            ),
            EvidenceQuery(
                "programme",
                "Project programme",
                (
                    "programme milestones lodgement approval possession construction "
                    "critical stage inspection occupation certificate response date"
                ),
            ),
            EvidenceQuery(
                "cost_plan_pmp",
                "Cost plan / PMP",
                f"cost plan PMP budget programme consultant fees {name}",
            ),
            EvidenceQuery(
                "consultant_tracker",
                "Consultant tracker",
                f"consultant tracker consultant register appointments procurement {name}",
            ),
            EvidenceQuery(
                "previous_correspondence",
                "Previous consultant correspondence",
                f"{name} consultant correspondence email request for fee proposal",
            ),
        ]
        return tuple(queries)

    queries = [
        EvidenceQuery(
            "project_brief",
            "PPR and project brief",
            (
                "Principal's Project Requirements PPR project brief owner brief "
                "objectives overarching scope quality outcomes site constraints"
            ),
        ),
        EvidenceQuery(
            "planning_pathway",
            "Planning pathway",
            "planning pathway approval CDC DA council certifier authority pathway",
        ),
        EvidenceQuery(
            "project_scope",
            "Project scope and spaces",
            f"project scope rooms spaces occupancy amenities kitchenette systems {name}",
        ),
        EvidenceQuery(
            "programme",
            "Project programme",
            "programme milestones lodgement approval possession construction practical completion occupation response date",
        ),
        EvidenceQuery(
            "cost_plan_pmp",
            "Cost plan / PMP",
            f"cost plan PMP budget programme consultant fees {name}",
        ),
        EvidenceQuery(
            "design_docs",
            "Design documents",
            f"{name} design drawings specifications architectural documentation scope",
        ),
        EvidenceQuery(
            "consultant_tracker",
            "Consultant tracker",
            f"consultant tracker consultant register appointments procurement {name}",
        ),
        EvidenceQuery(
            "previous_correspondence",
            "Previous consultant correspondence",
            f"{name} consultant correspondence email request for fee proposal",
        ),
    ]
    if profile.evidence_query_terms:
        queries.append(
            EvidenceQuery(
                "discipline_requirements",
                f"{name} requirements",
                " ".join(profile.evidence_query_terms),
            )
        )
    return tuple(queries)


def _assumptions_and_missing_inputs(
    *,
    project: Project,
    evidence: list[dict[str, Any]],
    forecast: dict[str, Any],
    profile: DisciplineProfile | None = None,
) -> tuple[list[str], list[str]]:
    roles = {item["role"] for item in evidence}
    missing: list[str] = []
    if "project_brief" not in roles:
        missing.append("Project brief or owner scope brief.")
    if "planning_pathway" not in roles:
        missing.append("Planning pathway and approval route.")
    if "design_docs" not in roles:
        missing.append("Current design drawings or design scope.")
    if "consultant_tracker" not in roles:
        missing.append("Existing consultant tracker or appointment register.")
    if "previous_correspondence" not in roles:
        missing.append("Previous consultant correspondence for this discipline.")
    if not getattr(project, "state", None):
        missing.append("Project state / jurisdiction.")
    identity = resolve_project_identity(project, evidence=evidence)
    if not identity.get("site_address"):
        missing.append("Confirmed site address.")
    if not identity.get("client"):
        missing.append("Client / owner name for the tender.")
    missing.extend(
        [
            "Preferred fee response date.",
            "Submission contact and issue method.",
        ]
    )
    if profile is not None and profile.slug == "hydraulic_engineer":
        missing.extend(
            [
                "Existing hydraulic drawings, services survey, and verified connection/capacity information.",
                "Current wet-area, sanitary-fixture, kitchenette, and equipment layouts or schedules.",
                "Landlord hydraulic connection, shutdown, access, metering, and design-review requirements.",
            ]
        )

    from app.sitewise.rfp_renderer import detect_rfp_identity_conflicts

    identity_conflicts = detect_rfp_identity_conflicts(
        project=project,
        project_evidence=evidence,
    )
    missing.extend(identity_conflicts)

    assumptions = [
        "This is a client-issued Request for Proposal seeking a consultant fee response.",
        "The consultant must confirm scope, exclusions, programme, and fee basis before appointment.",
    ]
    if not evidence:
        assumptions.append(
            "No project evidence was found; the draft is a working template to confirm before issue."
        )
    if not forecast.get("used"):
        assumptions.append("No discipline-specific fee benchmark was applied.")
    if identity_conflicts:
        assumptions.append(
            "Resolve profile versus evidence identity conflicts before issuing this RFP."
        )
    return assumptions, missing


_FEE_PROPOSAL_MARKERS = ("fee-proposal", "fee_proposal")


def _is_consultant_fee_proposal(item: dict[str, Any]) -> bool:
    """Identify a received/competing consultant fee proposal.

    Such documents must never be circulated as inputs inside a client-issued
    tender request (leakage), but they are still useful for internal fee reconciliation.
    """
    text = f"{item.get('filename') or ''} {item.get('relative_path') or ''}".lower()
    if any(marker in text for marker in _FEE_PROPOSAL_MARKERS):
        return True
    snippet = str(item.get("snippet") or "").lstrip().lower().lstrip("# ").strip()
    return snippet.startswith("fee proposal")


def _reviewable_evidence(
    evidence: list[dict[str, Any]],
    profile: DisciplineProfile,
) -> list[dict[str, Any]]:
    competing_ids = {
        id(item) for item in _received_same_discipline_proposals(evidence, profile)
    }
    return [item for item in evidence if id(item) not in competing_ids]


def _received_same_discipline_proposals(
    evidence: list[dict[str, Any]],
    profile: DisciplineProfile,
) -> list[dict[str, Any]]:
    terms = profile.benchmark_terms or tuple(
        token for token in profile.slug.split("_") if len(token) > 3
    )
    matches: list[dict[str, Any]] = []
    for item in evidence:
        if not _is_consultant_fee_proposal(item):
            continue
        text = (
            f"{item.get('filename') or ''} {item.get('relative_path') or ''} "
            f"{item.get('snippet') or ''}"
        ).lower()
        if profile.slug in text or any(term in text for term in terms):
            matches.append(item)
    return matches


def _extract_fee_amount(items: list[dict[str, Any]]) -> int | None:
    best: int | None = None
    for item in items:
        snippet = str(item.get("snippet") or "")
        for match in re.finditer(r"\$\s*(\d[\d,]*)", snippet):
            value = int(match.group(1).replace(",", ""))
            if best is None or value > best:
                best = value
    return best


def _reconcile_forecast_with_received(
    forecast: dict[str, Any],
    evidence: list[dict[str, Any]],
    profile: DisciplineProfile,
) -> dict[str, Any]:
    """Flag a received same-discipline fee proposal so the parametric benchmark
    is reconciled against real evidence instead of quietly overriding it."""
    received = _received_same_discipline_proposals(evidence, profile)
    if not received:
        return forecast
    forecast["received_proposal_on_file"] = True
    amount = _extract_fee_amount(received)
    if amount is not None:
        forecast["received_proposal_amount"] = amount
    forecast["received_proposal_paths"] = [
        item.get("relative_path") or item.get("filename") for item in received
    ]
    return forecast


def _money(value: int | None) -> str:
    if value is None:
        return "TBC"
    return f"${value:,.0f}"
