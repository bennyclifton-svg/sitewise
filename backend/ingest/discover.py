from pathlib import Path

from app.config import settings
from ingest.types import ManifestEntry

_SKIP_NAMES = {"README.md", "download.py", ".gitkeep"}
_SKIP_DIR_NAMES = {".git", "__pycache__"}


def _posix_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _project_from_relative(relative_path: str) -> str:
    return relative_path.split("/", maxsplit=1)[0]


def discover_corpus(
    data_dir: Path | None = None,
    *,
    folder: str | None = None,
    supported_extensions: set[str] | None = None,
) -> list[ManifestEntry]:
    root = (data_dir or settings.data_dir).resolve()
    extensions = supported_extensions or settings.ingest_supported_extensions_set
    entries: list[ManifestEntry] = []

    search_roots: list[Path]
    if folder:
        search_roots = [root / folder]
    else:
        search_roots = [child for child in sorted(root.iterdir()) if child.is_dir()]

    for search_root in search_roots:
        if not search_root.exists():
            continue
        for path in sorted(search_root.rglob("*")):
            if not path.is_file():
                continue
            if any(part in _SKIP_DIR_NAMES for part in path.parts):
                continue
            if path.name in _SKIP_NAMES:
                continue
            if path.stat().st_size == 0:
                continue

            relative_path = _posix_relative(path, root)
            extension = path.suffix.lower()
            if extensions and extension not in extensions:
                continue

            entries.append(
                ManifestEntry(
                    absolute_path=path,
                    relative_path=relative_path,
                    project=_project_from_relative(relative_path),
                    filename=path.name,
                    extension=extension,
                    size_bytes=path.stat().st_size,
                )
            )

    return entries
