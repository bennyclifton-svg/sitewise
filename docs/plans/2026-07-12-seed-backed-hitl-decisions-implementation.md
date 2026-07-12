# Seed-backed HITL Decisions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand PMP/cost-plan/tender human-in-the-loop decisions: seed-backed curated catalogs (~10–15 for sparse residential), shared-key hard sync across PMP and cost plan, TCM intake reuse, then matrix multi-candidate inline overrides.

**Architecture:** Parse structured `decision-catalog` YAML fences from `data/seed/` files; merge with `PMP_CORE_DECISIONS` into allowed option sets for Create/Update PMP and cost plan; persist locks in `project_decisions`; on override, restamp all drafts that contain matching fences. TCM intake reads shared decisions; matrix phase stores mapping corrections inline and removes those items from QA.

**Tech Stack:** FastAPI, SQLAlchemy, existing `pmp_decisions` / `DecisionControl`, seed markdown, Vitest, pytest

**Design:** `docs/plans/2026-07-12-seed-backed-hitl-decisions-design.md`

---

### Task 1: Seed decision catalog parser

**Files:**
- Create: `backend/app/sitewise/seed_decision_catalog.py`
- Create: `backend/tests/sitewise/test_seed_decision_catalog.py`

**Step 1: Write failing tests** for parsing a `decision-catalog` YAML fence, filtering by archetype/class, and rejecting malformed entries.

**Step 2: Implement parser** — extract fences named `decision-catalog`, parse YAML list of decisions with `id`, `label`, `section`, `options`, optional `applies_to`, `default_hint`.

**Step 3: Commit** `feat: parse seed decision catalogs`

---

### Task 2: Enrich finishes + brief seeds with decision catalogs

**Files:**
- Modify: `data/seed/finishes-residential.md`
- Modify: `data/seed/new-dwelling-guide.md` (and/or `residential-construction-guide.md`, `procurement-quoting-guide.md` as needed)
- Test: extend `test_seed_decision_catalog.py` to load real seed files and assert ≥8 brief/finishes decision ids for new-dwelling residential

**Step 1: Research** finishes/brief decision space from seed prose + NSW Class 1a practice.

**Step 2: Add `decision-catalog` fences** covering flooring, cladding, roofing, kitchen, wet areas, joinery, glazing, etc. Target ~10–12 seed decisions (plus 3 core = ~13–15 total).

**Step 3: Commit** `feat: add seed-backed brief and finishes decision catalogs`

---

### Task 3: Assemble allowed decision set for PMP

**Files:**
- Modify: `backend/app/sitewise/pmp_decisions.py`
- Create/Modify: `backend/tests/sitewise/test_pmp_decisions.py` (or new test file)
- Modify: `backend/app/workflows/create_pmp.py` / instructions if needed to require seed decisions when sparse

**Step 1: Add `decision_option_sets_for_project` merge** of core + taxonomy + filtered seed catalogs (cap ~15 preferring core + seed over unbounded taxonomy if needed — keep taxonomy dims that already exist).

**Step 2: Add helper** `format_required_decision_ids` / sparse-brief selection: when brief evidence is thin, include curated seed decision ids up to band.

**Step 3: Tests** for merge + filtering.

**Step 4: Commit** `feat: merge seed catalogs into PMP decision option sets`

---

### Task 4: Cost plan decision fences + locked restamp

**Files:**
- Modify: `backend/app/workflows/create_cost_plan.py` (and update path)
- Modify: `backend/app/workflows/create_cost_plan_instructions.md`
- Modify: `backend/app/api/projects.py` PUT decision handler
- Test: new `backend/tests/workflows/test_cost_plan_decisions.py` + API restamp test

**Step 1: Accept `pmp-decision` fences in cost plan markdown** (reuse parser; same fence name for UI compatibility).

**Step 2: On PUT decision**, restamp **all** latest drafts (PMP + cost plan) that contain the decision id.

**Step 3: Inject locked decisions + option sets into cost plan prompts.**

**Step 4: Commit** `feat: hard-sync shared decisions across PMP and cost plan drafts`

---

### Task 5: Cost-only decision catalog (small set)

**Files:**
- Modify: `data/seed/cost-management-principles.md`
- Wire into cost plan option sets

**Step 1: Add 2–4 cost-only decisions** (contingency band, PC/PS treatment, inclusions baseline).

**Step 2: Tests** that cost-only ids appear for cost plan but are optional for PMP.

**Step 3: Commit** `feat: add cost-plan-only seed decisions`

---

### Task 6: TCM intake shared decisions (Phase A)

**Files:**
- Modify tender intake API/UI as exists today
- Test: backend + frontend tests for prefill from `project_decisions`

**Step 1: Locate** `TenderIntakePanel` / intake schema.

**Step 2: Prefill shared keys** from `list_decisions` / locked selections; render DecisionControl for those fields.

**Step 3: Override** calls existing PUT `/projects/{id}/decisions/{decisionId}`.

**Step 4: Commit** `feat: prefill tender intake from shared project decisions`

---

### Task 7: TCM matrix multi-candidate inline overrides (Phase B)

**Files:**
- Modify: mapping/adjudication persistence to retain candidates
- Modify: `TenderMatrix.tsx` + types
- Modify: QA service to exclude multi-candidate items that have inline override path
- Tests: matrix + QA filtering

**Step 1: Persist candidate options** on mapping decisions when ≥2 candidates.

**Step 2: Render inline choice** on matrix cells; POST correction locks mapping.

**Step 3: Remove those items from QA queue.**

**Step 4: Commit** `feat: inline multi-candidate mapping overrides in tender matrix`

---

### Task 8: Final verification

**Step 1:** Run focused backend pytest suites for decisions/seeds/cost/tender.

**Step 2:** Run frontend vitest for DecisionControl / TenderMatrix / intake.

**Step 3:** Fix regressions; final commit if needed.

---

## Execution note

User authorized unattended completion. Prefer implementing in this worktree
(`.worktrees/seed-backed-hitl-decisions`) with frequent commits. Skip asking
between batches; continue until Task 8 passes.
