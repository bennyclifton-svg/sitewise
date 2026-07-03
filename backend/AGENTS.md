# Backend Agent Notes

This is the FastAPI service for Clerk. Read `../AGENTS.md` first; universal
direction and code rules live there. This file adds backend-specific guidance.

## Current Direction

The backend is moving from the legacy PydanticAI grounded-RAG chat path toward a
Hermes-backed agent runtime:

- Phase 2 adds `app/mcp_bridge/` and mounts FastMCP at `/mcp`.
- Phase 3 adds `app/agent/` for Hermes process invocation, AI-SDK-compatible
  SSE relay, session mapping, bounded concurrency, and cancellation.
- Phase 8.5 removes the old PydanticAI chat/orchestrator only after production
  acceptance passes.

Do not delete `app/assistant/`, `app/chat/orchestrator.py`, or Polar billing
early. They are live legacy modules until the planned cutover.

## Stack

- Python 3.12+
- FastAPI + uvicorn
- Pydantic v2 + pydantic-settings
- SQLAlchemy models + Alembic migrations
- Supabase Auth, Supabase Postgres, Supabase Storage
- OpenAI SDK for current LLM/embedding calls
- Hermes CLI via the planned `app/agent/` module
- FastMCP via `app/mcp_bridge/`
- `pytest` and `ruff`
- `uv` for dependency and project management

## Layout

```text
backend/
|-- alembic/
|   |-- env.py
|   `-- versions/
|-- app/
|   |-- main.py              # FastAPI entrypoint and router/mount wiring
|   |-- config.py            # single backend env source of truth
|   |-- agent/               # Phase 3 Hermes runtime, SSE relay, concurrency
|   |-- mcp_bridge/          # Phase 2 MCP tools and turn-token auth
|   |-- api/                 # FastAPI routers
|   |-- auth/                # Supabase JWT verification
|   |-- billing/             # Polar today, Stripe in Phase 7
|   |-- chat/                # legacy grounded-RAG chat and AI SDK streaming
|   |-- assistant/           # legacy PydanticAI agent modules
|   |-- retrieval/           # project/platform document retrieval
|   |-- grounding/           # citation validation for legacy chat
|   |-- database/            # SQLAlchemy models and query helpers
|   |-- storage/             # Supabase Storage helpers
|   |-- sitewise/            # SiteWise draft/workflow helpers
|   `-- workflows/           # existing PMP/cost/document workflows
|-- tender/                  # TCM module; owns tender_* tables
|-- ingest/                  # corpus/import tooling
|-- tests/
`-- pyproject.toml
```

## Backend Rules

- Type hints on public functions and module-level values. Do not annotate every
  local unless it clarifies the code.
- Use `async def` for route handlers and request-path I/O.
- Do not run blocking network or subprocess work on the event loop. Wrap or
  isolate it behind an async interface.
- Validate only at boundaries. Internal callers are trusted.
- Security seams are test-first: MCP turn tokens, project authorization,
  traversal-safe paths, webhook signatures, and agent cancellation.
- TCM arithmetic is Python. LLMs classify, extract, map, adjudicate, or draft;
  they do not compute totals or percentages.

## Configuration

`app.config.settings` is the backend source of truth. Import settings where
needed. Never call `os.getenv` in app code and never call `load_dotenv`.

If an SDK reads env vars directly, expose the values through `config.py` first.
For Hermes, inject per-turn secrets into the spawned child process environment,
not argv.

## Database Migrations

- Alembic is the source of truth for schema changes. Do not change production
  tables manually in Supabase.
- SQLAlchemy models describe tables and columns. Alembic autogenerate creates
  candidates, but every migration must be reviewed.
- Supabase/Postgres-specific features belong in explicit migration operations:
  extensions, generated `tsvector` columns, HNSW/GIN indexes, RLS, grants, and
  policies.
- Alembic must use the direct or session database connection, not the transaction
  pooler.
- Run migrations from `backend/` with `uv run alembic upgrade head`.

## Tests

- Fast unit tests should hit no network and no live database.
- Integration tests use `@pytest.mark.integration`.
- Tender eval/speed tests use `@pytest.mark.tender_eval`.
- Backend commands run from `backend/` via `uv run ...`.
- Prefer testing through the module interface that callers use. Do not reach past
  an interface just to make a test easy.

## Anti-Patterns

- `os.getenv` / `load_dotenv` outside config.
- Custom response envelopes around FastAPI responses.
- Over-catching `Exception` just to log and re-raise.
- Shared mutable runtime state through globals instead of app state or explicit
  registries.
- Silent config fallbacks.
- New Clerk core imports from `backend/tender/` other than explicit router/mount
  or MCP adapter wiring.

