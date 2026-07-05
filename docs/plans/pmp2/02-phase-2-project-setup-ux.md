# PMP 2.0 — Phase 2: Project Setup UX (frontend)

> **For Claude (implementing agent):** REQUIRED SUB-SKILL: Use superpowers:executing-plans to work this phase task-by-task.
> **Required reading first:** [../2026-07-05-pmp2-live-interactive-pmp.md](../2026-07-05-pmp2-live-interactive-pmp.md) — goal, current-state file map, design decisions D1–D13, test commands, recorded baseline test failures. Source spec: `docs/pmp2.0/pmp2.md` §3.2 (the three-column middle panel this phase builds).
> **Depends on:** [Phase 1](01-phase-1-taxonomy-foundation.md). **Parallel-safe with:** Phases 3, 4, 5.

**Outcome:** Creating/editing a project walks Class → Work Type → (Subclass | Scale | Complexity) three-column middle panel per pmp2.md §3.2; selections persist; risk flags surface as chips.

## Task 2.1: Types + API client + query

**Files:**
- Modify: `frontend/src/lib/types/project.ts` — `TaxonomyCatalog`, `BuildingClass`, `Subclass`, `ScaleField`, `ComplexityDimension`, `RiskFlagDefinition` types; extend `ProjectDetail`/`CreateProjectInput` with `building_class`, `work_type`, taxonomy metadata.
- Modify: `frontend/src/lib/api.ts` — `getTaxonomy()`.
- Create: `frontend/src/lib/queries/taxonomy.ts` — TanStack Query hook, `staleTime: Infinity`.
- Test: extend existing api tests if present; otherwise types are exercised by component tests below.

## Task 2.2: Class/Type/Subclass picker in CreateProjectPanel

**Files:**
- Modify: `frontend/src/components/project/CreateProjectPanel.tsx`
- Create: `frontend/src/components/project/TaxonomyPicker.tsx`
- Test: `frontend/src/components/project/TaxonomyPicker.test.tsx`

Behaviour (write tests first, vitest + testing-library, mirroring `ActivityFeed.test.tsx` style):
- Class grid (6 tiles) → work-type row (filtered by class's `work_types`) → middle panel 3 columns: **Subclass** (radio; checkbox list when `multi_subclass` i.e. mixed; always trailing "Other" with free-text input), **Scale** (inputs from selected subclass's `scale_fields`, typical-range placeholder text), **Complexity** (select per dimension, defaulting to first option).
- "Other" subclass free text stored as `{ value: "other", label: <user text> }` (spec: retained for AI pattern learning).
- Minimal path stays minimal: title alone must still submit (taxonomy optional — the one-line-brief user).
- Submit maps to the Phase 1 request shape. If an intermediate phase still needs `archetype` for tests/transitional generation before Phase 4 lands, derive it quietly from taxonomy; do not expose a legacy archetype UX or design a migration path for old projects.

## Task 2.3: Post-create taxonomy editing

**Files:**
- Modify: `backend/app/api/projects.py` — `PATCH /api/projects/{project_id}` accepting the same taxonomy fields (validate, persist, re-derive risk flags).
- Modify: `frontend/src/components/project/ProjectControlBoard.tsx` (or wherever project settings render — locate the settings surface in `ProjectShell.tsx` at implementation time) — "Project profile" section reusing `TaxonomyPicker` in edit mode.
- Tests: backend PATCH test + component test.

## Task 2.4: Risk flag chips

**Files:**
- Modify: `backend/app/schemas/projects.py` — `risk_flags: list[RiskFlag]` on `ProjectDetail` (computed via `derive_risk_flags`, not stored).
- Modify: frontend project header/control board — severity-coloured chips (critical/warning/info) with description tooltip.
- Tests both sides.

## Definition of done

`npm run test` green; `npm run lint` clean; manual smoke: create a `commercial / new / office` project and a title-only project.
