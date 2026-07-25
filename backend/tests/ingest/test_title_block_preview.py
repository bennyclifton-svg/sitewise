"""The register path must read a drawing's identity off the sheet, not off the
page's raw text order, because a decoupled title block has no usable order.
"""

import fitz

from ingest.document_metadata import parse_document_metadata
from ingest.title_block import pdf_title_block_preview


def _decoupled_title_block_pdf() -> bytes:
    """A sheet whose labels are graphically decoupled from their values.

    Mirrors the real failure: hundreds of fitting tags first, then a column of
    labels, then the values — so reading text in order pairs a label with the
    next label.
    """
    document = fitz.open()
    page = document.new_page(width=2384, height=1684)

    for index in range(40):
        page.insert_text((100 + (index % 8) * 90, 300 + (index // 8) * 60), "DL1", fontsize=9)

    # Compliance stamp, top left: label then value on the same row.
    page.insert_text((36, 90), "Drawing Title:", fontsize=8)
    page.insert_text((90, 90), "LEVEL 3 - POWER LAYOUT", fontsize=8)
    page.insert_text((256, 90), "Drawing No:", fontsize=8)
    page.insert_text((302, 90), "E07", fontsize=8)
    page.insert_text((37, 106), "Rev", fontsize=8)
    page.insert_text((43, 128), "D2", fontsize=8)
    # The stamp's remaining labels, which the text-order parser misreads.
    page.insert_text((37, 150), "Project Address:", fontsize=8)
    page.insert_text((37, 166), "DP Full Name", fontsize=8)

    # Main title block, bottom right: label above value in the same cell.
    page.insert_text((1776, 1520), "SHEET TITLE", fontsize=8)
    page.insert_text((1775, 1556), "ELECTRICAL SERVICES", fontsize=8)
    page.insert_text((1775, 1574), "LEVEL 3 - POWER LAYOUT", fontsize=8)

    data = document.tobytes()
    document.close()
    return data


def test_preview_reports_identity_from_a_decoupled_title_block():
    preview = pdf_title_block_preview(_decoupled_title_block_pdf())
    assert preview is not None

    result = parse_document_metadata(
        file_name="E07-EL~1.PDF",
        filed_path="04-projects/demo/03-design/electrical",
        source_path="04-projects/demo/_inbox/ELEC/E07-EL~1.PDF",
        preview_snippet=preview,
    )
    assert result.document_number == "E07"
    assert result.title == "LEVEL 3 - POWER LAYOUT"
    assert result.revision == "D2"
    assert result.canonical_file_name == "E07 - LEVEL 3 - POWER LAYOUT Rev D2.PDF"


def test_preview_is_none_when_the_pdf_has_no_title_block():
    document = fitz.open()
    document.new_page(width=600, height=800)
    data = document.tobytes()
    document.close()

    assert pdf_title_block_preview(data) is None
