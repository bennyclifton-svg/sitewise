import pytest

from ingest.classify import score_filename

CASES = [
    ("Cost Plan.pdf", "commercial"),
    ("Business Plan.pdf", None),  # deliberately ambiguous
    ("Payment Plan.pdf", "commercial"),
    ("A-101 Rev C.pdf", "drawing"),
    ("A-102 Ground Floor Plan.pdf", "drawing"),
    ("S203 Rev B.pdf", "drawing"),
    ("Structural Specification.pdf", "specification"),
    ("Heritage Impact Statement.pdf", "report"),
    ("Notice of Determination.pdf", "certificate"),
    ("Invoice 0043.pdf", "commercial"),
    ("Variation 017.pdf", "commercial"),
    ("Scan_20260815_001.pdf", None),  # no signal at all
    ("IMG_4471.pdf", None),
    ("Master Programme Rev 4.xlsx", "schedule"),
    ("Waverley LEP 2012.pdf", "statutory_instrument"),
    ("Structural Specification Plan.pdf", "specification"),
    ("Council RFI response.pdf", "correspondence"),
    ("Tender - Builder B.pdf", "commercial"),
    ("Builder B final.pdf", None),
    ("Inner-West-LEP-2022.pdf", "statutory_instrument"),
    ("Inner West DCP 2022.pdf", "statutory_instrument"),
    ("Heritage DCP assessment report.pdf", "report"),
    ("H-102 [D].pdf", "drawing"),
    ("C-001-civil-notes-legend-and-abbreviations.md", "drawing"),
    ("M02 - Mechanical Design & Spec - 02 Flexible [C].pdf", "drawing"),
    ("OVERALL SITE PLAN WITH SEWER ZOI [02].pdf", "drawing"),
    ("Fee Proposal.pdf", "commercial"),
    ("Tax Invoice August.pdf", "commercial"),
    ("Progress Claim 03.pdf", "commercial"),
    ("Gantt Lookahead.xlsx", "schedule"),
    ("Site Instruction letter.pdf", "correspondence"),
    ("Contract of Sale.pdf", "contract"),
    ("Deed of Novation.pdf", "contract"),
    ("BASIX Certificate.pdf", "certificate"),
    ("Fire Engineering Report.pdf", "report"),
    ("minutes of meeting.pdf", "correspondence"),
    ("EOI response.pdf", "commercial"),
    ("RFT Volume 1.pdf", "commercial"),
    ("Construction Programme.pdf", "schedule"),
    ("Acoustic Report.pdf", "report"),
    ("Cost Plan Rev B.xlsx", "commercial"),
    ("Specification.docx", "specification"),
    ("Elevation North.pdf", "drawing"),
    ("Section AA.pdf", "drawing"),
    ("Detail 12.pdf", "drawing"),
    ("unknown-scan.pdf", None),
]


@pytest.mark.parametrize("filename,expected", CASES)
def test_filename_scoring(filename: str, expected: str | None) -> None:
    assert score_filename(filename).winner == expected


def test_filename_matrix_has_at_least_40_cases() -> None:
    assert len(CASES) >= 40
