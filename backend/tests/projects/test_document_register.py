import uuid
from types import SimpleNamespace

from app.projects.document_register import (
    build_document_register_rows,
    search_document_register_rows,
)


def _id(value: int) -> uuid.UUID:
    return uuid.UUID(int=value)


def test_register_rows_keep_ui_identity_and_search_structured_metadata() -> None:
    source = SimpleNamespace(
        id=_id(1),
        relative_path="04-projects/demo/_inbox/A250.pdf",
        filename="A250.pdf",
        document_type="Drawing",
        document_class="drawing",
        document_metadata={
            "document_number": "250",
            "title": "Basement floor plan",
            "revision": "C02",
            "discipline": "Architectural",
        },
    )
    workspace = SimpleNamespace(
        id=_id(2),
        workspace_path="04-projects/demo/_inbox/A250.pdf",
        filename="A250.pdf",
    )

    rows = build_document_register_rows([source], [workspace])

    assert rows[0].id == source.id
    assert rows[0].workspace_file_id == workspace.id
    assert rows[0].document_number == "250"
    assert search_document_register_rows(rows, query="basement", limit=50) == rows
    assert search_document_register_rows(rows, query="roof", limit=50) == []
    assert search_document_register_rows(
        rows,
        query=None,
        document_number_greater_than=200,
        limit=50,
    ) == rows
    assert search_document_register_rows(
        rows,
        query=None,
        document_number_greater_than=250,
        limit=50,
    ) == []


def test_register_excludes_unavailable_source_and_includes_unindexed_inbox_file() -> None:
    stale_source = SimpleNamespace(
        id=_id(3),
        relative_path="04-projects/demo/_inbox/deleted.pdf",
        filename="deleted.pdf",
        document_type="Drawing",
        document_class="drawing",
        document_metadata={},
    )
    pending_workspace = SimpleNamespace(
        id=_id(4),
        workspace_path="04-projects/demo/_inbox/new-upload.pdf",
        filename="new-upload.pdf",
    )

    rows = build_document_register_rows([stale_source], [pending_workspace])

    assert [row.id for row in rows] == [pending_workspace.id]
    assert rows[0].title == "new-upload.pdf"
