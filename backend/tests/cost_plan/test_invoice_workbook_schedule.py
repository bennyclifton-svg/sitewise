from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.cost_invoices import _publish_edit
from app.cost_plan.workbook_rebuild import WorkbookRebuildCoordinator


PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DRAFT_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def test_invoice_publish_commits_then_schedules_workbook_without_touching_draft() -> None:
    session = AsyncMock()
    project = SimpleNamespace(id=PROJECT_ID, owner_user_id=USER_ID)
    state = SimpleNamespace(version=4, artefact_revision_id=DRAFT_ID)
    schedule = MagicMock(return_value={"status": "pending", "version": 4})

    with (
        patch(
            "app.api.cost_invoices.schedule_cost_plan_workbook_rebuild",
            schedule,
        ),
        patch(
            "app.api.cost_invoices.invoice_ledger_response",
            new=AsyncMock(return_value={"ok": True}),
        ),
        patch(
            "app.api.cost_invoices.workbook_workspace_path",
            return_value="01-cost/Cost_Plan_v04.draft.xlsx",
        ) as workbook_path,
    ):
        result = asyncio.run(
            _publish_edit(
                session,
                project=project,
                state=state,
            )
        )

    assert result == {"ok": True}
    session.get.assert_not_called()
    session.commit.assert_awaited_once()
    schedule.assert_called_once_with(PROJECT_ID, 4)
    workbook_path.assert_called_once_with(project, 4)


def test_ten_rapid_mixed_schedules_produce_one_workbook_build() -> None:
    async def scenario() -> list[int]:
        builds: list[int] = []
        coordinator = WorkbookRebuildCoordinator(quiet_seconds=0.01)

        for index in range(10):
            version = index + 1

            async def rebuild(selected: int = version) -> None:
                builds.append(selected)

            coordinator.schedule("project", rebuild)
        await asyncio.sleep(0.03)
        return builds

    assert asyncio.run(scenario()) == [10]
