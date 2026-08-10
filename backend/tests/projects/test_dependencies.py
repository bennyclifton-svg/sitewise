from app.database.project import Project
from app.projects.dependencies import (
    affected_artefacts,
    dirty_categories_for_profile_fields,
    mark_project_dirty,
)


def test_profile_changes_map_only_to_explicit_dependencies() -> None:
    dirty = dirty_categories_for_profile_fields(["work_scope"])
    affected = affected_artefacts(dirty)

    assert "scope_dirty" in dirty
    assert "cost_dirty" in dirty
    assert any(item.artefact_type == "cost_plan" for item in affected)
    assert not any("governance" in item.blocks for item in affected)


def test_project_records_dirty_categories_without_regenerating() -> None:
    project = Project(project_metadata={})
    mark_project_dirty(project, ["programme_dirty", "programme_dirty"])

    assert project.project_metadata["dirty_categories"] == ["programme_dirty"]
    assert {
        item["artefact_type"] for item in project.project_metadata["affected_artefacts"]
    } == {
        "pmp",
        "rfp",
        "rft",
    }
