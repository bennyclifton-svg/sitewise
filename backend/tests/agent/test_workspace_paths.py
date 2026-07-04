import uuid

import pytest

from app.agent.workspace_paths import (
    WorkspacePathError,
    normalize_workspace_path,
    project_workspace_root,
    resolve_workspace_path,
)
from app.config import settings

PROJECT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_PROJECT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def test_normal_relative_path_resolves_inside_project_root(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "agent_workspace_root", tmp_path)

    resolved = resolve_workspace_path(PROJECT_ID, "notes/report.md")

    assert resolved == (tmp_path / str(PROJECT_ID) / "notes" / "report.md").resolve(
        strict=False
    )
    assert normalize_workspace_path("notes\\report.md") == "notes/report.md"


@pytest.mark.parametrize(
    "path",
    [
        "../../etc/passwd",
        "notes/../../../secret.txt",
        "/var/tmp/secret.txt",
        r"C:\Users\someone\secret.txt",
        "//server/share/secret.txt",
        "notes/with:colon.txt",
    ],
)
def test_unsafe_paths_are_rejected(monkeypatch, tmp_path, path):
    monkeypatch.setattr(settings, "agent_workspace_root", tmp_path)

    with pytest.raises(WorkspacePathError):
        resolve_workspace_path(PROJECT_ID, path)


def test_symlink_escape_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "agent_workspace_root", tmp_path)
    root = project_workspace_root(PROJECT_ID)
    root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is not available in this environment")

    with pytest.raises(WorkspacePathError):
        resolve_workspace_path(PROJECT_ID, "escape/file.md")


def test_project_roots_do_not_overlap(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "agent_workspace_root", tmp_path)

    first = resolve_workspace_path(PROJECT_ID, "notes/report.md")
    other_root = project_workspace_root(OTHER_PROJECT_ID).resolve(strict=False)

    assert first.is_relative_to(project_workspace_root(PROJECT_ID).resolve(strict=False))
    assert not first.is_relative_to(other_root)
