from types import SimpleNamespace
import uuid

from app.agent.document_context import SelectedTurnDocument
from app.workflows.transmittal import render_transmittal_markdown, transmittal_workspace_path


def _document() -> SelectedTurnDocument:
    return SelectedTurnDocument(
        workspace_file_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        source_document_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        workspace_path="04-projects/demo/02-design/A101.pdf",
        filename="A101.pdf",
        content_hash="a" * 64,
        size_bytes=1234,
        document_number="A101",
        title="Ground | floor plan",
        revision="C02",
        category="Architectural",
    )


def test_transmittal_is_a_deterministic_unissued_draft() -> None:
    project = SimpleNamespace(
        title="Walsh Renovation",
        workspace_path="04-projects/walsh-renovation",
    )

    markdown = render_transmittal_markdown(
        project=project,
        documents=[_document()],
        recipient=None,
        purpose="Issue for construction",
    )

    assert "**Draft only — not issued or sent.**" in markdown
    assert "TBC — confirm before issue" in markdown
    assert "| A101 | Ground \\| floor plan | C02 | Architectural |" in markdown
    assert "Issue only the document revisions listed above." in markdown
    assert transmittal_workspace_path(project, version=2).endswith(
        "/05-procurement/00-transmittals/transmittal_v02.draft.md"
    )
