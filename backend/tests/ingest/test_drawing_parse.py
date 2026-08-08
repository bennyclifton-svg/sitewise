from ingest.drawing_parse import parse_drawing_filename


def test_parse_hydraulic_sheet():
    identity = parse_drawing_filename("H-102 [D].pdf")
    assert identity.drawing_number == "H-102"
    assert identity.revision == "D"


def test_parse_structural_sheet_with_paren_revision():
    identity = parse_drawing_filename("15123_S0001_Notes-(03).pdf")
    assert identity.drawing_number == "S0001"
    assert identity.revision == "03"
    assert identity.title == "Notes"


def test_parse_job_prefixed_structural_omits_shared_project_number():
    identity = parse_drawing_filename("15123_S0203_basement 1_TReo Plan-(03).pdf")
    assert identity.drawing_number == "S0203"
    assert identity.revision == "03"
    assert identity.title == "basement 1 TReo Plan"


def test_parse_project_prefixed_cc_sheet_with_trailing_revision():
    identity = parse_drawing_filename("1115 CC-01 SETOUT PLAN D.pdf")
    assert identity.drawing_number == "CC-01"
    assert identity.revision == "D"
    assert identity.title == "SETOUT PLAN"


def test_parse_cc_a_sheet_does_not_collapse_to_inner_a_number():
    identity = parse_drawing_filename("CC-A-010 SITE PLAN.pdf")
    assert identity.drawing_number == "CC-A-010"
    assert identity.title == "SITE PLAN"


def test_parse_electrical_windows_short_name():
    identity = parse_drawing_filename("E01-EL~1.PDF")
    assert identity.drawing_number == "E01"
    assert identity.title is None


def test_parse_electrical_long_form_sheet():
    identity = parse_drawing_filename("E03 - ELECTRICAL - LEVEL L1 - LIGHTING LAYOUT - [C1].pdf")
    assert identity.drawing_number == "E03"
    assert identity.revision == "C1"
