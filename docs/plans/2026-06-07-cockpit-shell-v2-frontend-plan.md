---
title: Cockpit Shell V2 Frontend Plan
date: 2026-06-07
status: proposed
owner: product-engineering
labels: [frontend, cockpit, practice-intelligence, sitewise, workflow-ui]
source_refs:
  - docs/plans/2026-06-07-clerk-practice-intelligence-integration-prd.md
  - docs/cockpit-shell-v2-todolist.md
  - D:/AI Projects/CMA04/practice-intelligence/apps/clerk-workspace-dashboard/src/client/App.tsx
  - D:/AI Projects/CMA04/practice-intelligence/apps/clerk-workspace-dashboard/src/client/vision/DashboardVision.tsx
  - D:/AI Projects/CMA04/practice-intelligence/apps/clerk-workspace-dashboard/docs/plans/2026-06-06-dashboard-ui-refactor.md
---

# Cockpit Shell V2 Frontend Plan

## Problem

Clerk now has a visible Practice Intelligence integration slice: authenticated projects, a project cockpit route, project-scoped chat, evidence previews, Create PMP, draft artefacts, and workflow trace.

The product still does not yet feel like the prior construction intelligence dashboard. The current UI reads as a chat-first app with a project detail page. The intended product is a project cockpit: a stable workspace where documents, lifecycle workflows, draft review, and Clerk chat are all visible parts of one operating surface.

## Target Outcome

By the end of this plan, opening a project in Clerk should immediately communicate:

- This is a SiteWise project workspace, not a generic chat.
- The left side is project and knowledge navigation.
- The centre is the active workbench: lifecycle stage, workflow status, trace, draft review.
- The right side is the document repository and evidence register.
- Clerk chat remains always available, but does not replace the workspace.

## Current Clerk Surface

Current implemented pieces:

- `frontend/src/pages/HomePage.tsx` lists hosted SiteWise projects and chat threads.
- `frontend/src/pages/ProjectCockpitPage.tsx` renders a three-column project page.
- `ProjectCockpitPage` can load project metadata, evidence, platform knowledge status, project chat, latest Create PMP draft, and run Create PMP.
- Backend routes already support project list/detail, evidence previews, project chat thread creation, latest draft lookup, Create PMP, and platform knowledge status.

Current gaps:

- The home page still separates projects and conversations instead of making projects the main product surface.
- The cockpit centre only has tabs for Dashboard, Evidence, and PMP Draft.
- Evidence is shown as snippets, not as a document repository.
- Draft review is a raw Markdown block, not an artefact review surface.
- Workflow capability is mostly hidden behind one Create PMP button.
- Chat occupies the right panel, leaving no permanent document repository.

## Reference Product Patterns To Port

From the Practice Intelligence dashboard, preserve the behavior and product shape, not the old runtime:

- Unified left navigation with project switcher, explorer, skills, knowledge, and admin sections.
- Centre workbench with lifecycle spine and active workflow detail.
- Always-on workflow dock for recurring project controls.
- Bottom-docked Clerk bar so chat remains present without consuming the repository panel.
- Right document repository with project files, classes, paths, and preview/open affordances.
- Workflow trace and context/evidence summary attached to the selected workflow or draft.
- Draft lifecycle actions: review, approve or accept, reopen, update, rerun.

Do not copy the Practice Node backend or local filesystem architecture into Clerk.

## Implementation Slices

### Slice 1: Cockpit Information Architecture

Goal: make Clerk visibly project-first.

- Create a `ProjectShell` component for the three-panel layout.
- Move project header, overlays, platform status, and sign-out/home actions into a stable shell.
- Replace the current centre tab strip with a workbench-oriented view.
- Keep the existing project route and API calls.

Acceptance:

- `/projects/:projectId` opens into a persistent cockpit layout.
- The first viewport shows project identity, overlay status, workflow state, document/evidence state, and Clerk access.
- No backend changes required.

### Slice 2: Lifecycle Control Board

Goal: port the prior dashboard's workflow mental model.

- Add a frontend workflow catalogue for the visible lifecycle: Brief/PMP, Cost, Design, Procurement, Delivery, Handover.
- Add an always-on catalogue: Document Intake, Risk Register, RFIs, Variations/EOT, Payment Claims, Meeting Minutes, Reports.
- Represent unavailable workflows as locked or coming soon, not absent.
- Wire Create PMP to the existing backend action.

Acceptance:

- Create PMP appears as the Brief/PMP lifecycle action.
- Other workflows are visible with accurate ready/locked/coming-soon state.
- Selecting a workflow changes the centre detail panel.

### Slice 3: Document Repository Panel

Goal: make evidence inspectable instead of hidden in chat citations.

- Move the right panel from chat to document repository.
- Group evidence by workspace path or document class using current evidence data first.
- Add compact rows with filename, class, source type, and excerpt availability.
- Open selected evidence in the centre workbench.

Acceptance:

- The right panel is always useful before running chat.
- Clicking evidence opens a centre evidence detail surface.
- The implementation can start with existing `/projects/{id}/evidence` data, then evolve when richer document APIs land.

### Slice 4: Bottom-Docked Clerk Chat

Goal: keep Clerk available without making chat the whole product.

- Convert project chat into a bottom-docked, expandable Clerk bar.
- Preserve project-only versus cross-project scope controls.
- Keep citations and source passage panel available when expanded.

Acceptance:

- Users can ask project-scoped questions from inside the cockpit.
- The document repository remains visible while chat is collapsed.
- Existing streaming chat behavior still works.

### Slice 5: Draft Review Surface

Goal: make generated workflow outputs feel like governed artefacts.

- Replace raw `<pre>` draft rendering with a draft review layout.
- Show draft title, version, status, model, runtime, workspace path, provenance, seed consulted, evidence refs, context refs, and workflow trace.
- Add disabled or planned affordances for accept/reopen/update where backend support is not yet present.

Acceptance:

- Create PMP output opens in the centre as a review artefact.
- Provenance is visible without reading raw frontmatter or JSON.
- Missing backend lifecycle actions are shown as unavailable, not implied as working.

### Slice 6: Richer Workspace APIs

Goal: support the UI with hosted Clerk contracts.

Likely backend additions:

- `GET /projects/{project_id}/documents` for a full document register.
- `GET /projects/{project_id}/documents/{document_id}/preview` for preview detail.
- `GET /projects/{project_id}/drafts` for draft history.
- `PATCH /projects/{project_id}/drafts/{draft_id}` for status transitions when accept/reopen lands.
- `GET /projects/{project_id}/workflows` for supported workflow states.

Acceptance:

- The frontend no longer has to infer repository and workflow state from preview snippets alone.
- Backend remains authoritative for workflow capability, draft status, and access control.

## Component Direction

Recommended frontend structure:

```text
frontend/src/components/project/
  ProjectShell.tsx
  ProjectLeftNav.tsx
  ProjectControlBoard.tsx
  ProjectWorkflowDetail.tsx
  DocumentRepositoryPanel.tsx
  EvidenceDetailPanel.tsx
  DraftReviewPanel.tsx
  ProjectChatBar.tsx
  OverlayGatePanel.tsx
```

Keep `ProjectCockpitPage.tsx` as the route-level loader/orchestrator until it becomes large enough to split into a page controller plus hooks.

## Design Principles

- Operational, not marketing.
- Dense enough for repeated project work.
- Stable three-panel workspace with minimal layout movement.
- Chat is a tool inside the cockpit, not the app frame.
- Show unavailable workflows honestly so the product roadmap is visible without fake functionality.
- Prefer small typed components over broad abstractions.
- Use existing shadcn/ui primitives and Tailwind; do not add frontend dependencies for layout.

## Verification

Frontend verification follows `frontend/AGENTS.md`:

- `cd frontend && pnpm tsc --noEmit`
- `cd frontend && pnpm lint`
- Manual browser check:
  - sign in
  - open home
  - open a project
  - inspect overlay gate
  - ask a project-scoped question
  - run Create PMP
  - inspect trace
  - open saved draft
  - inspect evidence/document panel

## Non-Goals

- Do not copy the Practice dashboard app wholesale.
- Do not reintroduce the Practice Node backend.
- Do not add a second frontend app.
- Do not add frontend test runners.
- Do not implement all workflows before the cockpit shell makes them visible.
- Do not imply accept/reopen/update are functional before backend routes exist.

