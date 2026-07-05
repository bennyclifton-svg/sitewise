# PMP 2.0 — Phase 3: Knowledge Layer Expansion (seed merge + class-aware selection)

> **For Claude (implementing agent):** REQUIRED SUB-SKILL: Use superpowers:executing-plans to work this phase task-by-task.
> **Required reading first:** [../2026-07-05-pmp2-live-interactive-pmp.md](../2026-07-05-pmp2-live-interactive-pmp.md) — goal, current-state file map, design decisions D1–D13 (especially D5 and D12), test commands, recorded baseline test failures.
> **Knowledge-layer ground rules (from the 2026-07-04 restructure):** selection changes happen in **frontmatter, not code**; `tests/sitewise/test_catalog_parity.py` pins selection output; `search_documents` deliberately keeps `include_platform_knowledge=False` — evidence and knowledge are separate channels by design, don't "fix" that.
> **Depends on:** [Phase 1](01-phase-1-taxonomy-foundation.md). **Blocks:** [Phase 4](04-phase-4-adaptive-pmp.md). **Parallel-safe with:** Phases 2, 5.

**Outcome:** The 10 `data/seed-commercial/` guides live in the catalog; seed selection understands building_class/work_type; PMP generation can route each core section to required/optional seed **sections**. Existing archetype parity tests remain as compatibility guards only; old projects are test fixtures, not migration targets.

## Task 3.1: Reconcile the five colliding guides

**Files:** `data/seed/{cost-management-principles,contract-administration-guide,program-scheduling-guide,ncc-reference-guide,as-standards-reference}.md` vs same names in `data/seed-commercial/`.

Steps:
1. Diff each pair. Produce a merged file in `data/seed/` that (a) keeps every section the residential eval fixtures/greenfield contracts reference, (b) adds the commercial content, (c) keeps the **catalog** frontmatter schema (tier/loaded_by/topics/summary/required_by/applies_to_*) — discard the seed-commercial schema keys (domainSlug etc.), carrying `applicableProjectTypes` into `applies_to_work_types`.
2. Guard: `uv run pytest tests/sitewise -v` must stay green after each merge (especially catalog parity and any pmp eval fixtures).
3. One commit per merged file.

## Task 3.2: Import the five new guides

**Files:** move + reheader `commercial-construction-guide.md`, `multi-residential-apartments-guide.md`, `residential-construction-guide.md`, `remediation-due-diligence-guide.md`, `procurement-tendering-guide.md` into `data/seed/`; delete `data/seed-commercial/` when empty; update `docs/pmp2.0/pmp2.md` reference or leave (doc is historical input).

Frontmatter template (new keys `applies_to_classes` / `applies_to_work_types` — Task 3.3 teaches the catalog to read them):

```yaml
---
tier: overlay
loaded_by: create-pmp
topics: [commercial, construction, ncc]
summary: "<one-line, LLM-drafted then human-reviewed — flag for Benny like the existing 24>"
applies_to_classes: [commercial, institution]
applies_to_work_types: [new, refurb, extend]
required_by:
  create-pmp: 2
---
```

Decide `required_by` rank per guide so ordering is deterministic (doctrine=0, class guide=1, role seed=2, cross-cutting 3+ — inspect existing frontmatter and match). Note: `procurement-tendering-guide` (commercial tendering) coexists with `procurement-quoting-guide` (residential) — class-scoped `applies_to_classes` keeps them apart.

## Task 3.3: Class-aware selection in the catalog

**Files:**
- Modify: `backend/app/sitewise/knowledge_catalog.py` — `CatalogEntry` gains `applies_to_classes` / `applies_to_work_types`; `select_required_paths(workflow, archetype, user_role)` gains optional `building_class`, `work_type` kwargs. Resolution: when building_class present → doctrine + class-matched guides + role seed + cross-cutting (rank-ordered); when NULL → existing archetype path for test/compatibility callers.
- Modify: `backend/app/sitewise/pmp_sources.py` — `required_platform_paths` passes the project's effective taxonomy (via `archetype_bridge.effective_taxonomy`); signature grows optional kwargs, callers in `create_pmp.py`/`update_pmp.py` pass the project.
- Test: `backend/tests/sitewise/test_catalog_parity.py` — keep enough existing archetype pins to catch accidental compatibility breakage, but do not add new legacy migration coverage; add new pinned expectations for representative new combos: (commercial, new, architect-pm), (industrial, new, d-and-c), (institution, refurb, architect-pm), (any, advisory, architect-pm), (mixed, new, architect-pm), (infrastructure, new, architect-pm).
- Test: `backend/tests/sitewise/test_taxonomy_seed_selection.py` — mapping rules (e.g. remediation work type always pulls `remediation-due-diligence-guide`).

Also: cost plan (`cost_plan_sources.py`) keeps its residential gate untouched — `RESIDENTIAL_ARCHETYPES` behaviour must not change (cost-plan expansion is out of scope, see overview §Deferred).

## Task 3.4: Corpus ingest of merged seeds

The ingest pipeline persists `data/seed/` to the corpus (see `_KNOWLEDGE_SOURCES` in `knowledge_catalog.py`, `backend/ingest/`). Steps: run the ingest path used for seeds (check `backend/ingest/pipeline.py` seed handling / any management command; if seeds are ingested at startup or via script, document the exact command in the commit message), verify `load_platform_documents_by_paths` returns the new paths in a test with the DB fixture, verify the MCP `list_platform_knowledge` overlay gate still passes (`backend/tests/mcp_bridge/test_tools_search.py`).

## Task 3.5: Section-level seed routing for PMP generation

**Files:**
- Create: `data/taxonomy/pmp-section-seed-map.json`
- Create: `backend/app/sitewise/pmp_seed_routing.py`
- Test: `backend/tests/sitewise/test_pmp_seed_routing.py`

Purpose: make D12 enforceable. Frontmatter chooses the applicable seed files; this task chooses which **sections** of those files are loaded for each PMP core section. The LLM must configure and summarise curated seed content, not source PMP domain content from pretrained memory.

Config shape:

```json
{
  "sections": {
    "compliance-approvals": {
      "required": [
        {"path": "seed/ncc-reference-guide.md", "section_ids": ["ncc-approval-pathways"]},
        {"path": "seed/as-standards-reference.md", "section_ids": ["fire-services"]}
      ],
      "optional": [
        {"path": "seed/remediation-due-diligence-guide.md", "section_ids": ["contamination-screening"], "when": {"work_type": "remediation"}}
      ]
    }
  }
}
```

Implementation rules:
1. `pmp_seed_routing.py` resolves routes from `(building_class, work_type, subclasses, work_scope, risk_flags)` and the selected catalog paths from Task 3.3.
2. Required routes must reference files selected for the project or cross-cutting doctrine/seed files; unknown files or section IDs are validation errors.
3. Required seed files/sections must be ingested before Create/Update PMP. Missing required ingested content blocks generation with a `WorkflowTraceEvent` that names the missing `path#section_id`.
4. Optional routes may warn and continue; warnings are included in the run trace.
5. The content loaded into generation records refs as `seed/path.md#section_id` in `seed_consulted` / provenance metadata, not just filenames.
6. Tests pin representative routes: residential new scope-heavy sections, commercial/refurb/fire_services compliance sections (AS 2419.1 and AS 2941 source sections), remediation due-diligence sections, advisory service/deliverable sections, and a small compatibility check for archetype fallback.

## Definition of done

Compatibility parity checks green + new taxonomy pins added; section-level seed routing tests green; `uv run pytest tests/sitewise tests/mcp_bridge -v` green; `data/seed-commercial/` gone.
