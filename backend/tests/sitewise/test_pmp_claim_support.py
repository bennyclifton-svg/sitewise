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
