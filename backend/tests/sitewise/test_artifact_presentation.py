from datetime import UTC, datetime

from app.projects.artefact_blocks import (
    materialize_block_identity,
    markdown_blocks,
    strip_block_markers,
)
from app.sitewise.artifact_presentation import (
    clean_issue_language,
    issue_export_markdown,
    prepare_issue_markdown,
)
from app.sitewise.taxonomy import DESIGN_LEAD_UNCONFIRMED_LABEL


NOW = datetime(2026, 8, 10, tzinfo=UTC)


def test_clean_issue_language_removes_review_shorthand_without_model_work() -> None:
    assert clean_issue_language("Confirm the programme before issue.") == (
        "State the programme before issue."
    )
    assert clean_issue_language("Date to be confirmed; fee TBC.") == (
        "Date not stated; fee —."
    )
    assert clean_issue_language(
        "Draft owner project brief - formal sign-off pending. "
        "Investigate and rectify the upper metal roof."
    ) == "Investigate and rectify the upper metal roof."
    assert clean_issue_language("Roof repair — User provided") == "Roof repair"
    assert clean_issue_language("Status: User provided current profile") == (
        "Status: current profile"
    )
    assert clean_issue_language("Uniting Church. Evidence on file.") == "Uniting Church."
    assert clean_issue_language("**Evidence on file:**") == ""
    assert clean_issue_language(
        "Evidence on file: engagement letter (executed 16/05/2026)."
    ) == "engagement letter (executed 16/05/2026)."


def test_clean_issue_language_preserves_design_lead_to_be_confirmed() -> None:
    sentence = (
        f"{DESIGN_LEAD_UNCONFIRMED_LABEL}. Record firm, fee, and appointment status only."
    )
    assert clean_issue_language(sentence) == sentence
    issued = prepare_issue_markdown(f"## Consultants\n\n{sentence}\n")
    assert DESIGN_LEAD_UNCONFIRMED_LABEL in issued
    assert "Design lead — not stated" not in issued


def test_prepare_issue_markdown_keeps_one_primary_copy_and_one_review_area() -> None:
    source = """# Project Management Plan

## Project overview

The brief confirms a warehouse project. [1]

| Field | Position |
| --- | --- |
| Tender date | TBC |
| Approval pathway | Confirm |

Scaffold status: review required.

## Actions and decisions

| Action | Owner |
| --- | --- |
| Issue master programme | Project manager |

## Citation key

[1] `brief.pdf`

## Internal audit layer

- **Facts**
  - The brief confirms a warehouse project. [1]
- **Assumptions**
  - Tender date is not evidenced.
- **Judgements**
  - Sequence the tender after design coordination.
- **Recommendations**
  - Issue master programme.
- **Register rows**
  - Issue master programme.
- **Workflow warnings**
  - Current programme is not on file.
"""

    prepared = prepare_issue_markdown(source)
    primary, qa = prepared.split("## Trace & QA", maxsplit=1)

    assert "TBC" not in primary
    assert "Confirm" not in primary
    assert "| Approval pathway | State |" in primary
    assert f"| Tender date | {chr(0x2014)} |" in primary
    assert primary.count("warehouse project") == 1
    assert primary.count("Issue master programme") == 1
    assert "Scaffold status" not in primary
    assert "Tender date" in qa
    assert "Assumptions: Tender date is not evidenced." in qa
    assert "Judgements: Sequence the tender after design coordination." in qa
    assert "Workflow Warnings: Current programme is not on file." in qa
    assert "Facts:" not in qa
    assert "Recommendations:" not in qa
    assert "Register Rows:" not in qa


def test_prepare_issue_markdown_is_idempotent_and_export_removes_review_area() -> None:
    source = """# Request for Tender

## Information issued and citations

| Document | Citation |
| --- | --- |
| Brief | [1] |

## Trace & QA

This review-only section is excluded from Word and PDF exports.

**Inputs to resolve**
- Tender close date

**Generation trace**
- Working basis: single-stage tender
"""

    prepared = prepare_issue_markdown(source)

    assert prepare_issue_markdown(prepared) == prepared
    exported = issue_export_markdown(prepared)
    assert "Trace & QA" not in exported
    assert "Tender close date" not in exported
    assert "Information issued and citations" in exported
    assert "[1]" in exported


def test_prepare_issue_markdown_preserves_materialized_block_identity() -> None:
    source = prepare_issue_markdown(
        """# Project Management Plan

## Project Summary

| Field | Project detail | Citation |
| --- | --- | --- |
| Project | Walsh 2 |  |
| Address | 42 Harvey Street, Petersham NSW | [1] |
| Owner | David and Emma Walsh | [1] |

## Brief

Coordinate the issued scope.

- Confirm the tender programme.
""",
        project_title="Walsh 2",
    )
    materialized = materialize_block_identity(
        source,
        actor_source="ai",
        generation_input_hash="context-v1",
        generation_version="v1",
        now=NOW,
    )
    identity_before = [
        (block.type, block.content, block.id)
        for block in markdown_blocks(materialized.markdown)
    ]

    prepared = prepare_issue_markdown(
        materialized.markdown,
        project_title="Walsh 2",
    )

    assert strip_block_markers(prepared) == source
    assert [
        (block.type, block.content, block.id) for block in markdown_blocks(prepared)
    ] == identity_before
    exported = issue_export_markdown(prepared, project_title="Walsh 2")
    assert "clerk:block" not in exported
    assert "42 Harvey Street, Petersham NSW" in exported


def test_prepare_issue_markdown_removes_pmp_governance_disclaimer() -> None:
    source = """# Project Management Plan

## Project Summary

| Project | Roof remedial works addressing water ingress near mechanical plant; residential aged care subclass — User provided | [2] |
| --- | --- | --- |

This is an owner side review and governance plan, not an instruction, statutory
submission, tender document or construction management plan.

## Brief

Repair the existing roof and associated stormwater interfaces.
"""

    prepared = prepare_issue_markdown(source)

    assert "owner side review and governance plan" not in prepared
    assert "construction management plan" not in prepared
    assert "Repair the existing roof" in prepared
    assert "owner side review and governance plan" not in issue_export_markdown(source)


def test_prepare_issue_markdown_removes_owner_brief_status_lead_in() -> None:
    source = """# Project Management Plan

## Brief

**Draft owner project brief — formal sign-off pending.** Investigate and rectify
the upper metal roof and associated stormwater drainage.
"""

    prepared = prepare_issue_markdown(source)
    exported = issue_export_markdown(source)

    assert "Draft owner project brief" not in prepared
    assert "formal sign-off pending" not in prepared
    assert "Investigate and rectify" in prepared
    assert "Draft owner project brief" not in exported
    assert "Investigate and rectify" in exported


def test_prepare_issue_markdown_removes_evidence_label_from_summary_detail() -> None:
    source = """# Project Management Plan

## Project Summary

| Field | Project detail | Citation |
| --- | --- | --- |
| Critical current position | Draft summary | — |
| Project | Roof remedial works addressing water ingress near mechanical plant; residential aged care subclass — User provided | [2] |
| Client / owner | Uniting Church of Australia. Proposal addressed to Cheyenne Shen. Evidence on file. | [1] |
| Site / asset | Uniting Abrina, 19-21 Victoria Street, Ashfield, New South Wales 2131. Investigate concerns the upper metal roof and associated stormwater drainage. | [1] |

## Citation key

[1] Proposal.pdf — on file
"""

    prepared = prepare_issue_markdown(source, project_title="Roof Repair")
    exported = issue_export_markdown(source, project_title="Roof Repair")

    assert "Proposal addressed to Cheyenne Shen." not in prepared
    assert "Evidence on file" not in prepared
    assert "User provided" not in prepared
    assert "User provided" not in exported
    assert "Critical current position" not in prepared
    assert "| Field | Project detail | Citation |" not in prepared
    assert "| Project | Roof Repair |  |" in prepared
    assert (
        "| Description | Roof remedial works addressing water ingress near mechanical "
        "plant; residential aged care subclass | [2] |"
    ) in prepared
    assert "| Owner | Uniting Church of Australia | [1] |" in prepared
    assert "| Address | Uniting Abrina, 19-21 Victoria Street, Ashfield, New South Wales 2131 | [1] |" in prepared
    assert prepared.index("| Project |") < prepared.index("| Address |")
    assert prepared.index("| Address |") < prepared.index("| Owner |")
    assert prepared.index("| Owner |") < prepared.index("| Description |")
    assert "Investigate concerns" not in prepared
    assert "| [1] |" in prepared
    assert "Evidence on file" not in exported
    assert "| Project | Roof Repair |  |" in exported
    assert "| Address | Uniting Abrina, 19-21 Victoria Street, Ashfield, New South Wales 2131 | [1] |" in exported


def test_prepare_issue_markdown_splits_combined_identity_and_strips_confirmed() -> None:
    source = """# Project Management Plan

## Project Summary

| Project / Owners / Site | Confirmed Walsh House / David and Emma Walsh / 42 Harvey Street, Petersham NSW | [1] |
| --- | --- | --- |

This paragraph summarises later sections and must not remain.

## Brief

Scope follows.
"""

    prepared = prepare_issue_markdown(source, project_title="Walsh 2")

    assert "| Project | Walsh 2 |  |" in prepared
    assert "| Address | 42 Harvey Street, Petersham NSW | [1] |" in prepared
    assert "| Owner | David and Emma Walsh | [1] |" in prepared
    assert "Confirmed" not in prepared
    assert "Project / Owners / Site" not in prepared
    assert "This paragraph summarises" not in prepared
    assert prepared.index("| Project |") < prepared.index("| Address |")
    assert prepared.index("| Address |") < prepared.index("| Owner |")
    assert "## Brief" in prepared


def test_clean_issue_language_strips_conflict_status_prose() -> None:
    assert clean_issue_language("Conflict") == ""
    assert clean_issue_language(
        "Sign brief seeks ground floor occupation if manageable. User setup says vacant. "
        "Conflict requiring resolution."
    ) == (
        "Sign brief seeks ground floor occupation if manageable. User setup says vacant."
    )


def test_prepare_issue_markdown_strips_coverage_register_and_citation_status_table() -> None:
    source = """# Project Management Plan

## Brief

Scope follows.

## Annexure A — Evidence coverage register

| Source | Category | Fact |
| --- | --- | --- |
| Brief.pdf | programme date | 1 November 2026 |

## Citation key

**Documents cited:**

[1] Brief.pdf — on file
[2] Engagement.pdf — on file

| Section | Evidence status | Citation |
| --- | --- | --- |
| Project Summary | Partial | [1] |
| Brief | Grounded | [1] |

Document control: draft v01.
"""

    prepared = prepare_issue_markdown(source, project_title="Walsh 2")

    assert "Evidence coverage register" not in prepared
    assert "1 November 2026" not in prepared
    assert "| Section | Evidence status | Citation |" not in prepared
    assert "Project Summary | Partial" not in prepared
    assert "**Documents cited:**" not in prepared
    assert "- [1] Brief.pdf — on file" in prepared
    assert "- [2] Engagement.pdf — on file" in prepared
    assert "Document control: draft v01." in prepared


def test_prepare_issue_markdown_blanks_consultants_fee_not_evidenced() -> None:
    source = """# Project Management Plan

## Consultants

| Discipline | Firm | Scope / services | Fee | Status | Citation |
| --- | --- | --- | --- | --- | --- |
| Structural engineer | — | Assumption — services not yet appointed | Not evidenced | Not evidenced | — |
| Surveyor | Acme Survey | Contour and detail survey | $4,200 | Partial | [1] |
"""

    prepared = prepare_issue_markdown(source)

    assert "Scope / services" not in prepared
    assert "services not yet appointed" not in prepared
    assert "| Structural engineer | — |  | Not evidenced | — |" in prepared
    assert "| Surveyor | Acme Survey | $4,200 | Partial | [1] |" in prepared
