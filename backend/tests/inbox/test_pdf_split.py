import fitz
import pytest


def _make_pdf(pages):
    doc = fitz.open()
    for width, height, text in pages:
        page = doc.new_page(width=width, height=height)
        if text:
            page.insert_text((72, 72), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def test_splits_into_single_pages_preserving_text():
    from app.inbox.pdf_split import split_pdf_pages

    data = _make_pdf([
        (1191, 842, "PAGE ONE SITE PLAN"),
        (1191, 842, "PAGE TWO ELEVATIONS"),
    ])
    parts = split_pdf_pages(data)
    assert len(parts) == 2
    for part in parts:
        d = fitz.open(stream=part, filetype="pdf")
        assert d.page_count == 1
        d.close()
    assert "PAGE ONE" in fitz.open(stream=parts[0], filetype="pdf")[0].get_text()
    assert "PAGE TWO" in fitz.open(stream=parts[1], filetype="pdf")[0].get_text()


def test_rejects_pdf_over_page_cap():
    from app.inbox.pdf_split import PdfSplitError, split_pdf_pages

    data = _make_pdf([(595, 842, "x")] * 3)
    with pytest.raises(PdfSplitError):
        split_pdf_pages(data, max_pages=2)
