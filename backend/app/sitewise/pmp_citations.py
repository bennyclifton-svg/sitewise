"""Deterministic numbered citations for PMP evidence documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath


def citation_token(n: int) -> str:
    return f"[{n}]"


def citation_or_dash(n: int | None) -> str:
    if n is None:
        return "—"
    return citation_token(n)


@dataclass(frozen=True, slots=True)
class CitationIndex:
    """Stable label → number map for active project evidence documents."""

    documents: tuple[tuple[str, str], ...]
    _numbers: dict[str, int]

    def number_for(self, path_or_label: str) -> int | None:
        return self._numbers.get(_normalize_path(path_or_label))

    def token_for(self, path_or_label: str) -> str:
        return citation_or_dash(self.number_for(path_or_label))


def build_citation_index(
    documents: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> CitationIndex:
    """Number documents by ascending path/label. Empty corpus → empty map.

    Duplicate paths keep the first occurrence. Backslashes are normalised to ``/``.
    """
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for path, date_or_status in documents:
        normalised = _normalize_path(path)
        if normalised in seen:
            continue
        seen.add(normalised)
        unique.append((normalised, date_or_status))
    ordered = tuple(sorted(unique, key=lambda item: item[0]))
    numbers = {path: index for index, (path, _) in enumerate(ordered, start=1)}
    return CitationIndex(documents=ordered, _numbers=numbers)


def format_citation_key_lines(index: CitationIndex) -> list[str]:
    """Return numbered list lines: ``- [n] {basename} — {date/status}``."""
    return [
        f"- {citation_token(n)} {_basename(path)} — {date_or_status}"
        for n, (path, date_or_status) in enumerate(index.documents, start=1)
    ]


def _normalize_path(path_or_label: str) -> str:
    return path_or_label.replace("\\", "/")


def _basename(path_or_label: str) -> str:
    return PurePosixPath(_normalize_path(path_or_label)).name
