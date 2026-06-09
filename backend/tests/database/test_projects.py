from app.database.projects import slug_from_title


def test_slug_from_title_normalises_project_names() -> None:
    assert slug_from_title("  My New Project: Stage 01  ") == "my-new-project-stage-01"


def test_slug_from_title_falls_back_for_symbol_only_names() -> None:
    assert slug_from_title("!!!") == "project"

