# Agent Instructions

This file is the source of truth for coding agents working in this repo. Read it
before touching code. Product direction changed in July 2026: Clerk is moving
toward a Hermes-backed, agent-first hosted product with Tender Comparison as the
flagship workflow.

## Canonical Docs

Read these in order when direction matters:

1. `docs/plans/2026-07-02-hermes-foundation-phases-0-2.md`
2. `docs/plans/2026-07-03-hermes-foundation-phases-3-8.md`
3. `docs/plans/2026-06-11-tender-comparison-module-prd.md`
4. `docs/architecture.md`

The Hermes phase plans govern product flow and migration sequence. The TCM PRD
governs Tender Comparison internals. If an older doc disagrees with the July
Hermes plans, the July Hermes plans win.

## Stack

- **Backend:** Python 3.12 + FastAPI
- **Frontend:** Vite + React SPA + TypeScript
- **Database:** Supabase Postgres
- **Storage:** Supabase Storage for canonical project files
- **Migrations:** SQLAlchemy models + Alembic from the backend
- **Retrieval:** Supabase `pgvector` + Postgres full-text search
- **Auth:** Supabase Auth
- **Agent runtime:** Hermes CLI headless, invoked by `backend/app/agent/`
- **Tool bridge:** FastMCP mounted on FastAPI at `/mcp`
- **LLM + embeddings:** OpenAI, with Hermes platform-key routing in later phases
- **Billing:** Polar exists today; Stripe replaces it in Phase 7
- **Hosting:** Docker + Dokploy on the `sitewise.au` VPS, Supabase external

Stack is locked unless explicitly changed. Do not propose alternatives without a
stated reason.

## Repo Layout

```text
clerk/
|-- AGENTS.md
|-- README.md
|-- data/
|-- docs/
|   |-- guides/
|   |-- plans/
|   `-- issues/
|-- backend/
`-- frontend/
```

## Product Direction

Clerk is the canonical hosted product repo. The current direction is:

- Phase 2 lands the MCP tool bridge with per-project turn-token authorization.
- Phases 3-8 add the Hermes runtime, AI-SDK-compatible SSE relay, chat polish,
  natural-language Tender Comparison, workspace/artefact editing, Stripe
  billing, VPS deployment, and legacy cutover.
- The existing PydanticAI grounded-RAG chat, Polar billing, and cockpit pages are
  legacy-retained until the Phase 8.5 cutover gate passes. Do not delete or
  rewrite them early.

## Tender Comparison Module (TCM)

The governing TCM document is
`docs/plans/2026-06-11-tender-comparison-module-prd.md`. These rules are
binding for all TCM work:

- TCM lives in `backend/tender/` and owns only `tender_*` tables. It may
  reference Clerk `projects`, `users`, and `drafts` by FK only. Clerk core
  should not import from `backend/tender/` except for the explicit FastAPI router
  mount and planned MCP tool adapters.
- TCM never uses Clerk's RAG chunking pipeline. It is schema-oriented extraction
  only, sharing upload/storage with Clerk core.
- LLMs classify and map; all arithmetic, totals, deltas, comparables,
  percentages, and benchmark calculations are computed in Python.
- Prompts are versioned files in `backend/tender/llm/prompts/`. Once the
  evaluation harness exists, no prompt, model, or taxonomy change merges without
  an eval run under PRD Section 14.
- Seed data in `data/tender/` is loaded by idempotent upserts. Run
  `data/tender/tools/validate.py` in CI.
- Report language must come from `data/tender/report_language.yaml`; never
  free-type customer-facing report phrases.

## Dependency Policy

Default: write it yourself. Reach for a library only when the alternative would
be non-trivial, error-prone, or reinvention of a standard. Every dependency is a
liability: bundle size, supply-chain risk, and future upgrade work.

OK to depend on:

- Things that are genuinely hard to get right: HTTP clients, ASGI servers, SQL
  drivers, parsers, LLM SDKs, ORM, migrations, auth SDKs.
- The declared stack: FastAPI, React, Vite, Supabase clients, OpenAI SDK,
  FastMCP, Hermes CLI integration, Stripe SDK when Phase 7 begins.

Not OK:

- Helper libraries that wrap 5-20 lines of stdlib or platform APIs.
- Frameworks where a function would do.
- "Nicer API" layers on top of an already-present dependency.

Before adding a runtime dependency, answer in the commit message:

1. What exactly does it do that we cannot write in under 30 lines of clear code?
2. How often does it get used?
3. What is its maintenance and transitive-dependency footprint?

Per-stack specifics live in `backend/AGENTS.md` and `frontend/AGENTS.md`.

## Configuration

A single settings module is the source of truth for environment per service:
`backend/app/config.py` and `frontend/src/lib/env.ts`. Do not call `os.getenv`,
read `process.env`, or read `import.meta.env` directly in app code. Do not call
`load_dotenv` anywhere.

If a third-party SDK reads environment variables directly, mirror those settings
in the service settings module. Do not sprinkle `setdefault` elsewhere.

Fail fast on startup if required config is missing. No silent fallbacks that hide
real config errors.

## Code Style

- Small, obvious functions. A 15-line function with clear names beats a
  three-class abstraction.
- No premature abstraction. Extract when there is a real third caller or a clear
  module interface worth protecting.
- Validate at boundaries: HTTP input, external APIs, DB writes, untrusted
  parsing, tool calls, file paths, webhooks.
- No backwards-compat shims unless explicitly asked for.
- No speculative feature flags. Existing phase gates and runtime switches are
  allowed where the plan calls for them.
- Comments explain why when non-obvious, never what. Remove stale TODOs.
- Keep files focused. Prefer small modules with clear interfaces.

