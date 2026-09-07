from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import uuid

import pytest

from app.agent.project_plan import project_plan_command, queue_project_plan
from app.workflows.runs import WorkflowRunCapabilityConflict
from tests.conftest import run_async
from tests.workflows.test_workflow_runs import _snapshot, _project_for_snapshot


@pytest.mark.parametrize(
    "command",
    [
        "Create PMP",
        "Please create a project management plan.",
        "Can you generate the project plan from the saved project profile?",
        "Draft a PMP using my current project snapshot",
        "Prepare the PMP now",
    ],
)
def test_explicit_creation(command):
    assert project_plan_command(command) == "create_project_plan"


@pytest.mark.parametrize(
    "command",
    [
        "Do not create PMP",
        "How do I create a PMP?",
        'Explain "Create PMP"',
        "Create PMP and change the budget to 1000000",
        "Create a PMP template",
        "Can you create a project plan if I upload documents?",
        "I asked it to create PMP",
    ],
)
def test_discussion_or_compound_request_is_not_executed(command):
    assert project_plan_command(command) is None


def test_update_command():
    assert project_plan_command("Update PMP") == "refresh_project_plan"


@pytest.mark.parametrize("existing", [None, SimpleNamespace(id=uuid.uuid4())])
def test_profile_only_request_commits_one_job_or_reuses_active_job(existing):
    snapshot = _snapshot()
    project = _project_for_snapshot(snapshot, context_version=1)
    session = AsyncMock()
    session.scalar.return_value = existing
    queued = SimpleNamespace(id=uuid.uuid4())
    start = AsyncMock(return_value=(queued, True))
    with (
        patch("app.agent.project_plan.lock_project", AsyncMock(return_value=project)),
        patch(
            "app.agent.project_plan.get_project_snapshot",
            AsyncMock(return_value=snapshot),
        ),
        patch("app.agent.project_plan.start_workflow_run", start),
    ):
        result = run_async(
            queue_project_plan(
                session,
                project_id=project.id,
                user_id=project.owner_user_id,
                thread_id=uuid.uuid4(),
                turn_id=uuid.uuid4(),
                workflow_type="create_project_plan",
            )
        )
    assert result is (existing or queued)
    if existing:
        start.assert_not_awaited()
    else:
        session.commit.assert_awaited_once()
        assert start.call_args.kwargs["snapshot"].evidence.active_count == 0
        assert start.call_args.kwargs["request"].expected_profile_revision == 2


def test_incomplete_profile_cannot_claim_to_be_queued():
    snapshot = _snapshot()
    snapshot.profile.state = None
    project = _project_for_snapshot(snapshot, context_version=1)
    session = AsyncMock()
    session.scalar.return_value = None
    with (
        patch("app.agent.project_plan.lock_project", AsyncMock(return_value=project)),
        patch(
            "app.agent.project_plan.get_project_snapshot",
            AsyncMock(return_value=snapshot),
        ),
        pytest.raises(WorkflowRunCapabilityConflict, match="state"),
    ):
        run_async(
            queue_project_plan(
                session,
                project_id=project.id,
                user_id=project.owner_user_id,
                thread_id=uuid.uuid4(),
                turn_id=uuid.uuid4(),
                workflow_type="create_project_plan",
            )
        )
    session.commit.assert_not_awaited()
