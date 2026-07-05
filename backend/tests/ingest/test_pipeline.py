from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ingest.classify import classify_entry
from ingest.metadata import infer_project_context
from ingest.pipeline import ingest_plan, plan_entry, plan_platform_knowledge
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
        ("seed/defects-and-dlp-guide.md", ".md", True),
        ("docs/clerk-brief.md", ".md", True),
        ("skills/systems/L09-House-Price.xlsx", ".xlsx", False),
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
def test_ingest_plan_chunks_and_embeds_platform_seed(
    mock_extract,
    mock_chunk,
    mock_embed,
    mock_persist,
) -> None:
    entry = _entry("seed/defects-and-dlp-guide.md")
    plan = plan_entry(entry)
    chunk = MagicMock(content="Seed chunk")
    mock_extract.return_value = MagicMock(
        normalized_content="Seed content",
        pages=[],
        extraction_metadata={},
    )
    mock_chunk.return_value = [chunk]
    mock_embed.return_value = [[0.1, 0.2]]

    assert ingest_plan(plan, skip_if_unchanged=False) is True

    mock_chunk.assert_called_once()
    mock_embed.assert_called_once_with(["Seed chunk"])
    mock_persist.assert_called_once()
    assert mock_persist.call_args[0][2] == mock_chunk.return_value
    assert mock_persist.call_args[0][3] == mock_embed.return_value


def test_plan_platform_knowledge_covers_doctrine_seed_and_reference(tmp_path) -> None:
    repo_root = tmp_path
    data_dir = repo_root / "data"
    (repo_root / "docs").mkdir()
    (data_dir / "seed").mkdir(parents=True)
    (data_dir / "skills" / "reference").mkdir(parents=True)
    (repo_root / "docs" / "clerk-brief.md").write_text("# Doctrine", encoding="utf-8")
    (data_dir / "seed" / "renovation-guide.md").write_text("# Renovation", encoding="utf-8")
    (data_dir / "seed" / "README.md").write_text("# skip", encoding="utf-8")
    (data_dir / "skills" / "reference" / "cost.md").write_text("# Cost", encoding="utf-8")

    plans = plan_platform_knowledge(data_dir=data_dir, repo_root=repo_root)

    assert [plan.entry.relative_path for plan in plans] == [
        "docs/clerk-brief.md",
        "seed/renovation-guide.md",
        "skills/reference/cost.md",
    ]
    assert [plan.context.source_type for plan in plans] == [
        "doctrine",
        "reference",
        "reference",
    ]
    assert all(should_persist_chunks(plan) for plan in plans)


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
