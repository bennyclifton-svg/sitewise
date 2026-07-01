# Phase 7 — Retire Clerk's old reasoning engine

> Part of [Omnigent Shell Integration](./README.md) — **read the README first**.
> **Depends on:** Phases [2](./02-domain-agent-tool-bridge.md)–[6](./06-per-project-workspaces.md) (Hermes must actually cover the workflows before deleting the old engine).
> **Resume context:** Hermes now reasons, calls Clerk tools, and the panels/workspaces work. Clerk's bespoke `assistant/agent.py` + `chat/orchestrator.py` + workflow engine are now redundant. This phase removes them — but only after confirming every old capability has a new home. Decision #2.

**Goal:** The bespoke assistant/orchestrator is gone; the backend test suite is green; no dead routes.

---

### Task 7.1: Map old capabilities to their new homes

**Files:**
- Create: `docs/plans/omnigent/retirement-map.md`
- Reference: `backend/app/assistant/agent.py`, `backend/app/chat/orchestrator.py`, `backend/app/workflows/*`, `backend/app/api/chat.py`.

**Steps:**
1. For each capability the old engine provided (project chat, `create_pmp`, `create_cost_plan`, `sort_files`), record where it now lives: an MCP tool (Phase 2), a dedicated panel action (Phase 5), or intentionally dropped.
2. Flag anything with no new home — that's a gap to close **before** deletion.

**Acceptance:** Every old capability is either re-homed or explicitly retired, in writing.

---

### Task 7.2: Remove the old chat/assistant surface

**Files:**
- Delete: `backend/app/assistant/`, `backend/app/chat/orchestrator.py`, old `backend/app/api/chat.py` routes (or reduce to what the shell still needs).
- Modify: `backend/app/main.py` (drop `chat_router` if fully replaced).
- Test: update/remove the corresponding tests.

**Steps:**
1. Delete in small commits; after each, run the full backend suite (`cd backend && uv run pytest`) and fix fallout.
2. Keep `workflows/*` only if a panel action still calls it via a tool; otherwise retire per the map.

**Acceptance:** Backend suite green with the old engine removed; no dead routes. Commit(s) `refactor: retire bespoke assistant/orchestrator (superseded by hermes)`.

---

**When all tasks pass:** mark Phase 7 ☑ in [README.md](./README.md). Proceed to [Phase 8](./08-cutover-cleanup.md).
