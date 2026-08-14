import asyncio
from unittest.mock import patch

from app.cost_plan.workbook_rebuild import WorkbookRebuildCoordinator


def test_rebuild_coordinator_coalesces_rapid_changes() -> None:
    async def scenario() -> list[str]:
        calls: list[str] = []
        coordinator = WorkbookRebuildCoordinator(quiet_seconds=0.01)

        async def first() -> None:
            calls.append("first")

        async def latest() -> None:
            calls.append("latest")

        coordinator.schedule("project", first)
        coordinator.schedule("project", latest)
        await asyncio.sleep(0.03)
        return calls

    assert asyncio.run(scenario()) == ["latest"]


def test_explicit_flush_rebuilds_immediately() -> None:
    async def scenario() -> tuple[bool, list[str]]:
        calls: list[str] = []
        coordinator = WorkbookRebuildCoordinator(quiet_seconds=60)

        async def rebuild() -> None:
            calls.append("rebuilt")

        coordinator.schedule("project", rebuild)
        return await coordinator.flush("project"), calls

    assert asyncio.run(scenario()) == (True, ["rebuilt"])


def test_rebuild_failure_is_swallowed_so_canonical_state_remains() -> None:
    canary = "ch03-workbook-storage-token-xxxxxxxxxxxxxxxxxxxxxxxx"

    async def scenario() -> str:
        coordinator = WorkbookRebuildCoordinator(quiet_seconds=0.01)

        async def rebuild() -> None:
            raise RuntimeError(canary)

        coordinator.schedule("project", rebuild)
        await asyncio.sleep(0.03)
        return "canonical-ok"

    with patch("app.cost_plan.workbook_rebuild.log.error") as log_error:
        assert asyncio.run(scenario()) == "canonical-ok"

    assert log_error.call_args.kwargs["extra"]["error_type"] == "RuntimeError"
    assert canary not in str(log_error.call_args)
