from app.sitewise.pmp_length import (
    length_retry_instruction,
    length_violations,
    over_length_violations,
    pmp_word_count,
    under_length_violations,
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


def test_under_length_violations_exclude_over_length() -> None:
    markdown = "# PMP\n\n## Brief\n\nshort draft\n"
    weights = {"scope-client-requirements": 0.3, "risks": 0.19}
    under = under_length_violations(
        markdown, weights=weights, min_words=800, max_words=1800
    )
    over = over_length_violations(
        markdown, weights=weights, min_words=800, max_words=1800
    )
    assert under
    assert all("minimum" in issue for issue in under)
    assert over == []


def test_length_retry_instruction_names_band_budgets_and_forbids_register_restatement() -> None:
    instruction = length_retry_instruction(
        ["Draft is 786 words, minimum 1330 - deepen Risks."],
        weights={
            "snapshot": 0.05,
            "risks": 0.19,
            "compliance-approvals": 0.16,
            "procurement-delivery": 0.13,
            "programme": 0.08,
            "citation-key": 0.04,
        },
        target_words=1900,
        current_markdown="# PMP\n\n## Risks\n\nthree generic rows\n",
    )
    assert "minimum 1330" in instruction
    assert "Risks and mitigations (~361 words)" in instruction
    assert "Planning and Compliance (~304 words)" in instruction
    assert "Procurement and Delivery (~247 words)" in instruction
    assert "Programme (heading only; dates live on the Program Gantt)" in instruction
    assert "project-specific depth" in instruction
    assert "not restate the register" in instruction
    assert "# PMP" in instruction
    assert "three generic rows" in instruction


def test_ffe_schedule_register_is_not_length_condensed() -> None:
    rows = "\n".join(
        f"| Item {index} | Location | TBC | TBC | To be confirmed | Typical |"
        for index in range(20)
    )
    markdown = f"""# PMP

## FFE Schedule

Unified Finishes, Fixtures and Equipment register.

{rows}
"""
    issues = length_violations(
        markdown,
        weights={"ffe-schedule": 0.03, "scope-client-requirements": 0.14},
        min_words=100,
        max_words=1800,
    )
    assert not any("FFE Schedule" in issue for issue in issues)

