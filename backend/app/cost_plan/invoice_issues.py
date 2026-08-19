"""Coded invoice validation issues (Pulse Stage 11)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.cost_plan.models import CostInvoice
from app.cost_plan.schemas import ExtractedInvoice, InvoiceAllocationInput

InvoiceIssueCode = Literal[
    "TOTAL_MISMATCH",
    "GST_MISMATCH",
    "DUPLICATE_INVOICE",
    "CONFLICTING_DUPLICATE",
    "UNKNOWN_SUPPLIER",
    "ABN_MISMATCH",
    "UNKNOWN_COST_CODE",
    "PO_NOT_FOUND",
    "VARIATION_NOT_FOUND",
    "UNAPPROVED_VARIATION",
    "DATE_OUTSIDE_PERIOD",
    "AMOUNT_EXCEEDS_COMMITMENT",
    "COST_PLAN_OVERRUN",
    "CLAIM_EXCEEDS_REMAINING_VALUE",
    "MAPPING_LOW_CONFIDENCE",
]
InvoiceIssueSeverity = Literal["error", "warning", "info"]
FieldReconciliationStatus = Literal[
    "match",
    "different",
    "missing_primary",
    "missing_secondary",
    "missing_both",
]

RECONCILED_FIELDS = (
    "invoice_number",
    "supplier_name",
    "supplier_abn",
    "invoice_date",
    "subtotal_ex_gst",
    "gst",
    "total_including_gst",
)


class InvoiceIssue(BaseModel):
    code: InvoiceIssueCode
    severity: InvoiceIssueSeverity
    field: str | None = None
    message: str = Field(min_length=1)


def arithmetic_issues(extracted: ExtractedInvoice) -> list[InvoiceIssue]:
    issues: list[InvoiceIssue] = []
    if not extracted.lines:
        return issues
    line_total = sum(
        (line.amount_ex_gst for line in extracted.lines), Decimal("0")
    ).quantize(Decimal("0.01"))
    subtotal = extracted.subtotal_ex_gst.quantize(Decimal("0.01"))
    gst = extracted.gst.quantize(Decimal("0.01"))
    inclusive = extracted.total_including_gst.quantize(Decimal("0.01"))
    if line_total != subtotal:
        issues.append(
            InvoiceIssue(
                code="TOTAL_MISMATCH",
                severity="error",
                field="subtotal_ex_gst",
                message=f"invoice line total {line_total} does not equal subtotal {subtotal}",
            )
        )
    if subtotal + gst != inclusive:
        issues.append(
            InvoiceIssue(
                code="GST_MISMATCH",
                severity="error",
                field="total_including_gst",
                message=(
                    f"subtotal plus GST {subtotal + gst} does not equal total {inclusive}"
                ),
            )
        )
    taxable_total = sum(
        (
            line.amount_ex_gst
            for line in extracted.lines
            if line.gst_treatment != "gst_free"
        ),
        Decimal("0"),
    )
    expected_gst = (taxable_total * Decimal("0.10")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if gst != expected_gst:
        issues.append(
            InvoiceIssue(
                code="GST_MISMATCH",
                severity="error",
                field="gst",
                message=f"GST {gst} does not equal 10% of taxable lines {expected_gst}",
            )
        )
    return issues


def allocation_issues(
    extracted: ExtractedInvoice, allocations: list[InvoiceAllocationInput]
) -> list[InvoiceIssue]:
    issues: list[InvoiceIssue] = []
    allocation_total = sum(
        (allocation.amount_ex_gst for allocation in allocations), Decimal("0")
    ).quantize(Decimal("0.01"))
    subtotal = extracted.subtotal_ex_gst.quantize(Decimal("0.01"))
    if allocation_total != subtotal:
        issues.append(
            InvoiceIssue(
                code="TOTAL_MISMATCH",
                severity="error",
                field="allocations",
                message=(
                    f"invoice allocation total {allocation_total} "
                    f"does not equal subtotal {subtotal}"
                ),
            )
        )
    if any(item.review_status == "needs_review" for item in allocations):
        issues.append(
            InvoiceIssue(
                code="MAPPING_LOW_CONFIDENCE",
                severity="warning",
                field="allocations",
                message="One or more allocations still need a cost-item mapping",
            )
        )
    return issues


def has_error_issues(issues: list[InvoiceIssue] | list[dict[str, Any]]) -> bool:
    for issue in issues:
        severity = issue.severity if isinstance(issue, InvoiceIssue) else issue.get("severity")
        if severity == "error":
            return True
    return False


def field_reconciliation(invoice: CostInvoice) -> dict[str, FieldReconciliationStatus]:
    machine = invoice.machine_extraction or {}
    reviewed = invoice.reviewed_extraction or {}
    secondary = machine.get("secondary") if isinstance(machine.get("secondary"), dict) else {}
    statuses: dict[str, FieldReconciliationStatus] = {}
    for field in RECONCILED_FIELDS:
        primary = machine.get(field)
        overlay = reviewed.get(field)
        second = secondary.get(field) if isinstance(secondary, dict) else None
        statuses[field] = _status(primary, overlay, second)
    return statuses


def _status(
    primary: object, overlay: object, secondary: object
) -> FieldReconciliationStatus:
    has_primary = primary not in (None, "")
    has_overlay = overlay not in (None, "")
    has_secondary = secondary not in (None, "")
    if has_overlay and has_primary and str(overlay) != str(primary):
        return "different"
    if has_overlay and not has_primary:
        return "missing_primary"
    if not has_primary and not has_secondary:
        return "missing_both"
    if not has_primary and has_secondary:
        return "missing_primary"
    if has_primary and not has_secondary:
        return "missing_secondary"
    return "match"


def should_run_secondary(issues: list[InvoiceIssue], snapshot: dict[str, Any]) -> bool:
    if any(issue.code in {"TOTAL_MISMATCH", "GST_MISMATCH"} for issue in issues):
        return True
    required = ("supplier_name", "invoice_number", "invoice_date", "subtotal_ex_gst")
    if any(not snapshot.get(key) for key in required):
        return True
    provenance = snapshot.get("provenance") if isinstance(snapshot.get("provenance"), dict) else {}
    fields = provenance.get("fields") if isinstance(provenance, dict) else None
    if isinstance(fields, dict):
        for payload in fields.values():
            if isinstance(payload, dict):
                confidence = payload.get("confidence")
                if isinstance(confidence, (int, float)) and confidence < 0.7:
                    return True
    reconciliation = snapshot.get("reconciliation")
    if isinstance(reconciliation, dict) and any(
        value == "different" for value in reconciliation.values()
    ):
        return True
    return False
