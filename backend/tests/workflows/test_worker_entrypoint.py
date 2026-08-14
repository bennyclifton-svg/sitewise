from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.workflows import worker_entrypoint
from app.workflows import worker as workflow_worker
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


class _Factory:
    def __init__(self, session) -> None:
        self.session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_args):
        return False


def test_worker_failure_logs_error_class_without_provider_detail() -> None:
    provider_detail = "provider-workflow-secret-" + ("x" * 24)
    run = SimpleNamespace(
        id=uuid.uuid4(),
        workflow_type="create_project_plan",
    )
    session = AsyncMock()

    async def _run() -> None:
        with (
            patch.object(
                workflow_worker,
                "claim_next_run",
                new=AsyncMock(return_value=run),
            ),
            patch.object(
                workflow_worker,
                "_heartbeat_loop",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                workflow_worker,
                "_dispatch",
                new=AsyncMock(side_effect=RuntimeError(provider_detail)),
            ),
            patch.object(
                workflow_worker,
                "fail_workflow_run",
                new=AsyncMock(),
            ),
            patch.object(workflow_worker.log, "error") as log_error,
        ):
            processed = await workflow_worker.run_once(_Factory(session), "worker-1")

        assert processed is True
        assert log_error.call_args.kwargs["error_type"] == "RuntimeError"
        assert "error" not in log_error.call_args.kwargs
        assert provider_detail not in str(log_error.call_args)

    run_async(_run())


def test_worker_lane_logs_error_class_without_traceback() -> None:
    shutdown = asyncio.Event()
    provider_detail = "provider-lane-secret-" + ("x" * 24)

    async def failing_once(_factory, _worker_id):
        shutdown.set()
        raise RuntimeError(provider_detail)

    async def _run() -> None:
        with (
            patch.object(workflow_worker, "run_once", new=failing_once),
            patch.object(workflow_worker.log, "error") as log_error,
        ):
            await workflow_worker.run_lane(AsyncMock(), "worker-1", shutdown)

        assert log_error.call_args.kwargs["error_type"] == "RuntimeError"
        assert "error" not in log_error.call_args.kwargs
        assert provider_detail not in str(log_error.call_args)

    run_async(_run())
