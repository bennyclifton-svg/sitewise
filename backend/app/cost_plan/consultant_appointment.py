"""Adopt a selected consultant fee proposal into Cost Plan and PMP.

Pi must not hunt artefact schema for this. Discipline is already classified on
the fee proposal; this module matches that label to the Cost Plan Approved
Contract column (`committed`) and the PMP Consultants register.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cost_plan.dependencies import dependency_snapshot as cost_dependency_snapshot
from app.cost_plan.schemas import CostItemInput
from app.cost_plan.service import (
    CostPlanNotFound,
    get_cost_plan,
    upsert_cost_item,
)
from app.cost_plan.workbook_rebuild import schedule_cost_plan_workbook_rebuild
from app.database.draft_artifacts import get_latest_draft_artifact
from app.database.project import Project
from app.database.source_document import SourceDocument
from app.projects.artefact_adapters import revise_workflow_artefact
from app.projects.consultant_facts import (
    APPOINTED_STATUS as APPOINTED_STATUS,
    map_discipline_to_register_label,
    object_id_for_discipline,
)
from app.projects.project_knowledge import (
    SharedProjectObjectUpdate,
    get_shared_project_object,
    upsert_shared_project_object,
    write_shared_project_object,
)
from app.projects.snapshot import get_project_snapshot
from app.sitewise.consultant_register import apply_consultant_register_facts
from ingest.consultant_firm import extract_issuing_firm_from_text, is_noise_firm_candidate

FeeSource = Literal["proposal", "nominated"]

_TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
_MONEY_RE = re.compile(r"-?\d[\d,]*(?:\.\d{1,2})?")
_REFERENCE_RE = re.compile(
    r"\*\*Our reference\*\*\s*\|\s*(.+?)\s*\|",
    re.IGNORECASE,
)
_DISCIPLINE_CELL_RE = re.compile(
    r"\*\*Discipline\*\*\s*\|\s*(.+?)\s*\|",
    re.IGNORECASE,
)
_HEADING_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_SUBHEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

_COST_PLAN_TOKENS: dict[str, tuple[str, ...]] = {
    "Architect": ("architect",),
    "Structural Engineer": ("structural",),
    "Town Planner": ("town planner", "town planning"),
    "Civil / stormwater": ("civil", "stormwater"),
    "Civil Engineer": ("civil", "stormwater"),
    "Building Certifier": ("certif", "principal certifier"),
    "Geotechnical Engineer": ("geotech",),
    "Surveyor": ("surveyor",),
    "Services Engineer (Hydraulic)": ("hydraulic", "wastewater"),
    "BASIX / energy assessor": ("basix", "energy assess"),
    "Quantity Surveyor": ("quantity survey", "cost advisory", " qs "),
    "Heritage Consultant": ("heritage",),
    "Landscape Architect": ("landscape",),
    "Acoustic Consultant": ("acoustic",),
    "Fire Engineer": ("fire",),
}

_ARCHITECT_CATEGORIES = ("fee", "consult")


@dataclass(frozen=True, slots=True)
class FeeProposalAppointment:
    discipline: str
    firm: str
    fee_ex_gst: Decimal
    proposal_reference: str | None
    source_document_id: uuid.UUID | None
    relative_path: str
    filename: str
    fee_source: FeeSource


@dataclass(frozen=True, slots=True)
class ConsultantAppointmentResult:
    discipline: str
    firm: str
    fee_ex_gst: Decimal
    fee_source: FeeSource
    proposal_reference: str | None
    cost_plan_item_key: str
    cost_plan_version: int
    approved_contract: Decimal
    pmp_updated: bool
    pmp_version: int | None
    source_document_id: uuid.UUID | None


class ConsultantAppointmentError(ValueError):
    pass


def format_appointed_fee(amount: Decimal) -> str:
    return f"${amount:,.2f} ex GST"


def extract_fee_proposal(
    document: SourceDocument,
    *,
    nominated_fee_ex_gst: Decimal | None = None,
    firm: str | None = None,
    discipline: str | None = None,
) -> FeeProposalAppointment:
    metadata = (
        document.document_metadata if isinstance(document.document_metadata, dict) else {}
    )
    content = document.normalized_content or ""
    resolved_discipline = _resolve_discipline(metadata, content, discipline)
    resolved_firm = _resolve_firm(metadata, content, document.filename, firm)
    if nominated_fee_ex_gst is not None:
        fee = nominated_fee_ex_gst
        fee_source: FeeSource = "nominated"
    else:
        extracted = _extract_fee_ex_gst(content)
        if extracted is None:
            raise ConsultantAppointmentError(
                "Could not read an ex-GST professional fee from the proposal. "
                "Nominate the engagement sum and retry."
            )
        fee = extracted
        fee_source = "proposal"
    return FeeProposalAppointment(
        discipline=resolved_discipline,
        firm=resolved_firm,
        fee_ex_gst=fee,
        proposal_reference=_extract_reference(content),
        source_document_id=getattr(document, "id", None),
        relative_path=document.relative_path or document.filename,
        filename=document.filename,
        fee_source=fee_source,
    )


def match_cost_plan_item(
    items: list[CostItemInput],
    discipline: str,
) -> CostItemInput | None:
    tokens = _tokens_for(discipline)
    preferred_categories = (
        _ARCHITECT_CATEGORIES if _normalize(discipline) == "architect" else ("consult",)
    )
    for category_markers in (preferred_categories, ("consult", "fee")):
        for item in items:
            if _is_authority_fee_row(item):
                continue
            if not any(marker in item.category.lower() for marker in category_markers):
                continue
            label = f" {_normalize(item.item)} "
            if any(token in label for token in tokens):
                return item
    return None


def apply_appointment_to_cost_items(
    items: list[CostItemInput],
    *,
    discipline: str,
    firm: str,
    fee_ex_gst: Decimal,
    basis: str,
) -> tuple[list[CostItemInput], str]:
    existing = match_cost_plan_item(items, discipline)
    if existing is None:
        used_codes = {item.cost_code for item in items}
        used_keys = {item.item_key for item in items}
        item_key = _unique_key(f"appointed:{_slug(discipline)}", used_keys)
        created = CostItemInput(
            item_key=item_key,
            cost_code=_next_consultant_code(used_codes),
            category="Consultants",
            item=discipline,
            budget=fee_ex_gst,
            committed=fee_ex_gst,
            forecast=fee_ex_gst,
            basis=basis,
            source_refs=[],
            confidence=Decimal("1"),
            status="confirmed",
        )
        return [*items, created], created.item_key

    forecast = max(fee_ex_gst, existing.paid)
    updated = existing.model_copy(
        update={
            "committed": fee_ex_gst,
            "forecast": forecast,
            "basis": basis,
            "status": "confirmed",
            "locked": False,
        }
    )
    replaced = [
        updated if item.item_key == existing.item_key else item for item in items
    ]
    return replaced, updated.item_key


def apply_appointment_to_consultant_facts(
    project: Project,
    *,
    discipline: str,
    firm: str,
    fee_ex_gst: Decimal,
    evidence_path: str | None = None,
) -> None:
    object_id = object_id_for_discipline(discipline)
    existing = get_shared_project_object(
        project, kind="consultant", object_id=object_id
    )
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id=object_id,
        update=SharedProjectObjectUpdate(
            expected_revision=existing.revision if existing else 0,
            value=_appointment_fact_value(
                existing=existing.value if existing else None,
                discipline=discipline,
                firm=firm,
                fee_ex_gst=fee_ex_gst,
                evidence_path=evidence_path,
            ),
        ),
        source="user",
    )


def _appointment_fact_value(
    *,
    existing: dict[str, Any] | None,
    discipline: str,
    firm: str,
    fee_ex_gst: Decimal,
    evidence_path: str | None,
) -> dict[str, Any]:
    paths: list[str] = []
    if existing and isinstance(existing.get("evidence_paths"), list):
        paths = [str(path) for path in existing["evidence_paths"] if path]
    if evidence_path and evidence_path not in paths:
        paths.append(evidence_path)
    return {
        "discipline": discipline,
        "firm": firm,
        "name": firm,
        "status": APPOINTED_STATUS,
        "fee": format_appointed_fee(fee_ex_gst),
        "evidence_paths": paths,
        "evidence_kind": "fee_proposal",
    }


def apply_appointment_to_pmp_markdown(markdown: str, *, project: Project) -> str:
    return apply_consultant_register_facts(markdown, project=project)


def appointment_basis(proposal: FeeProposalAppointment) -> str:
    reference = proposal.proposal_reference or proposal.filename
    return f"Appointed ({proposal.firm}); fee proposal {reference}"


async def appoint_consultant(
    session: AsyncSession,
    *,
    project: Project,
    author_user_id: uuid.UUID,
    source_document_id: uuid.UUID | None = None,
    firm: str | None = None,
    discipline: str | None = None,
    nominated_fee_ex_gst: Decimal | None = None,
    selected_source_document_ids: list[uuid.UUID] | None = None,
) -> ConsultantAppointmentResult:
    """Resolve a fee proposal and persist Cost Plan + PMP appointment updates."""
    document = await _resolve_document(
        session,
        project_id=project.id,
        source_document_id=source_document_id,
        selected_source_document_ids=selected_source_document_ids,
        firm=firm,
        discipline=discipline,
    )
    if document is not None:
        proposal = extract_fee_proposal(
            document,
            nominated_fee_ex_gst=nominated_fee_ex_gst,
            firm=firm,
            discipline=discipline,
        )
    else:
        proposal = _appointment_from_nomination(
            firm=firm,
            discipline=discipline,
            nominated_fee_ex_gst=nominated_fee_ex_gst,
        )

    try:
        state = await get_cost_plan(
            session,
            project_id=project.id,
            owner_user_id=project.owner_user_id,
        )
    except CostPlanNotFound as exc:
        raise ConsultantAppointmentError(
            "Create a Cost Plan before appointing a consultant."
        ) from exc

    items, item_key = apply_appointment_to_cost_items(
        list(state.items),
        discipline=proposal.discipline,
        firm=proposal.firm,
        fee_ex_gst=proposal.fee_ex_gst,
        basis=appointment_basis(proposal),
    )
    appointed_item = next(item for item in items if item.item_key == item_key)
    if proposal.source_document_id is not None:
        appointed_item = appointed_item.model_copy(
            update={
                "source_refs": [
                    {
                        "type": "project_evidence",
                        "document_id": str(proposal.source_document_id),
                        "ref": proposal.relative_path,
                        "filename": proposal.filename,
                        "proposal_reference": proposal.proposal_reference,
                        "supplier": proposal.firm,
                        "amount_ex_gst": str(proposal.fee_ex_gst),
                    }
                ]
            }
        )

    snapshot = await get_project_snapshot(
        session,
        project_id=project.id,
        owner_user_id=project.owner_user_id,
    )
    result = await upsert_cost_item(
        session,
        project=project,
        author_user_id=author_user_id,
        expected_base_version=state.version,
        item=appointed_item,
        current_snapshot=None,
        dependency_snapshot=cost_dependency_snapshot(
            snapshot,
            model_version=state.dependency_snapshot.model_version,
            prompt_version=state.dependency_snapshot.prompt_version,
            runtime_version="clerk-consultant-appointment-v1",
        ),
        actor_source="agent_consultant_appointment",
    )
    schedule_cost_plan_workbook_rebuild(project.id, result.state.version)

    object_id = object_id_for_discipline(proposal.discipline)
    existing_fact = get_shared_project_object(
        project, kind="consultant", object_id=object_id
    )
    fact_value = _appointment_fact_value(
        existing=existing_fact.value if existing_fact else None,
        discipline=proposal.discipline,
        firm=proposal.firm,
        fee_ex_gst=proposal.fee_ex_gst,
        evidence_path=proposal.relative_path or None,
    )
    await write_shared_project_object(
        session,
        project=project,
        kind="consultant",
        object_id=object_id,
        update=SharedProjectObjectUpdate(
            expected_revision=existing_fact.revision if existing_fact else 0,
            value=fact_value,
        ),
        source="user",
    )

    pmp_updated = False
    pmp_version: int | None = None
    draft = await get_latest_draft_artifact(
        session,
        project_id=project.id,
        workflow_type="create_pmp",
    )
    if draft is not None:
        patched = apply_appointment_to_pmp_markdown(
            draft.content_markdown, project=project
        )
        if patched != draft.content_markdown:
            updated_draft = await revise_workflow_artefact(
                session,
                project=project,
                draft=draft,
                expected_base_version=draft.version,
                author_user_id=author_user_id,
                content_markdown=patched,
                actor_source="ai_consultant_appointment",
            )
            pmp_updated = True
            pmp_version = updated_draft.version
        else:
            pmp_version = draft.version

    return ConsultantAppointmentResult(
        discipline=proposal.discipline,
        firm=proposal.firm,
        fee_ex_gst=proposal.fee_ex_gst,
        fee_source=proposal.fee_source,
        proposal_reference=proposal.proposal_reference,
        cost_plan_item_key=item_key,
        cost_plan_version=result.state.version,
        approved_contract=proposal.fee_ex_gst,
        pmp_updated=pmp_updated,
        pmp_version=pmp_version,
        source_document_id=proposal.source_document_id,
    )


def _appointment_from_nomination(
    *,
    firm: str | None,
    discipline: str | None,
    nominated_fee_ex_gst: Decimal | None,
) -> FeeProposalAppointment:
    if not firm or not discipline or nominated_fee_ex_gst is None:
        raise ConsultantAppointmentError(
            "Pass a fee-proposal source_document_id, or firm, discipline, and "
            "nominated_fee_ex_gst."
        )
    mapped = map_discipline_to_register_label(discipline) or discipline.strip()
    return FeeProposalAppointment(
        discipline=mapped,
        firm=firm.strip(),
        fee_ex_gst=nominated_fee_ex_gst,
        proposal_reference=None,
        source_document_id=None,
        relative_path="",
        filename="",
        fee_source="nominated",
    )


async def _resolve_document(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    source_document_id: uuid.UUID | None,
    selected_source_document_ids: list[uuid.UUID] | None,
    firm: str | None,
    discipline: str | None,
) -> SourceDocument | None:
    if source_document_id is not None:
        document = await session.get(SourceDocument, source_document_id)
        if document is None or document.project_id != project_id:
            raise ConsultantAppointmentError(
                "The named fee proposal is not in this project."
            )
        return document

    candidates: list[SourceDocument] = []
    if selected_source_document_ids:
        rows = (
            await session.execute(
                select(SourceDocument).where(
                    SourceDocument.project_id == project_id,
                    SourceDocument.id.in_(selected_source_document_ids),
                )
            )
        ).scalars().all()
        candidates = list(rows)
        if len(candidates) == 1:
            return candidates[0]
        fee_proposals = [row for row in candidates if _looks_like_fee_proposal(row)]
        if len(fee_proposals) == 1:
            return fee_proposals[0]
        if len(fee_proposals) > 1:
            raise ConsultantAppointmentError(
                "Multiple selected fee proposals; pass source_document_id for the "
                "one being appointed."
            )

    if firm or discipline:
        listing = (
            await session.execute(
                select(SourceDocument).where(SourceDocument.project_id == project_id)
            )
        ).scalars().all()
        matches = [
            row
            for row in listing
            if _looks_like_fee_proposal(row) and _document_matches(row, firm, discipline)
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            names = ", ".join(row.filename for row in matches[:5])
            raise ConsultantAppointmentError(
                "Multiple fee proposals match that firm or discipline "
                f"({names}). Pass source_document_id."
            )
        if matches:
            return matches[0]
    return None


def _looks_like_fee_proposal(document: SourceDocument) -> bool:
    blob = _normalize(
        f"{document.document_class} {document.filename} {document.relative_path}"
    )
    return "fee proposal" in blob or "fee_proposal" in blob or "quote" in blob


def _document_matches(
    document: SourceDocument,
    firm: str | None,
    discipline: str | None,
) -> bool:
    metadata = (
        document.document_metadata if isinstance(document.document_metadata, dict) else {}
    )
    if discipline:
        mapped = map_discipline_to_register_label(discipline)
        document_discipline = map_discipline_to_register_label(
            str(metadata.get("discipline") or "")
        )
        haystack = _normalize(
            f"{metadata.get('discipline') or ''} {document.filename} {document.relative_path}"
        )
        if mapped and document_discipline and mapped != document_discipline:
            if _normalize(mapped) not in haystack and _normalize(discipline) not in haystack:
                return False
        elif _normalize(discipline) not in haystack and (
            not mapped or _normalize(mapped) not in haystack
        ):
            return False
    if firm:
        haystack = _normalize(
            f"{metadata.get('issuing_firm') or ''} {document.filename} "
            f"{document.normalized_content[:2000]}"
        )
        if _normalize(firm) not in haystack:
            return False
    return True


def _resolve_discipline(
    metadata: dict[str, Any],
    content: str,
    override: str | None,
) -> str:
    for candidate in (
        override,
        str(metadata.get("discipline") or "") or None,
        _match_value(_DISCIPLINE_CELL_RE, content),
        _heading_discipline(content),
    ):
        mapped = map_discipline_to_register_label(candidate)
        if mapped:
            return mapped
    raise ConsultantAppointmentError(
        "The fee proposal has no classified discipline. Pass discipline explicitly."
    )


def _resolve_firm(
    metadata: dict[str, Any],
    content: str,
    filename: str,
    override: str | None,
) -> str:
    if override and override.strip() and not is_noise_firm_candidate(override):
        return override.strip()
    meta_firm = str(metadata.get("issuing_firm") or "").strip()
    if meta_firm and not is_noise_firm_candidate(meta_firm):
        return meta_firm
    heading = _first_subheading(content)
    if heading and not is_noise_firm_candidate(heading):
        return heading
    extracted = extract_issuing_firm_from_text(content)
    if extracted:
        return extracted
    stem = Path(filename).stem.replace("-", " ").strip()
    if stem:
        return stem
    raise ConsultantAppointmentError("Could not identify the consultant firm.")


def _heading_discipline(content: str) -> str | None:
    heading = _first_heading(content)
    if not heading:
        return None
    match = re.search(r"fee proposal\s+[—-]\s+(.+)$", heading, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _first_heading(content: str) -> str:
    match = _HEADING_RE.search(content)
    return _strip_markdown(match.group(1)) if match else ""


def _first_subheading(content: str) -> str:
    match = _SUBHEADING_RE.search(content)
    return _strip_markdown(match.group(1)) if match else ""


def _extract_reference(content: str) -> str | None:
    return _match_value(_REFERENCE_RE, content)


def _extract_fee_ex_gst(content: str) -> Decimal | None:
    for cells in _table_rows(content):
        label = _normalize(" ".join(cells[:-1]))
        if "professional fees excl gst" in label or "professional fees excluding gst" in label:
            amount = _money(cells[-1])
            if amount is not None:
                return amount
    fee_section = _markdown_section(content, "fee") or content
    for cells in _table_rows(fee_section):
        label = _normalize(cells[0] if cells else "")
        if label == "total" or label.startswith("total "):
            amount = _money(cells[-1])
            if amount is not None:
                return amount
    return None


def _table_rows(markdown: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in markdown.splitlines():
        stripped = raw.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(_TABLE_SEPARATOR_RE.match(cell.strip()) for cell in cells):
            continue
        rows.append(cells)
    return rows


def _markdown_section(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    target = heading.lower()
    collected: list[str] = []
    active = False
    level = 0
    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line.strip())
        if match:
            current_level = len(match.group(1))
            current = _normalize(match.group(2))
            if active and current_level <= level:
                break
            if current == target:
                active = True
                level = current_level
                continue
        if active:
            collected.append(line)
    return "\n".join(collected)


def _money(value: str) -> Decimal | None:
    match = _MONEY_RE.search(_strip_markdown(value).replace("$", ""))
    if match is None:
        return None
    try:
        return Decimal(match.group(0).replace(",", "")).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _tokens_for(discipline: str) -> tuple[str, ...]:
    mapped = map_discipline_to_register_label(discipline) or discipline
    if mapped in _COST_PLAN_TOKENS:
        return _COST_PLAN_TOKENS[mapped]
    normalized = _normalize(mapped)
    if normalized in {key.lower() for key in _COST_PLAN_TOKENS}:
        for key, tokens in _COST_PLAN_TOKENS.items():
            if key.lower() == normalized:
                return tokens
    return (normalized,)


def _is_authority_fee_row(item: CostItemInput) -> bool:
    label = _normalize(item.item)
    return "authority" in label or (
        "planning" in label and "certification" in label
    )


def _next_consultant_code(used: set[str]) -> str:
    for number in range(5, 40):
        code = str(number)
        if code not in used:
            return code
    index = 1
    while f"C.{index}" in used:
        index += 1
    return f"C.{index}"


def _unique_key(preferred: str, used: set[str]) -> str:
    if preferred not in used:
        return preferred
    index = 2
    while f"{preferred}-{index}" in used:
        index += 1
    return f"{preferred}-{index}"


def _match_value(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return _strip_markdown(match.group(1)) if match else None


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _strip_markdown(value).lower()).strip()


def _strip_markdown(value: str) -> str:
    return re.sub(r"(?:\*\*|__|`)", "", value).strip()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
