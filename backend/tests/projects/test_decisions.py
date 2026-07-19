import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.database.project import Project
from app.database.project_decision import ProjectDecision
from app.projects.decisions import (
    DecisionLockedConflict,
    DecisionRevisionConflict,
    sync_decisions_from_markdown,
    update_project_decision,
)


PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


class _Result:
    def __init__(self, value=None, rows=None):
        self.value = value
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.rows


def _project() -> Project:
    return Project(
        id=PROJECT_ID,
        owner_user_id=uuid.uuid4(),
        slug="demo",
        title="Demo",
        workspace_path="04-projects/demo",
        decision_set_revision=4,
        event_sequence=0,
    )


def _decision(*, selected: str = "traditional", locked: bool = True) -> ProjectDecision:
    return ProjectDecision(
        id=uuid.uuid4(),
        project_id=PROJECT_ID,
        decision_id="procurement-route",
        section="Procurement",
        label="Procurement route",
        options=[
            {"value": "traditional", "label": "Traditional"},
            {"value": "design_construct", "label": "Design & Construct"},
        ],
        selected=selected,
        source="user" if locked else "agent",
        revision=3,
        locked=locked,
        evidence_conflict=False,
        agent_suggestion=None,
        provenance={},
        workflow_type="create_pmp",
    )


def test_generated_conflict_does_not_replace_locked_selection() -> None:
    project = _project()
    row = _decision()
    session = AsyncMock()
    session.execute.side_effect = [_Result(value=project), _Result(rows=[row])]
    markdown = """```pmp-decision
{"id":"procurement-route","section":"Procurement","label":"Procurement route",
"options":[{"value":"traditional","label":"Traditional"},{"value":"design_construct","label":"D&C"}],
"selected":"traditional","source":"user","evidence_conflict":true,
"agent_suggestion":"design_construct"}
```"""

    with patch(
        "app.projects.decisions.publish_project_event", new=AsyncMock()
    ) as publish:
        asyncio.run(
            sync_decisions_from_markdown(
                session,
                project_id=PROJECT_ID,
                markdown=markdown,
                workflow_type="create_pmp",
            )
        )

    assert row.selected == "traditional"
    assert row.locked is True
    assert row.evidence_conflict is True
    assert row.agent_suggestion == "design_construct"
    assert row.revision == 4
    assert project.decision_set_revision == 5
    assert publish.await_args.kwargs["action"] == "conflict_detected"


def test_stale_decision_revision_is_rejected_before_update() -> None:
    project = _project()
    row = _decision(locked=False)
    session = AsyncMock()
    session.execute.side_effect = [_Result(value=project), _Result(value=row)]

    with pytest.raises(DecisionRevisionConflict):
        asyncio.run(
            update_project_decision(
                session,
                project_id=PROJECT_ID,
                decision_id=row.decision_id,
                selected="design_construct",
                expected_revision=2,
                expected_set_revision=4,
                actor_source="user",
            )
        )

    assert row.selected == "traditional"
    assert project.decision_set_revision == 4


def test_agent_cannot_overwrite_locked_decision() -> None:
    project = _project()
    row = _decision()
    session = AsyncMock()
    session.execute.side_effect = [_Result(value=project), _Result(value=row)]

    with pytest.raises(DecisionLockedConflict):
        asyncio.run(
            update_project_decision(
                session,
                project_id=PROJECT_ID,
                decision_id=row.decision_id,
                selected="design_construct",
                expected_revision=3,
                expected_set_revision=4,
                actor_source="agent",
            )
        )

    assert row.selected == "traditional"
