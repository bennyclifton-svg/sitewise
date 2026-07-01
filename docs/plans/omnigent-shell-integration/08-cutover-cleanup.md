# Phase 8 — Big-bang cutover & cleanup

> Part of [Omnigent Shell Integration](./README.md) — **read the README first**.
> **Depends on:** [Phase 7](./07-retire-old-engine.md) (old engine retired).
> **Resume context:** The new Omnigent-shelled product works and the old reasoning engine is gone, but the old frontend cockpit pages still exist behind a legacy route (R3 safety valve). This phase flips the product over to the new shell and deletes the old cockpit — only after a hard acceptance gate. Decision #12, with R3's safety valve.

**Goal:** A fresh Linux deploy serves the Omnigent-shelled product as the primary app; the old cockpit is deleted; docs let a new engineer run and extend the stack.

---

### Task 8.1: Acceptance gate before deleting old UI

**Files:**
- Create: `docs/plans/omnigent/cutover-checklist.md`

**Checklist (all must pass on the Linux target):**
- [ ] Sign in with Supabase → land in the Omnigent shell.
- [ ] Open a project → see chat + document repository + (when relevant) comparison/cost panels; no terminal/sub-agent/approval chrome.
- [ ] Upload documents → they appear in the repository and under the project workspace dir.
- [ ] "Compare the N selected tenders" → Hermes runs the pipeline → comparison panel shows results.
- [ ] Ask a document question → Hermes answers with citations via `search_project_documents`.
- [ ] Project isolation: a second user without access can't see project files (manual + Phase 3 tests).
- [ ] Billing entitlements still gate access (Polar unchanged).

**Acceptance:** Every box checked and recorded. **Do not proceed to 8.2 until this passes** (R3).

---

### Task 8.2: Delete the old frontend cockpit and flip the default route

**Files:**
- Delete: `frontend/src/pages/ProjectCockpitPage.tsx`, `TenderCockpitPage.tsx`, `CockpitPreviewPage.tsx`, and now-unused cockpit components (keep anything ported into `omni-web`).
- Modify: deployment to serve `omni-web` (via the vendored Omnigent server's `static/web-ui/`) as the primary app.

**Steps:**
1. Only after 8.1 passes. Delete in reviewable commits; keep the `pre-omnigent-integration` tag and the legacy route reachable until this task (R3).
2. Update `deploy/docker/backend.Dockerfile` and compose to build `omni-web`, run the Omnigent server + Clerk backend + Hermes, and front them with the auth gateway (Phase 3).

**Acceptance:** Fresh deploy on Linux serves the Omnigent-shelled product; old cockpit gone.

---

### Task 8.3: Documentation & runbook

**Files:**
- Modify: root `README.md`, `docs/` — how to run the integrated app, how to swap the Hermes model (`hermes model`), how auth flows, where project files live, how to add a new Clerk tool.

**Acceptance:** A new engineer can start the stack and add a tool by following the docs. Commit `docs: integrated omnigent+clerk runbook`.

---

**When all tasks pass:** mark Phase 8 ☑ in [README.md](./README.md). The integration is complete — the Omnigent shell + Hermes is the product, Clerk's backend is the layer beneath it.
