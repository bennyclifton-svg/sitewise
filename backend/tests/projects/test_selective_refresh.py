"""F7: selective narrative refresh — skip, affected blocks, audit, resolution."""

from __future__ import annotations

from datetime import UTC, datetime

from app.projects.artefact_blocks import (
    ArtefactBlockOperation,
    ArtefactBlockTarget,
    IncrementalBlockProposal,
    apply_block_operations,
    block_input_hash,
    markdown_blocks,
    materialize_block_identity,
    merge_incremental_block_updates,
)
from app.projects.selective_refresh import (
    apply_selective_section_refresh,
    build_incremental_audit,
    compute_refresh_input_hash,
    plan_selective_refresh,
    prior_refresh_input_hash,
    stamp_block_versions,
)

NOW = datetime(2026, 8, 11, tzinfo=UTC)

BASELINE_MD = """## Consultants

ABC Engineering remains engaged.

## Programme

Construction starts in Q3.
"""


def _ai_baseline() -> tuple[str, dict]:
    generated = materialize_block_identity(
        BASELINE_MD,
        actor_source="ai",
        generation_input_hash="initial",
        generation_version="v1",
        now=NOW,
    )
    stamped = stamp_block_versions(
        generated.metadata,
        context_version=1,
        source_version="evidence-1",
        seed_version="seed-1",
        generation_version="v1",
    )
    return generated.markdown, stamped


def test_unchanged_refresh_plan_skips_when_input_hash_matches() -> None:
    refresh_hash = compute_refresh_input_hash(
        context_version=2,
        source_version="evidence-2",
        seed_version="seed-1",
        artefact_type="pmp",
    )
    plan = plan_selective_refresh(
        {"incremental_update": {"input_hash": refresh_hash}},
        context_version=2,
        source_version="evidence-2",
        seed_version="seed-1",
        artefact_type="pmp",
    )
    assert plan.skip is True
    assert plan.refresh_input_hash == refresh_hash


def test_changed_context_plan_does_not_skip() -> None:
    prior = compute_refresh_input_hash(
        context_version=1,
        source_version="evidence-1",
        seed_version="seed-1",
        artefact_type="pmp",
    )
    plan = plan_selective_refresh(
        {"incremental_update": {"input_hash": prior}},
        context_version=2,
        source_version="evidence-1",
        seed_version="seed-1",
        artefact_type="pmp",
    )
    assert plan.skip is False


def test_prior_refresh_input_hash_reads_incremental_or_brief() -> None:
    assert (
        prior_refresh_input_hash({"incremental_update": {"input_hash": "abc"}}) == "abc"
    )
    brief_hash = "f" * 64
    assert (
        prior_refresh_input_hash(
            {"generation_brief": {"input_fingerprint": brief_hash}}
        )
        == brief_hash
    )


def test_selective_section_refresh_updates_only_affected_blocks() -> None:
    markdown, metadata = _ai_baseline()
    blocks = markdown_blocks(markdown)
    consultants = blocks[0]
    programme = blocks[1]
    assert consultants.id and programme.id

    regenerated = (
        f"## Consultants\n\n"
        f"<!-- clerk:block id={consultants.id} -->\n"
        f"Fluid Design replaces the hydraulic consultant.\n\n"
        f"## Programme\n\n"
        f"<!-- clerk:block id={programme.id} -->\n"
        f"Construction starts in Q4 — should not apply.\n"
    )
    section_hash = block_input_hash(
        context_version=2,
        source_version="evidence-2",
        seed_version="seed-1",
        inputs={"artefact_type": "pmp", "section_id": "consultants"},
    )
    result = apply_selective_section_refresh(
        markdown,
        metadata,
        regenerated,
        affected_section_ids=("consultants",),
        context_version=2,
        source_version="evidence-2",
        seed_version="seed-1",
        artefact_type="pmp",
        generation_version="v2",
        now=NOW,
    )

    assert "Fluid Design replaces the hydraulic consultant." in result.markdown
    assert "Construction starts in Q3." in result.markdown
    assert "Construction starts in Q4" not in result.markdown
    assert consultants.id in result.updated
    assert programme.id not in result.updated
    # Unaffected block remains byte-identical in-place.
    programme_after = next(
        block for block in markdown_blocks(result.markdown) if block.id == programme.id
    )
    programme_before = next(
        block for block in markdown_blocks(markdown) if block.id == programme.id
    )
    assert programme_after.content == programme_before.content
    assert result.metadata[consultants.id]["context_version"] == 2
    assert result.metadata[consultants.id]["source_version"] == "evidence-2"
    assert result.metadata[consultants.id]["seed_version"] == "seed-1"
    assert result.metadata[consultants.id]["input_hash"] == section_hash


def test_selective_refresh_skips_block_when_section_input_hash_unchanged() -> None:
    markdown, metadata = _ai_baseline()
    consultants = markdown_blocks(markdown)[0]
    assert consultants.id
    section_hash = block_input_hash(
        context_version=1,
        source_version="evidence-1",
        seed_version="seed-1",
        inputs={"artefact_type": "pmp", "section_id": "consultants"},
    )
    metadata[consultants.id]["input_hash"] = section_hash
    regenerated = (
        f"## Consultants\n\n"
        f"<!-- clerk:block id={consultants.id} -->\n"
        f"Should not replace when hash matches.\n\n"
        f"## Programme\n\n"
        f"Construction starts in Q3.\n"
    )
    result = apply_selective_section_refresh(
        markdown,
        metadata,
        regenerated,
        affected_section_ids=("consultants",),
        context_version=1,
        source_version="evidence-1",
        seed_version="seed-1",
        artefact_type="pmp",
        generation_version="v2",
        now=NOW,
    )
    assert "ABC Engineering remains engaged." in result.markdown
    assert "Should not replace" not in result.markdown
    assert consultants.id in result.preserved


def test_incremental_audit_includes_proposed_delete() -> None:
    markdown, metadata = _ai_baseline()
    first = markdown_blocks(markdown)[0]
    assert first.id
    current = apply_block_operations(
        markdown,
        [
            ArtefactBlockOperation(
                operation="ADD",
                target=ArtefactBlockTarget(id=first.id, type="paragraph"),
                placement="after",
                content="User-only note.",
            )
        ],
        existing_metadata=metadata,
        actor_source="user",
        now=NOW,
    )
    user_id = current.changed_block_ids[0]
    merged = merge_incremental_block_updates(
        current.markdown,
        current.metadata,
        [
            IncrementalBlockProposal(
                block_id=user_id,
                content=None,
                input_hash="new-hash",
            )
        ],
        now=NOW,
    )
    audit = build_incremental_audit(merged, refresh_input_hash="doc-hash")
    assert user_id in audit["proposed_delete"]
    assert user_id in audit["preserved"]
    assert audit["input_hash"] == "doc-hash"


def test_keep_and_confirm_delete_resolve_review_statuses() -> None:
    markdown, metadata = _ai_baseline()
    block = markdown_blocks(markdown)[0]
    assert block.id
    metadata[block.id]["status"] = "conflict"
    kept = apply_block_operations(
        markdown,
        [
            ArtefactBlockOperation(
                operation="KEEP",
                target=ArtefactBlockTarget(id=block.id, type="paragraph"),
            )
        ],
        existing_metadata=metadata,
        actor_source="user",
        now=NOW,
    )
    assert kept.markdown == markdown
    assert kept.metadata[block.id]["status"] == "active"
    assert kept.metadata[block.id]["baseline_content_hash"]

    metadata[block.id]["status"] = "propose_delete"
    deleted = apply_block_operations(
        markdown,
        [
            ArtefactBlockOperation(
                operation="CONFIRM_DELETE",
                target=ArtefactBlockTarget(id=block.id, type="paragraph"),
            )
        ],
        existing_metadata=metadata,
        actor_source="user",
        now=NOW,
    )
    assert block.id not in deleted.metadata
    assert "ABC Engineering remains engaged." not in deleted.markdown
