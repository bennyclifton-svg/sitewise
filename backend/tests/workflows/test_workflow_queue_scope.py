"""Queue scope keeps each environment's workflow runs to its own worker.

Every deployment pointed at one Supabase project polls the same
`workflow_runs` table. Before this, a run queued from local dev could be
claimed and executed by production running different code — which is how two
Wave 2 cost plans came out of two different compilers.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from app.database.workflow_run import WorkflowRun
from app.schemas.workflow_runs import WorkflowRunStartRequest
from app.workflows.runs import start_workflow_run
from app.workflows.worker import _stamp_result_dependencies
from tests.conftest import run_async
from tests.workflows.test_workflow_runs import (
    _RunSession,
    _project_for_snapshot,
    _snapshot,
)


def _start(scope: str) -> WorkflowRun:
    snapshot = _snapshot()
    project = _project_for_snapshot(snapshot, context_version=1)
    request = WorkflowRunStartRequest.model_validate(
        {
            "idempotency_key": "turn-1:create-project-plan",
            "expected_snapshot_fingerprint": snapshot.content_fingerprint,
            "expected_profile_revision": 2,
            "expected_decision_set_revision": 3,
            "parameters": {},
        }
    )
    with (
        patch("app.workflows.runs.settings.workflow_queue_scope", scope),
        patch("app.workflows.runs.lock_project", new=AsyncMock(return_value=project)),
        patch(
            "app.workflows.runs._find_idempotent_run", new=AsyncMock(return_value=None)
        ),
        patch(
            "app.workflows.runs.publish_project_event", new=AsyncMock(return_value=None)
        ),
    ):
        run, created = run_async(
            start_workflow_run(
                _RunSession(),
                project=project,
                user_id=project.owner_user_id,
                workflow_type="create_project_plan",
                request=request,
                snapshot=snapshot,
            )
        )
    assert created is True
    return run


@pytest.mark.parametrize("scope", ["dev", "production", "staging"])
def test_enqueue_stamps_the_configured_queue_scope(scope: str) -> None:
    assert _start(scope).queue_scope == scope


def test_claim_query_filters_on_queue_scope() -> None:
    """The scope predicate must be in the SQL, not applied after the fetch.

    `claim_next_run` locks one row with FOR UPDATE SKIP LOCKED. Filtering in
    Python would still let a foreign-scope row be locked and skipped by its
    rightful owner, so the predicate has to reach the database.
    """
    captured: list[str] = []

    class _CaptureSession:
        async def execute(self, statement):
            captured.append(
                str(
                    statement.compile(
                        dialect=postgresql.dialect(),
                        compile_kwargs={"literal_binds": True},
                    )
                )
            )
            raise _Stop()

        async def commit(self) -> None:  # pragma: no cover - never reached
            pass

    class _Stop(Exception):
        pass

    from app.workflows import runs as runs_module

    with (
        patch.object(
            runs_module,
            "_finalize_one_expired_cancellation",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            runs_module, "_fail_one_exhausted_lease", new=AsyncMock(return_value=None)
        ),
        pytest.raises(_Stop),
    ):
        run_async(
            runs_module.claim_next_run(
                _CaptureSession(), worker_id="w", queue_scope="dev"
            )
        )

    assert captured, "claim_next_run issued no query"
    sql = captured[0]
    assert "queue_scope" in sql
    assert "'dev'" in sql


def test_lease_sweepers_only_touch_their_own_scope() -> None:
    """A dev worker must not fail or cancel production's expired runs.

    Both sweepers run on every claim poll, so an unscoped sweep would let the
    quieter environment reap the busier one's work.
    """
    from app.workflows import runs as runs_module

    captured: list[str] = []

    class _CaptureSession:
        async def execute(self, statement):
            captured.append(
                str(
                    statement.compile(
                        dialect=postgresql.dialect(),
                        compile_kwargs={"literal_binds": True},
                    )
                )
            )
            return SimpleNamespace(first=lambda: None)

        async def rollback(self) -> None:  # pragma: no cover - not reached
            pass

    run_async(
        runs_module._finalize_one_expired_cancellation(
            _CaptureSession(), queue_scope="dev"
        )
    )
    run_async(
        runs_module._fail_one_exhausted_lease(_CaptureSession(), queue_scope="dev")
    )

    assert len(captured) == 2
    for sql in captured:
        assert "queue_scope" in sql
        assert "'dev'" in sql


def test_artefact_provenance_records_build_and_scope() -> None:
    """An artefact has to say which build and which environment made it."""
    draft = SimpleNamespace(
        id=uuid.uuid4(),
        workflow_type="create_pmp",
        model="openai-responses:gpt-5.6-terra",
        runtime="clerk-sitewise-create-pmp-adaptive-scaffold",
        provenance_metadata={"draft_mode": "platform_seeded"},
    )
    run = SimpleNamespace(
        frozen_artefact_version=None,
        frozen_profile_revision=2,
        frozen_evidence_fingerprint="b" * 64,
        frozen_decision_set_revision=3,
        frozen_project_context_version=3,
        queue_scope="dev",
    )

    class _Session:
        async def get(self, _model, _id):
            return draft

        async def flush(self) -> None:
            pass

    with patch("app.workflows.worker.build_version", return_value="a1b2c3d4-dirty"):
        run_async(
            _stamp_result_dependencies(
                _Session(), run, {"draft": {"id": str(draft.id)}}
            )
        )

    snapshot = draft.provenance_metadata["dependency_snapshot"]
    assert snapshot["build_version"] == "a1b2c3d4-dirty"
    assert snapshot["queue_scope"] == "dev"
    assert snapshot["runtime_version"] == "clerk-sitewise-create-pmp-adaptive-scaffold"
