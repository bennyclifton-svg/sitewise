# Wave 4 Test Outcome Sheet

**Run date:** 2026-08-14 (11:30–11:56 UTC) · **Prompts run:** corpus 13, 23, 34, 47, 53, 62 · **Graded:** 2026-08-14

> Wave 4 is class breadth: one project per building class, with the R8 question
> in front. Does the **class guide** appear in Trace, and does class-specific
> doctrine actually change the document? 47 / 53 / 62 are the R8 live proof
> (institution / mixed / infrastructure). 13 / 23 / 34 are the already-ingested
> residential / commercial / industrial controls.

**Grading provenance.** C1–C4, C6 and C8 are mechanically verified against the
database, the generation manifest and the artefact text. C5, C7 and C9 are
marked **[J]**.

**Attribution.** The three completed PMPs record `build_version: bfe7a350-dirty`,
`queue_scope: dev`, `compiler: adaptive_scaffold`, `attempt: 1`,
`draft_mode: platform_seeded`. Production API has
`WORKFLOW_WORKER_INPROC_ENABLED=false` and there is no core workflow worker
container, so these runs are the working tree.

Artefacts: [`w4--13-4-house--knock-down-rebuild--create_pmp.md`](artefacts/w4--13-4-house--knock-down-rebuild--create_pmp.md),
[`w4--23-4-office--new--create_pmp.md`](artefacts/w4--23-4-office--new--create_pmp.md),
[`w4--34-4-cold-storage--create_pmp.md`](artefacts/w4--34-4-cold-storage--create_pmp.md).
47 / 53 / 62 produced no artefact.

---

## What was produced

| # | Prompt | Project | Class / subclass / work type | Band | Words | In band | PMP |
|---|---|---|---|---|---:|---|---|
| 13 | House, knock-down rebuild | `13.4 House, knock-down rebuild` | residential / house / new | **S** · $1.6m *(corpus labelled M; taxonomy S because S max is $2m)* | **952** | ✅ 770–1595 | ✅ v1 |
| 23 | Office, new | `23.4 Office, new*` | commercial / office / new | L · $140m | **1,937** | ✅ 1330–2755 | ✅ v1 |
| 34 | Cold storage | `34.4 Cold storage` | industrial / cold_storage / new | L · $45m | **1,855** | ✅ 1330–2755 | ✅ v1 |
| 47 | Hospital redevelopment | `47.4 Hospital redevelopment` | institution / healthcare_hospital / refurb | L · $85m | — | — | ❌ attempt 1 |
| 53 | Residential over retail | `53.4 Residential over retail*` | mixed / residential_retail / new | L · $46m | — | — | ❌ attempt 1 |
| 62 | Water treatment plant | `62.4 Water treatment plant` | infrastructure / water_utilities / new | L · $180m | — | — | ❌ attempt 1 |

Classification on all six profiles is correct, including the three that never
got a PMP. Launch is the story for R8, not taxonomy.

---

## The headline measurement: R8 is not live until ingest lands

47, 53 and 62 failed for the same reason, on attempt 1, before any draft:

```
Create PMP could not load mandatory platform sources:
  seed/institution-construction-guide.md …
  seed/mixed-use-construction-guide.md …
  seed/infrastructure-construction-guide.md …
Ingest seed/ and docs/clerk-brief.md into the platform corpus.
```

R8 authored those three files, marked them `required_by: {create-pmp: 1}`, and
wired required sections in `pmp-section-seed-map.json`. They were on disk. They
were not rows in the live `sitewise-platform` corpus. Residential / commercial /
industrial guides already were, which is why 13 / 23 / 34 launched.

**Ingest status (2026-08-14 12:04 UTC).** The three missing files are now
persisted as platform knowledge:

| Path | Chunks |
|---|---:|
| `seed/institution-construction-guide.md` | 13 |
| `seed/mixed-use-construction-guide.md` | 12 |
| `seed/infrastructure-construction-guide.md` | 13 |

That unblocks launch. It does **not** close R8. Close R8 only when a re-run of
47 / 53 / 62 cites those files in Trace **and** the distinctive checks appear
in the body (AusHFG / ICRA / live ED; two NCC classes / fire-acoustic
separation / strata; process design / drinking-water regulator / proving).

The three controls that did launch already show the second half of that test
failing. The class guides exist in the corpus and do not drive the document.

Identical-line similarity (R3 gate **< 70%**):

| Comparison | Identical lines |
|---|---:|
| 13 vs 23 | **25.6%** |
| 13 vs 34 | 30.1% |
| 23 vs 34 | **43.4%** |

All three pairs are under the gate. Scale and class still change the document.
That is not the Wave 4 question.

---

## Per-run sheets

Scores: **0** = fail · **1** = partial · **2** = pass.

### Run 1 — Prompt 13, House knock-down rebuild (`13.4`)

| Field | |
|---|---|
| Expected | residential / house / new · M |
| Actual | residential / house / new · band **S** · $1.6m · Wollongong |
| C1 Classification | **2** — class, subclass and work type correct. Band S is the taxonomy reading of $1.6m, not a mis-class |
| C2 Input retention | **1** — address, Petrakis, 2 storey / 4 bed / 3 bath / double garage / pool / $1.6m retained. **`start on site early next year` is absent** |
| C3 Section applicability | **1** — demolition is in work_scope and Brief; FFE is a populated residential typical register. Pool is a bullet, not a separate Class 10b / barrier package |
| C4 Section absence | **0** — corpus checks were DA pathway, pool fencing compliance, BASIX. None of those words appear. The residential guide has all three |
| C5 Consultant **[J]** | **1** — Structural Engineer is design lead because superstructure is in work_scope. A house knock-down rebuild still wants an architect on the register |
| C6 Scale | **2** — 952 words, S target 1,100, band 770–1595. Stayed on the short scaffold (no L-band length expansion) |
| C7 Doctrine **[J]** | **0** — Trace lists only `seed/ncc-reference-guide.md#compliance-pathways-and-documentation`. `residential-construction-guide.md` is ingested, required for house/new, and not cited. BASIX and AS 1926 pool barriers from that guide never reach the body |
| C8 Invention | **2** — no fabricated appointments or rates |
| C9 Register **[J]** | **1** — usable scaffold for a first owner send; not a knock-down-rebuild PMP until DA / BASIX / pool barrier / enabling works are named |
| **Categories** | `DOCTRINE`, `SECTION-SET`, `DISCIPLINE` |

### Run 2 — Prompt 23, Office new (`23.4`)

| Field | |
|---|---|
| Expected | commercial / office / new · L |
| Actual | commercial / office / new · band L · Grade A · 12 storeys · 18,000 m² NLA |
| C1 Classification | **2** |
| C2 Input retention | **0** — 12 storeys, 18,000 m², Grade A, $140m survive. **`Target 5 star Green Star` and `Target 5.5 NABERS` are in `scope_narrative` and do not appear anywhere in the PMP.** CBD site correctly becomes an address Assumption |
| C3 Section applicability | **2** — façade consultant, base-build vs tenant boundary, DA/SSD pathway, commissioning. The right commercial furniture |
| C4 Section absence | **0** — corpus checks were Green Star / NABERS as programme-critical, with commissioning and tuning. Commissioning is generic. Rating tools are missing. The commercial guide has a dedicated Green Star / NABERS section |
| C5 Consultant **[J]** | **1** — Architect / design lead. `work_scope` is empty; R4 said that case prints “Design lead — to be confirmed” |
| C6 Scale | **2** — 1,937 words, L target 1,900 |
| C7 Doctrine **[J]** | **0** — no loaded-seed line in Trace. Length expansion replaced the scaffold Trace. `commercial-construction-guide.md` is not in `pmp-section-seed-map.json` at all — catalog `required_by` only — so even a perfect Trace would not list Green Star sections |
| C8 Invention | **0** — “tenancy strategy not provided” / rating targets omitted against a populated narrative. Same W3-1 shape as retail/warehouse |
| C9 Register **[J]** | **1** — would survive a first client send if the rating targets were in Programme and Cost |
| **Categories** | `INPUT-LOSS`, `DOCTRINE`, `DISCIPLINE` |

### Run 3 — Prompt 34, Cold storage (`34.4`)

| Field | |
|---|---|
| Expected | industrial / cold_storage / new · L |
| Actual | industrial / cold_storage / new · band L · 8,000 m² GFA |
| C1 Classification | **2** |
| C2 Input retention | **1** — 8,000 m² and $45m retained. **`Freezer chambers operating at approximately -25°C` and `Ammonia refrigeration system` are in `scope_narrative`, then the operational profile calls temperature zones and refrigeration plant Assumption** |
| C3 Section applicability | **2** — thermal envelope, refrigeration plant row, fire/BMS, cold-chain cost split. Mechanical leads the register (mechanical_hvac in work_scope) — better than Architect |
| C4 Section absence | **0** — corpus checks were ammonia safety, bunding, leak detection, insulated-panel fire, vapour barrier, underfloor heating, refrigeration as a specialist package, pull-down commissioning. Vapour is a one-line Assumption. The rest are absent |
| C5 Consultant **[J]** | **2** — Services Engineer (Mechanical) heads the register. Fire, electrical, BMS present. No refrigeration specialist named, which is the missing package |
| C6 Scale | **2** — 1,855 words, L band |
| C7 Doctrine **[J]** | **0** — no loaded-seed line. `industrial-construction-guide.md` names cold store as a subtype in the opener and does not carry ammonia / panel-fire / pull-down doctrine. Even a loaded class guide would not have closed these checks |
| C8 Invention | **1** — treating stated −25 °C and ammonia as unknown |
| C9 Register **[J]** | **1** — reads as a generic industrial shed with a cold-chain cost note, not a hazardous refrigeration project |
| **Categories** | `INPUT-LOSS`, `DOCTRINE`, `SECTION-SET` |

### Runs 4–6 — Prompts 47, 53, 62 (no PMP)

| Field | 47 Hospital | 53 Residential over retail | 62 Water treatment |
|---|---|---|---|
| Expected | institution / healthcare_hospital / refurb · L | mixed / residential_retail / new · L | infrastructure / water_utilities / new · L |
| Actual profile | ✅ institution / healthcare_hospital / refurb · $85m · ED cannot close | ✅ mixed / residential_retail / new · $46m · Marrickville · 8 storey / 54 apts | ✅ infrastructure / water_utilities / new · $180m · 40 ML/day |
| C1 Classification | **2** | **2** | **2** |
| C6 / C7–C9 | n/a — no artefact | n/a | n/a |
| Launch | **0** — missing `institution-construction-guide.md` | **0** — missing `mixed-use-construction-guide.md` | **0** — missing `infrastructure-construction-guide.md` |
| **Categories** | `WORKFLOW-LAUNCH` | `WORKFLOW-LAUNCH` | `WORKFLOW-LAUNCH` |

Do not grade body quality on these until the re-run. The profiles already have
the facts the PMP must keep: live ED / two theatres / $85m; Marrickville / 5
shops / 54 apartments / $46m; 40 ML/day / inlet–filtration–chlorination–storage–
pumping / $180m.

---

## Aggregated defect list

Ordered by leverage. Counts are out of the six Wave 4 runs.

| ID | Category | Defect | Count | Repo area |
|---|---|---|---|---|
| **W4-0** | `WORKFLOW-LAUNCH` | **R8 guides were required before they were ingested.** Institution / mixed / infrastructure PMPs hard-fail. Residential / commercial / industrial already in the corpus, so those three launched. Ingest of the three files is now done; launch is not re-measured until 47 / 53 / 62 are re-run | 3/6 | `ingest` platform corpus; `create_pmp.retrieve_create_pmp_sources` |
| **W4-1** | `DOCTRINE` | **Class guides still do not appear in Trace, and do not drive the distinctive checks, even when they are already ingested.** 13 cites NCC only. 23 / 34 have no loaded-seed line (L-band length expansion replaces the scaffold Trace). 23’s commercial guide has Green Star / NABERS and is not in the section seed map. 13’s residential guide has BASIX and pool barriers and they never render | 3/3 completed | `pmp-section-seed-map.json`; Trace rendering; length-expansion pass |
| **W4-2** | `INPUT-LOSS` | **Populated `scope_narrative` is then denied or dropped.** 23: Green Star / NABERS absent. 34: −25 °C and ammonia rendered Assumption. Same shape as W3-1 | 2/3 completed | `pmp_renderer.py`; length-expansion model pass |
| **W4-3** | `SECTION-SET` | **Class-specific packages are missing.** 13: no BASIX, no DA named, no pool barrier. 34: no ammonia / bunding / panel fire / pull-down. 34 is also a seed-coverage hole — the industrial class guide does not carry those sections | 2/3 completed | class-guide section map; industrial cold-storage overlay |
| **W4-4** | `DISCIPLINE` | **Empty `work_scope` still names Architect as design lead** (23). 13 leads Structural on a house because superstructure is selected | 2/3 completed | `design_lead_discipline` |

W3-0 (scale / similarity) is not re-opened. 13 / 23 / 34 are in band and pairwise
similarity is 26–43%.

---

## What Wave 4 does not need to re-open

- **Queue isolation (R0).** `queue_scope: dev` on every run, including the three failures.
- **Band enforcement (R2).** The three completed PMPs are in band. 13 is S, not M, because $1.6m is below the S ceiling.
- **Similarity gate (R3).** Every completed pair is under 50%.
- **Classification.** All six profiles, including the failed launches, landed on the expected class / subclass / work type.

---

## Re-run instruction

Same three projects, not new ones. Create PMP again on:

- `47.4 Hospital redevelopment`
- `53.4 Residential over retail*`
- `62.4 Water treatment plant`

R8 is live-closed only if Trace cites the matching class guide **and** the
corpus checks are in the body. Unit routing tests are not that proof.
