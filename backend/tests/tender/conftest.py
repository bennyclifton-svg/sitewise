import fitz
import pytest

# Letter-size page: 612 x 792 pt.
PAGE_WIDTH_PT = 612
PAGE_HEIGHT_PT = 792


@pytest.fixture
def text_pdf_bytes() -> bytes:
    """Two-page PDF with a real text layer (digital quote)."""

    doc = fitz.open()
    for page_index in range(2):
        page = doc.new_page(width=PAGE_WIDTH_PT, height=PAGE_HEIGHT_PT)
        for line in range(30):
            page.insert_text(
                (72, 72 + line * 20),
                f"Item {page_index}.{line:02d}  Supply and install plasterboard linings  $4,500.00",
            )
    payload = doc.tobytes()
    doc.close()
    return payload


@pytest.fixture
def image_only_pdf_bytes() -> bytes:
    """Two-page PDF with drawings but no extractable text (scanned quote)."""

    doc = fitz.open()
    for _ in range(2):
        page = doc.new_page(width=PAGE_WIDTH_PT, height=PAGE_HEIGHT_PT)
        page.draw_rect(fitz.Rect(50, 50, 550, 700), fill=(0.9, 0.9, 0.9))
        page.draw_line((72, 100), (540, 100))
        page.draw_circle((300, 400), 80, fill=(0.5, 0.5, 0.5))
    payload = doc.tobytes()
    doc.close()
    return payload
