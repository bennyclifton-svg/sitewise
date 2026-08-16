# Wave 3 Test Outcome Sheet

**Run date:** 2026-08-14 (10:17–11:17 UTC) · **Prompts run:** corpus 5, 26, 31, 35 · **Graded:** 2026-08-14

> Wave 3 is scale proportionality: the same product, four budgets, documents that should get longer and
> more ceremonial as the number goes up. Pair 5 vs 26 is the clean diagnostic (both
> `commercial / retail_standalone`, XS vs M). 31 and 35 are industrial M vs L.

**Grading provenance.** C1–C4, C6 and C8 are mechanically verified against the database, the generation
manifest and the artefact text. C5, C7 and C9 are marked **[J]**.

**Attribution.** All four PMPs record `build_version: bfe7a350-dirty`, `queue_scope: dev`,
`compiler: adaptive_scaffold`, `attempt: 1`, `state: complete`. Production API has
`WORKFLOW_WORKER_INPROC_ENABLED=false` and there is no core workflow worker container, so these runs
are the working tree. The `-dirty` suffix is the uncommitted corpus “Need a PMP.” lines on these four
prompts.

Artefacts: [`w3-05-roof--create_pmp.md`](artefacts/w3-05-roof--create_pmp.md),
[`w3-26-retail--create_pmp.md`](artefacts/w3-26-retail--create_pmp.md),
[`w3-31-warehouse--create_pmp.md`](artefacts/w3-31-warehouse--create_pmp.md),
[`w3-35-datacentre--create_pmp.md`](artefacts/w3-35-datacentre--create_pmp.md).

---

## What was produced

| # | Prompt | Project | Class / subclass / work type | Band | Words | In band | PMP |
|---|---|---|---|---|---:|---|---|
| 5 | Roof replacement and waterproofing | `5.3 Roof replacement and waterproofing` | commercial / retail_standalone / **remediation** *(expected refurb)* | XS · $160k | **767** | ✅ 489–1015 | ✅ v1 |
| 26 | Standalone retail | `26.1 Standalone retail` | commercial / retail_standalone / new | M · $7m | **1,570** | ✅ 1050–2175 | ✅ v1 *(cost plan also completed)* |
| 31 | Warehouse | `31.1 Warehouse` | industrial / warehouse / new | M · $18m | **1,361** | ✅ 1050–2175 | ✅ v1 |
| 35 | Data centre | `35. Data centre` | industrial / data_centre / new | L · $180m | **1,943** | ✅ 1330–2755 | ✅ v1 |

**Four prompts, four PMPs, four in-band.** Launch is no longer the story.

---

## The headline measurement: scale now changes the document

Wave 2’s L-band rail station was **786 words against a 1,330 floor** — the same length as the XS control.
R2’s proof condition was approximately **700 versus approximately 1,900**, not 795 versus 786.

| | Wave 1 roof (XS) | Wave 2 rail (L) | Wave 3 roof (XS) | Wave 3 retail (M) | Wave 3 warehouse (M) | Wave 3 data centre (L) |
|---|---:|---:|---:|---:|---:|---:|
| Words | 1,145 | 786 | **767** | **1,570** | **1,361** | **1,943** |
| Target | — | 1,900 | 700 | 1,500 | 1,500 | 1,900 |
| vs floor | n/a | −41% | +10% | +5% | −9% of target, still in band | +3% of target |

5 → 35 is **767 vs 1,943** (2.5×). Band targets are 700 vs 1,900 (2.7×). Ceremony follows the count: the
XS document is a short scaffold; M and L open into three-stage programmes, procurement-route widgets,
and eight-row risk registers.

Identical-line similarity (R3 gate was **< 70%** for pairs that differ in class, work type and band):

| Comparison | Identical lines | Notes |
|---|---:|---|
| 5 vs 26 | **27.9%** | same subclass, XS vs M — the diagnostic pair |
| 5 vs 31 | 26.1% | |
| 5 vs 35 | 27.8% | class + work + band all differ |
| 26 vs 31 | **49.5%** | both band M, different class |
| 26 vs 35 | 23.3% | |
| 31 vs 35 | 25.5% | industrial M vs L |

Wave 1 was 94–98%. Wave 2’s worst pair was 94.7%. **No Wave 3 pair is above 50%.** R2 and R3 have landed
on live artefacts, not only in unit tests.

---

## Per-run sheets

Scores: **0** = fail · **1** = partial · **2** = pass.

### Run 1 — Prompt 5, Roof replacement (`5.3`)

| Field | |
|---|---|
| Expected | commercial / retail_standalone / **refurb** · XS |
| Actual | commercial / retail_standalone / **remediation** · band XS |
| C1 Classification | **1** — class and subclass correct; work type is remediation because the agent selected `waterproofing_rectification`. Refurb already has `roofing` and `waterproofing`. A leaking occupied-building roof replacement is refurbishment, not a remediation project |
| C2 Input retention | **1** — 4/6. Metal roof, leak, box gutters, $160k retained in Brief/Cost. **`Tenant trading throughout` is absent** — the operational constraint that should have driven the programme |
| C3 Section applicability | **1** — FFE schedule is a one-row waterproofing-membrane stub. Exterior finishes are in-scope under R7; an empty typical row on a $160k roof job is still noise |
| C4 Section absence | **0** — no weather contingency, no temporary weatherproofing, no trading-hours restriction, no working-at-heights, no asbestos check on a 30-year-old-looking metal roof |
| C5 Consultant **[J]** | **1** — Waterproofing Consultant leads (from the rectification scope). Not Architect. Corpus wanted a building surveyor only if structural; a roofing contractor is never named |
| C6 Scale | **2** — 767 words, target 700, band 489–1015. Short relative to the other three. This is the R2 proof on the XS side |
| C7 Doctrine **[J]** | **0** — generation trace loads only `ncc-reference-guide.md#compliance-pathways-and-documentation`. `work_type: remediation` should have pulled `building-remediation-rectification-guide.md` (R9). Neither the commercial class guide nor the rectification guide is visible |
| C8 Invention | **1** — “Remediation / rectification works” as the Description lead is the work-type error written into the document |
| C9 Register **[J]** | **1** — readable scaffold; too generic to send as a roofing PMP |
| **Categories** | `CLASSIFY`, `INPUT-LOSS`, `DOCTRINE`, `SECTION-SET` |

### Run 2 — Prompt 26, Standalone retail (`26.1`)

| Field | |
|---|---|
| Expected | commercial / retail_standalone / new · M |
| Actual | commercial / retail_standalone / new · band M · `gla_sqm: 3200` |
| C1 Classification | **2** |
| C2 Input retention | **1** — 3/5. 3,200 m², highway, $7m survive. **`bulky goods` never appears. `Single tenant pre-committed` is inverted:** Description says “tenant commitment … are not evidenced” against a populated `scope_narrative` |
| C3 Section applicability | **2** — FFE, DA pathway, shell-vs-fitout boundary are the right sections for a new retail box |
| C4 Section absence | **1** — AFL/lease driving specification is only a demarcation row. RMS/highway access is an “unverified interface”, not a programme driver. “Simple structure, fast programme” became a full three-stage DA regime |
| C5 Consultant **[J]** | **1** — Architect / design lead. Work scope is empty; R4 said that case prints “Design lead — to be confirmed”, not Architect |
| C6 Scale | **2** — 1,570 words, target 1,500 |
| C7 Doctrine **[J]** | **1** — no loaded-seed line in Trace. Class 6 / DA / highway content is commercial-shaped, but `commercial-construction-guide.md` is not cited |
| C8 Invention | **0** — “Physical scope, tenant commitment, highway interface and operating conditions are not evidenced” is false. Those three are in the profile |
| C9 Register **[J]** | **1** — would survive a first client send if the Description stopped denying the brief |
| **Categories** | `INPUT-LOSS`, `REGISTER`, `DISCIPLINE` |

### Run 3 — Prompt 31, Warehouse (`31.1`)

| Field | |
|---|---|
| Expected | industrial / warehouse / new · M |
| Actual | industrial / warehouse / new · band M · Eastern Creek · `gfa_sqm: 12000`, `dock_doors: 8`, `clear_height_m: 12` |
| C1 Classification | **2** |
| C2 Input retention | **1** — 5/6. 12,000 m², 12 m, 8 docks, Eastern Creek, $18m retained. **`800 sqm office` is in `scope_narrative` and then rendered as Assumption** (“Office area is **Assumption**”; “office content” must be established) |
| C3 Section applicability | **2** — docks, slab, Class 7b fire, hardstand are the right furniture |
| C4 Section absence | **1** — no FM2 / floor flatness, no portal frame, no estate design guidelines, no ESFR / early suppression (hydrant AS 2419 only) |
| C5 Consultant **[J]** | **1** — Architect / design lead on empty work scope. Same R4 miss as 26 |
| C6 Scale | **2** — 1,361 words, in the M band. Shorter than the $7m retail M document; both legal |
| C7 Doctrine **[J]** | **1** — industrial content is present (Class 7b, docks, slab loading). `industrial-construction-guide.md` is not cited in Trace |
| C8 Invention | **1** — treating the stated 800 m² office as unknown |
| C9 Register **[J]** | **1** |
| **Categories** | `INPUT-LOSS`, `REGISTER`, `DISCIPLINE` |

### Run 4 — Prompt 35, Data centre (`35`)

| Field | |
|---|---|
| Expected | industrial / data_centre / new · L |
| Actual | industrial / data_centre / new · band L · `it_load_mw: 15`, `redundancy_tier: 3` |
| C1 Classification | **2** |
| C2 Input retention | **1** — 4/5. 15 MW, tier 3, $180m, site-clearance/earthworks retained. **`N+1 across power and cooling` is in `scope_narrative` and does not appear**; the document speaks “redundancy tier 3” instead |
| C3 Section applicability | **2** — BMS, security, ICT, resilience, utility feasibility, commissioning are the right set. FFE is thin but not a tenancy stub |
| C4 Section absence | **1** — no Uptime Institute, no substation lead time as critical path, no Level 1–5 commissioning cascade. Utility feasibility and generic commissioning are present |
| C5 Consultant **[J]** | **1** — Structural Engineer heads the register (superstructure in work_scope). Electrical and mechanical are listed. For a 15 MW data centre the design lead should be electrical or mechanical, not structural |
| C6 Scale | **2** — 1,943 words, target 1,900, band 1330–2755. This is the R2 proof on the L side |
| C7 Doctrine **[J]** | **1** — SOCI / high-security caveats, resilience interface register, 15 MW / tier-3 package split. Industrial class guide still not named in Trace |
| C8 Invention | **2** — DA is labelled a working placeholder. High-security is explicitly not a SCIF brief |
| C9 Register **[J]** | **2** — the first document in the four that a PM could send with a covering note |
| **Categories** | `INPUT-LOSS`, `DISCIPLINE` |

---

## Aggregated defect list

Ordered by leverage. Counts are out of the four graded runs.

| ID | Category | Defect | Count | Repo area |
|---|---|---|---|---|
| **W3-0** | `SCALE` | **Closed.** All four word counts sit inside their band. 5 vs 35 is 767 vs 1,943. Similarity 23–50%. Wave 2’s W2-4 is not reproduced | 0/4 | `pmp_length.py`; adaptive scaffold |
| **W3-1** | `REGISTER` / `INPUT-LOSS` | **Stated scope_narrative is then denied in the Description.** 26: “tenant commitment … not evidenced”. 31: 800 m² office rendered Assumption. 35: N+1 dropped for `redundancy_tier`. R5 stopped “not stated” on empty profile fields; the new failure is contradicting a populated narrative | 3/4 | `pmp_renderer.py`; `pmp_greenfield_brief.py` |
| **W3-2** | `DOCTRINE` | **Class and overlay guides still do not show up in Trace on live artefacts.** Prompt 5 (remediation) loads only the NCC compliance fragment — R9’s rectification guide is not in the generation trace. 26/31/35 have no loaded-seed line at all | 4/4 | seed routing into adaptive scaffold / hybrid narrative |
| **W3-3** | `DISCIPLINE` | **Empty work_scope still names Architect as design lead** (26, 31). R4’s “to be confirmed” path is not what rendered. Prompt 35 leads with Structural Engineer on a 15 MW electrical/mechanical facility | 3/4 | `design_lead_discipline`; empty-scope fallback |
| **W3-4** | `CLASSIFY` | **Occupied roof replacement classified as remediation** because `waterproofing_rectification` exists and `roofing` under refurb was not chosen. Class/subclass were right | 1/4 | agent instructions; `work-scopes.json` labels |
| **W3-5** | `SECTION-SET` | **XS roof PMP still carries a typical FFE row and omits the occupied-building programme** (trading, temporary weatherproofing, heights, asbestos) | 1/4 | FFE applicability; scaffold expansion for live operations |

### Categories used

The corpus list, plus `REGISTER` as the R5 leftover.

---

## What Wave 3 does not need to re-open

- **Queue isolation (R0).** `queue_scope: dev` on every artefact. Production inproc worker is off.
- **Band enforcement (R2).** Four of four in band; L is 1,943 not 786.
- **Similarity gate (R3).** Every pair under 50%.
- **Launch reliability.** Four of four PMPs on attempt 1.

Wave 4 (class breadth: 13, 23, 34, 47, 53, 62) is now the right next corpus wave. Do not run it to
re-measure scale; run it to see whether institution / mixed / infrastructure class guides actually
appear in the document, which Wave 3 Trace says they still do not.
