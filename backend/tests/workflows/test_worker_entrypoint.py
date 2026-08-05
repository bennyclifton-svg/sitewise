from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.workflows import worker_entrypoint
from tests.conftest import run_async


def test_worker_entrypoint_accepts_process_invoices() -> None:
    worker_entrypoint.validate_required_workflows(["process_invoices"])


def test_worker_entrypoint_rejects_an_unsupported_required_workflow() -> None:
    with pytest.raises(RuntimeError, match="missing required workflows: future_workflow"):
        worker_entrypoint.validate_required_workflows(["future_workflow"])


def test_worker_entrypoint_runs_healthcheck_after_capability_validation(
    monkeypatch,
) -> None:
    healthcheck = AsyncMock()
    worker = AsyncMock()
    monkeypatch.setattr(worker_entrypoint, "_healthcheck", healthcheck)
    monkeypatch.setattr(worker_entrypoint, "_main", worker)

    run_async(
        worker_entrypoint.run(
            required_workflows=["process_invoices"],
            healthcheck=True,
        )
    )

    healthcheck.assert_awaited_once_with()
    worker.assert_not_awaited()
