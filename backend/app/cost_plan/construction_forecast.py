"""Read explicit elemental construction forecasts without inventing trade allocations."""

from __future__ import annotations

import re
from decimal import Decimal

from app.cost_plan.evidence_reconciliation import CostEvidenceDocument
from app.cost_plan.schemas import CostItemInput


def extract_construction_forecast(
    documents: list[CostEvidenceDocument],
) -> list[CostItemInput]:
    """Return one reconciled ex-GST forecast; ambiguous or incomplete forecasts fail closed."""
    candidates = []
    for document in documents:
        section = re.search(
            r"^## Construction forecast\s*\n(.*?)(?=^#{1,2} |\Z)",
            document.content,
            re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        if section:
            candidates.append((document, section.group(1)))
    if not candidates:
        return []
    if len(candidates) != 1:
        raise ValueError("Multiple construction forecasts require source selection.")
    document, section = candidates[0]
    rows = [
        [cell.strip().replace("**", "") for cell in line.strip().strip("|").split("|")]
        for line in section.splitlines()
        if line.strip().startswith("|")
    ]
    if (
        not rows
        or len(rows[0]) != 2
        or not re.search(
            r"\b(?:ex|excl|excluding)\s+GST\b",
            rows[0][1],
            re.IGNORECASE,
        )
    ):
        raise ValueError(
            "Construction forecast requires an explicit ex-GST amount column."
        )
    items = []
    total = None
    for cells in rows[1:]:
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        if len(cells) != 2 or not re.fullmatch(r"\$[\d,]+(?:\.\d{1,2})?", cells[1]):
            raise ValueError(
                "Construction forecast contains an unpriced or unsupported row."
            )
        label, raw = cells
        amount = Decimal(raw.replace("$", "").replace(",", ""))
        if label.lower() == "forecast construction cost":
            if total is not None:
                raise ValueError("Construction forecast contains multiple totals.")
            total = amount
            continue
        if total is not None:
            raise ValueError("Construction forecast contains rows after its total.")
        index = len(items) + 1
        items.append(
            CostItemInput(
                item_key=f"construction-forecast:{document.id}:{index}",
                cost_code=f"CF.{index}",
                category="Construction",
                item=label,
                budget=amount,
                forecast=amount,
                allowance_type="contingency"
                if "contingency" in label.lower()
                else "none",
                basis=(
                    f"Construction forecast from {document.filename}; "
                    "source allowances retained, subject to review; not accepted or committed"
                ),
                source_refs=[
                    {
                        "type": "project_evidence",
                        "kind": "construction_forecast",
                        "document_id": str(document.id),
                        "ref": document.relative_path,
                        "filename": document.filename,
                        "source_label": label,
                        "line_amount_ex_gst": str(amount),
                    }
                ],
                status="proposed",
            )
        )
    if not items or total is None or sum(item.budget for item in items) != total:
        raise ValueError(
            "Construction forecast line amounts do not reconcile to its stated total."
        )
    return items
