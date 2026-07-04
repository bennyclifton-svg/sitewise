from __future__ import annotations

import uuid
from pathlib import Path, PurePosixPath, PureWindowsPath

from app.config import settings


class WorkspacePathError(ValueError):
    """Raised when a requested agent workspace path escapes its project root."""


def project_workspace_root(project_id: uuid.UUID) -> Path:
    return settings.agent_workspace_root / str(project_id)


def normalize_workspace_path(rel_path: str | None) -> str:
    raw = (rel_path or ".").strip()
    if raw in {"", "."}:
        return "."
    if "\x00" in raw:
        raise WorkspacePathError("workspace path contains a null byte")
    if (
        PurePosixPath(raw).is_absolute()
        or PureWindowsPath(raw).is_absolute()
        or PureWindowsPath(raw).drive
    ):
        raise WorkspacePathError("workspace path must be relative")

    normalised = raw.replace("\\", "/")
    parts = PurePosixPath(normalised).parts
    if not parts:
        return "."
    if any(part == ".." for part in parts):
        raise WorkspacePathError("workspace path must not contain traversal")
    if any(":" in part for part in parts):
        raise WorkspacePathError("workspace path contains an unsupported segment")
    return PurePosixPath(*parts).as_posix()


def resolve_workspace_path(project_id: uuid.UUID, rel_path: str | None = ".") -> Path:
    root = project_workspace_root(project_id).resolve(strict=False)
    normalised = normalize_workspace_path(rel_path)
    candidate = root if normalised == "." else root.joinpath(*normalised.split("/"))
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise WorkspacePathError("workspace path escapes the project root")
    return resolved

