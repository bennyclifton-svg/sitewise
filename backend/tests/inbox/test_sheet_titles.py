import fitz


def _make_pdf(pages):
    doc = fitz.open()
    for width, height, text in pages:
        page = doc.new_page(width=width, height=height)
        if text:
            page.insert_text((72, 72), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def test_extracts_titles_and_builds_unique_filenames():
    from app.inbox.sheet_titles import build_sheet_plan

    data = _make_pdf([
        (1191, 842, "SUBMISSION PLANS SITE PLAN SHEET: 2 OF 20"),
        (1191, 842, "SUBMISSION PLANS ELEVATIONS SHEET: 5 OF 20"),
        (1191, 842, "SUBMISSION PLANS ELEVATIONS SHEET: 6 OF 20"),
    ])
    sheets = build_sheet_plan(data, source_filename="L18 CC Plans.pdf")
    titles = [s.title for s in sheets]
    assert titles[0] == "Site Plan"
    # Repeated "Elevations" titles must yield distinct filenames.
    filenames = [s.filename for s in sheets]
    assert len(set(filenames)) == len(filenames)
    assert filenames[0].endswith(".pdf")


def test_positional_fallback_when_no_text():
    from app.inbox.sheet_titles import build_sheet_plan

    data = _make_pdf([(1191, 842, ""), (1191, 842, "")])
    sheets = build_sheet_plan(data, source_filename="scan.pdf")
    assert sheets[0].title == "Sheet 01"
    assert sheets[1].filename != sheets[0].filename
