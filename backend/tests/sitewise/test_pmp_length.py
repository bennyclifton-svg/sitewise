from app.sitewise.pmp_length import (
    condense_primary_markdown_to_word_band,
    length_violations,
    pmp_word_count,
)


def test_pmp_word_count_counts_selected_decision_label_only() -> None:
    markdown = """# PMP

## Actions and decisions

```pmp-decision
{
  "selected": "a",
  "options": [
    {"id": "a", "label": "Proceed with tender"},
    {"id": "b", "label": "This unselected option has many extra words"}
  ]
}
```
"""
    restamped = markdown.replace('"selected": "a"', '"selected": "a"')
    assert pmp_word_count(markdown) == pmp_word_count(restamped)
    assert pmp_word_count(markdown) == 7


def test_pmp_word_count_excludes_annexure_and_collapsed_details() -> None:
    markdown = """# PMP

## Project snapshot

Visible table text.

<details>
<summary>Annexure</summary>
Hidden words should not count.
</details>

## Annexure A

Hidden annexure words should not count.
"""
    assert pmp_word_count(markdown) == 6


def test_length_violation_names_oversized_section_budget() -> None:
    compliance_words = " ".join(["compliance"] * 620)
    markdown = f"""# PMP

## Compliance and approvals

{compliance_words}
"""
    issues = length_violations(
        markdown,
        weights={"compliance-approvals": 0.1834},
        min_words=100,
        max_words=1800,
    )
    assert any(
        "Compliance and approvals is 623 words, budget ~330 - condense" in issue
        for issue in issues
    )


def test_length_violation_tells_model_which_section_to_deepen() -> None:
    markdown = "# PMP\n\n## Scope and client requirements\n\nshort draft\n"
    issues = length_violations(
        markdown,
        weights={
            "snapshot": 0.1,
            "scope-client-requirements": 0.3,
            "compliance-approvals": 0.2,
        },
        min_words=800,
        max_words=1800,
    )
    assert any(
        "minimum 800 - deepen Scope and client requirements" in issue
        for issue in issues
    )


def test_condense_primary_markdown_to_word_band_shrinks_tables_and_lists() -> None:
    long_cell = (
        "Owner and architect to confirm detailed tenancy coordination requirements, "
        "landlord approvals, programme dependencies, consultant responsibilities, "
        "budget allowances, and evidence status before issue for construction"
    )
    rows = "\n".join(f"| Action {index} | {long_cell} |" for index in range(1, 50))
    bullets = "\n".join(
        f"- {long_cell} and record the decision in the next PMP issue."
        for _ in range(20)
    )
    markdown = f"""# PMP

## Project snapshot

User provided project setup summary.

## Actions and decisions

| Action | Next step |
| --- | --- |
{rows}

{bullets}
"""

    assert pmp_word_count(markdown) > 1800 * 1.05

    compacted = condense_primary_markdown_to_word_band(
        markdown,
        weights={"snapshot": 0.1, "actions-decisions": 0.05},
        min_words=800,
        max_words=1800,
    )

    assert pmp_word_count(compacted) <= 1800 * 1.05
    assert "| Action | Next step |" in compacted
    assert "## Actions and decisions" in compacted
