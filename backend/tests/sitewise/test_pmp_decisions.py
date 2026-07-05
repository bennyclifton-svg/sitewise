from app.sitewise.pmp_decisions import (
    decision_violations,
    extract_decisions,
    missing_locked_decisions,
    render_decisions_static,
    restamp_decisions,
)
from app.sitewise.pmp_evidence_validation import sanitize_evidence_grounded_markdown

SAMPLE_BLOCK = """\
Before text stays.

```pmp-decision
{
  "id": "procurement-route",
  "section": "Procurement posture",
  "label": "Procurement route",
  "options": [
    {"value": "traditional", "label": "Traditional (Lump Sum)"},
    {"value": "design_construct", "label": "Design & Construct"}
  ],
  "selected": "traditional",
  "source": "agent",
  "rationale": "Documented single-stage design suits lump sum."
}
```

After text stays.
"""


def test_extract_decisions_round_trip() -> None:
    decisions = extract_decisions(SAMPLE_BLOCK)
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.id == "procurement-route"
    assert decision.selected == "traditional"
    assert decision.source == "agent"
    assert len(decision.options) == 2


def test_restamp_preserves_surrounding_markdown() -> None:
    restamped = restamp_decisions(
        SAMPLE_BLOCK,
        {"procurement-route": "design_construct"},
    )
    assert restamped.startswith("Before text stays.")
    assert restamped.endswith("After text stays.\n")
    assert '"selected": "design_construct"' in restamped
    assert '"source": "user"' in restamped
    assert "Before text stays." in restamped
    assert "After text stays." in restamped


def test_restamp_records_evidence_conflict() -> None:
    restamped = restamp_decisions(
        SAMPLE_BLOCK.replace('"selected": "traditional"', '"selected": "design_construct"'),
        {"procurement-route": "traditional"},
    )
    assert '"evidence_conflict": true' in restamped
    assert '"agent_suggestion": "design_construct"' in restamped


def test_malformed_block_reported_not_crashed() -> None:
    markdown = "```pmp-decision\n{not json}\n```"
    violations = decision_violations(markdown)
    assert violations
    assert extract_decisions(markdown) == []


def test_duplicate_id_violation() -> None:
    markdown = SAMPLE_BLOCK + "\n" + SAMPLE_BLOCK
    violations = decision_violations(markdown)
    assert any("Duplicate decision id" in item for item in violations)


def test_missing_locked_decisions() -> None:
    missing = missing_locked_decisions(SAMPLE_BLOCK, {"procurement-route", "contract-form"})
    assert missing == ["contract-form"]


def test_render_decisions_static() -> None:
    rendered = render_decisions_static(SAMPLE_BLOCK)
    assert "**Procurement route:** Traditional (Lump Sum)" in rendered
    assert "```pmp-decision" not in rendered


def test_sanitize_leaves_decision_fences_intact() -> None:
    markdown = SAMPLE_BLOCK.replace(
        "After text stays.",
        "## Evidence basis and document control\n\nStatus: draft.",
    )
    refs = ["engagement letter"]
    cleaned = sanitize_evidence_grounded_markdown(markdown, refs)
    assert "```pmp-decision" in cleaned
    assert extract_decisions(cleaned)[0].id == "procurement-route"
