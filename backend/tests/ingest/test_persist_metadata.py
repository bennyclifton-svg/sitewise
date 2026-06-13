from pathlib import Path
from unittest.mock import patch

from ingest.drawing_parse import DrawingIdentity
from ingest.extractors.base import ExtractedDocument, PageText
from ingest.metadata import infer_project_context
from ingest.persist import _merged_metadata
from ingest.router import build_ingest_plan
from ingest.types import ManifestEntry


def _entry(relative_path: str, *, filename: str | None = None) -> ManifestEntry:
    name = filename or relative_path.rsplit("/", maxsplit=1)[-1]
    return ManifestEntry(
        absolute_path=Path(relative_path),
        relative_path=relative_path,
        project=relative_path.split("/", maxsplit=1)[0],
        filename=name,
        extension=Path(name).suffix.lower(),
        size_bytes=100,
    )


def test_merged_metadata_includes_register_fields_from_filename() -> None:
    entry = _entry(
        "delivery-demo/03-design/electrical/E03 - ELECTRICAL - LEVEL L1 - LIGHTING LAYOUT - [C1].pdf",
    )
    context = infer_project_context(entry.relative_path)
    from ingest.classify import classify_entry

    plan = build_ingest_plan(entry, context, classify_entry(entry))
    extracted = ExtractedDocument(normalized_content="Report body")

    metadata = _merged_metadata(plan, extracted)

    assert metadata["document_number"] == "E03"
    assert metadata["title"] == "LEVEL L1 - LIGHTING LAYOUT"
    assert metadata["revision"] == "C1"
    assert metadata["discipline"] == "Electrical"
    assert metadata["metadata_confidence"] == "high"
    assert metadata["drawing_number"] == "E03"
    assert metadata["canonical_file_name"] == "E03 - LEVEL L1 - LIGHTING LAYOUT Rev C1.pdf"


def test_merged_metadata_uses_title_block_preview() -> None:
    entry = _entry(
        "delivery-demo/03-design/hydraulic/H-101-B1-Layout1.pdf",
    )
    context = infer_project_context(entry.relative_path)
    from ingest.classify import classify_entry

    plan = build_ingest_plan(entry, context, classify_entry(entry))
    extracted = ExtractedDocument(
        normalized_content=(
            "# Drawing register: H-101-B1-Layout1.pdf\n\n"
            "## Title block\n\n"
            "Drawing No. H-101\n"
            "Drawing Title BASEMENT 1 HYDRAULIC SERVICES PLAN\n"
            "Revision C2"
        ),
        drawing_identity=DrawingIdentity(
            drawing_number="H-101",
            revision=None,
            title="B1",
        ),
    )

    metadata = _merged_metadata(plan, extracted)

    assert metadata["document_number"] == "H-101"
    assert metadata["title"] == "BASEMENT 1 HYDRAULIC SERVICES PLAN"
    assert metadata["revision"] == "C2"
    assert metadata["discipline"] == "Hydraulic"
    assert metadata["metadata_confidence"] == "high"


def test_merged_metadata_parses_electrical_windows_short_name_from_title_block() -> None:
    entry = _entry(
        "delivery-demo/03-design/electrical/E01-EL~1.PDF",
    )
    context = infer_project_context(entry.relative_path)
    from ingest.classify import classify_entry

    plan = build_ingest_plan(entry, context, classify_entry(entry))
    assert plan.extractor == "pdf_drawing"
    extracted = ExtractedDocument(
        normalized_content=(
            "# Drawing register: E01-EL~1.PDF\n\n"
            "## Title block\n\n"
            "Drawing No. E01\n"
            "Drawing Title GENERAL NOTES & LEGEND\n"
            "Revision C1"
        ),
        drawing_identity=DrawingIdentity(
            drawing_number="E01",
            revision=None,
            title=None,
        ),
    )

    metadata = _merged_metadata(plan, extracted)

    assert metadata["document_number"] == "E01"
    assert metadata["title"] == "GENERAL NOTES & LEGEND"
    assert metadata["revision"] == "C1"
    assert metadata["discipline"] == "Electrical"
    assert metadata["metadata_confidence"] == "high"
    assert metadata["canonical_file_name"] == "E01 - GENERAL NOTES & LEGEND Rev C1.PDF"


def test_merged_metadata_preserves_classification_keys() -> None:
    entry = _entry("procurement-blockb/06 EVALUATION/matrix.pdf")
    context = infer_project_context(entry.relative_path)
    from ingest.classify import classify_entry

    plan = build_ingest_plan(entry, context, classify_entry(entry))
    extracted = ExtractedDocument(normalized_content="Evaluation matrix content")

    metadata = _merged_metadata(plan, extracted)

    assert metadata.get("procurement_stage") == "evaluation"
    assert "document_number" in metadata
    assert metadata["filename"] == entry.filename


def test_merged_metadata_uses_first_page_when_no_title_block() -> None:
    entry = _entry("delivery-demo/03-design/structural/S702-03.pdf")
    context = infer_project_context(entry.relative_path)
    from ingest.classify import classify_entry

    plan = build_ingest_plan(entry, context, classify_entry(entry))
    extracted = ExtractedDocument(
        normalized_content="## Page 1\n\nDrawing Number\nS702\nDrawing Title\nFOOTING LAYOUT",
        pages=[PageText(page_number=1, text="Drawing Number\nS702\nDrawing Title\nFOOTING LAYOUT")],
    )

    metadata = _merged_metadata(plan, extracted)

    assert metadata["document_number"] == "S702"
    assert metadata["title"] == "FOOTING LAYOUT"
    assert metadata["revision"] == "03"


def test_merged_metadata_survives_parse_failure() -> None:
    entry = _entry("delivery-demo/03-design/architect/plan.pdf")
    context = infer_project_context(entry.relative_path)
    from ingest.classify import classify_entry

    plan = build_ingest_plan(entry, context, classify_entry(entry))
    extracted = ExtractedDocument(normalized_content="content")

    with patch("ingest.persist.parse_document_metadata", side_effect=RuntimeError("parse failed")):
        metadata = _merged_metadata(plan, extracted)

    assert metadata["filename"] == entry.filename
    assert "document_number" not in metadata
