from __future__ import annotations

import re
from decimal import Decimal

from app.cost_plan.schemas import (
    CostItemInput,
    CostPlanState,
    ExtractedInvoice,
    InvoiceAllocationInput,
    InvoiceLineInput,
)


_MARKERS: dict[str, tuple[str, ...]] = {
    "architect": ("architect", "architecture"),
    "structural": ("structural", "structure", "civil engineer"),
    "hydraulic": ("hydraulic", "plumbing", "wastewater"),
    "cost_advisory": (
        "quantity survey",
        "cost advisory",
        "cost consultant",
        "cost manager",
    ),
    "main_works": ("main works", "builder", "head contractor", "construction"),
    "statutory": (
        "planning portal",
        "statutory",
        "authority fee",
        "authority enquiry",
        "lodgement",
        "disbursement",
    ),
    "substructure": ("substructure", "footing", "slab", "excavation"),
    "framing": ("framing", "frame", "structural steel"),
    "envelope": ("envelope", "lock up", "lockup", "roof", "cladding", "glazing"),
    "fitout": ("fit out", "fitout", "joinery", "kitchen", "bathroom", "internal"),
    "completion": ("completion", "hand over", "handover", "defects", "commissioning"),
}


def map_invoice_allocations(
    invoice: ExtractedInvoice,
    cost_plan: CostPlanState,
) -> list[InvoiceAllocationInput]:
    return [
        _map_line(invoice, line, line_number, cost_plan.items)
        for line_number, line in enumerate(invoice.lines, start=1)
    ]


def _map_line(
    invoice: ExtractedInvoice,
    line: InvoiceLineInput,
    line_number: int,
    items: list[CostItemInput],
) -> InvoiceAllocationInput:
    exact = [item for item in items if _normalize(item.item) == _normalize(line.description)]
    if len(exact) == 1:
        return _mapped(line, line_number, exact[0], "exact", Decimal("1"))

    related = [item for item in items if _source_ref_matches(item, invoice)]
    scored = _scored_candidates(invoice, line, items)
    if scored:
        best_score = scored[0][0]
        best = [item for score, item in scored if score == best_score]
        if len(best) == 1:
            method = "related_reference" if best[0] in related and len(related) == 1 else "keyword"
            confidence = Decimal("1") if method == "related_reference" else Decimal("0.9000")
            return _mapped(line, line_number, best[0], method, confidence)

    return InvoiceAllocationInput(
        line_number=line_number,
        description=line.description,
        amount_ex_gst=line.amount_ex_gst,
        gst_treatment=line.gst_treatment,
        cost_item_label="Unidentified",
        mapping_method="unidentified",
        review_status="needs_review",
        source_locators=line.source_locators,
    )


def _scored_candidates(
    invoice: ExtractedInvoice,
    line: InvoiceLineInput,
    items: list[CostItemInput],
) -> list[tuple[int, CostItemInput]]:
    line_markers = _markers(line.description)
    supplier_markers = _markers(invoice.supplier_name)
    scored: list[tuple[int, CostItemInput]] = []
    for item in items:
        item_text = " ".join((item.category, item.item, item.basis))
        item_markers = _markers(item_text)
        score = 4 * len(line_markers & item_markers)
        score += len(supplier_markers & item_markers)
        if _source_ref_matches(item, invoice):
            score += 2
        if score > 0:
            scored.append((score, item))
    return sorted(scored, key=lambda value: (-value[0], value[1].cost_code, value[1].item_key))


def _source_ref_matches(item: CostItemInput, invoice: ExtractedInvoice) -> bool:
    invoice_supplier = _normalize(invoice.supplier_name)
    invoice_reference = _normalize(invoice.related_reference or "")
    for source_ref in item.source_refs:
        reference = _normalize(str(source_ref.get("proposal_reference", "")))
        supplier = _normalize(str(source_ref.get("supplier", "")))
        if invoice_reference and reference == invoice_reference:
            return True
        if invoice_supplier and supplier == invoice_supplier:
            return True
    return False


def _markers(value: str) -> set[str]:
    normalized = _normalize(value)
    return {
        marker
        for marker, phrases in _MARKERS.items()
        if any(phrase in normalized for phrase in phrases)
    }


def _mapped(
    line: InvoiceLineInput,
    line_number: int,
    item: CostItemInput,
    method: str,
    confidence: Decimal,
) -> InvoiceAllocationInput:
    return InvoiceAllocationInput(
        line_number=line_number,
        description=line.description,
        amount_ex_gst=line.amount_ex_gst,
        gst_treatment=line.gst_treatment,
        cost_item_key=item.item_key,
        cost_item_label=item.item,
        mapping_method=method,  # type: ignore[arg-type]
        mapping_confidence=confidence,
        review_status="mapped",
        source_locators=line.source_locators,
    )


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
