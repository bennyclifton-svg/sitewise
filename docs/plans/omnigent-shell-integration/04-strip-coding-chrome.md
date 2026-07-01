# Phase 4 — Strip coding-agent chrome from the shell (UI)

> Part of [Omnigent Shell Integration](./README.md) — **read the README first**.
> **Depends on:** [Phase 1](./01-vendor-omnigent.md) (the vendored `omni-web` SPA exists). UI-only — can run in parallel with Phases 2/3.
> **Resume context:** `omni-web` is Omnigent's stock chat UI, which ships coding-agent chrome (terminal tab, sub-agent tree, git-worktree file browser, shell-approval prompts) that is meaningless for a construction PM. This phase hides that chrome without gutting the underlying session/policy engine.

**Goal:** A construction PM sees chat + (Phase 5) domain panels, never terminal/sub-agent/worktree/approval UI. Decision #9. UI-layer conditional rendering only.

---

### Task 4.1: Inventory the chrome to hide

**Files:**
- Create: `docs/plans/omnigent/chrome-inventory.md`
- Reference (read): `omni-web/src/components/`, `omni-web/src/shell/`, `omni-web/src/pages/`

**Steps:**
1. Grep the vendored web for: Subagents panel, Terminal(s) tab, Files/worktree browser, policy/approval ("allow this agent to…") cards.
2. Record each component path + how it's mounted (route, tab, conditional).

**Acceptance:** Inventory lists each surface and its mount point.

---

### Task 4.2: Product-mode flag + hide coding chrome

**Files:**
- Modify: shell/layout components identified in 4.1
- Create: `omni-web/src/config/productMode.ts` (a single `PRODUCT_MODE = "clerk"` switch)
- Test: `omni-web/src/**/__tests__/…` (vitest)

**Steps:**
1. Failing test (vitest): rendering the shell in clerk mode does not render the Terminal tab / Subagents tree / worktree browser.
2. Implement conditional rendering gated on `PRODUCT_MODE`. **Keep the components in the tree** (don't delete) so the underlying session engine is untouched — just not surfaced.
3. Shell-approval prompts: since end users can't answer them, ensure the Clerk agent's guardrails (Task 2.6) never `ASK` (`gate_pushes: false` / deny-only). Add a test/assertion that the approval surface is absent in normal operation.
4. `npm run type-check` + `npm run test` → PASS. Commit `feat(shell): clerk product-mode hides coding-agent chrome`.

**Acceptance:** Chat + kept panels visible; no terminal/sub-agent/approval UI.

---

**When all tasks pass:** mark Phase 4 ☑ in [README.md](./README.md). Proceed to [Phase 5](./05-dedicated-panels.md).
