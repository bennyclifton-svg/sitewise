# Phase 5 — Keep dedicated Clerk panels beside the chat (UI)

> Part of [Omnigent Shell Integration](./README.md) — **read the README first**.
> **Depends on:** [Phase 2](./02-domain-agent-tool-bridge.md) (tools return comparison/doc data) + [Phase 4](./04-strip-coding-chrome.md) (shell chrome cleaned up).
> **Resume context:** The chat works and the tools return real data, but tender comparisons / cost plans / the document repository would otherwise only appear as markdown in a chat bubble. Decision #4 keeps them as real UI beside the chat, reusing Omnigent's existing side-panel slot mechanism.

**Goal:** Running a tender comparison from chat surfaces a real comparison **panel** (not raw markdown); the document repository is browsable beside the chat; selecting documents feeds the NL-trigger UX.

---

### Task 5.1: Identify reusable Clerk panel components

**Files:**
- Create: `docs/plans/omnigent/panels-port-list.md`
- Reference (read): `frontend/src/components/project/tender/ComparisonList.tsx`, `ComparisonOverview.tsx`, `frontend/src/components/project/ProjectControlBoard.tsx`, the document repository panel from the cockpit-shell-v2 work.

**Steps:**
1. List the Clerk components worth porting (comparison list/overview, cost-plan table, document repository/register). Note each one's data dependencies — most already call `frontend/src/lib/api.ts` against Clerk's backend (unchanged), so they can largely move as-is.

**Acceptance:** Port list with each component's API dependencies.

---

### Task 5.2: Mount a "Project" side panel in the shell

**Files:**
- Create: `omni-web/src/panels/ProjectPanel/…`
- Modify: shell layout to add the panel slot; `omni-web/src/lib/api.ts` (or copy Clerk's `api.ts`) pointed at the Clerk backend base URL.
- Test: vitest render tests per ported component.

**Steps (per component, TDD-lite):**
1. Copy the component; adjust imports; point its data hooks at Clerk's backend (through the same gateway origin so auth carries).
2. Render test: given mocked Clerk API data, the comparison overview renders rows.
3. Wire the panel to open when the Clerk agent references a comparison (e.g. the agent returns a `comparison_id` the UI deep-links to). Keep coupling loose: the panel reads Clerk APIs directly; the chat just surfaces ids/links.
4. `npm run test` + `type-check` → PASS. Commit per component.

**Acceptance:** A tender comparison from chat surfaces a real panel; document repository is browsable beside the chat.

---

### Task 5.3: Wire document selection → chat context (the NL-trigger UX)

**Files:**
- Modify: document repository panel (selection state) + chat input glue
- Test: vitest

**Steps:**
1. The document repository panel tracks a selection set (checkboxes).
2. When the user types "compare the selected tenders", the shell passes the selected document ids to the agent turn (structured context alongside the message).
3. Test: selecting 3 docs + sending a compare message includes those ids in the outgoing turn payload.
4. Commit `feat(shell): selected documents flow into the agent turn as context`.

**Acceptance:** Decision #7 works end to end — select docs → NL compare → Hermes calls `compare_tenders` with those ids → panel shows results.

---

**When all tasks pass:** mark Phase 5 ☑ in [README.md](./README.md). Proceed to [Phase 6](./06-per-project-workspaces.md) if not already done, else [Phase 7](./07-retire-old-engine.md).
