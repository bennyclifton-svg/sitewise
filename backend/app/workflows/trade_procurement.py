"""Evidence-grounded trade and head-contractor RFT drafting."""

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
from app.database.workspace_files import upsert_workspace_file
from app.inbox.paths import build_storage_key
from app.projects.artefact_context import (
    ProcurementArtefactContext,
    RftContext,
    build_rft_context,
)
from app.projects.artefact_revisions import set_export_result_for_path
from app.projects.generation_brief import ArtefactGenerationBrief
from app.projects.generation_context import ProjectGenerationContext
from app.sitewise.artifact_presentation import clean_issue_language
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
    ProgressPublisher,
    ProcurementDocument,
    ProcurementRequestResult,
    ProcurementTarget,
    draft_procurement_request,
    publish_procurement_progress,
)
from app.workflows.procurement_register import load_procurement_document_register
from app.workflows.rfp_narrative import (
    ProcurementNarrativeOutput,
    run_procurement_narrative_model,
)
from ingest.hashing import bytes_content_hash

WORKFLOW_TYPE_PREFIX = "trade"
RUNTIME_NAME = "clerk-trade-procurement"
KNOWLEDGE_WORKFLOW = "trade-procurement"
NARRATIVE_MAX_ATTEMPTS = 3
_LEADING_LIST_MARKER = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
_MAIN_WORKS_PLATFORM_EXCLUSIONS = (
    "electrical-services-guide",
    "fire-services-guide",
    "hydraulic-services-guide",
    "ict-av-security-guide",
    "mechanical-services-guide",
    "vertical-transportation-guide",
)


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
            "Deliver the complete Main Works in accordance with the PPR, project brief, approvals, and issued design information.",
            "Provide site establishment, temporary works, logistics, supervision, safety, environmental, quality, and programme management.",
            "Coordinate architectural, structural, civil, services, specialist-subcontractor, authority, and utility interfaces.",
            "State the design-management and design-responsibility basis, including shop drawings, temporary works, delegated design, and consultant coordination.",
            "Provide testing, commissioning, certification, defects close-out, as-builts, manuals, warranties, training, and handover.",
            "Identify every exclusion, qualification, departure, substitution, provisional allowance, authority interface, and required client decision.",
        ),
        price_rows=(
            "Preliminaries",
            "Site establishment, demolition and temporary works",
            "Structure and building fabric",
            "Envelope, facade, roofing and waterproofing",
            "Internal construction, finishes and joinery",
            "Civil, landscape and external works",
            "Hydraulic and fire services",
            "Mechanical and vertical transportation",
            "Electrical, communications and security",
            "Design management, approvals and specialist coordination",
            "Testing, commissioning and handover",
        ),
        returnables=(
            "Signed Form of Tender and Addenda acknowledgement",
            "Detailed completed price schedule, trade breakdown, GST, provisional sums, allowances, options, and rates",
            "Tender programme, procurement schedule, critical path, and lead times",
            "Project organisation chart, key personnel, experience, and availability",
            "Construction methodology, staging, site logistics, access, and neighbour management",
            "Design management and design-responsibility matrix",
            "Proposed consultants, major subcontractors, suppliers, and procurement status",
            "WHS, environmental, quality assurance, inspection, and test-plan approach",
            "Current licences, registrations, insurances, financial capacity, and comparable project references",
            "Proposed contract departures and departures schedule",
            "Detailed qualifications, exclusions, assumptions, substitutions, alternatives, and allowances",
            "Commissioning, certification, defects, as-built, manuals, warranties, and handover plan",
        ),
    ),
    "structural steel": _profile(
        "Structural Steel",
        aliases=("steel", "structural steelwork", "steel framing"),
        baseline_scope=(
            "Supply, fabricate, deliver, erect, and protect structural steelwork shown in the issued documents.",
            "Coordinate set-out, connections, access, temporary works, and interfaces with concrete, framing, cladding, and services.",
            "Provide shop drawings, certifications, inspections, coatings, and handover records where required.",
        ),
        price_rows=(
            "Shop drawings and engineering coordination",
            "Fabrication and coatings",
            "Delivery and erection",
            "Connections, testing and certification",
        ),
        returnables=(
            "Shop drawing schedule",
            "Programme and lead times",
            "Welding/coating certifications",
            "Qualifications and exclusions",
        ),
    ),
    "electrical": _profile(
        "Electrical Services",
        aliases=("electrician", "electrical services", "electrical contractor"),
        baseline_scope=(
            "Provide the electrical services scope identified in the issued documents and confirmed project evidence.",
            "Coordinate supply authority, switchboard, containment, lighting, power, controls, communications, and adjacent services interfaces.",
            "Include testing, commissioning, certification, as-builts, manuals, and training where applicable.",
        ),
        price_rows=(
            "Supply authority and metering",
            "Distribution and containment",
            "Lighting and power",
            "Controls, testing and commissioning",
        ),
        returnables=(
            "Programme and lead times",
            "Shop drawings and samples",
            "Test records and certificates",
            "As-builts, manuals and warranties",
        ),
    ),
    "windows and glazing": _profile(
        "Windows and Glazing",
        aliases=("windows", "glazing", "aluminium windows", "window supplier"),
        baseline_scope=(
            "Supply and install the scheduled windows, glazed doors, glazing, hardware, flashings, seals, and associated interfaces.",
            "Coordinate openings, structural tolerances, façade/weatherproofing interfaces, access, and protection.",
            "Provide shop drawings, samples, performance evidence, warranties, and installation records where required.",
        ),
        price_rows=(
            "Shop drawings and samples",
            "Window and door supply",
            "Glazing, hardware and seals",
            "Installation, protection and warranties",
        ),
        returnables=(
            "Shop drawings",
            "Samples and product data",
            "Lead-time programme",
            "Performance evidence and warranties",
        ),
    ),
    "hydraulic and plumbing": _profile(
        "Hydraulic and Plumbing Services",
        aliases=("plumbing", "hydraulic", "hydraulic services", "plumber"),
        baseline_scope=(
            "Provide the documented water, sanitary, stormwater, gas, trade-waste, and related hydraulic services scope.",
            "Coordinate authority connections, penetrations, fire-water interfaces, fixtures, access, and adjacent services.",
            "Include testing, commissioning, certification, as-builts, manuals, and warranties where applicable.",
        ),
        price_rows=(
            "Authority and connection works",
            "Water, sanitary and stormwater services",
            "Fixtures and specialist systems",
            "Testing, commissioning and certification",
        ),
        returnables=(
            "Shop drawings",
            "Programme and lead times",
            "Test records and certificates",
            "As-builts and manuals",
        ),
    ),
    "joinery and kitchens": _profile(
        "Joinery and Kitchens",
        aliases=("joinery", "kitchens", "cabinetry", "cabinet maker"),
        baseline_scope=(
            "Measure, manufacture, supply, deliver, and install the joinery and kitchen scope shown in the issued information.",
            "Coordinate finishes, appliances, services rough-ins, tolerances, access, protection, and making good.",
            "Provide shop drawings, samples, prototypes where required, warranties, and handover information.",
        ),
        price_rows=(
            "Shop drawings and samples",
            "Manufacture and finishes",
            "Delivery and installation",
            "Appliance/service coordination and warranties",
        ),
        returnables=(
            "Shop drawings",
            "Finish and hardware samples",
            "Programme",
            "Warranties and care information",
        ),
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
            f"Define the in-scope {cleaned} work from the issued project information.",
            "Identify interfaces, exclusions, design responsibility, programme constraints, and required client inputs.",
            "State required testing, commissioning, certification, warranties, as-builts, and handover information where applicable.",
        ),
        price_rows=(
            "Base scope",
            "Options and alternates",
            "Rates and provisional allowances",
        ),
        returnables=(
            "Scope definition",
            "Programme and lead times",
            "Qualifications and exclusions",
            "Applicable warranties and certificates",
        ),
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
    return workflow_type.startswith("trade_rft_") or workflow_type.startswith(
        "trade_rfq_"
    )


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
        content_hash=bytes_content_hash(
            (markdown or draft.content_markdown).encode("utf-8")
        ),
    )
    return saved_path


async def _sync_for_engine(
    session: AsyncSession, *, document: Any, **kwargs: Any
) -> str:
    del document
    return await sync_trade_procurement_draft_workspace(session, **kwargs)


async def run_validated_trade_narrative(
    *,
    project: Any,
    target: TradeProfile,
    kind: str,
    rft_context: RftContext | None = None,
    generation_brief: ArtefactGenerationBrief | None = None,
    run_date: date | None = None,
    project_evidence: list[dict[str, Any]],
    platform_knowledge: list[dict[str, Any]],
    citation_index: Any,
    on_progress: ProgressPublisher | None = None,
    on_section_complete=None,
) -> ProcurementNarrativeOutput:
    instructions_path = Path(__file__).with_name(
        "trade_rft_narrative_instructions.md"
        if kind == "rft"
        else "trade_rfq_narrative_instructions.md"
    )
    validation_feedback: str | None = None
    consistency_ai_call_count = 0
    resolved_run_date = run_date or date.today()
    for attempt in range(NARRATIVE_MAX_ATTEMPTS):
        try:
            output = await run_procurement_narrative_model(
                project=project,
                target_name=target.name,
                target_label="Procurement package",
                rft_context=rft_context,
                generation_brief=generation_brief,
                baseline_scope=target.baseline_scope,
                project_evidence=project_evidence,
                platform_knowledge=platform_knowledge,
                citation_index=citation_index,
                instructions_path=instructions_path,
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
            validate_procurement_output(output, citation_index=citation_index)
            return output.model_copy(
                update={"consistency_ai_call_count": consistency_ai_call_count}
            )
        except WorkflowValidationError as exc:
            consistency_ai_call_count += int(
                getattr(exc, "consistency_ai_call_count", 0) or 0
            )
            if attempt == NARRATIVE_MAX_ATTEMPTS - 1:
                exc.consistency_ai_call_count = consistency_ai_call_count
                raise
            validation_feedback = str(exc)
    raise RuntimeError("trade narrative retry loop exited unexpectedly")


async def load_trade_package_evidence(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    target: ProcurementTarget,
) -> list[dict[str, Any]]:
    """Compatibility wrapper for the shared scope-aware issue register."""
    return await load_procurement_document_register(
        session,
        project_id=project_id,
        target_name=target.name,
    )


def _scope_item(value: str) -> str:
    return _LEADING_LIST_MARKER.sub("", value, count=1).strip()


def _evidence_item_text(item: dict[str, Any]) -> str:
    metadata = item.get("document_metadata")
    metadata_text = " ".join(
        str(value)
        for value in (metadata.values() if isinstance(metadata, dict) else ())
    )
    return " ".join(
        (
            str(item.get("filename") or ""),
            str(item.get("relative_path") or ""),
            str(item.get("page_or_section") or ""),
            metadata_text,
        )
    ).casefold()


def _is_overarching_item(item: dict[str, Any]) -> bool:
    text = _evidence_item_text(item)
    return any(
        marker in text
        for marker in (
            "00-brief-pmp",
            "principal project requirement",
            "principal's project requirement",
            "principals project requirement",
            " ppr ",
            "project brief",
        )
    )


def _is_project_control_item(item: dict[str, Any]) -> bool:
    text = _evidence_item_text(item)
    return any(
        marker in text
        for marker in (
            "00-brief-pmp",
            "cost plan",
            "project management plan",
            " pmp ",
            "budget",
        )
    )


def _is_meaningful_item(item: dict[str, Any]) -> bool:
    snippet = " ".join(str(item.get("snippet") or "").split())
    if len(snippet) < 80:
        return False
    punctuation = sum(1 for char in snippet if char in ".·")
    return punctuation / max(len(snippet), 1) < 0.25


class TradeProcurementDocument(ProcurementDocument):
    seed_artefact_type = "rft"
    workspace_subfolder = "05-procurement"
    filename_stem = "trade"
    knowledge_workflow = KNOWLEDGE_WORKFLOW
    runtime_name = RUNTIME_NAME
    trace_tool_name = "draft_trade_procurement_artifact"
    trace_generation_purpose = "Generated and saved the trade procurement artefact."
    trace_evidence_purpose = (
        "Gathered active-project evidence for the trade request basis."
    )
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
        request_name = (
            "Request for Tender" if self.kind == "rft" else "Request for Quotation"
        )
        return f"{request_name} - {target.name}"

    def build_context(
        self,
        project_context: ProjectGenerationContext,
        target: ProcurementTarget,
    ) -> RftContext:
        return build_rft_context(project_context, target.name)

    def evidence_queries(self, target: ProcurementTarget) -> tuple[EvidenceQuery, ...]:
        name = target.name
        if target.slug == "main_works":
            return (
                EvidenceQuery(
                    "project_brief",
                    "PPR and project brief — overarching intent",
                    (
                        "Principal Project Requirements project overview development "
                        "description client objectives apartment quality outcomes"
                    ),
                ),
                EvidenceQuery(
                    "scope_of_works",
                    "PPR — whole-of-project contractor responsibilities",
                    (
                        "PPR main works contractor responsibilities whole project site "
                        "management design coordination quality assurance reporting construction"
                    ),
                ),
                EvidenceQuery(
                    "design_responsibility",
                    "PPR — delivery and design responsibility",
                    (
                        "PPR preliminary design design and construct contractor design "
                        "responsibility multidisciplinary coordination"
                    ),
                ),
                EvidenceQuery(
                    "programme",
                    "PPR and project controls — programme",
                    (
                        "PPR staging programme milestones commencement completion site "
                        "access construction sequencing"
                    ),
                ),
                EvidenceQuery(
                    "cost_plan_pmp",
                    "Cost plan / Project Management Plan",
                    (
                        "project management plan PMP cost plan budget procurement strategy "
                        "main works"
                    ),
                ),
                EvidenceQuery(
                    "approvals",
                    "PPR and authorities — approvals and compliance",
                    (
                        "PPR development application conditions authority approvals "
                        "construction certificate contractor compliance"
                    ),
                ),
            )
        return (
            EvidenceQuery(
                "project_brief",
                "PPR and project brief",
                (
                    "Principal's Project Requirements PPR project brief owner "
                    "objectives overarching scope quality outcomes site constraints"
                ),
            ),
            EvidenceQuery(
                "scope_of_works",
                "Scope and design information",
                f"{name} scope drawings specifications schedule interfaces",
            ),
            EvidenceQuery(
                "interface_drawings",
                "Relevant interface drawings",
                (
                    f"{name} architectural interface drawings floor plans reflected "
                    "ceiling plans sections shafts penetrations louvres plant access coordination"
                ),
            ),
            EvidenceQuery(
                "programme",
                "Programme",
                f"{name} programme milestones access lead time construction completion",
            ),
            EvidenceQuery(
                "cost_plan_pmp",
                "Cost plan / Project Plan",
                f"cost plan project plan {name} procurement programme",
            ),
            EvidenceQuery(
                "approvals",
                "Approvals and compliance",
                f"{name} approvals authority compliance certificates testing",
            ),
        )

    def filter_project_evidence(
        self,
        evidence: list[dict[str, Any]],
        target: ProcurementTarget,
    ) -> list[dict[str, Any]]:
        if target.slug != "main_works":
            return evidence

        grouped: dict[str, list[dict[str, Any]]] = {}
        role_order: list[str] = []
        for item in evidence:
            role = str(item.get("role") or "")
            if role not in grouped:
                grouped[role] = []
                role_order.append(role)
            grouped[role].append(item)

        filtered: list[dict[str, Any]] = []
        for role in role_order:
            candidates = grouped[role]
            if role == "project_brief":
                candidates = [item for item in candidates if _is_overarching_item(item)]
            elif role == "cost_plan_pmp":
                candidates = [
                    item for item in candidates if _is_project_control_item(item)
                ]
            candidates = [item for item in candidates if _is_meaningful_item(item)]
            candidates.sort(key=lambda item: 0 if _is_overarching_item(item) else 1)
            filtered.extend(candidates[:2])
        return filtered

    async def issued_documents(
        self,
        session: AsyncSession,
        *,
        project: Any,
        target: ProcurementTarget,
        narrative_evidence: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        del narrative_evidence
        return await load_trade_package_evidence(
            session,
            project_id=project.id,
            target=target,
        )

    def platform_guidance_paths(self, target: ProcurementTarget) -> tuple[str, ...]:
        from app.workflows.procurement_request import CONTRACTOR_TENDERING_GUIDANCE_PATH

        return (
            *super().platform_guidance_paths(target),
            CONTRACTOR_TENDERING_GUIDANCE_PATH,
            "seed/trade-interfaces-coordination-guide.md",
        )

    def filter_platform_knowledge(
        self,
        knowledge: list[dict[str, Any]],
        target: ProcurementTarget,
    ) -> list[dict[str, Any]]:
        if target.slug != "main_works":
            return knowledge
        return [
            item
            for item in knowledge
            if not any(
                marker in str(item.get("path") or "").casefold()
                for marker in _MAIN_WORKS_PLATFORM_EXCLUSIONS
            )
        ]

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
        return {
            "used": False,
            "reason": "Trade price schedules are deterministic blank returnables.",
        }

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
                (
                    "scope_of_works",
                    "Current drawings, specifications, and package scope.",
                ),
                (
                    "programme",
                    "Tender close, required-on-site date, and programme assumptions.",
                ),
            )
            if role not in roles
        ]
        if "design_responsibility" not in roles:
            missing.append("Delivery basis, contract basis, and design responsibility.")
        missing.append("Submission contact and lodgement method.")
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
        rft_context = (
            artefact_context if isinstance(artefact_context, RftContext) else None
        )
        del max_pages
        profile = (
            target
            if isinstance(target, TradeProfile)
            else normalise_trade_target(target.name)
        )
        citation_index = build_rfp_citation_index(project_evidence)
        scaffold = render_trade_request_scaffold(
            kind=self.kind,
            project=project,
            target=profile,
            citation_index=citation_index,
            forecast=forecast,
            project_evidence=project_evidence,
            issued_documents=issued_documents,
            assumptions=assumptions,
            missing_inputs=missing_inputs,
            instructions=instructions,
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

        narrative = await run_validated_trade_narrative(
            project=project,
            target=profile,
            kind=self.kind,
            rft_context=rft_context,
            generation_brief=generation_brief,
            project_evidence=project_evidence,
            platform_knowledge=platform_knowledge,
            citation_index=citation_index,
            on_progress=on_progress,
            on_section_complete=publish_progressive_preview,
        )
        scope_items = (
            list(profile.baseline_scope)
            if profile.slug == "main_works"
            else narrative.requested_services or list(profile.baseline_scope)
        )
        scope_markdown = "\n".join(
            f"{index}. {clean_issue_language(_scope_item(item))}"
            for index, item in enumerate(scope_items, start=1)
        )
        programme_markdown = "\n".join(
            f"- {clean_issue_language(item)}" for item in narrative.programme
        )
        return (
            scaffold.replace(
                BACKGROUND_PLACEHOLDER,
                clean_issue_language(narrative.background),
            )
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
    generation_context: ProjectGenerationContext | None = None,
    auto_commit: bool = True,
    on_progress: ProgressPublisher | None = None,
) -> TradeProcurementResult:
    if kind not in {"rft", "rfq"}:
        raise ValueError("kind must be rft or rfq")
    document = TRADE_RFT_DOCUMENT if kind == "rft" else TRADE_RFQ_DOCUMENT
    result: ProcurementRequestResult = await draft_procurement_request(
        session,
        project=project,
        user_id=user_id,
        document=document,
        raw_target=package,
        max_pages=max_pages,
        instructions=instructions,
        generation_context=generation_context,
        auto_commit=auto_commit,
        sync_workspace=_sync_for_engine,
        on_progress=on_progress,
    )
    return TradeProcurementResult(
        draft=result.draft,
        package=result.target_name,
        kind=kind,
        source_trace=result.source_trace,
    )
