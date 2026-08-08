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
    assert "You are Pi" in WORKSPACE_AGENTS_MD
    assert "SiteWise software" in WORKSPACE_AGENTS_MD
    assert "repository" in WORKSPACE_AGENTS_MD
    assert "list_document_register" in WORKSPACE_AGENTS_MD
    assert "select_document_register_files" in WORKSPACE_AGENTS_MD
    assert "refresh_cost_plan with reconcile_evidence=true" in WORKSPACE_AGENTS_MD
    assert "process_invoices" in WORKSPACE_AGENTS_MD
    assert "search_web" in WORKSPACE_AGENTS_MD
    assert "read_web_source" in WORKSPACE_AGENTS_MD
    assert "Search results are discovery candidates" in WORKSPACE_AGENTS_MD
    assert "external reference, not project evidence" in WORKSPACE_AGENTS_MD
    assert "Never call upsert_cost_item" in WORKSPACE_AGENTS_MD
    assert "Prefer headings and bullet lists for structure" in WORKSPACE_AGENTS_MD
    assert "**bold**" in WORKSPACE_AGENTS_MD


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
