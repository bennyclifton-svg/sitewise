import pytest

from app.inbox.paths import (
    InboxPathError,
    build_inbox_workspace_path,
    build_storage_key,
    sanitize_inbox_relative_path,
    sanitize_filename,
)


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
