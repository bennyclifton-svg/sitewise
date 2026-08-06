"""Evidence-grounded trade RFT and RFQ drafting through the shared engine."""

from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.draft_artifact import DraftArtifact
from app.database.source_document import SourceDocument
from app.database.workspace_files import upsert_workspace_file
from app.inbox.paths import build_storage_key
from app.projects.artefact_revisions import set_export_result_for_path
from app.sitewise.rfp_evidence_validation import validate_procurement_output
from app.sitewise.rfp_renderer import (
    BACKGROUND_PLACEHOLDER,
    PROGRAMME_PLACEHOLDER,
    REQUESTED_SERVICES_PLACEHOLDER,
    build_rfp_citation_index,
)
from app.sitewise.trade_request_renderer import render_trade_request_scaffold
from app.storage.project_files import upload_project_file
from app.workflows.create_pmp import WorkflowValidationError
from app.workflows.procurement_request import (
    EvidenceQuery,
    ProcurementDocument,
    ProcurementRequestResult,
    ProcurementTarget,
    draft_procurement_request,
)
from app.workflows.rfp_narrative import (
    ProcurementNarrativeOutput,
    run_procurement_narrative_model,
)
from ingest.document_metadata import infer_discipline_from_file_name
from ingest.hashing import bytes_content_hash

WORKFLOW_TYPE_PREFIX = "trade"
RUNTIME_NAME = "clerk-trade-procurement"
KNOWLEDGE_WORKFLOW = "trade-procurement"
NARRATIVE_MAX_ATTEMPTS = 3
_PACKAGE_DOCUMENT_CLASSES = frozenset({"drawing", "schedule", "specification"})
_LEADING_LIST_MARKER = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")


@dataclass(frozen=True, slots=True)
class TradeProfile:
    name: str
    slug: str
    aliases: tuple[str, ...]
    baseline_scope: tuple[str, ...]
    price_rows: tuple[str, ...]
    returnables: tuple[str, ...]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "trade_package"


def _normalise_key(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _profile(
    name: str,
    *,
    aliases: tuple[str, ...] = (),
    baseline_scope: tuple[str, ...],
    price_rows: tuple[str, ...],
    returnables: tuple[str, ...],
) -> TradeProfile:
    return TradeProfile(
        name=name,
        slug=_slugify(name),
        aliases=aliases,
        baseline_scope=baseline_scope,
        price_rows=price_rows,
        returnables=returnables,
    )


TRADE_PACKAGES: dict[str, TradeProfile] = {
    "main works": _profile(
        "Main Works",
        aliases=("head contractor", "main contractor", "builder"),
        baseline_scope=(
            "Review the issued design information and confirm the proposed construction scope.",
            "Coordinate all in-scope trade interfaces, site establishment, supervision, quality, safety, and programme obligations.",
            "Identify exclusions, design responsibility, authority interfaces, and required client decisions.",
        ),
        price_rows=("Preliminaries", "Building works", "Services coordination", "Testing, commissioning and handover"),
        returnables=("Programme", "Trade and consultant coordination approach", "Site management and WHS information", "Qualifications and exclusions"),
    ),
    "structural steel": _profile(
        "Structural Steel",
        aliases=("steel", "structural steelwork", "steel framing"),
        baseline_scope=(
            "Supply, fabricate, deliver, erect, and protect structural steelwork shown in the issued documents.",
            "Coordinate set-out, connections, access, temporary works, and interfaces with concrete, framing, cladding, and services.",
            "Provide shop drawings, certifications, inspections, coatings, and handover records where required.",
        ),
        price_rows=("Shop drawings and engineering coordination", "Fabrication and coatings", "Delivery and erection", "Connections, testing and certification"),
        returnables=("Shop drawing schedule", "Programme and lead times", "Welding/coating certifications", "Qualifications and exclusions"),
    ),
    "electrical": _profile(
        "Electrical Services",
        aliases=("electrician", "electrical services", "electrical contractor"),
        baseline_scope=(
            "Provide the electrical services scope identified in the issued documents and confirmed project evidence.",
            "Coordinate supply authority, switchboard, containment, lighting, power, controls, communications, and adjacent services interfaces.",
            "Include testing, commissioning, certification, as-builts, manuals, and training where applicable.",
        ),
        price_rows=("Supply authority and metering", "Distribution and containment", "Lighting and power", "Controls, testing and commissioning"),
        returnables=("Programme and lead times", "Shop drawings and samples", "Test records and certificates", "As-builts, manuals and warranties"),
    ),
    "windows and glazing": _profile(
        "Windows and Glazing",
        aliases=("windows", "glazing", "aluminium windows", "window supplier"),
        baseline_scope=(
            "Supply and install the scheduled windows, glazed doors, glazing, hardware, flashings, seals, and associated interfaces.",
            "Coordinate openings, structural tolerances, façade/weatherproofing interfaces, access, and protection.",
            "Provide shop drawings, samples, performance evidence, warranties, and installation records where required.",
        ),
        price_rows=("Shop drawings and samples", "Window and door supply", "Glazing, hardware and seals", "Installation, protection and warranties"),
        returnables=("Shop drawings", "Samples and product data", "Lead-time programme", "Performance evidence and warranties"),
    ),
    "hydraulic and plumbing": _profile(
        "Hydraulic and Plumbing Services",
        aliases=("plumbing", "hydraulic", "hydraulic services", "plumber"),
        baseline_scope=(
            "Provide the documented water, sanitary, stormwater, gas, trade-waste, and related hydraulic services scope.",
            "Coordinate authority connections, penetrations, fire-water interfaces, fixtures, access, and adjacent services.",
            "Include testing, commissioning, certification, as-builts, manuals, and warranties where applicable.",
        ),
        price_rows=("Authority and connection works", "Water, sanitary and stormwater services", "Fixtures and specialist systems", "Testing, commissioning and certification"),
        returnables=("Shop drawings", "Programme and lead times", "Test records and certificates", "As-builts and manuals"),
    ),
    "joinery and kitchens": _profile(
        "Joinery and Kitchens",
        aliases=("joinery", "kitchens", "cabinetry", "cabinet maker"),
        baseline_scope=(
            "Measure, manufacture, supply, deliver, and install the joinery and kitchen scope shown in the issued information.",
            "Coordinate finishes, appliances, services rough-ins, tolerances, access, protection, and making good.",
            "Provide shop drawings, samples, prototypes where required, warranties, and handover information.",
        ),
        price_rows=("Shop drawings and samples", "Manufacture and finishes", "Delivery and installation", "Appliance/service coordination and warranties"),
        returnables=("Shop drawings", "Finish and hardware samples", "Programme", "Warranties and care information"),
    ),
}

_TRADE_ALIASES = {
    _normalise_key(alias): profile
    for profile in TRADE_PACKAGES.values()
    for alias in (profile.name, *profile.aliases)
}


def normalise_trade_target(value: str) -> TradeProfile:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError("trade package is required")
    profile = _TRADE_ALIASES.get(_normalise_key(cleaned))
    if profile is not None:
        return profile
    return _profile(
        cleaned,
        baseline_scope=(
            f"Confirm the in-scope {cleaned} work from the issued project information.",
            "Identify interfaces, exclusions, design responsibility, programme constraints, and required client inputs.",
            "State required testing, commissioning, certification, warranties, as-builts, and handover information where applicable.",
        ),
        price_rows=("Base scope", "Options and alternates", "Rates and provisional allowances"),
        returnables=("Scope confirmation", "Programme and lead times", "Qualifications and exclusions", "Applicable warranties and certificates"),
    )


def trade_procurement_workspace_path(
    project: Any,
    *,
    kind: str,
    target_slug: str,
    version: int,
) -> str:
    root = project.workspace_path.rstrip("/")
    return (
        f"{root}/05-procurement/{target_slug}/02-tender-pack/"
        f"{target_slug}_{kind}_v{version:02d}.draft.md"
    )


def is_trade_procurement_workflow(workflow_type: str) -> bool:
    return workflow_type.startswith("trade_rft_") or workflow_type.startswith("trade_rfq_")


def _workflow_parts(workflow_type: str) -> tuple[str, str]:
    for kind in ("rft", "rfq"):
        prefix = f"trade_{kind}_"
        if workflow_type.startswith(prefix):
            return kind, workflow_type.removeprefix(prefix)
    raise ValueError(f"not a trade procurement workflow: {workflow_type}")


async def save_trade_procurement_workspace_file(
    session: AsyncSession,
    *,
    project: Any,
    draft: DraftArtifact,
    markdown: str,
) -> str:
    workspace_path = draft.workspace_path
    content = markdown.encode("utf-8")
    storage_key = build_storage_key(str(project.id), workspace_path)
    await asyncio.to_thread(
        upload_project_file,
        storage_key=storage_key,
        content=content,
        filename=Path(workspace_path).name,
    )
    await upsert_workspace_file(
        session,
        project_id=project.id,
        workspace_path=workspace_path,
        filename=Path(workspace_path).name,
        storage_bucket=settings.supabase_storage_bucket,
        storage_key=storage_key,
        content_hash=bytes_content_hash(content),
        size_bytes=len(content),
        ingest_status="generated",
        ingest_error=None,
        source_document_id=None,
    )
    return workspace_path


async def sync_trade_procurement_draft_workspace(
    session: AsyncSession,
    *,
    project: Any,
    draft: DraftArtifact,
    markdown: str | None = None,
) -> str:
    kind, target_slug = _workflow_parts(draft.workflow_type)
    canonical_path = trade_procurement_workspace_path(
        project,
        kind=kind,
        target_slug=target_slug,
        version=draft.version,
    )
    if draft.workspace_path != canonical_path:
        draft.workspace_path = canonical_path
        await session.flush()
        await session.refresh(draft)
    saved_path = await save_trade_procurement_workspace_file(
        session,
        project=project,
        draft=draft,
        markdown=markdown or draft.content_markdown,
    )
    await set_export_result_for_path(
        session,
        revision=draft,
        workspace_path=saved_path,
        content_hash=bytes_content_hash((markdown or draft.content_markdown).encode("utf-8")),
    )
    return saved_path


async def _sync_for_engine(session: AsyncSession, *, document: Any, **kwargs: Any) -> str:
    del document
    return await sync_trade_procurement_draft_workspace(session, **kwargs)


async def run_validated_trade_narrative(
    *,
    project: Any,
    target: TradeProfile,
    kind: str,
    project_evidence: list[dict[str, Any]],
    platform_knowledge: list[dict[str, Any]],
    citation_index: Any,
) -> ProcurementNarrativeOutput:
    instructions_path = Path(__file__).with_name(
        "trade_rft_narrative_instructions.md"
        if kind == "rft"
        else "trade_rfq_narrative_instructions.md"
    )
    validation_feedback: str | None = None
    for attempt in range(NARRATIVE_MAX_ATTEMPTS):
        output = await run_procurement_narrative_model(
            project=project,
            target_name=target.name,
            target_label="Procurement package",
            baseline_scope=target.baseline_scope,
            project_evidence=project_evidence,
            platform_knowledge=platform_knowledge,
            citation_index=citation_index,
            instructions_path=instructions_path,
            validation_feedback=validation_feedback,
        )
        try:
            validate_procurement_output(output, citation_index=citation_index)
            return output
        except WorkflowValidationError as exc:
            if attempt == NARRATIVE_MAX_ATTEMPTS - 1:
                raise
            validation_feedback = str(exc)
    raise RuntimeError("trade narrative retry loop exited unexpectedly")


async def load_trade_package_evidence(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    target: ProcurementTarget,
) -> list[dict[str, Any]]:
    """Load every primary-discipline design document for a trade package."""
    discipline = infer_discipline_from_file_name(target.name)
    if discipline is None:
        return []

    result = await session.execute(
        select(
            SourceDocument.id,
            SourceDocument.filename,
            SourceDocument.relative_path,
            SourceDocument.document_class,
            SourceDocument.document_metadata,
        )
        .where(SourceDocument.project_id == project_id)
        .order_by(SourceDocument.relative_path.asc())
    )
    evidence: list[dict[str, Any]] = []
    for document in result.all():
        metadata = (
            dict(document.document_metadata)
            if isinstance(document.document_metadata, dict)
            else {}
        )
        metadata_discipline = str(metadata.get("discipline") or "").casefold()
        filename_discipline = infer_discipline_from_file_name(document.filename)
        is_primary_discipline = (
            metadata_discipline == discipline.casefold()
            or filename_discipline == discipline
        )
        if (
            not is_primary_discipline
            or document.document_class not in _PACKAGE_DOCUMENT_CLASSES
        ):
            continue

        # A discipline-coded drawing number is stronger than a conflicting
        # caption elsewhere in a split-sheet filename (for example M01 ... Electrical).
        metadata["discipline"] = discipline
        document_number = metadata.get("document_number") or metadata.get(
            "drawing_number"
        )
        label = str(document_number or document.filename)
        evidence.append(
            {
                "role": "scope_of_works",
                "role_label": f"Issued {discipline} package document",
                "document_id": str(document.id),
                "chunk_id": str(document.id),
                "filename": document.filename,
                "relative_path": document.relative_path,
                "page_or_section": metadata.get("revision"),
                "snippet": (
                    f"{discipline} package register entry: {label}. "
                    f"Title: {metadata.get('title') or document.filename}. "
                    f"Revision: {metadata.get('revision') or 'unknown'}."
                ),
                "score": None,
                "document_metadata": metadata,
            }
        )
    return evidence


def _scope_item(value: str) -> str:
    return _LEADING_LIST_MARKER.sub("", value, count=1).strip()


class TradeProcurementDocument(ProcurementDocument):
    workspace_subfolder = "05-procurement"
    filename_stem = "trade"
    knowledge_workflow = KNOWLEDGE_WORKFLOW
    runtime_name = RUNTIME_NAME
    trace_tool_name = "draft_trade_procurement_artifact"
    trace_generation_purpose = "Generated and saved the trade procurement artefact."
    trace_evidence_purpose = "Gathered active-project evidence for the trade request basis."
    trace_guidance_purpose = "Gathered SiteWise trade procurement guidance."
    load_required_seed_content = True

    def __init__(self, kind: str) -> None:
        if kind not in {"rft", "rfq"}:
            raise ValueError("kind must be rft or rfq")
        self.kind = kind
        self.document_key = f"trade_{kind}"

    def provenance_metadata(self, target: ProcurementTarget) -> dict[str, Any]:
        return {"request_kind": self.kind, "trade_package": target.name}

    def resolve_target(self, raw: str) -> ProcurementTarget:
        return normalise_trade_target(raw)

    def title(self, target: ProcurementTarget) -> str:
        label = "Request for Tender" if self.kind == "rft" else "Request for Quotation"
        return f"{label} - {target.name}"

    def evidence_queries(self, target: ProcurementTarget) -> tuple[EvidenceQuery, ...]:
        name = target.name
        return (
            EvidenceQuery("project_brief", "Project brief", "project brief owner objectives scope site constraints"),
            EvidenceQuery("scope_of_works", "Scope and design information", f"{name} scope drawings specifications schedule interfaces"),
            EvidenceQuery(
                "interface_drawings",
                "Relevant interface drawings",
                (
                    f"{name} architectural interface drawings floor plans reflected "
                    "ceiling plans sections shafts penetrations louvres plant access coordination"
                ),
            ),
            EvidenceQuery("programme", "Programme", f"{name} programme milestones access lead time construction completion"),
            EvidenceQuery("cost_plan_pmp", "Cost plan / Project Plan", f"cost plan project plan {name} procurement programme"),
            EvidenceQuery("approvals", "Approvals and compliance", f"{name} approvals authority compliance certificates testing"),
        )

    async def supplemental_project_evidence(
        self,
        session: AsyncSession,
        *,
        project: Any,
        target: ProcurementTarget,
    ) -> list[dict[str, Any]]:
        return await load_trade_package_evidence(
            session,
            project_id=project.id,
            target=target,
        )

    def platform_query(self, target: ProcurementTarget) -> str:
        return (
            f"trade procurement request for tender request for quotation {target.name} "
            "scope interfaces price schedule returnables qualifications testing handover"
        )

    async def forecast(
        self,
        session: AsyncSession,
        *,
        project_id: uuid.UUID,
        target: ProcurementTarget,
    ) -> dict[str, Any]:
        del session, project_id, target
        return {"used": False, "reason": "Trade price schedules are deterministic blank returnables."}

    def assumptions_and_missing(
        self,
        *,
        project: Any,
        evidence: list[dict[str, Any]],
        forecast: dict[str, Any],
        target: ProcurementTarget,
    ) -> tuple[list[str], list[str]]:
        del project, forecast, target
        roles = {str(item.get("role") or "") for item in evidence}
        missing = [
            item
            for role, item in (
                ("project_brief", "Project brief and client objectives."),
                ("scope_of_works", "Current drawings, specifications, and package scope."),
                ("programme", "Tender close, required-on-site date, and programme assumptions."),
            )
            if role not in roles
        ]
        missing.extend(
            [
                "Delivery basis, contract basis, and design responsibility.",
                "Submission contact and lodgement method.",
            ]
        )
        assumptions = [
            "This is a client-issued draft procurement request, not an offer or award.",
            "Tenderers must identify qualifications, exclusions, and departures before issue or pricing.",
        ]
        return assumptions, missing

    async def render(
        self,
        *,
        project: Any,
        target: ProcurementTarget,
        project_evidence: list[dict[str, Any]],
        platform_knowledge: list[dict[str, Any]],
        forecast: dict[str, Any],
        assumptions: list[str],
        missing_inputs: list[str],
        max_pages: int,
        instructions: str | None,
    ) -> str:
        del max_pages
        profile = target if isinstance(target, TradeProfile) else normalise_trade_target(target.name)
        citation_index = build_rfp_citation_index(project_evidence)
        scaffold = render_trade_request_scaffold(
            kind=self.kind,
            project=project,
            target=profile,
            citation_index=citation_index,
            forecast=forecast,
            project_evidence=project_evidence,
            assumptions=assumptions,
            missing_inputs=missing_inputs,
            instructions=instructions,
        )
        narrative = await run_validated_trade_narrative(
            project=project,
            target=profile,
            kind=self.kind,
            project_evidence=project_evidence,
            platform_knowledge=platform_knowledge,
            citation_index=citation_index,
        )
        scope_items = narrative.requested_services or list(profile.baseline_scope)
        scope_markdown = "\n".join(
            f"{index}. {_scope_item(item)}"
            for index, item in enumerate(scope_items, start=1)
        )
        programme_markdown = "\n".join(f"- {item}" for item in narrative.programme)
        if not programme_markdown:
            programme_markdown = "- Programme details: TBC by client before issue."
        return (
            scaffold.replace(BACKGROUND_PLACEHOLDER, narrative.background)
            .replace(REQUESTED_SERVICES_PLACEHOLDER, scope_markdown)
            .replace(PROGRAMME_PLACEHOLDER, programme_markdown)
        )


TRADE_RFT_DOCUMENT = TradeProcurementDocument("rft")
TRADE_RFQ_DOCUMENT = TradeProcurementDocument("rfq")


@dataclass(frozen=True, slots=True)
class TradeProcurementResult:
    draft: DraftArtifact
    package: str
    kind: str
    source_trace: dict[str, Any]


async def draft_trade_procurement_artifact(
    session: AsyncSession,
    *,
    project: Any,
    user_id: uuid.UUID,
    package: str,
    kind: str,
    max_pages: int = 3,
    instructions: str | None = None,
    auto_commit: bool = True,
) -> TradeProcurementResult:
    document = TRADE_RFT_DOCUMENT if kind == "rft" else TRADE_RFQ_DOCUMENT if kind == "rfq" else None
    if document is None:
        raise ValueError("kind must be rft or rfq")
    result: ProcurementRequestResult = await draft_procurement_request(
        session,
        project=project,
        user_id=user_id,
        document=document,
        raw_target=package,
        max_pages=max_pages,
        instructions=instructions,
        auto_commit=auto_commit,
        sync_workspace=_sync_for_engine,
    )
    return TradeProcurementResult(
        draft=result.draft,
        package=result.target_name,
        kind=kind,
        source_trace=result.source_trace,
    )
