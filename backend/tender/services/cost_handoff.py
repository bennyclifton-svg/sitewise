from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.draft_artifact import DraftArtifact
from tender.models import (
    TaxonomyCell,
    TenderCellStatus,
    TenderComparison,
    TenderDocument,
    TenderQuote,
    TenderReport,
)
from tender.schemas import ApprovedTenderCostHandoff, ApprovedTenderCostItem


class TenderCostHandoffError(ValueError):
    pass


def require_handoff_quality(provenance: dict[str, Any] | None) -> dict[str, Any]:
    quality = provenance.get("tender_quality") if isinstance(provenance, dict) else None
    if not isinstance(quality, dict) or not quality.get("qs_gate_passed"):
        raise TenderCostHandoffError(
            "R3 customer QS acceptance is not persisted for this report"
        )
    if not quality.get("mandatory_qa_resolved"):
        raise TenderCostHandoffError("mandatory Tender QA is unresolved")
    return quality


def _stable_hash(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


async def approved_tender_cost_handoff(
    session: AsyncSession,
    *,
    comparison_id: uuid.UUID,
    selected_quote_id: uuid.UUID,
    package_scope: str,
    operator_user_id: uuid.UUID,
) -> ApprovedTenderCostHandoff:
    """Project an approved Tender only after the separately persisted R3 quality gate."""
    row = (
        await session.execute(
            select(TenderComparison, TenderReport, DraftArtifact, TenderQuote)
            .join(TenderReport, TenderReport.comparison_id == TenderComparison.id)
            .join(DraftArtifact, DraftArtifact.id == TenderReport.draft_id)
            .join(
                TenderQuote,
                (TenderQuote.comparison_id == TenderComparison.id)
                & (TenderQuote.id == selected_quote_id),
            )
            .where(TenderComparison.id == comparison_id)
            .order_by(TenderReport.version.desc())
            .limit(1)
        )
    ).one_or_none()
    if row is None:
        raise TenderCostHandoffError(
            "comparison, selected quote, or report was not found"
        )
    comparison, report, draft, quote = row
    if comparison.status not in {"approved", "delivered"} or report.approved_at is None:
        raise TenderCostHandoffError("Tender report is not approved")
    if draft.status != "accepted":
        raise TenderCostHandoffError("Tender report version is not frozen")
    if report.approved_by != operator_user_id:
        raise TenderCostHandoffError(
            "explicit operator approval does not match the frozen report"
        )

    provenance = (
        draft.provenance_metadata
        if isinstance(draft.provenance_metadata, dict)
        else None
    )
    quality = require_handoff_quality(provenance)

    cell_rows = (
        await session.execute(
            select(TenderCellStatus, TaxonomyCell)
            .join(TaxonomyCell, TaxonomyCell.code == TenderCellStatus.cell_code)
            .where(
                TenderCellStatus.comparison_id == comparison.id,
                TenderCellStatus.quote_id == quote.id,
                TenderCellStatus.status.in_(("included", "pc", "ps")),
            )
            .order_by(TaxonomyCell.sort_order, TaxonomyCell.code)
        )
    ).all()
    items: list[ApprovedTenderCostItem] = []
    for status, cell in cell_rows:
        if status.amount_cents is None:
            continue
        evidence = status.evidence if isinstance(status.evidence, dict) else {}
        items.append(
            ApprovedTenderCostItem(
                item_key=f"tender-{cell.code.lower()}",
                cost_code=cell.code,
                category=cell.grp,
                item=cell.name,
                amount_cents=status.amount_cents,
                allowance_type=status.status
                if status.status in {"pc", "ps"}
                else "none",
                source_refs=[evidence] if evidence else [],
            )
        )
    if not items:
        raise TenderCostHandoffError(
            "selected quote has no mapped comparable cost items"
        )

    documents = list(
        (
            await session.execute(
                select(TenderDocument)
                .where(TenderDocument.quote_id == quote.id)
                .order_by(TenderDocument.input_position, TenderDocument.id)
            )
        ).scalars()
    )
    source_documents = [
        {
            "document_id": str(document.id),
            "content_hash": document.content_hash,
            "storage_version": document.storage_version,
            "filename": document.original_filename,
        }
        for document in documents
    ]
    comparable_total = sum(item.amount_cents for item in items)
    qualifiers = quality.get("financial_qualifiers")
    qualifiers = qualifiers if isinstance(qualifiers, dict) else {}
    identity: dict[str, Any] = {
        "comparison_id": str(comparison.id),
        "report_id": str(report.id),
        "report_version": report.version,
        "quote_id": str(quote.id),
        "package_scope": package_scope,
        "documents": source_documents,
    }
    return ApprovedTenderCostHandoff(
        project_id=comparison.project_id,
        comparison_id=comparison.id,
        report_id=report.id,
        report_version=report.version,
        report_frozen=True,
        mandatory_qa_resolved=True,
        qs_gate_passed=True,
        operator_approved_by=operator_user_id,
        selected_quote_id=quote.id,
        package_scope=package_scope,
        comparison_version=comparison.input_fingerprint
        or _stable_hash(comparison.context),
        quote_version=_stable_hash(
            {
                "quote_id": quote.id,
                "stated_total_cents": quote.stated_total_cents,
                "gst_treatment": quote.gst_treatment,
                "documents": source_documents,
            }
        ),
        source_documents=source_documents,
        mapped_items=items,
        stated_total_cents=quote.stated_total_cents,
        comparable_total_cents=comparable_total,
        gst_treatment=quote.gst_treatment,
        alternates=list(qualifiers.get("alternates", [])),
        allowances=list(qualifiers.get("allowances", [])),
        exclusions=list(qualifiers.get("exclusions", [])),
        qualifications=list(qualifiers.get("qualifications", [])),
        idempotency_key=f"tender-cost:{_stable_hash(identity)}",
    )
