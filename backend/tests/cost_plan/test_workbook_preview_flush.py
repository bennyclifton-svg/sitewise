from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.api.projects import (
    download_project_workspace_file,
    get_project_workspace_file_preview,
)


PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


class _User:
    id = USER_ID


def test_workbook_preview_flushes_pending_rebuild_once() -> None:
    session = AsyncMock()
    project = SimpleNamespace(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        workspace_path="projects/demo",
    )
    refreshed = SimpleNamespace(
        filename="Cost_Plan_v05.draft.xlsx",
        workspace_path="projects/demo/01-cost/Cost_Plan_v05.draft.xlsx",
        storage_key="storage/key-v5",
    )
    flush = AsyncMock(return_value=True)

    with (
        patch(
            "app.api.projects.get_project",
            new=AsyncMock(return_value=project),
        ),
        patch(
            "app.api.projects._require_project_owner",
            return_value=project,
        ),
        patch(
            "app.api.projects.flush_cost_plan_workbook_rebuild",
            flush,
        ),
        patch(
            "app.api.projects.read_canonical_cost_plan",
            new=AsyncMock(return_value=SimpleNamespace(version=5)),
        ),
        patch(
            "app.api.projects.cost_plan_workbook_workspace_path",
            return_value="projects/demo/01-cost/Cost_Plan_v05.draft.xlsx",
        ),
        patch(
            "app.api.projects.get_workspace_file_by_path",
            new=AsyncMock(return_value=refreshed),
        ),
        patch(
            "app.api.projects.workbook_preview_from_bytes",
            return_value=SimpleNamespace(sheets=[], warnings=[]),
        ),
        patch("app.api.projects.asyncio.to_thread", new=AsyncMock(return_value=b"xlsx")),
    ):
        response = asyncio.run(
            get_project_workspace_file_preview(
                PROJECT_ID,
                path="projects/demo/01-cost/Cost_Plan_v04.draft.xlsx",
                user=_User(),
                session=session,
            )
        )

    flush.assert_awaited_once_with(PROJECT_ID)
    assert response.filename == "Cost_Plan_v05.draft.xlsx"
    assert response.workspace_path == "projects/demo/01-cost/Cost_Plan_v05.draft.xlsx"


def test_workbook_download_flushes_pending_rebuild_once() -> None:
    session = AsyncMock()
    project = SimpleNamespace(
        id=PROJECT_ID,
        owner_user_id=USER_ID,
        workspace_path="projects/demo",
    )
    refreshed = SimpleNamespace(
        filename="Cost_Plan_v05.draft.xlsx",
        workspace_path="projects/demo/01-cost/Cost_Plan_v05.draft.xlsx",
        storage_key="storage/key-v5",
    )
    flush = AsyncMock(return_value=True)

    with (
        patch(
            "app.api.projects.get_project",
            new=AsyncMock(return_value=project),
        ),
        patch(
            "app.api.projects._require_project_owner",
            return_value=project,
        ),
        patch(
            "app.api.projects.flush_cost_plan_workbook_rebuild",
            flush,
        ),
        patch(
            "app.api.projects.read_canonical_cost_plan",
            new=AsyncMock(return_value=SimpleNamespace(version=5)),
        ),
        patch(
            "app.api.projects.cost_plan_workbook_workspace_path",
            return_value="projects/demo/01-cost/Cost_Plan_v05.draft.xlsx",
        ),
        patch(
            "app.api.projects.get_workspace_file_by_path",
            new=AsyncMock(return_value=refreshed),
        ),
        patch(
            "app.api.projects.asyncio.to_thread",
            new=AsyncMock(return_value=b"newest-xlsx"),
        ),
    ):
        response = asyncio.run(
            download_project_workspace_file(
                PROJECT_ID,
                path="projects/demo/01-cost/Cost_Plan_v04.draft.xlsx",
                user=_User(),
                session=session,
            )
        )

    flush.assert_awaited_once_with(PROJECT_ID)
    assert response.body == b"newest-xlsx"
    assert "Cost_Plan_v05.draft.xlsx" in response.headers["content-disposition"]
