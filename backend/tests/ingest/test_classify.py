from pathlib import Path

import pytest

from ingest.classify import classify_entry, parse_procurement_stage
from ingest.metadata import infer_project_context
from ingest.router import build_ingest_plan
from ingest.types import ManifestEntry


def _entry(relative_path: str, *, extension: str = ".pdf", filename: str | None = None) -> ManifestEntry:
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
    ("relative_path", "stage", "tenderer_id"),
    [
        ("procurement-blockb/03 RFT/spec.pdf", "rft", None),
        ("procurement-blockb/05 SUBMISSION 01/bid.pdf", "submission", "01"),
        ("procurement-blockb/06 EVALUATION/matrix.pdf", "evaluation", None),
        ("procurement-blockb/08 TRR/report.pdf", "trr", None),
    ],
)
def test_parse_procurement_stage(relative_path, stage, tenderer_id):
    metadata = parse_procurement_stage(relative_path)
    assert metadata["procurement_stage"] == stage
    if tenderer_id is None:
        assert "tenderer_id" not in metadata
    else:
        assert metadata["tenderer_id"] == tenderer_id


def test_classify_tender_submission():
    entry = _entry("procurement-blockb/05 SUBMISSION 01/bid.pdf")
    classification = classify_entry(entry)
    assert classification.document_class == "tender_submission"
    assert classification.ingest_mode == "full_text"
    assert classification.document_metadata["tenderer_id"] == "01"


def test_classify_drawing_pdf():
    entry = _entry("delivery-bankstown/09 Hydraulic/H-102 [D].pdf")
    classification = classify_entry(entry)
    assert classification.document_class == "drawing"
    assert classification.ingest_mode == "register_only"


def test_classify_seed_reference():
    entry = _entry("seed/defects-and-dlp-guide.md", extension=".md")
    classification = classify_entry(entry)
    assert classification.document_class == "reference_guide"
    assert classification.ingest_mode == "full_text"


def test_parse_procurement_stage_demo_folder_names():
    metadata = parse_procurement_stage("procurment-demo/05 TENDER SUBMISSIONS/SUBMIT 01 ACTIVE.pdf")
    assert metadata["procurement_stage"] == "submission"
    assert metadata["tenderer_id"] == "01"

    trr = parse_procurement_stage("procurment-demo/07 TENDER RECOMMENDATION/TRR [B].pdf")
    assert trr["procurement_stage"] == "trr"


def test_classify_site_plan_as_drawing():
    entry = _entry("delivery-house/OVERALL SITE PLAN WITH SEWER ZOI [02].pdf")
    classification = classify_entry(entry)
    assert classification.document_class == "drawing"
    assert classification.ingest_mode == "register_only"


def test_router_selects_odl_for_drawing_pdf():
    entry = _entry("delivery-bankstown/09 Hydraulic/H-102 [D].pdf")
    context = infer_project_context(entry.relative_path)
    classification = classify_entry(entry)
    plan = build_ingest_plan(entry, context, classification)
    assert plan.extractor == "pdf_odl"
    assert plan.chunker == "register"


def test_router_selects_odl_for_project_pdf_upload():
    entry = _entry("04-projects/caves-beach-reno/_inbox/Kaposi.pdf")
    context = infer_project_context(entry.relative_path)
    classification = classify_entry(entry)

    plan = build_ingest_plan(entry, context, classification)

    assert plan.extractor == "pdf_odl"
    assert plan.chunker == "prose"
