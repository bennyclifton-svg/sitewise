"""`build_version` identifies the code that produced an artefact.

Wave 1 chased an error string that no longer existed in the source tree and
Wave 2 could not tell which of two cost-plan compilers had run, because nothing
on the artefact recorded the build.
"""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from app import build_version as module


def _fresh() -> str:
    module.build_version.cache_clear()
    try:
        return module.build_version()
    finally:
        module.build_version.cache_clear()


def test_injected_build_sha_wins_over_the_working_tree() -> None:
    """The container has no .git, so the deploy hands the SHA in."""
    with patch.object(module.settings, "build_sha", "deadbeef"):
        assert _fresh() == "deadbeef"


def test_clean_tree_reports_the_short_sha() -> None:
    with (
        patch.object(module.settings, "build_sha", ""),
        patch.object(module, "_git", side_effect=["a1b2c3d4", ""]),
    ):
        assert _fresh() == "a1b2c3d4"


def test_dirty_tree_is_marked_because_the_sha_alone_would_lie() -> None:
    with (
        patch.object(module.settings, "build_sha", ""),
        patch.object(module, "_git", side_effect=["a1b2c3d4", " M app/main.py"]),
    ):
        assert _fresh() == "a1b2c3d4-dirty"


def test_missing_git_degrades_to_unknown_rather_than_raising() -> None:
    """Provenance is not worth failing a workflow over."""
    with (
        patch.object(module.settings, "build_sha", ""),
        patch.object(module, "_git", return_value=None),
    ):
        assert _fresh() == "unknown"


def test_git_failure_is_swallowed() -> None:
    with (
        patch.object(module.settings, "build_sha", ""),
        patch.object(
            module.subprocess, "run", side_effect=subprocess.TimeoutExpired("git", 5)
        ),
    ):
        assert _fresh() == "unknown"


def test_resolves_once_per_process() -> None:
    """The code cannot change under a running interpreter; don't fork git per artefact."""
    module.build_version.cache_clear()
    with (
        patch.object(module.settings, "build_sha", ""),
        patch.object(module, "_git", side_effect=["a1b2c3d4", ""]) as git,
    ):
        first = module.build_version()
        second = module.build_version()
    module.build_version.cache_clear()
    assert first == second == "a1b2c3d4"
    assert git.call_count == 2  # rev-parse + status, once — not twice each
