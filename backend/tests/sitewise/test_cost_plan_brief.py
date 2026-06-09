from app.sitewise.cost_plan_brief import build_greenfield_brief


def test_build_greenfield_brief_evidence_grounded_is_compact() -> None:
    platform = build_greenfield_brief(
        archetype="new-dwelling",
        user_role="architect-pm",
        state="NSW",
        draft_mode="platform_seeded",
    )
    evidence = build_greenfield_brief(
        archetype="new-dwelling",
        user_role="architect-pm",
        state="NSW",
        draft_mode="evidence_grounded",
    )

    assert len(evidence) < len(platform) * 0.6
    assert "Evidence-grounded content contract" in evidence
    assert "### Section: GST basis" not in evidence
    assert "Greenfield content contract" in platform
