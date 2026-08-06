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


def test_recovers_split_identity_from_cover_sequence_and_source_revision():
    from app.inbox.sheet_titles import build_sheet_plan

    data = _make_pdf([
        (
            1191,
            842,
            "DRAWING LIST\n"
            "M01  MECHANICAL SERVICES - GENERAL NOTES\n"
            "M02  MECHANICAL SERVICES - EQUIPMENT SCHEDULE\n"
            "M03  MECHANICAL SERVICES - BASEMENT",
        ),
        (1191, 842, "EQUIPMENT SCHEDULE"),
        (1191, 842, "BASEMENT VENTILATION PLAN"),
    ])

    sheets = build_sheet_plan(
        data,
        source_filename="Mechanical Design & Spec [C].pdf",
    )

    assert [sheet.document_number for sheet in sheets] == ["M01", "M02", "M03"]
    assert [sheet.revision for sheet in sheets] == ["C", "C", "C"]
    assert sheets[0].filename.startswith("M01 - Mechanical Design & Spec - 01")
    assert sheets[0].filename.endswith("[C].pdf")


def test_does_not_infer_drawing_numbers_without_a_cover_register_heading():
    from app.inbox.sheet_titles import build_sheet_plan

    data = _make_pdf([
        (1191, 842, "EQUIPMENT SCHEDULE\nM01 FAN\nM02 FAN"),
        (1191, 842, "SECOND PAGE"),
    ])

    sheets = build_sheet_plan(data, source_filename="Mechanical Spec [C].pdf")

    assert [sheet.document_number for sheet in sheets] == [None, None]
    assert [sheet.revision for sheet in sheets] == ["C", "C"]


def _landscape_register_pdf() -> bytes:
    doc = fitz.open()
    schedule_titles = [
        "HARDSCAPE PLAN",
        "LANDSCAPE PLAN",
        "SECTION & DETAILS",
        "DETAILS",
        "SPECIFICATION",
    ]
    title_block_titles = [
        "HARDSCAPE PLAN",
        "LANDSCAPE PLAN",
        "DETAILS",
        "DETAILS",
        "SPECIFICATION",
    ]
    for index, title in enumerate(title_block_titles, start=1):
        page = doc.new_page(width=1191, height=842)
        if index == 1:
            page.insert_text((945, 620), "DRAWING SCHEDULE", fontsize=10)
            page.insert_text((945, 640), "SHEET #", fontsize=8)
            page.insert_text((1011, 640), "DRAWING TITLE", fontsize=8)
            page.insert_text((1144, 640), "REV.", fontsize=8)
            for row, schedule_title in enumerate(schedule_titles, start=1):
                y = 660 + (row * 14)
                page.insert_text((945, y), f"/{row}", fontsize=8)
                page.insert_text((1011, y), schedule_title, fontsize=8)
                page.insert_text((1144, y), "D", fontsize=8)

        page.insert_text((483, 744), "REV", fontsize=6)
        page.insert_text((925, 744), "TITLE:", fontsize=6)
        page.insert_text((1082, 744), "DWG.No:", fontsize=6)
        page.insert_text((933, 760), title, fontsize=10)
        page.insert_text((1094, 760), "LPCC 23 - 226 /", fontsize=6)
        page.insert_text((1147, 760), str(index), fontsize=6)
        for offset, revision in enumerate(("A", "B", "C", "D")):
            page.insert_text((487, 760 + offset * 10), revision, fontsize=6)

    data = doc.tobytes()
    doc.close()
    return data


def test_uses_drawing_schedule_and_title_blocks_for_split_sheet_identity():
    from app.inbox.sheet_titles import build_sheet_plan

    sheets = build_sheet_plan(
        _landscape_register_pdf(),
        source_filename="Landscape Design [D].pdf",
    )

    assert [sheet.title for sheet in sheets] == [
        "Hardscape Plan",
        "Landscape Plan",
        "Section & Details",
        "Details",
        "Specification",
    ]
    assert [sheet.document_number for sheet in sheets] == [
        "LPCC 23 - 226 / 1",
        "LPCC 23 - 226 / 2",
        "LPCC 23 - 226 / 3",
        "LPCC 23 - 226 / 4",
        "LPCC 23 - 226 / 5",
    ]
    assert [sheet.revision for sheet in sheets] == ["D"] * 5
    assert all("/" not in sheet.filename for sheet in sheets)
    assert sheets[0].filename == "LPCC-23-226-1 - Hardscape Plan [D].pdf"
