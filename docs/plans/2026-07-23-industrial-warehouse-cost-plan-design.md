# Design — NSW Industrial Warehouse / Logistics Cost Plan (v1)

**Date:** 2026-07-23  
**Status:** Approved for planning  
**Related:** Cost Plan capability gate (`workflow_capabilities.py`), hybrid compiler (`cost_plan_renderer.py`), platform catalog (`knowledge_catalog.py`)  
**Coordinate with:** `refactor/collapse-user-role` (role collapses to `architect-pm` / project-lead constant — do not reintroduce role branching)

---

## Problem

Project **Industrial** (`building_class=industrial`, subclass `warehouse`, NSW, architect-pm) cannot create a Cost Plan. The API returns **409** `workflow_capability_conflict` because Cost Plan coverage is hard-gated to **NSW residential + architect-PM**. The UI shows a generic “Request failed with status 409” because structured `detail` objects are not surfaced.

Industrial Cost Plan coverage is a real product goal. Expanding without a warehouse reference set and scaffold would either invent rates or emit residential rows (kitchen, BASIX) — both wrong.

---

## Decisions (locked)

| # | Decision | Choice |
|---|---|---|
| D1 | Slice | NSW Class 7b **warehouse** + **logistics_ecommerce** only |
| D2 | Depth | **Structure only** — elemental scaffold + appropriate fees/consultants; **no rate / % pack**; disclose gaps |
| D3 | Generation | Extend **hybrid compiler** — deterministic industrial scaffold + narrative LLM into placeholders |
| D4 | Role / state | Keep **NSW** + **architect-pm** (or collapsed constant). No interstate / other roles in v1 |
| D5 | Catalog subclass axis | **Not** added in v1. Subclass support lives in the **capability gate**. Industrial seed is class-level with warehouse/logistics content |
| D6 | Doctrine | Missing reference data is disclosed, never filled from general model knowledge |

---

## Product claim

**Supported:** `create_cost_plan` / `refresh_cost_plan` / related typed actions when:

- `building_class == "industrial"`
- at least one subclass in `{warehouse, logistics_ecommerce}`
- `state == "NSW"`
- `user_role == "architect-pm"` (or collapsed constant)
- required profile fields present (`building_class`, `work_type`, `user_role`, `state`)

**Unsupported (with reasons):** other industrial subclasses; non-NSW; non–architect-pm (until role collapse removes that axis).

**`reference_coverage`:**

- Residential path: `NSW residential architect-PM reference set` (unchanged)
- Warehouse/logistics path: `NSW industrial warehouse/logistics Class 7b scaffold set (structure only; no rate pack)`

---

## Reference data

1. **Fix leak:** add `applies_to_classes: [residential]` to  
   `data/skills/reference/nsw-residential-cost-breakdown-reference.md`  
   so taxonomy-mode industrial selection stops pulling the house breakdown.

2. **Add:** `data/skills/reference/nsw-industrial-warehouse-cost-breakdown-reference.md`  
   - `applies_to_classes: [industrial]`  
   - `required_by: {create-cost-plan: 2}`  
   - Practice taxonomy only — no market rates, not project evidence  
   - Workbook groups: Fees → Consultants → Construction → PC / Contingency (same shape as residential for workbook mapping)  
   - Construction families: Preliminaries; Siteworks/earthworks; Substructure/slabs; Structural steel/frame; Roof/cladding/envelope; Dock/hardstand/yard; Office fitout (ancillary); Building services; External works/stormwater; Specialist systems as **gaps** (racking, cool rooms, etc.)

3. **Catalog parity:** pin taxonomy-mode `create-cost-plan` paths for residential vs industrial.

4. **Re-ingest** platform knowledge after seed merge so runtime corpus includes the new file.

---

## Hybrid scaffold

Parameterize `cost_plan_renderer.py` by coverage family (`residential` | `industrial_warehouse`):

| Area | Residential (today) | Industrial warehouse (v1) |
|---|---|---|
| Fees | DA/CC, BASIX, Sydney Water, levies | DA/CC (or CDC as evidence-led), fire/statutory levies as TBC — no BASIX |
| Consultants | Structural, geotech, survey, hydraulic, BASIX/energy, certifier | Structural, civil, geotech, survey, fire engineer, hydraulic, certifier — evidence-led TBC |
| Construction | Kitchen/baths, residential envelope | Warehouse families above |
| Benchmark % | Keep residential indicative split | **None** — all construction amounts TBC + “no rate pack” disclosure |
| PC allowances | Kitchen joinery, wet area, etc. | Industrial-appropriate placeholders only where practice taxonomy warrants; otherwise omit residential PCs |

Hybrid eligibility: same feature flag + `evidence_grounded` rules; capability ensures only supported profiles reach create. Role check remains architect-pm until collapse lands.

Assembler / workbook stay taxonomy-agnostic consumers of markdown/typed rows.

---

## Capability & API

Update `_cost_plan_capability` in `workflow_capabilities.py`:

- After required fields, branch on `building_class`
- Residential: existing NSW + architect-pm checks
- Industrial: NSW + architect-pm + subclass ∈ `{warehouse, logistics_ecommerce}`
- Set `reference_coverage` per branch
- Other classes: unsupported with clear reasons (do not claim six-class coverage)

Start endpoints already return 409 with structured detail; keep that shape.

---

## Frontend

1. Disable Cost Plan Create/Refresh when `create_cost_plan.status !== "supported"` (today only checks overlay readiness).
2. Improve `errorDetail` in `frontend/src/lib/http.ts` to format object `detail` (reasons / required_fields / code) so 409s are readable.
3. Optionally show capability reasons in the Cost Plan panel when blocked (tile already shows Blocked).

---

## Out of scope (v1)

- Other industrial subclasses (cold_storage, manufacturing, data_centre, …)
- Interstate coverage
- Rate / benchmark / $/m² pack
- Catalog `applies_to_subclasses` axis
- Commercial Class 5/6 Cost Plan
- Tender handoff behaviour changes
- Inventing rates from model knowledge

---

## Acceptance (Industrial project)

1. Capability → `supported` with warehouse/logistics `reference_coverage`
2. Create succeeds; hybrid scaffold has industrial rows (no kitchen/BASIX)
3. Output discloses structure-only / no rate pack
4. `manufacturing` (etc.) stays `unsupported`
5. Residential NSW path unchanged (tests green)
6. UI disables Create when unsupported; structured errors if 409 still hit

---

## Follow-ons (not this plan)

- Warehouse rate / indicative % pack once a trusted reference exists  
- Widen to other Class 7b / Class 8 subclasses  
- Optional catalog `applies_to_subclasses` to stop industrial seed selection for unsupported subclasses at catalog layer  
- Industrial-specific authority-gate wording in hybrid scaffold (today still includes a residential HBCF/HOW row)

---

## Verified (2026-07-23)

Branch: `feat/industrial-warehouse-cost-plan` (worktree). Commits through `cb87cb98`.

| Check | Result |
|---|---|
| Live project Industrial (`warehouse`, NSW, architect-pm) capability via worktree code | `supported` with warehouse/logistics structure-only `reference_coverage` |
| Manufacturing industrial subclass | `unsupported` |
| Catalog paths for industrial | Includes industrial warehouse ref; excludes residential breakdown |
| Platform re-ingest | Forced persist of both cost-breakdown reference seeds; DB frontmatter `applies_to_classes` correct |
| Focused automated suites (Segments 0–4) | Green |

**Runtime UI Create** still requires restarting the FastAPI process from this branch/worktree (port 8000 was serving `D:\AI Projects\clerk\backend`, not the feature worktree). After restart + frontend on this branch, Create Cost Plan on Industrial should succeed without 409.
