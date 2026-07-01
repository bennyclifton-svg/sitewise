# Phase 6 — Per-project workspaces & file storage

> Part of [Omnigent Shell Integration](./README.md) — **read the README first**.
> **Depends on:** [Phase 2](./02-domain-agent-tool-bridge.md) + [Phase 3](./03-identity-bridge.md) (project authorization + identity exist).
> **Resume context:** The agent can reason and call tools, but its `sys_os_*` file tools and markdown saves aren't yet rooted in a per-project location, and uploads may land elsewhere. This phase gives each project its own directory and guarantees no project reads another's files. Decision #6 + the user's "each user saves markdown into their own directory" requirement (resolved as **per-project** directories).

**Goal:** The agent's file reads/writes/markdown-saves, uploaded documents, and the ingestion pipeline all share one per-project directory; project A can never read project B's files.

---

### Task 6.1: Define the per-project workspace root

**Files:**
- Create: `backend/app/workspaces/paths.py`, `backend/tests/workspaces/test_paths.py`

**Steps (TDD):**
1. Failing test: `workspace_root(project_id)` returns a stable, project-scoped path under a configured base (e.g. `<DATA_ROOT>/projects/<project_id>/`), and **rejects traversal** (a project id containing `..` or path separators is refused).
2. Implement with strict validation. Use the **stable project id** (the permanent id, not a mutable slug — the sitewise repo established this pattern).
3. Run → PASS. Commit.

**Acceptance:** Deterministic, traversal-safe per-project directories. Security seam #3 — do not skip the traversal check.

---

### Task 6.2: Scope the agent session's working directory to the project

**Files:**
- Modify: the session-launch path in the vendored server that sets `HARNESS_HERMES_CWD` (confirmed env var from `omni/omnigent/inner/hermes_harness.py`), or the agent's `os_env.cwd` resolution.
- Test: integration test asserting a session for project A launches with `cwd == workspace_root(A)`.

**Steps:**
1. Locate where the server spawns the Hermes runner and sets `HARNESS_HERMES_*` env (kept through Phase 1 pruning).
2. Inject `HARNESS_HERMES_CWD = workspace_root(project_id)` for the session's project.
3. On Linux, set `os_env.sandbox` to bind that cwd (bwrap) so filesystem writes are contained to the project dir (defense in depth; the Phase 3 tool-layer authorization is the primary boundary).
4. Test → PASS. Commit `feat(workspace): scope hermes session cwd to project workspace`.

**Acceptance:** The agent's file operations are physically rooted in the project's directory. Security seam #4 (sandboxed cwd on Linux).

---

### Task 6.3: Reconcile uploads/documents with the workspace

**Files:**
- Modify: `backend/tender/services/ingestion.py` / `app.storage.project_files` (wherever uploads land today) to write under `workspace_root(project_id)`.
- Test: existing ingestion tests + a new path-assertion test.

**Steps:**
1. Ensure uploaded documents for a project are stored under its workspace root, so the agent's `sys_os_*` view and the ingestion pipeline agree on one location (single source of truth for files).
2. Keep register/metadata rows in Postgres keyed by project id (unchanged).
3. Run ingestion tests → PASS. Commit.

**Acceptance:** Uploads, agent file tools, and markdown saves all share one per-project directory.

---

**When all tasks pass:** mark Phase 6 ☑ in [README.md](./README.md). Proceed to [Phase 7](./07-retire-old-engine.md).
