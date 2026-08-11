"""Geometry-driven title-block extraction.

CAD title blocks are grids with no reliable text reading order, so these tests
work from span rectangles captured off real sheets. Add a new sheet with:

    python scripts/dump_title_block_fixture.py DRAWING.pdf \
        tests/fixtures/title_blocks/<name>.json
"""

import json
from pathlib import Path

from ingest.title_block import TextSpan, extract_title_block_fields

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "title_blocks"


def load_spans(name: str) -> list[TextSpan]:
    payload = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    return [
        TextSpan(
            x0=span["x0"],
            y0=span["y0"],
            x1=span["x1"],
            y1=span["y1"],
            text=span["text"],
        )
        for span in payload["spans"]
    ]


def test_reads_identity_from_petersham_electrical_sheet():
    # E02-EL~1.PDF — the sheet whose 8.3 filename carries no title or revision,
    # so every field has to come off the drawing itself.
    fields = extract_title_block_fields(
        load_spans("e02-petersham-lighting-layout.json")
    )
    assert fields.document_number == "E02"
    assert fields.title == "LEVEL L0 GROUND - LIGHTING LAYOUT"
    assert fields.revision == "C1"


def test_pairs_label_with_value_to_its_right_on_the_same_row():
    fields = extract_title_block_fields(
        [
            TextSpan(x0=36, y0=84, x1=84, y1=92, text="Drawing Title:"),
            TextSpan(x0=86, y0=84, x1=241, y1=94, text="GENERAL NOTES & LEGEND"),
        ]
    )
    assert fields.title == "GENERAL NOTES & LEGEND"


def test_pairs_label_with_value_below_it_in_the_same_column():
    fields = extract_title_block_fields(
        [
            TextSpan(x0=1776, y0=1513, x1=1838, y1=1523, text="SHEET TITLE"),
            TextSpan(x0=1775, y0=1549, x1=2078, y1=1565, text="ROOF PLAN"),
        ]
    )
    assert fields.title == "ROOF PLAN"


def test_never_pairs_a_label_with_another_label():
    fields = extract_title_block_fields(
        [
            TextSpan(x0=36, y0=84, x1=84, y1=92, text="Drawing Title:"),
            TextSpan(x0=256, y0=83, x1=299, y1=91, text="Drawing No:"),
            TextSpan(x0=37, y0=100, x1=51, y1=107, text="Rev"),
        ]
    )
    assert fields.title is None
    assert fields.document_number is None
    assert fields.revision is None


def test_takes_only_the_revision_token_from_a_combined_issue_cell():
    fields = extract_title_block_fields(
        [
            TextSpan(x0=2262, y0=1580, x1=2292, y1=1590, text="ISSUE"),
            TextSpan(x0=2286, y0=1594, x1=2347, y1=1641, text="C1"),
            TextSpan(x0=2286, y0=1650, x1=2400, y1=1660, text="CONSTRUCTION ISSUE"),
        ]
    )
    assert fields.revision == "C1"


def test_strips_discipline_heading_stacked_above_the_sheet_title():
    fields = extract_title_block_fields(
        [
            TextSpan(x0=1776, y0=1513, x1=1838, y1=1523, text="SHEET TITLE"),
            TextSpan(x0=1775, y0=1530, x1=1900, y1=1545, text="ELECTRICAL SERVICES"),
            TextSpan(x0=1775, y0=1549, x1=2078, y1=1565, text="LEVEL 1 - POWER LAYOUT"),
        ]
    )
    assert fields.title == "LEVEL 1 - POWER LAYOUT"


def test_returns_empty_fields_when_no_labels_are_present():
    fields = extract_title_block_fields(
        [TextSpan(x0=0, y0=0, x1=10, y1=10, text="DL1")]
    )
    assert fields.document_number is None
    assert fields.title is None
    assert fields.revision is None
    assert fields.issuing_firm is None


def test_reads_issuing_firm_from_architect_label_beside_value():
    fields = extract_title_block_fields(
        [
            TextSpan(x0=40, y0=80, x1=100, y1=92, text="Architect:"),
            TextSpan(x0=110, y0=80, x1=280, y1=92, text="Roda Architects Pty Ltd"),
        ]
    )
    assert fields.issuing_firm == "Roda Architects Pty Ltd"


def test_reads_issuing_firm_from_consultant_label_below_value():
    fields = extract_title_block_fields(
        [
            TextSpan(x0=1800, y0=1400, x1=1880, y1=1412, text="CONSULTANT"),
            TextSpan(
                x0=1800,
                y0=1420,
                x1=2050,
                y1=1434,
                text="TDL Engineering Consulting Pty. Ltd.",
            ),
        ]
    )
    assert fields.issuing_firm == "TDL Engineering Consulting Pty. Ltd."


def test_ignores_phone_contact_line_as_issuing_firm():
    fields = extract_title_block_fields(
        [
            TextSpan(x0=1800, y0=1400, x1=1880, y1=1412, text="CONSULTANT"),
            TextSpan(x0=1800, y0=1420, x1=1920, y1=1434, text="Phone: 9922 5312"),
            TextSpan(
                x0=1800,
                y0=1440,
                x1=2100,
                y1=1454,
                text="Sulphurcrest Enterprises Pty Ltd",
            ),
        ]
    )
    assert fields.issuing_firm == "Sulphurcrest Enterprises Pty Ltd"


def test_ignores_identity_labels_inside_a_regulated_design_record_stamp():
    fields = extract_title_block_fields(
        [
            TextSpan(
                x0=163,
                y0=78,
                x1=281,
                y1=87,
                text="Regulated Design Record",
            ),
            TextSpan(x0=53, y0=146, x1=113, y1=156, text="Drawing Title:"),
            TextSpan(x0=216, y0=146, x1=270, y1=156, text="Drawing No:"),
            TextSpan(x0=54, y0=166, x1=72, y1=176, text="Rev"),
            TextSpan(x0=53, y0=168, x1=96, y1=178, text="dd.mm.yy"),
            TextSpan(x0=216, y0=186, x1=280, y1=196, text="XIAOGUANG GU"),
            TextSpan(x0=54, y0=186, x1=68, y1=196, text="01"),
        ]
    )

    assert fields.document_number is None
    assert fields.title is None
    assert fields.revision is None


def test_reads_consultant_title_block_with_generic_title_fragmented_number_and_revision_table():
    fields = extract_title_block_fields(
        [
            TextSpan(x0=483, y0=742, x1=497, y1=749, text="REV"),
            TextSpan(x0=925, y0=743, x1=937, y1=747, text="TITLE:"),
            TextSpan(x0=1082, y0=743, x1=1099, y1=747, text="DWG.No:"),
            TextSpan(x0=933, y0=751, x1=1034, y1=763, text="HARDSCAPE PLAN"),
            TextSpan(x0=487, y0=752, x1=492, y1=759, text="A"),
            TextSpan(x0=1095, y0=752, x1=1146, y1=760, text="LPCC 23 - 226 /"),
            TextSpan(x0=1147, y0=752, x1=1151, y1=760, text="1"),
            TextSpan(x0=487, y0=762, x1=492, y1=769, text="B"),
            TextSpan(x0=487, y0=771, x1=492, y1=778, text="C"),
            TextSpan(x0=487, y0=781, x1=492, y1=788, text="D"),
        ]
    )

    assert fields.document_number == "LPCC 23 - 226 / 1"
    assert fields.title == "HARDSCAPE PLAN"
    assert fields.revision == "D"


def _rotated_sheet_pdf() -> bytes:
    """A 90-degree rotated sheet, as CAD tools commonly export.

    Span coordinates come back in the page's unrotated frame, so "right of" and
    "below" only mean what a reader sees once the page rotation is applied.
    """
    import fitz

    document = fitz.open()
    page = document.new_page(width=1684, height=2384)

    def place(view_x: float, view_y: float, text: str) -> None:
        # Inverse of the 90-degree view transform: view_x = 2384 - raw_y.
        page.insert_text((view_y, 2384 - view_x), text, fontsize=9, rotate=90)

    place(1000, 500, "Drawing Title:")
    place(1120, 500, "HYDRAULICS SERVICES SPATIALS")
    place(1000, 540, "Drawing No.")
    place(1120, 540, "SK-003")
    place(1000, 580, "Rev.")
    place(1120, 580, "P1")
    page.set_rotation(90)

    data = document.tobytes()
    document.close()
    return data


def test_reads_a_rotated_sheets_title_block_in_reading_orientation(tmp_path):
    from ingest.title_block import extract_pdf_title_block_fields

    pdf_path = tmp_path / "rotated.pdf"
    pdf_path.write_bytes(_rotated_sheet_pdf())

    fields = extract_pdf_title_block_fields(pdf_path)

    assert fields.document_number == "SK-003"
    assert fields.title == "HYDRAULICS SERVICES SPATIALS"
    assert fields.revision == "P1"


def test_prefers_the_drawing_number_over_an_internal_reference():
    # A rotated ADP hydraulic sheet carries two number cells: "Drawing / Sketch
    # No." (HY-SK-01, the drawing) and "dwg no" (221102 - SK-003, an internal
    # reference). The drawing number is the one the register wants.
    fields = extract_title_block_fields(
        load_spans("hy-sk-01-rotated-hydraulic.json")
    )
    assert fields.document_number == "HY-SK-01"
    assert fields.revision == "P1"
