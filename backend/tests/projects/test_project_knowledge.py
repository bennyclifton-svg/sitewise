import asyncio
import uuid

from app.database.project import Project
from app.projects.project_knowledge import (
    SharedProjectObjectConflict,
    SharedProjectObjectUpdate,
    upsert_shared_project_object,
    write_shared_project_object,
)


def test_consultant_fact_marks_only_explicit_dependants_dirty() -> None:
    project = Project(project_metadata={})
    result = upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="hydraulic",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={"name": "Fluid Design"},
        ),
        source="user",
    )

    assert result.revision == 1
    assert project.project_metadata["dirty_categories"] == ["consultants_dirty"]
    assert {
        item["artefact_type"] for item in project.project_metadata["affected_artefacts"]
    } == {
        "pmp",
        "rfp",
        "consultant_register",
        "cost_plan",
    }


def test_user_protection_rejects_later_ai_overwrite() -> None:
    project = Project(project_metadata={})
    upsert_shared_project_object(
        project,
        kind="consultant",
        object_id="hydraulic",
        update=SharedProjectObjectUpdate(
            expected_revision=0,
            value={"name": "Fluid Design"},
            user_protected=True,
        ),
        source="user",
    )

    try:
        upsert_shared_project_object(
            project,
            kind="consultant",
            object_id="hydraulic",
            update=SharedProjectObjectUpdate(
                expected_revision=1,
                value={"name": "ABC Engineering"},
            ),
            source="ai",
        )
    except SharedProjectObjectConflict as exc:
        assert "protected" in str(exc)
    else:
        raise AssertionError("AI overwrite should have been rejected")


def test_persisted_shared_object_locks_project_and_advances_context_once() -> None:
    project = Project(
        id=uuid.uuid4(),
        owner_user_id=uuid.uuid4(),
        slug="demo",
        title="Demo",
        workspace_path="04-projects/demo",
        phase="brief-planning",
        project_context_version=5,
        event_sequence=2,
        project_metadata={},
    )
    session = _Session()

    result = asyncio.run(
        write_shared_project_object(
            session,
            project=project,
            kind="milestone",
            object_id="practical-completion",
            update=SharedProjectObjectUpdate(
                expected_revision=0,
                value={"date": "2027-03-01"},
            ),
            source="user",
        )
    )

    assert result.revision == 1
    assert session.locked is True
    assert project.project_context_version == 6
    assert project.event_sequence == 3
    assert len(session.added) == 1
    event = session.added[0]
    assert event.resource_type == "shared_project_object"
    assert event.resource_id == "practical-completion"


class _Session:
    def __init__(self) -> None:
        self.locked = False
        self.added = []

    async def refresh(self, _project, **kwargs) -> None:
        self.locked = kwargs == {"with_for_update": True}

    def add(self, row) -> None:
        self.added.append(row)

    async def flush(self) -> None:
        pass
