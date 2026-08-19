import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agent.document_context import (
    SelectedDocumentContextError,
    documents_from_turn_context,
    resolve_selected_turn_documents,
)
from tests.conftest import run_async


PROJECT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
WORKSPACE_FILE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
SOURCE_DOCUMENT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _workspace_file() -> SimpleNamespace:
    return SimpleNamespace(
        id=WORKSPACE_FILE_ID,
        source_document_id=SOURCE_DOCUMENT_ID,
        workspace_path="04-projects/demo/02-design/A101.pdf",
        filename="A101.pdf",
        content_hash="a" * 64,
        size_bytes=1234,
    )


def _source_document() -> SimpleNamespace:
    return SimpleNamespace(
        id=SOURCE_DOCUMENT_ID,
        document_class="drawing",
        document_metadata={
            "document_number": "A101",
            "title": "Ground floor plan",
            "revision": "C02",
            "discipline": "Architectural",
        },
    )


def test_resolves_source_document_register_row_to_server_owned_file() -> None:
    session = SimpleNamespace(
        execute=AsyncMock(
            return_value=SimpleNamespace(all=lambda: [(_workspace_file(), _source_document())])
        )
    )

    documents = run_async(
        resolve_selected_turn_documents(
            session,
            project_id=PROJECT_ID,
            document_ids=[SOURCE_DOCUMENT_ID],
        )
    )

    assert len(documents) == 1
    document = documents[0]
    assert document.workspace_file_id == WORKSPACE_FILE_ID
    assert document.source_document_id == SOURCE_DOCUMENT_ID
    assert document.document_number == "A101"
    assert document.title == "Ground floor plan"
    assert document.revision == "C02"
    assert document.category == "Architectural"
    assert document.document_class == "drawing"


def test_rejects_a_register_row_that_does_not_resolve_in_the_project() -> None:
    session = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(all=lambda: []))
    )

    with pytest.raises(SelectedDocumentContextError, match="no longer available"):
        run_async(
            resolve_selected_turn_documents(
                session,
                project_id=PROJECT_ID,
                document_ids=[SOURCE_DOCUMENT_ID],
            )
        )


def test_turn_context_accepts_only_the_server_derived_document_shape() -> None:
    documents = documents_from_turn_context(
        {
            "selected_documents": [
                {
                    "workspace_file_id": str(WORKSPACE_FILE_ID),
                    "source_document_id": str(SOURCE_DOCUMENT_ID),
                    "workspace_path": "04-projects/demo/02-design/A101.pdf",
                    "filename": "A101.pdf",
                    "content_hash": "a" * 64,
                    "size_bytes": 1234,
                    "document_number": "A101",
                    "title": "Ground floor plan",
                    "revision": "C02",
                    "category": "Architectural",
                }
            ]
        }
    )

    assert documents[0].workspace_file_id == WORKSPACE_FILE_ID
    assert documents_from_turn_context({"selected_documents": [{"title": "bad"}]}) == []
