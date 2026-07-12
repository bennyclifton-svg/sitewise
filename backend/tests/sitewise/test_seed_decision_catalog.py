from __future__ import annotations

from pathlib import Path

from app.sitewise.seed_decision_catalog import (
    SeedDecisionSpec,
    extract_decision_catalogs,
    filter_decisions_for_project,
    load_decision_catalogs_from_seed_text,
)

SAMPLE_SEED = """\
---
tier: topic
applies_to_archetypes: [new-dwelling, renovation]
applies_to_classes: [residential]
---

# Finishes

Some prose about timber floors.

```decision-catalog
- id: flooring-finish
  section: Brief and scope
  label: Primary flooring finish
  applies_to:
    archetypes: [new-dwelling, renovation]
    classes: [residential]
  options:
    - { value: timber, label: Timber flooring }
    - { value: engineered, label: Engineered timber }
    - { value: tile, label: Tile }
  default_hint: engineered
- id: kitchen-benchtop
  section: Brief and scope
  label: Kitchen benchtop
  applies_to:
    archetypes: [new-dwelling]
    classes: [residential]
  options:
    - { value: laminate, label: Laminate }
    - { value: stone, label: Engineered stone }
    - { value: natural_stone, label: Natural stone }
  default_hint: stone
```

More prose.
"""


def test_extract_decision_catalogs_parses_yaml_fence() -> None:
    specs = extract_decision_catalogs(SAMPLE_SEED)
    assert len(specs) == 2
    flooring = specs[0]
    assert flooring.id == "flooring-finish"
    assert flooring.label == "Primary flooring finish"
    assert flooring.section == "Brief and scope"
    assert flooring.default_hint == "engineered"
    assert [opt["value"] for opt in flooring.options] == [
        "timber",
        "engineered",
        "tile",
    ]


def test_filter_decisions_for_project_by_archetype_and_class() -> None:
    specs = extract_decision_catalogs(SAMPLE_SEED)
    filtered = filter_decisions_for_project(
        specs,
        archetype="renovation",
        building_class="residential",
    )
    assert [spec.id for spec in filtered] == ["flooring-finish"]


def test_filter_includes_new_dwelling_kitchen() -> None:
    specs = extract_decision_catalogs(SAMPLE_SEED)
    filtered = filter_decisions_for_project(
        specs,
        archetype="new-dwelling",
        building_class="residential",
    )
    assert {spec.id for spec in filtered} == {"flooring-finish", "kitchen-benchtop"}


def test_malformed_catalog_skipped() -> None:
    markdown = "```decision-catalog\n{not: [valid\n```"
    assert extract_decision_catalogs(markdown) == []


def test_incomplete_entries_skipped() -> None:
    markdown = """\
```decision-catalog
- id: missing-options
  label: Broken
- id: ok
  label: Ok
  section: Scope
  options:
    - { value: a, label: A }
```
"""
    specs = extract_decision_catalogs(markdown)
    assert [spec.id for spec in specs] == ["ok"]


def test_load_from_seed_text_matches_extract() -> None:
    specs = load_decision_catalogs_from_seed_text(SAMPLE_SEED)
    assert isinstance(specs[0], SeedDecisionSpec)
    assert len(specs) == 2


def test_real_seeds_provide_sparse_brief_catalog() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    seed_dir = repo_root / "data" / "seed"
    specs: list[SeedDecisionSpec] = []
    for name in ("finishes-residential.md", "new-dwelling-guide.md"):
        specs.extend(extract_decision_catalogs((seed_dir / name).read_text(encoding="utf-8")))
    filtered = filter_decisions_for_project(
        specs,
        archetype="new-dwelling",
        building_class="residential",
    )
    ids = {spec.id for spec in filtered}
    assert len(ids) >= 8
    assert "flooring-finish" in ids
    assert "kitchen-benchtop" in ids
    assert "dwelling-storeys" in ids
    assert "external-cladding" in ids
