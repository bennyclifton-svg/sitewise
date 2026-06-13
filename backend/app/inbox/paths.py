from pathlib import PurePosixPath

from app.storage.keys import sanitize_storage_key


class InboxPathError(ValueError):
    pass


def is_inbox_workspace_path(workspace_path: str) -> bool:
    return "/_inbox/" in workspace_path.replace("\\", "/")


def sanitize_filename(filename: str) -> str:
    name = filename.replace("\\", "/").split("/")[-1].strip()
    if not name or name in {".", ".."}:
        msg = "Filename is required"
        raise InboxPathError(msg)
    if ".." in name:
        msg = "Invalid filename"
        raise InboxPathError(msg)
    return name


def sanitize_inbox_relative_path(relative_path: str | None) -> str:
    if relative_path is None or not relative_path.strip():
        return ""
    normalized = relative_path.replace("\\", "/").strip().strip("/")
    if not normalized:
        return ""
    parts = [part for part in PurePosixPath(normalized).parts if part not in {".", ".."}]
    if len(parts) != len(PurePosixPath(normalized).parts):
        msg = "Relative path must not contain parent segments"
        raise InboxPathError(msg)
    return "/".join(parts)


def build_inbox_workspace_path(
    project_workspace_path: str,
    *,
    filename: str,
    relative_path: str | None = None,
) -> str:
    safe_filename = sanitize_filename(filename)
    safe_relative = sanitize_inbox_relative_path(relative_path)
    base = f"{project_workspace_path.rstrip('/')}/_inbox"
    if safe_relative:
        return f"{base}/{safe_relative}/{safe_filename}"
    return f"{base}/{safe_filename}"


def build_storage_key(project_id: str, workspace_path: str) -> str:
    return sanitize_storage_key(f"{project_id}/{workspace_path}")
