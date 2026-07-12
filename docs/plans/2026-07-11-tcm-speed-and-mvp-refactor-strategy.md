# TCM Speed and MVP Refactor Strategy

Date: 2026-07-11

Status: proposed strategy (supersedes speed assumptions in the 2026-07-10 plan where they conflict)

Audience: product owner + implementation agents

Related:

- `docs/plans/2026-07-10-integrated-agentic-workflows-performance.md` (integration OS plan — keep)
- `docs/plans/2026-06-11-tender-comparison-module-prd.md` (TCM internals — keep)
- July Hermes foundation plans (agent runtime — keep)

---

## 1. Verdict

Tender Comparison is slow because of **many sequential LLM round-trips over extracted quote line items**, not because the taxonomy “ledger” has ~100 cells.

Shrinking the taxonomy from ~100 cells to ~10 would **not** get you under one minute. It would destroy comparison usefulness and only slightly shrink T3 prompts. The real loop is:

```text
for each quote:
  for each extracted line item:   # tens to low hundreds per quote
      T0 synonym → else T1 embedding → else T2 LLM → else T3 frontier LLM
```

That loop is **strictly serial** today (`backend/tender/services/mapping.py` `map_items`). With weak synonym coverage, most items hit T2/T3. At ~2–8 s per LLM call, 50–80 items × 3–5 quotes is minutes of wall clock before ingest and extract even finish.

The July 10 plan correctly diagnoses **product locality** (UI vs chat vs workflows) and sets a **60 s goal / 90 s stretch** for a three-quote fixture. It does **not** yet contain the concrete TCM algorithm changes required to hit that number. This document fills that gap and reorders delivery so speed is a first-class release gate, not a Phase 6 afterthought.

---

## 2. What the five MVP modules actually are

| Module | Role today | Agent-ready? | Coupling |
| --- | --- | --- | --- |
| Document repository | Shared upload / workspace / evidence hub | Read/search MCP yes | Feeds everything |
| Chat | Dual path: legacy RAG + Hermes/MCP (agent off by default) | Wired, gated | Can start TCM; cannot run PMP/Cost create |
| Project Plan (PMP) | Strong cockpit workflow → draft artefact | No create MCP tool | Uses RAG evidence |
| Cost Plan | Strong cockpit workflow → markdown + workbook | Forecast/read MCP only | **Not** consumed by TCM |
| Tender Comparison | Full queue pipeline + matrix + QA + report | MCP start/status yes; worker often off | Uses workspace files via separate ODL ingest; internal taxonomy ledger ≠ Cost Plan |

Critical product confusion to kill:

- **Clerk Cost Plan** = project budget artefact (`01-cost/`, workbook).
- **TCM taxonomy / comparable ledger** = Class 1 cell grid (~100 cells now; PRD aims 180–250) used to normalise builder quotes.

They are not the same object. TCM does not map quote lines onto the Cost Plan workbook. Mapping quote lines onto taxonomy cells is the slow path.

---

## 3. Why a run takes 5–10 minutes

### 3.1 Measured architecture (code-backed)

Pipeline per document/quote:

1. `ingest_document` — ODL PDF + page PNG render + storage (no LLM; often 15–40 s/doc)
2. `classify_document` — 1 small LLM
3. `extract_line_items` — 1 large structured LLM over full document text
4. `embed_items` — batched embeddings
5. `map_items` — **0–2 LLM calls per line item, sequential**
6. Comparison barriers → expectations → silence batch LLM → analysis → flags → report

Worker: max **4** parallel jobs, **2 s** idle poll. No in-handler `asyncio.gather` for mapping. T3 sends **all active taxonomy cells** (~100) on every frontier call.

### 3.2 Ranked bottlenecks

| Rank | Bottleneck | Why it hurts | Typical share of 5–10 min |
| --- | --- | --- | --- |
| 1 | Sequential `map_items` | LLM latency × line items × quotes | 40–60% |
| 2 | Low T0/T1 hit rate | Forces T2/T3; early synonym coverage is thin | amplifies #1 |
| 3 | Per-document extract LLM | Large prompt + long generation | 15–25% |
| 4 | PDF ingest (ODL + PNG + upload) | JVM + sequential pages | 15–30% |
| 5 | Fine-grained jobs + 2 s poll | Stage gaps add tens of seconds | 5–10% |
| 6 | T3 full-taxonomy prompts | Slow frontier model + huge input | spikes when T3 share high |
| 7 | Deterministic analysis/report | Negligible | <5% |

### 3.3 Worked example (3 quotes × ~60 line items, mediocre synonyms)

Assume 50% need T2 (~3 s), 10% escalate to T3 (~8 s), serial mapping:

- Mapping alone: 3 × (30×3 + 6×8) ≈ **414 s** (~7 min)
- Add ingest + extract + queue overhead → **8–12 min**

Same run with parallel mapping (16 concurrent) and 70% T0/T1:

- Mapping: roughly **20–40 s**
- Full cold pipeline still needs ingest/extract work → **~90–150 s** unless those are cached or parallelised harder

### 3.4 Honest answer on “under one minute”

| Definition of “done” | Feasible? | What it takes |
| --- | --- | --- |
| Cold start: upload 3 PDFs → QA-ready matrix in ≤60 s | **Hard / maybe not** on first run | Needs extract cache, parallel ingest, parallel map, high T0/T1, and possibly deferred PNG/QA assets |
| Warm: files already ingested once → compare ≤60 s | **Yes** | Parallel map + batch T2 + T3 routing + skip re-ingest |
| Perceived UX: first useful matrix rows in ≤20 s, complete ≤90 s | **Yes (best product bet)** | Progressive UI + same backend speed work |
| PRD five-quote ≤30 min excl. QA | Already met | Not the commercial bar |

**Recommendation:** ship a **hard gate of ≤90 s warm three-quote** and a **≤60 s goal**, with progressive matrix fill so the product never feels like a 10-minute black box. Do not claim cold ≤60 s until measured.

---

## 4. Do not shrink the taxonomy to 10 lines

### Why the instinct is wrong

- Comparison value lives in **cell-level gaps** (kitchen vs bathrooms vs prelims vs exclusions). Ten lines collapses that into a useless summary a frontier chat already does.
- Mapping cost scales with **extracted quote lines**, not taxonomy size, except for T3 prompt bulk.
- PRD already targets **more** cells (180–250), not fewer. Quality and QS acceptance need that resolution.
- Cost Plan row count is a separate product decision; shortening Cost Plan markdown does not speed TCM.

### What *does* help on the “ledger” side

1. **Hierarchical mapping** — first map to one of ~22 groups, then only to cells inside that group (shrinks T2/T3 choice set without deleting cells).
2. **Context-active cells only** — already partially true via expectations; enforce that T3 never sees inactive/out-of-context cells.
3. **MVP display rollup** — show 8–12 summary groups in the first viewport; keep full cell grid behind expand. UX compression ≠ taxonomy deletion.
4. **Synonym flywheel** — every QA correction becomes a T0 hit next time. This is the PRD cost flywheel and the highest leverage quality+speed lever.

---

## 5. Path to sub-minute Tender Comparison

### Sprint S0 — Measure (2–3 days)

Without this, every optimisation is guesswork.

1. Wire real `llm_calls` / token counts from `tender/llm/openai_client.py` into `telemetry.record_stage_timing`.
2. Add per-tier counters inside `map_items` (t0/t1/t2/t3 counts + durations).
3. Add full-pipeline fixture: 3 real quotes, cold and warm, stage ledger to `docs/performance/tender/`.
4. Expose stage timings on progress API (or debug endpoint) so cockpit shows where time went.

Gate: one comparison produces a stage ledger with non-zero LLM stats.

### Sprint S1 — Kill serial mapping (highest ROI, ~1 week)

Files: `backend/tender/services/mapping.py`, worker session handling, focused tests.

1. Parallelise line-item cascade with a bounded semaphore (start at 8, measure 16).
2. Use short-lived sessions or carefully scoped DB work so concurrent awaits do not share one AsyncSession unsafely.
3. Batch T2 adjudications via `adjudicate_many` (same pattern as silence) for items that need T2.
4. Cache `active_cells` once per `map_items` job (already loaded repeatedly on T3 path).
5. Keep arithmetic/QA rules unchanged.

Gate: warm three-quote mapping stage ≤25 s on the fixture; quality tests unchanged.

### Sprint S2 — Raise free-tier hit rate (ongoing, start immediately)

1. Seed synonyms from the three flagship PDFs’ ground-truth mappings (manual or eval annotations).
2. Ensure QA corrections write synonym candidates and get promoted.
3. Tune T1 accept thresholds only with eval (PRD §14) — do not guess.

Gate: fixture T0+T1 share ≥60%; T3 share ≤10%.

### Sprint S3 — Shrink expensive calls without deleting cells (~1 week)

1. **Group-then-cell routing** for T2/T3: choose group first, then cells in group.
2. T3 receives only candidate group cells (or top-K by embedding), never the full 100-cell dump.
3. Chunk or section extract for long quotes if extract stage dominates the ledger.
4. Content-hash raw extraction cache keyed by `(project_id, content_hash, extractor_version)` — never cross-project.

Gate: T3 median input tokens down ≥70%; extract warm cache hit skips LLM.

### Sprint S4 — Ingest and queue overhead (~3–5 days)

1. Parallel page upload within a document where storage allows; keep ODL JVM contention bounded.
2. Coalesce classify+extract into one job to remove poll gaps.
3. Drop idle poll toward 0.25–0.5 s when the queue is non-empty (or wake-on-enqueue).
4. Defer page PNG generation until QA opens an item (matrix/report can use text+coords first).

Gate: warm re-compare of already-ingested files skips ingest entirely; cold three-PDF ingest ≤45 s or PNGs deferred.

### Sprint S5 — Product perception (frontend, ~3 days)

1. Progressive matrix: show mapped cells as each quote’s `map_items` completes.
2. Stage timing strip on Tender cockpit (reuse progress milestones + new durations).
3. Default path: “Compare selected” assumes files already in repo (warm path).

Gate: user sees first mapped rows ≤20 s on warm fixture.

### Target budgets after S1–S5 (three-quote warm)

| Stage | Budget |
| --- | --- |
| Skip ingest / use cache | 0–5 s |
| Classify + extract (cached or parallel) | ≤20 s |
| Embed | ≤5 s |
| Map (parallel + high T0/T1) | ≤25 s |
| Silence + analysis + report draft | ≤10 s |
| Queue overhead | ≤5 s |
| **Total warm** | **≤60–70 s** |

Cold first-time with PDF ingest: **≤90–120 s** stretch until PNG deferral + extract cache land.

---

## 6. Review of the 2026-07-10 integrated plan

### Keep (correct and necessary)

- UUID project-evidence tenancy (Phase 0) before broader agent write power.
- Shared Project Profile / Decisions / Snapshot / Capability (R1).
- Artefact Revision + durable Workflow Run so buttons and chat share one path (R2).
- Typed Cost Plan + approved-Tender **proposal** handoff (R4) — this is how Cost Plan and TCM finally connect.
- Event outbox + frontend reconciliation.
- TCM boundary rules (no RAG chunks, Python arithmetic, eval before prompt/model changes).
- Additive release gates; no early Phase 8.5 deletion.

### Fix / re-prioritise

| Issue in July 10 plan | Correction |
| --- | --- |
| TCM speed buried in Phase 6 after large OS work | Pull **S0–S5 speed sprints** forward in parallel with Phase 0/1; commercial viability depends on it |
| 60 s listed as goal but optimisation packets are “measure then invent” | This doc names the packets: parallel map, batch T2, hierarchical T3, extract cache, PNG deferral |
| Implies full-pipeline ≤90 s without defining warm vs cold | Split warm/cold gates explicitly |
| Integration depth before flagship feel | Ship **fast Tender + progressive UI** as R0 commercial gate alongside tenancy |
| Plan is excellent for “one OS” but easy to execute as a 3-month architecture march | Time-box OS phases; never block S1 mapping parallelism on Profile/Artefact work |

### What the July 10 plan is *not*

It is not a TCM algorithm redesign. Following it alone will make Clerk coherent and agentic, but **will not by itself** turn a 10-minute comparison into a 1-minute one.

---

## 7. Full MVP → construction OS strategy

North star: Clerk is a **project operating system** where Document Repo, Profile, PMP, Cost Plan, Tender, and Chat are adapters over shared state — with Tender as the flagship proof that AI automation beats “paste into ChatGPT.”

### Release gates (reordered)

```text
R0  Fast Tender (this doc S0–S5) + progressive UI
    Gate: warm 3-quote ≤90 s (goal 60 s); first rows ≤20 s

R1  Safe tenancy + Project Profile/State (July 10 Phase 0–1)
    Gate: UUID evidence isolation; chat and UI share profile

R2  Durable PMP/Cost actions via Workflow Run + Artefact Revision
    Gate: button and chat create the same artefacts

R3  Tender intake correctness + eval/QS (July 10 Phase 2 + 6.4–6.5)
    Gate: atomic quote groups; eval thresholds; customer-safe reports

R4  Typed Cost Plan + approved Tender → proposed Cost revision
    Gate: no silent builder/budget acceptance

R5  Project intelligence snapshot + role acceptance + production cutover
    Gate: then Phase 8.5 legacy deletion
```

### Workstreams that can run in parallel

| Stream | Owner focus | Depends on |
| --- | --- | --- |
| A. TCM speed | tender/ mapping, telemetry, worker | Nothing from Profile |
| B. Tenancy + measurement | ingest IDs, retrieval UUID, timing | — |
| C. Project Profile/State | projects module, MCP, events | B for evidence UUID before broad release |
| D. Workflow Run + Artefact | PMP/Cost async parity | C snapshot/capability |
| E. Tender product correctness | selections, atomic intake, report scope | C snapshot; A for speed |
| F. Typed Cost + handoff | cost_plan module | D + R3 quality |

### Cross-module intelligence (the “next level”)

Only after R0–R2:

1. **One Project Snapshot** feeds PMP, Cost, Tender preparation.
2. **Persisted quote groups** in Document Repo (not ad-hoc file picks).
3. **Approved Tender handoff** creates a **proposed** Cost Plan revision with mapped codes — this is the first real CM automation loop.
4. **Accepted Cost summary** may offer PMP refresh — never a silent cycle.
5. Chat never “clicks around”; it calls the same typed commands as the UI.

Out of scope for MVP (do not boil the ocean): correspondence, RFIs, programme, site instructions. Those are later skills on top of the OS, not prerequisites.

---

## 8. Implementation packets (assignable)

### Packet A1 — Mapping parallelism

- Modify: `backend/tender/services/mapping.py`
- Test: new `backend/tests/tender/test_mapping_parallel.py`
- Behavior: bounded concurrent `map_line_item_cascade`; identical mapping outcomes on fixture
- Non-goals: prompt/model/taxonomy changes

### Packet A2 — Telemetry + full-pipeline speed fixture

- Modify: `llm/openai_client.py`, `services/telemetry.py`, `worker.py`, `services/progress.py`
- Create: `backend/tests/tender/performance/test_full_pipeline_speed.py`, `docs/performance/tender/`
- Behavior: stage ledger with llm_calls/tokens; warm/cold reports

### Packet A3 — Batch T2 + hierarchical T3 input

- Modify: `mapping.py`, prompts under `llm/prompts/` (eval required before merge)
- Behavior: T2 via `adjudicate_many`; T3 sees group-scoped cells only
- Gate: PRD eval thresholds hold

### Packet A4 — Extract content-hash cache + skip re-ingest on warm compare

- Modify: extraction/ingestion services + comparison intake
- Behavior: same project+hash returns cached raw extract; re-compare does not re-ODL

### Packet A5 — Progressive Tender UI

- Modify: `TenderMatrix`, progress strip, cockpit polling
- Behavior: matrix updates as quotes finish map; timings visible

### Packets B/C/D/E/F

Execute as written in `2026-07-10-integrated-agentic-workflows-performance.md`, with R0 speed packets unblocked.

---

## 9. Definition of done for “people will actually use this”

Tender Comparison is commercially viable when:

1. Warm three-quote comparison reaches QA-ready (or report-ready) in **≤90 s**, goal **≤60 s**.
2. User sees useful matrix content in **≤20 s**.
3. Cold first ingest of the same three PDFs is **≤120 s**, with a clear “already processed” warm path next time.
4. LLM cost stays within PRD budget (≤ A$15/comparison) and preferably drops as T0/T1 rise.
5. Quality does not regress on eval; silence still never auto-passes without QA where PRD requires review.
6. Chat and UI can start the **same** comparison from the **same** quote-group selection.
7. Taxonomy remains QS-useful (≥ current ~100 cells; hierarchical routing instead of deletion).

The broader OS is “next level” when R1–R4 also pass — but **R0 is the survival gate**. Without it, the other four MVP modules will not save the product.

---

## 10. Immediate next actions

1. Run one real comparison and capture stage timings (or implement Packet A2 first if timings are zeroed today).
2. Implement Packet A1 (parallel mapping) — largest single wall-clock cut.
3. Seed synonyms from that run’s QA/corrections (Packet S2).
4. Only then debate Cost Plan row count / taxonomy display rollups — as UX, not as the speed fix.
5. Keep executing July 10 Phases 0–1 in parallel for tenancy and agent/UI parity.
