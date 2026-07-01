# Omnigent Shell Integration — Plan Index

> **For any agent/LLM picking this up:** This is a sharded implementation plan. **Read this whole README first** — it is the shared context (goal, architecture, decisions, risks, tech stack) that every phase file assumes. Then open the phase file you're working on. Each phase file is self-contained enough to execute without re-reading the others, but all of them assume this README.
>
> **REQUIRED SUB-SKILL (if you have superpowers):** Use `superpowers:executing-plans` to implement a phase task-by-task. If you don't have that skill, just execute each task's numbered steps in order, committing after each task.

## Why this is sharded

The work is split across independent files so it can be resumed cheaply by a fresh agent (any LLM, any subscription) and so context stays small — load only the phase you're on plus this README. Dependency order is linear (Phase N needs Phase N-1) with a few noted exceptions.

## How to resume with a fresh agent

1. Read this README top to bottom.
2. Check the **Phase Status** table below for the first unchecked phase.
3. Open that phase file, read its "Resume context" header, and start at its first incomplete task.
4. Verify prior phases actually landed by running their acceptance checks before building on them (don't trust the checkbox alone).

---

## Goal

Replace Clerk's bespoke chat/assistant UI and reasoning engine with a forked-in copy of Omnigent's polished chat shell driven by the **Hermes** agent, while keeping Clerk's FastAPI backend (Supabase auth, Polar billing, projects, documents) and exposing its domain logic (tender comparison, PMP, cost plan, document search) to Hermes as tools.

## Architecture

Omnigent's `web/` SPA and server are vendored (copied) into this repo and owned outright — no upstream upgrade path. Omnigent becomes the session/user/chat shell; **Hermes** (model-agnostic, its own `~/.hermes/config.yaml`) is the reasoning brain. Clerk's existing FastAPI backend stays the system of record and exposes its business logic to Hermes through an **MCP-over-HTTP** tool server. Identity flows from **Supabase** (unchanged, still the billing/ownership source of truth) into Omnigent via **header auth** — Clerk's backend validates the Supabase JWT and injects a trusted identity header. Isolation is **per-project** (the project id is the `tenant_id`), enforced at the tool layer, not just by working directory. Dedicated non-chat panels (document repository, tender comparison, cost-plan tables) survive as real UI beside the chat, the way Omnigent already renders file/terminal panels.

## Tech Stack

React 19 + Vite + Tailwind v4 + shadcn/ui + TanStack Query + Zustand + React Router 7 (shared by both codebases). FastAPI + SQLAlchemy 2 + Alembic + Supabase (Python 3.12+). Omnigent server (Python 3.12+, FastAPI). Hermes CLI (`~/.hermes/config.yaml`, provider/model swappable). MCP (`fastmcp` / `mcp` Python SDK) for the Clerk↔Hermes tool bridge.

## Repo geography (important — several look-alike dirs exist)

- `d:/AI Projects/clerk-old` — **this repo, the target.** Git remote is actually `bennyclifton-svg/sitewise.git`. Most complete backend.
- `d:/AI Projects/sitewise` — separate repo, reference only (has an early OpenDataLoader parse).
- `d:/AI Projects/clerk` — a `pdf-register-rag` scaffold (Omnigent+Hermes+OpenDataLoader design docs), reference only, not a git repo.
- Upstream Omnigent: https://github.com/omnigent-ai/omnigent (Apache-2.0). A pruned clone was inspected during planning; see phase 1 for what to vendor.

---

## Phase Status

| Phase | File | Depends on | Status |
|-------|------|-----------|--------|
| 0 | [00-preflight.md](./00-preflight.md) | — | ☐ |
| 1 | [01-vendor-omnigent.md](./01-vendor-omnigent.md) | 0 | ☐ |
| 2 | [02-domain-agent-tool-bridge.md](./02-domain-agent-tool-bridge.md) | 1 | ☐ |
| 3 | [03-identity-bridge.md](./03-identity-bridge.md) | 2 | ☐ |
| 4 | [04-strip-coding-chrome.md](./04-strip-coding-chrome.md) | 1 (UI) | ☐ |
| 5 | [05-dedicated-panels.md](./05-dedicated-panels.md) | 2, 4 | ☐ |
| 6 | [06-per-project-workspaces.md](./06-per-project-workspaces.md) | 2, 3 | ☐ |
| 7 | [07-retire-old-engine.md](./07-retire-old-engine.md) | 2–6 | ☐ |
| 8 | [08-cutover-cleanup.md](./08-cutover-cleanup.md) | 7 | ☐ |

Update the checkbox (☐ → ☑) when a phase's final acceptance passes. Phase 4 can run in parallel with 2/3 once 1 is done (it's UI-only).

---

## Decisions Ledger (resolved during grill-me, 2026-07-01)

| # | Decision | Resolution |
|---|----------|-----------|
| 1 | Target repo | `clerk-old` (this repo). `sitewise` / `clerk` scaffolds are reference-only. |
| 2 | Reasoning engine | Retire Clerk's `assistant/agent.py` + `chat/orchestrator.py`; Hermes reasons. |
| 3 | Harness | Hermes (`harness: hermes`). |
| 4 | UI shape | Not chat-only — keep dedicated panels (doc repo, tender comparison, cost plan) beside chat. |
| 5 | Auth | Supabase stays primary; bridge into Omnigent (header-injection mode recommended). |
| 6 | Isolation boundary | Per-project (project id == tenant id); team members share a project. |
| 7 | Tender Comparison Module | Rewrite. Target UX: NL trigger ("compare the 3 selected structural tenders") → Hermes reasons over selected docs → kicks off pipeline. |
| 8 | Deployment | Simplest to maintain/deploy; upstream-tracking not required. |
| 9 | Coding-agent chrome | Strip terminal/sub-agent/worktree/shell-approval UI from end-user view. |
| 10 | Vendoring | Fork Omnigent's code into this repo and own it. |
| 11 | Hermes model backing | Hermes in-repo, model-agnostic (user can swap LLM). See R1 — resolved via `openai-codex` OAuth. |
| 12 | Rollout | Big-bang: build new shell, then delete old cockpit pages. |

## Open Risks / Preflight

- **R1 — "Codex subscription" for Hermes. RESOLVED (2026-07-01).** Hermes has official support for the **`openai-codex`** provider via **OAuth on a ChatGPT subscription — no API key**. Authenticate with `hermes auth add codex-oauth` (or `hermes model` → OpenAI Codex); same device-code flow as the Codex CLI, persists to `~/.hermes/config.yaml`. Hermes stays fully model-agnostic (30+ providers incl. openrouter, anthropic, gemini, deepseek, xai — swap via `hermes model`), so decision #11's intent is honored with zero new credentials. This is Hermes' **own** `openai-codex` provider, distinct from Omnigent's `codex-native` harness (which we do **not** need for the subscription). Bonus: route Hermes **auxiliary tasks** (title generation, context compression, vision detect, session search) to a cheaper provider in `config.yaml` to preserve the ChatGPT rate limit. Watch the `openai-codex` `api_mode` (`chat_completions` vs `codex_responses`) — Hermes issue #5718. Docs: https://hermes-agent.nousresearch.com/docs/integrations/providers
- **R2 — Hermes/Omnigent on Windows.** Omnigent's native terminal harnesses need `tmux`/`bwrap` and are degraded on Windows (dev here is `win32`). The server + web UI are the supported Windows surface; full sandboxing is not. **Deploy target must be Linux (VPS/Docker)**; treat Windows as dev-only for the server, and validate Hermes end-to-end on Linux early (Phase 0). This is the only remaining unresolved preflight item — it's an environment fact, not a decision.
- **R3 — Big-bang cutover risk.** Deleting `ProjectCockpitPage`/`TenderCockpitPage` before the new shell covers current workflows risks a regression. Mitigation: keep old pages behind a feature flag / legacy route until the Phase 8 acceptance gate passes, then delete. Big-bang in intent, with a safety valve — do not skip it.
- **R4 — Tender pipeline rewrite scope.** The TCM worker (`backend/tender/`) is mid-"Stage 0.5". This plan rewrites its **entry point** (NL trigger + selected-doc reasoning) and re-exposes results as tools, but reuses existing per-stage handlers where they work. Don't rewrite handlers that already pass their tests unless a task says so.

---

## Cross-Cutting Engineering Notes (apply to every phase)

- **DRY:** Every MCP tool delegates to an existing Clerk service; no query/business logic is re-implemented in the tool layer.
- **YAGNI:** Only Hermes (+ optionally one Codex/Claude sub-agent for cross-checks) ships. Don't vendor harnesses we won't offer.
- **TDD:** Backend tools, auth gateway, isolation, and workspace paths are all test-first (they're the security-critical seams). UI ports get vitest render tests; the shell spike/cutover are manual-checklist gated.
- **Frequent commits:** Each task ends in a commit; each deletion phase commits in small, revertable steps.
- **Security seams to never skip:** (2.5) tool-layer project authorization, (3.2) header overwrite at the edge, (6.1) traversal-safe workspace paths, (6.2) sandboxed cwd on Linux. These are the whole isolation story.
- **Windows caveat:** develop backend/tools on Windows, but validate the server + Hermes + sandbox on Linux (R2). CI and deploy are Linux.
- **Run backend tests from `backend/`:** `uv run pytest ...` and `uv run ruff check ...`. End commit messages with the repo's `Co-Authored-By` trailer.

## Reference: the Omnigent agent-config shape

The Clerk agent (Phase 2) is modeled on Omnigent's `examples/scribe` and `examples/sentinel` — domain "lead" agents that author prose themselves, use `sys_os_*` filesystem+shell tools scoped to a `cwd`, delegate read-only work to sub-agents, and enforce guardrails via policies. Agent config skeleton:

```yaml
spec_version: 1
name: clerk
description: >-
  A construction project-management operations lead...
executor:
  type: omnigent
  config:
    harness: hermes
prompt: |
  You are ... (the product's voice)
os_env:
  type: caller_process
  cwd: .            # scoped per-project at launch (Phase 6)
  sandbox:
    type: none      # or platform sandbox on Linux
guardrails:
  policies:
    blast_radius:
      type: function
      function:
        path: omnigent.inner.nessie.policies.blast_radius
        arguments: { gate_pushes: false }
tools:
  # MCP server declared in tools/mcp/clerk.yaml (transport: http, url to Clerk backend /mcp)
  agents: []        # optional sub-agents
```

Tool wiring options (both confirmed in Omnigent's `docs/AGENT_YAML_SPEC.md`): **MCP server** (`tools/mcp/<name>.yaml`, `transport: http`, `url`) — the chosen path — or auto-discovered **local Python tools** (`tools/python/*.py`).
