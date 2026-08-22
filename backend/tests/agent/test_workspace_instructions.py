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
    assert "search_project_email" in WORKSPACE_AGENTS_MD
    assert "create_email_draft" in WORKSPACE_AGENTS_MD
    assert "Never claim the message was sent" in WORKSPACE_AGENTS_MD
    assert "list_document_register" in WORKSPACE_AGENTS_MD
    assert "select_document_register_files" in WORKSPACE_AGENTS_MD
    assert "refresh_cost_plan with reconcile_evidence=true" in WORKSPACE_AGENTS_MD
    assert "process_invoices" in WORKSPACE_AGENTS_MD
    assert "only books ingested invoice evidence" in WORKSPACE_AGENTS_MD
    assert "never invent invoice numbers" in WORKSPACE_AGENTS_MD
    assert "search_web" in WORKSPACE_AGENTS_MD
    assert "read_web_source" in WORKSPACE_AGENTS_MD
    assert "attach_official_instrument" in WORKSPACE_AGENTS_MD
    assert "Search results are discovery candidates" in WORKSPACE_AGENTS_MD
    assert "external reference, not project evidence" in WORKSPACE_AGENTS_MD
    assert "Never call upsert_cost_item" in WORKSPACE_AGENTS_MD
    assert "apply_artefact_operations" in WORKSPACE_AGENTS_MD
    assert "apply_cost_plan_operations" in WORKSPACE_AGENTS_MD
    assert "get_programme" in WORKSPACE_AGENTS_MD
    assert "apply_programme_operations" in WORKSPACE_AGENTS_MD
    assert "only schedule source of truth" in WORKSPACE_AGENTS_MD
    assert "delay activity" in WORKSPACE_AGENTS_MD
    assert '"target_type": "activity"' in WORKSPACE_AGENTS_MD
    assert '"parent_key": "planning"' in WORKSPACE_AGENTS_MD
    assert "predecessor_key to the previous" in WORKSPACE_AGENTS_MD
    assert "genuinely concurrent" in WORKSPACE_AGENTS_MD
    assert "program-scheduling-guide.md" in WORKSPACE_AGENTS_MD
    assert "get_artefact_blocks" in WORKSPACE_AGENTS_MD
    assert "upsert_shared_project_knowledge" in WORKSPACE_AGENTS_MD
    assert "ffe_item" in WORKSPACE_AGENTS_MD
    assert "FFE Schedule" in WORKSPACE_AGENTS_MD
    assert "accommodation_space" in WORKSPACE_AGENTS_MD
    assert "Accommodation Schedule" in WORKSPACE_AGENTS_MD
    assert "already has an Accommodation Schedule" in WORKSPACE_AGENTS_MD
    assert "does not already have it" in WORKSPACE_AGENTS_MD
    assert "scope_narrative" in WORKSPACE_AGENTS_MD
    assert "empty Accommodation Schedule is wrong" in WORKSPACE_AGENTS_MD
    assert "Prefer headings and bullet lists for structure" in WORKSPACE_AGENTS_MD
    assert "**bold**" in WORKSPACE_AGENTS_MD
    assert "appoint_consultant" in WORKSPACE_AGENTS_MD
    assert "Approved Contract" in WORKSPACE_AGENTS_MD
    assert "do not call refresh_cost_plan" in WORKSPACE_AGENTS_MD
    assert "get_procurement_strategy" in WORKSPACE_AGENTS_MD
    assert "apply_procurement_strategy_operations" in WORKSPACE_AGENTS_MD
    assert "search_procurement_candidates" in WORKSPACE_AGENTS_MD
    assert "leads, not endorsements" in WORKSPACE_AGENTS_MD
    compact = " ".join(WORKSPACE_AGENTS_MD.split())
    assert "A failed research tool does not mean Tenderer slots are unavailable" in compact


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
