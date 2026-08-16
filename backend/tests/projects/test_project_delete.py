"""Owned project delete collects storage keys and removes the row."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.projects.project_delete import delete_owned_project
from tests.conftest import run_async


PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _execute_result(scalars_all: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = scalars_all
    return result


def test_delete_owned_project_returns_storage_keys_and_deletes() -> None:
    project = SimpleNamespace(id=PROJECT_ID, slug="demo")
    session = AsyncMock()
    session.scalars = AsyncMock(
        side_effect=[
            SimpleNamespace(all=lambda: ["demo/_inbox/brief.pdf", ""]),
            SimpleNamespace(all=lambda: ["demo/pmp.docx"]),
        ]
    )

    keys = run_async(delete_owned_project(session, project=project))

    assert keys == ["demo/_inbox/brief.pdf", "demo/pmp.docx"]
    session.delete.assert_not_called()
    session.flush.assert_awaited()
    session.commit.assert_awaited_once()


def test_delete_owned_project_clears_restrict_children_before_project() -> None:
    project = SimpleNamespace(id=PROJECT_ID, slug="demo")
    order: list[tuple[str, str]] = []
    session = AsyncMock()
    session.scalars = AsyncMock(
        side_effect=[
            SimpleNamespace(all=lambda: []),
            SimpleNamespace(all=lambda: []),
        ]
    )

    async def _execute(stmt, *args, **kwargs):  # noqa: ANN001
        order.append(("execute", stmt.table.name))
        return _execute_result([])

    session.execute = AsyncMock(side_effect=_execute)

    run_async(delete_owned_project(session, project=project))

    assert order == [
        ("execute", "programme_versions"),
        ("execute", "cost_plan_versions"),
        ("execute", "procurement_requests"),
        ("execute", "workflow_input_retention_locks"),
        ("execute", "project_document_selection_items"),
        ("execute", "chat_threads"),
        ("execute", "projects"),
    ]
    session.delete.assert_not_called()
