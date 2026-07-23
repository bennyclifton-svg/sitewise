"""Stable workspace paths (e.g. PMP.md) must reclaim artefact_exports.storage_key."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.projects.artefact_revisions import (
    ArtefactPolicyViolation,
    _reclaim_export_storage_keys,
)
from tests.conftest import run_async


def test_reclaim_export_storage_keys_deletes_same_project_rows() -> None:
    project_id = uuid.uuid4()
    other_draft = uuid.uuid4()
    old = SimpleNamespace(
        id=uuid.uuid4(),
        project_id=project_id,
        draft_id=other_draft,
        storage_key=f"{project_id}/04-projects/demo/00-brief-pmp/PMP.md",
    )
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [old]
    session.execute = AsyncMock(return_value=result)
    session.delete = AsyncMock()
    session.flush = AsyncMock()

    removed = run_async(
        _reclaim_export_storage_keys(
            session,
            project_id=project_id,
            storage_keys=[old.storage_key],
        )
    )

    assert removed == 1
    session.delete.assert_awaited_once_with(old)
    session.flush.assert_awaited_once()


def test_reclaim_export_storage_keys_rejects_other_project() -> None:
    project_id = uuid.uuid4()
    foreign = SimpleNamespace(
        project_id=uuid.uuid4(),
        storage_key="other/PMP.md",
    )
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [foreign]
    session.execute = AsyncMock(return_value=result)

    try:
        run_async(
            _reclaim_export_storage_keys(
                session,
                project_id=project_id,
                storage_keys=[foreign.storage_key],
            )
        )
        raised = None
    except ArtefactPolicyViolation as exc:
        raised = exc

    assert raised is not None
    assert "another project" in str(raised)


def test_reclaim_export_storage_keys_noop_when_empty() -> None:
    session = AsyncMock()
    removed = run_async(
        _reclaim_export_storage_keys(
            session,
            project_id=uuid.uuid4(),
            storage_keys=[],
        )
    )
    assert removed == 0
    session.execute.assert_not_called()
