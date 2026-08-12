# Wave 2 Test Outcome Sheet

**Run date:** 2026-08-12 (12:36–12:56 UTC) · **Prompts run:** corpus 6, 11, 14, 43, 61 (+ prompt 1 re-run as control) · **Graded:** 2026-08-12

> **Which prompts were run.** Wave 2 is defined as prompts **6, 11, 14, 40, 43, 61** — one of each work
> type. **Prompt 40 (cleanroom · industrial / cleanroom / refurb · M) was never created**; no project by
> that name or subclass exists in the database. So the wave tested **four** work types, not five:
> remediation (6), advisory (11), extend (14), new (43, by misclassification) and refurb (61).
> A sixth project, `1.3 Mechanical plant replacement`, re-ran corpus prompt 1 immediately before the wave
> and is graded here as the **control** — it is the only run where the profile was fully populated.

**Grading provenance.** C1–C4, C6 and C8 are mechanically verified against the database, the generation
manifest and the artefact text — reproducible, no judgement. C5, C7 and C9 are marked **[J]** and are the
agent's reading, not a domain verdict; override freely.

---

## ⚠️ Test-validity warning — read before trusting any number below

**Two different code versions executed Wave 2 artefacts.** The `1.3` cost plan records
`compiler: "legacy"` / `runtime_version: clerk-sitewise-create-cost-plan`; the `14.1` cost plan twelve
minutes later records `compiler: "typed"` / `clerk-sitewise-create-cost-plan-typed`. The `legacy` branch
**does not exist in the working tree** — `git show HEAD:backend/app/workflows/create_cost_plan.py` has it,
the uncommitted file does not (`runtime_name = RUNTIME_TYPED_NAME` unconditionally at
[`create_cost_plan.py:1560`](../../../backend/app/workflows/create_cost_plan.py#L1560)).

The mechanism is now identified. The workflow worker runs **in-process inside the API**
([`main.py:59`](../../../backend/app/main.py#L59) `start_inprocess_workflow_worker`), and the hosted
`sitewise.au` deployment shares this Supabase database. **Both the local dev backend and the deployed
production container poll the same `workflow_runs` queue and race to claim runs.** Production is on
committed code (deploy `955256a1`, 2026-08-11); local is on the working tree. Which one executes a given
run is a coin toss.

This is the same phenomenon Wave 1 recorded as *"D7(a) has not taken effect in the running system"* —
prompt 10 failing on a seed path string that no longer existed in the source tree. It was not a stale
worker; it was **the production container executing dev-queued work**.

**Consequence:** every measurement in this sheet is attributable to *a* SiteWise build, not necessarily to
the build in the working tree. The PMP findings are consistent across all five runs and the PMP path was
untouched between 22:21 local (last edit to `pmp_renderer.py` / `taxonomy.py`) and the first run at 22:37,
so they are safe. The **cost-plan findings are not comparable to each other** and should be re-run after
the queue is isolated. Fixing this is recommendation R0 and it precedes everything else.

---

## What was produced

| # | Prompt | Project | Class / subclass / work type | Band | PMP | Cost plan |
|---|---|---|---|---|---|---|
| 1 | Mechanical plant replacement *(control)* | `1.3 Mechanical plant replacement` | commercial / office / refurb | XS | ✅ v1 | ✅ v1 *(legacy compiler)* |
| 6 | Remedial concrete and facade | `6.1 Remedial concrete and facade` | residential / apartments / remediation | S | ✅ v1 | — not requested |
| 11 | Due diligence advisory | `11. 1 Due diligence advisory` | **none — profile empty** | — | ❌ **refused** | ❌ |
| 14 | House, extension and addition | `14.1 House, extension and addition` | residential / house / extend | S | ✅ v1 | ✅ v1 *(typed compiler)* |
| 40 | Cleanroom | — | — | — | ❌ **never run** | — |
| 43 | Solar and battery on existing site | `43.1 Industrial other — solar…` | **infrastructure / energy_renewables / new** | M | ✅ v1 | ❌ **refused** |
| 61 | Rail station | `61. Rail station` | infrastructure / rail_metro / refurb | L | ✅ v1 | — not requested |

**Five PMPs from six prompts.** Launch reliability is materially better than Wave 1's ~50%: four of five
attempted PMPs queued and completed on `attempt=1`, no snapshot conflicts, no seed-route hard failures.
The one failure (prompt 11) is a *refusal*, not a crash — a different and more tractable problem.

---

## The headline measurement: work type does not change the document

Wave 2's question was **"does work type actually change anything?"** The answer is: it changes the
noun in three sentences and the section weights, and nothing else.

| Comparison | Identical lines |
|---|---|
| 14.1 extend vs 43.1 new | **94.7%** |
| 6.1 remediation vs 14.1 extend | 93.8% |
| 6.1 remediation vs 43.1 new | 92.1% |
| 1.3 refurb vs 6.1 remediation | 86.7% |
| 6.1 remediation vs 61 refurb | 82.5% |

A **$750k heritage-conservation-area second-storey addition in Newtown** and a **$4m 2MW rooftop solar and
battery retrofit on a live distribution centre** are **94.7% the same document.** Different work type,
different class, different scale band, different everything — and the diff is class/subclass noun
substitution plus one FFE row.

Wave 1 measured 94–98%. Wave 2 measures 82–95%. The spread widened slightly; the documents did not
diverge.

### Where the wave separates cleanly into two groups

The one run that differs is the control, and the reason is measurable:

| | `work_scope` captured | `assets` captured | Fact retention |
|---|---|---|---|
| **1.3** control | ✅ 2 items | ✅ 1 row | **8 / 9** |
| 61 rail | ✅ 3 items | ✗ | 2 / 7 |
| 43.1 solar | ✗ | ✗ | 4 / 6 *(via scale fields)* |
| 6.1 remediation | ✗ | ✗ | **2 / 9** |
| 14.1 extension | ✗ | ✗ | **2 / 10** |

**The asset register is the whole difference.** Prompt 1 retains R22, Actron, 30 kW, 30 years, the service
centre and the western office because they land in an `assets` row that renders as an equipment schedule.
Every other run had no asset register written, and every fact in the prompt was discarded before
generation. `work_scope` alone is not enough — prompt 61 captured three scope items and still lost lifts,
footbridge, platforms, canopies and possessions, because those are prose, and `work_scope` is an enum.

---

## Per-run sheets

Scores: **0** = fail · **1** = partial · **2** = pass · **n/a** = no artefact to grade.

### Control — Prompt 1, Mechanical plant replacement (`1.3`)

Included because it is the only well-formed profile in the wave and it sets the achievable ceiling.

| Field | |
|---|---|
| Expected | commercial / office / refurb · XS |
| Actual | commercial / office / refurb · **band XS resolved** |
| C1 Classification | **2** |
| C2 Input retention | **2** — 8/9. `R22`, `Actron`, `30kW`, `30 years`, `$180k`, `service centre`, `western office`, count 2 all present. Only `Pioneer` is missing from the body (it is in the stored profile) |
| C3 Section applicability | **2** — FFE Schedule renders as the **equipment schedule**: `\| Split ducted air conditioning system \| Service centre and western office \| 2 \| 30 kW each \| Replace \| 30 years old; Replace with Actron…; Existing systems remain on R22 \|` |
| C4 Section absence | **1** — commissioning is implied by scope, but no refrigerant-handling obligation, no shutdown/out-of-hours window, no electrical capacity check, no asbestos-in-old-plant check |
| C5 Consultant **[J]** | **1** — Services Engineer (Mechanical) is in the register, but the design lead is **"Building Consultant"** — see D3′ below |
| C6 Scale | **2** — 795 words against XS bounds 489–1015. The only run inside its own band |
| C7 Doctrine **[J]** | **1** — `commercial-construction-guide` loaded, but so is `nsw-commercial-fitout-cost-breakdown-reference` on an R22 plant swap (Wave 1's D6 complaint, unchanged), and no mechanical-services guide |
| C8 Invention | **2** — nothing asserted that the user did not supply |
| C9 Register **[J]** | **1** — genuinely usable as a starting draft. `scale —` still renders a bare em dash in the Description |
| **Categories** | `DOCTRINE`, `DISCIPLINE` |

### Run 1 — Prompt 6, Remedial concrete and facade (`6.1`)

| Field | |
|---|---|
| Expected | residential / apartments / remediation · S |
| Actual | residential / apartments / remediation · band S |
| C1 Classification | **2** |
| C2 Input retention | **0** — 2/9. Absent: `concrete cancer`, `spalling`, `basement carpark`, `eastern facade`, `1970s`, `strata`, `engineer's report`. Present: 6 levels (as `storeys 6`), the budget string |
| C3 Section applicability | **2** — the **only** run to correctly drop the FFE Schedule (`ffe-schedule` weight 0.0). D4 working as designed |
| C4 Section absence | **0** — no investigation-before-scope-lock, no provisional sums for unknown extent, no resident access / parking loss, no strata levy or funding path, no access/scaffold strategy. Risk register is three generic rows |
| C5 Consultant **[J]** | **0** — Architect is the design lead **and the only row**. A structural engineer leads concrete remediation; none appears |
| C6 Scale | **1** — band S resolved, but 738 words against a 770 floor, and indistinguishable in weight from the XS control |
| C7 Doctrine **[J]** | **0** — `building-remediation-rectification-guide.md` **not loaded**. 6 seeds, 5 section refs. Measured counterfactual: with `work_scope: [facade_cladding]` the router returns the remediation guide **and** `nsw-building-remediation-cost-breakdown-reference`, and section refs rise 5 → **9** |
| C8 Invention | **1** — no invented technical facts, but the Description asserts *"Site, asset, and scope details remain not stated"* against a prompt that supplied all three, and the chat claimed *"I've recorded the project setup… Scope described: concrete cancer in the basement carpark and spalling to the eastern facade"* while writing `work_scope: []` |
| C9 Register **[J]** | **0** — a remediation PMP that never says "concrete" or "facade" |
| **Categories** | `INPUT-LOSS`, `DOCTRINE`, `DISCIPLINE`, `SCALE`, `TAXONOMY-GAP`, `REGISTER` |

**Taxonomy gap found.** `remediation` offers exactly four work-scope values —
`contamination_remediation`, `waterproofing_rectification`, `fire_safety_orders`, `facade_cladding`.
`facade_cladding` covers the spalling; **there is no value for structural concrete repair**, so "concrete
cancer in the basement carpark" — the primary scope — cannot be expressed even by a perfect agent.

### Run 2 — Prompt 11, Due diligence advisory (`11.1`)

| Field | |
|---|---|
| Expected | industrial / logistics_ecommerce / advisory · S |
| Actual | **nothing recorded.** `building_class = NULL`, `work_type = NULL`, `profile_revision = 1`, **0 project events**, 0 workflow runs, 0 artefacts |
| C1 Classification | **0** — no classification attempted on an unambiguous prompt |
| C2–C7, C9 | **n/a** |
| C8 Invention | **0** — the reply opens *"## Project setup recorded from your brief"* and lists eight recorded attributes. **Nothing was recorded.** `project_events` for this project is empty; no proposal was ever raised. This is a false claim of action, and it is the most serious C8 failure across both waves |
| **Blocker** | On `create pmp`: *"I can't create the Project Management Plan yet because the project profile is missing: Building class, Work type."* It then asked the user to supply them **in vocabulary the profile cannot accept** — *"Building class: Class 7b warehouse/distribution centre"*, *"Work type: Existing-building technical due diligence/advisory"*. The valid values are `industrial` and `advisory` |
| **Categories** | `WORKFLOW-LAUNCH`, `CLASSIFY`, `INVENT` |

The prose answer itself was strong — a four-part DD workstream, capex horizons, deal-breaker review. The
chat layer understood the project completely and wrote none of it down. **Advisory remains the untested
work type**: Wave 1 prompt 10 died on a seed route, Wave 1b prompt 10 hard-failed, Wave 2 prompt 11 never
classified. Advisory has still never produced a graded artefact from a cold prompt.

### Run 3 — Prompt 14, House extension and addition (`14.1`)

| Field | |
|---|---|
| Expected | residential / house / extend · S |
| Actual | residential / house / extend · band S |
| C1 Classification | **2** |
| C2 Input retention | **0** — 2/10. Absent: `second storey`, `rear extension`, `semi`, `Newtown`, **`heritage conservation area`**, `bathroom`, `kitchen`, `living elsewhere`. Present: 2 beds (`bedrooms 2`), the budget string |
| C3 Section applicability | **1** — FFE Schedule renders the empty `TBC — record finishes, fixtures and equipment selections` stub. Defensible for a kitchen-and-bathroom job; nothing populates it |
| C4 Section absence | **0** — **all five corpus checkpoints missing**: heritage referral and conservation-area controls, structural adequacy of the existing dwelling, party wall / adjoining owner, existing-to-new interface, excavation near neighbours |
| C5 Consultant **[J]** | **1** — Architect leads, which is right for this job, but it is the only row. No structural engineer, no heritage consultant. *(The cost plan names structural, geotech, surveyor and BASIX — the PMP does not.)* |
| C6 Scale | **1** — band S resolved; 708 words against a 770 floor |
| C7 Doctrine **[J]** | **0** — `residential-construction-guide` loaded. [`renovation-guide.md`](../../../data/seed/renovation-guide.md) — whose summary reads *"due diligence package, latent conditions, dilapidation and neighbour management, structural intervention, BASIX for additions, **heritage checks**, live-occupancy staging and old-to-new tie-in risks"*, i.e. this exact project — is `status: legacy-retained`, `loaded_by: "archetype: renovation"`, and is unreachable from the taxonomy router. Measured: work_scope makes no difference to this route (6 section refs either way) |
| C8 Invention | **1** — `operational_constraints: vacant` is correct here. Description again claims scope "not stated" |
| C9 Register **[J]** | **0** — heritage is the governing constraint and the document does not contain the word |
| **Categories** | `INPUT-LOSS`, `SECTION-SET`, `DOCTRINE`, `TAXONOMY-GAP`, `REGISTER` |

**Two more gaps found.**
1. **No heritage complexity dimension exists.** The nine universal dimensions are planning,
   procurement_route, contamination_level, access_constraints, operational_constraints,
   stakeholder_complexity, environmental_sensitivity, bushfire_exposure, flood_exposure. The nearest
   value is `environmental_sensitivity: aboriginal_heritage`, which is a different thing. Built-heritage
   and conservation-area status have **nowhere to land** — and they drive prompts 14 and 59.
2. **`extend` work-scope vocabulary is interface-only** — `structural_tie_in`, `weatherproofing_tie_in`,
   `services_connections`, `staged_occupation`. "Adding 2 beds and a bathroom, opening the rear to a new
   kitchen and living" maps to none of them. The agent's own proposal said *"Scope: … kitchen/living
   fitout"* and then wrote `work_scope: []`, because there was no value to write.

**Also a behavioural regression:** this run required a confirmation round-trip (*"Please confirm these
profile details so I can queue the documents"*) before anything happened. Runs 1.3 and 61 auto-applied in
a single turn. The auto-apply rule fires inconsistently across runs with equally explicit prompts.

### Run 4 — Prompt 40, Cleanroom conversion

**Not run.** No project exists. The one Wave 2 prompt that would have tested a heavily-regulated
industrial refurb (ISO 14644, validation before handover, existing-services capacity, vibration criteria)
was skipped, so `industrial` class was not exercised at all in this wave.

### Run 5 — Prompt 43, Solar and battery on an existing site (`43.1`)

| Field | |
|---|---|
| Expected | industrial / other / **extend** · M |
| Actual | **infrastructure / energy_renewables / new** — wrong on all three axes |
| C1 Classification | **0** |
| C2 Input retention | **1** — 4/6. `2 MW` and `1 MWh` survive as `capacity_mw` / `battery_storage_mwh` scale fields and render in the Brief. **`rooftop` and `existing distribution centre` are lost entirely** — the host building disappears from the document |
| C3 Section applicability | **0** — FFE Schedule stub on a solar and battery installation; an NCC DtS/performance pathway row on an infrastructure asset |
| C4 Section absence | **0** — no roof structural capacity, **no grid connection or network approval** (the actual critical path), no DC isolation and fire strategy, no detail on working over live operations, no metering and tariff |
| C5 Consultant **[J]** | **0** — Architect leads a 2 MW electrical installation. No electrical engineer, no structural engineer |
| C6 Scale | **1** — band M resolved (floor 1050); 779 words, **26% under** |
| C7 Doctrine **[J]** | **0** — **zero class doctrine loaded.** Measured counterfactual: classified as `industrial / other / extend` the router returns `industrial-construction-guide.md` and **10** section refs against the 8 actually loaded |
| C8 Invention | **1** — *"New infrastructure project… Site, asset, and scope details remain not stated"* for a retrofit onto a named existing asset. `work_type: new` is itself an invented framing of an addition |
| C9 Register **[J]** | **0** |
| **Categories** | `CLASSIFY`, `SECTION-SET`, `DISCIPLINE`, `DOCTRINE`, `INPUT-LOSS`, `TAXONOMY-GAP` |

**The misclassification is partly the taxonomy's fault, and that matters for the fix.** The agent chose
`infrastructure / energy_renewables` because that is the **only** place `capacity_mw` and
`battery_storage_mwh` exist as scale fields — and it used them. Choosing the corpus-expected
`industrial / other / extend` would have gained the industrial guide and lost the only fields that can
express 2 MW and 1 MWh. The taxonomy currently forces a choice between the right class and the right
scale metrics for any energy retrofit onto an existing building.

**Downstream consequence:** the cost plan was **refused** — *"the Cost Plan workflow supports selected
building-project reference families, not infrastructure energy/renewables projects."* One classification
error removed an entire artefact. The refusal message is at least honest and well-worded.

### Run 6 — Prompt 61, Rail station upgrade (`61`)

| Field | |
|---|---|
| Expected | infrastructure / rail_metro / refurb · L |
| Actual | infrastructure / rail_metro / refurb · band L |
| C1 Classification | **2** |
| C2 Input retention | **0** — 2/7. Absent: `lifts`, `footbridge`, `platforms`, `canopies`, **`possessions`**. Present: the budget, and "operational" via the live-environment flag. The three captured scope items render as generic labels — "Live Environment Fitout", "Accessibility Upgrade" |
| C3 Section applicability | **0** — FFE Schedule stub on a station upgrade |
| C4 Section absence | **0** — no track possessions, no rail safety accreditation or worker competency, no electrical isolation near live overhead, no DSAPT, no rail authority interface. `authority_interfaces: critical_network` produced one SOCI Act risk row — the only rail-adjacent content in the document, and SOCI is not the governing instrument for a station accessibility upgrade |
| C5 Consultant **[J]** | **0** — *"The **Project Manager** row is the design lead"*. A PM is not a design discipline. Register: PM, Services Engineer, Commissioning Agent, Access Consultant, Building Certifier. Access Consultant is correct; there is no structural or civil engineer for a footbridge and two lift shafts, and no rail systems engineer |
| C6 Scale | **0** — band L resolved (floor 1330); **786 words, 41% under**, and the same weight as the $180k plant swap. The scale dimension exists and produces no visible effect |
| C7 Doctrine **[J]** | **0** — 7 seeds, all cross-cutting; only NCC visible in output. **No infrastructure doctrine exists anywhere in `data/seed/`** |
| C8 Invention | **1** — `Scale summary: rail_metro; scale unresolved` and `scale —` render raw enums and a bare em dash into client-facing text |
| C9 Register **[J]** | **0** — this document could not be sent to a rail authority |
| **Categories** | `INPUT-LOSS`, `SECTION-SET`, `DISCIPLINE`, `DOCTRINE`, `SCALE`, `REGISTER` |

---

## Cost plans

Two produced, by two different compilers, and they are not comparable — see the validity warning.

| | `1.3` (legacy compiler) | `14.1` (typed compiler) |
|---|---|---|
| Words | **2,087** | **548** |
| Rows | 22 | 25 |
| Budget referenced | ✅ `$180,000` ×4 | ❌ **`$750k` appears nowhere** |
| GST discipline | ✅ 12 mentions, ex-GST stated | ❌ none |
| Narrative / control decision | ✅ full section, procurement gate advice | ❌ none — bare table |
| Priced lines | **0 of 22 — every value TBC** | **0 of 25 — every value TBC** |
| Trade-specific codes | ✅ plant removal, ductwork, controls/BMS, TAB commissioning | ✅ old-to-new weatherproofing, existing-structure repair, kitchen/bathrooms PC |
| Asset register read | ❌ `R22`, `Actron`, `Pioneer` absent despite being in the profile | n/a |

Both cost-code structures are genuinely good and trade-appropriate. Two problems sit on top:

1. **No cost plan contains any cost.** 100% TBC on both. This looks deliberate (`draft_mode:
   platform_seeded`, *"not project cost evidence in this draft mode"*), and the discipline is defensible —
   but a PM who states a budget and receives a 25-row table of TBCs has not received a cost plan. At
   minimum the stated budget should be apportioned across the codes as an indicative, clearly-labelled
   allocation.
2. **The typed compiler drops the budget entirely** and produces a quarter of the content. If typed is the
   intended future path, it has regressed against what legacy produced on the same day.

---

## Aggregated defect list

Ordered by leverage. Counts are out of the five graded corpus runs (control excluded unless noted).

| ID | Category | Defect | Count | Repo area |
|---|---|---|---|---|
| **W2-0** | `HARNESS` | **Dev and production share one workflow queue.** The worker is in-process ([`main.py:59`](../../../backend/app/main.py#L59)) and the hosted deployment polls the same Supabase `workflow_runs` table. Two Wave 2 cost plans ran two different compilers, one of which exists only in committed code. Wave 1's "D7(a) has not taken effect" mystery has the same cause. **No wave result is attributable until this is isolated** | wave-wide | `workflow_worker.py`, deployment config |
| **W2-1** | `INPUT-LOSS` | **Prose scope has no destination.** `work_scope` is an enum and `assets` is only written when the agent recognises discrete plant. Everything else — "concrete cancer in the basement carpark", "second storey addition to a semi in Newtown", "new lifts, footbridge, canopies", "rooftop, on an existing DC" — is acknowledged in chat and discarded before generation. Retention 2/9, 2/10, 2/7, 4/6 where absent; **8/9 where the asset register fired** | 4/5 | profile schema; `SETUP_PROPOSAL_FIELDS`; agent instructions |
| **W2-2** | `DOCTRINE` | **Three of six building classes have no class guide.** `data/seed/` has `residential-`, `commercial-` and `industrial-construction-guide.md`. **`institution`, `mixed` and `infrastructure` have none** — that is corpus prompts 44–52, 53–59 and 60–67, i.e. **24 of 67 prompts**, and both Wave 2 infrastructure runs loaded zero class doctrine | 2/5 | `data/seed/` |
| **W2-3** | `DOCTRINE` | **Right doctrine exists and is unreachable.** `building-remediation-rectification-guide.md` requires a work scope the agent did not set (measured: 5 → 9 section refs when it is set). `renovation-guide.md` — heritage checks, dilapidation, latent conditions, old-to-new tie-in — is `status: legacy-retained` and routed only by legacy archetype, so the heritage extension could never reach it | 2/5 | `seed_routing.py`; seed frontmatter |
| **W2-4** | `SCALE` | **The band resolves and changes nothing.** Bands XS/S/M/L all resolved correctly from budget text. Word counts: 795 (XS), 738 (S), 708 (S), 779 (M), **786 (L)**. Four of five are **below their own band floor**; the L project is 41% under. Length is `advisory (not enforced)` at [`create_pmp.py:2216`](../../../backend/app/workflows/create_pmp.py#L2216), so nothing retries or fails | 4/5 | `create_pmp.py` length loop; scaffold expansion |
| **W2-5** | `DISCIPLINE` | **Design lead is decided by JSON declaration order and picks non-design roles.** [`design_lead_discipline()`](../../../backend/app/sitewise/taxonomy.py#L267) returns the first consultant of the first selected scope, but `work_scope_items_for` re-orders the selection into **`work-scopes.json` declaration order** — so the answer is invariant to what the agent wrote and is decided by an authoring sequence that was never meant to encode design primacy. Verified: `design_lead_discipline("refurb", ["mechanical_hvac","building_condition"])` and the reverse both return **"Building Consultant"**, because `building_condition` is declared first. Result: *"The Building Consultant row is the design lead"* (1.3) and *"The Project Manager row is the design lead"* (61, from `live_environment_fitout`). Where scope is empty it falls back to Architect — leading concrete remediation (6.1) and a 2 MW electrical install (43.1) | 4/5 + control | [`taxonomy.py:267`](../../../backend/app/sitewise/taxonomy.py#L267); `work-scopes.json` ordering |
| **W2-6** | `TAXONOMY-GAP` | **Three vocabulary holes found in one wave.** (a) `remediation` has no structural-repair scope — concrete cancer is inexpressible; (b) `extend` scope is interface-only — a new kitchen, bathroom and bedrooms map to nothing; (c) **no heritage or conservation-area complexity dimension exists** in the nine universal dimensions | 3/5 | `work-scopes.json`, `complexity-dimensions.json` |
| **W2-7** | `CLASSIFY` | **Energy retrofit onto an existing building cannot be classified correctly.** `capacity_mw` / `battery_storage_mwh` exist only under `infrastructure / energy_renewables`; the industrial doctrine exists only under `industrial`. Prompt 43 had to lose one to get the other, and the misclassification also cost it the cost plan | 1/5 | `building-classes.json` scale fields |
| **W2-8** | `SECTION-SET` | **FFE Schedule still renders empty on 3 of 5.** D4 applicability correctly dropped it on the remediation run and correctly rendered the equipment schedule on the control, but a rail station upgrade and a rooftop solar array both carry `TBC — record finishes, fixtures and equipment selections` | 3/5 | `emphasis-profiles.json` `applicability` |
| **W2-9** | `WORKFLOW-LAUNCH` | **Advisory still never produces an artefact, now for a third distinct reason.** Wave 1: seed route hard-fail. Wave 1b: workflow failure. Wave 2: the agent declines to classify, claims setup was recorded when `project_events` is empty, and asks for taxonomy values in prose vocabulary the profile cannot accept | 1/5 | agent instructions; `turn_context.py` |
| **W2-10** | `REGISTER` | **Raw enums and null artefacts in client-facing text.** `Scale summary: rail_metro; scale unresolved`, `scale —`, and the Description sentence *"Site, asset, and scope details remain not stated"* printed on three projects that supplied all three | 4/5 | `pmp_renderer.py` label rendering |
| **W2-11** | `COST` | **Cost plans contain no costs, and the typed compiler drops the budget.** 0 priced lines out of 47 across two plans; the typed plan never mentions $750k and produces 548 words against legacy's 2,087 | 2/2 | `create_cost_plan.py` typed path |

### Categories used

The corpus's eight, plus `WORKFLOW-LAUNCH` (added in Wave 1) and two new ones this wave:

- `TAXONOMY-GAP` — the vocabulary has no value for a fact the prompt supplied. Distinct from `INPUT-LOSS`
  (fact had somewhere to go and did not get there) and from `CLASSIFY` (wrong value chosen from a
  sufficient vocabulary). It cannot be fixed in the agent or the renderer; it is a data change.
- `HARNESS` — the test environment, not the product, invalidated the measurement.

---

## What Wave 2 actually answered

**Question: does work type change anything?**

| Layer | Does work type change it? | Evidence |
|---|---|---|
| Classification | ✅ yes, 4/5 correct | only prompt 43 wrong, and for a structural reason |
| Scale band | ✅ resolves from budget text, all 5 | XS/S/S/M/L all correct |
| Section weights | ✅ yes, materially | `risks` 0.12 → 0.19 remediation; `ffe-schedule` 0.03 → 0.0 |
| Section set | 🟡 partly | dropped FFE on remediation only; still stubs it on rail and solar |
| Seed routing | 🟡 in principle | routes differ by class, but 3 classes have no doctrine and 2 guides are unreachable |
| Consultant register | 🟡 when scope exists | 61 got 5 disciplines; 6.1 and 43.1 got Architect alone |
| **Document length** | ❌ **no** | 708–795 words across XS→L |
| **Document content** | ❌ **no** | 82–95% identical lines; 94.7% between the two most dissimilar projects in the wave |

The plumbing built after Wave 1 works. **The band, the weights and the routes all resolve correctly and
then fail to produce a different document**, because the scaffold renders effectively fixed boilerplate
and the model is not made to expand it against the resolved target. That is the single structural finding
of Wave 2, and it is different from Wave 1's finding: Wave 1's profile was empty, Wave 2's profile is
populated and the document still does not move.

---

## Grading boundary

**Mechanically verified — reproducible from the database, the artefacts and the generation manifests:**
C1 on all runs; C2 fact-presence counts; C3/C4 against corpus checkpoints; C6 word counts against computed
band bounds; C8 profile-vs-prompt contradictions; every similarity percentage, seed list, section weight,
counterfactual route count and compiler identifier above. The seed-routing counterfactuals were produced
by calling `select_seed_knowledge_for_taxonomy` directly against the live catalog.

**Agent judgement, marked [J] — override freely:** C5 consultant correctness, C7 doctrine sufficiency,
C9 register. Unlike Wave 1 these are now discriminating rather than uniformly zero — the control scores
1–2 where the corpus runs score 0 — which suggests they are measuring something real.

**Not verified:** anything about the cost plans, for the reason in the validity warning; and prompt 40,
which was not run.

---

**Recommendations:** [`wave-2-recommendations.md`](wave-2-recommendations.md)
