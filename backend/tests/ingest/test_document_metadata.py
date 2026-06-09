import json
import re
from pathlib import Path

from ingest.document_metadata import parse_document_metadata

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
CORPUS_PATH = FIXTURES_DIR / "intake-filename-corpus.json"


def _parse(**kwargs):
    return parse_document_metadata(**kwargs)


def test_parses_cc_a_architectural_drawing_numbers():
    result = _parse(
        file_name="CC-A-010 SITE PLAN.pdf",
        filed_path="04-projects/demo/03-design/architect",
        source_path="04-projects/demo/_inbox/ARCHITECTURE/CC 010 _ SITE PLAN/CC-A-010 SITE PLAN.pdf",
    )
    assert result.document_number == "CC-A-010"
    assert result.title == "SITE PLAN"
    assert result.revision == "Current"
    assert result.discipline == "Architectural"
    assert result.confidence == "high"
    assert result.canonical_file_name == "CC-A-010 - SITE PLAN.pdf"


def test_parses_electrical_sheets_with_bracket_revision():
    result = _parse(
        file_name="E03 - ELECTRICAL - LEVEL L1 - LIGHTING LAYOUT - [C1].pdf",
        filed_path="04-projects/demo/03-design/electrical",
        source_path="04-projects/demo/_inbox/ELEC/E03 - ELECTRICAL - LEVEL L1 - LIGHTING LAYOUT - [C1].pdf",
    )
    assert result.document_number == "E03"
    assert result.title == "LEVEL L1 - LIGHTING LAYOUT"
    assert result.revision == "C1"
    assert result.discipline == "Electrical"
    assert result.confidence == "high"
    assert result.canonical_file_name == "E03 - LEVEL L1 - LIGHTING LAYOUT Rev C1.pdf"


def test_parses_hydraulic_layout_drawings_from_filename():
    result = _parse(
        file_name="H-101-B1-Layout1.pdf",
        filed_path="04-projects/demo/03-design/hydraulic",
        source_path="04-projects/demo/_inbox/HYDRAULIC/H-101-B1-Layout1.pdf",
    )
    assert result.document_number == "H-101"
    assert result.title == "B1"
    assert result.discipline == "Hydraulic"
    assert result.confidence == "medium"
    assert result.canonical_file_name == "H-101 - B1.pdf"


def test_parses_hydraulic_drawings_from_pdf_title_blocks():
    result = _parse(
        file_name="H-101-B1-Layout1.pdf",
        filed_path="04-projects/demo/03-design/hydraulic",
        source_path="04-projects/demo/_inbox/HYDRAULIC/H-101-B1-Layout1.pdf",
        preview_snippet="\n".join(
            [
                "Drawing No. H-101",
                "Drawing Title BASEMENT 1 HYDRAULIC SERVICES PLAN",
                "Revision C2",
            ]
        ),
    )
    assert result.document_number == "H-101"
    assert result.title == "BASEMENT 1 HYDRAULIC SERVICES PLAN"
    assert result.revision == "C2"
    assert result.discipline == "Hydraulic"
    assert result.confidence == "high"
    assert result.canonical_file_name == "H-101 - BASEMENT 1 HYDRAULIC SERVICES PLAN Rev C2.pdf"


def test_prefers_pdf_title_block_rows_over_hydraulic_filename_fallbacks():
    result = _parse(
        file_name="H-104-L2-Layout1.pdf",
        filed_path="04-projects/demo/03-design/hydraulic",
        source_path="04-projects/demo/_inbox/H-104-L2-Layout1.pdf",
        preview_snippet="\n".join(
            [
                "Drawing No: H-104",
                "Drawing Title: LEVEL 2 - DRAINAGE LAYOUT",
                "Revision: 01",
            ]
        ),
    )
    assert result.document_number == "H-104"
    assert result.title == "LEVEL 2 - DRAINAGE LAYOUT"
    assert result.revision == "01"
    assert result.discipline == "Hydraulic"
    assert result.confidence == "high"
    assert result.canonical_file_name == "H-104 - LEVEL 2 - DRAINAGE LAYOUT Rev 01.pdf"


def test_parses_structural_sheets_without_duplicating_drawing_number():
    result = _parse(
        file_name="S702-03.pdf",
        filed_path="04-projects/demo/03-design/structural",
        source_path="04-projects/demo/_inbox/STRUCTURAL/S702-03.pdf",
    )
    assert result.document_number == "S702"
    assert result.title == ""
    assert result.revision == "03"
    assert result.discipline == "Structural"
    assert result.confidence == "medium"
    assert result.canonical_file_name == "S702 Rev 03.pdf"


def test_parses_s_series_structural_sheets_with_repeated_drawing_number_suffixes():
    result = _parse(
        file_name="S101 - GENERAL NOTES, SHEET 1 Drawing No- S101 Rev SET.pdf",
        filed_path="04-projects/demo/03-design/structural",
        source_path="04-projects/demo/_inbox/S101 - GENERAL NOTES, SHEET 1 Drawing No- S101 Rev SET.pdf",
    )
    assert result.document_number == "S101"
    assert result.title == "GENERAL NOTES, SHEET 1"
    assert result.revision == "SET"
    assert result.discipline == "Structural"
    assert result.confidence == "medium"
    assert result.canonical_file_name == "S101 - GENERAL NOTES, SHEET 1 Rev SET.pdf"


def test_parses_s_series_structural_cover_sheets_with_drawing_number_suffixes():
    result = _parse(
        file_name="DRAWING No. REV. - COVER SHEET Drawing No- S100 Rev 03.pdf",
        filed_path="04-projects/demo/03-design/structural",
        source_path="04-projects/demo/_inbox/DRAWING No. REV. - COVER SHEET Drawing No- S100 Rev 03.pdf",
    )
    assert result.document_number == "S100"
    assert result.title == "COVER SHEET"
    assert result.revision == "03"
    assert result.discipline == "Structural"
    assert result.confidence == "medium"
    assert result.canonical_file_name == "S100 - COVER SHEET Rev 03.pdf"


def test_parses_structural_drawing_titles_from_pdf_title_blocks():
    result = _parse(
        file_name="S702-03.pdf",
        filed_path="04-projects/demo/03-design/structural",
        source_path="04-projects/demo/_inbox/STRUCTURAL/S702-03.pdf",
        preview_snippet="\n".join(
            [
                "Drawing Number",
                "S702",
                "Drawing Title",
                "FOOTING LAYOUT - LEVEL 3",
                "Revision",
                "03",
            ]
        ),
    )
    assert result.document_number == "S702"
    assert result.title == "FOOTING LAYOUT - LEVEL 3"
    assert result.revision == "03"
    assert result.confidence == "high"
    assert result.canonical_file_name == "S702 - FOOTING LAYOUT - LEVEL 3 Rev 03.pdf"


def test_prefers_clean_structural_title_block_titles_over_noisy_filenames():
    result = _parse(
        file_name="BLOCKWORK - STANDARD MASONRY DETAILS Drawing No- BLOCKWORK VERTICAL 70 COVER TO VERTICAL REINFORCEMENT Rev 01.pdf",
        filed_path="04-projects/demo/03-design/structural",
        source_path="04-projects/demo/_inbox/BLOCKWORK - STANDARD MASONRY DETAILS Drawing No- BLOCKWORK VERTICAL 70 COVER TO VERTICAL REINFORCEMENT Rev 01.pdf",
        preview_snippet="\n".join(
            [
                "Drawing No: S114",
                "Drawing Title: STANDARD MASONRY DETAILS",
                "Revision: 01",
            ]
        ),
    )
    assert result.document_number == "S114"
    assert result.title == "STANDARD MASONRY DETAILS"
    assert result.revision == "01"
    assert result.discipline == "Structural"
    assert result.confidence == "high"
    assert result.canonical_file_name == "S114 - STANDARD MASONRY DETAILS Rev 01.pdf"


def test_expands_ctmp_filenames_and_reads_reference_numbers_from_report_front_pages():
    result = _parse(
        file_name="CTMP (FINAL).pdf",
        filed_path="04-projects/demo/07-construction/04-management-plans",
        source_path="04-projects/demo/_inbox/TRAFFIC/CTMP (FINAL).pdf",
        preview_snippet="\n".join(
            [
                "Construction Traffic Management Plan",
                "Reference No. TMP-22372-FINAL",
                "Revision 2",
            ]
        ),
    )
    assert result.document_number == "TMP-22372-FINAL"
    assert result.title == "Construction Traffic Management Plan"
    assert result.revision == "2"
    assert result.discipline == "Traffic"
    assert result.confidence == "high"
    assert result.canonical_file_name == "TMP-22372-FINAL - Construction Traffic Management Plan Rev 2.pdf"


def test_parses_hydrant_style_for_construction_filenames():
    result = _parse(
        file_name="FOR CONSTRUCTION 26.03.21 [H]FS001 - SITE PLAN AND WATER SUPPLY [H].pdf",
        filed_path="04-projects/demo/03-design/fire",
    )
    assert result.document_number == "FS001"
    assert result.title == "SITE PLAN AND WATER SUPPLY"
    assert result.revision == "H"
    assert result.confidence == "high"


def test_strong_filename_wins_over_value_above_label_title_block():
    # ArchiCAD/GSPublisher title blocks print the value on the line *above* its
    # label, and flatten to a confusing order. The label-adjacency parser grabs
    # "CC-A-182" as the title and "STATUS" as the number. A high-confidence
    # filename that already carries number + title must win outright.
    result = _parse(
        file_name="CC-A-182 RCP - LEVEL 1.pdf",
        filed_path="04-projects/demo/03-design/architect",
        source_path="04-projects/demo/_inbox/ARCHITECTURE/CC-A-182 RCP - LEVEL 1.pdf",
        preview_snippet="\n".join(
            [
                "CC-A-182",
                "22_009",
                "RCP - LEVEL 1",
                "DRAWING TITLE",
                "CC-A-182",
                "CC2 ISSUE FOR CONSTRUCTION",
                "REV A 06.11.2023",
                "DRAWING NUMBER",
                "STATUS",
            ]
        ),
    )
    assert result.document_number == "CC-A-182"
    assert result.title == "RCP - LEVEL 1"
    assert result.discipline == "Architectural"
    assert result.confidence == "high"
    assert result.canonical_file_name == "CC-A-182 - RCP - LEVEL 1.pdf"


def test_title_block_does_not_capture_label_words_as_document_number():
    # When the filename is not informative, the title-block parser must still
    # refuse to treat a label word ("STATUS") as the document number.
    result = _parse(
        file_name="Scan_0007.pdf",
        filed_path="04-projects/demo/03-design/architect",
        source_path="04-projects/demo/_inbox/ARCHITECTURE/Scan_0007.pdf",
        preview_snippet="\n".join(
            [
                "SOME PLAN TITLE",
                "DRAWING NUMBER",
                "STATUS",
            ]
        ),
    )
    assert result.document_number != "STATUS"


def test_parses_markdown_title_blocks_from_preview_snippets():
    result = _parse(
        file_name="C-11.md",
        filed_path="04-projects/demo/03-design/architect",
        preview_snippet="\n".join(
            [
                "| **Drawing title** | SITE PLAN — BAL ZONES, SETBACKS & APZ |",
                "| **Drawing number** | SDS-T03-SP-01 |",
                "| **Revision** | **Rev B — DA ISSUE** |",
            ]
        ),
    )
    assert result.document_number == "SDS-T03-SP-01"
    assert result.title == "SITE PLAN — BAL ZONES, SETBACKS & APZ"
    assert result.revision == "B"
    assert result.confidence == "high"


def test_keeps_windows_short_names_unchanged():
    result = _parse(
        file_name="E01-EL~1.PDF",
        filed_path="04-projects/demo/03-design/electrical",
        source_path="04-projects/demo/_inbox/ELEC/E01-EL~1.PDF",
    )
    assert result.canonical_file_name == "E01-EL~1.PDF"
    assert result.confidence == "low"


def test_parses_petersham_corpus_with_strong_coverage():
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    entries = corpus["entries"]
    confidence_counts = {"high": 0, "medium": 0, "low": 0}
    for entry in entries:
        confidence = entry["parsed"]["confidence"]
        confidence_counts[confidence] += 1

    assert len(entries) >= 300
    assert confidence_counts["high"] + confidence_counts["medium"] > 180
    assert confidence_counts["low"] / len(entries) < 0.5


def test_round_trips_corpus_entries_through_parse_document_metadata():
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    for entry in corpus["entries"][:40]:
        parsed = _parse(
            file_name=entry["fileName"],
            filed_path=entry["filedPath"],
            source_path=entry["sourcePath"],
        )
        assert parsed.confidence == entry["parsed"]["confidence"]
        assert parsed.document_number == entry["parsed"]["documentNumber"]
        assert parsed.title == entry["parsed"]["title"]
        assert parsed.canonical_file_name == entry["parsed"]["canonicalFileName"]


def test_ignores_scale_labels_misparsed_as_revision_from_pdf_title_blocks():
    result = _parse(
        file_name="Acoustic Details Hydraulic Flooring (Preliminary).pdf",
        filed_path="04-projects/demo/03-design/architect",
        source_path="04-projects/demo/_inbox/ACOUSTIC/Acoustic Details Hydraulic Flooring (Preliminary).pdf",
        preview_snippet="\n".join(
            [
                "Drawing No. -",
                "Title - Acoustic Details Hydraulic Flooring (Preliminary)",
                "Rev",
                "Scale: 1:100",
            ]
        ),
    )
    assert result.document_number == ""
    assert result.title == "Acoustic Details Hydraulic Flooring (Preliminary)"
    assert result.revision == "Current"
    assert result.canonical_file_name == "Acoustic Details Hydraulic Flooring (Preliminary).pdf"
    assert not re.search(r"[:/\\|?*]", result.canonical_file_name)
    assert not result.canonical_file_name.startswith("-")
