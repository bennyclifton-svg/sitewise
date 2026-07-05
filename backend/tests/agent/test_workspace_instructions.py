from pathlib import Path

from app.agent.workspace_instructions import (
    WORKSPACE_AGENTS_MD,
    ensure_workspace_instructions,
)


def test_writes_agents_md_into_workspace(tmp_path: Path) -> None:
    ensure_workspace_instructions(tmp_path)

    target = tmp_path / "AGENTS.md"
    assert target.read_text(encoding="utf-8") == WORKSPACE_AGENTS_MD
    assert "construction management intelligence agent" in WORKSPACE_AGENTS_MD
    assert "Clerk software" in WORKSPACE_AGENTS_MD
    assert "repository" in WORKSPACE_AGENTS_MD


def test_rewrite_is_skipped_when_content_is_current(tmp_path: Path) -> None:
    ensure_workspace_instructions(tmp_path)
    target = tmp_path / "AGENTS.md"
    before = target.stat().st_mtime_ns

    ensure_workspace_instructions(tmp_path)

    assert target.stat().st_mtime_ns == before


def test_stale_instructions_are_refreshed(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("old persona", encoding="utf-8")

    ensure_workspace_instructions(tmp_path)

    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == WORKSPACE_AGENTS_MD
