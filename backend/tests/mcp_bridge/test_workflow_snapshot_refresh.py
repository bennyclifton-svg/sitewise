"""Snapshot-conflict recovery when a turn mutates the profile then launches.

Regression: a chat turn that accepted a profile proposal and then queued the
PMP failed with "Workflow inputs changed: profile revision". The agent read the
snapshot at turn start, the acceptance bumped profile_revision mid-turn, and the
optimistic-concurrency guard rejected the launch. The user was told the request
"requires a fresh workflow submission" and no artefact was ever produced.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.mcp_bridge import server
from app.workflows.runs import WorkflowRunCapabilityConflict
from tests.conftest import run_async

PROJECT_ID = "22222222-2222-2222-2222-222222222222"


class _Session:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    async def commit(self):
        return None


def _install(monkeypatch, *, snapshots, persist):
    """Wire the minimum surface _start_mcp_workflow touches."""
    project = SimpleNamespace(
        id=uuid.UUID(PROJECT_ID), owner_user_id=uuid.uuid4()
    )
    claims = SimpleNamespace(turn_id=uuid.uuid4(), user_id=uuid.uuid4())
    authorization = SimpleNamespace(project=project, claims=claims)

    monkeypatch.setattr(server, "get_session_factory", lambda: _Session)
    monkeypatch.setattr(
        server,
        "authorize_project_mutation_with_claims",
        AsyncMock(return_value=authorization),
    )
    monkeypatch.setattr(server, "_auth_header", lambda: "Bearer test")
    monkeypatch.setattr(
        server, "read_project_snapshot", AsyncMock(side_effect=snapshots)
    )
    monkeypatch.setattr(server, "capability_block_message", lambda *_a, **_k: None)
    monkeypatch.setattr(server, "persist_workflow_run", persist)
    monkeypatch.setattr(
        server.agent_turn_status_bus, "publish", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        server.WorkflowRunView,
        "model_validate",
        classmethod(
            lambda _cls, run: SimpleNamespace(
                model_dump=lambda mode="json": {"id": str(run.id), "status": "queued"}
            )
        ),
    )
    return authorization


def _snapshot(fingerprint: str, profile_revision: int, decision_revision: int):
    return SimpleNamespace(
        content_fingerprint=fingerprint,
        profile=SimpleNamespace(profile_revision=profile_revision),
        decisions=SimpleNamespace(set_revision=decision_revision),
    )


def test_launch_retries_once_against_refreshed_snapshot(monkeypatch) -> None:
    # The project already moved to revision 2 (the proposal this same turn
    # accepted); the agent is still holding the revision-1 expectations it
    # froze at turn start.
    fresh = _snapshot("b" * 64, 2, 3)
    attempts: list[tuple[str, int]] = []

    async def persist(_session, *, project, user_id, workflow_type, request, snapshot):
        attempts.append(
            (
                request.expected_snapshot_fingerprint,
                request.expected_profile_revision,
            )
        )
        if request.expected_profile_revision != snapshot.profile.profile_revision:
            raise WorkflowRunCapabilityConflict(
                "Workflow inputs changed: profile revision"
            )
        return SimpleNamespace(id=uuid.uuid4()), True

    _install(monkeypatch, snapshots=[fresh, fresh], persist=persist)

    result = run_async(
        server._start_mcp_workflow(
            project_id=PROJECT_ID,
            workflow_type="create_project_plan",
            idempotency_key="turn-1:pmp",
            expected_snapshot_fingerprint="a" * 64,
            expected_profile_revision=1,
            expected_decision_set_revision=3,
        )
    )

    assert result["status"] == "queued"
    assert result["snapshot_refreshed"] is True
    assert attempts == [("a" * 64, 1), ("b" * 64, 2)]


def test_launch_does_not_retry_more_than_once(monkeypatch) -> None:
    """A genuinely unstable project must still surface the conflict."""
    moving = [
        _snapshot("a" * 64, 1, 3),
        _snapshot("b" * 64, 2, 3),
        _snapshot("c" * 64, 3, 3),
    ]
    calls = {"n": 0}

    async def persist(_session, *, project, user_id, workflow_type, request, snapshot):
        calls["n"] += 1
        raise WorkflowRunCapabilityConflict("Workflow inputs changed: profile revision")

    _install(monkeypatch, snapshots=moving, persist=persist)

    with pytest.raises(server.ToolError) as excinfo:
        run_async(
            server._start_mcp_workflow(
                project_id=PROJECT_ID,
                workflow_type="create_project_plan",
                idempotency_key="turn-1:pmp",
                expected_snapshot_fingerprint="a" * 64,
                expected_profile_revision=1,
                expected_decision_set_revision=3,
            )
        )

    assert "workflow_run_conflict" in str(excinfo.value)
    assert calls["n"] == 2


def test_capability_block_is_not_retried(monkeypatch) -> None:
    """A blocked capability is a real refusal, not a stale-snapshot race."""
    calls = {"n": 0}

    async def persist(_session, **_kwargs):
        calls["n"] += 1
        raise AssertionError("must not reach persist")

    _install(
        monkeypatch,
        snapshots=[_snapshot("a" * 64, 1, 3), _snapshot("a" * 64, 1, 3)],
        persist=persist,
    )
    monkeypatch.setattr(
        server, "capability_block_message", lambda *_a, **_k: "Cost plan is locked"
    )

    with pytest.raises(server.ToolError) as excinfo:
        run_async(
            server._start_mcp_workflow(
                project_id=PROJECT_ID,
                workflow_type="create_project_plan",
                idempotency_key="turn-1:pmp",
                expected_snapshot_fingerprint="a" * 64,
                expected_profile_revision=1,
                expected_decision_set_revision=3,
            )
        )

    assert "Cost plan is locked" in str(excinfo.value)
    assert calls["n"] == 0
