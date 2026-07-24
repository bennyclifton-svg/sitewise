from app.sitewise.pmp_greenfield_brief import (
    ARCHITECT_PM_COMMON_MARKERS,
    build_greenfield_brief,
    greenfield_markers_missing,
    greenfield_quality_markers,
    greenfield_structure_violations,
    programme_submilestone_table,
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
    assert "Evidence on file:" in brief
    assert "post-engagement" in brief.lower()


def test_build_greenfield_brief_includes_due_diligence_checklist() -> None:
    brief = build_greenfield_brief(
        archetype="new-dwelling",
        state="NSW",
    )
    assert "Due diligence checklist" in brief
    assert "Dilapidation (adjoining)" in brief
    assert "03-design/01-due-diligence/" in brief


def test_build_greenfield_brief_includes_programme_submilestones() -> None:
    brief = build_greenfield_brief(
        archetype="new-dwelling",
        state="NSW",
    )
    assert "Sub-milestone" in brief
    assert "Slab / substructure" in brief
    assert "Lockup" in brief
    assert "Defects liability period (DLP)" in brief


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


def test_programme_submilestone_table_is_single_shape() -> None:
    table = programme_submilestone_table().lower()
    assert "| builder procured / contract executed |" in table


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


def test_greenfield_markers_missing_detects_gaps() -> None:
    missing = greenfield_markers_missing(
        "# PMP\n\nGeneric content only.",
        archetype="new-dwelling",
    )
    assert "basix" in missing
    assert "what this means" in missing
    assert "slab" in missing
