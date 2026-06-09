import os

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


TITLE_BLOCK = "SHEET: 2 OF 20 SCALE: 1:200 DRAWN BY: AW DATE: 11.03.24"


def test_detects_drawing_set_uniform_a3_landscape_with_title_blocks():
    from app.inbox.drawing_detection import detect_drawing_set

    data = _make_pdf([(1191, 842, f"SITE PLAN {TITLE_BLOCK}")] * 6)
    result = detect_drawing_set(data)
    assert result.is_drawing_set is True
    assert result.confidence >= 0.7
    assert result.page_count == 6


def test_rejects_single_page():
    from app.inbox.drawing_detection import detect_drawing_set

    data = _make_pdf([(1191, 842, f"SITE PLAN {TITLE_BLOCK}")])
    assert detect_drawing_set(data).is_drawing_set is False


def test_rejects_portrait_a4_report():
    from app.inbox.drawing_detection import detect_drawing_set

    body = "This report describes the methodology and findings in detail. " * 20
    data = _make_pdf([(595, 842, body)] * 8)
    assert detect_drawing_set(data).is_drawing_set is False


def test_rejects_landscape_without_title_block_keywords():
    from app.inbox.drawing_detection import detect_drawing_set

    data = _make_pdf([(1191, 842, "Slide content only, no title block")] * 4)
    assert detect_drawing_set(data).is_drawing_set is False


def test_rejects_mixed_page_sizes():
    from app.inbox.drawing_detection import detect_drawing_set

    pages = [(1191, 842, f"SITE PLAN {TITLE_BLOCK}"), (595, 842, "report text")]
    assert detect_drawing_set(_make_pdf(pages)).is_drawing_set is False


L18 = os.path.join(
    os.path.dirname(__file__), "..", "..", "..",
    "data", "delivery-house", "L18 CC Plans.pdf",
)


@pytest.mark.skipif(not os.path.exists(L18), reason="L18 fixture not present")
def test_detects_real_l18_drawing_set():
    from app.inbox.drawing_detection import detect_drawing_set

    with open(L18, "rb") as fh:
        result = detect_drawing_set(fh.read())
    assert result.is_drawing_set is True
    assert result.page_count == 20
    assert result.confidence >= 0.8
