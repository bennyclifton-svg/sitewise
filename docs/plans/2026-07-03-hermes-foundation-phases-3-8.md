# Hermes Foundation (Phases 3–8) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan phase-by-phase, task-by-task. Commit after every task. This is the continuation of [2026-07-02-hermes-foundation-phases-0-2.md](./2026-07-02-hermes-foundation-phases-0-2.md); do not start Phase 3 until Phases 0–2 have landed and their gates pass.

**Goal:** Turn the MCP tool bridge (Phase 2) into a working agent-first product — Hermes reasons behind Clerk's chat, drives the flagship tender-comparison workflow end-to-end, users edit agent artefacts and files in-app, subscribe via Stripe, and the whole thing ships to the `sitewise.au` VPS with the legacy cockpit retired.

**Execution shards:** This file remains the canonical overview. Execute from the
phase-specific shards under
[`docs/plans/hermes-foundation/`](./hermes-foundation/00-index.md), starting with
the Phase 2 gate before any Phase 3 implementation.

**Architecture:** Clerk's FastAPI stays the system of record. A new `backend/agent/` module invokes headless Hermes (`hermes -z` / `hermes chat -q`, proven in Phase 0) per chat turn, feeds it the MCP server URL + a per-turn token (Phase 2), and relays Hermes output as **Vercel-AI-SDK-compatible SSE** so Clerk's existing React chat keeps working. The frontend is *extended*, not replaced. Billing swaps Polar→Stripe behind the existing entitlement seam. Deploy is Dokploy compose, with Hermes + a workspace volume added to the backend image.

**Tech Stack:** Python 3.12, FastAPI, async SQLAlchemy 2, Alembic, `fastmcp`, Hermes CLI v0.17.0 (headless), `stripe` Python SDK, pytest. Frontend: React 19, Vite 8, Tailwind 4, radix-ui/shadcn, TanStack Query, react-router 7, **Vercel AI SDK (`@ai-sdk/react` + `ai`)**, vitest. Deploy: Docker + Dokploy, nginx, Supabase (external).

---

## READ FIRST — corrections to the design doc's assumptions

The design doc ([2026-07-02-agent-first-dashboard-design.md](./2026-07-02-agent-first-dashboard-design.md)) was written before the codebase was audited. Three of its assumptions are wrong or imprecise; this plan supersedes them:

1. **Frontend state is NOT Zustand.** Clerk's chat is built on the **Vercel AI SDK** (`@ai-sdk/react`'s `useChat` + `DefaultChatTransport`), see [frontend/src/components/chat/ChatPanel.tsx](../../frontend/src/components/chat/ChatPanel.tsx). It already does token streaming, a status line (`data-clerk-status` → [StreamingIndicator.tsx](../../frontend/src/components/chat/StreamingIndicator.tsx)), citation/source panels, and error banners. **Consequence:** Phase 4 is much smaller than "transplant Omnigent's Zustand chat." We keep the AI-SDK chat and *add* tool-call chips, a session list, a stop button, and artefact cards. Do not vendor Omnigent's store. Use Omnigent only as a *visual* reference.

2. **Storage is Supabase Storage (object buckets), NOT the VPS filesystem.** See [app/storage/project_files.py](../../backend/app/storage/project_files.py) and the `workspace_files` table ([app/database/workspace_file.py](../../backend/app/database/workspace_file.py)) which maps `workspace_path` → `storage_bucket`/`storage_key`. **Consequence:** Hermes cannot be pointed at a project `cwd` full of the user's PDFs — they live in Supabase. Phase 6 Task 0 resolves this explicitly (recommended: Hermes reaches documents through **MCP tools**, and its filesystem `cwd` is a per-turn scratch/artefact dir on a VPS volume, not the document store).

3. **The SSE contract is fixed by the frontend.** `useChat` consumes a specific event vocabulary (`start`, `text-start`, `text-delta`, `text-end`, `data-clerk-status`, `source-document`, `finish`, `[DONE]`) — see [app/chat/streaming.py](../../backend/app/chat/streaming.py). **Consequence:** Phase 3's Hermes relay MUST emit these same events, so Phase 4's frontend changes stay additive. This is the single most important integration constraint in the plan.

Also noted from the audit (act on where flagged):
- The backend Dockerfile **already** installs `openjdk-17-jre-headless` + `libreoffice` ([deploy/docker/backend.Dockerfile:25](../../deploy/docker/backend.Dockerfile#L25)) — Phase 1 Task 9's JVM concern is already satisfied; Phase 8 only needs to add Hermes.
- The Dokploy compose ([deploy/dokploy.compose.yml](../../deploy/dokploy.compose.yml)) runs `sitewise-api` + `sitewise-web` only — **there is no tender worker service**. Phase 5 must ensure the TCM worker actually runs (in-process task or a compose service), or the flagship pipeline never progresses past `pending`.
- The billing gate seam is `require_active_entitlement(session, user)` ([app/billing/entitlements.py:65](../../backend/app/billing/entitlements.py#L65)), already applied at chat endpoints. Phase 7 swaps the implementation behind it; it does not invent a new seam.

**Cross-cutting rules (every phase):** DRY (tools/relays delegate to existing services), YAGNI (only what a gate needs), TDD on security/contract seams, a commit per task with the trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Backend commands run from `backend/` via `uv run …`; Hermes/ODL-in-Docker validate on Linux/WSL2. Keep the legacy cockpit behind routes until Phase 8's gate passes (R3 safety valve).

---

# Phase 3 — `backend/agent/` Hermes runtime + SSE + sessions

**Resume context:** Phase 2 delivered an MCP server at `/mcp`, HMAC turn tokens (`app/mcp_bridge/tokens.py`), and tool-layer authz. Phase 0 proved `hermes -z '<prompt>'` runs headless (final-only) and `hermes chat -q` line-streams. This phase makes a real chat turn go: user message → Hermes (with MCP tools + turn token) → streamed answer in the existing chat UI.

**Objective / gate:** A streamed Hermes turn works end-to-end through `POST /chat/stream` (or a sibling endpoint), emitting Vercel-AI-SDK SSE events, persisted as chat messages in Postgres, with bounded concurrency and a working cancel. Existing `ChatPanel` renders it with **zero frontend changes**.

**Key design decisions to make in Task 0 (record answers in a short `docs/plans/omnigent/phase3-notes.md`):**
- **Invocation mode:** per-turn `hermes chat -q --source tool` (line-streamed) vs `hermes -z` (final-only). Recommended: `hermes chat -q` for streaming; fall back to `-z` + synthetic word-streaming (like [streaming.py:64](../../backend/app/chat/streaming.py#L64) already does for the stub) if chrome-stripping proves fragile. Phase 0 notes flagged Rich box chrome on the streamed path — decide whether to strip it or use `hermes serve`/`acp`.
- **Session mapping:** reuse the existing `chat_threads`/`chat_messages` tables (see [app/database/chat_thread.py](../../backend/app/database/chat_thread.py), [app/api/chat.py](../../backend/app/api/chat.py)). Add a nullable `hermes_session_id` column to `chat_threads` so multi-turn `--resume` works. Do NOT invent a parallel session store.
- **Where it plugs in:** add agent turns as a new branch/endpoint alongside the existing grounded-RAG `run_chat_turn`, not by ripping it out (that's Phase 8's cutover). Feature-flag with a setting `agent_runtime_enabled`.

### Task 3.0: Design spike + config
- **Files:** Create `docs/plans/omnigent/phase3-notes.md`; modify `backend/app/config.py`.
- Add settings (follow the existing `Settings` field style, all with safe defaults): `agent_runtime_enabled: bool = False`, `hermes_binary_path: str = "hermes"`, `hermes_invocation_mode: str = "chat_stream"` (`chat_stream`|`oneshot`), `agent_platform_api_key: str | None = None`, `agent_mcp_url: str = "http://127.0.0.1:8000/mcp"`, `agent_max_concurrent_turns: int = 4`, `agent_turn_timeout_seconds: int = 180`, `agent_turn_token_secret` (already added in Phase 2 — reuse).
- Record in notes: chosen invocation command line, how chrome is stripped (if any), and how the MCP turn token is injected (Phase 0 found env interpolation is process-wide → inject via the spawned process's env, one token per turn).
- **Commit:** `feat(agent): phase 3 config + design notes`.

### Task 3.1: Hermes process wrapper (TDD)
- **Files:** Create `backend/app/agent/__init__.py`, `backend/app/agent/hermes_process.py`; Test `backend/tests/agent/test_hermes_process.py`.
- **Behaviour:** `async def stream_hermes_turn(*, prompt: str, mcp_url: str, turn_token: str, cwd: str, spawn=<injectable>) -> AsyncIterator[str]` — builds the argv from settings, injects the platform API key + MCP token into the child env, spawns via `asyncio.create_subprocess_exec`, and yields cleaned text chunks as they arrive. **Inject the spawner** so tests never launch real Hermes.
- **Tests (mock spawn with a fake process that yields scripted stdout lines):** (a) yields text chunks in order; (b) child env contains the API key and the `Authorization: Bearer <token>` value but NOT in argv (secret hygiene); (c) Rich-chrome/ANSI lines are stripped; (d) non-zero exit raises `HermesTurnError` with stderr tail; (e) a turn exceeding `agent_turn_timeout_seconds` is killed and raises `HermesTurnTimeout`.
- Red → green → **commit** `feat(agent): headless hermes process wrapper`.

### Task 3.2: SSE relay in the frontend's event vocabulary (TDD)
- **Files:** Create `backend/app/agent/sse_relay.py`; Test `backend/tests/agent/test_sse_relay.py`.
- **Behaviour:** `async def relay_agent_turn(chunks: AsyncIterator[str], *, status: AsyncIterator[str] | None = None) -> AsyncIterator[str]` producing the exact Vercel-AI-SDK events from [streaming.py](../../backend/app/chat/streaming.py): `start`→`text-start`→`text-delta`*→`text-end`→`finish`→`[DONE]`. **Reuse `app/chat/streaming.py`'s `_sse` helper and `clerk_status_event`** — do not re-implement the framing (DRY). Add a `data-clerk-status` event for tool-call chips (Phase 4 renders them): shape `{"type":"data-clerk-status","data":{"message": "...", "kind":"tool", "tool":"start_tender_comparison", "state":"running|done"}}`.
- **Tests:** (a) a 3-chunk stream yields well-formed ordered SSE ending in `[DONE]`; (b) tool-status items interleave as `data-clerk-status` events; (c) an error mid-stream emits the `error` event then `[DONE]` (matches `stream_error`).
- Red → green → **commit** `feat(agent): SSE relay in AI-SDK event vocabulary`.

### Task 3.3: Concurrency + cancellation guard (TDD)
- **Files:** Create `backend/app/agent/concurrency.py`; Test `backend/tests/agent/test_concurrency.py`.
- **Behaviour:** a process-wide `asyncio.Semaphore(settings.agent_max_concurrent_turns)` plus a per-turn `asyncio.Task` registry keyed by `(thread_id)` so a `POST /chat/{thread}/cancel` can cancel an in-flight turn (and later, its spawned pipeline jobs). No unbounded fan-out (adopted doctrine).
- **Tests:** (a) the N+1th concurrent turn waits, not errors; (b) cancel() actually cancels the registered task and releases the semaphore; (c) a finished turn deregisters.
- Red → green → **commit** `feat(agent): bounded turn concurrency + cancellation`.

### Task 3.4: Agent chat endpoint + thread column (migration)
- **Files:** Create Alembic migration for `chat_threads.hermes_session_id String(128) nullable`; modify `backend/app/database/chat_thread.py`; add endpoint in `backend/app/api/chat.py` (new `POST /chat/agent/stream` guarded by `settings.agent_runtime_enabled`) and `POST /chat/agent/{thread_id}/cancel`; Test `backend/tests/agent/test_agent_endpoint.py`.
- **Reuse:** `require_thread_owner`, `require_project_owner`, `require_active_entitlement`, `ensure_user_exists` (all already in `app/api/chat.py`); the turn-token minting from Phase 2 (`app/mcp_bridge/tokens.py`); message persistence via `app/database/chats.py`'s `create_message`.
- **Flow:** authenticate → mint a turn token bound to (user, project) → resolve the project workspace cwd (Phase 6 provides the real dir; until then use a temp dir) → `relay_agent_turn(stream_hermes_turn(...))` inside a `StreamingResponse(media_type="text/event-stream", headers={... "x-vercel-ai-ui-message-stream":"v1"})` (copy headers from the existing `post_chat_stream`) → persist user + assistant messages after the stream closes.
- **Tests (mock `stream_hermes_turn`):** (a) unauthenticated → 401; (b) non-owner thread → 403; (c) no entitlement → 402; (d) happy path streams AI-SDK events and persists two messages; (e) cancel endpoint stops the turn.
- Run migration (`uv run alembic upgrade head`), full suite, ruff. **Commit** `feat(agent): streaming agent chat endpoint + hermes_session_id`.

### Task 3.5: Manual E2E on Linux/WSL2 (gate)
- Configure a real platform API key in a scratch `.env`, set `agent_runtime_enabled=true`, run the backend, point the existing `ChatPanel` at `/chat/agent/stream` (temporary env toggle), and confirm a real Hermes turn streams into the UI and can call an MCP tool (e.g. "list my tender comparisons"). Record in `phase3-notes.md`. **Gate:** streamed Hermes turn renders in the unchanged chat UI + one successful MCP tool call.
- **Commit** notes: `docs(agent): phase 3 E2E gate passed`.

**Phase 3 risks:** chrome-stripping fragility (fallback: `-z` + synthetic streaming); MCP token injection racing across concurrent turns (each turn spawns its own process with its own env — verify isolation, Phase 0 flagged process-wide env interpolation).

---

# Phase 4 — Chat UI: tool chips, sessions, stop, artefact cards

**Resume context:** Phase 3 emits AI-SDK SSE incl. `data-clerk-status` tool events and exposes `/chat/agent/stream` + cancel. The existing `ChatPanel` already renders text, status, citations, errors. This phase reaches Omnigent-grade polish by *extending* it. **Frontend TDD = vitest render tests** (`frontend` has no test runner yet — Task 4.0 adds vitest).

**Objective / gate:** Manual UX checklist passes: token streaming (already), collapsible tool-call chips with live state, per-project session list (resume/rename/delete), a working Stop button, artefact cards linking to panels, readable error states.

### Task 4.0: Add vitest + testing-library
- **Files:** modify `frontend/package.json` (devDeps `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`), add `frontend/vitest.config.ts`, `frontend/src/test/setup.ts`, add `"test": "vitest run"` script.
- Write one trivial passing render test to prove the harness. **Commit** `test(web): add vitest + testing-library`.

### Task 4.1: Tool-call chips (TDD)
- **Files:** Create `frontend/src/components/chat/ToolCallChip.tsx` + test; modify `ChatPanel.tsx`'s `onData` handler to collect `data-clerk-status` events of `kind:"tool"` into per-message chip state.
- **Behaviour:** each tool event renders a collapsible chip ("Running comparison pipeline… 3/5", "Reading Kaposi.pdf ✓") with running/done/error states; multiple chips stack; clicking expands detail. Use lucide icons + shadcn styling already in the repo.
- **Tests:** render with a running tool event → shows spinner + label; with a done event → shows check; error event → error style.
- Red → green → **commit** `feat(web): tool-call chips in chat`.

### Task 4.2: Stop button (TDD)
- **Files:** modify `ChatPanel.tsx`; add a `stop()` call wired to `useChat`'s `stop` AND a `POST /chat/agent/{threadId}/cancel` (so the backend kills Hermes + jobs, not just the browser stream). Test the button appears only while `isBusy` and calls both.
- Red → green → **commit** `feat(web): working stop button (cancels backend turn)`.

### Task 4.3: Session list panel (TDD)
- **Files:** Create `frontend/src/components/chat/SessionList.tsx` + test; reuse existing thread APIs (`GET/POST/PATCH /chat/threads`, already in [app/api/chat.py](../../backend/app/api/chat.py); frontend calls likely in `lib/api.ts`). Add delete: a `DELETE /chat/threads/{id}` endpoint if missing (check first; add with owner check + cascade if absent) and its frontend call.
- **Behaviour:** per-project thread list, click to resume (`/chat/:threadId` route exists), inline rename (PATCH), delete with confirm. TanStack Query for cache/invalidation (already the app's data layer).
- Red → green → **commit** `feat(web): per-project chat session list`.

### Task 4.4: Artefact cards (TDD)
- **Files:** Create `frontend/src/components/chat/ArtefactCard.tsx` + test; extend `onData` to handle an artefact event (`{"type":"data-clerk-status","data":{"kind":"artefact","artefactId":...,"workflowType":"tender_comparison","title":...}}` emitted by Phase 5).
- **Behaviour:** renders a rich card in-chat linking to the relevant dashboard panel/route (e.g. tender comparison route). Test: artefact event → card with title + working link.
- Red → green → **commit** `feat(web): in-chat artefact cards`.

### Task 4.5: Manual UX checklist (gate)
- Create `docs/plans/omnigent/phase4-ux-checklist.md` and walk it: streaming smoothness, chip states, stop actually stops, resume/rename/delete, artefact card navigation, error copy for rate-limit/tool-failure/partial-pipeline. **Gate:** all boxes ticked. **Commit** the checklist.

**Phase 4 risks:** AI-SDK `useChat` message-shape assumptions when mixing tool chips with text parts — keep chips in separate component state keyed by message id (as `ChatPanel` already does for status), don't fake them as message parts.

---

# Phase 5 — Flagship end-to-end: NL trigger → TCM → panel + artefact

**Resume context:** Phase 2 built `start_tender_comparison` (composing existing tender services) + comparison read tools; Phase 3/4 give a streaming agent chat with tool chips + artefact cards. Phase 1 landed the ODL Stage-0.5 pipeline (`ingest → classify → extract → embed → map → …`). This phase makes the whole flagship demo real and fast.

**Objective / gate:** In chat, "compare the 3 selected structural tenders" → Hermes calls `start_tender_comparison` → the TCM worker runs the pipeline → results populate the tender comparison panel AND a report artefact appears as an in-chat card — within the speed gate (simple 3-tender package cold 60–90 s), proven by a scripted acceptance run.

### Task 5.0: Ensure the worker runs (blocker)
- **Investigate:** the TCM pipeline is a poll-loop worker (`backend/tender/worker.py`) but the compose has no worker service. Determine how jobs currently drain in dev/prod. **Decide + implement:** either (a) a background asyncio task started in FastAPI lifespan (`app/main.py`) that runs `worker.run_once` in a loop when `settings.tender_worker_inproc_enabled`, or (b) a separate `sitewise-worker` compose service (Phase 8 wires it). Recommended for MVP: in-process task behind a flag, so one container runs both. Add a test that the lifespan starts/stops the worker loop.
- **Commit** `feat(tender): in-process worker loop behind a flag`.

### Task 5.1: `list_selected_documents` + selection model (TDD)
- The flagship phrase implies the user has *selected* documents. Confirm whether a selection concept exists (grep tender/frontend for "select"); if not, the simplest MVP is: the tool takes explicit `workspace_paths` (Phase 2's `start_tender_comparison` already does). Add `list_selected_documents(project_id)` returning candidate tender PDFs from `workspace_files` so Hermes can reason about which to compare. TDD with a stub session. **Commit** `feat(mcp): list_selected_documents tool`.

### Task 5.2: `get_comparison_status` / `get_comparison_result` polish (TDD)
- Ensure the read tools surface per-stage progress (for tool chips) and a final structured result (for the artefact). Delegate to `tender/services/matrix.py`/`report.py`/`qa.py`. TDD each. **Commit** `feat(mcp): comparison status + result tools for agent`.

### Task 5.3: Persist the report as a `draft_artifact` (TDD)
- On comparison completion, write a `draft_artifacts` row (`workflow_type="tender_comparison"`, `content_markdown` = the report, `provenance_metadata` = model/timings/comparison_id) — the table already exists ([app/database/draft_artifact.py](../../backend/app/database/draft_artifact.py)). Emit the artefact SSE event (Phase 4 renders the card). TDD the persistence + event. **Commit** `feat(tender): comparison report persisted as editable artefact`.

### Task 5.4: Timing ledger + speed gate (TDD, adopted doctrine)
- Confirm/extend the timing ledger (design doc §Timing ledger; local-repo doctrine) records per-stage duration/LLM-calls/tokens/cache for a comparison run. Add a **CI-marked speed test** (`@pytest.mark.tender_eval`) that runs the simple 3-tender fixture package (Enmore/Kaposi/NexusBuilt from Phase 1) cold and asserts total < 90 s, printing the per-stage table. This is the doctrine gate. **Commit** `test(tender): flagship speed gate (simple package < 90s cold)`.

### Task 5.5: Scripted acceptance run (gate)
- Create `docs/plans/omnigent/phase5-acceptance.md`: a scripted manual run of the full flagship flow on Linux/WSL2 with real Hermes + real ODL, recording the timing table and screenshots of chip progress + the artefact card + the populated comparison panel. **Gate:** flow completes, artefact appears, speed gate green. **Commit** the acceptance record.

**Phase 5 risks (highest in the plan):** TCM speed (design R4/doctrine) — if the cold run blows 90 s, profile with the ledger and apply batching/caching rules before widening scope; do NOT rewrite passing per-stage handlers. Worker-not-running is the silent killer — Task 5.0 is a hard prerequisite.

---

# Phase 6 — Workspaces, document repository panel, artefact editing

**Resume context:** Files live in **Supabase Storage** (not filesystem). `workspace_files` + `draft_artifacts` tables exist. Frontend already has `DocumentRepositoryPanel.tsx`, `WorkspaceExplorer.tsx`, `WorkspaceFilePanel.tsx`, `DraftReviewPanel.tsx`. This phase makes the repo real (browse/upload/download, sources read-only, artefacts editable) with the agent sharing the same tree safely.

**Objective / gate:** Users browse/upload/download project files and edit agent artefacts in-app; sources (PDFs) are view/annotate-only; the agent reads/writes the same workspace through traversal-safe scoped paths. Gate: traversal tests pass; an artefact edit round-trips (agent writes → user edits → persists → agent sees the edit).

### Task 6.0: Resolve the filesystem/object-store tension (design decision, record it)
- **Files:** `docs/plans/omnigent/phase6-storage-decision.md`.
- **Recommended resolution:** Hermes never gets raw filesystem access to the document store. Documents are reached via **MCP tools** (`get_document`, `search_documents`, `list_selected_documents`). Hermes' filesystem `cwd` is a **per-project scratch/artefact directory** on a VPS volume (`AGENT_WORKSPACE_ROOT/{project_id}/`), materialized/synced on demand, holding only agent working files + generated artefacts — never the canonical source PDFs. Artefacts persist to `draft_artifacts` (DB) as the source of truth; the scratch dir is disposable. Record the decision + the exact path scheme.
- **Commit** `docs(agent): resolve workspace storage model`.

### Task 6.1: Traversal-safe workspace path helper (TDD — security seam)
- **Files:** Create `backend/app/agent/workspace_paths.py`; Test `backend/tests/agent/test_workspace_paths.py`.
- **Behaviour:** `resolve_workspace_path(project_id, rel_path) -> Path` that joins under `settings.agent_workspace_root/{project_id}` and **rejects traversal** (`..`, absolute paths, symlink escape) — raise `WorkspacePathError`. Mirror the safety of `app/storage/keys.py`'s sanitization but for filesystem paths.
- **Tests:** (a) normal rel path resolves inside the project dir; (b) `../../etc/passwd` rejected; (c) absolute path rejected; (d) a path that normalizes outside the root rejected; (e) two different project ids never resolve into each other's tree.
- Red → green → **commit** `feat(agent): traversal-safe workspace paths`.

### Task 6.2: Document repository API completeness (TDD)
- Audit existing workspace-file endpoints (grep `workspace` in `app/api/projects.py`); ensure browse/list, upload (→ Supabase + `workspace_files` row + ODL ingest enqueue), download (signed URL or proxied bytes), and delete exist with owner checks. Add only what's missing (DRY — reuse `app/storage/project_files.py` + `app/database/workspace_files.py`). TDD each added endpoint. **Commit** `feat(files): complete document repository API`.

### Task 6.3: Sources read-only, artefacts editable — backend (TDD)
- **Files:** artefact edit endpoint `PATCH /projects/{id}/artefacts/{artefactId}` writing a new `draft_artifacts` version (the table is versioned by `(project_id, workflow_type, version)`), with owner + entitlement checks; reject edits to source documents (they're `workspace_files`, not artefacts). TDD: edit creates a new version; editing a non-artefact 404s; non-owner 403s.
- **Commit** `feat(artefacts): versioned in-app artefact editing`.

### Task 6.4: MCP file tools for the agent (TDD — security seam)
- **Files:** add `read_workspace_file` / `write_workspace_file` / `list_workspace` MCP tools in `app/mcp_bridge/server.py`, each going through `resolve_workspace_path` + tool-layer authz (Phase 2). Writes land in the scratch dir; artefact writes go through the `draft_artifacts` path (Task 6.3), not raw files. TDD: authorized read/write inside project scope works; cross-project path or token rejected; traversal rejected.
- **Commit** `feat(mcp): traversal-safe agent file tools`.

### Task 6.5: Frontend — repo browse + artefact editor (vitest)
- Wire `DocumentRepositoryPanel`/`WorkspaceExplorer` to the completed APIs; make `DraftReviewPanel` an editor for artefacts (structured markdown edit → PATCH). Sources open in a read-only viewer (`PageImageViewer.tsx` exists). vitest render tests for the editor save path. **Commit** `feat(web): document repository + artefact editor`.

### Task 6.6: Round-trip gate
- Manual: agent generates an artefact (Phase 5) → user edits it in-app → re-open → agent `read_workspace_file`/`get artefact` sees the edit. Record in `docs/plans/omnigent/phase6-roundtrip.md`. **Gate:** traversal tests green + round-trip verified. **Commit**.

**Phase 6 risks:** scratch-dir/DB divergence — keep `draft_artifacts` (DB) authoritative; the filesystem is a cache. On a fresh container the scratch dir is empty and must rehydrate from DB/Supabase on demand.

---

# Phase 7 — Stripe billing + usage quotas

**Resume context:** Billing is Polar today: `require_active_entitlement` gate ([entitlements.py](../../backend/app/billing/entitlements.py)), `EntitlementState`, `PolarCustomer`/`PolarSubscription` models, `/billing/*` endpoints ([api/billing.py](../../backend/app/api/billing.py)), a `polar_enabled` flag + `polar_*` settings, and env in the compose. Polar was dropped (flat $50/mo). This phase swaps in Stripe **behind the same gate seam** and adds usage quotas keyed off the timing ledger.

**Objective / gate:** Stripe Checkout signup + Customer Portal manage; one webhook flips subscription state in Postgres; the entitlement gate honors Stripe; agent turns soft-warn at 80 % and block past the quota (dashboards/docs stay usable). Gate: webhook signature tests pass; quota block works.

### Task 7.0: Decide model shape + config (record)
- **Files:** `docs/plans/omnigent/phase7-billing-decision.md`; modify `config.py`.
- Add settings: `billing_provider: str = "none"` (`none`|`stripe`), `stripe_secret_key`, `stripe_webhook_secret`, `stripe_price_id`, `stripe_checkout_success_path`, `stripe_portal_return_path`, `agent_monthly_turn_quota: int = 500` (tune later). Keep Polar code importable but inert (`polar_enabled=False`); do not delete it until Phase 8 (safety valve). Decide: new `stripe_customers`/`stripe_subscriptions` tables mirroring the Polar ones vs a generalized `billing_subscriptions`. Recommended: **new Stripe tables** mirroring the Polar shape (lowest risk, parallels `app/database/billing.py`).
- **Commit** `feat(billing): stripe config + decision notes`.

### Task 7.1: `uv add stripe` + Stripe client wrapper (TDD)
- **Files:** `backend/app/billing/stripe_client.py` (create_checkout_session, create_portal_session — thin over the SDK, URLs from settings); Test with the SDK mocked. **Commit** `feat(billing): stripe client wrapper`.

### Task 7.2: Stripe models + migration (TDD)
- **Files:** `app/database/stripe_customer.py`, `app/database/stripe_subscription.py` (mirror the Polar models), `app/database/stripe_billing.py` (upsert/query helpers mirroring `app/database/billing.py`), an Alembic migration. TDD the upserts against a session. **Commit** `feat(billing): stripe customer + subscription models`.

### Task 7.3: Webhook endpoint with signature verification (TDD — security seam)
- **Files:** `app/billing/stripe_webhooks.py` (verify via `stripe.Webhook.construct_event` using `stripe_webhook_secret`; handle `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted` → upsert subscription state); endpoint `POST /billing/webhook/stripe` in `api/billing.py`; Test `tests/billing/test_stripe_webhooks.py`.
- **Tests:** (a) bad signature → 400, nothing written; (b) `checkout.session.completed` creates customer+subscription; (c) `subscription.deleted` marks inactive. Use Stripe's documented test payloads / construct_event mock.
- Red → green → **commit** `feat(billing): stripe webhook sync`.

### Task 7.4: Entitlement gate honors Stripe (TDD)
- **Files:** modify `app/billing/entitlements.py` — `get_entitlement_state` branches on `settings.billing_provider`: `stripe` reads the Stripe tables (active/trialing = not read-only), `none` = internal (unchanged), legacy `polar` path retained. **Keep the `require_active_entitlement` signature identical** so all existing callers (chat, tender, etc.) work unchanged. TDD the three branches. **Commit** `feat(billing): entitlement gate reads stripe`.

### Task 7.5: Usage quota from the timing ledger (TDD)
- **Files:** `app/billing/usage.py` — aggregate agent turns/LLM usage per user per calendar month from the timing ledger (Phase 5); `require_turn_within_quota(session, user)` returning a soft-warn flag at 80 % and raising 402 past 100 %. Wire it into the Phase 3 agent endpoint (before spawning Hermes). Dashboards/document endpoints stay ungated (design: they must keep working past quota). TDD: under quota ok; at 80 % warns; over quota blocks agent turn only.
- **Commit** `feat(billing): monthly agent usage quota`.

### Task 7.6: Frontend billing (vitest)
- Update `BillingPage.tsx` + `lib/types/billing.ts` for Stripe (checkout button → `/billing/checkout` → redirect; manage → `/billing/portal`); surface quota usage + the 80 % warning banner. vitest for the quota banner. **Commit** `feat(web): stripe billing + quota UI`.

### Task 7.7: Gate
- Manual (Stripe test mode): signup via Checkout → webhook flips state → gated action allowed; cancel via Portal → blocked; simulate quota exhaustion → agent blocked, dashboard still works. Record in `docs/plans/omnigent/phase7-billing-gate.md`. **Gate.** **Commit.**

**Phase 7 risks:** GST/merchant-of-record is ours with Stripe (design note) — out of scope for the build, flag to the user. Don't delete Polar yet (Phase 8).

---

# Phase 8 — VPS deploy, Linux validation, legacy cutover

**Resume context:** Everything works in dev. Deploy is Dokploy compose (`sitewise-api` + `sitewise-web`, external `sitewise-public` network, Supabase external). Backend image already has JVM + LibreOffice. This phase ships to `sitewise.au`, validates on the real Linux host, and deletes the legacy cockpit + retired-engine code behind the R3 safety valve.

**Objective / gate:** Production demo on `sitewise.au`: signup → subscribe (Stripe) → create project → upload tenders → "compare the tenders" in chat → streamed Hermes turn with tool chips → comparison panel + artefact → edit artefact. Then legacy pages/engine deleted, suite green.

### Task 8.1: Add Hermes to the backend image
- **Files:** `deploy/docker/backend.Dockerfile` — install the Hermes CLI (pin v0.17.x; use the documented install method from Phase 0 notes), and bake a base `~/.hermes/config.yaml` (platform-key provider + MCP server pointing at `http://127.0.0.1:8000/mcp`, `Authorization: Bearer ${AGENT_TURN_TOKEN}` interpolation). Verify the image builds on Linux and `hermes -z` runs inside it (WSL2/docker). **Commit** `build(docker): bundle hermes CLI in backend image`.

### Task 8.2: Compose + volume + env
- **Files:** `deploy/dokploy.compose.yml`, `deploy/env/sitewise-api.env.example` — add a persistent volume for `AGENT_WORKSPACE_ROOT`; add the agent + Stripe env vars (drop the Polar block once Phase 8.5 removes Polar); add the worker (in-process flag from Task 5.0, or a `sitewise-worker` service). Update `nginx/sitewise.conf` if `/mcp` or SSE needs proxy tuning (SSE: `proxy_buffering off`). **Commit** `build(deploy): agent workspace volume + env + worker`.

### Task 8.3: Deploy to staging-ish + Linux validation
- Deploy the branch to the VPS (or a staging Dokploy app). Validate on the real host: Hermes headless works in-container, MCP round-trips over the internal network, SSE streams through nginx without buffering, ODL runs, the worker drains jobs. Record issues + fixes in `docs/plans/omnigent/phase8-deploy.md`.

### Task 8.4: Production acceptance run (gate)
- Run the full scripted acceptance (Phase 5 + billing) against `sitewise.au`. **Gate:** the end-to-end demo passes in production. Record it.

### Task 8.5: Legacy cutover (only after 8.4 passes)
- Delete the retired reasoning engine (`app/chat/orchestrator.py`, `app/assistant/agent.py`, `app/assistant/run_agent.py` and their now-dead helpers — verify with grep before deleting) and the legacy cockpit routes/pages the new shell replaced (`CockpitPreviewPage`, and any `ProjectCockpitPage`/`TenderCockpitPage` surfaces superseded by the dashboard). Remove Polar code + settings + compose env. Flip `agent_runtime_enabled=true` as the default. Small, revertable commits. Full suite + ruff + web lint green. **Commit** series `chore: retire legacy chat engine`, `chore: remove polar billing`, `feat: agent runtime on by default`.

### Task 8.6: Docs + close-out
- Update `README.md`, `docs/deployment.md`, and the design doc's build-sequence table (Phases 3–8 → done, dated). **Commit** `docs: agent-first dashboard shipped`.

**Phase 8 risks:** SSE through nginx (buffering) is a classic failure — test explicitly; Hermes-in-Docker networking to `127.0.0.1:8000/mcp` (same container) vs a separate host; big-bang deletion regressions (that's why 8.5 is gated on 8.4 and done in revertable steps).

---

## Global completion

After Phase 8: the flagship demo runs in production, legacy code is gone, billing is Stripe, and the design doc's build sequence is fully checked. Suggested next tranche (not in this plan): re-skin the pattern for PMP and Cost Plan (design decision #6, "prove once, re-skin"), and add a second reviewer sub-agent for cross-checks (YAGNI until the flagship is stable).

## Execution note for the handoff agent

- Phases are **sequential** (3→8); within a phase, tasks are mostly sequential. Do not start Phase 3 until Phases 0–2 land.
- The three "READ FIRST" corrections override the design doc wherever they conflict.
- Every task ends in a commit with the `Co-Authored-By` trailer. Security/contract seams (3.2 SSE contract, 6.1 traversal, 7.3 webhook signature, tool-layer authz) are test-first and never skipped.
- Where a task says "TDD," write the failing test first, watch it fail, then implement. Where a task is a spike/gate (manual E2E, UX checklist, deploy), produce the recorded artefact named in the task as the evidence.
