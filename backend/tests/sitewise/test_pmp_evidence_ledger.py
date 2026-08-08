from app.sitewise.pmp_evidence_ledger import (
    build_document_digest,
    build_evidence_ledger,
    conflict_summary_violations,
    format_evidence_ledger,
)


def test_document_digest_retains_high_consequence_conclusion_after_old_cutoff() -> None:
    text = "DESIGN REPORT\n" + ("background material\n" * 700)
    text += "\nPerformance solution required for fire brigade access before CC."

    digest = build_document_digest(text, max_chars=2_000)

    assert len(digest) <= 2_000
    assert "Performance solution required for fire brigade access before CC." in digest


def test_ledger_surfaces_unit_and_gfa_conflicts_at_the_front() -> None:
    texts = [
        "Design brief for Unit 10. The proposed GFA is 4,200 m2.",
        "Development Application for Unit 7A. Gross floor area: 4,450 m2.",
    ]
    labels = ["Design Brief.pdf", "DA Report.pdf"]

    rendered = format_evidence_ledger(build_evidence_ledger(texts, labels))

    assert "Project/unit identity conflict" in rendered
    assert "Unit 10" in rendered
    assert "Unit 7A" in rendered
    assert "Total project area conflict" in rendered
    assert "4200 m2" in rendered
    assert "4450 m2" in rendered


def test_conflicts_must_appear_in_draft_body() -> None:
    ledger = build_evidence_ledger(
        [
            "Design brief for Unit 10. The proposed GFA is 4,200 m2.",
            "Development Application for Unit 7A. Gross floor area: 4,450 m2.",
        ],
        ["Design Brief.pdf", "DA Report.pdf"],
    )

    assert conflict_summary_violations(
        "## Project Summary\n\nCurrent documents refer to Unit 10 only.",
        ledger,
    )
    assert conflict_summary_violations(
        "## Programme\n\n"
        "| Occupation / staging | Brief cites Unit 10; DA cites Unit 7A. "
        "Areas 4,200 m2 vs 4,450 m2. | [1] |\n",
        ledger,
    ) == []
