from app.sitewise.pmp_claim_support import (
    citation_claim_support_violations,
    exclusion_citation_violations,
)


def test_claim_support_rejects_builder_claim_cited_to_geotechnical_report() -> None:
    markdown = """
## Procurement

Invite two experienced commercial fit-out builders to tender. [1]

## Citation key

[1] Geotech Investigation Report.pdf — current
"""

    violations = citation_claim_support_violations(
        markdown,
        source_texts=[
            "Our fee proposal covered two boreholes and one test pit. "
            "The investigation informs footing and pavement design."
        ],
        source_labels=["Geotech Investigation Report.pdf"],
    )

    assert violations
    assert "two experienced commercial fit-out builders" in violations[0]
    assert "Geotech Investigation Report.pdf" in violations[0]


def test_claim_support_accepts_faithful_project_claim() -> None:
    markdown = """
## Brief

The extension forms a secure standalone tenancy with separately metered services. [1]

## Citation key

[1] Industrial Design Brief.pdf — current
"""

    assert citation_claim_support_violations(
        markdown,
        source_texts=[
            "Extension to the existing warehouse to form a secure, standalone "
            "tenancy with separately operable and metered services."
        ],
        source_labels=["Industrial Design Brief.pdf"],
    ) == []


def test_claim_support_skips_assumption_and_user_provided_lines() -> None:
    markdown = """
## Programme and staging regime

Working regime: Stage 1 concept/schematic design to DA submission; Stage 2 design development; Stage 3 construction documentation and delivery. This is a PMP baseline **Assumption**. [1]

## Cost, programme and procurement posture

**User provided:** traditional lump-sum procurement. Ironbark's proposal is a fixed-price tender based on Quoin tender set QUA-KAV-T01–T18. [1]

## Citation key

- [1] Geotech Investigation Report.pdf — current
"""

    assert citation_claim_support_violations(
        markdown,
        source_texts=[
            "Our fee proposal covered two boreholes and one test pit. "
            "The investigation informs footing and pavement design."
        ],
        source_labels=["Geotech Investigation Report.pdf"],
    ) == []


def test_claim_support_skips_action_register_rows() -> None:
    markdown = """
## Actions and decisions

| ID | Action | Owner | Status |
| --- | --- | --- | --- |
| A01 | Verify DA/CC, certifier and conditions. | Architect-PM | Open | [1] |
| R01 | Approval/certifier evidence absent; stop site mobilisation. | Architect-PM | Open | [1] |

## Citation key

- [1] Geotech Investigation Report.pdf — current
"""

    assert citation_claim_support_violations(
        markdown,
        source_texts=[
            "Our fee proposal covered two boreholes and one test pit."
        ],
        source_labels=["Geotech Investigation Report.pdf"],
    ) == []


def test_claim_support_allows_mispointed_citation_when_corpus_supports_claim() -> None:
    markdown = """
## Cost

The current builder proposal is a fixed contract sum of $1,234,000 ex GST and includes separate provisional allowances of $30,000 ex GST for rock removal and $22,000 ex GST for pool. [1]

## Citation key

- [1] Geotech Investigation Report.pdf — current
"""

    assert citation_claim_support_violations(
        markdown,
        source_texts=[
            "Boreholes and test pits only. No builder pricing.",
            "Fixed contract sum excluding GST $1,234,000.00. "
            "Includes a $30,000.00 ex-GST provisional allowance for rock removal "
            "and a $22,000.00 ex-GST provisional allowance for pool-interface drainage.",
        ],
        source_labels=[
            "Geotech Investigation Report.pdf",
            "05-building-proposal-ironbark-main-works.md",
        ],
    ) == []


def test_confirmed_exclusion_requires_citation_but_unverified_gap_does_not() -> None:
    markdown = """
## Brief

### Exclusions

| Item | Position | Citation |
| --- | --- | --- |
| Tenant racking | Confirmed exclusion | — |
| Solar PV | Not evidenced; verify with client | — |
| Loose furniture | Assumption: items are excluded unless later instructed | — |
"""

    violations = exclusion_citation_violations(markdown)

    assert len(violations) == 2
    assert "Tenant racking" in violations[0]
    assert "Loose furniture" in violations[1]
