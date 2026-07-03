import struct

import fitz

from tender.services.pdf import PageExtract, extract_pages, render_page_png


def _text_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "Fixed Price Quotation\nSlab and footings $45,000")
    data = doc.tobytes()
    doc.close()
    return data


def test_extract_pages_returns_text_layer() -> None:
    pages = extract_pages(_text_pdf())
    assert len(pages) == 1
    assert isinstance(pages[0], PageExtract)
    assert "Slab and footings" in pages[0].text
    assert pages[0].page_no == 1


def _png_dimensions(data: bytes) -> tuple[int, int]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def test_render_page_png_is_png_at_150_dpi() -> None:
    png = render_page_png(_text_pdf(), page_no=1, dpi=150)
    assert _png_dimensions(png) == (1275, 1650)
