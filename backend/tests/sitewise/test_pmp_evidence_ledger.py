from pathlib import Path

from app.sitewise.accommodation_schedule import (
    parse_accommodation_schedule_tables,
    scheduled_area_total,
)
from app.sitewise.pmp_evidence_ledger import (
    build_document_digest,
    build_evidence_ledger,
    conflict_summary_violations,
    format_evidence_ledger,
)

_NEWTOWN_BRIEF = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "demo-corpus"
    / "newtown"
    / "01-brief"
    / "owners-project-brief.md"
)


def test_document_digest_retains_high_consequence_conclusion_after_old_cutoff() -> None:
    text = "DESIGN REPORT\n" + ("background material\n" * 700)
    text += "\nPerformance solution required for fire brigade access before CC."

    digest = build_document_digest(text, max_chars=2_000)

    assert len(digest) <= 2_000
    assert "Performance solution required for fire brigade access before CC." in digest


def test_document_digest_keeps_accommodation_schedule_table() -> None:
    preamble = "OWNER BRIEF\n" + ("context paragraph about the house and heritage.\n" * 80)
    table = """
## 4. Accommodation schedule

| Space | Level | Area | Characteristics | Status |
| --- | --- | --- | --- | --- |
| Kitchen (existing) | Ground | 12 m² | 1980s addition, to be removed | Demolished |
| Rear Sitting Room | Ground | 15 m² | 1980s addition, to be removed | Demolished |
| Kitchen | Ground | 16 m² | island bench | New |
| Covered Deck | External | 18 m² | off living | New |
"""
    text = preamble + table + ("\nmore notes about tapware and the construction budget.\n" * 40)
    assert len(text) > 4_500

    digest = build_document_digest(text, max_chars=4_500)
    rows = parse_accommodation_schedule_tables(digest)
    names = {row["space"] for row in rows}

    assert "| Space | Level | Area | Characteristics | Status |" in digest
    assert names >= {
        "Kitchen (existing)",
        "Rear Sitting Room",
        "Kitchen",
        "Covered Deck",
    }
    assert {row["space"] for row in rows if row["status"] == "Demolished"} == {
        "Kitchen (existing)",
        "Rear Sitting Room",
    }


def test_document_digest_keeps_schedule_of_accommodation_and_room_schedule() -> None:
    preamble = "BRIEF\n" + ("heritage and existing-house context.\n" * 90)
    table = """
## Schedule of accommodation

| Room | Level | Area | Status |
| --- | --- | --- | --- |
| Kitchen (existing) | Ground | 12 m² | Demolished |
| Kitchen | Ground | 16 m² | New |
"""
    later = """
## Room schedule

| Space | Level | Area | Status |
| --- | --- | --- | --- |
| Rear Sitting Room | Ground | 15 m² | Demolished |
"""
    text = preamble + table + ("\nbudget notes and tapware preferences.\n" * 40) + later
    assert len(text) > 4_500

    digest = build_document_digest(text, max_chars=4_500)
    rows = parse_accommodation_schedule_tables(digest)
    names = {row["space"] for row in rows}

    assert names >= {"Kitchen (existing)", "Kitchen", "Rear Sitting Room"}
    assert {row["space"] for row in rows if row["status"] == "Demolished"} >= {
        "Kitchen (existing)",
        "Rear Sitting Room",
    }


def test_document_digest_keeps_newtown_brief_schedule() -> None:
    text = _NEWTOWN_BRIEF.read_text(encoding="utf-8")
    digest = build_document_digest(text, max_chars=4_500)
    rows = parse_accommodation_schedule_tables(digest)
    demolished = {row["space"] for row in rows if row["status"] == "Demolished"}

    assert len(rows) == 26
    assert demolished == {
        "Kitchen (existing)",
        "Bathroom (existing)",
        "Laundry (existing)",
        "Rear Sitting Room",
        "Rear Verandah",
    }
    assert scheduled_area_total(rows) == 261.0


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
