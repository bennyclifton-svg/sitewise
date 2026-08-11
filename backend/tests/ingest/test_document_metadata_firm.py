from ingest.document_metadata import parse_document_metadata


def test_parse_document_metadata_reads_consultant_line_from_preview():
    parsed = parse_document_metadata(
        file_name="H-001-COVER-Layout1.pdf",
        filed_path="04-projects/petersham/03-design/hydraulic/H-001 COVER.pdf",
        preview_snippet=(
            "Drawing No. H-001\n"
            "Drawing Title COVER SHEET\n"
            "Consultant TDL Engineering Consulting Pty Ltd\n"
        ),
    )
    assert parsed.issuing_firm == "TDL Engineering Consulting Pty Ltd"
