from types import SimpleNamespace

from app.api.projects import _filter_stale_inbox_documents, _is_markdown_filename


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


def test_markdown_filename_detection_covers_markdown_extension() -> None:
    assert _is_markdown_filename("brief.md")
    assert _is_markdown_filename("brief.markdown")
    assert not _is_markdown_filename("brief.docx")
