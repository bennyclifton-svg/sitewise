from app.sitewise.pmp_sources import (
    required_platform_paths,
    required_section_headings,
    seed_consulted_includes_required,
)


def test_required_platform_paths_for_renovation_architect_pm() -> None:
    paths = required_platform_paths(archetype="renovation", user_role="architect-pm")
    assert paths[0] == "docs/clerk-brief.md"
    assert "seed/renovation-guide.md" in paths
    assert "seed/role-architect-pm.md" in paths
    assert "seed/setup-and-commission-guide.md" in paths
    assert "seed/procurement-quoting-guide.md" in paths


def test_required_section_headings_vary_by_role() -> None:
    architect_sections = required_section_headings("architect-pm")
    builder_sections = required_section_headings("builder")
    assert "Two-brief discipline" in architect_sections
    assert "Two-brief discipline" not in builder_sections
    assert "Statutory instruments and insurance" in builder_sections


def test_seed_consulted_includes_required_detects_missing() -> None:
    missing = seed_consulted_includes_required(
        ["seed/role-architect-pm.md"],
        archetype="renovation",
        user_role="architect-pm",
    )
    assert "seed/renovation-guide.md" in missing
    assert "seed/setup-and-commission-guide.md" in missing
