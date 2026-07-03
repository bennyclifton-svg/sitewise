# Agent-First Construction Management Dashboard — Design

Date: 2026-07-02
Status: validated design (brainstormed and approved 2026-07-02)
Supersedes: `docs/plans/omnigent-shell-integration/` Phases 1–8 (Phase 0 spike results remain valid and are relied on here)

> **Current-status note:** Keep this as design history and rationale. The
> implementation plan in
> `docs/plans/2026-07-03-hermes-foundation-phases-3-8.md` supersedes this file
> where it is more precise, especially: Clerk chat is already Vercel AI SDK, not
> Zustand; Supabase Storage is canonical for uploaded files, not the VPS
> filesystem; and Phase 3 must preserve the existing AI-SDK SSE event vocabulary.

## Summary

Hosted Clerk at `sitewise.au` becomes an agent-first construction management dashboard:
**Hermes is the reasoning brain, Clerk's own React SPA is the shell.** Omnigent is **not**
vendored — its chat UI components are transplanted selectively instead. Clerk's FastAPI
stays the system of record and exposes domain logic to Hermes via MCP-over-HTTP tools.
Flagship workflow: natural-language tender comparison. Users subscribe via Stripe; the
agent runs on a platform API key.

## Decisions ledger (resolved 2026-07-02)

| # | Decision | Resolution |
|---|----------|-----------|
| 1 | Shell strategy | **Hermes brain, Clerk shell.** Keep/evolve Clerk's React SPA; do not vendor Omnigent's web app or server. Transplant Omnigent chat components (Apache-2.0) where they fit; rebuild on shadcn where entangled. |
| 2 | LLM credentials for subscribers | **Platform API key**, cost baked into subscription. Founder's ChatGPT OAuth is dev-only. |
| 3 | Local-first plan (`docs/local-repo/local-repo-v3.md`) | **Parked; doctrine adopted.** Hosted VPS SaaS is the only product track. Adopted as law: deterministic Python first, bounded/batched LLM calls, timing ledger on every workflow run, CI speed gates, content-hash extraction cache. Parked: Electron, Redis/arq (revisit only if queueing — not extraction — fails the speed gate), offline mode. |
| 4 | OpenDataLoader (ODL) | **Universal PDF intake from day one.** All PDF ingestion goes through ODL. Engineering hedge: ODL sits behind an extraction interface; accuracy eval on real fixtures (Enmore/Kaposi/NexusBuilt) before the old extraction path is deleted. JVM joins the backend Docker image. |
| 5 | File access | **In-app repo + artefact editing.** Per-project workspace on VPS filesystem. Sources (PDFs) read-only to users — view/annotate. Agent artefacts (PMP, cost plan, comparison reports) editable through structured in-app editors. Agent works in the same tree via traversal-safe scoped tools. |
| 6 | Flagship workflow | **Tender comparison.** "Compare the 3 selected structural tenders" → Hermes → TCM pipeline → dashboard panel + report artefact. Prove once, re-skin for PMP/cost. |
| 7 | Billing | **Stripe Checkout + Customer Portal** (Polar dropped — flat fee too costly pre-revenue). One webhook flips `status`/`tier`/`current_period_end` on the user; a FastAPI dependency gates agent turns and project creation. Manual `subscription_active` flag is an acceptable interim for hand-recruited users. Stripe is not a merchant of record — GST stays ours; revisit Lemon Squeezy/Paddle only if tax admin becomes a burden. |

### Carried over unchanged from the omnigent-shell plan

- MCP-over-HTTP tool bridge; every tool delegates to an existing Clerk service (DRY).
- Per-project tenant isolation **enforced at the tool layer** (project id == tenant id).
- Supabase Auth (email) as identity source of truth.
- Old cockpit pages survive behind legacy routes until the new shell reaches parity (R3 safety valve), then delete.
- Route Hermes auxiliary tasks (title generation, compression) to a cheap model in config.

### Dropped from the omnigent-shell plan

- Vendoring Omnigent's web app and server (old Phases 1, 4, 5 as written).
- Identity-header bridge into Omnigent (old Phase 3) — no Omnigent server to bridge into.
- Omnigent host/session runtime — sessions persist in Clerk's Postgres, not `~/.omnigent/chat.db`.

## Architecture

```
Browser (Clerk React SPA — dashboard-first)
  ├─ Left nav: Projects → Overview / Documents / Tenders / Cost Plan / PMP
  ├─ Chat panel (docked right or full-screen; Omnigent-grade polish)
  │     ↓ SSE
Clerk FastAPI (system of record)
  ├─ backend/agent/  — Hermes lifecycle, streaming, sessions, bounded concurrency
  ├─ MCP-over-HTTP server (fastmcp) — thin tools → existing services
  ├─ Workflow pipelines (TCM, PMP, cost) + timing ledger + speed gates
  ├─ ODL intake (JVM) — PDF → structured JSON, content-hash cached
  └─ Stripe webhooks + quota checks
  ↕
Supabase (auth + Postgres)   VPS filesystem (per-project workspaces)
  ↕
Hermes CLI (headless, platform API key, model-agnostic config)
```

Flagship flow: chat "compare the 3 selected structural tenders" → backend authenticates
(Supabase JWT), resolves project workspace, invokes Hermes with the Clerk agent prompt +
MCP URL + workspace `cwd` → Hermes calls tools (`list_selected_documents`,
`start_tender_comparison`, `get_comparison_status`, …) → TCM pipeline runs (ODL intake →
classify → map → compute → flag) → results stream into chat **and** populate the
comparison panel; the report is an editable artefact.

## Chat experience (parity bar: Omnigent)

Both codebases share React 19 + Vite + Tailwind v4 + shadcn/ui + TanStack Query +
Zustand + Router 7, so transplanting is a porting job, not a rewrite. Parity means:

- Token streaming (SSE) with smooth incremental markdown/table rendering.
- Tool-call visibility: collapsible status chips ("Reading Kaposi.pdf… ✓",
  "Running comparison pipeline… 3/5 stages") — never a dead spinner.
- Session management: per-project list, resume, rename, delete; persisted in Postgres.
- Working Stop button: cancels the Hermes turn **and** spawned pipeline jobs.
- Artefact cards in-chat linking to dashboard panels.
- Readable error states (rate-limit, tool failure, partial pipeline failure).

Transplant Omnigent's message list / streaming renderer / tool chips; rewire their data
layer to Clerk endpoints; rebuild on shadcn primitives where too entangled.

## Backend design

- **`backend/agent/`** — owns the Hermes lifecycle (per-turn invocation or pooled session;
  decided by the Phase 0 probe). Injects platform API key, Clerk agent prompt, MCP URL,
  workspace `cwd`. Streams over SSE. Concurrency bounded by config (max turns per host,
  per user) — no unbounded fan-out.
- **MCP tools** — `search_documents`, `get_document`, `list_selected_documents`,
  `start_tender_comparison`, `get_comparison_status`, `get_comparison_result`,
  `create_pmp_draft`, `update_cost_plan_row`, … Thin; authorized per project at the tool
  layer. This is a security seam: test-first, never skipped.
- **Workspaces** — `workspaces/{project_id}/sources/` (read-only to users) and
  `artefacts/` (in-app editable). One traversal-safe path helper; Hermes file tools
  scoped to the workspace; users reach the tree only through Clerk APIs.
- **ODL intake** — every uploaded PDF → ODL → structured JSON persisted beside the
  original, keyed by content hash (same bytes = cache hit; filename/path never a key).
  Tender extraction consumes ODL output; PMP/cost evidence reads the same layer.
- **Timing ledger** — every workflow run records stage, duration, LLM call count,
  tokens, retries, cache hit/miss, model. Wired into TCM first. Doubles as the usage
  meter for billing quotas.
- **Worker** — existing Postgres-polling worker stays at MVP.

## Billing and metering

- Stripe Checkout (hosted) for signup; Customer Portal (hosted) for cancel/card changes.
- One webhook endpoint (`checkout.session.completed`,
  `customer.subscription.updated/deleted`) → flips flag in Postgres.
- Quotas key off `tier`: soft-warn at 80%, block agent turns past limit (dashboards and
  documents stay usable). One generous tier at MVP; watch ledger data before inventing more.

## Deployment

- VPS via Dokploy (`sitewise.au`). Images: `backend` (FastAPI + MCP + Hermes CLI + JVM;
  workspaces on a persistent volume), `frontend` (static SPA behind reverse proxy).
  Supabase stays hosted/external.
- Dev loop: backend + SPA on Windows as today; anything touching Hermes execution or
  ODL-in-Docker verifies in WSL2 (spike discipline). CI and deploy are Linux.
- Secrets (platform LLM key, Supabase service key, Stripe webhook secret) env-injected
  via Dokploy.

## Risks (ordered)

1. **Hermes headless mode unverified** — the whole design hinges on programmatic
   invocation with streaming. The spike only proved the interactive TUI.
   *Phase 0 probes exactly this before any product code.*
2. **Chat polish parity** — transplant may fight Omnigent's stores. Fallback:
   rebuild-on-shadcn using Omnigent as visual spec. Gate: manual UX checklist
   (streaming, chips, stop, resume).
3. **ODL on messy construction PDFs** — universal-from-day-one accepted; hedge is the
   extraction interface + fixture eval before deleting the old path.
4. **TCM speed (hours today)** — doctrine applies: batching rules, content-hash cache,
   timing ledger, CI speed gate (60–90 s simple 3-tender package cold).
5. **Platform-key cost blowout** — quotas from day one; cheap model for aux tasks.

## Testing

- TDD on security seams: tool-layer authz, traversal-safe paths, Stripe webhooks.
- TDD on deterministic pipeline stages; eval harness green **before** any pipeline refactor.
- Vitest render tests for chat components.
- Flagship demo = manual acceptance script; chat polish = manual UX checklist.
- Speed gates CI-enforced per adopted doctrine.

## Build sequence

| Phase | Work | Gate |
|-------|------|------|
| 0 | Probe Hermes headless + streaming + platform API key (WSL2 spike) | **Done 2026-07-02** — probe PASS (see `omnigent/hermes-headless-probe.md`) |
| 1 | Commit/land Stage-0.5 tender work; ODL intake behind extraction interface + fixture eval | **Done 2026-07-03** — landed as split commits; ODL eval baseline recorded (3 fixtures, ~1.3 s/doc) |
| 2 | MCP tool bridge + per-project authz (TDD) | **Done 2026-07-03** — authz tests green; 4 tools delegate to existing services; mounted at `/mcp` |
| 3 | `backend/agent/` runtime + SSE + sessions in Postgres | Streamed turn E2E via API |
| 4 | Chat UI transplant into Clerk SPA | Manual UX checklist passes |
| 5 | Flagship E2E: NL trigger → TCM → panel + artefact | Speed gate + acceptance script |
| 6 | Workspaces, doc repo panel, artefact editing | Traversal tests; edit round-trip |
| 7 | Stripe + quotas | Webhook tests; quota block works |
| 8 | VPS deploy, Linux validation, delete old cockpit + retired plan phases | Production demo on `sitewise.au` |

## Housekeeping noted during design

- The omnigent-shell plan's "Repo geography" note is stale: **this repo**
  (`d:/AI Projects/clerk`, remote `bennyclifton-svg/sitewise.git`) is the target.
- Tender Stage-0.5 and omnigent work are interleaved uncommitted on
  `feature/omnigent-shell` — separate and land as part of Phase 1.
