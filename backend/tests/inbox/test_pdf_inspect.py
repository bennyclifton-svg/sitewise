import fitz


def _make_pdf(pages):
    # pages: list of (width, height, text)
    doc = fitz.open()
    for width, height, text in pages:
        page = doc.new_page(width=width, height=height)
        if text:
            page.insert_text((72, 72), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def test_inspect_returns_page_geometry_and_text():
    from app.inbox.pdf_inspect import inspect_pdf

    data = _make_pdf([
        (1191, 842, "SITE PLAN SHEET: 2 OF 20 SCALE: 1:200"),
        (1191, 842, "GROUND FLOOR PLAN SHEET 3 OF 20"),
    ])
    info = inspect_pdf(data)

    assert info.page_count == 2
    assert info.encrypted is False
    assert info.pages[0].width == 1191
    assert info.pages[0].height == 842
    assert info.pages[0].is_landscape is True
    assert "SITE PLAN" in info.pages[0].text
    assert info.pages[0].has_text is True
