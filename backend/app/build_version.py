"""Identify the build that is executing, so artefacts record what made them.

Wave 1 of the prompt-corpus evaluation spent a day chasing an error string that
no longer existed in the source tree, and Wave 2 could not tell which of two
cost-plan compilers had run. In both cases the artefact recorded the runtime
name and the model but nothing about the code, and several environments share
one database. `build_version()` closes that gap.

In a container there is no `.git`, so the deploy injects `BUILD_SHA`. In dev the
tree is the source of truth, including whether it is dirty — an uncommitted
working tree is exactly the case where the SHA alone would mislead.
"""

from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

from app.config import settings

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_GIT_TIMEOUT_SECONDS = 5


@lru_cache(maxsize=1)
def build_version() -> str:
    """Return a short identifier for the running build.

    Shapes: `a1b2c3d`, `a1b2c3d-dirty`, or `unknown`. Resolved once per process
    — the code cannot change under a running interpreter.
    """
    configured = (settings.build_sha or "").strip()
    if configured:
        return configured
    sha = _git("rev-parse", "--short=8", "HEAD")
    if sha is None:
        return "unknown"
    return f"{sha}-dirty" if _git("status", "--porcelain") else sha


def _git(*args: str) -> str | None:
    """Run a git command in the repo root, or return None if git is unusable."""
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()
