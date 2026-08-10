from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.cost_plan.schemas import (
    CostItemInput,
    CostPlanOperation,
    CostPlanState,
    DependencySnapshot,
)
from app.cost_plan.service import apply_cost_plan_operations
from app.database.project import Project
from app.projects.artefact_revisions import ArtefactPolicyViolation


USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _item(key: str, code: str, *, paid: str = "0") -> CostItemInput:
    return CostItemInput(
        item_key=key,
        cost_code=code,
        category="Construction",
        item=key.title(),
        budget=Decimal("100"),
        forecast=Decimal("100"),
        paid=Decimal(paid),
        basis="Manual allowance",
        status="manual",
    )


def _state(items: list[CostItemInput], version: int = 1) -> CostPlanState:
    return CostPlanState(
        project_id=PROJECT_ID,
        version=version,
        dependency_snapshot=DependencySnapshot(
            profile_revision=1,
            evidence_fingerprint="evidence",
            decision_set_revision=1,
            runtime_version="test",
        ),
        items=items,
    )


def test_batch_operations_publish_once_and_return_a_delta() -> None:
    base = _state([_item("joinery", "C-01"), _item("ffe", "C-02")])

    async def publish(*args, state: CostPlanState, **kwargs) -> CostPlanState:
        return state.model_copy(update={"version": 2, "totals": _totals(state)})

    with (
        patch(
            "app.cost_plan.service._base_for_mutation", new=AsyncMock(return_value=base)
        ),
        patch(
            "app.cost_plan.service._publish_state", new=AsyncMock(side_effect=publish)
        ) as publish_mock,
    ):
        result = asyncio.run(
            apply_cost_plan_operations(
                AsyncMock(),
                project=Project(id=PROJECT_ID, owner_user_id=USER_ID),
                author_user_id=USER_ID,
                expected_base_version=1,
                operations=[
                    CostPlanOperation(
                        operation="UPDATE",
                        target_type="cost_item",
                        target_id="joinery",
                        values={"budget": "150", "forecast": "150"},
                    ),
                    CostPlanOperation(
                        operation="DUPLICATE",
                        target_type="cost_item",
                        target_id="ffe",
                        values={"item_key": "ffe-2", "cost_code": "C-03"},
                    ),
                ],
            )
        )

    publish_mock.assert_awaited_once()
    assert result.delta.version == 2
    assert {item.item_key for item in result.delta.changed_items} == {
        "joinery",
        "ffe-2",
    }
    assert result.delta.workbook_status == "pending"


def test_delete_blocks_items_with_invoice_or_commitment_dependencies() -> None:
    base = _state([_item("paid", "C-01", paid="25")])
    with patch(
        "app.cost_plan.service._base_for_mutation",
        new=AsyncMock(return_value=base),
    ):
        with pytest.raises(ArtefactPolicyViolation, match="paid invoices"):
            asyncio.run(
                apply_cost_plan_operations(
                    AsyncMock(),
                    project=Project(id=PROJECT_ID, owner_user_id=USER_ID),
                    author_user_id=USER_ID,
                    expected_base_version=1,
                    operations=[
                        CostPlanOperation(
                            operation="DELETE",
                            target_type="cost_item",
                            target_id="paid",
                        )
                    ],
                )
            )


def _totals(state: CostPlanState):
    from app.cost_plan.calculations import calculate_totals

    return calculate_totals(
        state.items,
        contingency_percent=state.contingency_percent,
        escalation_percent=state.escalation_percent,
        gst_treatment=state.gst_treatment,
    )
