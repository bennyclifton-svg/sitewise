from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ingest.classify import classify_entry
from ingest.metadata import infer_project_context
from ingest.pipeline import ingest_plan, plan_entry
from ingest.router import build_ingest_plan, should_persist_chunks
from ingest.types import ManifestEntry


def _entry(relative_path: str, *, extension: str = ".md", filename: str | None = None) -> ManifestEntry:
    name = filename or relative_path.rsplit("/", maxsplit=1)[-1]
    return ManifestEntry(
        absolute_path=Path(relative_path),
        relative_path=relative_path,
        project=relative_path.split("/", maxsplit=1)[0],
        filename=name,
        extension=extension,
        size_bytes=100,
    )


@pytest.mark.parametrize(
    ("relative_path", "extension", "expected"),
    [
        ("seed/defects-and-dlp-guide.md", ".md", False),
        ("docs/clerk-brief.md", ".md", False),
        ("delivery-bankstown/09 Hydraulic/H-102 [D].pdf", ".pdf", False),
        ("procurement-blockb/06 EVALUATION/matrix.pdf", ".pdf", True),
    ],
)
def test_should_persist_chunks(relative_path, extension, expected) -> None:
    entry = _entry(relative_path, extension=extension)
    context = infer_project_context(entry.relative_path)
    classification = classify_entry(entry)
    plan = build_ingest_plan(entry, context, classification)
    assert should_persist_chunks(plan) is expected


@patch("ingest.pipeline.persist_ingest", return_value=True)
@patch("ingest.pipeline.embed_texts")
@patch("ingest.pipeline.chunk_document")
@patch("ingest.pipeline.extract_document")
def test_ingest_plan_skips_chunk_and_embed_for_seed(
    mock_extract,
    mock_chunk,
    mock_embed,
    mock_persist,
) -> None:
    entry = _entry("seed/defects-and-dlp-guide.md")
    plan = plan_entry(entry)
    mock_extract.return_value = MagicMock(normalized_content="Seed content")

    assert ingest_plan(plan, skip_if_unchanged=False) is True

    mock_chunk.assert_not_called()
    mock_embed.assert_not_called()
    mock_persist.assert_called_once()
    assert mock_persist.call_args[0][2] == []
    assert mock_persist.call_args[0][3] == []


@patch("ingest.pipeline.persist_ingest", return_value=True)
@patch("ingest.pipeline.embed_texts", return_value=[[0.1, 0.2]])
@patch("ingest.pipeline.chunk_document")
@patch("ingest.pipeline.extract_document")
def test_ingest_plan_chunks_and_embeds_reports(
    mock_extract,
    mock_chunk,
    mock_embed,
    mock_persist,
) -> None:
    entry = _entry("procurement-blockb/06 EVALUATION/matrix.pdf", extension=".pdf")
    plan = plan_entry(entry)
    chunk = MagicMock(content="Report section")
    mock_extract.return_value = MagicMock(
        normalized_content="Report content",
        pages=[],
        extraction_metadata={"pdf_extraction_source": "text_layer_fallback"},
    )
    mock_chunk.return_value = [chunk]
    events = []

    assert ingest_plan(plan, skip_if_unchanged=False, trace_callback=lambda *args: events.append(args)) is True

    mock_chunk.assert_called_once()
    mock_embed.assert_called_once_with(["Report section"])
    mock_persist.assert_called_once()
    extract_event = next(event for event in events if event[0] == "extract")
    assert extract_event[3]["pdf_extraction_source"] == "text_layer_fallback"
