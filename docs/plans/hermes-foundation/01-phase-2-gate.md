# Phase 2 Gate: MCP Bridge Ready For Hermes

## Objective

Prove the MCP bridge is complete before any Phase 3 Hermes runtime work starts.
Phase 3 must not begin until this gate is green.

## Current Repo Snapshot

Status: **GREEN on 2026-07-03**. Phase 3 may begin.

Present:

- `backend/app/mcp_bridge/tokens.py`
- `backend/app/mcp_bridge/auth.py`
- `backend/app/mcp_bridge/server.py`
- `list_tender_comparisons`
- `get_tender_comparison`
- `start_tender_comparison`
- `search_documents`
- `/mcp` mounted in `backend/app/main.py`
- mounted `/mcp` auth integration coverage
- unit tests for tokens, auth, comparison read tools, action/search tools,
  and mount behavior
- `fastmcp==3.4.2` declared in `backend/pyproject.toml`

Manual smoke:

- WSL Hermes v0.17.0 connected to `http://<windows-host>:8000/mcp/`,
  discovered all four Clerk tools, and called `list_tender_comparisons` with a
  minted project turn token. Result: `{"result":{"result":[]}}`.

## Required Work

- Complete `backend/app/mcp_bridge/server.py` with the remaining Phase 2 tools:
  `start_tender_comparison` and `search_documents`.
- Keep tools thin. Delegate to existing TCM services, tender router helpers, job
  enqueue helpers, and the existing retrieval layer.
- Mount the FastMCP app at `/mcp` from `backend/app/main.py`, preserving the
  existing FastAPI lifespan.
- Add `backend/tests/mcp_bridge/test_mount.py` to prove MCP initialize works and
  unauthenticated tool calls return an authorization error.
- Run the focused MCP test suite, then the backend suite and ruff.
- Run one manual smoke in WSL/Linux: Hermes calls `/mcp` with a minted turn
  token and successfully lists tender comparisons.

## Gate Checklist

- [x] `uv run pytest tests/mcp_bridge -q` — 22 passed.
- [x] `uv run pytest tests -q` — 615 passed, 7 skipped.
- [x] `uv run ruff check .`
- [x] `/mcp` is reachable from the FastAPI app.
- [x] Missing or invalid turn token returns a tool authorization error.
- [x] Cross-project token cannot access another project.
- [x] Hermes can call at least one read tool through the mounted MCP endpoint.
- [x] `start_tender_comparison` enqueues the expected TCM jobs.
- [x] `search_documents` delegates to the existing retriever.

## Handoff Rule

Only after every checklist item passes may Phase 3 begin. If any item fails,
finish or revise Phase 2 instead of compensating in the Hermes runtime.
