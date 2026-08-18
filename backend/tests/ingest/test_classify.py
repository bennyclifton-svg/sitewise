from pathlib import Path

import pytest

from ingest.classify import classify_entry, parse_procurement_stage
from ingest.metadata import infer_project_context
from ingest.router import build_ingest_plan
from ingest.title_block import TitleBlockFields
from ingest.types import ManifestEntry


def _entry(
    relative_path: str, *, extension: str = ".pdf", filename: str | None = None
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
    assert classification.document_class == "commercial"
    assert classification.ingest_mode == "full_text"
    assert classification.document_metadata["procurement_stage"] == "submission"
    assert classification.document_metadata["tenderer_id"] == "01"
    assert classification.document_subject == "none"
    assert classification.confidence == 0.85
    assert classification.basis == "filename"


def test_classify_drawing_pdf():
    entry = _entry("delivery-bankstown/09 Hydraulic/H-102 [D].pdf")
    classification = classify_entry(entry)
    assert classification.document_class == "drawing"


def test_classify_cost_plan_is_not_a_drawing():
    entry = _entry("01-cost/Cost Plan.pdf")
    classification = classify_entry(entry)
    # Stage 1: was misclassified as drawing
    assert classification.document_class != "drawing"


def test_classify_split_mechanical_sheet_as_drawing():
    entry = _entry(
        "04-projects/petersham/_inbox/"
        "M02 - Mechanical Design & Spec - 02 Flexible [C].pdf"
    )

    classification = classify_entry(entry)

    assert classification.document_class == "drawing"


def test_classify_seed_reference():
    entry = _entry("seed/defects-and-dlp-guide.md", extension=".md")
    classification = classify_entry(entry)
    assert classification.document_class == "report"
    assert classification.document_metadata["reference_kind"] == "reference_guide"
    assert classification.ingest_mode == "full_text"
    assert classification.basis == "structural"
    assert classification.confidence == 0.95


def test_parse_procurement_stage_demo_folder_names():
    metadata = parse_procurement_stage(
        "procurment-demo/05 TENDER SUBMISSIONS/SUBMIT 01 ACTIVE.pdf"
    )
    assert metadata["procurement_stage"] == "submission"
    assert metadata["tenderer_id"] == "01"

    trr = parse_procurement_stage(
        "procurment-demo/07 TENDER RECOMMENDATION/TRR [B].pdf"
    )
    assert trr["procurement_stage"] == "trr"


def test_classify_site_plan_as_drawing():
    entry = _entry("delivery-house/OVERALL SITE PLAN WITH SEWER ZOI [02].pdf")
    classification = classify_entry(entry)
    assert classification.document_class == "drawing"


def test_router_selects_odl_for_drawing_pdf():
    entry = _entry("delivery-bankstown/09 Hydraulic/H-102 [D].pdf")
    context = infer_project_context(entry.relative_path)
    classification = classify_entry(entry)
    plan = build_ingest_plan(entry, context, classification)
    assert plan.extractor == "pdf_odl"
    assert plan.chunker == "register"


def test_classify_markdown_civil_sheet_as_drawing():
    entry = _entry(
        "04-projects/newtown-extension-2/_inbox/"
        "C-001-civil-notes-legend-and-abbreviations.md",
        extension=".md",
    )
    classification = classify_entry(entry)
    assert classification.document_class == "drawing"
    assert classification.document_metadata["drawing_number"] == "C-001"

    context = infer_project_context(entry.relative_path)
    plan = build_ingest_plan(entry, context, classification)
    assert plan.extractor == "markdown"
    assert plan.chunker == "register"


def test_classify_markdown_fee_proposal_is_not_a_drawing():
    entry = _entry(
        "04-projects/newtown-extension-2/_inbox/"
        "catchment-civil-hydraulic-cch-p2604.md",
        extension=".md",
    )
    classification = classify_entry(entry)
    assert classification.document_class != "drawing"


def test_classify_lep_filename_as_planning_instrument():
    entry = _entry("delivery-newtown/official/Inner-West-LEP-2022.pdf")
    classification = classify_entry(entry)
    assert classification.document_class == "statutory_instrument"
    assert classification.ingest_mode == "full_text"


def test_router_selects_rtf_for_planning_instrument_upload():
    entry = _entry(
        "04-projects/newtown/_inbox/Inner-West-LEP-2022.rtf",
        extension=".rtf",
    )
    classification = classify_entry(entry)
    context = infer_project_context(entry.relative_path)
    plan = build_ingest_plan(entry, context, classification)

    assert classification.document_class == "statutory_instrument"
    assert plan.extractor == "rtf"
    assert plan.chunker == "prose"


def test_router_selects_rtf_for_generic_rich_text_upload():
    entry = _entry(
        "04-projects/newtown/_inbox/iwlep2022344.rtf",
        extension=".rtf",
    )
    classification = classify_entry(entry)
    context = infer_project_context(entry.relative_path)
    plan = build_ingest_plan(entry, context, classification)

    assert plan.extractor == "rtf"
    assert plan.chunker == "prose"


def test_classify_dcp_filename_as_planning_instrument():
    entry = _entry("delivery-newtown/_inbox/Inner West DCP 2022.pdf")
    classification = classify_entry(entry)
    assert classification.document_class == "statutory_instrument"


def test_classify_does_not_treat_dcp_assessment_report_as_instrument():
    entry = _entry("delivery-newtown/_inbox/Heritage DCP assessment report.pdf")
    classification = classify_entry(entry)
    assert classification.document_class == "report"


def test_router_selects_odl_for_project_pdf_upload():
    entry = _entry("04-projects/caves-beach-reno/_inbox/Kaposi.pdf")
    context = infer_project_context(entry.relative_path)
    classification = classify_entry(entry)

    plan = build_ingest_plan(entry, context, classification)

    assert plan.extractor == "pdf_odl"
    assert plan.chunker == "prose"


def test_scan_filename_resolves_from_content_markers() -> None:
    entry = _entry("04-projects/demo/_inbox/Scan_20260815_001.pdf")
    classification = classify_entry(
        entry,
        extracted_text=(
            "HERITAGE IMPACT STATEMENT\n"
            "The subject site is listed as a local heritage item."
        ),
    )
    assert classification.document_class == "report"
    assert classification.document_subject == "heritage"
    assert classification.basis == "content"
    assert classification.confidence == 0.95


def test_parsed_title_block_is_structural_drawing() -> None:
    entry = _entry("04-projects/demo/_inbox/scan-sheet.pdf")
    classification = classify_entry(
        entry,
        title_block=TitleBlockFields(document_number="A-204", revision="C"),
    )
    assert classification.document_class == "drawing"
    assert classification.basis == "structural"
    assert classification.confidence == 0.95
