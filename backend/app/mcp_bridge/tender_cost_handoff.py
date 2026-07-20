from __future__ import annotations

from decimal import Decimal

from app.cost_plan.schemas import CostItemInput, ExternalCostProposal
from tender.schemas import ApprovedTenderCostHandoff


def map_tender_handoff(handoff: ApprovedTenderCostHandoff) -> ExternalCostProposal:
    """Explicit composition boundary: TCM DTO in, generic core proposal out."""
    return ExternalCostProposal(
        project_id=handoff.project_id,
        source_type="approved_tender",
        source_id=handoff.report_id,
        source_version=handoff.report_version,
        selected_option_id=handoff.selected_quote_id,
        package_scope=handoff.package_scope,
        idempotency_key=handoff.idempotency_key,
        items=[
            CostItemInput(
                item_key=item.item_key,
                cost_code=item.cost_code,
                category=item.category,
                item=item.item,
                budget=Decimal(item.amount_cents) / Decimal("100"),
                committed=Decimal(item.amount_cents) / Decimal("100"),
                forecast=Decimal(item.amount_cents) / Decimal("100"),
                allowance_type=item.allowance_type,
                basis="Explicitly selected approved Tender package",
                source_refs=item.source_refs,
                status="proposed",
            )
            for item in handoff.mapped_items
        ],
        financial_qualifiers={
            "stated_total_cents": handoff.stated_total_cents,
            "comparable_total_cents": handoff.comparable_total_cents,
            "gst_treatment": handoff.gst_treatment,
            "alternates": handoff.alternates,
            "allowances": handoff.allowances,
            "exclusions": handoff.exclusions,
            "qualifications": handoff.qualifications,
        },
        source_versions={
            "comparison": handoff.comparison_version,
            "report": handoff.report_version,
            "quote": handoff.quote_version,
            "documents": handoff.source_documents,
        },
    )
