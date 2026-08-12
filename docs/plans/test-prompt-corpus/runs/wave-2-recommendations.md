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

### R13 — Corpus and harness maintenance · **Size S**

- **Run prompt 40.** It was skipped, so `industrial` was untested in the wave and the ISO 14644 /
  validation-before-handover checkpoints are unexercised.
- **Add "Need a PMP" to corpus prompt 3**, still outstanding from Wave 1.
- **Add `TAXONOMY-GAP` and `HARNESS` to the corpus's defect-category list.** Both were needed this wave
  and neither is expressible in the original eight.
- **Add a `Build SHA` row to the recording template**, once R0b lands.

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
