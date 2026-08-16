from __future__ import annotations

from decimal import Decimal

from app.cost_plan.normalization import (
    normalize_business_key,
    normalize_description_key,
)
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

_PROFESSIONAL_TRADE_MARKERS = {
    "architect",
    "structural",
    "hydraulic",
    "cost_advisory",
}


def map_invoice_allocations(
    invoice: ExtractedInvoice,
    cost_plan: CostPlanState,
    remembered_mappings: dict[tuple[str, str], tuple[str, str]] | None = None,
) -> list[InvoiceAllocationInput]:
    return [
        _map_line(
            invoice,
            line,
            line_number,
            cost_plan.items,
            remembered_mappings=remembered_mappings,
        )
        for line_number, line in enumerate(invoice.lines, start=1)
    ]


def _map_line(
    invoice: ExtractedInvoice,
    line: InvoiceLineInput,
    line_number: int,
    items: list[CostItemInput],
    remembered_mappings: dict[tuple[str, str], tuple[str, str]] | None = None,
) -> InvoiceAllocationInput:
    remembered = (remembered_mappings or {}).get(
        (
            normalize_business_key(invoice.supplier_name),
            normalize_description_key(line.description),
        )
    )
    if remembered is not None:
        return _mapped(line, line_number, remembered, "remembered", Decimal("1"))

    eligible_items = _eligible_items(line, items, invoice.supplier_name)
    exact = [
        item
        for item in eligible_items
        if _normalize(item.item) == _normalize(line.description)
    ]
    if len(exact) == 1:
        return _mapped(line, line_number, exact[0], "exact", Decimal("1"))

    related = [
        item for item in eligible_items if _source_ref_matches(item, invoice)
    ]
    scored = _scored_candidates(invoice, line, eligible_items)
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


def _eligible_items(
    line: InvoiceLineInput,
    items: list[CostItemInput],
    supplier_name: str = "",
) -> list[CostItemInput]:
    """Keep explicit professional services out of construction trade rows.

    Structural invoices often mention framing, slabs, or roofs as design scope.
    Those words describe the engineer's service and must not outweigh the
    professional discipline when an existing consultant identity is available.
    The supplier name is part of that identity: "Ardent Structural" should
    map to the consultant row even when the fee line never says "structural".
    """
    line_professional = _markers(line.description) & _PROFESSIONAL_TRADE_MARKERS
    supplier_professional = _markers(supplier_name) & _PROFESSIONAL_TRADE_MARKERS
    if not line_professional and not supplier_professional:
        return items
    eligible = [
        item
        for item in items
        if "construction" not in _normalize(item.category)
    ]
    if not line_professional:
        return eligible
    return [
        item
        for item in eligible
        if line_professional
        & _markers(" ".join((item.category, item.item, item.basis)))
    ]


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
    item: CostItemInput | tuple[str, str],
    method: str,
    confidence: Decimal,
) -> InvoiceAllocationInput:
    if isinstance(item, tuple):
        cost_item_key, cost_item_label = item
    else:
        cost_item_key, cost_item_label = item.item_key, item.item
    return InvoiceAllocationInput(
        line_number=line_number,
        description=line.description,
        amount_ex_gst=line.amount_ex_gst,
        gst_treatment=line.gst_treatment,
        cost_item_key=cost_item_key,
        cost_item_label=cost_item_label,
        mapping_method=method,  # type: ignore[arg-type]
        mapping_confidence=confidence,
        review_status="mapped",
        source_locators=line.source_locators,
    )


_normalize = normalize_description_key
