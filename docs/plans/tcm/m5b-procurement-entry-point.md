# M5b supplement — wiring TCM into the Procurement cockpit tile

> Read alongside `04-m5-qa-console-report.md` Part B. This resolves *where* the
> TCM frontend attaches to the existing cockpit. It does not change any Part B
> task; it constrains how Part B Task 1 ("Routes + comparisons list") hangs off
> the current UI.

## Verdict

**Yes — the Procurement lifecycle tile is the correct entry point for TCM, and
it is already the intended home.** But TCM lives at its own nested routes
(`/projects/:projectId/tender/*`, PRD §16), *not* inside the cockpit page's
view-state. The Procurement tile is the launch affordance; the `/tender` routes
are the workflow surface. These two facts are complementary, not in tension.

## Why Procurement is the right tile (verified in code)

- `ProjectControlBoard.tsx` already defines a `procurement` lifecycle tile
  (`id: "procurement"`, folder `05-procurement`, icon `BriefcaseBusiness`),
  currently a `implemented: false` / `status: "unavailable"` / "Soon" placeholder.
- `workflow/workflowRouting.ts` already maps the SiteWise slugs `rft`,
  `tender_evaluation`, and `tender_recommendation` → the `procurement` tile.
  TCM **is** the implementation of tender evaluation/recommendation, so it
  belongs to exactly this tile — no new tile, no taxonomy change.
- `CockpitPreviewPage.tsx` already describes the `05-procurement` folder as
  "Tender packages, submissions, evaluation, and TRR drafts." TCM fills it.

So "link TCM to the Procurement shell" = promote the existing placeholder tile
to a launchable state and point it at the `/tender` routes. Confirmed correct.

## How the current cockpit is built (the constraint)

- One route only: `App.tsx` has `/projects/:projectId` → `ProjectCockpitPage`.
  There is **no nested routing** under a project today.
- `ProjectCockpitPage` switches panes via `activeView` state
  (`workbench | file | draft | folder`) inside one big component (~500 lines).
  Tiles are selected via `selectedWorkflowId` state; the selected tile renders a
  `WorkflowDetail` pane inside the `workbench` view.
- The shell (`ProjectShell` = left nav + main + repo panel + chat bar) is the
  reusable frame; `ProjectLeftNav` and `DraftReviewPanel` are the house-style
  references the M5b doc already names.

## The decision (made — PRD wins)

**Add real nested routes for TCM; do not extend `activeView`.**

- PRD §16 specifies five concrete URLs (`/tender`, `/tender/:cid`,
  `/tender/:cid/qa|matrix|report`). The handoff rules say the PRD wins, and deep
  links + back/forward + shareable QA-item URLs all need real routes.
- The cockpit page is already large; folding five TCM surfaces into its
  view-state would bloat it and fight the one-way-module ethos. Keep TCM frontend
  self-contained under `frontend/src/components/project/tender/`.

**Rejected — Option B (TCM as extra `activeView` states in `ProjectCockpitPage`).**
Simpler shell reuse, but no real URLs (violates §16), and concentrates more state
in the most overloaded component. Don't do this.

## Wiring steps (fold into Part B Task 1)

1. **Promote the Procurement tile.** In `ProjectControlBoard.tsx`, give the
   `procurement` tile an "implemented/launchable" treatment: a detail pane with
   an **Open Tender Comparison** CTA (and, when comparisons exist, a short list).
   The CTA navigates to `/projects/:projectId/tender` (react-router `useNavigate`
   / `Link`). Keep status semantics consistent with the other tiles
   (`workflowStatus.ts`). The board currently receives no router context — pass a
   navigate callback down from `ProjectCockpitPage`, mirroring the existing
   `onRunCreatePmp`/`onOpenDraft` callback prop pattern (do not import the router
   inside the board if the house style keeps it presentational).
2. **Register the nested routes.** In `App.tsx`, add the §16 routes as a sibling
   group under `/projects/:projectId/tender` (own page component, e.g.
   `TenderWorkflowPage`), wrapped in the same `AuthGuard`. Reuse `ProjectShell`
   for frame parity (left nav, repo panel, chat bar) so TCM feels native; the
   main pane renders the comparisons list / overview / QA / matrix / report per
   the Part B tasks.
3. **Left-nav affordance (optional, low priority).** Once TCM is reachable, the
   Procurement section can also surface a "Tender Comparisons" link in
   `ProjectLeftNav`. Not required for the exit criteria; tile entry is enough.
4. **Data layer.** Add a `tender` API client + types following the existing
   `lib/api` + `lib/queries/project-data` idiom against the §15 endpoints M5a
   builds. No new state libraries (Part B decision 1).

## Open product choice (non-blocking — note, then proceed with default)

The `procurement` tile label is generic ("Procurement"). TCM v1 only does tender
*comparison*. **Default:** keep the tile labelled "Procurement" and let the
comparisons list be its content, so future procurement workflows (RFT drafting,
TRR) live under the same tile. Relabel to "Tender Comparison" only if Ben wants
the tile to read as TCM-specific. Either way the route stays `/tender`.

## What this does NOT change

- No backend change. M5a's `/api/tender` router (PRD §15) is unaffected.
- No change to the SiteWise lifecycle-tile model or `workflowRouting.ts` mappings.
- No new dependency beyond what Part B already contemplates (virtualisation lib).
