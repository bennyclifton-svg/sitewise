from ingest.drawing_parse import parse_drawing_filename


def test_parse_hydraulic_sheet():
    identity = parse_drawing_filename("H-102 [D].pdf")
    assert identity.drawing_number == "H-102"
    assert identity.revision == "D"


def test_parse_structural_sheet_with_paren_revision():
    identity = parse_drawing_filename("15123_S0001_Notes-(03).pdf")
    assert identity.drawing_number == "15123_S0001"
    assert identity.revision == "03"
