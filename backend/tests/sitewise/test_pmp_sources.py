from app.sitewise.pmp_sources import (
    required_platform_paths,
    required_section_headings,
    seed_consulted_includes_required,
)


def test_required_platform_paths_for_renovation() -> None:
    paths = required_platform_paths(archetype="renovation")
    assert paths[0] == "docs/clerk-brief.md"
    assert "seed/renovation-guide.md" in paths
    assert "seed/role-architect-pm.md" in paths
    assert "seed/setup-and-commission-guide.md" in paths
    assert "seed/procurement-quoting-guide.md" in paths


def test_required_section_headings_are_single_shape() -> None:
    sections = required_section_headings()
    assert "Two-brief discipline" in sections
    assert "Architect-PM role and appointment" in sections


def test_seed_consulted_includes_required_detects_missing() -> None:
    missing = seed_consulted_includes_required(
        ["seed/role-architect-pm.md"],
        archetype="renovation",
    )
    assert "seed/renovation-guide.md" in missing
    assert "seed/setup-and-commission-guide.md" in missing
