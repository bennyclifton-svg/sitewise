from __future__ import annotations

import re
from datetime import UTC, datetime

from app.projects.artefact_blocks import (
    ArtefactBlockOperation,
    ArtefactBlockTarget,
    IncrementalBlockProposal,
    apply_block_operations,
    block_input_hash,
    materialize_block_identity,
    markdown_blocks,
    merge_incremental_block_updates,
    reconcile_regenerated_blocks,
    strip_block_markers,
)


MARKDOWN = """# Plan

## Scope

Existing paragraph.

- First item
- Second item

| Item | Status |
| --- | --- |
| Tap | Proposed |
"""
NOW = datetime(2026, 8, 10, tzinfo=UTC)


def test_delete_table_row_does_not_leave_blank_line_inside_table() -> None:
    """GFM ends a table at a blank line; delete must not insert one mid-table."""
    markdown = """## Project Summary

| Field | Detail | Citation |
| --- | --- | --- |
| Project | Walsh2 |  |
| Address | 42 Hargrave Street | [1] |<!-- clerk:block id=blk_c5b155667c74837540ac88af34a7d358 -->
| Owner | David and Emma Walsh | [1] |<!-- clerk:block id=blk_9a7b77fe4970e4836f3c148540452ecf -->
| Description | Terrace renovation | [1] |<!-- clerk:block id=blk_ade5ba1bfc81abd258442ace94e4a835 -->
"""
    owner = next(
        block
        for block in markdown_blocks(markdown)
        if block.type == "table_row" and "Owner" in block.content
    )
    # Parser addresses the visible line only (no trailing newline).
    assert markdown[owner.end : owner.end + 1] == "\n"

    deleted = apply_block_operations(
        markdown,
        [
            ArtefactBlockOperation(
                operation="DELETE",
                target=ArtefactBlockTarget(id=owner.id, type="table_row"),
            )
        ],
        existing_metadata={
            owner.id: {
                "id": owner.id,
                "type": "table_row",
                "user_protected": False,
            }
        },
        actor_source="user",
        now=NOW,
    )

    assert "| Owner | David and Emma Walsh |" not in deleted.markdown
    assert re.search(
        r"\| Address \| 42 Hargrave Street \| \[1\] \|(?:<!--.*?-->)?\n\| Description \| Terrace renovation \| \[1\] \|",
        deleted.markdown,
    ), deleted.markdown
    assert "\n\n| Description |" not in deleted.markdown


def test_add_after_table_row_accepts_range_excluding_trailing_marker() -> None:
    markdown = """## Summary

| Field | Detail | Citation |
| --- | --- | --- |
| Address | Bankstown | [1] |<!-- clerk:block id=blk_c5b155667c74837540ac88af34a7d358 -->
| Owner | FULLERTON | [2] |<!-- clerk:block id=blk_9a7b77fe4970e4836f3c148540452ecf -->
"""
    address = next(
        block
        for block in markdown_blocks(markdown)
        if block.type == "table_row" and "Address" in block.content
    )
    short_end = markdown.index("<!--", address.start)
    assert short_end < address.end

    added = apply_block_operations(
        markdown,
        [
            ArtefactBlockOperation(
                operation="ADD",
                target=ArtefactBlockTarget(
                    type="table_row", start=address.start, end=short_end
                ),
                placement="after",
                content="| Test | row | |",
            )
        ],
        existing_metadata=None,
        actor_source="user",
        now=NOW,
    )
    assert "| Address | Bankstown | [1] |" in added.markdown
    address_at = added.markdown.index("| Address | Bankstown | [1] |")
    test_at = added.markdown.index("| Test | row | |")
    owner_at = added.markdown.index("| Owner | FULLERTON | [2] |")
    assert address_at < test_at < owner_at


def test_paragraph_duplicate_and_add_use_blank_line_separator() -> None:
    paragraph = next(
        block for block in markdown_blocks(MARKDOWN) if block.type == "paragraph"
    )
    duplicated = apply_block_operations(
        MARKDOWN,
        [
            ArtefactBlockOperation(
                operation="DUPLICATE",
                target=ArtefactBlockTarget(
                    type="paragraph", start=paragraph.start, end=paragraph.end
                ),
            )
        ],
        existing_metadata=None,
        actor_source="user",
        now=NOW,
    )
    assert "Existing paragraph.\n\n<!-- clerk:block id=" in duplicated.markdown
    assert duplicated.markdown.count("Existing paragraph.") == 2

    added = apply_block_operations(
        MARKDOWN,
        [
            ArtefactBlockOperation(
                operation="ADD",
                target=ArtefactBlockTarget(
                    type="paragraph", start=paragraph.start, end=paragraph.end
                ),
                placement="after",
                content="Inserted paragraph.",
            )
        ],
        existing_metadata=None,
        actor_source="user",
        now=NOW,
    )
    assert "Existing paragraph.\n\n<!-- clerk:block id=" in added.markdown
    assert "Inserted paragraph." in added.markdown


def test_parser_addresses_paragraph_list_items_and_table_rows() -> None:
    blocks = markdown_blocks(MARKDOWN)

    assert [block.type for block in blocks] == [
        "paragraph",
        "list_item",
        "list_item",
        "table_row",
    ]
    assert blocks[-1].content == "| Tap | Proposed |"


def test_generated_block_ids_are_repeatable_for_unchanged_content() -> None:
    first = materialize_block_identity(
        MARKDOWN,
        actor_source="ai",
        generation_input_hash="generation-one",
        now=NOW,
    )
    second = materialize_block_identity(
        MARKDOWN,
        actor_source="ai",
        generation_input_hash="generation-two",
        now=NOW,
    )

    assert first.changed_block_ids == second.changed_block_ids
    assert first.markdown == second.markdown


def test_identity_markers_round_trip_visible_markdown_for_supported_blocks() -> None:
    source = """# Plan

## FFE

Intro paragraph.

- Basin mixer

| ID | Item |
| --- | --- |
| FFE-01 | Filtered tap |
"""
    first = materialize_block_identity(
        source,
        actor_source="ai",
        generation_input_hash="context-v1",
        generation_version="v1",
        now=NOW,
    )
    first_identity = [
        (block.type, block.id) for block in markdown_blocks(first.markdown)
    ]

    assert [block_type for block_type, _ in first_identity] == [
        "paragraph",
        "list_item",
        "table_row",
    ]
    assert all(block_id is not None for _, block_id in first_identity)
    assert "| FFE-01 | Filtered tap |" in first.markdown

    visible = strip_block_markers(first.markdown)
    assert visible == source

    second = materialize_block_identity(
        visible,
        actor_source="ai",
        generation_input_hash="context-v2",
        generation_version="v2",
        now=NOW,
    )
    assert [
        (block.type, block.id) for block in markdown_blocks(second.markdown)
    ] == first_identity


def test_identity_marker_stripping_preserves_crlf_and_terminal_newline() -> None:
    source = (
        "# Plan\r\n\r\n"
        "Intro paragraph.\r\n\r\n"
        "- Basin mixer\r\n\r\n"
        "| ID | Item |\r\n"
        "| --- | --- |\r\n"
        "| FFE-01 | Filtered tap |\r\n"
    )

    generated = materialize_block_identity(source, actor_source="ai", now=NOW)

    assert strip_block_markers(generated.markdown) == source


def test_strip_block_markers_hides_truncated_identity_comments() -> None:
    source = (
        "Rear extension and first-floor addition. [1] Inclusions: kitchen. "
        "<!-- clerk:block id=blk_dba9073a16ea8cddb7bc1e7117d5e43 -->"
    )

    visible = strip_block_markers(source)

    assert visible == (
        "Rear extension and first-floor addition. [1] Inclusions: kitchen."
    )
    assert "clerk:block" not in visible


def test_generated_table_markers_follow_the_complete_visible_row() -> None:
    source = "| Project | Walsh 2 |\n| --- | --- |\n| Address | Paddington |"
    generated = materialize_block_identity(
        source,
        actor_source="ai",
        now=NOW,
    )

    stamped_rows = [
        line for line in generated.markdown.splitlines() if "clerk:block" in line
    ]
    assert generated.markdown.startswith("| Project | Walsh 2 |\n| --- | --- |")
    assert len(stamped_rows) == 1
    assert all("|<!-- clerk:block" in line for line in stamped_rows)
    assert all(line.endswith("-->") for line in stamped_rows)
    assert strip_block_markers(generated.markdown) == source


def test_updating_first_document_block_replaces_its_marker_once() -> None:
    generated = materialize_block_identity(
        "First paragraph.", actor_source="ai", now=NOW
    )
    block = markdown_blocks(generated.markdown)[0]

    updated = apply_block_operations(
        generated.markdown,
        [
            ArtefactBlockOperation(
                operation="UPDATE",
                target=ArtefactBlockTarget(id=block.id, type="paragraph"),
                content="Updated paragraph.",
            )
        ],
        existing_metadata=generated.metadata,
        actor_source="user",
        now=NOW,
    )

    assert updated.markdown.count(f"id={block.id}") == 1


def test_update_add_duplicate_and_delete_use_one_operation_model() -> None:
    paragraph, first_item, *_ = markdown_blocks(MARKDOWN)
    updated = apply_block_operations(
        MARKDOWN,
        [
            ArtefactBlockOperation(
                operation="UPDATE",
                target=ArtefactBlockTarget(
                    type="paragraph", start=paragraph.start, end=paragraph.end
                ),
                content="Updated paragraph.",
            )
        ],
        existing_metadata=None,
        actor_source="user",
        now=NOW,
    )
    block_id = updated.changed_block_ids[0]

    assert f"<!-- clerk:block id={block_id} -->" in updated.markdown
    assert updated.metadata[block_id]["last_modified_by"] == "user"

    target = next(
        block
        for block in markdown_blocks(updated.markdown)
        if block.content == "- First item"
    )
    added = apply_block_operations(
        updated.markdown,
        [
            ArtefactBlockOperation(
                operation="ADD",
                target=ArtefactBlockTarget(
                    type="list_item", start=target.start, end=target.end
                ),
                placement="after",
                content="- Added item",
            )
        ],
        existing_metadata=updated.metadata,
        actor_source="user",
        now=NOW,
    )
    assert added.markdown.index("- First item") < added.markdown.index("- Added item")

    added_block = next(
        block
        for block in markdown_blocks(added.markdown)
        if block.content == "- Added item"
    )
    duplicated = apply_block_operations(
        added.markdown,
        [
            ArtefactBlockOperation(
                operation="DUPLICATE",
                target=ArtefactBlockTarget(id=added_block.id, type="list_item"),
            )
        ],
        existing_metadata=added.metadata,
        actor_source="user",
        now=NOW,
    )
    assert duplicated.markdown.count("- Added item") == 2

    deleted = apply_block_operations(
        duplicated.markdown,
        [
            ArtefactBlockOperation(
                operation="DELETE",
                target=ArtefactBlockTarget(id=added_block.id, type="list_item"),
            )
        ],
        existing_metadata=duplicated.metadata,
        actor_source="user",
        now=NOW,
    )
    assert added_block.id not in deleted.metadata
    assert deleted.markdown.count("- Added item") == 1
    assert first_item.content == "- First item"


def test_incremental_updates_preserve_user_content_and_skip_unchanged_inputs() -> None:
    paragraph = markdown_blocks(MARKDOWN)[0]
    created = apply_block_operations(
        MARKDOWN,
        [
            ArtefactBlockOperation(
                operation="UPDATE",
                target=ArtefactBlockTarget(
                    type="paragraph", start=paragraph.start, end=paragraph.end
                ),
                content="User wording.",
            )
        ],
        existing_metadata=None,
        actor_source="user",
        now=NOW,
    )
    block_id = created.changed_block_ids[0]
    proposal_hash = block_input_hash(
        context_version=2,
        source_version="evidence-2",
        seed_version="seed-1",
        inputs={"scope": "revised"},
    )
    merged = merge_incremental_block_updates(
        created.markdown,
        created.metadata,
        [
            IncrementalBlockProposal(
                block_id=block_id,
                content="AI replacement.",
                input_hash=proposal_hash,
            )
        ],
        now=NOW,
    )

    assert "User wording." in merged.markdown
    assert merged.conflicts == (block_id,)
    assert merged.metadata[block_id]["status"] == "conflict"


def test_regeneration_preserves_user_block_and_flags_semantic_conflict() -> None:
    generated = materialize_block_identity(
        MARKDOWN,
        actor_source="ai",
        generation_input_hash="initial",
        generation_version="v1",
        now=NOW,
    )
    paragraph = markdown_blocks(generated.markdown)[0]
    current = apply_block_operations(
        generated.markdown,
        [
            ArtefactBlockOperation(
                operation="UPDATE",
                target=ArtefactBlockTarget(id=paragraph.id, type="paragraph"),
                content="User-controlled wording.",
            )
        ],
        existing_metadata=generated.metadata,
        actor_source="user",
        now=NOW,
    )
    proposed = apply_block_operations(
        generated.markdown,
        [
            ArtefactBlockOperation(
                operation="UPDATE",
                target=ArtefactBlockTarget(id=paragraph.id, type="paragraph"),
                content="New AI wording.",
            )
        ],
        existing_metadata=generated.metadata,
        actor_source="ai",
        now=NOW,
    )

    merged = reconcile_regenerated_blocks(
        current.markdown,
        current.metadata,
        proposed.markdown,
        generation_input_hash="revised",
        generation_version="v2",
        now=NOW,
    )

    assert "User-controlled wording." in merged.markdown
    assert "New AI wording." not in merged.markdown
    assert merged.conflicts == (paragraph.id,)
    assert merged.metadata[paragraph.id]["status"] == "conflict"


def test_regeneration_restores_omitted_user_block_as_proposed_delete() -> None:
    generated = materialize_block_identity(
        MARKDOWN,
        actor_source="ai",
        generation_input_hash="initial",
        generation_version="v1",
        now=NOW,
    )
    first_item = markdown_blocks(generated.markdown)[1]
    current = apply_block_operations(
        generated.markdown,
        [
            ArtefactBlockOperation(
                operation="ADD",
                target=ArtefactBlockTarget(id=first_item.id, type="list_item"),
                placement="after",
                content="- User-added item",
            )
        ],
        existing_metadata=generated.metadata,
        actor_source="user",
        now=NOW,
    )
    user_block_id = current.changed_block_ids[0]

    merged = reconcile_regenerated_blocks(
        current.markdown,
        current.metadata,
        generated.markdown,
        generation_input_hash="revised",
        generation_version="v2",
        now=NOW,
    )

    assert "- User-added item" in merged.markdown
    assert merged.metadata[user_block_id]["status"] == "propose_delete"
    assert user_block_id in merged.preserved


def test_protect_marks_provenance_without_changing_markdown() -> None:
    generated = materialize_block_identity(
        "Stable paragraph.", actor_source="ai", now=NOW
    )
    block = markdown_blocks(generated.markdown)[0]

    protected = apply_block_operations(
        generated.markdown,
        [
            ArtefactBlockOperation(
                operation="PROTECT",
                target=ArtefactBlockTarget(id=block.id, type="paragraph"),
            )
        ],
        existing_metadata=generated.metadata,
        actor_source="user",
        now=NOW,
    )

    assert protected.markdown == generated.markdown
    assert protected.metadata[block.id]["user_protected"] is True
    assert (
        protected.metadata[block.id]["baseline_content_hash"]
        == generated.metadata[block.id]["baseline_content_hash"]
    )
    assert protected.changed_block_ids == (block.id,)


def test_protected_block_rejects_ai_update_and_delete() -> None:
    generated = materialize_block_identity(
        "Protected fact.", actor_source="ai", now=NOW
    )
    block = markdown_blocks(generated.markdown)[0]
    protected = apply_block_operations(
        generated.markdown,
        [
            ArtefactBlockOperation(
                operation="PROTECT",
                target=ArtefactBlockTarget(id=block.id, type="paragraph"),
            )
        ],
        existing_metadata=generated.metadata,
        actor_source="user",
        now=NOW,
    )

    try:
        apply_block_operations(
            protected.markdown,
            [
                ArtefactBlockOperation(
                    operation="UPDATE",
                    target=ArtefactBlockTarget(id=block.id, type="paragraph"),
                    content="AI overwrite.",
                )
            ],
            existing_metadata=protected.metadata,
            actor_source="ai",
            now=NOW,
        )
        raise AssertionError("expected protected UPDATE rejection")
    except ValueError as exc:
        assert "protected" in str(exc).lower()

    try:
        apply_block_operations(
            protected.markdown,
            [
                ArtefactBlockOperation(
                    operation="DELETE",
                    target=ArtefactBlockTarget(id=block.id, type="paragraph"),
                )
            ],
            existing_metadata=protected.metadata,
            actor_source="ai",
            now=NOW,
        )
        raise AssertionError("expected protected DELETE rejection")
    except ValueError as exc:
        assert "protected" in str(exc).lower()

    updated = apply_block_operations(
        protected.markdown,
        [
            ArtefactBlockOperation(
                operation="UPDATE",
                target=ArtefactBlockTarget(id=block.id, type="paragraph"),
                content="User revision.",
            )
        ],
        existing_metadata=protected.metadata,
        actor_source="user",
        now=NOW,
    )
    assert "User revision." in updated.markdown
    assert updated.metadata[block.id]["user_protected"] is True


def test_unprotect_clears_protection_flag() -> None:
    generated = materialize_block_identity("Fact.", actor_source="ai", now=NOW)
    block = markdown_blocks(generated.markdown)[0]
    protected = apply_block_operations(
        generated.markdown,
        [
            ArtefactBlockOperation(
                operation="PROTECT",
                target=ArtefactBlockTarget(id=block.id, type="paragraph"),
            )
        ],
        existing_metadata=generated.metadata,
        actor_source="user",
        now=NOW,
    )

    cleared = apply_block_operations(
        protected.markdown,
        [
            ArtefactBlockOperation(
                operation="UNPROTECT",
                target=ArtefactBlockTarget(id=block.id, type="paragraph"),
            )
        ],
        existing_metadata=protected.metadata,
        actor_source="user",
        now=NOW,
    )

    assert cleared.markdown == protected.markdown
    assert cleared.metadata[block.id]["user_protected"] is False


def test_move_updates_provenance_timestamps() -> None:
    generated = materialize_block_identity(
        "First.\n\nSecond.", actor_source="ai", now=NOW
    )
    first, second = markdown_blocks(generated.markdown)
    later = datetime(2026, 8, 11, tzinfo=UTC)

    moved = apply_block_operations(
        generated.markdown,
        [
            ArtefactBlockOperation(
                operation="MOVE",
                target=ArtefactBlockTarget(id=first.id, type="paragraph"),
                reference_id=second.id,
                placement="after",
            )
        ],
        existing_metadata=generated.metadata,
        actor_source="user",
        now=later,
    )

    assert moved.metadata[first.id]["last_modified_by"] == "user"
    assert moved.metadata[first.id]["updated_at"] == later.isoformat().replace(
        "+00:00", "Z"
    )
    assert first.id in moved.changed_block_ids
