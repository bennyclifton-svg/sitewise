---
title: Practice UI Port Pipeline
date: 2026-06-07
status: active
owner: product-engineering
labels: [frontend, cockpit, practice-intelligence, sitewise, migration]
source_refs:
  - docs/plans/2026-06-07-clerk-practice-intelligence-integration-prd.md
  - docs/plans/2026-06-07-cockpit-shell-v2-frontend-plan.md
  - D:/AI Projects/CMA04/practice-intelligence/apps/clerk-workspace-dashboard/src/client/vision/DashboardVision.tsx
  - D:/AI Projects/CMA04/practice-intelligence/apps/clerk-workspace-dashboard/src/client/LeftNav.tsx
---

# Practice UI Port Pipeline

Port the workflow styling, layout, and interaction model from Practice Intelligence (`clerk-workspace-dashboard`) into Clerk's hosted React + FastAPI stack.

**Rules:** Port product shape and visual language. Do not port the Node backend, filesystem adapter, or monolithic `App.tsx`.

**Reference repo:** `D:/AI Projects/CMA04/practice-intelligence/apps/clerk-workspace-dashboard`

---

## Wave 0 — Baseline & lock reference (3 days)

- [ ] Commit current Clerk integration slice (backend + cockpit frontend)
- [ ] Run live verification per [sitewise-cockpit-verification.md](../guides/sitewise-cockpit-verification.md)
- [ ] Capture Practice screenshots (home, control board, trace, draft, repo pane)
- [ ] Capture Clerk "before" screenshots for comparison

**Gate:** Create PMP + draft review works against live backend before Wave 1 polish.

---

## Wave 1 — Visual parity layer (5 days, frontend only)

**Goal:** Clerk feels like Practice before new APIs land.

**Practice reference:** `vision.css`, `sitewise-refinements.css`, `DashboardVision.tsx` (`v-trace`, `v-btn`, spine nodes)

- [x] Add workflow status tokens (`frontend/src/components/project/workflow/workflowStatus.ts`)
- [x] Add cockpit CSS variables in `frontend/src/index.css`
- [x] Restyle `WorkflowTracePanel` to Practice trace layout (tool chips, step list, run header)
- [x] Add lifecycle spine connector row to `ProjectControlBoard`
- [x] Denser workflow tiles using shared status tokens
- [x] Collapsible left nav + document repo in `ProjectShell`
- [ ] Side-by-side screenshot check against Practice
- [x] `pnpm tsc --noEmit` passes
- [x] `pnpm lint` passes

---

## Wave 2 — Left nav & workspace explorer (5 days) ✅

**Goal:** Port Practice navigation model.

**Practice reference:** `LeftNav.tsx`, `workspaceNav.tsx`

- [x] Wire `GET /projects/{id}/workspace-tree` in cockpit loader
- [x] Explorer section with folder tree in `ProjectLeftNav`
- [x] `WorkspaceFolderPanel` for selected folder detail
- [x] Accordion nav sections (Explorer / Skills / Knowledge / Admin)
- [x] `ProjectSwitcher` component (`GET /projects`)
- [x] `PlatformKnowledgePanel` as dedicated Knowledge section
- [x] Tree node opens mapped workflow when `related_workflows` present

---

## Greenfield Create PMP (backend slice)

- [x] Load doctrine/seed via `load_platform_whole_documents` (not chunk retrieval)
- [x] Allow `platform_seeded` draft when no project evidence exists
- [x] Keep `evidence_grounded` mode when project evidence is present
- [x] Record `draft_mode` in provenance and workflow trace
- [x] Show draft mode in `DraftReviewPanel`

---

## Wave 3 — Control board v2 (7 days)

**Goal:** Port `DashboardVision` workbench and action matrix.

**Practice reference:** `DashboardVision.tsx`, `buildProjectDashboardModel.ts`, `skillsDashboardCatalogue.ts`

- [ ] Port `workflowCatalogue.ts` (spine + always-on IDs and icons)
- [ ] Port `buildWorkflowTileState.ts` (todo / running / draft / approved / locked)
- [ ] Extract `ProjectWorkflowDetail.tsx` from `ProjectControlBoard`
- [ ] Add `WorkflowActionBar.tsx` (Create, Review, Approve, Re-run, Update, Re-open)
- [ ] Stale indicator when new evidence exists after approved draft
- [ ] Optional: `GET /projects/{id}/workflows` backend contract

---

## Wave 4 — Document repository v2 (7 days)

**Goal:** Port Practice `repo-pane`.

**Backend:**

- [ ] `GET /projects/{id}/documents`
- [ ] `GET /projects/{id}/documents/{id}/preview`

**Frontend:**

- [ ] File-type badges (pdf, md, xlsx) in `DocumentRepositoryPanel`
- [ ] Path grouping by workspace folder
- [ ] Full preview in `EvidenceDetailPanel`
- [ ] `api.listDocuments`, `api.getDocumentPreview`

---

## Wave 5 — Draft governance UI (7 days)

**Goal:** Port draft lifecycle (review → approve → reopen).

**Backend:**

- [ ] `GET /projects/{id}/drafts?workflow_type=`
- [ ] `PATCH /projects/{id}/drafts/{id}` (status transitions)

**Frontend:**

- [ ] Markdown rendering in `DraftReviewPanel` (replace `<pre>`)
- [ ] `DraftVersionList` sidebar
- [ ] Enable Approve / Re-open in `WorkflowActionBar`

---

## Wave 6 — Workflow catalogue API (5 days)

**Goal:** Backend owns workflow tile state.

- [ ] `GET /projects/{id}/workflows` returns phase, version, new_evidence_count, blockers
- [ ] Control board reads server state on load (not only post-run inference)

---

## Wave 7 — Hosted document intake (see CPI-013–016)

**Goal:** Replace local `_inbox/` filesystem intake with hosted upload + Sort Files.

**Issue pack:** `docs/issues/clerk-practice-intelligence-integration/CPI-013` through `CPI-017`.

- [ ] `CPI-017` — Port Practice `documentMetadata.ts` (doc number, title, rev, category from filename + title block)
- [ ] `CPI-013` — Supabase Storage + inbox upload API + auto-ingest with register metadata
- [ ] `CPI-014` — **Far-right `DocumentRepositoryPanel` is the drag-drop upload zone** (files default to `_inbox/`)
- [ ] `CPI-016` — **Register table**: Doc No | Title | Rev | Category (Practice `DocumentRegisterSurface`)
- [ ] `CPI-015` — Document Intake / Sort Files workflow (canonical rename + register upsert)

## Wave 8 — Advanced features (optional, 10 days)

- [ ] PDF preview (`PdfPreviewSurface` port)
- [ ] Programme/cost workbook grid
- [ ] Dark mode toggle
- [ ] Overlay editor in cockpit (`PATCH /projects/{id}`)

---

## File mapping

| Practice | Clerk target |
|----------|--------------|
| `App.tsx` shell | `ProjectShell.tsx` |
| `LeftNav.tsx` | `ProjectLeftNav.tsx` + `WorkspaceExplorer` (in nav) |
| `DashboardVision.tsx` | `ProjectControlBoard.tsx` + `ProjectWorkflowDetail.tsx` (Wave 3) |
| `ClerkBar.tsx` | `ProjectChatBar.tsx` |
| `repo-pane` | `DocumentRepositoryPanel.tsx` |
| `vision.css` | `index.css` + `workflowStatus.ts` |
| `buildProjectDashboardModel.ts` | `buildWorkflowTileState.ts` (Wave 3) |

---

## Recommended track

**Track C (balanced):** Wave 1 + Wave 2 in parallel → Wave 3 → Wave 4 → Wave 5 → Wave 6.

Current focus: **Wave 1** (visual parity).
