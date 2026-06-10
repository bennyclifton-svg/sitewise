# Fast Retrieval By Document Class — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Prefer vertical slices; keep the existing hybrid chunk+vector path until the new paths are proven.

**Goal:** Make everyday Clerk chat (seed, doctrine, inventory, drawing register) feel as snappy as local folder-based Hermes, while keeping Supabase, grounded citations, and chunk+vector only for long reports.

**Architecture:** Strangler migration inside the existing chat pipeline. Add a **retrieval router** before `run_chat_turn` that picks a **profile** from `document_class` / `ingest_mode` / query intent. Reuse `source_documents.normalized_content` for whole-document paths. Do **not** remove pgvector or the PydanticAI agent until Phase 6+; route around them first.

**Principles (minimal change):**

1. **Derive before migrate** — map profiles from existing `document_class`, `ingest_mode`, and `document_metadata` before adding columns.
2. **One new module, thin wiring** — put routing + whole-doc loaders in `backend/app/retrieval/`; touch `orchestrator.py` and `chat.py` only at decision points.
3. **Fast paths return the same `GroundedAnswer`** — no frontend contract changes until streaming work (Phase 4).
4. **Measure every checkpoint** — use `debug_chat.py` + uvicorn logs; record `total_elapsed_ms` on `chat_turn_validated`.

**Tech stack:** Existing FastAPI, SQLAlchemy, Supabase Postgres, PydanticAI (cold path only), structlog.

**Related docs:** [architecture.md](../architecture.md), [phase-6-ingestion](2026-06-07-phase-6-ingestion.md), [clerk-practice-intelligence-integration-prd](2026-06-07-clerk-practice-intelligence-integration-prd.md).

---

## Document profiles (target behaviour)

| Profile | Document types | Ingest (target) | Query (target) | LLM |
| ------- | -------------- | --------------- | -------------- | --- |
| `whole_document` | doctrine, reference/seed, pinned spec | Full text in `normalized_content`; **no embed** | Load doc(s) by metadata/path or cheap FTS on `source_documents`; **no query embed** | Single call, no tools |
| `register_only` | drawings | Metadata in `document_metadata`; minimal text | SQL/JSONB filter | Often none |
| `inventory` | N/A (synthetic) | N/A | SQL listing | None |
| `chunked_vector` | long reports (default) | Chunk + embed (unchanged) | Current hybrid retriever | Simplified agent (later) |

**Phase 1 mapping (no migration):** derive profile in Python:

```text
doctrine | reference_guide + ingest_mode full_text  → whole_document
drawing + register_only                            → register_only
document_class report                              → chunked_vector (default path)
everything else                                    → chunked_vector (unchanged for now)
```

**Later (Phase 7):** `document_metadata.query_priority = full_text` for pinned specifications.

---

## Success metrics (manual benchmarks)

Run from `backend/` after each checkpoint:

```text
uv run python scripts/debug_chat.py "list the seed knowledge files you have ingested"
uv run python scripts/debug_chat.py "what is a PMP"
uv run python scripts/debug_chat.py "what are the main stages of a residential construction program"
```

| Checkpoint | Target `total_elapsed_ms` (debug script) | Notes |
| ---------- | ---------------------------------------- | ----- |
| After Phase 1 | Seed list **< 2s** | SQL-only, no LLM |
| After Phase 3 | Seed/doctrine Q&A **< 15s** | One LLM, no tools, no query embed |
| After Phase 4 | UI shows first tokens **< 3s** after send | Streaming UX |
| After Phase 5 | Ingest platform folder without embed API | Re-ingest `seed/`, `docs/clerk-brief.md` |
| After Phase 6 | Report Q&A still works | Regression on procurement/delivery reports |

Record baseline **before Phase 1** in the checkpoint table below.

---

## Checkpoint log (fill in during implementation)

| Date | Phase | Query | `total_elapsed_ms` | Pass? |
| ---- | ----- | ----- | ------------------ | ----- |
| 2026-06-07 | Baseline | (pending manual run) | | |
| 2026-06-07 | **1 done** | list seed files | SQL fast path; unit tests green | ✓ code |
| 2026-06-07 | **2–3 done** | what is a PMP | whole-doc load + single LLM, tools disabled | ✓ code |
| 2026-06-07 | **4 done** | all chat | SSE status events + UI progress label | ✓ code |
| 2026-06-07 | **5 done** | ingest seed/doctrine/drawings | skip chunk+embed; catalog uses document id | ✓ code |

---

## Phase 0 — Baseline timing (no behaviour change)

**Objective:** Make slow steps visible before changing logic.

### Tasks

- [ ] **0.1** Add `LOG_LEVEL=DEBUG` note to local dev checklist (optional).
- [ ] **0.2** Ensure `debug_chat.py` prints `total_elapsed_ms` from orchestrator (already logs `chat_turn_validated` — confirm visible).
- [ ] **0.3** Run the three benchmark queries; fill baseline rows in checkpoint log.
- [ ] **0.4** Confirm uvicorn prints `-> POST /chat/stream` and `chat_stream_start` for UI sends.

**Files:** none required (verification only).

**Done when:** Baseline table filled; team agrees targets above are acceptable.

---

## Phase 1 — Inventory & register SQL fast paths

**Objective:** Answer catalog/register questions with **no retrieval embed, no agent, no LLM**.

### Tasks

- [ ] **1.1** Add `backend/app/retrieval/profiles.py` — `RetrievalProfile` enum + `derive_profile(document_class, ingest_mode, metadata)`.
- [ ] **1.2** Extend `backend/app/chat/intent.py` — detect inventory questions (`seed files`, `platform knowledge`, `ingested`, `list seed`, …) without breaking existing catalog regex.
- [ ] **1.3** Add `backend/app/retrieval/inventory.py` — `list_seed_documents(session)`, `list_platform_documents(session, kind?)` querying `source_documents` + `document_metadata.sitewise_knowledge_kind`.
- [ ] **1.4** Add `backend/app/retrieval/register.py` — `list_drawings(session, filters?)` returning metadata rows for `document_class = drawing`.
- [ ] **1.5** Add `build_inventory_answer()` / `build_register_answer()` returning `GroundedAnswer` (reuse catalog answer patterns from `retrieval/catalog.py`).
- [ ] **1.6** Wire in `orchestrator.run_chat_turn` — if intent matches inventory → return inventory answer; if drawing register intent → register answer.
- [ ] **1.7** Unit tests: `tests/chat/test_intent.py`, `tests/retrieval/test_inventory.py` (no integration, mock session).

**Files (expected):**

- Create: `backend/app/retrieval/profiles.py`, `inventory.py`, `register.py`
- Modify: `backend/app/chat/intent.py`, `backend/app/chat/orchestrator.py`
- Test: `backend/tests/retrieval/test_inventory.py`, `backend/tests/chat/test_intent.py`

**Verify:**

- [ ] `debug_chat.py "list the seed knowledge files you have ingested"` completes **< 2s**, log shows **no** `retrieval_complete` / **no** `chat_turn_agent_complete`.
- [ ] UI same question shows answer quickly; uvicorn shows `chat_stream_end` with low `total_ms`.

**Done when:** Checkpoint log Phase 1 row passes for seed list query.

---

## Phase 2 — Whole-document loader (platform / doctrine)

**Objective:** Load full text from `source_documents` without chunk join, embed, or pgvector.

### Tasks

- [ ] **2.1** Add `backend/app/retrieval/whole_document.py` — `load_platform_documents(session, *, kinds, limit)` returning passages built from **full** `normalized_content` (one passage per doc, cap content chars via existing `assistant_passage_content_chars` or new whole-doc limit in settings).
- [ ] **2.2** Add optional cheap rank: `rank_documents_by_fts(session, query, candidates)` using **document-level** FTS — migration only if chunk FTS is insufficient (see 2.5).
- [ ] **2.3** Add `should_use_whole_document_path(query, filters, thread)` in router — default **on** for non-project-scoped chat and platform-scoped project chat; **off** when `cross_project` broad search is intentional (keep hybrid).
- [ ] **2.4** In orchestrator: if whole-doc path → load platform/doctrine docs → skip `DocumentRetriever.retrieve()` hybrid call.
- [ ] **2.5** *(Optional, only if needed)* Migration `00N_document_level_fts.py` — generated `tsvector` on `source_documents.normalized_content` + GIN index. Skip if SQL filter + in-memory keyword match on small corpus is enough.

**Files (expected):**

- Create: `backend/app/retrieval/whole_document.py`, `backend/app/retrieval/router.py`
- Modify: `backend/app/chat/orchestrator.py`, maybe `backend/app/config.py` (`whole_document_max_docs`, `whole_document_content_chars`)
- Maybe: `backend/alembic/versions/00N_document_level_fts.py`

**Verify:**

- [ ] `debug_chat.py "what is a PMP"` log shows **no** `query_embedding_complete` on hot path.
- [ ] `retrieval_complete` absent or replaced by `whole_document_load_complete` with `elapsed_ms` **< 500ms** (Sydney DB) or **< 2s** (remote DB).

**Done when:** Whole-doc load logged; embed step gone for platform Q&A.

---

## Phase 3 — Single-pass LLM for whole-document path

**Objective:** Replace PydanticAI tool loop with **one** `agent.run` (or direct model call) when passages are already loaded.

### Tasks

- [ ] **3.1** Add `run_whole_document_turn(session, user_text, passages, filters)` — calls agent **without** registering tool deps that trigger re-retrieval; pass `format_turn_instructions(None, passages)`.
- [ ] **3.2** Temporarily disable tools on whole-doc path **or** pass deps where `retriever.retrieve` is never called (minimal: branch in orchestrator before `run_agent_with_retry`).
- [ ] **3.3** Tighten `instructions.md` — clarify citations may use chunk/passage ids from **initial context** (fixes model calling `search_documents` unnecessarily).
- [ ] **3.4** Unit test: mock agent; assert `search_documents` tool not invoked for whole-doc orchestration branch.

**Files (expected):**

- Modify: `backend/app/chat/orchestrator.py`, `backend/app/assistant/instructions.md`, `backend/tests/chat/test_orchestrator.py`

**Verify:**

- [ ] `debug_chat.py "what is a PMP"` — single `chat_turn_agent_complete`; total **< 15s** locally (remote DB may be higher).
- [ ] No second `query_embedding_complete` with short query length in logs.

**Done when:** Checkpoint log Phase 3 row passes for PMP query.

---

## Phase 4 — Streaming UX (minimal)

**Objective:** User sees progress before the turn finishes; reduce “frozen UI” feel.

### Tasks

- [ ] **4.1** Emit an immediate SSE event from `post_chat_stream` before `run_chat_turn` (e.g. `{ "type": "data-status", "message": "Retrieving…" }` or AI SDK-compatible status part — match `@ai-sdk/react` expectations).
- [ ] **4.2** **Better:** stream real model tokens for whole-doc path using PydanticAI streaming API; fall back to current `stream_grounded_answer` only if streaming integration is too large for this slice.
- [ ] **4.3** Frontend: show status line in `ChatPanel` when status part received (small change to `StreamingIndicator` or parse data parts).

**Files (expected):**

- Modify: `backend/app/api/chat.py`, `backend/app/chat/streaming.py`, optionally `frontend/src/components/chat/ChatPanel.tsx`

**Verify:**

- [ ] Network tab shows first SSE bytes **< 1s** after POST.
- [ ] User sees non-empty feedback while waiting.

**Done when:** UI no longer appears dead for 30+ seconds on platform questions.

---

## Phase 5 — Ingest: skip embed/chunk for whole-doc & register profiles

**Objective:** Ingest faster; stop writing useless vectors for seed/doctrine/drawings.

### Tasks

- [x] **5.1** Map `ingest_mode` + `document_class` to skip rules in `ingest/pipeline.py`:
  - `register_only` → persist document only; **zero chunks** (delete existing chunks for that doc id on re-ingest).
  - `whole_document` (doctrine, reference_guide) → **zero chunks**; rely on `normalized_content` only.
- [x] **5.2** Skip `embed_texts()` when chunk list empty.
- [x] **5.3** Classify `report` → keep current chunk+embed path (`chunked_vector`).
- [ ] **5.4** Re-ingest `seed/` and `docs/clerk-brief.md`; confirm chunk count drops for those docs in DB.
- [x] **5.5** Update `docs/plans/2026-06-07-phase-6-ingestion.md` cross-reference (one paragraph, no full rewrite).

**Files (expected):**

- Modify: `backend/ingest/pipeline.py`, `backend/ingest/persist.py`, `backend/ingest/classify.py` (optional: explicit `retrieval_profile` in metadata JSONB without Alembic)
- Test: `backend/tests/ingest/test_pipeline.py` (unit: mock embed, assert not called for doctrine)

**Verify:**

- [ ] Ingest log shows no `embed_batch_complete` for seed files.
- [ ] Chat still answers seed questions after re-ingest (Phase 3 path).

**Done when:** Platform docs have no rows in `document_chunks` (or single legacy row cleaned up).

---

## Phase 6 — Report cold path only

**Objective:** Long reports use chunk+vector; default chat router does not hit hybrid for platform questions.

### Tasks

- [ ] **6.1** Set `document_class == report` (and optionally large PDF heuristic) to `chunked_vector` in router.
- [ ] **6.2** In orchestrator: if profile is `chunked_vector` → existing `DocumentRetriever` + agent tools (current behaviour).
- [ ] **6.3** Simplify agent on cold path later (optional sub-task): cap tool calls to 1, or remove tools when initial retrieval score is high.
- [ ] **6.4** Regression: `debug_chat.py` with a report-specific question against ingested delivery/procurement report still returns cited answer.

**Files (expected):**

- Modify: `backend/app/retrieval/router.py`, `backend/app/chat/orchestrator.py`
- Test: existing `tests/retrieval/test_retriever.py` stays green

**Verify:**

- [ ] Platform queries never log hybrid `retrieval_complete` with semantic timings.
- [ ] Report query still logs semantic/lexical fusion.

**Done when:** Phase 6 regression row in checkpoint log passes.

---

## Phase 7 — Pinned specifications (optional, small schema)

**Objective:** User marks one spec as “query in full”; load whole text like seed.

### Tasks

- [ ] **7.1** Add `document_metadata["query_priority"] = "full_text"` convention (no migration if JSONB sufficient).
- [ ] **7.2** API: `PATCH /projects/{id}/documents/{id}` or metadata flag on project — **minimal:** admin script first.
- [ ] **7.3** Whole-doc loader includes pinned project specs when `filters.active_project` set.
- [ ] **7.4** Cockpit UI toggle (defer if scope creep — script-only is OK for first slice).

**Done when:** Pinned spec question loads full spec text without chunk search.

---

## Phase 8 — Cleanup & deprecation (only after metrics green)

**Objective:** Remove dead code paths; document the new default.

### Tasks

- [ ] **8.1** Update `docs/architecture.md` — retrieval router diagram; note chunk+vector is report cold path.
- [ ] **8.2** Remove or gate unused hybrid retrieval for platform `source_type` in hot path (keep functions for reports).
- [ ] **8.3** Add manual verification section to `docs/guides/sitewise-cockpit-verification.md` (latency smoke, three benchmark questions).

**Do not do until Phases 1–6 checkpoints pass.**

---

## Implementation order (recommended)

```text
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4
                              ↘
                               Phase 5 (can parallel after Phase 2)
                              ↘
                               Phase 6 → Phase 7 → Phase 8
```

**Smallest first win:** Phase 1 only (~1–2 sessions) — seed list instant.

**Biggest user-perceived win:** Phase 3 + Phase 4 — doctrine/seed Q&A feels like Hermes.

---

## Explicit non-goals (this plan)

- Replacing Supabase or auth stack
- Removing pgvector entirely (reports may still need it)
- Rewriting Create PMP workflow retrieval (separate follow-up)
- Co-locating VPS/Supabase to Sydney (ops task; do in parallel, not blocked on code)
- Frontend three-panel layout (separate plan)

---

## Risk register

| Risk | Mitigation |
| ---- | ---------- |
| Whole doc exceeds context window | Cap docs loaded (`whole_document_max_docs`); rank by FTS; truncate with explicit “partial doc” in answer |
| Grounding fails without chunk ids | Register passages with stable `chunk_id` = `document_id` or synthetic id per whole-doc row |
| Create PMP still uses chunk retriever | Leave workflow path on hybrid until workflow-specific Phase 9 (future) |
| Re-ingest deletes chunks other code expects | Phase 5 only after Phase 2 whole-doc reader uses `normalized_content` |

---

## Quick reference — files touched by phase

| Phase | Primary touch points |
| ----- | -------------------- |
| 1 | `chat/intent.py`, `chat/orchestrator.py`, `retrieval/inventory.py` |
| 2 | `retrieval/whole_document.py`, `retrieval/router.py`, `orchestrator.py` |
| 3 | `orchestrator.py`, `assistant/instructions.md` |
| 4 | `api/chat.py`, `chat/streaming.py`, `ChatPanel.tsx` |
| 5 | `ingest/pipeline.py`, `ingest/persist.py` |
| 6 | `retrieval/router.py`, `orchestrator.py` |
| 7 | `retrieval/whole_document.py`, projects API |
| 8 | `docs/architecture.md` |
