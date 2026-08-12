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
    session = _Session(project)

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


def test_write_shared_object_accepts_detached_project_like_workflow_worker() -> None:
    """Workflow workers pass a frozen Project that is not in the SQLAlchemy session."""
    project_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    persistent = Project(
        id=project_id,
        owner_user_id=owner_id,
        slug="walsh-2",
        title="WALSH 2",
        workspace_path="04-projects/walsh-2",
        phase="brief-planning",
        project_context_version=5,
        event_sequence=2,
        project_metadata={},
    )
    detached = Project(
        id=project_id,
        owner_user_id=owner_id,
        slug="walsh-2",
        title="WALSH 2",
        workspace_path="04-projects/walsh-2",
        phase="brief-planning",
        project_context_version=5,
        event_sequence=2,
        project_metadata={},
    )
    session = _Session(persistent)

    result = asyncio.run(
        write_shared_project_object(
            session,
            project=detached,
            kind="consultant",
            object_id="hydraulic",
            update=SharedProjectObjectUpdate(
                expected_revision=0,
                value={"firm": "TDL Engineering", "discipline": "Hydraulic"},
            ),
            source="evidence",
        )
    )

    assert result.revision == 1
    assert session.locked is True
    assert persistent.project_context_version == 6
    assert persistent.event_sequence == 3
    assert detached.project_context_version == 6
    assert detached.project_metadata["shared_knowledge"]["consultant:hydraulic"][
        "value"
    ]["firm"] == "TDL Engineering"


class _Session:
    def __init__(self, project: Project) -> None:
        self.locked = False
        self.added = []
        self._project = project

    async def get(self, model, ident, **kwargs):
        assert model is Project
        assert ident == self._project.id
        self.locked = bool(kwargs.get("with_for_update"))
        return self._project

    async def refresh(self, _project, **kwargs) -> None:
        raise RuntimeError(
            f"Instance '{_project!r}' is not persistent within this Session"
        )

    def add(self, row) -> None:
        self.added.append(row)

    async def flush(self) -> None:
        pass
