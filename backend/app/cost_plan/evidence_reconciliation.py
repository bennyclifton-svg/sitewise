"""Extract received cost proposals and map them onto a typed Cost Plan.

The model is deliberately narrow: source documents propose values, typed Cost
Plan revisions remain reviewable, and Python verifies every quoted total before
it can participate in arithmetic.
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.cost_plan.schemas import CostItemInput, CostPlanState
from app.sitewise.pmp_corpus import list_current_pmp_corpus_documents

ProposalKind = Literal[
    "architecture",
    "structural",
    "hydraulic",
    "cost_advisory",
    "main_works",
]

_PROPOSAL_REFERENCE_RE = re.compile(
    r"^\*\*Proposal reference:\*\*\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE
)
_DATE_RE = re.compile(r"^\*\*Date:\*\*\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_VALID_UNTIL_RE = re.compile(
    r"^\*\*(?:Valid until|Tender validity):\*\*\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_SUPPLIER_RE = re.compile(
    r"^\*\*([^*\n]*(?:Pty\s+Ltd|Limited))\*\*\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")


@dataclass(frozen=True, slots=True)
class CostEvidenceDocument:
    id: uuid.UUID
    filename: str
    relative_path: str
    content: str


@dataclass(frozen=True, slots=True)
class ProposalLine:
    label: str
    amount_ex_gst: Decimal


@dataclass(frozen=True, slots=True)
class ReceivedCostProposal:
    kind: ProposalKind
    source_document_id: uuid.UUID
    filename: str
    relative_path: str
    supplier: str
    proposal_reference: str
    proposal_date: str | None
    valid_until: str | None
    total_ex_gst: Decimal
    line_items: tuple[ProposalLine, ...]


@dataclass(frozen=True, slots=True)
class CostEvidenceReconciliation:
    proposed_items: tuple[CostItemInput, ...]
    received_proposals: tuple[ReceivedCostProposal, ...]
    issues: tuple[str, ...]


async def load_cost_evidence_documents(
    session: AsyncSession, *, project_id: uuid.UUID
) -> list[CostEvidenceDocument]:
    """Load the active project's ingested documents for cost reconciliation."""
    listing = await list_current_pmp_corpus_documents(
        session,
        project_id=project_id,
    )
    return [
        CostEvidenceDocument(
            id=row.id,
            filename=row.filename,
            relative_path=row.relative_path,
            content=row.normalized_content,
        )
        for row in listing.documents
    ]


def build_cost_evidence_reconciliation(
    base: CostPlanState,
    documents: list[CostEvidenceDocument],
) -> CostEvidenceReconciliation:
    """Return reviewable typed item proposals derived from reconciled source totals."""
    received: list[ReceivedCostProposal] = []
    issues: list[str] = []
    for document in documents:
        proposal, issue = _extract_received_proposal(document)
        if proposal is not None:
            received.append(proposal)
        if issue is not None:
            issues.append(issue)

    by_kind: dict[ProposalKind, list[ReceivedCostProposal]] = defaultdict(list)
    for proposal in received:
        by_kind[proposal.kind].append(proposal)

    proposed_by_key: dict[str, CostItemInput] = {}
    for kind in ("architecture", "structural", "hydraulic", "cost_advisory"):
        candidates = by_kind[kind]  # type: ignore[index]
        if len(candidates) > 1:
            issues.append(
                f"Multiple {kind.replace('_', ' ')} fee proposals are on file; "
                "select the applicable proposal before updating that Cost Plan row."
            )
            continue
        if not candidates:
            continue
        item = _consultant_item(base, candidates[0])
        proposed_by_key[item.item_key] = item

    main_works = by_kind["main_works"]
    if len(main_works) > 1:
        issues.append(
            "Multiple main works proposals are on file; Clerk will not choose a builder "
            "or silently replace the construction budget."
        )
    elif main_works:
        for item in _main_works_items(base, main_works[0], issues):
            proposed_by_key[item.item_key] = item

    proposed_items = tuple(
        sorted(proposed_by_key.values(), key=lambda item: _natural_key(item.cost_code))
    )
    return CostEvidenceReconciliation(
        proposed_items=proposed_items,
        received_proposals=tuple(received),
        issues=tuple(issues),
    )


def _extract_received_proposal(
    document: CostEvidenceDocument,
) -> tuple[ReceivedCostProposal | None, str | None]:
    heading = _first_heading(document.content)
    heading_lower = heading.lower()
    filename_lower = document.filename.lower()
    is_candidate = (
        "fee proposal" in heading_lower
        or "building proposal" in heading_lower
        or "fee-proposal" in filename_lower
        or "building-proposal" in filename_lower
    )
    if not is_candidate:
        return None, None

    kind = _proposal_kind(heading)
    if kind is None:
        return (
            None,
            f"Could not classify received cost proposal {document.relative_path}.",
        )

    supplier = _match_value(_SUPPLIER_RE, document.content) or document.filename
    reference = _match_value(_PROPOSAL_REFERENCE_RE, document.content)
    if reference is None:
        return None, f"Proposal reference is missing from {document.relative_path}."

    section_heading = "Works breakdown" if kind == "main_works" else "Professional fee"
    section = _markdown_section(document.content, section_heading)
    if not section:
        return None, (
            f"{document.relative_path} has no {section_heading!r} section; "
            "no Cost Plan value was proposed."
        )

    total_labels = (
        ("fixed contract sum excluding gst",)
        if kind == "main_works"
        else ("total professional fee",)
    )
    total = _labelled_total(section, total_labels)
    if total is None:
        return None, (
            f"Could not find an explicit ex-GST proposal total in {document.relative_path}."
        )

    lines = _proposal_lines(section, kind=kind)
    if not lines:
        return None, f"No priced proposal lines were found in {document.relative_path}."
    line_total = sum((line.amount_ex_gst for line in lines), Decimal("0"))
    if line_total != total:
        return None, (
            f"Proposal total in {document.relative_path} does not reconcile: "
            f"line items {line_total:.2f}, stated total {total:.2f}."
        )

    return (
        ReceivedCostProposal(
            kind=kind,
            source_document_id=document.id,
            filename=document.filename,
            relative_path=document.relative_path,
            supplier=supplier,
            proposal_reference=reference,
            proposal_date=_match_value(_DATE_RE, document.content),
            valid_until=_match_value(_VALID_UNTIL_RE, document.content),
            total_ex_gst=total,
            line_items=tuple(lines),
        ),
        None,
    )


def _proposal_kind(heading: str) -> ProposalKind | None:
    normalized = _normalize(heading)
    if "fixed price building proposal" in normalized or "main works" in normalized:
        return "main_works"
    if "architect" in normalized:
        return "architecture"
    if "structural" in normalized:
        return "structural"
    if "hydraulic" in normalized:
        return "hydraulic"
    if "quantity surveying" in normalized or "cost advisory" in normalized:
        return "cost_advisory"
    return None


def _consultant_item(
    base: CostPlanState, proposal: ReceivedCostProposal
) -> CostItemInput:
    labels: dict[ProposalKind, tuple[str, tuple[str, ...], str]] = {
        "architecture": ("Architect / PM", ("architect",), "3"),
        "structural": ("Structural engineer", ("structural",), "4"),
        "hydraulic": (
            "Hydraulic / wastewater",
            ("hydraulic", "wastewater", "plumbing"),
            "4.1",
        ),
        "cost_advisory": (
            "Quantity surveyor / cost advisory",
            ("quantity survey", "cost advisory", "cost manager", " qs "),
            "4.2",
        ),
        "main_works": ("Main works", ("main works",), "MW"),
    }
    label, tokens, preferred_code = labels[proposal.kind]
    category_markers = ("consult", "fee") if proposal.kind == "architecture" else ("consult",)
    existing = _find_item(
        base.items,
        category_markers=category_markers,
        tokens=tokens,
    )
    if existing is None:
        used_codes = {item.cost_code for item in base.items}
        cost_code = _available_code(preferred_code, used_codes)
        existing = CostItemInput(
            item_key=f"received-proposal:{proposal.kind}",
            cost_code=cost_code,
            category="Consultants",
            item=label,
            budget=proposal.total_ex_gst,
            forecast=proposal.total_ex_gst,
            basis=_proposal_basis(proposal, "fee"),
            source_refs=[_source_ref(proposal)],
            confidence=Decimal("1"),
            status="proposed",
        )
    return _revised_item(
        existing,
        amount=proposal.total_ex_gst,
        basis=_proposal_basis(proposal, "fee"),
        source_refs=[_source_ref(proposal)],
    )


def _main_works_items(
    base: CostPlanState,
    proposal: ReceivedCostProposal,
    issues: list[str],
) -> list[CostItemInput]:
    construction = [item for item in base.items if "construct" in item.category.lower()]
    if not construction:
        issues.append(
            "The Cost Plan has no construction rows to reconcile with the main works proposal."
        )
        return []

    grouped: dict[str, list[ProposalLine]] = defaultdict(list)
    for line in proposal.line_items:
        grouped[_main_works_target(line.label)].append(line)

    proposed: dict[str, CostItemInput] = {}
    for current in construction:
        proposed[current.item_key] = _revised_item(
            current,
            amount=Decimal("0"),
            basis=(
                f"Superseded by received main works proposal "
                f"{proposal.proposal_reference}; no separate allocation"
            ),
            source_refs=[_source_ref(proposal)],
        )

    used_codes = {item.cost_code for item in base.items}
    for target, lines in grouped.items():
        amount = sum((line.amount_ex_gst for line in lines), Decimal("0"))
        tokens = _target_tokens(target)
        existing = _find_item(
            construction,
            category_markers=("construct",),
            tokens=tokens,
        )
        source_ref = _source_ref(proposal)
        source_ref["mapped_line_items"] = [
            {"label": line.label, "amount_ex_gst": str(line.amount_ex_gst)}
            for line in lines
        ]
        basis = _proposal_basis(
            proposal,
            "main works",
            mapped_labels=[line.label for line in lines],
        )
        if existing is None:
            preferred = "13.1" if target == "Finishes and external works" else "MW.1"
            code = _available_code(preferred, used_codes)
            used_codes.add(code)
            item = CostItemInput(
                item_key=f"received-proposal:main-works:{_slug(target)}",
                cost_code=code,
                category="Construction",
                item=target,
                budget=amount,
                forecast=amount,
                basis=basis,
                source_refs=[source_ref],
                confidence=Decimal("1"),
                status="proposed",
            )
        else:
            item = _revised_item(
                existing,
                amount=amount,
                basis=basis,
                source_refs=[source_ref],
            )
        proposed[item.item_key] = item

    proposed_total = sum((item.budget or Decimal("0")) for item in proposed.values())
    if proposed_total != proposal.total_ex_gst:
        issues.append(
            "Mapped main works rows do not reconcile to the received proposal total; "
            "construction changes were withheld."
        )
        return []
    return list(proposed.values())


def _main_works_target(label: str) -> str:
    normalized = _normalize(label)
    if "home warranty" in normalized or "contract administration" in normalized:
        return "Preliminaries"
    if "preliminaries" in normalized or "site establishment" in normalized:
        return "Preliminaries"
    if (
        "demolition" in normalized
        or "excavation" in normalized
        or "siteworks" in normalized
    ):
        return "Siteworks"
    if "footings" in normalized or "slab" in normalized:
        return "Footings and slab"
    if "structural steel" in normalized or "framing" in normalized:
        return "Framing"
    if "external doors" in normalized or "garage door" in normalized:
        return "External envelope and lockup"
    if "roof" in normalized or "cladding" in normalized or "glazing" in normalized:
        return "External envelope and lockup"
    if "joinery" in normalized or "kitchen" in normalized or "bathrooms" in normalized:
        return "Kitchen and bathrooms"
    if (
        "rough in" in normalized
        or "mechanical" in normalized
        or "services" in normalized
    ):
        return "Building services"
    if (
        "external works" in normalized
        or "hand over" in normalized
        or "handover" in normalized
    ):
        return "Finishes and external works"
    return label.strip()


def _target_tokens(target: str) -> tuple[str, ...]:
    return {
        "Preliminaries": ("prelim",),
        "Siteworks": ("sitework", "demolition"),
        "Footings and slab": ("footing", "slab"),
        "Framing": ("framing", "frame"),
        "External envelope and lockup": ("external envelope", "envelope", "lockup"),
        "Kitchen and bathrooms": ("kitchen", "bathroom"),
        "Building services": ("building services", "services"),
        "Finishes and external works": ("finishes", "external works"),
    }.get(target, (_normalize(target),))


def _find_item(
    items: list[CostItemInput],
    *,
    category_markers: tuple[str, ...],
    tokens: tuple[str, ...],
) -> CostItemInput | None:
    for item in items:
        if not any(marker in item.category.lower() for marker in category_markers):
            continue
        label = f" {_normalize(item.item)} "
        if any(token in label for token in tokens):
            return item
    return None


def _revised_item(
    item: CostItemInput,
    *,
    amount: Decimal,
    basis: str,
    source_refs: list[dict[str, object]],
) -> CostItemInput:
    forecast = max(amount, item.paid, item.committed)
    return CostItemInput.model_validate(
        {
            **item.model_dump(mode="python"),
            "budget": amount,
            "forecast": forecast,
            "basis": basis,
            "source_refs": source_refs,
            "confidence": Decimal("1"),
            "status": "proposed",
            "locked": False,
            "quantity": None,
            "unit": None,
            "rate": None,
        }
    )


def _proposal_basis(
    proposal: ReceivedCostProposal,
    subject: str,
    *,
    mapped_labels: list[str] | None = None,
) -> str:
    detail = f"Received {subject} proposal {proposal.proposal_reference} from {proposal.supplier}"
    if mapped_labels:
        detail += "; mapped from " + "; ".join(mapped_labels)
    if proposal.valid_until:
        detail += f"; stated validity {proposal.valid_until}"
    return detail + "; proposal on file, not accepted or committed"


def _source_ref(proposal: ReceivedCostProposal) -> dict[str, object]:
    return {
        "type": "project_evidence",
        "document_id": str(proposal.source_document_id),
        "ref": proposal.relative_path,
        "filename": proposal.filename,
        "proposal_reference": proposal.proposal_reference,
        "supplier": proposal.supplier,
        "amount_ex_gst": str(proposal.total_ex_gst),
    }


def _proposal_lines(section: str, *, kind: ProposalKind) -> list[ProposalLine]:
    lines: list[ProposalLine] = []
    for cells in _table_rows(section):
        if len(cells) < 2:
            continue
        label = _strip_markdown(cells[0])
        normalized = _normalize(label)
        if (
            not label
            or normalized == "gst"
            or normalized.startswith("total")
            or "fixed contract sum" in normalized
        ):
            continue
        if normalized in {"stage", "work package"}:
            continue
        if kind != "main_works" and not re.match(r"^\d+\.", label):
            continue
        amount = _money(cells[-1])
        if amount is not None:
            lines.append(ProposalLine(label=label, amount_ex_gst=amount))
    return lines


def _labelled_total(section: str, labels: tuple[str, ...]) -> Decimal | None:
    for cells in _table_rows(section):
        normalized = _normalize(" ".join(cells[:-1]))
        if any(label in normalized for label in labels):
            return _money(cells[-1])
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
    cleaned = _strip_markdown(value).replace("$", "").replace(",", "").strip()
    match = re.search(r"-?\d+(?:\.\d{1,2})?", cleaned)
    if match is None:
        return None
    try:
        return Decimal(match.group(0)).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _first_heading(markdown: str) -> str:
    for line in markdown.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line.strip())
        if match:
            return _strip_markdown(match.group(1))
    return ""


def _match_value(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return " ".join(match.group(1).split()) if match else None


def _available_code(preferred: str, used: set[str]) -> str:
    if preferred not in used:
        return preferred
    stem_match = re.match(r"^(\d+)", preferred)
    stem = stem_match.group(1) if stem_match else preferred
    index = 1
    while f"{stem}.{index}" in used:
        index += 1
    return f"{stem}.{index}"


def _natural_key(value: str) -> tuple[object, ...]:
    return tuple(
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", value)
        if part
    )


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _strip_markdown(value).lower()).strip()


def _strip_markdown(value: str) -> str:
    return re.sub(r"(?:\*\*|__|`)", "", value).strip()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
