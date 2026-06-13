import pytest

from app.inbox.paths import (
    InboxPathError,
    build_inbox_workspace_path,
    build_storage_key,
    sanitize_inbox_relative_path,
    sanitize_filename,
)
from app.storage.keys import sanitize_storage_key


def test_build_inbox_workspace_path_defaults_to_inbox_root() -> None:
    path = build_inbox_workspace_path(
        "04-projects/demo",
        filename="report.pdf",
    )
    assert path == "04-projects/demo/_inbox/report.pdf"


def test_build_inbox_workspace_path_preserves_nested_relative_path() -> None:
    path = build_inbox_workspace_path(
        "04-projects/demo",
        filename="CC-A-010 SITE PLAN.pdf",
        relative_path="ARCHITECTURE/CC 010 _ SITE PLAN",
    )
    assert path == "04-projects/demo/_inbox/ARCHITECTURE/CC 010 _ SITE PLAN/CC-A-010 SITE PLAN.pdf"


def test_sanitize_inbox_relative_path_rejects_parent_segments() -> None:
    with pytest.raises(InboxPathError):
        sanitize_inbox_relative_path("../secrets")


def test_sanitize_filename_rejects_empty() -> None:
    with pytest.raises(InboxPathError):
        sanitize_filename("   ")


def test_build_storage_key_scopes_by_project() -> None:
    key = build_storage_key(
        "11111111-1111-1111-1111-111111111111",
        "04-projects/demo/_inbox/report.pdf",
    )
    assert key.startswith("11111111-1111-1111-1111-111111111111/")


def test_sanitize_storage_key_replaces_square_brackets() -> None:
    sanitized = sanitize_storage_key(
        "E00 - ELECTRICAL - COVER SHEET - [C1].pdf",
    )
    assert "[" not in sanitized
    assert "]" not in sanitized
    assert sanitized == "E00 - ELECTRICAL - COVER SHEET - _C1_.pdf"


def test_sanitize_storage_key_replaces_tilde_in_windows_short_names() -> None:
    sanitized = sanitize_storage_key("E01-EL~1.PDF")
    assert "~" not in sanitized
    assert sanitized == "E01-EL_1.PDF"


def test_build_storage_key_sanitizes_revision_brackets_in_filename() -> None:
    key = build_storage_key(
        "11111111-1111-1111-1111-111111111111",
        "04-projects/demo/_inbox/E00 - ELECTRICAL - COVER SHEET - [C1].pdf",
    )
    assert "[" not in key
    assert "]" not in key
    assert key.endswith("E00 - ELECTRICAL - COVER SHEET - _C1_.pdf")
