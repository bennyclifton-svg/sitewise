"""Regression tests for the Kaposi failure: a builder quote uploaded as the only
project evidence must be considered by Create PMP, and the evidence map must
never claim documents that are not in the corpus."""

from app.sitewise.mobilisation_evidence import (
    GAP_ENGAGEMENT,
    build_evidence_map_rows,
    build_evidence_on_file_lines,
    extract_builder_quote_summary,
    extract_mobilisation_evidence_pack,
)
from app.sitewise.pmp_evidence_validation import evidence_map_claim_violations

KAPOSI_LIKE_QUOTE = """## Page 1

# PRICE ESTIMATE

|STAGE 1|SHED|EARTHWORKS|INSTALL 14,880.00 $|$ 14,880.00|
|STAGE 4| |INTERNEL WALLS|6,500.00 $|25,675.00|
|STAGE 5|FIT OFF|TILING|11,810.00 $|63,692.00 $| |

EXC GST

$                      182,417.00

PLUS 10% BUILDER MARGIN

$                    200,658.70

# NOTE:

This price does not included uforseen items and items below:

1. Asbestos removal

2. Exsiting floor leveling

3. Timber root

4. Termite damage
"""

QUOTE_REF = "project_evidence:04-projects/test/_inbox/Kaposi.pdf#chunk=abc"


def test_quote_summary_extracts_pricing_and_exclusions() -> None:
    summary = extract_builder_quote_summary(KAPOSI_LIKE_QUOTE, "Kaposi.pdf")

    assert summary is not None
    assert "Kaposi.pdf" in summary
    assert "$182,417.00 ex GST" in summary
    assert "$200,658.70" in summary
    assert "10% builder margin" in summary
    assert "staged trade breakdown" in summary
    assert "Asbestos removal" in summary
    assert "latent-condition risks" in summary


def test_quote_summary_rejects_non_quote_content() -> None:
    assert extract_builder_quote_summary("Meeting minutes for site walk.", "m.pdf") is None
    assert (
        extract_builder_quote_summary(
            "Letter of engagement for architect-PM services $148,500 ex GST", "e.md"
        )
        is None
    )


def test_pack_carries_quote_and_flags_missing_engagement() -> None:
    pack = extract_mobilisation_evidence_pack(
        [KAPOSI_LIKE_QUOTE], [QUOTE_REF], ["Kaposi.pdf"]
    )

    assert len(pack.builder_quotes) == 1
    assert "Kaposi.pdf" in pack.builder_quotes[0]
    assert pack.other_evidence == []
    assert pack.gaps[0] == GAP_ENGAGEMENT

    lines = build_evidence_on_file_lines(pack)
    assert any("Kaposi.pdf" in line for line in lines)
    assert not any("not yet indexed" in line for line in lines)


def test_pack_passes_through_unmatched_evidence() -> None:
    pack = extract_mobilisation_evidence_pack(
        ["Handwritten site note about a fence."], [QUOTE_REF], ["SiteNote.pdf"]
    )

    assert pack.builder_quotes == []
    assert len(pack.other_evidence) == 1
    assert "SiteNote.pdf" in pack.other_evidence[0]

    lines = build_evidence_on_file_lines(pack)
    assert any("SiteNote.pdf" in line for line in lines)


def test_evidence_map_never_claims_absent_documents() -> None:
    pack = extract_mobilisation_evidence_pack(
        [KAPOSI_LIKE_QUOTE], [QUOTE_REF], ["Kaposi.pdf"]
    )

    rows = {section: (status, ref) for section, status, ref in build_evidence_map_rows(pack)}
    assert rows["Appointment & fee"] == ("Not evidenced", "—")
    assert rows["Project understanding"] == ("Not evidenced", "—")
    assert rows["Builder pricing"][0] == "On file — unverified"


def test_validator_catches_fabricated_grounded_claims() -> None:
    markdown = (
        "## Evidence basis and document control\n\n"
        "**Evidence on file:**\n- Builder price estimate (Kaposi.pdf).\n\n"
        "| Section | Evidence status | Ref |\n"
        "| --- | --- | --- |\n"
        "| Appointment & fee | Grounded | engagement letter |\n"
        "| Project understanding | Partial | fee proposal |\n"
    )
    violations = evidence_map_claim_violations(markdown, [KAPOSI_LIKE_QUOTE])

    assert len(violations) == 2
    assert any("engagement letter" in violation for violation in violations)
    assert any("fee proposal" in violation for violation in violations)


def test_validator_accepts_claims_backed_by_corpus() -> None:
    markdown = (
        "## Evidence basis and document control\n\n"
        "| Section | Evidence status | Ref |\n"
        "| --- | --- | --- |\n"
        "| Appointment & fee | Grounded | engagement letter |\n"
        "| Construction budget | Not evidenced | — |\n"
    )
    corpus = ["Letter of engagement — architect-PM services, executed 16/05/2026."]
    assert evidence_map_claim_violations(markdown, corpus) == []
