"""Coalesce repeated workbook rebuild requests behind a quiet period."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable


Rebuild = Callable[[], Awaitable[None]]
log = logging.getLogger(__name__)


class WorkbookRebuildCoordinator:
    def __init__(self, *, quiet_seconds: float = 2.0) -> None:
        self.quiet_seconds = max(0, quiet_seconds)
        self._pending: dict[str, tuple[int, Rebuild]] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def schedule(self, key: str, rebuild: Rebuild) -> None:
        generation = self._pending.get(key, (0, rebuild))[0] + 1
        self._pending[key] = (generation, rebuild)
        previous = self._tasks.get(key)
        if previous is not None:
            previous.cancel()
        self._tasks[key] = asyncio.create_task(self._after_quiet(key, generation))

    async def flush(self, key: str) -> bool:
        pending = self._pending.pop(key, None)
        task = self._tasks.pop(key, None)
        if task is not None and task is not asyncio.current_task():
            task.cancel()
        if pending is None:
            return False
        await pending[1]()
        return True

    async def _after_quiet(self, key: str, generation: int) -> None:
        try:
            await asyncio.sleep(self.quiet_seconds)
            pending = self._pending.get(key)
            if pending is None or pending[0] != generation:
                return
            await self.flush(key)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            # The canonical state is already committed and remains authoritative;
            # a later preview/export request retries this derived artefact.
            log.error(
                "cost_plan_workbook_rebuild_failed",
                extra={"key": key, "error_type": type(exc).__name__},
            )


workbook_rebuilds = WorkbookRebuildCoordinator()


def _cost_plan_key(project_id: uuid.UUID) -> str:
    return f"cost-plan:{project_id}"


def schedule_cost_plan_workbook_rebuild(
    project_id: uuid.UUID,
    version: int,
) -> dict[str, object]:
    """Queue only the newest workbook revision for a project's quiet period."""

    async def rebuild() -> None:
        from app.cost_plan.service import get_cost_plan
        from app.database.draft_artifacts import get_draft_artifact
        from app.database.projects import get_project
        from app.database.session import get_session_factory
        from app.workflows.create_cost_plan import sync_cost_plan_revision_artifacts

        async with get_session_factory()() as session:
            project = await get_project(session, project_id)
            if project is None:
                return
            state = await get_cost_plan(
                session,
                project_id=project_id,
                owner_user_id=project.owner_user_id,
                version=version,
            )
            if state.artefact_revision_id is None:
                return
            draft = await get_draft_artifact(session, state.artefact_revision_id)
            if draft is None:
                return
            await sync_cost_plan_revision_artifacts(
                session,
                project=project,
                draft=draft,
                typed_state=state,
            )
            await session.commit()

    workbook_rebuilds.schedule(_cost_plan_key(project_id), rebuild)
    return {"status": "pending", "version": version}


async def flush_cost_plan_workbook_rebuild(project_id: uuid.UUID) -> bool:
    """Build a pending workbook now when a preview/export genuinely needs it."""
    return await workbook_rebuilds.flush(_cost_plan_key(project_id))
