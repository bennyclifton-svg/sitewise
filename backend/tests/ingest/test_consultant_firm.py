"""Text-path extraction of issuing consultant firms from certificates and covers."""

from ingest.consultant_firm import extract_issuing_firm_from_text


def test_extracts_firm_from_hydraulic_design_certificate_phrasing():
    text = """
    HYDRAULIC SERVICES DESIGN CERTIFICATE
    Hydraulic Services drawings issued by TDL Engineering Consulting Pty. Ltd.
    Project: 82 Queen Street, Petersham
    """
    assert extract_issuing_firm_from_text(text) == "TDL Engineering Consulting Pty Ltd"


def test_extracts_firm_from_fire_safety_studio_certificate():
    text = """
    FIRE SERVICES DESIGN CERTIFICATE
    Prepared by Fire Safety Studio Pty Ltd
    On behalf of the design practitioner
    """
    assert extract_issuing_firm_from_text(text) == "Fire Safety Studio Pty Ltd"


def test_extracts_structural_copyright_owner_as_issuing_firm():
    text = """
    STRUCTURAL ENGINEERING DRAWINGS
    COPYRIGHT ARE THE PROPERTY OF ZAIT ENGINEERING SOLUTIONS PTY LTD
    Drawing No. S100
    """
    assert (
        extract_issuing_firm_from_text(text) == "Zait Engineering Solutions Pty Ltd"
    )


def test_ignores_client_builder_entities_when_consultant_phrasing_present():
    text = """
    Acoustic Certification Design
    This document is the property of Acoustic Logic Pty Ltd
    Prepared for J & CG Con Pty Ltd / Joins Win Pty Ltd
    """
    assert extract_issuing_firm_from_text(text) == "Acoustic Logic Pty Ltd"


def test_returns_none_when_no_firm_signal_exists():
    text = "ELECTRICAL SERVICES\nDRAWING SCHEDULE\nE00 COVER SHEET"
    assert extract_issuing_firm_from_text(text) is None


def test_ignores_project_builder_banner_jw_building():
    text = "JW BUILDING\n572 PARRAMATTA ROAD\nELECTRICAL SERVICES\nDRAWING SCHEDULE"
    assert extract_issuing_firm_from_text(text) is None


def test_ignores_phone_contact_line_as_firm():
    text = "CONSULTANT\nPhone: 9922 5312\nCopyright Sulphurcrest Enterprises Pty Ltd"
    assert extract_issuing_firm_from_text(text) == "Sulphurcrest Enterprises Pty Ltd"


def test_strips_copyright_prefix_from_landscape_firm():
    text = "Copyright Sulphurcrest Enterprises Pty Ltd trading as LPCC"
    assert extract_issuing_firm_from_text(text) == "Sulphurcrest Enterprises Pty Ltd"


def test_prefers_fire_safety_studio_over_tdl_on_fer_certificate():
    text = """
    FER FIRE SAFETY STUDIO
    Fire Safety Studio Pty Ltd
    wet/dry fire/hydraulic drawings by TDL Engineering Consulting Pty Ltd
    """
    assert extract_issuing_firm_from_text(text) == "Fire Safety Studio Pty Ltd"
