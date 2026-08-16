from app.programme.models import ProgrammeActivity, ProgrammeVersion


def test_programme_table_names() -> None:
    assert ProgrammeVersion.__tablename__ == "programme_versions"
    assert ProgrammeActivity.__tablename__ == "programme_activities"


def test_programme_constraint_names() -> None:
    version_args = ProgrammeVersion.__table_args__
    activity_args = ProgrammeActivity.__table_args__
    version_names = {item.name for item in version_args if hasattr(item, "name")}
    activity_names = {item.name for item in activity_args if hasattr(item, "name")}
    assert "ck_programme_versions_status" in version_names
    assert "ck_programme_versions_view_scale" in version_names
    assert "uq_programme_versions_project_version" in version_names
    assert "ix_programme_versions_project_status" in version_names
    assert "uq_programme_activities_version_key" in activity_names
    assert "ck_programme_activities_kind" in activity_names


def test_programme_unique_column_pairs() -> None:
    version_unique = next(
        item
        for item in ProgrammeVersion.__table_args__
        if getattr(item, "name", None) == "uq_programme_versions_project_version"
    )
    activity_unique = next(
        item
        for item in ProgrammeActivity.__table_args__
        if getattr(item, "name", None) == "uq_programme_activities_version_key"
    )
    assert list(version_unique.columns.keys()) == ["project_id", "version"]
    assert list(activity_unique.columns.keys()) == [
        "programme_version_id",
        "activity_key",
    ]
