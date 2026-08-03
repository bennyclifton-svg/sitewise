---
target: ProjectCockpitPage
total_score: 21
max_score: 40
na_heuristics:
p0_count: 2
p1_count: 2
timestamp: 2026-08-03T10-08-27Z
slug: frontend-src-pages-projectcockpitpage-tsx
---
Method: dual-agent (A: 7256b73d-443d-4980-a3bb-5993e2dd34c5 · B: c38c7a25-9401-49c3-9674-ec52651dcf90)

Target: frontend/src/pages/ProjectCockpitPage.tsx (Operate / project cockpit)
Browser: unavailable in both agents (tab bridge failed). Vite at /cockpit-preview was reachable (HTTP 200). No [Human] overlay.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 2 | Nav computes status labels but never shows them; evidence trace hidden while runs execute |
| 2 | Match System / Real World | 3 | AU construction terms and folder doctrine land well |
| 3 | User Control and Freedom | 2 | Overlay gates funnel to one path; limited cancel/undo beyond run cancel |
| 4 | Consistency and Standards | 1 | Raw amber/sky/destructive utilities vs `--wf-*` / Drawing Office tokens in same surfaces |
| 5 | Error Prevention | 3 | Strong disable/gate patterns before risky actions |
| 6 | Recognition Rather Than Recall | 2 | Must click tiles to rediscover Ready/Blocked/Draft |
| 7 | Flexibility and Efficiency | 2 | Resizable panes help; duplicate Sort Files controls diverge |
| 8 | Aesthetic and Minimalist Design | 2 | Authored shell; cluttered stacked notices inside workflows |
| 9 | Error Recovery | 3 | Named blockers + humanized API errors |
| 10 | Help and Documentation | 1 | No first-run cockpit guidance |
| **Total** | | **21/40** | **Acceptable** |

## Design Specificity Verdict

**LLM assessment:** Authored frame, generic floor. Ribbon, mark, grain, three-pane workbench read as SiteWise Drawing Office. Workflow content (`ProjectControlBoard`, `DocumentRepositoryPanel`) is mostly stock shadcn + ad-hoc Tailwind chroma — interchangeable document SaaS. Signature motifs (eyebrows, zone titles, bracketed cards) exist in CSS but barely appear on this page (one giant signature wrapper).

**Deterministic scan:** `detect.mjs --json` on cockpit page + `components/project` → exit 0, `[]` findings. Re-run with `--no-config` also empty. Coverage caveat: React `.tsx` only hits a narrow regex rule set; page-level rules (flat type, spacing, dark-glow, buzzwords) never run without a full HTML document. Zero findings ≠ clean bill of health.

**Visual overlays:** Not available — browser tab bridge failed in both assessments. No user-visible detector overlay.

## Overall Impression

The chrome earns the brand; the workbench content undercuts it. Biggest opportunity: migrate high-traffic workflow/repo surfaces onto the existing `--wf-*` / Drawing Office language and surface status in the nav so the product feels SiteWise where people actually work.

## What's Working

1. Shell chrome (ribbon, mark, grain, resizable panes) is specific and on-brief.
2. Gate/error copy is disciplined — names blockers and usually offers a fix.
3. `WorkflowTracePanel` is the right provenance idea for construction pros; timing is the miss.

## Priority Issues

### [P0] Competing color systems for the same semantics
- **Why:** Breaks One Hot Accent / Evidence vs Inference; makes content feel generic SaaS.
- **Fix:** Replace amber/sky/destructive utilities in `DocumentRepositoryPanel` + `ProjectControlBoard` with `--wf-*` / `workflowStatus` helpers (already used in tender + trace).
- **Suggested command:** `/impeccable colorize`

### [P0] Workflow status computed but not shown in nav
- **Why:** Power users cannot scan Ready/Blocked/Draft without click-through.
- **Fix:** Render `tile.statusLabel` via existing badge helpers in `ProjectWorkflowNav`.
- **Suggested command:** `/impeccable layout`

### [P1] Overlay-gate notices duplicated three times
- **Why:** Drift risk; optional escape hatch can be omitted.
- **Fix:** One `<WorkflowOverlayGate />` bound to tile context.
- **Suggested command:** `/impeccable harden`

### [P1] Evidence trace hidden during runs
- **Why:** Peak anxiety moment for Morgan (anti-vapour AI) loses provenance proof.
- **Fix:** Progressive trace while running, not only after.
- **Suggested command:** `/impeccable clarify`

### [P2] Duplicate Sort Files entry points with divergent disable logic
- **Why:** Buttons can disagree on availability.
- **Fix:** Single enabled predicate shared by repo header and Document Intake.
- **Suggested command:** `/impeccable distill`

## Persona Red Flags

**Alex:** No nav status scan; narrowed repo panel + fixed table cols truncates.
**Jordan:** No cockpit onboarding; brand peak (ribbon) then generic forms.
**Sam:** Color-heavy status; null Suspense fallbacks; landmarks/focus unverified without live a11y pass.
**Morgan:** Trace hidden mid-run; silent AI profile auto-accept (`ProfileProposalStrip`) conflicts with Evidence vs Inference.

## Cognitive load

4/8 checklist failures (moderate–high). Primary pain: hidden status + stacked notices + unclear primary action on Create PMP (Create vs Update).

## Minor Observations

- Preview banner itself uses amber utilities.
- Loading: page uses generic pulse; brand `.cockpit-skeleton` underused.
- Recurring tiles built but not clearly surfaced in left nav — dead path or vapour roadmap.
- Chat on `/cockpit-preview` is a stand-in, not live `ChatRail`.

## Questions to Consider

1. Why do the busiest panels bypass `--wf-*` while tender/trace use them?
2. Should unbuilt recurring tiles be visible, or is that vapour?
3. Should evidence trace stream during the run?
4. Should AI identity proposals ever auto-apply without an assumed chip + confirm?
5. Was the single giant signature bracket restraint — or an unfinished motif?
