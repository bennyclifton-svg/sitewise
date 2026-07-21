from app.sitewise.pmp_length import length_violations, pmp_word_count


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

## Project Summary

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

## Planning and Compliance

{compliance_words}
"""
    issues = length_violations(
        markdown,
        weights={"compliance-approvals": 0.1834},
        min_words=100,
        max_words=1800,
    )
    assert any(
        "Planning and Compliance is 623 words, budget ~330 - condense" in issue
        for issue in issues
    )


def test_length_violation_tells_model_which_section_to_deepen() -> None:
    markdown = "# PMP\n\n## Brief\n\nshort draft\n"
    issues = length_violations(
        markdown,
        weights={
            "snapshot": 0.1,
            "citation-key": 0.5,
            "scope-client-requirements": 0.3,
            "compliance-approvals": 0.2,
        },
        min_words=800,
        max_words=1800,
    )
    assert any(
        "minimum 800 - deepen Brief" in issue
        for issue in issues
    )
    assert not any("Citation key" in issue for issue in issues)
