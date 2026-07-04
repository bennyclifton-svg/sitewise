import uuid
from types import SimpleNamespace

from app.api.projects import (
    _append_unindexed_inbox_workspace_files,
    _evidence_preview_from_document,
    _evidence_preview_from_values,
    _filter_stale_inbox_documents,
)


def _document(relative_path: str):
    return SimpleNamespace(relative_path=relative_path)


def test_filter_stale_inbox_documents_hides_moved_inbox_rows() -> None:
    stale_inbox = _document("04-projects/demo/_inbox/sorted.md")
    active_inbox = _document("04-projects/demo/_inbox/unresolved.md")
    filed = _document("04-projects/demo/04-planning-and-authorities/sorted.md")

    active = _filter_stale_inbox_documents(
        [stale_inbox, active_inbox, filed],
        {
            "04-projects/demo/_inbox/unresolved.md",
            "04-projects/demo/04-planning-and-authorities/sorted.md",
        },
    )

    assert [document.relative_path for document in active] == [
        "04-projects/demo/_inbox/unresolved.md",
        "04-projects/demo/04-planning-and-authorities/sorted.md",
    ]


def test_filter_stale_inbox_documents_keeps_legacy_projects_without_workspace_files() -> None:
    documents = [_document("04-projects/demo/_inbox/legacy.md")]

    assert _filter_stale_inbox_documents(documents, set()) == documents


def test_append_unindexed_inbox_workspace_files_adds_pending_inbox_rows() -> None:
    workspace_file_id = uuid.UUID("55555555-5555-5555-5555-555555555555")
    indexed = _evidence_preview_from_values(
        document_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        document_type=None,
        metadata={},
        filename="indexed.md",
        relative_path="04-projects/demo/_inbox/indexed.md",
        source_type="project_evidence",
        document_class="project_evidence",
        excerpt_source="Indexed inbox excerpt.",
    )
    workspace_file = SimpleNamespace(
        id=workspace_file_id,
        filename="E00 - ELECTRICAL - COVER SHEET - [C1].pdf",
        workspace_path="04-projects/demo/_inbox/E00 - ELECTRICAL - COVER SHEET - [C1].pdf",
    )

    merged = _append_unindexed_inbox_workspace_files(
        [indexed],
        [workspace_file, SimpleNamespace(
            id=uuid.UUID("66666666-6666-6666-6666-666666666666"),
            filename="filed.md",
            workspace_path="04-projects/demo/03-design/filed.md",
        )],
    )

    assert [preview.relative_path for preview in merged] == [
        "04-projects/demo/_inbox/indexed.md",
        "04-projects/demo/_inbox/E00 - ELECTRICAL - COVER SHEET - [C1].pdf",
    ]
    pending = merged[1]
    assert pending.id == workspace_file_id
    assert pending.category is None
    assert pending.document_class == "inbox_pending"


def _source_document(filename: str, normalized_content: str):
    return SimpleNamespace(
        id=uuid.UUID("77777777-7777-7777-7777-777777777777"),
        document_type=None,
        document_metadata={},
        filename=filename,
        relative_path=f"04-projects/demo/03-design/{filename}",
        source_type="project_evidence",
        document_class="project_evidence",
        normalized_content=normalized_content,
    )


def test_evidence_preview_includes_full_content_for_non_markdown_documents() -> None:
    document = _source_document(
        "E00 - ELECTRICAL - COVER SHEET - [C1].pdf",
        "# Cover Sheet\n\nFull extracted markdown body.",
    )

    preview = _evidence_preview_from_document(document, include_content=True)

    assert preview.content == "# Cover Sheet\n\nFull extracted markdown body."


def test_evidence_preview_omits_content_when_not_requested() -> None:
    document = _source_document("brief.pdf", "Full extracted markdown body.")

    preview = _evidence_preview_from_document(document, include_content=False)

    assert preview.content is None
