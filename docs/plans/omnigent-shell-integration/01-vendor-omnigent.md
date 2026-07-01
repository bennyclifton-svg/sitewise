# Phase 1 — Vendor Omnigent into the repo

> Part of [Omnigent Shell Integration](./README.md) — **read the README first**.
> **Depends on:** [Phase 0](./00-preflight.md) (a Hermes+Omnigent turn proven on Linux).
> **Resume context:** Omnigent runs on the target but nothing is in this repo yet. This phase copies the pieces of Omnigent we will own — and nothing we won't — into `clerk-old`, and gets them building in isolation before wiring anything to Clerk.

**Goal:** A vendored, pruned Omnigent server + web SPA that build and run in-repo, unmodified, serving a Hermes session. This is the "Omnigent works in-repo" checkpoint before we start changing it.

---

### Task 1.1: Decide and document the in-repo layout

**Files:**
- Create: `docs/plans/omnigent/vendoring-manifest.md`

**Layout to adopt (later tasks reference these exact paths):**
```
clerk-old/
├── backend/                     # existing Clerk FastAPI (unchanged home)
├── frontend/                    # existing Clerk SPA — REPLACED as primary in Phase 5/8
├── omni/                        # NEW: vendored Omnigent server (Python)
│   ├── omnigent/                # copied from upstream omnigent/ (pruned)
│   └── pyproject.toml           # pruned deps
├── omni-web/                    # NEW: vendored Omnigent web SPA (React)
│   └── src/…                    # copied from upstream web/
├── agents/                      # NEW: our agent configs (Phase 2)
└── docs/plans/omnigent/         # decision + manifest docs
```
Rationale: keep Omnigent code physically separate from Clerk's `backend/`/`frontend/` at first (clean diff, clean revert), then integrate at the seams in later phases. `omni-web` becomes the primary SPA in Phase 8.

**Acceptance:** Manifest doc lists every top-level dir being copied and every one deliberately excluded (see 1.3).

---

### Task 1.2: Copy the Omnigent server package

**Steps:**
1. Copy upstream `omnigent/` → `omni/omnigent/`, and `pyproject.toml`, `config.yaml` → `omni/`.
2. Copy `sdks/python-client` **only if** a later task calls Omnigent from Python (the TS web client is standalone per upstream `web/README.md` reducer-parity note). Defer unless needed.
3. Do **not** copy: `tests/e2e_ui/` (Windows path-length landmines), `web/ios`, `web/electron`, `designs/`, `dev/`, `.coverage`.

> Windows note: upstream has files with very long paths under `tests/e2e_ui/visual/snapshots/`. If cloning on Windows, `git config core.longpaths true` and sparse-checkout only the dirs you need.

**Acceptance:** `omni/omnigent/` imports cleanly under Python 3.12 in a scratch venv (`python -c "import omnigent"` after `uv pip install -e omni/`).

---

### Task 1.3: Prune harnesses we will never ship

**Files:** Modify — delete unused native-harness modules under `omni/omnigent/`.

**Steps:**
1. **Keep:** `hermes_native*`, `inner/hermes_*`, the shared runner/server/spec/tools/policies machinery, and (optionally) `codex_native*` if you later want a Codex cross-check sub-agent (NOT needed for the ChatGPT subscription — Hermes' own `openai-codex` provider handles that).
2. **Delete** the harness modules for agents we won't offer end users: `antigravity_native*`, `cursor_native*`, `goose_native*`, `kimi_native*`, `kiro_native*`, `opencode_native*`, `qwen_native*`, and their `inner/*` counterparts. Also `claude_native*` unless keeping Claude Code as a sub-agent option.
3. After each deletion batch, run `python -c "import omnigent"` and fix broken imports. Some registries enumerate harnesses — `harness_aliases.py`, `native_coding_agents.py`, `runtime/harnesses/`. Prefer removing the registry entry over leaving a dangling import.

**Acceptance:** `python -c "import omnigent"` succeeds; `omnigent --help` lists only the harnesses we kept. Commit: `chore(omni): vendor + prune omnigent server`.

---

### Task 1.4: Copy and build the Omnigent web SPA in isolation

**Files:**
- Create: `omni-web/` (copied from upstream `web/`, excluding `ios/`, `electron/`, `platform-assets/` unless PWA install is wanted).

**Steps:**
1. Copy `web/src`, `web/public`, `web/index.html`, `web/package.json`, `web/vite.config.ts`, `web/tsconfig*.json`, `web/components.json`, `web/sw-src`, and the Tailwind/lint config.
2. `cd omni-web && npm install`.
3. `npm run build` — confirm it produces a bundle. Upstream `vite.config.ts` writes to `../omnigent/server/static/web-ui/`; **retarget** that output to `../omni/omnigent/server/static/web-ui/` so the vendored server serves it.
4. `npm run type-check` clean.

**Acceptance:** `omni-web` builds standalone; the bundle lands under `omni/omnigent/server/static/web-ui/`. Commit: `chore(omni-web): vendor omnigent web SPA`.

---

### Task 1.5: Run the vendored server against the vendored UI

**Steps:**
1. Copy `examples/scribe` into the repo as a smoke agent (or reference it from the upstream checkout).
2. `cd omni && uv run omnigent server --agent ../examples/scribe`.
3. Open `http://localhost:6767/`, confirm the vendored UI loads and a Hermes session runs (reuse Phase 0 provider config).

**Acceptance:** Vendored server + vendored UI + Hermes complete a turn locally. Commit any config/glue. This is the checkpoint that Omnigent works in-repo unmodified before we change it.

---

**When all tasks pass:** mark Phase 1 ☑ in [README.md](./README.md). Proceed to [Phase 2](./02-domain-agent-tool-bridge.md) (core integration) and/or [Phase 4](./04-strip-coding-chrome.md) (UI-only, can run in parallel).
