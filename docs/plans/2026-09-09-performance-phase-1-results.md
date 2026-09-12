# Performance phase 1 — local changes and verification

9 September 2026. Implements the first set of changes from [the review](2026-09-09-performance-review.md). Changes are local and have not been deployed. Existing uncommitted work has been preserved; no runtime dependencies, database schema, models or generation prompts were changed.

## Results

| Area | Before | After | Evidence |
|---|---|---|---|
| Pulse during cockpit updates | 13 API calls in the captured cost-plan-start regression | One API call and one cached feed; also holds across Cost Plan → Procurement → Project Plan navigation | Real cockpit component with mocked API, regression failed before the fix and passes after |
| Pulse event freshness | Explicit date-window queries missed exact-key invalidation | Every cached window for the affected project invalidates; other projects remain untouched | Evidence, workflow and email event tests |
| Procurement draft reads | 5/25/100 individual draft loads for lists of those sizes | One project-scoped summary query, without draft bodies/provenance | Endpoint tests exercise the real database helper, inspect its selected columns and count calls; no production SQL timing claim |
| Procurement code loading | Module requested when the panel was first opened | Module requested after bootstrap's workbench data prefetch settles | Import-boundary regression; the code is still lazy and stays outside the initial static shell |
| Browser-visible backend timings | Bootstrap stage timings only in body/logs | Bootstrap and procurement-list stages also appear in `Server-Timing` headers | Endpoint tests |

Pulse uses the server's existing rolling seven-day default. The cache key remains stable while the server advances the window at each poll; this does not freeze the time range for long-running sessions. Existing polling cadence and dismissal behaviour are retained.

Procurement list ownership is checked before reading drafts. The summary query filters by both project and referenced IDs. Missing drafts still yield a request with `current_draft: null`; requests without draft IDs perform no draft query. Individual create/get/status endpoints retain their existing behaviour.

## Procurement opening: what is and is not established

The deployed “Opening procurement…” message is the parent Suspense fallback for the lazy panel module. The panel uses ordinary `useQuery`, not a suspending data query. That observation narrows the investigation toward module loading/evaluation or work preventing the boundary from committing; it does not prove that the procurement-list database lookup caused the long delay.

The new prefetch moves code loading ahead of the expected navigation and catches speculative-load failures so they cannot fail bootstrap. It begins after opening data requests settle, avoiding extra competition at their start. Browser imports reuse loaded modules. This is a tested removal of a first-click code-loading waterfall, **not proof that the entire deployed delay is resolved**. The browser-only review did not provide a network trace or a measured latency distribution.

The three investigated possibilities remain distinguishable: delayed code request (addressed by prefetch), contention while bootstrap settles (requests are sequenced before that prefetch), and expensive render/module evaluation (still needs browser profiling). A cold-cache, direct Procurement entry should be checked alongside normal sequential use.

## Reproducible build measurements

Node is 22.20.0; pnpm is 11.5.2. The local Vite package is 8.0.16, matching the lockfile. However, bare `pnpm exec vite --version` reports 7.1.9 in this environment. This corrects the initial review's suspicion of an outdated installed package: the commands resolve different executables. No reinstall was needed for these comparisons. Both comparison builds explicitly invoked the project's installed Vite binary.

Run from `frontend/`:

```powershell
pnpm exec node ./node_modules/vite/bin/vite.js build --outDir ../output/performance-review/phase1-after
node scripts/measure-build-size.mjs --dist ../output/performance-review/phase1-after --enforce
```

The measurement script now accepts `--dist` and additionally reports complete static JS/CSS workflow dependencies beyond the cockpit shell. Existing JS-only budget semantics remain unchanged. Fonts, images and dynamically imported descendants are not included in these additional static-dependency figures. Gzip figures are sums of compressed local files, not measured network transfers.

| Measure | Before | After |
|---|---:|---:|
| Initial cockpit JavaScript, gzip bytes | 245,663 | 246,542 |
| Initial cockpit JS + CSS, gzip bytes | 280,255 | 281,134 |
| Additional Project Plan static JS/CSS, gzip bytes | 171,436 | 171,440 |
| Additional Procurement static JS/CSS, gzip bytes | 9,960 | 9,964 |
| Additional Tender static JS/CSS, gzip bytes | 149,307 | 149,352 |

Both builds pass the existing bundle budgets. This work trades a small initial-code increase for fewer repeated requests and earlier loading of approximately 10 kB of additional procurement assets. It does not claim a smaller bundle. The Project Plan's dependency footprint remains a useful candidate for phase 2.

Raw outputs: `output/performance-review/phase1-before.json`, `phase1-after.json`, `phase1-build.log`, and the corresponding build directories. The baseline is the existing working tree immediately before these application edits, not a clean release checkout.

## Verification

- Frontend selection: 128 tests passed across eight files, covering cockpit, query/event reconciliation, workbench, procurement, cost editing and draft review. The extended cockpit navigation regression also passed in its final focused rerun.
- Backend selection: 78 tests passed across request/bootstrap/Pulse/strategy/workflow/cost-operation coverage. An additional missing-draft case was then added; all nine procurement endpoint tests passed in the final focused rerun (79 distinct backend tests across these selections).
- `pnpm typecheck` and `pnpm lint` passed; targeted backend Ruff checks passed.
- Both production-mode builds and bundle enforcement passed using Vite 8.0.16.
- Seven Hills corpus validation passed again: 140 evidence documents, 52 current drawings, 13 reports, 25 consultant invoices, three builder tenders.
- The frontend mechanical detector reported no findings on the changed cockpit page. No visual styling was changed.

Tests use controlled network/database seams. They verify request counts, payload shape and correctness, not real model-provider or production database latency. The prior review's 768-versus-800-word PMP scaffold failure is outside this patch and has not been changed.

## Remaining validation and next phase

The staged Seven Hills live generation benchmark remains unexecuted. Do not overwrite the existing Seven Hills demonstration to run it. Use an isolated test project and the corpus run sheet to create RFPs, base costs/programme, PMP versions, appointments/invoices, then revised evidence and cost/PMP updates in chronological order. Keep outbound correspondence as drafts.

Use the new response headers to split bootstrap/project-list database time from browser waiting. Existing `frontend/src/lib/performance.ts` provides workflow-stage and local-mutation measures; these must be correlated with the initiating user action and backend workflow logs before treating them as full end-to-end latency. Capture code-request and render timing for Procurement, and compare identical build, corpus, model and cache conditions.

Next implementation candidates are cached document/draft rendering, consolidating overlapping workflow polls and removing workbook regeneration from navigation. They should be measured against the same lifecycle baseline. No deployment was attempted because this checkout also contains substantial unrelated work that must be handled as part of release selection.
