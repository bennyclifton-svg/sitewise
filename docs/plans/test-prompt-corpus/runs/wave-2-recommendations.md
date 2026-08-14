# Wave 2 — Schedule of Recommendations

**Source:** [`wave-2-outcome-sheet.md`](wave-2-outcome-sheet.md) · **Raised:** 2026-08-12

Fourteen items, sequenced. The ordering is by *unblocking power*, not by severity: R0 makes measurement
possible, R1–R3 are the ones that change the document, R4–R9 are correctness, R10–R13 are polish and
coverage. Every item names the file it lands in and the test that proves it.

**Reading the columns.** *Defect* maps to the Wave 2 aggregated list. *Size* is engineering effort:
S ≈ under an hour, M ≈ half a day, L ≈ a day or more, XL ≈ multi-day or a data-authoring project.
*Proof* is what must be true before the item is closed — a runtime observation where the defect is a
runtime defect, not a unit test that asserts the fix in isolation.

---

## Stage 0 — Make the measurement trustworthy

Nothing below Stage 0 can be attributed to a code change until this lands. Two Wave 2 artefacts were
produced by a build that is not in the working tree.

### R0 — Isolate the workflow queue from production · `HARNESS` W2-0 · **Size S** · **Blocking**

The workflow worker runs in-process in the API ([`main.py:59`](../../../backend/app/main.py#L59)) and the
hosted `sitewise.au` deployment shares this Supabase database, so both poll `workflow_runs` and race to
claim runs. Production is on deploy `955256a1`; local is on the working tree.

Pick one:

- **Preferred** — give the worker an environment scope. Add a `workflow_worker_queue_scope` setting
  (default `production`), stamp it on the run at enqueue, and have `claim_next_run` filter on it. Local
  dev sets `dev`. Costs one column and one predicate; permanently ends cross-environment claiming.
- **Immediate** — set `workflow_worker_inproc_enabled=false` on the hosted deployment for the duration of
  corpus testing, or point local dev at a separate Supabase project.

**Proof:** queue one run locally, confirm `lock_owner` carries the dev worker id for its whole lifetime,
and confirm the produced artefact's `provenance_metadata.compiler` matches the working tree. Re-run the
two Wave 2 cost plans and confirm both report `typed`.

### R0b — Record the running build on every artefact · `HARNESS` · **Size S**

`dependency_snapshot` already carries `runtime_version` and `model_version`. Add the **git SHA and dirty
flag** of the process that generated the artefact. Wave 1 lost a day to a phantom error string, and Wave 2
lost the cost-plan comparison, both because nothing in the record says which code ran.

**Proof:** an artefact generated from a dirty tree records the SHA plus `dirty: true`.

---

## Fix log — R0 and R0b (2026-08-12)

**Both landed and are confirmed live.** Runs are now scoped to the environment
that queued them, and every artefact records the build that made it.

**R0 — queue scope.** `workflow_runs` gains a `queue_scope` column
([`046_workflow_run_queue_scope`](../../../backend/alembic/versions/046_workflow_run_queue_scope.py),
`NOT NULL DEFAULT 'production'`). `start_workflow_run` stamps
`settings.workflow_queue_scope` at enqueue; `claim_next_run` filters on it in
SQL — the predicate has to reach the database, because the claim locks one row
with `FOR UPDATE SKIP LOCKED` and a Python-side filter would still let a
foreign-scope row be locked and skipped by its rightful owner.

**Both lease sweepers are scoped too**, which is the part that is easy to miss:
`_finalize_one_expired_cancellation` and `_fail_one_exhausted_lease` run on
every claim poll, so leaving them unscoped would let a quiet dev laptop reap
production's expired runs — a worse failure than the one being fixed.

The scope also leads the worker id, so `lock_owner` reads
`dev:inproc-core:HOST:PID` and says which environment claimed a run without a
join. The 526 existing rows backfilled to `production`; one `needs_input` run
was the only non-terminal row and is not claimable, so nothing was stranded.

Local dev sets `WORKFLOW_QUEUE_SCOPE=dev` in `backend/.env`. Production keeps
the code default, so it cannot break by omission — but it is now documented in
[`DEPLOYMENT.md`](../../../DEPLOYMENT.md) Step 1, because a second environment
added later would silently share a queue.

**R0b — build identity.** New [`app/build_version.py`](../../../backend/app/build_version.py):
`BUILD_SHA` when injected (the container has no `.git`), else the working
tree's short SHA with a `-dirty` suffix when uncommitted, else `unknown`.
Resolved once per process — the code cannot change under a running interpreter.
It lands in `provenance_metadata.dependency_snapshot.build_version` alongside
`queue_scope`, for both the worker's central stamper and the cost-plan path.
`BUILD_SHA` is wired through the Dockerfile as a build arg and through the
compose env anchor.

**Runtime verification.** A real `create_project_plan` run queued through the
API against a throwaway user and project, sampling `lock_owner` for the whole
run:

| Check | Result |
|---|---|
| Run scoped to `dev` | ✅ |
| Every observed `lock_owner` is a dev worker | ✅ `dev:inproc-core:DESKTOP-H82BB8Q:23196#0` |
| Artefact records `build_version` | ✅ `192b95c5-dirty` |
| Artefact records `queue_scope` | ✅ `dev` |
| Run completed | ✅ |

That is the R0 proof condition met in full: the run never left the dev worker,
and the artefact it produced names the build that made it.

**Deliberately not done: reconciling the two cost-plan compilers.** R0 makes
the question answerable but does not answer it — that is R12, and it needs a
fresh cost-plan run now that the queue is isolated.

### R0 is one-sided until production is redeployed — found during R1

The scope predicate lives in `claim_next_run`, so **it only binds a worker that
has the new code.** Local dev now refuses production's runs. Production, still
on deploy `955256a1`, has no predicate at all and goes on claiming
**dev-scoped** runs.

This is not theoretical either. During the R1 re-run, three prompts were queued
from local dev seconds apart and split:

| Prompt | `build_version` on the artefact | Claimed by |
|---|---|---|
| 6 | `bd65695c-dirty`, `queue_scope: dev` | the dev worker |
| 14 | **null** | a worker with no R0b code — production |
| 61 | **null** | production |

The two production-claimed runs produced documents without the R1 change; the
dev-claimed one produced the document R1 was built for. **R0b is what made this
a one-query diagnosis** instead of another day of inference — a missing build
stamp is a positive identification of a foreign worker.

**Required to finish R0 — an ops action, not a code change.** Either redeploy
production so its worker gains the predicate, or set
`WORKFLOW_WORKER_INPROC_ENABLED=false` on the hosted stack for the duration of
corpus testing. **Until one of those happens, roughly two runs in three are
still executed by production and no wave result is attributable.** The migration
is already applied to the shared database, so a redeploy needs no further DB
work.

**Verification:** backend 2091 passed, 7 skipped, 0 failed. 12 new tests across
[`test_build_version.py`](../../../backend/tests/test_build_version.py) and
[`test_workflow_queue_scope.py`](../../../backend/tests/workflows/test_workflow_queue_scope.py),
covering the enqueue stamp, the SQL predicate on both the claim and the two
sweepers, the provenance fields, and every `build_version` fallback.

---

## Stage 1 — Make the document respond to the project

These three are the wave's structural finding. The band, weights and routes all resolve correctly today
and the document does not change. Fixing anything else first produces correctly-configured boilerplate.

### R1 — Give prose scope a destination · `INPUT-LOSS` W2-1 · **Size L** · **Highest leverage**

Fact retention was **8/9 where the asset register fired and 2/9, 2/10, 2/7 where it did not.** The gap is
not agent quality; it is that a taxonomy enum cannot hold "concrete cancer in the basement carpark" or
"new lifts, footbridge, accessible platforms and canopies".

Add a **`scope_narrative`** profile field: a short list of user-stated scope items in the user's own words,
alongside `work_scope` rather than replacing it — the enum keeps driving routing and consultants, the
narrative keeps the words. Wire it exactly as `budget` and `assets` were: `PROFILE_FIELDS`, patch and view
schemas, `read_profile`, the write-back, `SETUP_PROPOSAL_FIELDS` so D1 auto-applies it, and the agent
instructions. Render it in the Brief under **Inclusions**, beneath the enum labels.

Then extend the asset-register instruction beyond discrete plant: a facade, a basement slab, a lift, a roof
and a switchboard are all assets with a location, a condition and an action. Prompt 6 should produce
`{type: "Reinforced concrete structure", location: "Basement carpark", condition: "...", action: "remediate"}`.

**Proof:** re-run prompts 6, 14 and 61 and measure fact retention ≥ 6/9, ≥ 6/10, ≥ 5/7. Retention is the
metric; the field is only the mechanism.

#### Fix log — R1 (2026-08-13)

**Landed. Proven on the one run that reached the dev worker; the other two were
claimed by production and are still unmeasured** — see the R0 note above.

**New `scope_narrative` profile field.** A short list of the user's own scope
wording, alongside `work_scope` rather than replacing it: the enum keeps routing
consultants and doctrine, the narrative keeps the words. Wired exactly as
`budget` and `assets` were — `PROFILE_FIELDS`, the patch/view/create/update
schemas, `read_profile`, the write-back, `SETUP_PROPOSAL_FIELDS` so the
auto-apply path captures it without a confirmation round-trip, and the agent
instructions. Capped at 12 items of 200 characters: it exists *because* the enum
cannot hold prose, which makes it the obvious place for an agent to paste the
whole prompt, and that would push the same undifferentiated text into every
document the enum was meant to structure.

**It renders in two places.** The Brief's **Inclusions** list appends the
narrative under the enum labels, and the Description now *leads* with the
narrative — a reader recognises "concrete cancer in the basement carpark" and
does not recognise "Facade/Cladding Rectification", which is a routing key that
happens to be printable. The Description's "Site, asset, and scope details
remain not stated" clause is suppressed when scope is in fact stated; it was
printing on three Wave 2 documents whose prompts had supplied all three.

**An asset is not only plant.** The asset-register instruction was written around
mechanical plant and the agent read it literally, so a facade and a basement slab
went unrecorded. It now says so explicitly: a facade, a slab, a roof, a lift, a
switchboard, a footbridge and a canopy are assets with a location, a condition
and an action. Concrete cancer is a reinforced concrete structure at that
location with action `remediate`.

**Prompt 6, measured end to end on the dev worker:**

| | Wave 2 | After R1 |
|---|---|---|
| Fact retention | **2/9** | **7/9** — concrete cancer, spalling, basement carpark, eastern facade, 6 levels, engineer's report, $1.2m |
| Still absent | — | `1970s`, `strata` (the latter is in `complexity`, never rendered as prose) |
| Description | "Site, asset, and scope details remain not stated" | "Remediation works for apartments; 6 storeys. Scope includes Remediate concrete cancer in the basement carpark; Remediate spalling on the eastern facade" |
| Asset schedule | *(nothing to show)* | two rows — reinforced concrete structure / basement carpark / remediate, and building facade / eastern facade / remediate |
| Workflow | **hard-failed** on the apartments seed route | **completes** |

Target was ≥ 6/9. The deterministic scaffold was also rendered directly from the
stored rows for all three projects, and every narrative item appears — so the
code is confirmed for 14 and 61 even though their documents were produced
elsewhere:

```
61 → - Temporary Works | … | - New lifts | - Footbridge | - Accessible platforms
     | - Canopies | - Rail line remains operational | - Works undertaken in possessions
14 → - Second storey addition to a semi-detached house | - Rear extension
     | - Add two bedrooms and a bathroom at upper level | - Heritage conservation area
```

**What R1 does not fix, now visible rather than inferred:**

- **`work_scope` is often left empty once the narrative exists.** Prompts 6 and 14
  both came back `work_scope: []`. The instruction says to set both; the agent,
  given somewhere expressive to write, stops filling the enum. That keeps W2-3
  alive — prompt 6 still loaded no remediation doctrine — and R9 has to account
  for it rather than assume a populated enum.
- **Prompt 61 was misclassified `new`** on this run (a station *upgrade*), with
  `work_scope` filled as `substructure`/`superstructure`/`temporary_works`.
  W2-7's classification problem is untouched by R1.
- `strata` and `1970s` still never reach the document: one lives in `complexity`
  and is never rendered as prose, the other has no field at all.

**Verification:** backend 2107 passed, 7 skipped, 0 failed. 16 new tests across
[`test_profile_scope_narrative.py`](../../../backend/tests/projects/test_profile_scope_narrative.py)
and [`test_scope_narrative_rendering.py`](../../../backend/tests/sitewise/test_scope_narrative_rendering.py),
covering the field wiring, the caps, independence from `work_scope`, both render
sites, and the suppressed "not stated" claim. One existing profile-contract
expectation grew a `scope_narrative` key.

### R2 — Make the scale band change the document · `SCALE` W2-4 · **Size M**

The band resolves correctly on all five runs and produces 708–795 words from XS to L. Four of five are
below their own floor; the $120m rail project is **41% under** at 786 words against a 1330 floor.

Two parts:

1. **Enforce the floor.** [`create_pmp.py:2216`](../../../backend/app/workflows/create_pmp.py#L2216)
   computes correct bounds and logs `length | advisory (not enforced)`. Turn the under-length case into a
   retry with the advisory text fed back as the instruction — the loop already exists for other
   validations. Keep over-length advisory; over-length is not the failure mode here.
2. **Give the scaffold something to expand.** The floor cannot be met by padding boilerplate. The banded
   target must reach the section prompts with per-section word budgets, and the L-band sections that carry
   the weight (risks 0.19, compliance 0.16, procurement 0.13 on prompt 61) must be told to write
   project-specific depth, not to restate the register.

**Proof:** re-run prompts 1 and 61. Word counts land inside their bands and differ by roughly the band
ratio — approximately 700 versus approximately 1900, not 795 versus 786.

### R3 — Break the 94.7% similarity · `INPUT-LOSS` + `SCALE` · **Size M** · *depends on R1, R2*

R1 and R2 should do this on their own; this item is the **measurement**, and it is the acceptance gate for
the stage. Add a similarity check to the corpus tooling: render the current scaffold for a fixed set of
taxonomies and assert pairwise identical-line similarity below a threshold.

Wave 1 measured 94–98%, Wave 2 measured 82–95%. **Target: no pair above 70%** for projects differing in
class *and* work type *and* band.

**Proof:** `14.1 extend` versus `43.1 new` drops from 94.7% to under 70%.

---

## Stage 2 — Correctness of what the document asserts

### R4 — Resolve the design lead from discipline, not declaration order · `DISCIPLINE` W2-5 · **Size S**

[`design_lead_discipline()`](../../../backend/app/sitewise/taxonomy.py#L267) returns the first consultant
of the first selected scope — but `work_scope_items_for` filters `work_scope_options_for(work_type)`, so
the selection is silently re-ordered into **`work-scopes.json` declaration order**. The design lead is
therefore decided by an authoring sequence, not by the project. Verified directly:

```
design_lead_discipline("refurb", ["mechanical_hvac", "building_condition"])  → "Building Consultant"
design_lead_discipline("refurb", ["building_condition", "mechanical_hvac"])  → "Building Consultant"
design_lead_discipline("refurb", ["accessibility_upgrade", "live_environment_fitout", …]) → "Project Manager"
```

The result does not change when the agent's ordering changes. `building_condition` is declared before
`mechanical_hvac`; `live_environment_fitout` before `accessibility_upgrade`. Hence *"The **Building
Consultant** row is the design lead"* and *"The **Project Manager** row is the design lead"* — neither is a
design discipline. Where scope is empty it falls back to Architect, which put an architect in charge of
concrete remediation and a 2 MW electrical install.

Three changes:

1. Mark which consultants in `work-scopes.json` are **design disciplines**. Project Manager, Building
   Consultant, Commissioning Agent and Building Certifier are not; they may sit in the register but must
   never be named as the lead.
2. Rank scope items by design significance explicitly — add a `design_primacy` weight to each scope rather
   than relying on file order. Structural and services scopes outrank condition assessment and staging.
3. When no scope is selected, print **"Design lead — to be confirmed"** rather than defaulting to
   Architect. A blank is honest; an architect leading concrete remediation is a false statement in a
   client-facing document.

**Proof:** prompt 6 → Structural Engineer or "to be confirmed", never Architect. Prompt 1 → Services
Engineer (Mechanical). Prompt 61 → not the Project Manager.

### R5 — Stop printing "not stated" for facts the user stated · `REGISTER` W2-10 · **Size S**

Three of five documents open with *"Site, asset, and scope details remain not stated from the project
profile or current evidence"* against prompts that supplied all three. `Scale summary: rail_metro; scale
unresolved` and a bare `scale —` render raw enums and null artefacts into client-facing prose.

Suppress each clause when the corresponding field is populated; route every enum through its display label
before it reaches prose; drop the fragment entirely when a scale field is unresolved rather than printing
an em dash.

**Proof:** grep the rendered corpus set for `_`-cased identifiers and for "not stated" appearing against a
populated field. Zero hits.

### R6 — Fix advisory, for the third time · `WORKFLOW-LAUNCH` W2-9 · **Size M**

Advisory has never produced a graded artefact from a cold prompt across three attempts. Wave 2's failure is
new: the agent replied *"## Project setup recorded from your brief"* and `project_events` for that project
is **empty** — no proposal was ever raised. It then declined the PMP and asked the user for *"Building
class: Class 7b warehouse/distribution centre"* and *"Work type: Existing-building technical due
diligence/advisory"*, neither of which the profile accepts.

Two instruction-level changes in [`turn_context.py`](../../../backend/app/agent/turn_context.py):

1. **Never claim a write that did not happen.** "Recorded" is reserved for a state the agent can observe
   after the tool returns. If no proposal was raised, the reply must say what is missing.
2. **Ask in the taxonomy's own vocabulary.** When classification is blocked, present the valid enum values
   for the relevant class, not free prose.

Then diagnose why an unambiguous advisory prompt raised no proposal at all when four sibling prompts in
the same session raised one within 40 seconds. The prompt contains "due diligence", "before settlement",
"capex forecast" — if `advisory` is hard to reach from that, the mapping needs an explicit rule.

**Proof:** corpus prompt 11 run cold produces `industrial / logistics_ecommerce / advisory` and a PMP with
no procurement or delivery section, in one turn.

### R7 — Make FFE applicability depend on the work, not the class · `SECTION-SET` W2-8 · **Size S**

D4 works — it dropped FFE on the remediation run and rendered a real equipment schedule on the control.
It still stubs an empty finishes table onto a rail station upgrade and a rooftop solar array.

Extend the `exclude_when` conditions in
[`emphasis-profiles.json`](../../../data/taxonomy/emphasis-profiles.json): exclude the FFE Schedule where
no fitout-family scope is selected and no asset register exists, regardless of class. Infrastructure and
services-only scopes should never carry it.

**Proof:** prompts 61 and 43 render 10 sections; prompt 8 (tenancy refresh) still renders 11 with a
populated FFE schedule. That contrast is the corpus's original diagnostic.

---

## Stage 3 — Coverage: the vocabulary and the doctrine

These are data-authoring items, not code. They are the reason four runs could not have scored well even
with a perfect agent, and they get larger the further into the corpus you run.

### R8 — Author the three missing class guides · `DOCTRINE` W2-2 · **Size XL** · *the biggest single gap*

`data/seed/` has class guides for `residential`, `commercial` and `industrial`.
**`institution`, `mixed` and `infrastructure` have none.** Both Wave 2 infrastructure runs loaded zero
class doctrine and cited only `ncc-reference-guide#compliance-pathways-and-documentation` — on a rail
station, where the NCC is barely the governing instrument.

This is **24 of 67 corpus prompts**: institution 44–52, mixed 53–59, infrastructure 60–67. Sequence by
corpus weight:

1. `infrastructure-construction-guide.md` — 8 prompts. Authority interfaces, possessions and outages, rail
   and road safety accreditation, network operator approvals, linear works, commissioning into a live
   network.
2. `institution-construction-guide.md` — 9 prompts. Public procurement and probity, operating-calendar
   constraints (terms, clinical hours), child protection and security clearance, stakeholder governance,
   accessibility beyond minimum.
3. `mixed-use-construction-guide.md` — 7 prompts. Multiple classifications in one structure, fire and
   acoustic separation between uses, stratification and separate services, staged handover by use.

**Proof:** `select_seed_knowledge_for_taxonomy` returns a class guide for all six classes across every
work type. Re-run prompt 61 and find possessions and rail safety accreditation in the output.

### R9 — Make the doctrine you already have reachable · `DOCTRINE` W2-3 · **Size M**

Two guides exist, apply exactly, and could not be reached:

- **`building-remediation-rectification-guide.md`** requires
  `applies_to_work_scopes: [waterproofing_rectification, fire_safety_orders, facade_cladding]`. Prompt 6
  set no scope, so remediation doctrine did not load on a remediation project. Measured: adding the scope
  takes section refs from **5 to 9** and pulls in the remediation cost reference. Make the class guide load
  on `work_type: remediation` alone, with the scope list narrowing sections rather than gating the file.
- **`renovation-guide.md`** is `status: legacy-retained`, `superseded_by: residential-construction-guide.md`,
  `loaded_by: "archetype: renovation"` — unreachable from the taxonomy router. Its summary is heritage
  checks, dilapidation and neighbour management, latent conditions, BASIX for additions, live-occupancy
  staging and old-to-new tie-in: **precisely prompt 14**. Either promote it to a work-type overlay for
  `refurb`/`extend`, or move its content into `residential-construction-guide.md`. Do not leave the right
  content behind a legacy flag.

**Proof:** prompt 6 loads the remediation guide with `work_scope: []`. Prompt 14 loads heritage and
old-to-new tie-in doctrine.

### R10 — Close the three vocabulary holes · `TAXONOMY-GAP` W2-6 · **Size M**

One wave found three. All three are data changes with a validation and a UI consequence.

| Hole | Add | Prompts affected |
|---|---|---|
| `remediation` has no structural-repair scope — concrete cancer is inexpressible | `structural_remediation` to `work-scopes.json` under `remediation`, consultants led by Structural Engineer | 6, and most strata remediation work |
| `extend` scope is interface-only (`structural_tie_in`, `weatherproofing_tie_in`, `services_connections`, `staged_occupation`) — a new kitchen, bathroom and bedrooms map to nothing | the fitout-family scopes already defined under `refurb` — `partitions_walls`, `joinery`, `flooring`, `hydraulic_plumbing` | 13, 14, 16, 45 |
| **No heritage dimension.** Nine universal dimensions and none covers built heritage; `environmental_sensitivity: aboriginal_heritage` is a different thing | `heritage_status` to `complexity-dimensions.json`: `none` / `conservation_area` / `local_heritage_item` / `state_heritage_register`, with a risk-flag modifier | 14, 59, and any inner-Sydney work |

**Proof:** each of prompts 6, 14 and 59 can be fully expressed in the profile without prose spillover.

### R11 — Let an energy retrofit be classified correctly · `CLASSIFY` W2-7 · **Size M**

Prompt 43 was classified `infrastructure / energy_renewables / new` — wrong on all three axes — and the
agent's choice was rational. `capacity_mw` and `battery_storage_mwh` exist **only** under
`infrastructure / energy_renewables`; the industrial doctrine exists **only** under `industrial`. The
taxonomy forces a choice between the right class and the right scale metrics, and the misclassification
then cost the project its cost plan.

Add `capacity_mw` and `battery_storage_mwh` as scale fields available to `industrial` (and `commercial`)
where an energy scope is selected, and add an `energy_generation_storage` work scope under `extend` and
`refurb` with electrical and structural consultants attached.

**Proof:** prompt 43 classifies as `industrial / other / extend`, retains 2 MW and 1 MWh, loads
`industrial-construction-guide.md`, and produces a cost plan.

### R12 — Put costs in the cost plan · `COST` W2-11 · **Size M** · *after R0*

Across two cost plans, **0 of 47 lines carry a figure.** The typed compiler additionally drops the budget
entirely — `$750k` appears nowhere in the 14.1 plan — and produces 548 words against the legacy
compiler's 2,087 on the same day.

1. Confirm which compiler is intended (R0 makes this answerable), then bring the typed path back to parity
   on the things legacy did well: the stated budget echoed and reconciled, ex-GST discipline stated, and a
   short control-decision narrative above the table.
2. Apportion the stated budget across the cost codes as an **indicative allocation, labelled as such**.
   "TBC" on every line of a plan the user asked for against a stated budget is a refusal dressed as an
   artefact.
3. Read the asset register. `R22`, `Actron` and `Pioneer` are in the 1.3 profile and absent from its cost
   plan, which prices "New mechanical plant" without naming the plant.

**Proof:** prompt 1's cost plan carries an indicative split of $180k across its 22 codes and names the
Actron replacement.

#### Fix log — R12 (2026-08-14)

**Landed and unit-tested. Live prompt-1 cost-plan artefact not re-run** — same live-run skip as prompt 61.

The intended compiler is **typed**. `run_create_cost_plan_workflow` always calls
`run_create_cost_plan_typed`; the hybrid flag defaults true. The legacy markdown
report path is not revived.

**Stated budget is echoed and split.** Create-time allocation reads the pack
ceiling, then Cost Plan context, then `project_budget`. When any Construction
or PC-allowance row is still TBC, the scaffold round-trips through
`build_adopted_budget_forecast` with `source_ref="project_profile"`. Typed
markdown always states **ex GST**; when allocation ran it adds Control decision
and Reconciliation, labelled **indicative allocation**.

**Assets land on the construction row they belong to.** Mechanical plant
(Pioneer / Actron / R22) is appended to the Mechanical / building-services
label. Benchmark `%` lookup still uses the undecorated original label.

**Protected rows stay protected.** `_typed_cost_items` maps Approved/Evidenced
to status `"confirmed"`. Forecast treated that as unprotected until
`"confirmed"` was added to `PROTECTED_STATUS_TOKENS`. Without that, a TBC
envelope triggered a re-split that overwrote evidenced fees and contingency
(Harrison Clarke hybrid). Confirmed + TBC remains allocatable because
protection still requires a budget figure.

Commercial fitout PC sits under `"Client-direct and landlord works"`, not
`"PC allowances"`, so a $180k envelope is Construction-only. That is the
prompt-1 shape.

**Proof tests (59 passed):**
[`test_typed_compiler_allocates_stated_budget_and_names_actron`](../../../backend/tests/workflows/test_create_cost_plan.py)
splits $180,000 across envelope rows, names Actron/Pioneer, and prints ex GST
plus the indicative-allocation label.
[`test_mechanical_assets_are_named_on_the_mechanical_row`](../../../backend/tests/sitewise/test_cost_plan_lines.py)
puts Pioneer, Actron, R22 and the service-centre location on the Mechanical
services line. Hybrid integration (Harrison Clarke fees, industrial warehouse
smoke, progressive batches) stayed green after the confirmed-status fix.

Live prompt-1 artefact remains the remaining proof gate.

### R13 — Corpus and harness maintenance · **Size S**

- **Run prompt 40.** It was skipped, so `industrial` was untested in the wave and the ISO 14644 /
  validation-before-handover checkpoints are unexercised.
- **Add "Need a PMP" to corpus prompt 3**, still outstanding from Wave 1.
- **Add `TAXONOMY-GAP` and `HARNESS` to the corpus's defect-category list.** Both were needed this wave
  and neither is expressible in the original eight.
- **Add a `Build SHA` row to the recording template**, once R0b lands.

#### Fix log — R13 (2026-08-14)

**Corpus and template landed. Live prompt 40 not run** — same live-run skip as
prompts 61 and 1.

In [`sitewise-test-prompt-corpus.md`](../sitewise-test-prompt-corpus.md):

- Prompt 3 now ends **Need a PMP.**
- Wave 2 note: do not skip prompt **40** (industrial / ISO 14644 /
  validation-before-handover).
- Recording template has a **Build SHA** row.
- Defect categories now include `WORKFLOW-LAUNCH`, `TAXONOMY-GAP`, `HARNESS`,
  and `COST`.

Live prompt 40 remains the remaining proof gate for industrial coverage.

---

## Sequencing

```
R0   isolate the queue ─────────────────────────► everything else is measurable
 │
 ├─ Stage 1  (the document)      R1 scope narrative ─┬─► R3 similarity gate
 │                               R2 band enforcement ┘
 │
 ├─ Stage 2  (correctness)       R4 design lead
 │                               R5 register / enum leakage
 │                               R6 advisory
 │                               R7 FFE applicability
 │
 └─ Stage 3  (coverage)          R8 three class guides   ← largest, start authoring in parallel
                                 R9 unreachable doctrine
                                 R10 vocabulary holes
                                 R11 energy retrofit classification
                                 R12 cost plan
                                 R13 corpus maintenance
```

**R8 is XL and independent of all the code work** — begin authoring it in parallel with Stage 1 rather
than after Stage 2, or it will gate Waves 4 and 5.

---

## Re-test set

**After Stage 1 (R0–R3)** — re-run **6, 14, 61**. These are the three that scored 0 on both retention and
scale. The measurements that must move:

| Metric | Wave 2 | Target |
|---|---|---|
| Fact retention, prompt 6 | 2/9 | ≥ 6/9 |
| Fact retention, prompt 14 | 2/10 | ≥ 6/10 |
| Fact retention, prompt 61 | 2/7 | ≥ 5/7 |
| Words, prompt 61 (band L) | 786 | 1330–2755 |
| Similarity, 14 vs 43 | 94.7% | < 70% |

**After Stage 2 (R4–R7)** — add **11** and **40**, the two prompts this wave did not grade. Prompt 11 is
the advisory test that has now failed three times; prompt 40 has never run.

**After Stage 3** — Wave 3 (scale proportionality: 5, 26, 31, 35) becomes meaningful for the first time,
because it measures exactly what R2 fixes. Do not run Wave 3 before R2 lands; it will only re-measure
W2-4.
