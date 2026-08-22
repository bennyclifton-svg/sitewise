from app.sitewise.pmp_greenfield_brief import (
    ARCHITECT_PM_COMMON_MARKERS,
    build_greenfield_brief,
    greenfield_markers_missing,
    greenfield_quality_markers,
    greenfield_structure_violations,
)


def test_build_greenfield_brief_includes_archetype_overlay() -> None:
    brief = build_greenfield_brief(
        archetype="new-dwelling",
        state="NSW",
    )
    assert "BASIX" in brief
    assert "Class 1a" in brief
    assert "Section: Approvals and compliance" in brief


def test_build_greenfield_brief_evidence_grounded_omits_pre_engagement_defaults() -> None:
    brief = build_greenfield_brief(
        archetype="new-dwelling",
        state="NSW",
        draft_mode="evidence_grounded",
    )
    assert "Evidence-grounded content contract" in brief
    assert "neither brief filed yet" not in brief
    assert "Engagement instruments gap" not in brief
    assert "evidence-status labels" in brief.lower()
    assert "mobilisation document" in brief.lower()
    assert "post-engagement" in brief.lower()


def test_build_greenfield_brief_includes_due_diligence_checklist() -> None:
    brief = build_greenfield_brief(
        archetype="new-dwelling",
        state="NSW",
    )
    assert "Due diligence checklist" in brief
    assert "Dilapidation (adjoining)" in brief
    assert "03-design/01-due-diligence/" in brief


def test_build_greenfield_brief_keeps_programme_as_gantt_only() -> None:
    brief = build_greenfield_brief(
        archetype="new-dwelling",
        state="NSW",
    )
    assert "heading only" in brief
    assert "Program Gantt is the source of truth" in brief
    assert "Sub-milestone" not in brief
    assert "staging-strategy decision" in brief


def test_build_greenfield_brief_includes_owner_escalation_format() -> None:
    brief = build_greenfield_brief(
        archetype="new-dwelling",
        state="NSW",
    )
    assert "What this means for you" in brief
    assert "Section: Communications protocol" in brief


def test_build_greenfield_brief_includes_procurement_specificity() -> None:
    brief = build_greenfield_brief(
        archetype="new-dwelling",
        state="NSW",
    )
    assert "2–3 invited builders" in brief
    assert "05-procurement/" in brief


def test_build_greenfield_brief_includes_date_rule() -> None:
    brief = build_greenfield_brief(
        archetype="new-dwelling",
        state="NSW",
    )
    assert "Date rule" in brief
    assert "Never invent past calendar dates" in brief


def test_build_greenfield_brief_flags_non_nsw_state() -> None:
    brief = build_greenfield_brief(
        archetype="new-dwelling",
        state="VIC",
    )
    assert "VIC gap callout" in brief


def test_build_greenfield_brief_renovation_due_diligence() -> None:
    brief = build_greenfield_brief(
        archetype="renovation",
        state="NSW",
    )
    assert "Hazardous materials" in brief
    assert "Latent conditions" in brief or "latent" in brief.lower()


def test_greenfield_quality_markers_merges_architect_pm_common() -> None:
    markers = greenfield_quality_markers(archetype="new-dwelling")
    for common in ARCHITECT_PM_COMMON_MARKERS:
        assert common in markers


def test_build_greenfield_brief_adapts_due_diligence_for_vic() -> None:
    brief = build_greenfield_brief(
        archetype="renovation",
        state="VIC",
    )
    assert "not BASIX" in brief
    assert "BASIX alteration trigger (NSW" not in brief


def test_greenfield_structure_violations_detects_prose_risks() -> None:
    markdown = """
## Risks, decisions and next actions
### Risks:
1. Latent conditions
2. Tie-ins

## Internal audit layer
- **Facts**
- item
"""
    violations = greenfield_structure_violations(
        markdown,
        archetype="renovation",
    )
    assert any("risk register table" in issue for issue in violations)


def test_greenfield_structure_violations_enforces_simple_project_summary() -> None:
    markdown = """
## Project Summary

### Critical current position

| Project | Roof Repair |  |
| --- | --- | --- |
| Owner | Owner | — |
| Site | 10 Example Street | [1] |
"""

    violations = greenfield_structure_violations(markdown)

    assert any("Critical current position" in issue for issue in violations)
    assert any("ordered rows" in issue for issue in violations)


def test_greenfield_structure_violations_accepts_ordered_identity_summary() -> None:
    markdown = """
## Project Summary

| Project | Roof Repair |  |
| --- | --- | --- |
| Address | 10 Example Street | [1] |
| Owner | Alex Smith | [2] |
| Description | Repair the existing roof. | [3] |
"""

    assert greenfield_structure_violations(markdown) == []


def test_greenfield_markers_missing_detects_gaps() -> None:
    missing = greenfield_markers_missing(
        "# PMP\n\nGeneric content only.",
        archetype="new-dwelling",
    )
    assert "basix" in missing
    assert "what this means" in missing
    assert "invited" in missing
