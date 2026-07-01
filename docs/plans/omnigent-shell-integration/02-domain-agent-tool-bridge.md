# Phase 2 — The Clerk domain agent (Hermes) + tool bridge

> Part of [Omnigent Shell Integration](./README.md) — **read the README first** (esp. the "Reference: agent-config shape" section).
> **Depends on:** [Phase 1](./01-vendor-omnigent.md) (vendored Omnigent runs in-repo).
> **Resume context:** Omnigent + Hermes run in-repo but know nothing about Clerk. This phase is the **core integration**: define a `clerk` Hermes agent, and expose Clerk's business logic (documents, tender comparison, PMP, cost plan) to it as MCP tools mounted in Clerk's existing FastAPI app. This is the "embed Clerk as a layer below Omnigent" step.

**Goal:** Hermes can list/search a project's documents and start + read a tender comparison, entirely through project-scoped MCP tools that delegate to existing Clerk services.

**Reference pattern:** `examples/scribe/config.yaml` / `examples/sentinel/config.yaml` — a domain "lead" agent that authors prose, uses `sys_os_*` tools scoped to a `cwd`, delegates read-only work to sub-agents, and enforces guardrails via policies. The Clerk agent is the same shape: a construction-PM lead that reasons over project documents and calls Clerk tools.

---

### Task 2.1: Failing test for the Clerk MCP tool server

**Files:**
- Test: `backend/tests/mcp/test_clerk_tools.py`
- Create (later): `backend/app/mcp/server.py`

**Step 1 — failing test:**
```python
# backend/tests/mcp/test_clerk_tools.py
from app.mcp.server import build_mcp_app, list_tool_names

def test_mcp_exposes_core_clerk_tools():
    names = set(list_tool_names())
    assert {
        "list_project_documents",
        "search_project_documents",
        "compare_tenders",
        "get_comparison",
    }.issubset(names)

def test_mcp_app_mounts():
    assert build_mcp_app() is not None
```

**Step 2 — run, expect fail:** `cd backend && uv run pytest tests/mcp/test_clerk_tools.py -v` → FAIL (module not found).

---

### Task 2.2: MCP dependency + skeleton server

**Files:**
- Modify: `backend/pyproject.toml` (add `fastmcp` or `mcp`)
- Create: `backend/app/mcp/__init__.py`, `backend/app/mcp/server.py`

**Steps:**
1. Add the MCP server SDK (`fastmcp` gives an ASGI app mountable in FastAPI; confirm version-compatible with the `mcp` client Omnigent uses in `omni/omnigent/tools/mcp.py`).
2. `uv sync`.
3. Implement `build_mcp_app()` returning a FastMCP ASGI app and `list_tool_names()` returning the registered names. Register the four tools as **stubs first** (return a clear "not implemented" payload), each taking an explicit `project_id: str` first argument (the tenant scope — see Task 2.5).
4. Run → PASS.

**Commit:** `feat(mcp): clerk tool server skeleton with project-scoped tool stubs`.

---

### Task 2.3: Implement `list_project_documents` + `search_project_documents`

**Files:**
- Modify: `backend/app/mcp/server.py`
- Reference (read, don't rewrite): `backend/app/retrieval/catalog.py`, `backend/app/database/projects.py`, `backend/tender/services/*`.
- Test: extend `backend/tests/mcp/test_clerk_tools.py`

**Steps (TDD each tool):**
1. Failing test: given a seeded project with N documents, `list_project_documents(project_id)` returns those N rows (mock the DB session/service like existing tender/app tests).
2. Implement by delegating to the existing catalog/retrieval service — **do not** duplicate query logic; call what `ProjectCockpitPage`'s evidence endpoint already calls.
3. Repeat for `search_project_documents(project_id, query)` → returns cited chunks (reuse the existing retrieval path; keep page/bbox/heading citation metadata).
4. Run → PASS. Commit.

**Acceptance:** Both tools return real project-scoped data in tests, reusing existing services (DRY).

---

### Task 2.4: Tender-comparison tools (the headline UX)

**Files:**
- Modify: `backend/app/mcp/server.py`
- Reference: `backend/tender/router.py` (prefix `/api/tender`), `backend/tender/services/jobs.py`, `backend/tender/worker.py`, `backend/tender/services/mapping.py`.
- Test: `backend/tests/mcp/test_compare_tenders.py`

**Target behavior (decision #7):** user types *"compare the 3 structural tenders selected in the document repo"* → Hermes resolves which documents from the selection + its reasoning over metadata → calls `compare_tenders(project_id, document_ids)` → tool kicks off the existing tender pipeline for those docs and returns a comparison handle → `get_comparison(comparison_id)` returns status + results for the dedicated panel (Phase 5).

**Steps:**
1. Failing test: `compare_tenders(project_id, document_ids=[…])` enqueues the comparison pipeline (assert a `tender_jobs`/comparison record is created; mock the worker).
2. Implement `compare_tenders` as a thin wrapper over `tender/services/jobs.py` — enqueue, return `{comparison_id, status}`. **Do not** re-implement the worker.
3. Failing test + impl for `get_comparison(comparison_id)` → returns status and, when ready, the mapping/silence results the existing services produce.
4. Run → PASS. Commit `feat(mcp): compare_tenders + get_comparison over existing tender pipeline`.

**Acceptance:** Hermes-callable tools can start a tender comparison from a set of document ids and read its result, without touching worker internals. (Ref R4: reuse handlers that work.)

---

### Task 2.5: Enforce per-project isolation at the tool boundary

**Files:**
- Modify: `backend/app/mcp/server.py`
- Create: `backend/app/mcp/context.py`
- Test: `backend/tests/mcp/test_isolation.py`

**Steps:**
1. Failing test: a tool call for `project_id=A` by a user with no membership of A raises/returns a permission error; every tool filters by `project_id`.
2. Implement `require_project_access(user_id, project_id)` reusing Clerk's existing membership/ownership checks (`backend/app/api/projects.py`, `backend/app/database/projects.py`). Every tool calls it first.
3. Thread caller identity: the MCP server reads the identity Omnigent forwards (Phase 3 wires how it arrives). For MVP, require an explicit authenticated principal per call; reject anonymous.
4. Run → PASS. Commit.

**Acceptance:** No tool returns another project's data. This is security seam #1 — do not skip. Matches the "three places" tenant doctrine (SQL filter + authorize + scoped identity).

---

### Task 2.6: Mount MCP in Clerk's FastAPI + declare it to the Clerk agent

**Files:**
- Modify: `backend/app/main.py` (mount MCP ASGI app at `/mcp`)
- Create: `agents/clerk/config.yaml`, `agents/clerk/tools/mcp/clerk.yaml`
- Test: `backend/tests/mcp/test_mount.py`

**Steps:**
1. Mount: in `main.py`, `fastapi_app.mount("/mcp", build_mcp_app())`. Keep it behind the same CORS/auth posture as the rest of the API.
2. Write `agents/clerk/config.yaml` modeled on `examples/scribe/config.yaml` (see README "agent-config shape"):
   - `executor: {type: omnigent, config: {harness: hermes}}`
   - `prompt:` — a construction-PM "operations lead" prompt: reasons over project documents, uses the Clerk MCP tools, explains tender comparisons, drafts PMP/cost narratives. **This prose is the product's voice — author it carefully.**
   - `os_env.cwd` → scoped to the per-project workspace (wired in Phase 6) with an appropriate Linux sandbox.
   - `guardrails.policies.blast_radius` with `gate_pushes: false` (end users can't answer approval prompts — deny-only, never ASK).
3. Declare the MCP server per Omnigent's `docs/AGENT_YAML_SPEC.md` §"MCP server": `agents/clerk/tools/mcp/clerk.yaml` with `type: mcp`, `transport: http`, `url: http://localhost:8000/mcp`, listing the tool names.
4. Test `/mcp` mounts and lists tools over HTTP.

**Acceptance:** `omnigent run agents/clerk --harness hermes` boots an agent that calls the Clerk tools; a manual "list the documents in project X" returns real rows. Commit `feat(agent): clerk hermes agent + mcp tool binding`.

---

**When all tasks pass:** mark Phase 2 ☑ in [README.md](./README.md). Proceed to [Phase 3](./03-identity-bridge.md).
