from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass
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
from app.storage.project_files import upload_project_file
from ingest.hashing import bytes_content_hash
from app.retrieval.retriever import DocumentRetriever
from app.retrieval.schemas import RetrievalFilters
from app.sitewise.knowledge_catalog import (
    DOCTRINE_PATH,
    catalog_entry_for_path,
    select_required_paths,
)
from app.sitewise.cost_plan_consultant_forecast import (
    FORECAST_BASIS,
    FORECAST_STATUS,
    forecast_consultant_fees_for_markdown,
)
from app.workflows.create_cost_plan import WORKFLOW_TYPE as CREATE_COST_PLAN_WORKFLOW_TYPE

WORKFLOW_TYPE_PREFIX = "consultant_procurement"
RUNTIME_NAME = "clerk-consultant-procurement"
# Knowledge-catalog workflow key: seeds opt in via `required_by: {consultant-procurement: N}`.
KNOWLEDGE_WORKFLOW = "consultant-procurement"


@dataclass(frozen=True, slots=True)
class DisciplineProfile:
    name: str
    slug: str
    benchmark_terms: tuple[str, ...]
    requested_services: tuple[str, ...]
    deliverables: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceQuery:
    key: str
    label: str
    query: str


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
    benchmark_terms: tuple[str, ...] = (),
    requested_services: tuple[str, ...],
    deliverables: tuple[str, ...],
) -> DisciplineProfile:
    return DisciplineProfile(
        name=name,
        slug=_slugify(name),
        benchmark_terms=benchmark_terms,
        requested_services=requested_services,
        deliverables=deliverables,
    )


DISCIPLINE_PROFILES: dict[str, DisciplineProfile] = {
    _normalise_key("architect"): _profile(
        "Architect",
        requested_services=(
            "Review the project brief, planning pathway, design status, and client objectives.",
            "Confirm architectural design scope, consultant coordination role, and approval support.",
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
        benchmark_terms=("structural",),
        requested_services=(
            "Review architectural drawings, project brief, site constraints, and any geotechnical advice.",
            "Provide structural design, drawings, calculations, certification inputs, and coordination advice.",
            "Allow for builder queries, design clarifications, and construction-stage inspections where required.",
        ),
        deliverables=(
            "Structural fee proposal with design, documentation, certification, and site-phase allowances.",
            "List of required inputs, exclusions, and assumptions.",
            "Hourly rates for variations, meetings, inspections, and additional design work.",
        ),
    ),
    _normalise_key("hydraulic engineer"): _profile(
        "Hydraulic engineer",
        benchmark_terms=("hydraulic", "wastewater"),
        requested_services=(
            "Review the project brief, authority pathway, site services, and architectural/design documents.",
            "Advise on hydraulic, stormwater, sewer, water, drainage, and authority-service interfaces.",
            "Coordinate design documentation and certification inputs with the project team.",
        ),
        deliverables=(
            "Hydraulic services fee proposal with staged design and documentation scope.",
            "Authority coordination assumptions and required client/site information.",
            "Exclusions, disbursements, hourly rates, and optional service items.",
        ),
    ),
    _normalise_key("geotechnical engineer"): _profile(
        "Geotechnical engineer",
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
        benchmark_terms=("basix", "energy", "nathers"),
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
        benchmark_terms=("certifier", "principal certifier", "pca"),
        requested_services=(
            "Review the planning/building approval pathway, design status, and statutory inspection needs.",
            "Price certification advice, CC/CDC or approval support, inspection regime, and occupation certificate inputs.",
            "Identify authority fees, excluded consultant certificates, and client-side obligations.",
        ),
        deliverables=(
            "Certification fee proposal with statutory role, inspections, and approval deliverables.",
            "Schedule of required certificates, documents, and owner/consultant inputs.",
            "Exclusions, statutory fees, disbursements, and additional hourly rates.",
        ),
    ),
    _normalise_key("landscape architect"): _profile(
        "Landscape architect",
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
    _normalise_key("hydraulic consultant"): _normalise_key("hydraulic engineer"),
    _normalise_key("civil engineer"): _normalise_key("civil / stormwater engineer"),
    _normalise_key("stormwater engineer"): _normalise_key("civil / stormwater engineer"),
    _normalise_key("stormwater consultant"): _normalise_key("civil / stormwater engineer"),
}


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
    return await save_consultant_procurement_workspace_file(
        session,
        project=project,
        draft=draft,
        markdown=markdown or draft.content_markdown,
    )


def normalise_discipline(discipline: str) -> DisciplineProfile:
    cleaned = " ".join(discipline.strip().split())
    if not cleaned:
        raise ValueError("discipline is required")
    key = _normalise_key(cleaned)
    aliased = DISCIPLINE_ALIASES.get(key, key)
    if aliased in DISCIPLINE_PROFILES:
        return DISCIPLINE_PROFILES[aliased]
    return _profile(
        cleaned,
        requested_services=(
            f"Review the project brief, available design information, and approval pathway for {cleaned} services.",
            "Confirm the scope, assumptions, deliverables, programme, exclusions, and required client inputs.",
            "Identify coordination, authority, tender, and construction-stage services needed for the project.",
        ),
        deliverables=(
            f"{cleaned} fee proposal with staged scope and exclusions.",
            "Deliverables schedule, required inputs, assumptions, and programme.",
            "Hourly rates and disbursements for additional services.",
        ),
    )


async def draft_consultant_procurement_artifact(
    session: AsyncSession,
    *,
    project: Project,
    user_id: uuid.UUID,
    discipline: str,
    max_pages: int = 1,
    instructions: str | None = None,
) -> ConsultantProcurementResult:
    profile = normalise_discipline(discipline)
    pages = max(1, min(max_pages, 3))
    retriever = DocumentRetriever(session)
    project_evidence = await _retrieve_project_evidence(
        retriever,
        project=project,
        profile=profile,
    )
    platform_knowledge = await _retrieve_platform_knowledge(
        retriever,
        profile=profile,
    )
    platform_knowledge = _merge_required_guidance(platform_knowledge, project)
    forecast = await _forecast_for_discipline(
        session,
        project_id=project.id,
        profile=profile,
    )
    forecast = _reconcile_forecast_with_received(forecast, project_evidence, profile)
    assumptions, missing_inputs = _assumptions_and_missing_inputs(
        project=project,
        evidence=project_evidence,
        forecast=forecast,
    )
    source_trace = _source_trace(
        project_evidence=project_evidence,
        platform_knowledge=platform_knowledge,
        forecast=forecast,
        assumptions=assumptions,
        missing_inputs=missing_inputs,
    )
    markdown = _render_markdown(
        project=project,
        profile=profile,
        project_evidence=project_evidence,
        platform_knowledge=platform_knowledge,
        forecast=forecast,
        assumptions=assumptions,
        missing_inputs=missing_inputs,
        max_pages=pages,
        instructions=instructions,
    )

    workflow_type = consultant_procurement_workflow_type(profile.name)
    version_hint = await next_draft_version(
        session,
        project_id=project.id,
        workflow_type=workflow_type,
    )
    draft = await create_draft_artifact(
        session,
        project_id=project.id,
        workflow_type=workflow_type,
        title=f"Request for Fee Proposal - {profile.name}",
        workspace_path=consultant_procurement_workspace_path(
            project,
            discipline_slug=profile.slug,
            version=version_hint,
        ),
        author_user_id=user_id,
        content_markdown=markdown,
        model=None,
        runtime=RUNTIME_NAME,
        provenance_metadata={
            "workflow": WORKFLOW_TYPE_PREFIX,
            "discipline": profile.name,
            "max_pages": pages,
            "instructions": instructions,
            "source_trace": source_trace,
        },
    )
    await sync_consultant_procurement_draft_workspace(
        session,
        project=project,
        draft=draft,
        markdown=markdown,
    )
    await session.commit()
    return ConsultantProcurementResult(
        draft=draft,
        discipline=profile.name,
        source_trace=source_trace,
    )


async def _retrieve_project_evidence(
    retriever: DocumentRetriever,
    *,
    project: Project,
    profile: DisciplineProfile,
) -> list[dict[str, Any]]:
    filters = RetrievalFilters(
        active_project=project.slug,
        include_platform_knowledge=False,
    )
    evidence: list[dict[str, Any]] = []
    seen_chunks: set[str] = set()
    for query in _evidence_queries(profile):
        passages = await retriever.retrieve(
            query.query,
            filters=filters,
            limit=3,
            include_neighbours=False,
        )
        for passage in passages:
            chunk_key = str(_attr(passage, "chunk_id", ""))
            if chunk_key and chunk_key in seen_chunks:
                continue
            if chunk_key:
                seen_chunks.add(chunk_key)
            evidence.append(_project_evidence_item(query, passage))
    return evidence


async def _retrieve_platform_knowledge(
    retriever: DocumentRetriever,
    *,
    profile: DisciplineProfile,
) -> list[dict[str, Any]]:
    passages = await retriever.retrieve(
        (
            f"consultant procurement request for fee proposal {profile.name} "
            "scope deliverables exclusions fee response programme"
        ),
        filters=RetrievalFilters(project="sitewise-platform", phase="reference"),
        limit=5,
        include_neighbours=False,
    )
    knowledge: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for passage in passages:
        path = str(_attr(passage, "relative_path", ""))
        if path and path in seen_paths:
            continue
        if path:
            seen_paths.add(path)
        knowledge.append(_platform_knowledge_item(passage))
    return knowledge


def _required_guidance_paths(project: Project) -> list[str]:
    """Resolve the platform's consultant-procurement doctrine for this project.

    Uses the frontmatter-driven knowledge catalog so the governing guidance is
    surfaced deterministically, independent of whether semantic search happens
    to hit it. Only the consultant-procurement-tagged seeds are returned — the
    doctrine core, archetype, and role scaffolding are excluded so the RFP cites
    the procurement guidance specifically. Returns ``[]`` when project overlays
    are incomplete (guidance cannot be resolved).
    """
    user_role = getattr(project, "user_role", None)
    if not user_role:
        return []
    archetype = getattr(project, "archetype", None)
    building_class = getattr(project, "building_class", None)
    work_type = getattr(project, "work_type", None)
    if not archetype and not building_class:
        return []
    try:
        resolved = select_required_paths(
            workflow=KNOWLEDGE_WORKFLOW,
            archetype=archetype or "",
            user_role=user_role,
            building_class=building_class,
            work_type=work_type,
        )
    except ValueError:
        return []
    guidance: list[str] = []
    for path in resolved:
        if path == DOCTRINE_PATH:
            continue
        entry = catalog_entry_for_path(path)
        if entry is not None and KNOWLEDGE_WORKFLOW in entry.required_by:
            guidance.append(path)
    return guidance


def _merge_required_guidance(
    knowledge: list[dict[str, Any]],
    project: Project,
) -> list[dict[str, Any]]:
    """Fold catalog-mandated consultant-procurement doctrine into the platform
    knowledge list, so guidance is present even when semantic search returns
    nothing. Semantic hits keep their position; mandatory paths are appended."""
    existing = {item.get("path") for item in knowledge}
    for path in _required_guidance_paths(project):
        if path in existing:
            continue
        existing.add(path)
        entry = catalog_entry_for_path(path)
        knowledge.append(
            {
                "path": path,
                "title": entry.title if entry is not None else path.rsplit("/", maxsplit=1)[-1],
                "section": None,
                "snippet": entry.summary if entry is not None else "",
                "score": None,
                "source_type": "required-doctrine",
            }
        )
    return knowledge


async def _forecast_for_discipline(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    profile: DisciplineProfile,
) -> dict[str, Any]:
    if not profile.benchmark_terms:
        return {"used": False, "reason": "No benchmark rule for this discipline."}

    draft = await get_latest_draft_artifact(
        session,
        project_id=project_id,
        workflow_type=CREATE_COST_PLAN_WORKFLOW_TYPE,
    )
    if draft is None:
        return {"used": False, "reason": "No cost plan draft was available."}

    forecast = forecast_consultant_fees_for_markdown(
        draft.content_markdown,
        source_path=draft.workspace_path,
    )
    for row in forecast.rows:
        label = _normalise_key(row.cost_item)
        if not any(term in label for term in profile.benchmark_terms):
            continue
        if row.action != "forecasted" or row.forecast_budget is None:
            return {
                "used": False,
                "source_path": draft.workspace_path,
                "reason": "A matching consultant row exists, but it is already known or not forecasted.",
            }
        return {
            "used": True,
            "tool": "forecast_consultant_fees",
            "source_path": draft.workspace_path,
            "cost_item": row.cost_item,
            "forecast_budget": row.forecast_budget,
            "status": FORECAST_STATUS,
            "basis": FORECAST_BASIS,
            "construction_base": forecast.construction_base,
            "warnings": list(forecast.warnings),
            "label": (
                f"{_money(row.forecast_budget)} ex GST judgement allowance "
                "for internal budget checking only; not a received fee proposal."
            ),
        }

    return {
        "used": False,
        "source_path": draft.workspace_path,
        "reason": "No matching consultant benchmark row was found in the current cost plan.",
    }


def _evidence_queries(profile: DisciplineProfile) -> tuple[EvidenceQuery, ...]:
    name = profile.name
    return (
        EvidenceQuery(
            "project_brief",
            "Project brief",
            "project brief owner brief objectives scope site constraints",
        ),
        EvidenceQuery(
            "planning_pathway",
            "Planning pathway",
            "planning pathway approval CDC DA council certifier authority pathway",
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
    )


def _project_evidence_item(query: EvidenceQuery, passage: Any) -> dict[str, Any]:
    return {
        "role": query.key,
        "role_label": query.label,
        "document_id": str(_attr(passage, "document_id", "")),
        "chunk_id": str(_attr(passage, "chunk_id", "")),
        "filename": _attr(passage, "filename", "Unknown document"),
        "relative_path": _attr(passage, "relative_path", ""),
        "page_or_section": _attr(passage, "page_or_section", None),
        "snippet": _compact(_attr(passage, "content", ""), limit=260),
        "score": _attr(passage, "score", None),
    }


def _platform_knowledge_item(passage: Any) -> dict[str, Any]:
    metadata = _attr(passage, "document_metadata", None) or {}
    return {
        "path": _attr(passage, "relative_path", ""),
        "title": _platform_title(passage, metadata),
        "section": _attr(passage, "page_or_section", None),
        "snippet": _compact(_attr(passage, "content", ""), limit=260),
        "score": _attr(passage, "score", None),
        "source_type": _attr(passage, "source_type", None),
    }


def _assumptions_and_missing_inputs(
    *,
    project: Project,
    evidence: list[dict[str, Any]],
    forecast: dict[str, Any],
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
    missing.extend(
        [
            "Preferred fee response date.",
            "Submission contact and issue method.",
        ]
    )

    assumptions = [
        "This is a client-issued request for fee proposal, not a consultant-issued fee proposal.",
        "The consultant must confirm scope, exclusions, programme, and fee basis before appointment.",
    ]
    if not evidence:
        assumptions.append(
            "No project evidence was found; the draft is a working template to confirm before issue."
        )
    if not forecast.get("used"):
        assumptions.append("No discipline-specific fee benchmark was applied.")
    return assumptions, missing


def _source_trace(
    *,
    project_evidence: list[dict[str, Any]],
    platform_knowledge: list[dict[str, Any]],
    forecast: dict[str, Any],
    assumptions: list[str],
    missing_inputs: list[str],
) -> dict[str, Any]:
    tools = [
        {
            "name": "draft_consultant_procurement_artifact",
            "purpose": "Generated and saved the consultant procurement artefact.",
        },
        {
            "name": "search_documents",
            "purpose": "Gathered active-project evidence for the RFP basis.",
        },
        {
            "name": "search_platform_knowledge",
            "purpose": "Gathered SiteWise consultant procurement guidance.",
        },
    ]
    if forecast.get("used"):
        tools.append(
            {
                "name": "forecast_consultant_fees",
                "purpose": "Added an internal judgement allowance for budget context.",
            }
        )

    return {
        "project_documents": project_evidence,
        "platform_knowledge": platform_knowledge,
        "forecast": forecast,
        "assumptions": assumptions,
        "missing_inputs": missing_inputs,
        "tools": tools,
    }


def _render_markdown(
    *,
    project: Project,
    profile: DisciplineProfile,
    project_evidence: list[dict[str, Any]],
    platform_knowledge: list[dict[str, Any]],
    forecast: dict[str, Any],
    assumptions: list[str],
    missing_inputs: list[str],
    max_pages: int,
    instructions: str | None,
) -> str:
    service_limit = 4 if max_pages == 1 else 8
    deliverable_limit = 4 if max_pages == 1 else 8
    info_to_review = _information_to_review(project_evidence)
    forecast_line = (
        f"- Internal benchmark: {forecast['label']}"
        if forecast.get("used")
        else "- No internal fee benchmark is available for issue; consultant to price from scope."
    )
    if forecast.get("received_proposal_on_file"):
        amount = forecast.get("received_proposal_amount")
        amount_text = f" ({_money(amount)} ex GST)" if amount else ""
        forecast_line += (
            f"\n- Note: a received {profile.name} fee proposal is on file"
            f"{amount_text}; reconcile the internal benchmark against it before relying on it."
        )
    instruction_lines = _instruction_lines(instructions)

    sections = [
        f"# Request for Fee Proposal - {profile.name}",
        "",
        "## Project",
        f"- Project: {project.title}",
        f"- State / phase: {getattr(project, 'state', None) or 'TBC'} / {getattr(project, 'phase', None) or 'TBC'}",
        f"- Consultant discipline: {profile.name}",
        "",
        "## Background",
        _background(project, project_evidence),
        "",
        "## Requested services",
        *_bullets(profile.requested_services[:service_limit]),
        "",
        "## Information to review",
        *_bullets(info_to_review),
        "",
        "## Required deliverables",
        *_bullets(profile.deliverables[:deliverable_limit]),
        "",
        "## Programme / response date",
        "- Provide earliest availability, key programme assumptions, and duration for each stage.",
        "- Fee response date: TBC by client before issue.",
        "",
        "## Fee response requirements",
        "- Submit a lump-sum fee excluding GST, with GST shown separately.",
        "- Break the fee down by project stage and identify optional services, disbursements, and hourly rates.",
        "- State assumptions, exclusions, client inputs, authority fees, and validity period.",
        forecast_line,
        "",
        "## Exclusions / assumptions",
        *_bullets(assumptions[:4]),
        *_bullets(instruction_lines),
        "",
        "## Site visit / clarifications",
        "- Confirm whether a site visit is required and list any preconditions for attendance.",
        "- Submit clarification questions before pricing where information is incomplete.",
        "",
        "## Submission instructions",
        "- Submit the fee proposal to the client-nominated contact in PDF format.",
        "- Include company details, insurances, proposed personnel, and any terms requiring acceptance.",
        "",
        _basis_footer(project_evidence, platform_knowledge, forecast, missing_inputs),
    ]
    return "\n".join(sections).rstrip() + "\n"


def _background(project: Project, evidence: list[dict[str, Any]]) -> str:
    reviewable = _reviewable_evidence(evidence)
    if not reviewable:
        return (
            "Prepare this RFP from the declared project context only. Confirm the project brief, "
            "approval pathway, current design status, and consultant interfaces before issuing."
        )
    names = _unique_display_names(reviewable, limit=3)
    return (
        f"Prepare this RFP for {project.title} using the current project corpus, "
        f"including {', '.join(names)}."
    )


def _information_to_review(evidence: list[dict[str, Any]]) -> list[str]:
    reviewable = _reviewable_evidence(evidence)
    if not reviewable:
        return [
            "Project brief, current drawings, planning pathway, programme, and consultant tracker to be issued when available."
        ]
    lines = []
    for item in _unique_by_path(reviewable)[:6]:
        label = _document_kind(item) or item["role_label"]
        path = item["relative_path"] or item["filename"]
        lines.append(f"{label}: {path}")
    return lines


_FEE_PROPOSAL_MARKERS = ("fee-proposal", "fee_proposal")


def _is_consultant_fee_proposal(item: dict[str, Any]) -> bool:
    """Identify a received/competing consultant fee proposal.

    Such documents must never be circulated as inputs inside a client-issued
    RFP (leakage), but they are still useful for internal fee reconciliation.
    """
    text = f"{item.get('filename') or ''} {item.get('relative_path') or ''}".lower()
    if any(marker in text for marker in _FEE_PROPOSAL_MARKERS):
        return True
    snippet = str(item.get("snippet") or "").lstrip().lower().lstrip("# ").strip()
    return snippet.startswith("fee proposal")


def _document_kind(item: dict[str, Any]) -> str | None:
    """Label a document by its own identity, not the query that surfaced it.

    Returns ``None`` when the identity cannot be determined confidently, so the
    caller can fall back to the retrieval role label.
    """
    if _is_consultant_fee_proposal(item):
        return "Consultant fee proposal"
    text = f"{item.get('filename') or ''} {item.get('relative_path') or ''}".lower()
    if any(token in text for token in ("engagement-letter", "engagement_letter", "letter-of-engagement")):
        return "Engagement letter"
    if any(token in text for token in ("owner-project-brief", "owner_project_brief", "project-brief", "project_brief")):
        return "Owner project brief"
    if any(token in text for token in ("cost-plan", "cost_plan", "pmp")):
        return "Cost plan / PMP"
    if "heritage" in text:
        return "Heritage advice"
    return None


def _reviewable_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in evidence if not _is_consultant_fee_proposal(item)]


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


def _basis_footer(
    evidence: list[dict[str, Any]],
    knowledge: list[dict[str, Any]],
    forecast: dict[str, Any],
    missing_inputs: list[str],
) -> str:
    doc_names = ", ".join(_unique_display_names(_reviewable_evidence(evidence), limit=3)) or "none found"
    knowledge_names = ", ".join(
        item["title"] for item in knowledge[:2] if item.get("title")
    ) or "none found"
    forecast_text = forecast["label"] if forecast.get("used") else forecast.get("reason", "not used")
    missing = "; ".join(missing_inputs[:4])
    return (
        "Basis used: "
        f"project docs: {doc_names}. "
        f"Platform guidance: {knowledge_names}. "
        f"Forecast: {forecast_text}. "
        f"Missing inputs: {missing}."
    )


def _instruction_lines(instructions: str | None) -> list[str]:
    if not instructions or not instructions.strip():
        return []
    return [f"Additional instruction: {' '.join(instructions.split())}"]


def _bullets(items: tuple[str, ...] | list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def _unique_by_path(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("relative_path") or item.get("filename") or item.get("chunk_id"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _unique_display_names(items: list[dict[str, Any]], *, limit: int) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for item in _unique_by_path(items):
        name = item.get("filename") or item.get("relative_path")
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(str(name))
        if len(names) >= limit:
            break
    return names


def _platform_title(passage: Any, metadata: dict[str, Any]) -> str:
    frontmatter = metadata.get("frontmatter") if isinstance(metadata, dict) else None
    if isinstance(frontmatter, dict) and isinstance(frontmatter.get("title"), str):
        return frontmatter["title"]
    filename = str(_attr(passage, "filename", "Platform knowledge"))
    return filename.rsplit("/", maxsplit=1)[-1]


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


def _compact(value: str, *, limit: int) -> str:
    cleaned = " ".join(str(value).split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "..."


def _money(value: int | None) -> str:
    if value is None:
        return "TBC"
    return f"${value:,.0f}"
