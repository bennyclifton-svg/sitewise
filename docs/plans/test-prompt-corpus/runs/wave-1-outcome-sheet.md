# Wave 1 Test Outcome Sheet

**Run date:** 2026-08-12 · **Prompts run:** corpus 1–6 (Section 1, sequential) · **Graded:** 2026-08-12

> **Note on which prompts were run.** The corpus Wave 1 set is prompts **1, 2, 3, 8, 10, 49** — chosen to
> spread across FFE contrast (1 vs 8), advisory (10) and a second XS fitout (49). What was actually run is
> prompts **1–6** in document order. That is still a valid wave, but it loses the prompt 1 / prompt 8
> diagnostic pair and tests no advisory work type. Neither gap blocks the findings below, because the
> defects found are upstream of section applicability. Prompts 8, 10 and 49 are worth running after the
> D1/D2 fixes land, as the re-test.

**Grading provenance.** C1–C4 and C8 are mechanically verified against the database, the generation
manifest and the artefact text — reproducible, no judgement. C5–C7 and C9 are marked **[J]** and are
provisional: they are the agent's reading, not a domain verdict, and should be overridden freely.

---

## What was produced

| # | Prompt | Project | Class / subclass / work type | PMP? | Cost plan? |
|---|---|---|---|---|---|
| 1 | Mechanical plant replacement | `Mech AC Replacement` (05:19) | commercial / office / refurb | ✅ v1 | — |
| 1 | Mechanical plant replacement (re-run) | `Test-Mech-Plant` (07:43) | commercial / office / refurb | ✅ v1 | ✅ v1 |
| 2 | Fire services upgrade | `test-Fire-services-upgrade` | industrial / warehouse / refurb | ❌ **never queued** | ✅ v1 |
| 3 | Switchboard upgrade | `test switchboard and electrical upgrade` | institution / education_primary_secondary / refurb | ❌ **no workflow** | ❌ |
| 4 | Lift replacement | `test lift replacement` | residential / apartments / refurb | ✅ v1 | — |
| 5 | Roof replacement | `test Roof replacement and waterproofing` | commercial / retail_standalone / refurb | ✅ v1 | — |
| 6 | Remedial concrete and facade | `Remedial concrete and facade` | residential / apartments / remediation | ❌ **workflow failed** | ❌ |

**Six prompts, four PMPs.** Three of six runs produced no PMP at all, for three different reasons. That is
the first finding: before section quality is even in question, the PMP path has a ~50% completion rate on
small-works prompts.

---

## The headline measurement

The four PMPs that were produced are **94–98% line-identical to each other.**

| Comparison | Identical |
|---|---|
| Mech AC vs Lift replacement | 94.1% |
| Mech AC vs Roof replacement | 96.5% |
| Mech AC (run 1) vs Mech AC (run 2) | 97.6% |
| Lift vs Roof | 94.1% |

All four: **85 lines, ~1,145 rendered words, identical 12-heading section list.** Diffing the $180k
mechanical replacement against the $1.4m occupied-strata lift replacement yields **five differing lines**,
and every one is a class/subclass noun substitution:

```
- | Description | Refurb commercial project. …
+ | Description | Refurb residential project. …
- Class/type/subclass: commercial / refurb / office.
+ Class/type/subclass: residential / refurb / apartments.
- Planning emphasis for this commercial refurb: …
+ Planning emphasis for this residential refurb: …
- - Scale summary: office; scale unresolved.
+ - Scale summary: apartments; scale unresolved.
```

This is not "the documents are too generic." The documents are **the same document**.

---

## Per-run sheets

Scores: **0** = fail · **1** = partial · **2** = pass · **n/a** = no artefact to grade.

### Run 1 — Prompt 1, Mechanical plant replacement (`Test-Mech-Plant`)

| Field | |
|---|---|
| Expected | commercial / office / refurb · XS |
| Actual | commercial / office / refurb · scale unresolved |
| C1 Classification | **2** — class, subclass and work type all correct |
| C2 Input retention | **0** — 0 of 7 facts retained. `R22`, `Pioneer`, `Actron`, `30kW`, `180`, `service centre`, `western office` all absent from the artefact |
| C3 Section applicability | **0** — FFE Schedule rendered as an empty stub on a mechanical plant replacement |
| C4 Section absence | **0** — no commissioning/balancing, no shutdown or staging, no refrigerant handling, no electrical capacity check |
| C5 Consultant **[J]** | **0** — Architect named as design lead; no mechanical engineer anywhere |
| C6 Scale **[J]** | **0** — 1,145 words with zero project content for an $80–180k job |
| C7 Doctrine **[J]** | **0** — loaded `nsw-commercial-fitout-cost-breakdown-reference` and `role-architect-pm` for an R22 plant swap; only seed section cited in output is `ncc-reference-guide#compliance-pathways` |
| C8 Invention | **1** — no invented *technical* facts, but profile asserts `vacant`, `unrestricted access`, `nil contamination`, `cdc` with no basis |
| C9 Register **[J]** | **0** — the artefact states "Site, asset, and scope details remain not stated" while the user supplied all three |
| **Categories** | `INPUT-LOSS`, `SECTION-SET`, `DISCIPLINE`, `SCALE`, `DOCTRINE`, `INVENT` |

### Run 2 — Prompt 2, Fire services upgrade

| Field | |
|---|---|
| Expected | industrial / warehouse / refurb · S |
| Actual | industrial / warehouse / refurb — **classification correct, PMP never generated** |
| C1 | **2** — and this is the one run where the profile was actually populated (site, budget, live-operation constraint all captured in chat) |
| C2–C9 | **n/a** — no PMP artefact |
| **Blocker** | Four user round-trips. Agent asked for confirmation → user confirmed → *"The current turn does not provide the required profile-update authority, so no profile changes or artefacts were created"* → user re-pasted the entire prompt → agent raised a profile proposal → user said "accepted" → cost plan queued, and: **"The PMP request encountered a snapshot conflict and was not queued successfully; it requires a fresh workflow submission."** |
| **Categories** | `WORKFLOW-LAUNCH` (new category — see below) |

### Run 3 — Prompt 3, Switchboard and electrical upgrade

| Field | |
|---|---|
| Expected | institution / education_primary_secondary / refurb · XS |
| Actual | classified correctly; **no workflow queued, no artefact of any kind** |
| C1 | **2** |
| C2–C9 | **n/a** |
| **Not a defect** | ~~The prompt does not contain the words "create PMP", so nothing launched.~~ **Corrected on review:** corpus prompt 3 does not ask for a PMP — it ends at "About $220k." The agent replied with a sound six-point chat answer, which is the right response to a description with no request. This is a corpus gap, not a launch bug. Add "Need a PMP" to prompt 3 before re-running |
| **Blocker (real)** | *"I could not write these new scope, budget, and programme details into the confirmed Project Profile because this turn does not include profile-mutation authority."* — the D1 defect, not a launch defect |
| C8 note | Agent asserted **"Site currently vacant, based on the confirmed profile"** — for a primary school whose works are scheduled into the summer holidays specifically *because* it is occupied |
| **Categories** | `WORKFLOW-LAUNCH`, `INVENT` |

### Run 4 — Prompt 4, Lift replacement

| Field | |
|---|---|
| Expected | residential / apartments / refurb · S |
| Actual | residential / apartments / refurb |
| C1 | **2** |
| C2 Input retention | **0** — `Bondi`, `1988`, `1.4m`, `strata`, `8 levels`, `occupation` all absent. The word "lift" appears only in the echoed project title |
| C3 | **0** — FFE Schedule stub on a lift replacement |
| C4 | **0** — no sequential replacement, no strata by-law process, no DDA/AS 1735 upgrade trigger, no resident communication |
| C5 **[J]** | **0** — Architect leads; no vertical transportation consultant |
| C6 **[J]** | **0** — identical weight to the $160k roof job |
| C7 **[J]** | **1** — `multi-residential-apartments-guide` did load, but nothing from it is visible in the output |
| C8 | **1** — profile asserts `vacant` against an explicit *"Residents stay in occupation"* |
| C9 **[J]** | **0** |
| **Categories** | `INPUT-LOSS`, `SECTION-SET`, `DISCIPLINE`, `SCALE`, `DOCTRINE`, `INVENT` |

### Run 5 — Prompt 5, Roof replacement and waterproofing

| Field | |
|---|---|
| Expected | commercial / retail_standalone / refurb · XS |
| Actual | commercial / retail_standalone / refurb |
| C1 | **2** |
| C2 Input retention | **0** — `box gutter`, `160`, `tenant`, `trading`, `leak` all absent |
| C3 | **0** — FFE Schedule stub on a roof replacement |
| C4 | **0** — no weather contingency, no temporary weatherproofing, no trading-hours restriction, no working-at-heights, no asbestos check |
| C5 **[J]** | **0** — Architect leads a re-roofing job |
| C6 **[J]** | **0** |
| C7 **[J]** | **0** |
| C8 | **1** |
| C9 **[J]** | **0** |
| **Notable** | The chat layer *caught the defect itself*: **"The project is vacant according to the current profile, but your instruction says the tenant is trading throughout. That operational constraint should be corrected because it materially affects the methodology, programme, safety controls and price."** It then generated the PMP from the wrong profile anyway |
| **Categories** | `INPUT-LOSS`, `SECTION-SET`, `DISCIPLINE`, `SCALE`, `DOCTRINE`, `INVENT` |

### Run 6 — Prompt 6, Remedial concrete and facade

| Field | |
|---|---|
| Expected | residential / apartments / remediation · S |
| Actual | residential / apartments / remediation — **workflow failed** |
| C1 | **2** |
| C2–C9 | **n/a** |
| **Blocker** | `WorkflowResultFailed: required route file is not selected: seed/multi-residential-apartments-guide.md` (message duplicated). Failed at 08:45:51, nine seconds after queueing. `attempt=1/3` — **the retry budget was never used.** `progress = {"stage": "failed"}`. The chat said *"The draft will appear when ready"* and then never reported the failure |
| **Sharp detail** | Run 4 loaded `multi-residential-apartments-guide.md` successfully on the `refurb` route. Run 6 hard-failed demanding the same file on the `remediation` route. Same seed, same subclass, opposite outcome |
| **Categories** | `WORKFLOW-LAUNCH`, `DOCTRINE` |

---

## Aggregated defect list

Ordered by leverage. Counts are out of the six runs.

| ID | Category | Defect | Count | Repo area |
|---|---|---|---|---|
| **D1** | `INPUT-LOSS` | **Prompt facts never reach the generator.** The chat turn acknowledges the facts in prose but cannot write them to the profile — *"this turn does not include profile-mutation authority"* (runs 2 and 3 say this verbatim). `work_scope` is `None` or `[]` on **all 7** projects; `scale` is `None`/`{}` on 6 of 7. The workflow then reads an empty profile | **6/6** | chat turn → profile mutation path; `project_profile_proposals` |
| **D2** | `INVENT` | **Complexity defaults contradict the prompt.** `operational_constraints=vacant`, `access_constraints=unrestricted`, `contamination_level=nil`, `planning=cdc` are written on 6 of 7 projects regardless of input. Five of six prompts explicitly state occupation ("residents stay in occupation", "tenant trading throughout", "warehouses stay operational", summer-holiday-only school works). The `live_operations` risk-flag modifier in `emphasis-profiles.json` can therefore never fire | **6/6** | project creation defaults; `derive_risk_flags` |
| **D3** | `DISCIPLINE` | **Architect is the design lead unconditionally.** [`pmp_renderer.py:1452`](../../../backend/app/sitewise/pmp_renderer.py#L1452) appends the Architect row *before* the work-scope consultant loop at line 1455 and seeds `seen = {"architect"}`. With D1 leaving `work_scope` empty, the loop adds nothing — so Architect is the *entire* register. Compounded twice more: `user_role=architect-pm` loads `seed/role-architect-pm.md` into every run, and the Consultants preamble hard-states *"The Architect row is the design lead"*. Architect also owns 2 of 3 risk rows and 2 of 4 action rows | **4/4 PMPs** | `pmp_renderer.py:1436–1454` |
| **D4** | `SECTION-SET` | **Section list is invariant.** All four PMPs render the same 12 headings. FFE Schedule appears as an empty stub on a plant replacement, a lift replacement and a re-roofing job. There is no include/exclude mechanism — [`section_contracts.py:28-34`](../../../backend/app/sitewise/section_contracts.py#L28-L34) iterates `PMP_CORE_SECTIONS` unconditionally and [`pmp_renderer.py:1828-1835`](../../../backend/app/sitewise/pmp_renderer.py#L1828-L1835) raises `RuntimeError` if any section is missing, so omission is currently a crash rather than an option | **4/4 PMPs** | `emphasis-profiles.json`, `section_contracts.py`, `pmp_renderer.py:1828` |
| **D5** | `SCALE` | **No scale dimension.** ~1,145 words whether the job is $160k or $1.4m. `scale` resolved to `unknown` on every field (`grade`, `nla_sqm`, `storeys` all null) even though every prompt gave a budget. The emphasis key is `class\|work_type` with no scale band | **4/4 PMPs** | `emphasis-profiles.json` key schema |
| **D6** | `DOCTRINE` | **Wrong seeds, and loaded seeds stay invisible.** The R22 mechanical replacement consulted `nsw-commercial-fitout-cost-breakdown-reference` and `role-architect-pm`; nothing mechanical, services or refrigerant-related exists in the set. Across all four PMPs the only seed section cited in the rendered output is `ncc-reference-guide#compliance-pathways-and-documentation` — 8–9 seeds consulted, 1 visible | **4/4 PMPs** | seed routing; `seed_consulted` vs rendered citations |
| **D7** | `WORKFLOW-LAUNCH` | **PMP fails to launch, two distinct ways.** (a) Run 6 hard-fails on `required route file is not selected: seed/multi-residential-apartments-guide.md`, with `attempt=1/3` — retries unused — and no user-facing error; chat still says "will appear when ready". (b) Run 2 hits a **"snapshot conflict"** after profile acceptance and is silently not queued. ~~(c) Run 3~~ withdrawn — corpus prompt 3 never asks for a PMP | **2/6** | workflow launch/queue; route-file selection gate; `frozen_snapshot_fingerprint` |
| **D8** | `VALIDATION` | **Length validation passes below its own floor.** All four PMPs recorded `word_count` 742–747 against `pmp_min_words=800`, and every one logged `validation: passed` | **4/4 PMPs** | `pmp_length.py` / create_pmp validation loop |

### New category proposed

`WORKFLOW-LAUNCH` — the run never produced an artefact. Not in the corpus's original eight because the
corpus assumed generation always happens. It should be added: **3 of 6 runs died here**, which is a larger
effect than anything in the generated documents.

---

## Root cause chain

The eight defects are not eight bugs. They are one chain with two independent branches:

```
User types a rich prompt
        │
        ├─ chat agent parses it correctly ────────► prose reply is good
        │                                            (run 5 even flags the contradiction)
        │
        └─ profile mutation blocked ──────────────► D1  work_scope = None
                 "no profile-mutation authority"        scale     = None
                                │                       complexity = defaults  ── D2
                                ▼
                    workflow reads empty profile
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
   work_scope empty      no scale band      wrong seed route
        │                      │                  │
        ▼                      ▼                  ▼
   consultant loop        same word budget    generic doctrine
   adds nothing           for $160k & $1.4m        │
        │                      │                   ▼
        ▼                      ▼                  D6
   Architect only          D5 / D4
        │
        ▼
       D3

Separately:  route-file gate + snapshot conflict + no launch keyword ──► D7 (3/6 runs)
```

**D1 is the single highest-leverage fix.** It is upstream of D2, D3, D5 and D6. Fixing section
applicability (D4) while the profile stays empty would produce *correctly-chosen empty sections* —
better, but still not a usable document.

**D7 is the highest-severity fix**, because 50% of runs produce nothing, and Wave 2 cannot be measured
until it lands.

---

## Evidence that the platform is not uniformly broken

The **cost plans are markedly better than the PMPs** and use a different pipeline
(`clerk-sitewise-create-cost-plan`, model `gpt-5.6-luna`, no adaptive scaffold):

- 2,188 and 2,076 words vs the PMPs' ~1,145
- **25.8% similar to each other**, against the PMPs' 94–98%
- Real content: cost codes, a services engineer line, a hazardous-materials allowance reading
  *"Investigation allowance; no evidence of asbestos status"*

So the defect is specific to the **PMP adaptive-scaffold path**, not to the model, the taxonomy or the
platform generally. The cost plan still inherits the bad profile (its header reads *"unrestricted access,
vacant operation, clean/non-contaminated"*), which is further confirmation that D1/D2 sit upstream of both.

---

## Recommended fix order

1. **D7** — unblock launch. Nothing else is measurable at a 50% completion rate. Three separate causes;
   the route-file gate and the snapshot conflict are the two that produce silent failures.
2. **D1** — give the chat turn profile-write authority, or auto-accept a profile proposal derived from
   the opening prompt. This alone should move C2 from 0 to something gradeable across every run.
3. **D2** — stop defaulting `vacant`/`unrestricted`/`nil`/`cdc`. Default to `unknown` and let the absence
   be visible, rather than asserting a falsehood the document then reasons from.
4. **D3** — resolve design lead from dominant scope; delete the unconditional Architect row and the
   "Architect row is the design lead" preamble.
5. **D4 + D5** — section applicability and a scale band in the emphasis key. These are the structural
   changes from the original diagnosis, and they are still correct — just not first.
6. **D8** — make the length floor actually gate.

## Re-test set

After D7 and D1 land, re-run **1, 4, 5** (the three that produced PMPs) plus **8, 10, 49** (the Wave 1
prompts not yet run). That gives the prompt 1 / prompt 8 FFE contrast and the advisory suppression test,
against a profile that now carries the prompt facts.

---

## Fix log — D7 and D1 (2026-08-12)

### D7(a) — seed route gate. The one failure was 37 failures.

Root cause: two files disagreed. `data/taxonomy/pmp-section-seed-map.json` required
`seed/multi-residential-apartments-guide.md` for any residential/apartments project; that guide's own
frontmatter declares `applies_to_work_types: [new, refurb, extend]`. On `remediation` the catalog never
selected it, the section map still demanded it, and `_validate_section_routes` raised.

Sweeping all 265 class × subclass × work-type combinations found **37 (13%) that hard-fail before
generation** — not one. The distribution matters: **33 of them are `advisory`**, so corpus prompts 10 and
11 would both have died the same way, and `seed/advisory-services-guide.md` — which describes itself as a
"Cross-class advisory-services overlay" — listed only three of six classes in its frontmatter.

| | Before | After |
|---|---|---|
| Combinations that hard-fail | 37 / 265 | **0 / 265** |
| Advisory combos routing the advisory guide | 20 / 53 | **53 / 53** |

Changes: [`seed_routing.py`](../../../backend/app/sitewise/seed_routing.py) — a required route whose file
the catalog did not select is now dropped rather than raised, because the section map and seed frontmatter
are separate files evolving independently and their disagreement is evaluated at runtime against live
taxonomy. Unknown files and unknown section ids stay fatal; those are authoring errors that tests catch.
Plus the three data corrections: advisory guide frontmatter widened to all six classes, apartments guide
route scoped to its declared work types, commercial procurement guide no longer required on residential
advisory.

### D7(b) — snapshot conflict now self-heals

The agent freezes `expected_profile_revision` when the turn begins. A turn that accepts a profile proposal
and then queues the artefact the user just asked for invalidates its own expectations before it launches.
[`server.py`](../../../backend/app/mcp_bridge/server.py) re-reads the snapshot and retries **once**;
a second conflict means something outside the turn is writing, and still surfaces. The result payload
carries `snapshot_refreshed` so the retry is visible in the trace rather than silent.

### D1 — setup fields now follow the identity-field rule

The gate was one line: auto-apply fired only when a proposal contained *nothing but* `client` and
`site_address`. Everything else queued for explicit approval, so `work_scope`, `scale` and `complexity`
stayed empty and the PMP generated from a blank profile.

`should_auto_apply_proposal` now extends the rule architecture.md §5.2 already documents — fill a blank,
never overwrite an answer — to the setup fields, with one deliberate split:

- **User-stated** setup values (no evidence references) auto-apply into empty fields, flagged for review
- **Evidence-derived** setup values keep their review step however empty the field is — reading a claim off
  page 2 of a report is not the user instructing you
- Anything that would overwrite a settled value stays pending, for identity and setup alike

`_accept_identity_proposal` became `_accept_additive_proposal` and now treats `[]` and `{}` as unset, which
is the shape a fresh project actually starts in. Agent instructions in
[`turn_context.py`](../../../backend/app/agent/turn_context.py) now direct one proposal covering the setup
fields a prose description establishes, before any artefact is queued, and explicitly forbid filling
`operational_constraints` / `access_constraints` / `contamination_level` with defaults the user did not give
— which is D2's root cause, and stops it being re-introduced here.

### Combined effect, measured

Residential / apartments / remediation — the run 6 taxonomy:

| | Section refs routed | Remediation doctrine loaded |
|---|---|---|
| Before (workflow failed) | — | — |
| After D7 alone, `work_scope` empty | 5 | ✗ |
| After D7 + D1, `work_scope` captured | **9** | ✓ `building-remediation-rectification-guide.md` |

### Verification

`2039 passed, 7 skipped, 31 deselected` — full backend suite, no failures. 14 new tests across
[`test_pmp_seed_routing.py`](../../../backend/tests/sitewise/test_pmp_seed_routing.py) (including the
all-combinations sweep, which now guards against the next frontmatter drift),
[`test_workflow_snapshot_refresh.py`](../../../backend/tests/mcp_bridge/test_workflow_snapshot_refresh.py)
and [`test_profile_proposal_auto_apply.py`](../../../backend/tests/projects/test_profile_proposal_auto_apply.py).

**Not yet verified at runtime.** These are unit-level results. The re-run of prompts 1–6 is what confirms
the PMPs stop being 94% identical, and that is still to do.

---

## Wave 1b — re-run after D7/D1 (2026-08-12, 10:16–10:26 UTC)

Six projects, now prefixed by corpus number. **Note:** prompts 4 and 5 were not among them — the set that
ran is 8, 10, 49, 1, 2, 3.

| # | Project | PMP? | Profile captured from prompt? |
|---|---|---|---|
| 8 | Cosmetic tenancy refresh | ✗ not requested | ✗ **proposal stayed pending** |
| 10 | Advisory — condition assessment | ✗ **workflow failed** | ✓ work_scope |
| 49 | Allied health clinic | ✗ not requested | ✓ class, work type, subclass, scale |
| 1 | Mechanical plant replacement | ✓ | ✓ class, work type, subclass, complexity, work_scope |
| 2 | Fire services upgrade | ✓ | ✓ class, work type, subclass, complexity, work_scope |
| 3 | Switchboard upgrade | ✗ not requested | ✗ nothing proposed |

### D1 works — proven in the event log

`project_events` shows, for prompts 1, 2, 10 and 49: `proposal/proposed` → `proposal/accepted` →
`project_profile/updated`, all `actor_source=agent`, all within the same second, all `evidence_count: 0`.
Before the change only `{client, site_address}` could auto-apply, so a `work_scope` or `complexity`
proposal could not have been applied by the agent at all.

The measurable consequences:

| | Wave 1 | Wave 1b |
|---|---|---|
| `work_scope` on prompt 1 | `None` | `["services_upgrade", "integrated_commissioning_handover"]` |
| `operational_constraints` on prompts 1–2 | `vacant` | **`live_environment`** |
| Prompt 1 consultants | Architect only | Architect, **Services Engineer**, **Commissioning Agent** |
| Prompt 2 consultants | *(no PMP produced)* | Architect, Project Manager, **Fire Engineer** |
| Prompt 2 seeds | *(no PMP produced)* | + `fire-life-safety-guide`, + `as-standards-reference#as-2419-series` |
| Prompt 1 Description | "Site, asset, and scope details remain **not stated**" | "Scope includes Integrated Commissioning and Handover; Building Services Upgrade" |

Prompt 2 now loads exactly the AS 2419 / fire-life-safety doctrine its corpus checkpoint demanded, because
`work_scope: ["fire_services"]` finally reaches the router. The consultant loop at
[`pmp_renderer.py:1455`](../../../backend/app/sitewise/pmp_renderer.py#L1455) finally has scope to iterate.

**Prompt 8 behaved exactly as predicted, and that is the D2 evidence.** Its proposal covered
`["complexity","scale","work_scope"]`, and `complexity` was already populated with the creation-form
defaults, so the additive rule correctly declined and the proposal stayed pending. The creation form
writes `vacant`/`unrestricted`/`nil`/`cdc` before the user types anything, and D1 cannot overwrite a value
that looks like a user's own choice. **D2 now blocks D1 on any project created through the form.**

### What did not move: the document

| | Wave 1 | Wave 1b |
|---|---|---|
| Prompt 1 vs prompt 2 similarity | 94.1% | **84.2%** |
| Prompt 1 old vs new | — | **91.0% identical** |
| Prompt 1 fact retention | 0/7 | **0/8** |
| Prompt 2 fact retention | — | **2/7** (`pump`, `operational`) |
| FFE Schedule on a plant replacement | empty stub | **empty stub** |
| Design lead | Architect | **Architect** |

`R22`, `Pioneer`, `Actron`, `30kW`, `$180k`, `service centre`, `western office` — still absent. This is the
gap the original diagnosis named and neither D1 nor D7 addresses: **the profile has no field for the asset**.
`work_scope` is a taxonomy enum, so "services_upgrade" is the most the prompt can become. Two 30-year-old
R22 Pioneer units in two named zones have nowhere to land, so they are still discarded before generation.

### D7(a) has not taken effect in the running system

Prompt 10 failed at 10:19:36 UTC with `required route file is not selected:
seed/advisory-services-guide.md` — **a string that no longer exists anywhere in the source tree.** The chat
turn in the same project ran the new code (its profile proposal auto-applied, which only the new code
does), so the API process is current while the process executing durable workflows is not.

Leading hypothesis: the durable workflow is consumed by a worker that was not restarted, or by the hosted
deployment sharing this Supabase database — Dokploy deploys are manual. Not proven; no local worker process
was found, and `lock_owner` is cleared on completion. **Decisive test:** restart the workflow worker (or
redeploy), then re-run prompt 10 alone. If it produces a document, D7(a) is confirmed live; the code-level
result is already unambiguous — 0/265 combinations fail on disk, against 37/265 before.

---

## Fix log — D2 (2026-08-12)

**One line, in the frontend.** [`TaxonomyPicker.tsx`](../../../frontend/src/components/project/TaxonomyPicker.tsx)
filled every unanswered complexity dimension with `dimension.options[0].value`. Each dimension's first
option is its benign one — `cdc`, `traditional`, `nil`, `unrestricted`, `vacant`, `single_owner` — so the
creation form asserted a clean, empty, unconstrained site before the user typed anything.

`defaultComplexity` is now `sanitiseComplexity`: it keeps the dimensions the user answered, drops values
invalid for the selected class, and invents nothing. The select carries an explicit **"Not stated"** option,
choosing it removes the key, and `selectWorkType` resets to `{}` rather than to a fresh set of defaults.

**Why this was blocking D1, not merely wrong.** A pre-filled `vacant` is indistinguishable from a chosen
`vacant`, and D1's additive rule refuses to overwrite a settled value — correctly. Prompt 8 is the proof:
its proposal covered `["complexity","scale","work_scope"]`, `complexity` was already populated, so the whole
proposal stayed pending and none of it applied. D2 was gating the fix it looked unrelated to.

**Downstream, verified rather than assumed:**

- `complexity_labels` skips absent keys ([`taxonomy.py:287`](../../../backend/app/sitewise/taxonomy.py#L287)) —
  the cost plan header stops claiming "unrestricted access, vacant operation, clean/non-contaminated"
- `_risk_rule_matches` returns False for a missing dimension ([`taxonomy.py:307`](../../../backend/app/sitewise/taxonomy.py#L307)) —
  no crash, and `live_operations` can now actually fire once the agent records `live_environment`
- `_validate_complexity` only checks values that are present — an absent dimension was always valid
- **No workflow requires complexity.** The gates are `building_class`, `subclasses`, `work_type`, `state`
  ([`workflow_capabilities.py:25-29`](../../../backend/app/projects/workflow_capabilities.py#L25-L29)), so
  unsetting it blocks nothing

**Verification:** frontend 220 passed / 27 files; backend 2041 passed, 7 skipped, 0 failed; `tsc` clean for
the changed files. The existing picker test asserted `operational_constraints: "vacant"` as correct
behaviour — it encoded the defect, and now asserts the field stays unstated. Three new tests cover
unset-by-default, set-on-pick, clear-on-Not-stated, plus two backend tests for the D2/D1 interaction.

**Not addressed — existing projects keep their bad defaults.** Every project already created carries
`vacant`/`unrestricted`/`nil`/`cdc`, and nothing can now distinguish those from deliberate answers, so a
blanket migration would erase real choices. Wave 2 projects will be clean; prompts 1–49 need their
complexity corrected by hand or by re-creating the project.

---

## Fix log — asset register (2026-08-12)

The unnumbered defect behind C2. Fact retention stayed at 0/8 through D1 and D2 because the profile
modelled **buildings** — GFA, storeys, NLA, bed count — and nothing modelled the **plant being replaced**.
`work_scope` is an enum, so the mechanical prompt could only ever compress to `services_upgrade`. Two
30-year-old R22 Pioneer units in two named zones had nowhere to land and were dropped before generation.

**New profile field: `assets`** — a list of `ProjectAsset`, each with `type`, `count`, `location`,
`make_model`, `capacity`, `age_years`, `condition`, `action`, `replacement_spec`, `notes`. Condition and
action are validated against [`asset-register.json`](../../../data/taxonomy/asset-register.json); the
register applies to refurb, remediation, extend and advisory, since a new build has no existing asset.

Wired through: `PROFILE_FIELDS`, `ProjectProfilePatch` / `ProjectProfileView`, `read_profile`,
`validate_profile_patch`, the create route, `taxonomy_options_payload`, and — critically —
`SETUP_PROPOSAL_FIELDS`, so the D1 auto-apply path captures it from a prose description without a
confirmation round-trip. A stored row that no longer parses is skipped rather than breaking the profile.

**It renders into the FFE Schedule.** When a project has no explicit FFE items but does have assets, the
schedule renders the asset rows instead of the `TBC — record finishes, fixtures and equipment selections`
placeholder. That is the "empty FFE stub on a plant replacement" complaint answered from the other side:
the equipment being replaced *is* the schedule that job needs. Explicit FFE items still take precedence, so
nothing changes for fitout projects. The section set is untouched — this is not D4.

For the Wave 1 mechanical prompt the row now reads:

```
| Split ducted air conditioning system | Service centre; western office | 2 | 30kW | Replace |
  30 years old; Replace with Actron 30kW split ducted; R22 refrigerant; phase-out obligations apply |
```

Every fact Wave 1 dropped is in that one row.

**Verification:** backend 2052 passed, 7 skipped, 0 failed; frontend 346 passed / 50 files; `tsc` clean for
changed files. 11 new tests across
[`test_profile_assets.py`](../../../backend/tests/projects/test_profile_assets.py) and
[`test_asset_schedule_rendering.py`](../../../backend/tests/sitewise/test_asset_schedule_rendering.py).
Two existing expectations changed because the profile contract genuinely grew a field.

**Deliberately not built: the profile-panel editor.** The agent writes assets and the PMP renders them, but
there is no UI yet to add or correct a row by hand. No data is at risk — the PATCH route uses
`model_fields_set`, so a Control Board save that omits `assets` leaves them untouched — but manual
correction is not yet possible. That is the next piece of this work, not a hidden gap.

---

## Fix log — D4 + D5 (2026-08-12)

Done together because they share one mechanism: the emphasis profile stops being a fixed list of eleven
sections with per-`class|work_type` weights, and starts resolving *which* sections apply and *how long* the
document should be.

**D4 — section applicability.** [`emphasis-profiles.json`](../../../data/taxonomy/emphasis-profiles.json)
gains an `applicability` block with `include_when` / `exclude_when` conditions over work type, work scope
and the presence of an asset register. `applicable_sections()` resolves it;
[`pmp_renderer.py`](../../../backend/app/sitewise/pmp_renderer.py) renders from a section→renderer map
rather than a fixed list; `pmp_section_headings` and `required_section_headings` narrow to the same set, so
the `RuntimeError` contract now checks what the project actually needs instead of all eleven.

**D5 — scale band.** `parse_budget_amount` reads the loose text a PM types — `$180k`, `around $1.4m`,
`approximately $850,000`, `Budget not fixed yet, maybe $1.2m` — and `scale_band_for` maps it to XS/S/M/L on
the corpus thresholds. The band feeds three things: emphasis modifiers (XS pulls weight out of procurement
and consultants and into snapshot and scope; L does the reverse), the word target, and the length-validation
bounds. No budget means no band, and everything falls back to today's behaviour.

**Measured across corpus prompts:**

| Prompt | Band | Word target | Sections | FFE | Procurement |
|---|---|---|---|---|---|
| 1 — mech plant $180k, assets | XS | 700 | 11 | ✓ *(as equipment)* | ✓ |
| 5 — roof replacement $160k | XS | 700 | **10** | **✗** | ✓ |
| 8 — tenancy refresh $95k, fitout | XS | 700 | 11 | **✓** | ✓ |
| 10 — advisory, no budget | — | default | **9** | ✗ | **✗** |
| 23 — office new build $140m | L | **1900** | 11 | ✓ | ✓ |

**The prompt 1 / prompt 8 pair now differentiates** — the diagnostic the corpus was built around. Prompt 5
against prompt 8 is the cleaner version of the same contrast: same class, same work type, same XS band, and
one carries a finishes schedule while the other does not. Word targets span 700–1900 where every project
previously got 1300.

**A consequence worth naming: the flat 800-word floor had to go.** Dropping sections legitimately shortens
the scaffold — two fixtures fell to 799 and 752 words — and a correct short document must not fail
validation for being short. `scale_band_word_bounds` derives the floor from the band's target and scales it
by how many sections actually apply. That is most of D8 arriving early, because leaving it would have meant
shipping a known-broken gate.

**Verification:** backend 2055 passed, 7 skipped, 0 failed. Four new section-contract tests cover the
fitout/services/asset/advisory cases. Three existing assertions changed because the contract genuinely
changed — they asserted that a fire-services refurb renders an FFE Schedule, which was the defect.

**Still open:** D3 (Architect as unconditional design lead), D6 (wrong seeds on some routes), the rest of
D8, the asset-register UI, and D7(a)'s runtime verification.

---

## R2 verification runs (2026-08-12, 11:46 / 11:53 UTC)

Two runs, fresh projects, before Wave 2. Both completed.

| | Wave 1 | R2 |
|---|---|---|
| Prompt 1 fact retention | **0/7** | **6/7** — R22, Pioneer, Actron, 30kW, service centre, western office |
| Prompt 1 `complexity` | 9 defaults incl. `vacant` | **`{"operational_constraints": "live_environment"}`** — one key, the one described |
| Prompt 1 FFE Schedule | `TBC — record finishes…` stub | **equipment row** with count 2, make, capacity, age, R22, Actron replacement |
| Prompt 1 consultants | Architect only | Architect + Services Engineer (Mechanical) |
| Prompt 10 workflow | **hard-failed** on the advisory seed route | **completes** |
| Prompt 10 sections | — | **9** — no FFE, no Procurement and Delivery |

**D7(a) is confirmed live** — prompt 10 previously died on
`required route file is not selected: seed/advisory-services-guide.md` and now produces a document.
**D2, D1, the asset register and D4 are all confirmed working in the running app.**

### Three defects the R2 runs exposed

- **`budget` is never captured, so D5 never fires.** Both projects show `budget=None`; the scale band
  cannot resolve, and prompt 1 came out at 785 words rather than the XS target of 700. Budget lives in
  `taxonomy["budget"]` but is not a profile field and is not in the proposal path, so the agent had nowhere
  to put "$180k". **D5 is built and inert until this is wired.** Highest-value remaining fix.
- **The agent wrote `split_ducted_air_conditioning_system` as the asset type** — a snake_case identifier,
  rendered verbatim into the client-facing table. It needs to be a human label ("Split ducted air
  conditioning system"). Instruction-level fix.
- **The FFE "Finish" column carries "Pioneer"** — the make. Column semantics are wrong for equipment rows;
  an equipment variant of the header would read properly.

---

## Fix log — D3 (2026-08-12)

`design_lead_discipline()` resolves the lead from the dominant scope: each work-scope item lists its
consultants most-relevant-first, so the first consultant of the first selected scope is the discipline that
actually leads. Architect stays the answer for architectural scope and the fallback when no scope is
selected.

Applied in four places that all hardcoded it:
[`pmp_renderer.py:1476`](../../../backend/app/sitewise/pmp_renderer.py#L1476) (the unconditional register
row and the `seen` set), the section preamble that asserted "The Architect row is the design lead", the
baseline risk-row owners, and the actions table.

| Scope | Design lead |
|---|---|
| `mechanical_hvac` | Services Engineer (Mechanical) |
| `electrical_power` | Services Engineer (Electrical) |
| `fire_services` | Fire Engineer |
| `partitions_walls` | Architect |
| *(none selected)* | Architect |

**Verification:** backend 2062 passed, 7 skipped, 0 failed. Six new tests. One existing test changed — it
looked for the engagement citation on a row starting `| Architect |` in a fire-services fixture, which now
correctly leads with the Fire Engineer.

---

## Fix log — budget capture, and the two R2 rendering defects (2026-08-12)

**`budget` is now a profile field.** It was the reason D5 shipped inert: budget lived only in taxonomy
metadata, was never a profile field, and was not in the proposal path — so the agent had nowhere to put
"$180k" and every document fell back to the 1300-word default.

Wired the same way `assets` was: `PROFILE_FIELDS`, patch and view schemas, `read_profile`, the write-back,
`SETUP_PROPOSAL_FIELDS` (so D1 auto-applies it), and the agent instructions. It stores **the user's own
words** rather than a normalised number — "around $180k", "$1.4m approved" — because that is what C2 and C8
are grading; `parse_budget_amount` derives the band from the text. Validation requires only that a figure is
present, so "to be confirmed" is rejected while "Budget not fixed yet, maybe $1.2m" is accepted.

D5 now fires:

| Budget as typed | Band | Word target |
|---|---|---|
| `Budget around $180k` | XS | **700** |
| `roughly $850k` | S | 1100 |
| `$1.4m approved` | S | 1100 |
| `$28m` | L | **1900** |
| *(not stated)* | — | 1300 default |

**The two rendering defects from R2:**

- **Asset type labelling.** The agent wrote `split_ducted_air_conditioning_system` into a client-facing
  table. The instructions now require `type` to be a human label and say why — it renders verbatim.
- **Equipment column semantics.** When the schedule is built from the asset register the header becomes
  `| Item | Location | Qty | Make / capacity | Action | Notes |` and the preamble describes an equipment
  schedule rather than finishes and fixtures. "Pioneer" was previously landing under "Finish".

The mechanical prompt now renders:

```
Equipment schedule derived from the project asset register — the plant being replaced, upgraded or
remediated, with the make, capacity and condition recorded against each item.

| Item | Location | Qty | Make / capacity | Action | Notes |
| Split ducted air conditioning system | Service centre; western office | 2 | 30kW | Replace |
  30 years old; Replace with Actron 30kW split ducted; R22 refrigerant |
```

**Verification:** backend 2076 passed, 7 skipped, 0 failed. 14 new budget tests covering the phrasings from
the corpus itself. One existing profile-contract expectation grew a `budget` key.

---

## Grading boundary

**Mechanically verified — reproducible from the database and artefacts:** C1 on all six runs; C2 fact-presence
counts; C3/C4 against the corpus checkpoints; C8 profile-vs-prompt contradictions; every defect count,
similarity percentage, word count, seed list and error message above.

**Agent judgement, marked [J] — override freely:** C5 consultant correctness, C6 scale proportionality,
C7 doctrine visibility, C9 register. These are scored 0 almost uniformly, which is itself a signal that they
were not really independent measurements here — when a document contains no project content, every
judgement column collapses to the same answer. They will start discriminating once D1 is fixed, and that
is the point at which your own marking becomes the thing that matters.
