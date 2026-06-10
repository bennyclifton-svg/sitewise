# Clerk — implementation checklist

Work through this top to bottom. Check items off as you go (`[ ]` → `[x]`).

## Active frontend cockpit track

The Practice Intelligence integration now needs a visible cockpit front end, not only project-scoped chat. Track that work here:

- [ ] **Practice UI port pipeline (active):** [plans/2026-06-07-practice-ui-port-pipeline.md](plans/2026-06-07-practice-ui-port-pipeline.md)
- [ ] Cockpit Shell V2 plan: [plans/2026-06-07-cockpit-shell-v2-frontend-plan.md](plans/2026-06-07-cockpit-shell-v2-frontend-plan.md)
- [ ] Cockpit Shell V2 todolist: [cockpit-shell-v2-todolist.md](cockpit-shell-v2-todolist.md)

## How to approach the build

**Do not pick “backend first” or “frontend first” and finish one side completely.** Clerk is a full-stack product where the backend owns trust (retrieval, grounding, citations) and the frontend owns interaction (auth session, chat UI, streaming display). Build in **thin vertical slices** so you always have something runnable.

Recommended rhythm:

1. **Foundation** — accounts, env, both service scaffolds (can be done in parallel).
2. **Data + schema** — before any real AI; you need a place to store project documents, chunks, and chats.
3. **Auth end-to-end** — browser signs in, API verifies JWT; nothing else matters until this works.
4. **Chat shell with a stub** — prove streaming and persistence before wiring retrieval/LLM.
5. **Ingestion + retrieval** — class-aware indexing of the corpus in Supabase; hybrid search working in isolation.
6. **Real assistant** — PydanticAI agent under SiteWise doctrine; citations, grounding enforcement.
7. **Product polish** — citation UI, errors, empty states, deployment.
8. **Deliverable workflows** — repeatable skills (PMP, RFT, cost plan, programme) once Q&A is trustworthy.
9. **Tender evaluation** — multi-submission ingest, comparison, TRR-style outputs guided by doctrine + seed.

The architecture doc’s implementation sequence is baked into the phases below. Backend-heavy work comes first for **data and trust**; frontend comes alongside once auth and a stub chat endpoint exist.

---

## Client brief — what “done” means

Clerk helps a **project lead** work under [SiteWise doctrine](clerk-brief.md) — using real project evidence, reference seed knowledge, and repeatable PM workflows. Retrieval and chat are enablers; doctrine-governed judgement is the product.

### Layer 1 — Q&A (Phases 6–9)

A project lead must be able to:

- [ ] Ask questions in plain English about the curated corpus (contracts, claims, tenders, specifications, submissions, seed guides)
- [ ] Get a sourced answer that cites document, project, and page/section
- [ ] See citations distinguished by source type: **project evidence**, **doctrine** (`clerk-brief.md`), **reference** (`seed/`)
- [ ] Receive doctrine-governed responses — assumptions labelled (Fact / Assumption / Judgement / Recommendation per §evidence-discipline), escalation triggers surfaced
- [ ] Scope project-specific questions to one project folder (authority stack: active project evidence first)
- [ ] Trust the answer enough to base downstream decisions on it, or get a clear “insufficient evidence” response
- [ ] Use it from a browser, logged in with their work email
- [ ] See their own past conversations (threads + history)

### Layer 2 — Deliverable workflows (Phase 11, after Q&A is solid)

The user will ask Clerk to **produce** phase-gate deliverables, not only answer questions:

- [ ] Project management plan (PMP)
- [ ] Request for tender / request for proposal (RFT / RFP)
- [ ] Cost plan (elemental / HIA format where appropriate)
- [ ] Programme / master schedule outline

These are **repeatable skill-driven workflows** — structured processes informed by existing SiteWise skills, re-authored for Clerk. Each run must consult doctrine + relevant seed guides + active project evidence; outputs carry `seed_consulted` / evidence traceability where applicable.

### Layer 3 — Tender evaluation (Phase 12)

Procurement is the hardest corpus use case. The `data/` folders are **working examples of what good looks like** — especially packages with submissions **and** a tender recommendation report (TRR).

A project lead must be able to:

- [ ] Ingest tender submissions (often multi-file per bidder) alongside RFT, addenda, and evaluation criteria
- [ ] Query iteratively to compare submissions against criteria (price and non-price)
- [ ] Draft or refine a tender recommendation report grounded in retrieved submission evidence, RFT criteria, and exemplar TRRs in the corpus
- [ ] Stay within doctrine (§05-procurement) and seed (`procurement-quoting-guide.md`, `tender-evaluation` patterns)

**Validation corpus (in order):** `procurment-demo/` (pipeline smoke) → `procurement-blockb/` (structured TEP→EOI→RFT→submissions→evaluation→TRR) → `procurement-campy/` (largest; submissions + TRR at scale).

Non-goals (do not build): fetching documents from external APIs at runtime, multi-tenant, Next.js/SSR, direct OpenAI from the browser, geometric interpretation of CAD drawings.

---

## Local corpus (`data/`)

All source material lives on disk under `data/`. See [data/README.md](../data/README.md) for full detail.

The corpus serves three purposes:

1. **Project evidence** — real file sets from projects partway through or near completion (what good PM filing looks like).
2. **Reference seed** — archetype, role, and topic guides in `seed/`.
3. **Doctrine** — [clerk-brief.md](clerk-brief.md) (judgement layer; ingest separately from seed).

Procurement folders are intentionally rich — several include **tender submissions plus TRR** so Clerk can learn evaluation patterns from exemplars.


| Folder                | Role                                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `procurment-demo/`    | Smallest procurement set — **pipeline smoke test** (35 files)                                                             |
| `procurement-blockb/` | Block B procurement — TEP, EOI, RFT, addenda, **two submission sets**, evaluation, **TRR** — **primary tender validation corpus** (210 files; folder structure matches §05-procurement) |
| `procurement-campy/`  | Largest tender package — RFT, submissions, evaluation, recommendation; includes DWG (655 files)                           |
| `delivery-house/`     | Compact delivery — contracts, BASIX/CC, specs, cost schedules (28 files)                                                  |
| `delivery-petersham/` | Full D&C delivery — claims, variations, EOT, correspondence (405 files)                                                 |
| `consultants-campy/`  | Consultant procurement (empty — ready to populate)                                                                       |
| `seed/`               | Reference guides — `source_type: reference`                                                                               |
| `docs/clerk-brief.md` | SiteWise doctrine — `source_type: doctrine`                                                                               |


**Document classes** (ingestion must route by class, not just extension): contract, specification, report, correspondence, certificate, drawing (metadata + title block only), schedule, planning_instrument (reserved), reference, doctrine.

**Ingest priority:** PDF and Word for full text first; drawing register metadata (filename, title block, revision); Excel, MSG, DWG geometry, and images in later ingest waves.

---

## Phase 0 — Prerequisites

Get tooling, services, and the local corpus ready before writing app code.

- [x] Install Python 3.12+, uv, Node 20+, pnpm (see `README.md`)
- [x] Create a [Supabase](https://supabase.com) project named **Clerk** ([guide](guides/supabase-setup.md))
- [x] Collect Supabase URL, anon key, service role key, and **direct** `DATABASE_URL`
- [x] Create an [OpenAI API key](https://platform.openai.com/api-keys) (needed from Phase 6 onward)
- [x] Copy env templates:
  - [x] `backend/.env` from `backend/.env.example`
  - [x] `frontend/.env` from `frontend/.env.example`
- [x] Confirm all six corpus folders are present under `data/` (see table above)
- [x] Spot-check sample files open correctly (e.g. a PDF from `delivery-petersham/`, a guide from `seed/`)

**Done when:** Supabase project is healthy, env files are filled, and the `data/` corpus is in place.

---

## Phase 1 — Scaffold both services (parallel OK)

Backend and frontend scaffolds can be built at the same time. Neither depends on the other yet.

### Backend

- [x] `cd backend && uv sync`
- [x] Add dependencies per [backend-setup.md](guides/backend-setup.md) (`fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `alembic`, etc.)
- [x] Create `app/main.py` — FastAPI app with health check (`GET /health`)
- [x] Create `app/config.py` — pydantic-settings; fail fast on missing required vars
- [x] Configure editable package install in `pyproject.toml` (see backend setup guide)
- [x] Run: `uv run uvicorn app.main:app --reload` → `http://localhost:8000/health` returns OK

### Frontend

- [x] `cd frontend && pnpm create vite . --template react-ts` (per [frontend-setup.md](guides/frontend-setup.md))
- [x] Add `react-router-dom`, `@supabase/supabase-js`, Tailwind, shadcn/ui
- [x] Create `src/lib/env.ts` — validate `VITE_`* vars at boot
- [x] Create minimal routes: `/login`, `/` (placeholder), `/chat/:threadId` (placeholder)
- [x] Run: `pnpm dev` → app loads at `http://localhost:5173`

**Done when:** Both services start locally with no missing-config crashes.

---

## Phase 2 — Database schema (backend)

Schema before ingestion, retrieval, or chat persistence.

- [x] Init Alembic: `uv run alembic init alembic`
- [x] Wire `alembic/env.py` to `app.database.models` metadata and `settings.DATABASE_URL`
- [x] Define SQLAlchemy models for:
  - [x] `users`
  - [x] `source_documents` — project, phase, document type, filename, source path, normalized content
  - [x] `document_chunks` (embedding + `tsvector` columns)
  - [x] `chat_threads`
  - [x] `chat_messages`
  - [x] `message_citations`
- [x] Generate migration: `uv run alembic revision --autogenerate -m "initial schema"`
- [x] **Review migration** — manually add:
  - [x] `create extension if not exists vector`
  - [x] HNSW index on embeddings
  - [x] GIN index on `search_vector`
  - [x] RLS policies (users see only their own chats)
- [x] Apply: `uv run alembic upgrade head`

**Done when:** Tables exist in Supabase; `pgvector` extension is enabled.

---

## Phase 3 — Auth end-to-end

Users must sign in before any chat or retrieval logic runs.

### Frontend

- [x] `src/lib/supabase.ts` — browser Supabase client
- [x] Login page — email sign-in / sign-up (Supabase Auth, email only)
- [x] Auth guard — redirect unauthenticated users to `/login`
- [x] Session helper — `getAccessToken()` for API calls

### Backend

- [x] `app/auth/dependencies.py` — verify `Authorization: Bearer <token>` via Supabase Auth
- [x] `get_current_user` dependency on all protected routes
- [x] `app/database/supabase.py` — user-scoped and service-role clients
- [x] `POST /auth/me` or similar — returns current user profile (smoke test)

**Done when:** You can sign in in the browser, call a protected backend route with the token, and get `401` without it.

---

## Phase 4 — API client + chat persistence shell

Wire frontend ↔ backend before streaming or LLM work.

### Shared API layer (frontend)

- [x] `src/lib/http.ts` — `fetch` wrapper, timeouts, typed `ApiError` (incl. network vs HTTP)
- [x] `src/lib/api.ts` — injects Supabase bearer token automatically
- [x] CORS: `ALLOWED_ORIGINS` includes `http://localhost:5173`

### Chat CRUD (backend, no LLM yet)

- [x] `app/database/chats.py` — create/list/load threads and messages
- [x] `GET /chat/threads` — list current user’s threads
- [x] `POST /chat/threads` — create thread
- [x] `GET /chat/threads/{id}/messages` — load message history
- [x] Enforce ownership — `403` if thread belongs to another user

### Chat CRUD (frontend)

- [x] Thread list page — show past conversations
- [x] New chat button — creates thread, navigates to `/chat/:id`
- [x] Load initial messages when opening a thread

**Done when:** Signed-in user can create a thread, leave, come back, and see it in the list (empty messages OK).

---

## Phase 5 — Streaming chat shell (stub assistant)

Prove the streaming contract before real retrieval.

### Backend

- [x] `POST /chat/stream` — accepts AI SDK message format + `threadId`
- [x] `app/chat/streaming.py` — emits AI SDK-compatible stream events
- [x] Stub response — fixed text + fake citation metadata
- [x] Persist user + assistant messages after stream completes
- [x] `structlog` logging on auth, stream start/end, errors

### Frontend

- [x] Add Vercel AI SDK UI packages
- [x] `src/components/chat/`* — message list, input, streaming status
- [x] `useChat` pointed at `POST /chat/stream` with bearer token
- [x] Basic error display (401, network, 500)

**Done when:** User sends a message, sees streamed stub reply, refreshes page, and history reloads.

---

## Phase 6 — Ingestion pipeline

Turn the local `data/` corpus into searchable chunks **and** a document register in Supabase. See [plans/2026-06-07-phase-6-ingestion.md](plans/2026-06-07-phase-6-ingestion.md).

### Schema

- [x] Migration: unique `(document_id, chunk_index)` for idempotent chunk upserts
- [x] Migration: `document_class`, `ingest_mode`, `document_metadata` (JSONB), `content_hash` on `source_documents`
- [x] Three `source_type` values: `project_evidence`, `reference`, `doctrine`

### Pipeline (`backend/ingest/`)

- [x] **Discover** — walk corpus; manifest (path, project, folder, filename, extension, size)
- [x] **Classify** — `document_class` from extension + path + filename (contract, spec, drawing, tender_submission, trr, …)
- [x] **Router** — class-specific extractors and chunkers (not one-size-fits-all)
- [x] **Extract** — PDF/Word/Markdown full text; drawing PDF/DWG **register metadata** (number, title, rev, discipline — no geometry)
- [x] Upsert `source_documents` with project, phase, `document_class`, `document_metadata`, `relative_path`
- [x] **Chunk** — stable chunk IDs; class-aware strategies (prose, specification trade-section, contract clause, register-only for drawings)
- [x] Generate embeddings (OpenAI `text-embedding-3-small`)
- [x] Upsert `document_chunks` (embedding + auto-generated `tsvector`)
- [x] Idempotent re-run — safe to re-ingest without duplicates
- [x] Unit tests for classify, chunkers, filename/drawing parsers (no network)

### Ingest order

- [x] `procurment-demo/` — smoke test (~30 ingestible PDF/DOCX)
- [x] `docs/clerk-brief.md` — doctrine (`source_type: doctrine`)
- [x] `seed/` — reference guides
- [x] `delivery-house/` — compact delivery evidence
- [x] `procurement-blockb/` — **tender vertical slice** (TEP → submissions → evaluation → TRR); tag `procurement_stage` in metadata from folder (`03 RFT`, `05 SUBMISSION 01`, `08 TRR`, etc.)
- [ ] Stretch: `delivery-petersham/`, `procurement-campy/` (scale + DWG register)

**Done when:** `procurment-demo/`, `delivery-house/`, `procurement-blockb/`, `seed/`, and `clerk-brief.md` are in Supabase with sane row counts; blockb TRR and submission folders are retrievable by project + procurement stage.

---

## Phase 7 — Hybrid retrieval

Retrieval must work in tests before the LLM depends on it.

- [x] `app/retrieval/queries.py` — pgvector semantic search + Postgres full-text search
- [x] `app/retrieval/fusion.py` — Reciprocal Rank Fusion in Python
- [x] `app/retrieval/retriever.py` — query → ranked `SourcePassage` list
- [x] Optional filters — by project (`delivery-petersham`), phase, or `source_type`
- [x] Neighbouring-chunk fetch for grounding context
- [x] Unit tests with mocked DB or integration tests behind `@pytest.mark.integration`

**Done when:** Test queries return relevant chunks, e.g.:

- “What progress claims exist for Petersham?” (after Petersham ingest)
- “What are the Block B tender evaluation criteria?” (`procurement-blockb/06 EVALUATION`)
- “Summarise Tenderer 01’s price qualifications in Block B” (submission folder scoped)
- “What does the Block B TRR recommend and why?” (`08 TRR` vs submissions)
- “What does the seed guide say about defects during DLP?”
- “What does doctrine say about certifying progress without inspection?” (`clerk-brief` §07)

---

## Phase 8 — PydanticAI assistant + grounding

Replace the stub with a real, typed, cited assistant.

- [x] `app/assistant/deps.py` — `DocumentAgentDeps` (user, thread, retriever, validator)
- [x] `app/assistant/outputs.py` — `GroundedAnswer`, `Citation`, `SourcePassage`
- [x] `app/assistant/instructions.md` — product contract (distilled from [clerk-brief.md](clerk-brief.md)):
  - [x] Authority stack: project evidence → doctrine → seed → LLM last
  - [x] Answer from retrieved passages; cite every factual claim
  - [x] Distinguish `project_evidence`, `doctrine`, and `reference` in answers and citations
  - [x] Label Fact / Assumption / Judgement / Recommendation (§evidence-discipline)
  - [x] Surface escalation triggers; do not smooth them over
  - [x] Say clearly when the corpus does not contain enough evidence
  - [x] Do not present assumptions as project fact
  - [x] Detect deliverable/workflow intent (“write me an RFT”) — defer to Phase 11 skills or explain capability gap
- [x] `app/assistant/agent.py` — PydanticAI agent with bounded tools (`search_documents`, `read_chunk`, `read_surrounding_chunks`)
- [x] `app/chat/orchestrator.py` — one turn: retrieve → agent → validate → stream → persist
- [x] `app/grounding/validator.py` — every citation maps to a retrieved passage
- [x] Unit tests: citation extraction, grounding enforcement, “insufficient evidence” path

**Done when:** Real questions return grounded answers with valid citations, or a clear “not enough evidence” response.

---

## Phase 9 — Citation UI + product polish

Satisfy the “trust the answer” requirement in the UI.

- [x] Citation chips/links on assistant messages
- [x] Source passage panel — project, document name, phase, page/section, excerpt
- [x] Visual distinction between project evidence, doctrine, and seed reference citations
- [x] Empty states — no threads, no corpus match, first-time user
- [x] Friendly error states — 401 (re-login), 403, retrieval failure, grounding failure
- [x] Thread title auto-generation or editable title
- [x] Loading / streaming indicators

**Done when:** A user can read an answer, click a citation, and verify the excerpt against the source document without leaving the app.

---

## Phase 10 — Deploy + harden

- [ ] Railway: backend service (Uvicorn)
- [ ] Railway: frontend service (Vite static build)
- [ ] Production env vars on both services
- [ ] Supabase: re-enable email confirmation if disabled for dev
- [ ] Re-run ingestion against production Supabase (or sync strategy documented)
- [ ] Smoke test production auth + chat + citation flow
- [ ] `pnpm tsc --noEmit` and `pnpm lint` clean
- [ ] `pytest -m "not integration"` green; integration tests documented

**Done when:** Users can use Clerk in production with **Layer 1** of the client brief (Q&A under doctrine).

---

## Phase 11 — Deliverable workflows (skills)

**Prerequisite:** Phases 6–9 solid — grounded Q&A on `procurement-blockb/` and `delivery-house/` before generating deliverables.

Repeatable PM processes, informed by existing SiteWise skills (rewrite/port for Clerk as needed):

- [ ] `backend/app/workflows/` — workflow runner: load skill spec → gather context (retrieval + doctrine + seed) → structured output schema → stream/persist
- [ ] Skill registry — PMP, RFT/RFP, cost plan, programme (minimum set)
- [ ] §seed-consultation gate — require archetype / user_role / state (project context) before phase-gate deliverables; stop and ask if missing
- [ ] Output templates match doctrine deliverables (§00–§09 folder-aligned lists)
- [ ] Each workflow output: evidence traceability, `seed_consulted` metadata, Assumption labelling
- [ ] Chat entry: user says “draft an RFT for …” → workflow invoked with thread context + project scope
- [ ] Unit tests: workflow schemas, gate behaviour, insufficient-evidence path

**Done when:** User can run at least one workflow end-to-end (e.g. procurement strategy note or RFT outline) on `procurement-blockb/` context with doctrine + seed citations.

See [plans/2026-06-07-workflows-and-tender.md](plans/2026-06-07-workflows-and-tender.md).

---

## Phase 12 — Tender evaluation vertical slice

**Prerequisite:** `procurement-blockb/` fully ingested; Phase 11 procurement skills or Phase 8 agent handles multi-step tender tasks.

- [ ] Ingest metadata links submissions to tenderer ID and procurement stage (`05 SUBMISSION 01`, `07 SUBMISSION 02`, …)
- [ ] Retrieval filters: by `procurement_stage`, tenderer, document_class (`tender_submission`, `evaluation`, `trr`)
- [ ] Tender comparison workflow skill — criteria matrix, price/non-price separation (doctrine §05)
- [ ] TRR draft workflow — structure from exemplar `08 TRR` in blockb + campy; grounded in submission retrieval
- [ ] Iterative chat: user refines evaluation across many turns without losing tenderer scope
- [ ] Evaluation tests against known blockb TRR conclusions (integration / golden queries)

**Done when:** User can ask “Compare the Block B submissions against the evaluation criteria and draft a recommendation summary” and receive a grounded, doctrine-compliant response citing submissions + TRR exemplar + seed; or insufficient evidence where corpus gaps exist.

**Scale path:** blockb (validate) → `procurement-industrial-new/` (small) → `procurement-campy/` (655 files, DWG register).

---

## Quick reference — what to build when


| Order | Focus                                   | Why                                            |
| ----- | --------------------------------------- | ---------------------------------------------- |
| 0     | Tools + Supabase + local `data/` corpus | Nothing runs without infra or source documents |
| 1     | Backend + frontend scaffolds            | Parallel; establishes conventions              |
| 2     | Schema + migrations                     | Corpus and chats need a home                   |
| 3     | Auth                                    | Security boundary for everything else          |
| 4     | API client + thread CRUD                | Persistence before intelligence                |
| 5     | Stub streaming chat                     | Proves the hardest UX path early               |
| 6     | Class-aware ingestion + register        | Corpus + document repository for transmittals  |
| 7     | Retrieval                               | Testable without LLM cost                      |
| 8     | PydanticAI + doctrine grounding         | The trust layer                                |
| 9     | Citation UI                             | Client brief “trust” requirement               |
| 10    | Deploy                                  | Ship Layer 1 Q&A                               |
| 11    | Deliverable workflows (skills)          | PMP, RFT, cost plan, programme                 |
| 12    | Tender evaluation                       | Submissions + TRR; blockb → campy              |


---

## Notes

- **Backend-first for data and trust; frontend alongside from Phase 3.** After auth, alternate backend capability with frontend wiring so you always have a demoable slice.
- **The corpus on disk is the source of truth.** Ingestion reads from `data/` only — no runtime fetching from external document APIs.
- **Do not call OpenAI from the browser.** All LLM and embedding calls stay in FastAPI.
- **Migrations use the direct Supabase DB URL**, not the pooler.
- Corpus layout and conventions: [data/README.md](../data/README.md).
- SiteWise doctrine (judgement layer): [clerk-brief.md](clerk-brief.md).
- Ingestion plan: [plans/2026-06-07-phase-6-ingestion.md](plans/2026-06-07-phase-6-ingestion.md).
- Workflows + tender plan: [plans/2026-06-07-workflows-and-tender.md](plans/2026-06-07-workflows-and-tender.md).
- Architecture and stack details: [architecture.md](architecture.md).
