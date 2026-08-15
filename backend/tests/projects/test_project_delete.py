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
            SimpleNamespace(
                all=lambda: [
                    SimpleNamespace(storage_key="demo/_inbox/brief.pdf"),
                    SimpleNamespace(storage_key=""),
                ]
            ),
            SimpleNamespace(
                all=lambda: [SimpleNamespace(storage_key="demo/pmp.docx")]
            ),
        ]
    )

    keys = run_async(delete_owned_project(session, project=project))

    assert keys == ["demo/_inbox/brief.pdf", "demo/pmp.docx"]
    session.delete.assert_awaited_once_with(project)
    session.flush.assert_awaited()
    session.commit.assert_awaited_once()
