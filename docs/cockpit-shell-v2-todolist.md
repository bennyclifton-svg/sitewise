# Cockpit Shell V2 Todolist

Use this checklist to track the frontend work that makes Clerk resemble the prior construction intelligence dashboard while staying inside Clerk's hosted React/FastAPI architecture.

Primary plan: [plans/2026-06-07-cockpit-shell-v2-frontend-plan.md](plans/2026-06-07-cockpit-shell-v2-frontend-plan.md)

## 0. Baseline

- [ ] Screenshot current `HomePage` and `ProjectCockpitPage` for before/after comparison
- [ ] Confirm existing project route loads with at least one imported project
- [ ] Confirm Create PMP works or records a clear blocked/failed trace
- [ ] Confirm `pnpm tsc --noEmit` passes before refactor work
- [ ] Confirm `pnpm lint` passes before refactor work

## 1. Cockpit Shell

- [x] Create `frontend/src/components/project/ProjectShell.tsx`
- [x] Move the project cockpit page into a stable shell layout
- [x] Preserve the existing `/projects/:projectId` route
- [x] Keep project title, workspace path, status, phase, overlays, and platform status visible
- [x] Replace the current tab-first centre layout with a workbench layout
- [x] Add responsive behavior for desktop and mobile without overlapping text
- [x] Verify the shell still handles loading, not found, forbidden, and backend error states

## 2. Left Navigation

- [x] Create `ProjectLeftNav`
- [x] Add project switcher or project identity block
- [ ] Add Explorer section
- [ ] Add Skills section
- [ ] Add Knowledge section
- [ ] Add Admin/status section
- [x] Surface overlay gate state in the left nav
- [x] Keep current Home/back navigation available

## 3. Lifecycle Control Board

- [x] Create `ProjectControlBoard`
- [x] Add lifecycle stages: Brief/PMP, Cost, Design, Procurement, Delivery, Handover
- [x] Add always-on workflows: Document Intake, Risk Register, RFIs, Variations/EOT, Payment Claims, Meeting Minutes, Reports
- [x] Show Create PMP as the active implemented Brief/PMP workflow
- [x] Show unsupported workflows as locked or coming soon
- [x] Add selected workflow detail panel
- [x] Add workflow status states: ready, blocked, running, draft ready, failed, unavailable
- [x] Wire Create PMP button to the existing `api.runCreatePmp`
- [x] Keep workflow errors visible in the selected workflow detail

## 4. Document Repository

- [x] Create `DocumentRepositoryPanel`
- [x] Move the right panel from project chat to document/evidence repository
- [x] Render evidence rows from existing `/projects/{id}/evidence`
- [x] Group or filter by document class
- [x] Show filename, relative path, source type, document class, and excerpt
- [x] Add selected evidence state
- [x] Open selected evidence in the centre workbench
- [x] Add empty state for projects with no indexed evidence
- [ ] Identify backend fields needed for a full document register

## 5. Bottom-Docked Clerk Chat

- [x] Create `ProjectChatBar`
- [x] Move project chat out of the right panel
- [x] Support collapsed and expanded states
- [x] Preserve project-only and cross-project controls
- [x] Preserve streaming message behavior
- [x] Preserve citation selection and source passage display when expanded
- [x] Refresh messages after workflow runs
- [x] Verify chat remains project-scoped by default

## 6. Draft Review

- [x] Create `DraftReviewPanel`
- [x] Replace raw `<pre>` draft display with a review layout
- [x] Show title, status, version, model, runtime, saved date, and workspace path
- [x] Show seed consulted
- [x] Show evidence refs
- [x] Show context refs
- [x] Show workflow trace linked to the draft
- [x] Add disabled accept/reopen/update controls until backend support lands
- [x] Keep Markdown content readable in a scrollable review pane

## 7. Workflow Trace And Provenance

- [x] Create reusable `WorkflowTracePanel`
- [x] Render gate, retrieval, model, validation, and draft save events
- [x] Distinguish passed, blocked, failed, running, and complete states visually
- [x] Show retrieval counts when metadata is present
- [x] Link trace to current workflow result and latest draft provenance
- [x] Keep trace visible after page refresh when available from draft metadata

## 8. API Follow-Up

- [x] Add backend contract for `POST /projects`
- [x] Add backend contract for `GET /projects/{project_id}/workspace-tree`
- [ ] Draft backend contract for `GET /projects/{project_id}/documents`
- [ ] Draft backend contract for document preview/download
- [ ] Draft backend contract for draft history
- [ ] Draft backend contract for draft status transitions
- [ ] Draft backend contract for workflow state catalogue
- [ ] Add backend implementation issues once contracts are agreed

## 9. Home Page

- [x] Make projects the primary home surface
- [x] Move conversations into secondary/recent activity treatment
- [x] Add clear "open cockpit" affordance for each project
- [ ] Show overlay gate state and latest draft state per project where available
- [x] Keep sign out and backend auth smoke actions available without dominating the page
- [x] Add offline-visible cockpit preview route for backend-unavailable states
- [x] Add create-project form wired to `POST /projects`

## 9.5 Project Template Tree

- [x] Define hosted SiteWise project template folders in the backend
- [x] Return virtual template directories from `GET /projects/{project_id}/workspace-tree`
- [x] Fetch workspace tree in the project cockpit
- [x] List template directories in the left nav Explorer
- [x] Open selected folders in the centre workspace
- [x] Show related workflow hints for selected folders
- [ ] Add document counts by folder once full document register API lands

## 10. Verification

- [x] TypeScript check (`frontend/node_modules/.bin/tsc.cmd --noEmit`; PowerShell blocked the `pnpm` shim)
- [x] `cd frontend && pnpm lint`
- [x] Backend targeted tests for project slugging and SiteWise template
- [x] Browser: open cockpit preview
- [x] Browser: inspect preview document repository
- [x] Browser: inspect preview workflow trace
- [x] Browser: click preview template folder and inspect folder summary
- [ ] Browser: sign in
- [ ] Browser: open project list
- [ ] Browser: open project cockpit
- [ ] Browser: inspect document repository
- [ ] Browser: ask project-scoped question
- [ ] Browser: run Create PMP
- [ ] Browser: inspect workflow trace
- [ ] Browser: open latest PMP draft
- [ ] Browser: verify mobile layout does not overlap controls or text

## Done Criteria

- [ ] The project page visibly resembles a construction/project intelligence cockpit
- [ ] The three-panel layout is stable and useful before chat is opened
- [ ] Create PMP is represented as one workflow in a broader lifecycle board
- [ ] Evidence/documents are always visible as project material
- [ ] Drafts are review artefacts with provenance, not raw chat output
- [ ] Chat remains available and project-scoped without replacing the workspace
