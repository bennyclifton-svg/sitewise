from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.cost_plan.deletion_blockers import (
    CostPlanDeletionBlocked,
    collect_cost_item_deletion_blockers,
)
from app.cost_plan.schemas import CostItemInput, CostPlanDeletionBlocker


PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
INVOICE_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
ALLOCATION_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _item(
    key: str = "joinery",
    *,
    paid: str = "0",
    committed: str = "0",
    forecast: str = "100",
    source_refs: list[dict[str, object]] | None = None,
) -> CostItemInput:
    return CostItemInput(
        item_key=key,
        cost_code="C-01",
        category="Construction",
        item="Joinery",
        budget=Decimal("100"),
        forecast=Decimal(forecast),
        paid=Decimal(paid),
        committed=Decimal(committed),
        basis="Manual allowance",
        status="manual",
        source_refs=source_refs or [],
    )


def test_collects_typed_blockers_from_ledger_queries_and_item_dependencies() -> None:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = [
        (
            SimpleNamespace(id=ALLOCATION_ID, cost_item_key="joinery"),
            SimpleNamespace(
                id=INVOICE_ID,
                supplier_name="Quoin Architecture",
                invoice_number="QUA-2601",
                processing_status="booked",
            ),
        )
    ]
    session.execute = AsyncMock(return_value=result)

    blockers = asyncio.run(
        collect_cost_item_deletion_blockers(
            session,
            project_id=PROJECT_ID,
            item=_item(
                paid="25",
                committed="40",
                source_refs=[
                    {"kind": "variation", "id": "var-1", "label": "VO-01"},
                    {"kind": "forecast_adjustment", "id": "fc-1"},
                    {"kind": "procurement_package", "id": "pkg-hvac"},
                ],
            ),
        )
    )

    assert [blocker.kind for blocker in blockers] == [
        "invoice",
        "commitment",
        "variation",
        "forecast",
        "procurement",
    ]
    assert blockers[0] == CostPlanDeletionBlocker(
        kind="invoice",
        id=str(INVOICE_ID),
        label="Quoin Architecture QUA-2601",
        reference_id=str(ALLOCATION_ID),
    )
    session.execute.assert_awaited_once()


def test_deletion_blocked_error_exposes_typed_blockers() -> None:
    blockers = [
        CostPlanDeletionBlocker(
            kind="invoice",
            id=str(INVOICE_ID),
            label="Quoin Architecture QUA-2601",
            reference_id=str(ALLOCATION_ID),
        )
    ]
    with pytest.raises(CostPlanDeletionBlocked) as raised:
        raise CostPlanDeletionBlocked(item_key="joinery", blockers=blockers)

    assert raised.value.item_key == "joinery"
    assert raised.value.blockers == blockers
    assert raised.value.detail()["code"] == "cost_plan_deletion_blocked"
    assert "joinery" in str(raised.value)
