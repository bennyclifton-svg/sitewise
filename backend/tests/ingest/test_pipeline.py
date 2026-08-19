from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ingest.classify import classify_entry
from ingest.metadata import infer_project_context
from ingest.pipeline import (
    ingest_folder,
    ingest_plan,
    ingest_platform_knowledge,
    plan_entry,
    plan_platform_knowledge,
)
from ingest.router import build_ingest_plan, should_persist_chunks
from ingest.types import ManifestEntry


def _entry(
    relative_path: str, *, extension: str = ".md", filename: str | None = None
) -> ManifestEntry:
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
    ("relative_path", "extension", "extracted_text", "expected"),
    [
        ("seed/defects-and-dlp-guide.md", ".md", "x" * 200, True),
        ("docs/clerk-brief.md", ".md", "x" * 200, True),
        ("skills/systems/L09-House-Price.xlsx", ".xlsx", "x" * 200, False),
        ("delivery-bankstown/09 Hydraulic/H-102 [D].pdf", ".pdf", "x" * 200, True),
        ("procurement-blockb/06 EVALUATION/matrix.pdf", ".pdf", "x" * 200, True),
    ],
)
def test_should_persist_chunks(relative_path, extension, extracted_text, expected) -> None:
    entry = _entry(relative_path, extension=extension)
    context = infer_project_context(entry.relative_path)
    classification = classify_entry(entry)
    plan = build_ingest_plan(entry, context, classification)
    assert should_persist_chunks(plan, extracted_text=extracted_text) is expected


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
        normalized_content="Seed content " * 20,
        pages=[],
        extraction_metadata={},
    )
    mock_chunk.return_value = [chunk]
    mock_embed.return_value = [[0.1, 0.2]]

    assert ingest_plan(plan, skip_if_unchanged=False) is True

    mock_chunk.assert_called_once()
    mock_embed.assert_called_once_with(
        ["Seed chunk"], relative_paths=["seed/defects-and-dlp-guide.md"]
    )
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
    (data_dir / "seed" / "renovation-guide.md").write_text(
        "# Renovation", encoding="utf-8"
    )
    (data_dir / "seed" / "README.md").write_text("# skip", encoding="utf-8")
    (data_dir / "skills" / "reference" / "cost.md").write_text(
        "# Cost", encoding="utf-8"
    )

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
    assert all(should_persist_chunks(plan, extracted_text="x" * 200) for plan in plans)


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
        normalized_content="Report content " * 20,
        pages=[],
        extraction_metadata={"pdf_extraction_source": "text_layer_fallback"},
    )
    mock_chunk.return_value = [chunk]
    events = []

    assert (
        ingest_plan(
            plan,
            skip_if_unchanged=False,
            trace_callback=lambda *args: events.append(args),
        )
        is True
    )

    mock_chunk.assert_called_once()
    mock_embed.assert_called_once_with(
        ["Report section"],
        relative_paths=["procurement-blockb/06 EVALUATION/matrix.pdf"],
    )
    mock_persist.assert_called_once()
    extract_event = next(event for event in events if event[0] == "extract")
    assert extract_event[3]["pdf_extraction_source"] == "text_layer_fallback"


@pytest.mark.parametrize(
    ("runner", "plan_patch", "event"),
    [
        (ingest_folder, "ingest.pipeline.plan_folder", "ingest_file_failed"),
        (
            ingest_platform_knowledge,
            "ingest.pipeline.plan_platform_knowledge",
            "ingest_platform_file_failed",
        ),
    ],
)
def test_batch_ingest_logs_only_failure_class(runner, plan_patch, event) -> None:
    canary = "ch03-ingest-provider-token-xxxxxxxxxxxxxxxxxxxxxxxx"
    plan = plan_entry(_entry("seed/defects-and-dlp-guide.md"))

    with (
        patch(plan_patch, return_value=[plan]),
        patch("ingest.pipeline.ingest_plan", side_effect=RuntimeError(canary)),
        patch("ingest.pipeline.logger.error") as log_error,
    ):
        result = (
            runner("seed", dry_run=False)
            if runner is ingest_folder
            else runner(dry_run=False)
        )

    assert result.skipped == 1
    assert log_error.call_args.args[0] == event
    assert log_error.call_args.kwargs["error_type"] == "RuntimeError"
    assert canary not in str(log_error.call_args)
