"""Immutable machine invoice snapshot and reviewed overlay (Pulse Stage 10)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.cost_plan.models import CostInvoice
from app.cost_plan.schemas import ExtractedInvoice

OVERLAY_SCALAR_KEYS = frozenset(
    {
        "supplier_name",
        "supplier_abn",
        "invoice_number",
        "invoice_date",
        "due_date",
        "po_number",
        "related_reference",
        "subtotal_ex_gst",
        "gst",
        "total_including_gst",
        "currency",
    }
)


class MachineExtractionImmutable(RuntimeError):
    pass


class ReviewedLinesNotAllowed(ValueError):
    pass


def machine_snapshot_payload(extracted: ExtractedInvoice) -> dict[str, Any]:
    return extracted.model_dump(mode="json")


def set_machine_extraction(invoice: CostInvoice, payload: dict[str, Any]) -> None:
    existing = invoice.machine_extraction or {}
    if existing:
        raise MachineExtractionImmutable(
            "machine_extraction is immutable after insert"
        )
    invoice.machine_extraction = payload


def effective_extraction(invoice: CostInvoice) -> ExtractedInvoice:
    overlay = dict(invoice.reviewed_extraction or {})
    if "lines" in overlay:
        raise ReviewedLinesNotAllowed(
            "reviewed_extraction cannot replace machine lines"
        )
    payload = {**(invoice.machine_extraction or {}), **overlay}
    return ExtractedInvoice.model_validate(payload, context={"strict": False})


def effective_invoice_number(invoice: CostInvoice) -> str:
    overlay = (invoice.reviewed_extraction or {}).get("invoice_number")
    if overlay:
        return str(overlay)
    machine = (invoice.machine_extraction or {}).get("invoice_number")
    if machine:
        return str(machine)
    return invoice.invoice_number


def apply_reviewed_overlay(
    invoice: CostInvoice,
    overlay: dict[str, Any],
    *,
    actor_id,
    reviewed_at: datetime,
) -> None:
    if "lines" in overlay:
        raise ReviewedLinesNotAllowed(
            "reviewed_extraction cannot replace machine lines"
        )
    cleaned = {
        key: value
        for key, value in overlay.items()
        if key in OVERLAY_SCALAR_KEYS and value is not None
    }
    invoice.reviewed_extraction = {**(invoice.reviewed_extraction or {}), **cleaned}
    invoice.reviewed_by_user_id = actor_id
    invoice.reviewed_at = reviewed_at
    try:
        extracted = effective_extraction(invoice)
    except Exception:
        return
    invoice.supplier_name = extracted.supplier_name
    invoice.invoice_number = extracted.invoice_number
    invoice.invoice_date = extracted.invoice_date
    invoice.due_date = extracted.due_date
    invoice.po_number = extracted.po_number
    invoice.related_reference = extracted.related_reference
    if _amounts_bookable(extracted):
        invoice.subtotal_ex_gst = extracted.subtotal_ex_gst
        invoice.gst = extracted.gst
        invoice.total_including_gst = extracted.total_including_gst
        invoice.billing_month = extracted.billing_month


def _amounts_bookable(extracted: ExtractedInvoice) -> bool:
    try:
        ExtractedInvoice.model_validate(
            extracted.model_dump(mode="json"), context={"strict": True}
        )
    except Exception:
        return False
    return True
