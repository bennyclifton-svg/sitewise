# NSW Industrial Warehouse / Logistics Cost Plan Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unlock Create Cost Plan for NSW industrial projects with subclass `warehouse` or `logistics_ecommerce`, using a structure-only hybrid scaffold and a dedicated platform reference — without inventing rates or emitting residential rows.

**Architecture:** Widen `_cost_plan_capability` for the warehouse/logistics slice; fix residential catalog leak; add an industrial warehouse cost-breakdown seed; parameterize the hybrid scaffold by coverage family; disable the Create button on unsupported capability and surface structured 409 details in the UI.

**Tech Stack:** Python 3.12 + FastAPI + pytest (`backend/`); Vite + React + Vitest (`frontend/`); platform seeds under `data/skills/reference/`.

**Design:** `docs/plans/2026-07-23-industrial-warehouse-cost-plan-design.md`

**Coordinate with:** Branch `refactor/collapse-user-role` may land in parallel. Keep role checks as `architect-pm` (or the collapsed constant). Do **not** reintroduce multi-role Cost Plan branching.

---

## How to use this plan

- Run backend tests from `backend/` via `uv run pytest …`
- Run frontend tests from `frontend/` via `pnpm test …` / `pnpm exec vitest run …`
- Commit after each segment (or after each task group if segment is large)
- Re-ingest platform knowledge after Segment 2 seeds land (Segment 6)

Dependency graph:

```
Segment 0  Catalog leak fix + industrial seed
    │
Segment 1  Capability gate
    │
Segment 2  Hybrid renderer taxonomy branch
    │
Segment 3  Frontend capability disable + 409 detail
    │
Segment 4  Integration / catalog parity / acceptance
    │
Segment 5  Platform re-ingest + manual verify on Industrial
```

---

# Segment 0 — Reference data: stop residential leak + add warehouse seed

**Depends on:** nothing  
**Why:** Taxonomy-mode industrial selection currently pulls `nsw-residential-cost-breakdown-reference.md` because it has no `applies_to_classes`. Without a warehouse seed and the leak fix, opening capability would still ground industrial plans on house taxonomy.

**Files:**
- Modify: `data/skills/reference/nsw-residential-cost-breakdown-reference.md`
- Create: `data/skills/reference/nsw-industrial-warehouse-cost-breakdown-reference.md`
- Modify: `backend/app/sitewise/cost_plan_sources.py` (add constant for the new path)
- Modify: `backend/tests/sitewise/test_catalog_parity.py`

### Task 0.1 — Write failing catalog parity tests for taxonomy-mode cost plan

Add tests that assert:

1. `select_required_paths(workflow="create-cost-plan", archetype="new-dwelling", user_role="architect-pm", building_class="residential", work_type="new")` includes `skills/reference/nsw-residential-cost-breakdown-reference.md` and does **not** include the industrial warehouse path.
2. Same call with `building_class="industrial", work_type="new"` includes `skills/reference/nsw-industrial-warehouse-cost-breakdown-reference.md` and does **not** include the residential breakdown path.
3. Both still include doctrine + `seed/cost-management-principles.md` + role overlay (whatever `ROLE_SEED_PATHS["architect-pm"]` resolves to on this branch).

```python
def test_create_cost_plan_taxonomy_residential_excludes_industrial_ref() -> None:
    paths = select_required_paths(
        workflow="create-cost-plan",
        archetype="new-dwelling",
        user_role="architect-pm",
        building_class="residential",
        work_type="new",
    )
    assert NSW_RESIDENTIAL_COST_REFERENCE in paths
    assert NSW_INDUSTRIAL_WAREHOUSE_COST_REFERENCE not in paths


def test_create_cost_plan_taxonomy_industrial_excludes_residential_ref() -> None:
    paths = select_required_paths(
        workflow="create-cost-plan",
        archetype="new-dwelling",
        user_role="architect-pm",
        building_class="industrial",
        work_type="new",
    )
    assert NSW_INDUSTRIAL_WAREHOUSE_COST_REFERENCE in paths
    assert NSW_RESIDENTIAL_COST_REFERENCE not in paths
```

### Task 0.2 — Run tests to verify they fail

```bash
cd backend
uv run pytest tests/sitewise/test_catalog_parity.py -k "taxonomy_industrial or taxonomy_residential" -v
```

Expected: FAIL (industrial path missing / residential still selected for industrial).

### Task 0.3 — Fix residential frontmatter leak

In `data/skills/reference/nsw-residential-cost-breakdown-reference.md` frontmatter, add:

```yaml
applies_to_classes: [residential]
```

Keep existing `applies_to_archetypes` for archetype-mode selection.

### Task 0.4 — Add industrial warehouse reference seed

Create `data/skills/reference/nsw-industrial-warehouse-cost-breakdown-reference.md` with frontmatter:

```yaml
---
tier: topic
applies_to_roles: [architect-pm, owner-builder, builder, d-and-c]
applies_to_classes: [industrial]
topics: [cost, taxonomy]
summary: "Practice-level taxonomy for early NSW Class 7b warehouse/logistics cost plans: workbook-ready groups and construction breakdown shape. Structure only — never market rates or active-project evidence."
required_by: {create-cost-plan: 2}
status: reference
author: agent
date: 2026-07-23
scope: practice guidance only — structure only; no rate pack
---
```

Body must include:

- Explicit boundary: warehouse / logistics_ecommerce Class 7b practice shape; not rates; not evidence
- Workbook-ready groups: Fees and charges · Consultants · Construction · Contingency / allowances
- Construction taxonomy table with families: Preliminaries; Siteworks and earthworks; Substructure and slabs; Structural steel and frame; Roof cladding and envelope; Dock hardstand and yard; Office fitout (ancillary); Building services; External works and stormwater; Specialist systems (gap — racking, cool rooms, etc.)
- Fees/consultants guidance: no BASIX / residential kitchen framing; DA/CC or CDC evidence-led; fire engineer / civil as typical industrial consultants
- Use rules mirroring residential: starting taxonomy, GST ex basis, contingency on construction only, lump sums over fake precision, disclose missing rate pack

### Task 0.5 — Export constant in `cost_plan_sources.py`

```python
NSW_INDUSTRIAL_WAREHOUSE_COST_REFERENCE = (
    "skills/reference/nsw-industrial-warehouse-cost-breakdown-reference.md"
)
```

### Task 0.6 — Re-run catalog parity tests

```bash
cd backend
uv run pytest tests/sitewise/test_catalog_parity.py -v
```

Expected: PASS (including existing archetype-mode contracts).

### Task 0.7 — Commit

```bash
git add data/skills/reference/nsw-residential-cost-breakdown-reference.md \
  data/skills/reference/nsw-industrial-warehouse-cost-breakdown-reference.md \
  backend/app/sitewise/cost_plan_sources.py \
  backend/tests/sitewise/test_catalog_parity.py
git commit -m "$(cat <<'EOF'
feat: add NSW warehouse cost taxonomy seed and stop residential catalog leak

Industrial taxonomy selection was pulling the house breakdown because the
residential reference had no applies_to_classes filter.
EOF
)"
```

---

# Segment 1 — Capability gate

**Depends on:** Segment 0 (coverage claim must match real reference)  
**Why:** API 409 for Industrial comes from `_cost_plan_capability` rejecting non-residential.

**Files:**
- Modify: `backend/app/projects/workflow_capabilities.py`
- Modify: `backend/tests/projects/test_workflow_capabilities.py`

### Task 1.1 — Write failing capability tests

```python
_WAREHOUSE_SUBCLASSES = ("warehouse", "logistics_ecommerce")


def test_cost_plan_supports_nsw_warehouse_and_logistics() -> None:
    for subclass in _WAREHOUSE_SUBCLASSES:
        cost_plan = workflow_capabilities(
            _snapshot(
                building_class="industrial",
                subclasses=[subclass],
                state="NSW",
                user_role="architect-pm",
            )
        ).capabilities["create_cost_plan"]
        assert cost_plan.status == "supported"
        assert any("warehouse/logistics" in item for item in cost_plan.reference_coverage)


def test_cost_plan_rejects_other_industrial_subclasses() -> None:
    cost_plan = workflow_capabilities(
        _snapshot(
            building_class="industrial",
            subclasses=["manufacturing"],
            state="NSW",
            user_role="architect-pm",
        )
    ).capabilities["create_cost_plan"]
    assert cost_plan.status == "unsupported"
    assert any("warehouse" in reason.lower() or "logistics" in reason.lower() for reason in cost_plan.reasons)


def test_cost_plan_still_rejects_interstate_industrial() -> None:
    cost_plan = workflow_capabilities(
        _snapshot(
            building_class="industrial",
            subclasses=["warehouse"],
            state="VIC",
            user_role="architect-pm",
        )
    ).capabilities["create_cost_plan"]
    assert cost_plan.status == "unsupported"
    assert any("NSW" in reason for reason in cost_plan.reasons)
```

Keep existing `test_cost_plan_does_not_claim_six_class_or_interstate_coverage` (commercial + VIC still unsupported).

### Task 1.2 — Run tests to verify they fail

```bash
cd backend
uv run pytest tests/projects/test_workflow_capabilities.py -k cost_plan -v
```

Expected: FAIL on new supported warehouse cases.

### Task 1.3 — Implement capability branching

In `_cost_plan_capability`:

1. Keep `_PROJECT_PLAN_FIELDS` needs_input behaviour; when missing, set `reference_coverage` to a neutral list or both sets — prefer listing both coverage names once industrial exists, or keep residential string until fields known. Simplest: keep current residential string for needs_input (unchanged).
2. After fields present:
   - If `building_class == "residential"`: existing NSW + architect-pm checks; residential `reference_coverage`
   - Elif `building_class == "industrial"`: require NSW + architect-pm + subclass intersection with `{warehouse, logistics_ecommerce}` (use same `_subclass_value` helper as tender); industrial `reference_coverage`; reason if subclass wrong: e.g. `"Cost Plan industrial coverage is currently NSW warehouse / logistics Class 7b only."`
   - Else: unsupported — residential/industrial-warehouse only (update commercial reason text accordingly)

Helper sketch:

```python
_INDUSTRIAL_WAREHOUSE_SUBCLASSES = frozenset({"warehouse", "logistics_ecommerce"})


def _profile_subclasses(snapshot: ProjectSnapshot) -> set[str]:
    return {_subclass_value(item) for item in getattr(snapshot.profile, "subclasses", [])}
```

For industrial supported reason, mirror residential honesty: structure-only coverage; missing rate pack must be confirmed/disclosed, never filled from general model knowledge.

### Task 1.4 — Re-run capability tests

```bash
cd backend
uv run pytest tests/projects/test_workflow_capabilities.py -v
```

Expected: PASS.

### Task 1.5 — Commit

```bash
git add backend/app/projects/workflow_capabilities.py backend/tests/projects/test_workflow_capabilities.py
git commit -m "$(cat <<'EOF'
feat: support Cost Plan capability for NSW warehouse/logistics

Opens create/refresh for industrial Class 7b warehouse and logistics_ecommerce
while keeping other industrial subclasses and interstate profiles unsupported.
EOF
)"
```

---

# Segment 2 — Hybrid renderer industrial scaffold

**Depends on:** Segment 1  
**Why:** Once capability opens, hybrid must not emit kitchen/BASIX rows for warehouse projects.

**Files:**
- Modify: `backend/app/sitewise/cost_plan_renderer.py`
- Modify: `backend/tests/sitewise/test_cost_plan_renderer.py`
- Optionally touch: `backend/app/workflows/create_cost_plan.py` only if hybrid eligibility or drafting notes hardcode residential

### Task 2.1 — Write failing renderer tests

Add a warehouse project fixture (`building_class="industrial"`, subclasses via metadata if needed) and assert scaffold markdown:

- Contains industrial construction labels (e.g. `"Structural steel and frame"`, `"Dock hardstand and yard"`)
- Does **not** contain `"Kitchen and bathrooms"`, `"BASIX"`
- Contains an explicit no-rate-pack / structure-only disclosure string you choose and keep stable for tests

Residential fixture tests must still expect kitchen/BASIX.

### Task 2.2 — Run tests to verify they fail

```bash
cd backend
uv run pytest tests/sitewise/test_cost_plan_renderer.py -v
```

Expected: FAIL on industrial assertions.

### Task 2.3 — Parameterize row taxonomies

In `cost_plan_renderer.py`:

1. Introduce a small coverage resolver, e.g. `_coverage_family(project) -> Literal["residential", "industrial_warehouse"]` based on `project.building_class` (capability already blocked unsupported industrial subclasses).
2. Replace module-level single `_FEE_ROWS` / `_CONSULTANT_ROWS` / `_CONSTRUCTION_ROWS` / PC rows with per-family tables (or dict keyed by family).
3. Residential tables = current constants (byte-stable labels).
4. Industrial tables = structure aligned to the new seed; **no** `_CONSTRUCTION_BENCHMARK_PCT` for industrial — render TBC amounts and disclosure instead of % split.
5. Update copy that says `"Construction rows follow NSW residential taxonomy."` to branch.
6. Keep `architect-pm` role hard-check in `render_cost_plan_scaffold` until role collapse removes it.

Do not invent market rates. Prefer lump-sum TBC lines.

### Task 2.4 — Re-run renderer tests + residential regression

```bash
cd backend
uv run pytest tests/sitewise/test_cost_plan_renderer.py tests/workflows/test_create_cost_plan.py -q --tb=line
```

Expected: PASS (or only intentional hybrid-integration skips if network).

### Task 2.5 — Commit

```bash
git add backend/app/sitewise/cost_plan_renderer.py backend/tests/sitewise/test_cost_plan_renderer.py
git commit -m "$(cat <<'EOF'
feat: add industrial warehouse Cost Plan hybrid scaffold

Branches fee, consultant, and construction rows by coverage family so NSW
warehouse plans no longer emit residential kitchen/BASIX taxonomy.
EOF
)"
```

---

# Segment 3 — Frontend: capability gate UX + readable 409s

**Depends on:** Segment 1 (capability status already correct on project payload)  
**Why:** Industrial users can click Create today when overlay is ready; 409 detail is an object and collapses to “Request failed with status 409”.

**Files:**
- Modify: `frontend/src/lib/http.ts`
- Modify: `frontend/src/components/project/ProjectControlBoard.tsx`
- Modify: `frontend/src/components/project/ProjectControlBoard.test.tsx` (and/or `workflowTiles.test.ts` / cockpit tests)
- Optionally: add a small unit test file for `errorDetail` if none exists — prefer testing via exported behaviour or extract a pure helper

### Task 3.1 — Write failing tests

1. Cost Plan Create button disabled when `create_cost_plan.status === "unsupported"` even if `overlay_status.ready`.
2. `errorDetail` (or ApiError message path) for payload:

```json
{
  "detail": {
    "code": "workflow_capability_conflict",
    "status": "unsupported",
    "reasons": ["Cost Plan reference-data coverage is currently residential only."],
    "required_fields": []
  }
}
```

produces a message containing the reason text (not only “status 409”).

### Task 3.2 — Implement `errorDetail` object formatting

In `frontend/src/lib/http.ts`, extend `errorDetail`:

- string `detail` → unchanged
- object `detail` with `reasons: string[]` → join reasons; append `required_fields` if non-empty
- fallback: `JSON.stringify` short form or status string

Keep ApiError construction unchanged otherwise.

### Task 3.3 — Disable Cost Plan actions on capability

In `ProjectControlBoard.tsx` cost-plan branch:

```ts
const costPlanCapability = project.workflow_capabilities?.capabilities.create_cost_plan;
const costPlanSupported = !costPlanCapability || costPlanCapability.status === "supported";
```

Disable Create / Refresh when `!costPlanSupported` (in addition to overlay / running / draft rules). Optionally render `costPlanCapability.reasons` above the buttons when blocked (short list).

### Task 3.4 — Run frontend tests

```bash
cd frontend
pnpm exec vitest run src/components/project/ProjectControlBoard.test.tsx src/lib/http.test.ts
```

(Create `http.test.ts` if you extracted/ covered `errorDetail` there.)

Expected: PASS.

### Task 3.5 — Commit

```bash
git add frontend/src/lib/http.ts frontend/src/components/project/ProjectControlBoard.tsx \
  frontend/src/components/project/ProjectControlBoard.test.tsx
# plus any new http test file
git commit -m "$(cat <<'EOF'
fix: block unsupported Cost Plan starts and show 409 reasons

Capability conflicts returned structured detail objects that the client
collapsed to a generic status message, and Create stayed clickable.
EOF
)"
```

---

# Segment 4 — Parity, hybrid smoke, docs cross-links

**Depends on:** Segments 0–3  
**Why:** Lock the end-to-end contract and update any tests that asserted residential-only forever.

**Files:**
- Modify as needed: `backend/tests/cost_plan/test_typed_cost_plan.py`
- Modify as needed: `backend/tests/workflows/test_create_cost_plan_hybrid_integration.py` (add industrial fixture smoke if cheap with existing mocks)
- Modify: `docs/plans/2026-07-23-industrial-warehouse-cost-plan-design.md` only if implementation drift requires a one-line correction
- Check: `frontend/src/components/project/workflow/workflowTiles.test.ts`

### Task 4.1 — Update typed capability snapshot tests

If `test_capability_matrix_publishes_all_typed_cost_actions` hardcodes residential-only `reference_coverage`, add a parallel industrial warehouse snapshot assertion or widen the residential case explicitly.

### Task 4.2 — Optional hybrid integration smoke (mocked)

Mirror an existing hybrid integration test with `building_class="industrial"` and subclasses `["warehouse"]`, asserting scaffold/result does not contain kitchen/BASIX. Prefer mocks already used in `test_create_cost_plan_hybrid_integration.py`.

### Task 4.3 — Full focused suite

```bash
cd backend
uv run pytest tests/projects/test_workflow_capabilities.py tests/sitewise/test_catalog_parity.py tests/sitewise/test_cost_plan_renderer.py tests/cost_plan/test_typed_cost_plan.py -q --tb=line
```

```bash
cd frontend
pnpm exec vitest run src/components/project/ProjectControlBoard.test.tsx src/components/project/workflow/workflowTiles.test.ts
```

Expected: PASS.

### Task 4.4 — Commit

```bash
git add -A
git commit -m "$(cat <<'EOF'
test: lock industrial warehouse Cost Plan coverage contracts
EOF
)"
```

---

# Segment 5 — Platform re-ingest + manual verification

**Depends on:** Segments 0–4 merged to the runtime environment you verify against  
**Why:** Seeds on disk are not enough; platform knowledge must be ingested into Supabase/`sitewise-platform` for the running app.

### Task 5.1 — Re-ingest platform knowledge

Use the repo’s existing platform ingest path (same process used after seed edits — check `docs/runbooks/` or ingest scripts under `backend/ingest/`). Confirm the new path appears via platform knowledge list/search tools or DB.

### Task 5.2 — Manual verify on project Industrial

On `http://localhost:5173` for project **Industrial**:

1. Cost Plan tile is Ready (not Blocked) for warehouse + NSW
2. Create cost plan starts (202) and completes without 409
3. Draft scaffold shows warehouse families; no kitchen/BASIX
4. Draft discloses structure-only / no rate pack
5. Temporarily set subclass to `manufacturing` → capability Blocked / Create disabled

### Task 5.3 — Note verification outcome

Append a short “Verified” note under the design doc or leave a PR checklist comment. Do not invent rates during manual review.

---

## Definition of Done (whole plan)

- [ ] Residential catalog leak fixed (`applies_to_classes: [residential]`)
- [ ] Industrial warehouse reference seed present and selected for `building_class=industrial`
- [ ] Capability supports NSW + warehouse/logistics only among industrial
- [ ] Hybrid scaffold branches industrial vs residential
- [ ] Frontend disables Create when unsupported and shows structured 409 reasons
- [ ] Focused backend + frontend tests green
- [ ] Platform re-ingest done; Industrial project creates a Cost Plan successfully

---

## Out of scope (do not implement in this plan)

- Other industrial subclasses, interstate, rate packs
- Catalog `applies_to_subclasses` axis
- Commercial Cost Plan coverage
- Role multi-path rendering (role collapse owns that)
- Changing tender handoff semantics
