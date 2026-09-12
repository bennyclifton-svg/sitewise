from __future__ import annotations

import asyncio
import uuid
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.api.projects import (
    _ensure_cost_plan_workspace_file,
    _cost_plan_workbook_bytes,
    _resolve_workspace_file_for_read,
    download_project_workspace_file,
    get_project_workspace_file_preview,
)


PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


class _User:
    id = USER_ID


def test_navigation_schedules_missing_workbook_without_building_it() -> None:
    project = SimpleNamespace(id=PROJECT_ID, workspace_path="projects/demo")
    summary = SimpleNamespace(version=5)
    with (
        patch(
            "app.api.projects.flush_cost_plan_workbook_rebuild", new=AsyncMock()
        ) as flush,
        patch(
            "app.api.projects.sync_cost_plan_revision_artifacts", new=AsyncMock()
        ) as build,
        patch("app.api.projects.schedule_cost_plan_workbook_rebuild") as schedule,
    ):
        files = asyncio.run(
            _ensure_cost_plan_workspace_file(
                AsyncMock(),
                project=project,
                workspace_files=[],
                draft_summaries={"create_cost_plan": summary},
            )
        )
    assert files == []
    schedule.assert_called_once_with(PROJECT_ID, 5)
    flush.assert_not_awaited()
    build.assert_not_awaited()


@pytest.mark.parametrize("requested_version", [4, 5])
def test_missing_workbook_repair_only_builds_the_requested_current_revision(
    requested_version,
) -> None:
    project = SimpleNamespace(id=PROJECT_ID, workspace_path="projects/demo")
    draft = SimpleNamespace(version=5)
    current_path = "projects/demo/01-cost/Cost_Plan_v05.draft.xlsx"
    path = f"projects/demo/01-cost/Cost_Plan_v{requested_version:02d}.draft.xlsx"
    record = SimpleNamespace(workspace_path=current_path)
    with (
        patch(
            "app.api.projects.flush_cost_plan_workbook_rebuild",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.api.projects.get_workspace_file_by_path",
            new=AsyncMock(side_effect=[None, record]),
        ),
        patch(
            "app.api.projects.get_latest_draft_artifact",
            new=AsyncMock(return_value=draft),
        ),
        patch(
            "app.api.projects.sync_cost_plan_revision_artifacts", new=AsyncMock()
        ) as build,
    ):
        result = asyncio.run(
            _resolve_workspace_file_for_read(
                AsyncMock(),
                project=project,
                workspace_path=path,
            )
        )
    if requested_version == 5:
        assert result is record
        build.assert_awaited_once()
    else:
        assert result is None
        build.assert_not_awaited()


def test_draft_download_recovers_its_own_missing_workbook() -> None:
    project = SimpleNamespace(id=PROJECT_ID, workspace_path="projects/demo")
    draft = SimpleNamespace(version=3, provenance_metadata={})
    path = "projects/demo/01-cost/Cost_Plan_v03.draft.xlsx"
    record = SimpleNamespace(filename="Cost_Plan_v03.draft.xlsx", storage_key="v3")
    session = AsyncMock()
    with (
        patch(
            "app.api.projects.flush_cost_plan_workbook_rebuild",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.api.projects.get_workspace_file_by_path",
            new=AsyncMock(side_effect=[None, record]),
        ) as lookup,
        patch(
            "app.api.projects.sync_cost_plan_revision_artifacts", new=AsyncMock()
        ) as build,
        patch(
            "app.api.projects.asyncio.to_thread", new=AsyncMock(return_value=b"v3-xlsx")
        ),
    ):
        content, filename = asyncio.run(
            _cost_plan_workbook_bytes(session, project=project, draft=draft)
        )
    assert content == b"v3-xlsx"
    assert filename == record.filename
    build.assert_awaited_once_with(session, project=project, draft=draft)
    assert lookup.await_args.kwargs["workspace_path"] == path


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
        patch(
            "app.api.projects.asyncio.to_thread", new=AsyncMock(return_value=b"xlsx")
        ),
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
