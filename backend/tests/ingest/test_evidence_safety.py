"""D3: classification decides routing, never whether text is indexed."""
from __future__ import annotations

from pathlib import Path

from ingest.router import build_ingest_plan, should_persist_chunks
from ingest.types import Classification, ManifestEntry, ProjectContext


def _entry(filename: str, extension: str = ".pdf") -> ManifestEntry:
    return ManifestEntry(
        absolute_path=Path("/tmp") / filename,
        relative_path=f"01-cost/{filename}",
        project="demo",
        filename=filename,
        extension=extension,
        size_bytes=1024,
    )


def _context() -> ProjectContext:
    return ProjectContext(project="demo", phase="delivery", source_type="project_evidence")


def test_drawing_with_useful_text_still_persists_chunks() -> None:
    """A drawing's general notes are evidence. Class must not suppress them."""
    classification = Classification(
        document_class="drawing", ingest_mode="register_only", document_metadata={}
    )
    plan = build_ingest_plan(_entry("A-101 Rev C.pdf"), _context(), classification)

    assert should_persist_chunks(plan, extracted_text="GENERAL NOTES: refer structural. " * 20)


def test_document_without_useful_text_is_register_only() -> None:
    """No text is a legitimate reason to skip chunking. Class is not."""
    classification = Classification(
        document_class="drawing", ingest_mode="register_only", document_metadata={}
    )
    plan = build_ingest_plan(_entry("IMG_4471.pdf"), _context(), classification)

    assert not should_persist_chunks(plan, extracted_text="")


def test_useful_text_threshold_is_200_chars() -> None:
    classification = Classification(
        document_class="unknown", ingest_mode="full_text", document_metadata={}
    )
    plan = build_ingest_plan(_entry("Scan_001.pdf"), _context(), classification)

    assert not should_persist_chunks(plan, extracted_text="x" * 199)
    assert should_persist_chunks(plan, extracted_text="x" * 200)
