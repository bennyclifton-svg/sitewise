from app.database.projects import slug_from_title
from app.email.alias_names import is_reserved_inbound_local_part


def test_slug_from_title_normalises_project_names() -> None:
    assert slug_from_title("  My New Project: Stage 01  ") == "my-new-project-stage-01"


def test_slug_from_title_falls_back_for_symbol_only_names() -> None:
    assert slug_from_title("!!!") == "project"


def test_reserved_inbound_slugs_are_blocked() -> None:
    assert is_reserved_inbound_local_part("support")
    assert is_reserved_inbound_local_part("Hello")
    assert not is_reserved_inbound_local_part("wianamatta-avenue")

