"""Explicit ledger/dependency checks before Cost Plan item deletion."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cost_plan.models import CostInvoice, CostInvoiceAllocation
from app.cost_plan.schemas import CostItemInput, CostPlanDeletionBlocker
from app.projects.artefact_revisions import ArtefactPolicyViolation


class CostPlanDeletionBlocked(ArtefactPolicyViolation):
    """Raised when deleting a cost item would orphan ledger dependencies."""

    def __init__(
        self,
        *,
        item_key: str,
        blockers: list[CostPlanDeletionBlocker],
    ) -> None:
        self.item_key = item_key
        self.blockers = blockers
        labels = ", ".join(blocker.label for blocker in blockers)
        super().__init__(f"Cannot delete {item_key!r}; referenced by {labels}")

    def detail(self) -> dict[str, object]:
        return {
            "code": "cost_plan_deletion_blocked",
            "item_key": self.item_key,
            "blockers": [blocker.model_dump(mode="json") for blocker in self.blockers],
            "message": str(self),
        }


async def collect_cost_item_deletion_blockers(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    item: CostItemInput,
) -> list[CostPlanDeletionBlocker]:
    """Return typed blockers from invoice rows and item ledger dependencies."""
    blockers: list[CostPlanDeletionBlocker] = []
    rows = (
        await session.execute(
            select(CostInvoiceAllocation, CostInvoice)
            .join(
                CostInvoice,
                (CostInvoice.id == CostInvoiceAllocation.invoice_id)
                & (CostInvoice.project_id == CostInvoiceAllocation.project_id),
            )
            .where(
                CostInvoiceAllocation.project_id == project_id,
                CostInvoiceAllocation.cost_item_key == item.item_key,
                CostInvoice.processing_status != "void",
            )
        )
    ).all()
    for allocation, invoice in rows:
        blockers.append(
            CostPlanDeletionBlocker(
                kind="invoice",
                id=str(invoice.id),
                label=f"{invoice.supplier_name} {invoice.invoice_number}",
                reference_id=str(allocation.id),
            )
        )

    if item.paid and not any(blocker.kind == "invoice" for blocker in blockers):
        blockers.append(
            CostPlanDeletionBlocker(
                kind="invoice",
                id=None,
                label=f"paid ledger amount ${_money(item.paid)}",
            )
        )
    if item.committed:
        blockers.append(
            CostPlanDeletionBlocker(
                kind="commitment",
                id=None,
                label=f"commitment ${_money(item.committed)}",
            )
        )

    seen_kinds: set[str] = {blocker.kind for blocker in blockers}
    for reference in item.source_refs:
        if not isinstance(reference, dict):
            continue
        kind = str(reference.get("kind") or "").casefold()
        mapped = _source_ref_kind(kind)
        if mapped is None or mapped in seen_kinds:
            continue
        seen_kinds.add(mapped)
        blockers.append(
            CostPlanDeletionBlocker(
                kind=mapped,
                id=str(reference["id"]) if reference.get("id") is not None else None,
                label=_source_ref_label(mapped, reference),
                reference_id=(
                    str(reference["reference_id"])
                    if reference.get("reference_id") is not None
                    else None
                ),
            )
        )
    return blockers


def raise_if_blocked(
    *,
    item_key: str,
    blockers: list[CostPlanDeletionBlocker],
) -> None:
    if blockers:
        raise CostPlanDeletionBlocked(item_key=item_key, blockers=blockers)


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def _source_ref_kind(kind: str) -> str | None:
    for token, mapped in (
        ("invoice", "invoice"),
        ("commitment", "commitment"),
        ("variation", "variation"),
        ("forecast", "forecast"),
        ("procurement", "procurement"),
    ):
        if token in kind:
            return mapped
    return None


def _source_ref_label(kind: str, reference: dict[str, object]) -> str:
    label = reference.get("label") or reference.get("id") or kind
    return str(label)
