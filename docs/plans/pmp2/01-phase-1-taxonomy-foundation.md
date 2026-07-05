# PMP 2.0 — Phase 1: Taxonomy Foundation (backend)

> **For Claude (implementing agent):** REQUIRED SUB-SKILL: Use superpowers:executing-plans to work this phase task-by-task.
> **Required reading first:** [../2026-07-05-pmp2-live-interactive-pmp.md](../2026-07-05-pmp2-live-interactive-pmp.md) — goal, current-state file map, design decisions D1–D13, test commands, recorded baseline test failures. Source spec: `docs/pmp2.0/pmp2.md` (its tables are the data to transcribe).
> **Depends on:** nothing — this phase lands first. **Blocks:** Phases 2, 3, 4, 5.

**Outcome:** Class/type/subclass/scale/complexity/risk-flag taxonomy exists as validated config + DB columns + API, with the emphasis profiles that later drive adaptive PMP depth (D7). Legacy archetype handling is compatibility/test-fixture support only; do not create a product migration path for old projects. No generation behaviour changes yet.

## Task 1.1: Taxonomy config files + loader

**Files:**
- Create: `data/taxonomy/building-classes.json`
- Create: `data/taxonomy/complexity-dimensions.json`
- Create: `data/taxonomy/risk-flags.json`
- Create: `data/taxonomy/work-scopes.json`
- Create: `data/taxonomy/emphasis-profiles.json`
- Create: `backend/app/sitewise/taxonomy.py`
- Test: `backend/tests/sitewise/test_taxonomy.py`

**Step 1: Write failing tests** — load catalog, validate structure, reject bad combos:

```python
"""Taxonomy config is the single source of truth for class/type/subclass/
scale/complexity options. These tests pin the contract the frontend and
seed selection depend on."""
from app.sitewise.taxonomy import (
    building_classes, work_types, subclasses_for, scale_fields_for,
    complexity_dimensions_for, risk_flag_definitions, validate_project_taxonomy,
)

def test_building_classes_complete():
    assert [c.value for c in building_classes()] == [
        "residential", "commercial", "industrial",
        "institution", "mixed", "infrastructure",
    ]

def test_work_types_complete():
    assert [w.value for w in work_types()] == [
        "new", "refurb", "extend", "remediation", "advisory"
    ]

def test_every_class_has_subclasses_with_other():
    for cls in building_classes():
        subs = subclasses_for(cls.value)
        assert len(subs) >= 3
        assert subs[-1].value == "other"

def test_mixed_class_allows_multiple_subclasses():
    assert next(c for c in building_classes() if c.value == "mixed").multi_subclass

def test_scale_fields_exist_for_every_subclass():
    for cls in building_classes():
        for sub in subclasses_for(cls.value):
            if sub.value == "other":
                continue
            assert scale_fields_for(cls.value, sub.value), f"{cls.value}/{sub.value}"

def test_universal_complexity_dimensions_present_for_all_classes():
    for cls in building_classes():
        keys = {d.key for d in complexity_dimensions_for(cls.value)}
        assert {"contamination_level", "access_constraints",
                "operational_constraints", "procurement_route",
                "stakeholder_complexity", "environmental_sensitivity"} <= keys

def test_validate_rejects_unknown_combo():
    errors = validate_project_taxonomy(
        building_class="residential", work_type="teleportation", subclasses=["house"])
    assert errors

def test_validate_accepts_minimal_brief_combo():
    assert validate_project_taxonomy(
        building_class="residential", work_type="new", subclasses=["house"]) == []

def test_emphasis_weights_normalised_for_every_combo():
    from app.sitewise.taxonomy import PMP_CORE_SECTIONS, section_weights_for
    for cls in building_classes():
        for wt in work_types():
            weights = section_weights_for(
                building_class=cls.value, work_type=wt.value,
                work_scope=[], risk_flags=[])
            assert abs(sum(weights.values()) - 1.0) < 1e-6
            assert set(weights) == set(PMP_CORE_SECTIONS)

def test_fire_services_scope_boosts_compliance_weight():
    from app.sitewise.taxonomy import section_weights_for
    base = section_weights_for(building_class="commercial", work_type="refurb",
                               work_scope=[], risk_flags=[])
    boosted = section_weights_for(building_class="commercial", work_type="refurb",
                                  work_scope=["fire_services"], risk_flags=[])
    assert boosted["compliance-approvals"] > base["compliance-approvals"]

def test_residential_new_scope_outweighs_compliance():
    from app.sitewise.taxonomy import section_weights_for
    weights = section_weights_for(building_class="residential", work_type="new",
                                  work_scope=[], risk_flags=[])
    assert weights["scope-client-requirements"] > weights["compliance-approvals"]
```

**Step 2: Run** `cd backend && uv run pytest tests/sitewise/test_taxonomy.py -v` — expect import errors (module missing).

**Step 3: Author the config files.** Schema for `building-classes.json` (one complete class shown; transcribe all six from pmp2.md §3.2 Column 1/Column 2 tables, including the industrial additions in pmp2.md §2.3 — heavy_manufacturing, food_processing, pharmaceutical_gmp, cleanroom, battery_manufacturing, waste_to_energy):

```json
{
  "building_classes": [
    {
      "value": "residential",
      "label": "Residential",
      "multi_subclass": false,
      "work_types": ["new", "refurb", "extend", "remediation", "advisory"],
      "subclasses": [
        {
          "value": "house",
          "label": "House (Class 1a)",
          "ncc_class": "1a",
          "scale_fields": [
            {"key": "gfa_sqm", "label": "GFA (m²)", "type": "number", "typical": "50-800"},
            {"key": "storeys", "label": "Storeys", "type": "integer", "typical": "1-3"},
            {"key": "bedrooms", "label": "Bedrooms", "type": "integer", "typical": "2-6"},
            {"key": "garage_spaces", "label": "Garage Spaces", "type": "integer"}
          ]
        }
      ]
    }
  ]
}
```

`complexity-dimensions.json`: the six universal dimensions verbatim from pmp2.md (contamination_level … environmental_sensitivity) under `"universal"`, plus per-class/per-subclass overlays (e.g. cleanroom `iso_class`, agricultural block if kept — reviewer note: the spec's `agricultural` block has no matching building class; fold its dimensions into industrial/infrastructure where sensible and note the mapping in the file's `_comment`). Each option keeps its label including cost-uplift hints ("+10-20%").

`risk-flags.json`: the ten `riskDefinitions` from pmp2.md (high_security … flood_overlay) plus derivation rules:

```json
{
  "definitions": { "remote_site": {"severity": "warning", "title": "Very Remote Location", "description": "…"} },
  "derivations": [
    {"flag": "remote_site", "when": {"dimension": "access_constraints", "values": ["remote"]}},
    {"flag": "live_operations", "when": {"dimension": "operational_constraints", "values": ["live_environment", "24_7_occupied"]}}
  ]
}
```

`work-scopes.json`: transcribe pmp2.md §5.1 (`new`) and §5.2 (`advisory`) verbatim (categories → items → consultants → riskFlag/complexityPoints). Existing refurb/extend/remediation scopes: if none exist in the repo today (they don't — verify), author minimal parallel structures using the same category style; keep them shorter, flag for later enrichment.

`emphasis-profiles.json` (D7 — drives adaptive section depth within the 2–4 page band). The core section ids are the contract between this file, the section skeleton, and the length validator (both in [04-phase-4-adaptive-pmp.md](04-phase-4-adaptive-pmp.md)):

```json
{
  "sections": [
    "snapshot", "scope-client-requirements", "compliance-approvals",
    "programme", "cost-budget", "procurement-delivery",
    "risks", "actions-decisions"
  ],
  "base_weights": {
    "residential|new":   {"snapshot": 0.10, "scope-client-requirements": 0.30, "compliance-approvals": 0.10, "programme": 0.12, "cost-budget": 0.12, "procurement-delivery": 0.10, "risks": 0.10, "actions-decisions": 0.06},
    "commercial|refurb": {"snapshot": 0.10, "scope-client-requirements": 0.15, "compliance-approvals": 0.25, "programme": 0.10, "cost-budget": 0.10, "procurement-delivery": 0.12, "risks": 0.12, "actions-decisions": 0.06},
    "default":           {"snapshot": 0.10, "scope-client-requirements": 0.20, "compliance-approvals": 0.15, "programme": 0.12, "cost-budget": 0.12, "procurement-delivery": 0.12, "risks": 0.13, "actions-decisions": 0.06}
  },
  "modifiers": [
    {"when": {"work_scope_any": ["fire_services"]}, "boost": {"compliance-approvals": 0.10}},
    {"when": {"risk_flag": "live_operations"}, "boost": {"risks": 0.05}},
    {"when": {"risk_flag": "heritage_adaptive_reuse"}, "boost": {"compliance-approvals": 0.05}},
    {"when": {"work_type": "remediation"}, "boost": {"compliance-approvals": 0.08, "risks": 0.05}}
  ]
}
```

Author a `base_weights` entry for every class×work-type pair that meaningfully deviates from `"default"` (at minimum: all residential rows scope-heavy, commercial/institution refurb compliance-heavy, advisory rows scope+actions-heavy); weights are renormalised to 1.0 after modifiers apply, so boosts are relative nudges, not absolute overrides.

**Step 4: Implement `backend/app/sitewise/taxonomy.py`** — frozen dataclasses + `lru_cache` loader mirroring `knowledge_catalog.py` (`REPO_ROOT / "data" / "taxonomy"`), functions used in the tests, `derive_risk_flags(complexity: dict[str, str], work_scope: list[str]) -> list[RiskFlag]` applying the derivation rules, and `section_weights_for(building_class, work_type, work_scope, risk_flags) -> dict[str, float]` (lookup `"{class}|{work_type}"` → fall back to `"default"` → apply matching modifiers → renormalise). Export `PMP_CORE_SECTIONS` from the config's `sections` list.

**Step 5:** Tests pass → `git commit -m "feat(taxonomy): declarative building-class/work-type/complexity config and loader"`

## Task 1.2: Projects schema migration + model

**Files:**
- Create: `backend/alembic/versions/018_project_taxonomy.py` (next free number)
- Modify: `backend/app/database/project.py` (add `building_class`, `work_type` `Mapped[str | None]` String(64) columns after `archetype`)
- Modify: `backend/app/schemas/projects.py` (`ProjectSummary`, `CreateProjectRequest` + new optional fields `building_class`, `work_type`, `subclasses: list[str] | None`, `scale: dict | None`, `complexity: dict | None`, `work_scope: list[str] | None`)
- Modify: `backend/app/api/projects.py` (create-project handler: validate via `validate_project_taxonomy`, persist columns, stash subclasses/scale/complexity/work_scope under `project_metadata["taxonomy"]`)
- Test: `backend/tests/test_project_taxonomy_api.py`

**Steps (red→green→commit):**
1. Failing API test: create project with full taxonomy payload → 200, response echoes `building_class`/`work_type`, GET detail exposes `metadata.taxonomy`; create with invalid combo → 422 listing the validation errors; create with **only** title (minimal brief) → 200 with NULLs. Follow the existing test style in `backend/tests/test_project_cockpit_bootstrap.py` for session/fixtures.
2. Migration: `op.add_column("projects", sa.Column("building_class", sa.String(64)))` + `work_type`. No user-facing legacy project migration is required; old projects are test fixtures only. If a small deterministic backfill is useful to keep existing fixtures/tests readable, it may set `building_class='residential'` for residential archetypes and `='commercial'` for `small-commercial`, but do not infer work_type/subclass or add migration UX. Downgrade drops both.
3. `uv run alembic upgrade head`, tests green, commit `feat(taxonomy): project building_class/work_type columns with archetype backfill`.

## Task 1.3: Test-only archetype bridge

**Files:**
- Create: `backend/app/sitewise/archetype_bridge.py`
- Test: `backend/tests/sitewise/test_archetype_bridge.py`

One small compatibility function for existing tests/fixtures and transitional callers:

```python
def effective_taxonomy(project) -> EffectiveTaxonomy:
    """Resolve (building_class, work_type, subclasses) from new columns,
    falling back to the legacy archetype mapping when columns are NULL.
    new-dwelling -> (residential, new, [house]); renovation -> (residential, refurb, [house]);
    multi-dwelling -> (residential, new, [townhouses]); ancillary -> (residential, extend, [other]);
    small-commercial -> (commercial, None, [other])."""
```

Tests cover: columns win over archetype; each legacy mapping; both NULL → `(None, None, [])`. Do not build user-facing migration flows around this bridge. Commit.

## Task 1.4: Taxonomy API endpoint

**Files:**
- Modify: `backend/app/api/projects.py` — `GET /api/projects/taxonomy` returning the full config (classes with subclasses/scale fields, complexity dimensions per class, risk-flag definitions, work scopes, emphasis profile sections). Static, cacheable, no auth-sensitive content beyond login.
- Test: extend `backend/tests/test_project_taxonomy_api.py` — response shape, all six classes present, universal dimensions present.

Commit `feat(taxonomy): taxonomy options API`.

## Definition of done

`uv run pytest tests/sitewise/test_taxonomy.py tests/sitewise/test_archetype_bridge.py tests/test_project_taxonomy_api.py -v` green; `uv run pytest tests/sitewise tests/workflows -v` no new failures; migration up/down clean.
