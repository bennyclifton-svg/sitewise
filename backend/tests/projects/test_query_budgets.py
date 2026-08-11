"""F9: audited read paths avoid N+1 query shapes."""

from __future__ import annotations

import inspect

from app.cost_plan import service as cost_plan_service
from app.database import draft_artifacts


def test_get_cost_plan_eager_loads_items() -> None:
    source = inspect.getsource(cost_plan_service.get_cost_plan)
    assert "selectinload(CostPlanVersion.items)" in source
    assert source.count("await session.execute") == 1


def test_latest_draft_lookups_are_single_selects() -> None:
    latest = inspect.getsource(draft_artifacts.get_latest_draft_artifact)
    by_path = inspect.getsource(
        draft_artifacts.get_latest_draft_artifact_by_workspace_path
    )
    assert latest.count("await session.execute") == 1
    assert by_path.count("await session.execute") == 1
    assert ".limit(1)" in latest
    assert ".limit(1)" in by_path
