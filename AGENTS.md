# Agent Instructions

This file is the source of truth for any coding agent (Claude Code, Cursor, Codex, etc.) working in this repo. Read it before touching code.

## Stack

- **Backend:** Python + FastAPI
- **Frontend:** Vite + React SPA + TypeScript
- **Database:** Supabase Postgres (users, chats, projects, source documents, chunks, draft artefacts)
- **Migrations:** SQLAlchemy models + Alembic from the backend
- **Retrieval:** Supabase `pgvector` + Postgres full-text search
- **Auth:** Supabase Auth
- **Hosting:** Railway (backend service + frontend service)
- **LLM + embeddings:** OpenAI

Stack is locked unless explicitly changed. Don't propose alternatives without a stated reason.

## Repo layout

```text
clerk/
├── AGENTS.md           # this file
├── README.md
├── data/               # local corpus + download script (payloads gitignored)
├── docs/               # specs, briefs, design notes
├── backend/            # FastAPI service (see backend/AGENTS.md)
└── frontend/           # React SPA (see frontend/AGENTS.md)
```

## Migration direction

The governing migration document is `docs/plans/2026-06-07-clerk-practice-intelligence-integration-prd.md`. Clerk is the canonical hosted product repo. Practice Intelligence is source material and reference implementation; Hermes is retired as a separate runtime once Clerk reaches workflow parity.

## Tender Comparison Module (TCM)

The governing TCM document is `docs/plans/2026-06-11-tender-comparison-module-prd.md`. These rules are binding for all future TCM work:

- TCM lives in `backend/tender/` and owns only `tender_*` tables. It may reference Clerk `projects`, `users`, and `drafts` by FK only. No Clerk core module may import from `backend/tender/`.
- TCM never uses Clerk's RAG chunking pipeline. It is schema-oriented extraction only, sharing just upload/storage with Clerk core.
- LLMs classify and map; all arithmetic, totals, deltas, comparables, percentages, and benchmark calculations are computed in Python.
- Prompts are versioned files in `backend/tender/llm/prompts/`. Once the evaluation harness exists, no prompt, model, or taxonomy change merges without an eval run under PRD Section 14.
- Seed data in `data/tender/` is loaded by idempotent upserts. Run `data/tender/tools/validate.py` in CI.
- Report language must come from `data/tender/report_language.yaml`; never free-type customer-facing report phrases.

## Dependency policy

**Default: write it yourself. Reach for a library only when the alternative would be non-trivial, error-prone, or reinvention of a standard.** Every dependency is a liability — bundle size, supply-chain risk, future upgrade work.

OK to depend on:

- Things that are genuinely hard to get right (HTTP clients, ASGI servers, SQL drivers, parsers, LLM SDKs, ORM, migrations, auth SDKs).
- The declared stack (FastAPI, React, Vite, Supabase clients, OpenAI SDK, etc.).

Not OK:

- Helper libraries that wrap 5–20 lines of stdlib or platform APIs.
- Frameworks where a function would do.
- "Nicer API" layers on top of an already-present dependency.

Before adding a runtime dep, answer in the commit message:

1. What exactly does it do that we can't write in <30 lines of clear code?
2. How often does it get used?
3. What's its maintenance / transitive-dep footprint?

Per-stack specifics live in `backend/AGENTS.md` and `frontend/AGENTS.md`.

## Configuration

A single settings module is the source of truth for environment per service (`backend/app/config.py`, `frontend/lib/env.ts`). Do not call `os.getenv` / read `process.env` directly in app code. Do not call `load_dotenv` anywhere. If a third-party SDK reads env vars directly, mirror them in the settings module — don't sprinkle `setdefault` elsewhere.

Fail fast on startup if required config is missing. No silent fallbacks that hide real config errors.

## Code style (universal)

- **Small, obvious functions.** A 15-line function with clear names beats a three-class abstraction.
- **No premature abstraction.** Three similar lines is better than a badly-named base class. Extract when there's a third caller, not a hypothetical one.
- **No error handling for cases that can't happen.** Trust internal callers and framework guarantees. Validate only at boundaries: HTTP input, external APIs, DB writes, untrusted parsing.
- **No backwards-compat shims** unless explicitly asked for.
- **No feature flags** added speculatively.
- **Comments:** explain *why* when non-obvious, never *what*. Remove stale TODOs.
- **Keep files focused.** Prefer small modules.
