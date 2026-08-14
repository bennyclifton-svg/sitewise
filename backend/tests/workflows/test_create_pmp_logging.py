from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.workflows.create_pmp import _publish_preview, _publish_progress
from tests.conftest import run_async


def test_preview_publish_failure_logs_only_exception_class() -> None:
    canary = "ch03-preview-provider-token-xxxxxxxxxxxxxxxxxxxxxxxx"
    publisher = AsyncMock(side_effect=RuntimeError(canary))

    with patch("app.workflows.create_pmp.log.warning") as log_warning:
        run_async(_publish_preview(publisher, stage="drafting", markdown="safe"))

    assert log_warning.call_args.kwargs["error_type"] == "RuntimeError"
    assert canary not in str(log_warning.call_args)


def test_progress_publish_failure_logs_only_exception_class() -> None:
    canary = "ch03-progress-provider-token-xxxxxxxxxxxxxxxxxxxxxxxx"
    publisher = AsyncMock(side_effect=RuntimeError(canary))

    with patch("app.workflows.create_pmp.log.warning") as log_warning:
        run_async(_publish_progress(publisher, {"stage": "saving"}))

    assert log_warning.call_args.kwargs["error_type"] == "RuntimeError"
    assert canary not in str(log_warning.call_args)
