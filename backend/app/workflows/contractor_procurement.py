from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.draft_artifact import DraftArtifact
from app.database.project import Project
from app.projects.identity import classification_summary, resolve_project_identity
from app.workflows.procurement_request import (
    EvidenceQuery,
    ProcurementDocument,
    ProcurementTarget,
    draft_procurement_request,
)

WORKFLOW_TYPE_PREFIX = "contractor_eoi"
RUNTIME_NAME = "clerk-contractor-eoi"
KNOWLEDGE_WORKFLOW = "head-contractor-procurement"


@dataclass(frozen=True, slots=True)
class PackageProfile:
    name: str
    slug: str


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "main_works"


def normalise_package(package: str) -> PackageProfile:
    cleaned = " ".join(package.strip().split()) or "Main Works"
    return PackageProfile(name=cleaned, slug=_slugify(cleaned))


class ContractorEoiDocument(ProcurementDocument):
    document_key = WORKFLOW_TYPE_PREFIX
    workspace_subfolder = "02-procurement"
    filename_stem = "contractor_eoi"
    knowledge_workflow = KNOWLEDGE_WORKFLOW
    runtime_name = RUNTIME_NAME
    trace_tool_name = "draft_contractor_eoi_artifact"
    trace_generation_purpose = "Generated and saved the contractor EOI artefact."
    trace_evidence_purpose = "Gathered active-project evidence for the EOI basis."
    trace_guidance_purpose = "Gathered SiteWise head-contractor procurement guidance."

    def resolve_target(self, raw: str) -> ProcurementTarget:
        return normalise_package(raw)

    def title(self, target: ProcurementTarget) -> str:
        return f"Expression of Interest - {target.name}"

    def evidence_queries(
        self, target: ProcurementTarget
    ) -> tuple[EvidenceQuery, ...]:
        return (
            EvidenceQuery(
                "project_brief",
                "Project brief",
                "project brief owner objectives scope site constraints",
            ),
            EvidenceQuery(
                "scope_of_works",
                "Scope of works",
                "scope of works design drawings specifications trade breakdown",
            ),
            EvidenceQuery(
                "programme",
                "Programme",
                "programme milestones construction start completion sequencing",
            ),
            EvidenceQuery(
                "planning_pathway",
                "Planning pathway",
                "planning approval DA CC construction certificate conditions of consent",
            ),
            EvidenceQuery(
                "procurement_strategy",
                "Procurement strategy",
                "procurement strategy contract form AS 4000 head contractor tender",
            ),
        )

    def platform_query(self, target: ProcurementTarget) -> str:
        return (
            f"head contractor procurement expression of interest {target.name} "
            "shortlisting capability experience capacity returnables"
        )

    async def forecast(
        self,
        session: AsyncSession,
        *,
        project_id: uuid.UUID,
        target: ProcurementTarget,
    ) -> dict[str, Any]:
        return {
            "used": False,
            "reason": "EOI is unpriced; no fee benchmark applies.",
        }

    def assumptions_and_missing(
        self,
        *,
        project: Project,
        evidence: list[dict[str, Any]],
        forecast: dict[str, Any],
        target: ProcurementTarget,
    ) -> tuple[list[str], list[str]]:
        roles = {item["role"] for item in evidence}
        missing: list[str] = []
        if "scope_of_works" not in roles:
            missing.append("Scope of works / current design status.")
        if "programme" not in roles:
            missing.append("Indicative construction programme and key dates.")
        missing.extend(
            [
                "Intended contract form (e.g. AS 4000) and procurement route.",
                "Indicative value band (client to confirm; not published from the cost plan).",
                "EOI close date and time.",
                "Submission contact and lodgement method.",
            ]
        )
        assumptions = [
            "This is a client-issued Expression of Interest to shortlist a head "
            "contractor. It is not a tender, not an offer, and respondents are not "
            "asked to price the works.",
            "The client is not bound to shortlist, issue an RFT, or proceed, and "
            "respondents bear their own EOI costs.",
        ]
        return assumptions, missing

    def render(
        self,
        *,
        project: Project,
        target: ProcurementTarget,
        project_evidence: list[dict[str, Any]],
        platform_knowledge: list[dict[str, Any]],
        forecast: dict[str, Any],
        assumptions: list[str],
        missing_inputs: list[str],
        max_pages: int,
        instructions: str | None,
    ) -> str:
        state = getattr(project, "state", None) or "TBC"
        identity = resolve_project_identity(project, evidence=project_evidence)
        site_address = identity.get("site_address") or "TBC"
        client = identity.get("client") or "TBC"
        classification = classification_summary(project)
        overview_lines = [
            f"- Project: {project.title}",
            f"- Site address: {site_address}",
            f"- Client / owners: {client}",
            f"- Jurisdiction: {state}",
        ]
        if classification:
            overview_lines.append(f"- Project type: {classification}")
        overview_lines.extend(
            [
                "- Indicative value band: TBC by client before issue.",
                "- Intended procurement route / contract form: TBC by client before issue.",
                "- Indicative programme window: TBC by client before issue.",
            ]
        )
        sections = [
            f"# Expression of Interest - {target.name}",
            "",
            "## Invitation",
            f"- {project.title} invites Expressions of Interest for the {target.name} package.",
            "- This EOI is issued to shortlist capable contractors. It is not a tender or an offer.",
            "",
            "## Project overview",
            *overview_lines,
            "",
            "## Scope of the works package",
            "- Describe the in-scope main works and note separate consultant and trade packages.",
            *[f"- {line}" for line in _scope_lines(project_evidence)],
            "",
            "## EOI returnables",
            "- Company profile, structure, and financial capacity (turnover, references).",
            "- Comparable project experience with referees.",
            "- Proposed key personnel and project team.",
            "- Current workload and capacity to resource this project.",
            "- High-level delivery methodology and programme approach.",
            "- Licences, insurances, and accreditations (builder's licence, safety, quality).",
            "- Declaration of any conflicts of interest.",
            "",
            "## Shortlisting basis",
            "- EOIs are assessed on capability, relevant experience, capacity, and financial standing.",
            "- Price is not sought at EOI stage; shortlisted respondents may be invited to tender (RFT).",
            "",
            "## Conditions of EOI",
            *[f"- {line}" for line in assumptions[:2]],
            "- The client may vary, suspend, or discontinue this process at any time.",
            "",
            "## Submission instructions",
            "- Submit the EOI response to the client-nominated contact in PDF format.",
            "- Close date/time and lodgement method: TBC by client before issue.",
            "",
            _basis_footer(project_evidence, platform_knowledge, missing_inputs),
        ]
        if instructions and instructions.strip():
            sections.insert(
                -1,
                f"- Additional instruction: {' '.join(instructions.split())}",
            )
        return "\n".join(sections).rstrip() + "\n"


CONTRACTOR_EOI_DOCUMENT = ContractorEoiDocument()


@dataclass(frozen=True, slots=True)
class ContractorEoiResult:
    draft: DraftArtifact
    package: str
    source_trace: dict[str, Any]


async def draft_contractor_eoi_artifact(
    session: AsyncSession,
    *,
    project: Project,
    user_id: uuid.UUID,
    package: str = "Main Works",
    max_pages: int = 1,
    instructions: str | None = None,
    auto_commit: bool = True,
) -> ContractorEoiResult:
    result = await draft_procurement_request(
        session,
        project=project,
        user_id=user_id,
        document=CONTRACTOR_EOI_DOCUMENT,
        raw_target=package,
        max_pages=max_pages,
        instructions=instructions,
        auto_commit=auto_commit,
    )
    return ContractorEoiResult(
        draft=result.draft,
        package=result.target_name,
        source_trace=result.source_trace,
    )


def _scope_lines(evidence: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    lines: list[str] = []
    for item in evidence:
        if item.get("role") != "scope_of_works":
            continue
        path = item.get("relative_path") or item.get("filename")
        if path and path not in seen:
            seen.add(path)
            lines.append(f"Refer scope evidence: {path}")
    return lines or ["Scope of works to be issued to shortlisted respondents."]


def _basis_footer(
    evidence: list[dict[str, Any]],
    knowledge: list[dict[str, Any]],
    missing_inputs: list[str],
) -> str:
    docs = ", ".join(
        sorted(
            {
                item.get("filename") or item.get("relative_path") or ""
                for item in evidence
            }
            - {""}
        )
    ) or "none found"
    guidance = ", ".join(
        item.get("title", "") for item in knowledge[:2] if item.get("title")
    ) or "none found"
    missing = "; ".join(missing_inputs[:4])
    return (
        f"Basis used: project docs: {docs}. Platform guidance: {guidance}. "
        f"Missing inputs: {missing}."
    )
