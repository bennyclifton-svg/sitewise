# Performance implementation: phase 2

Implemented locally on 9 September 2026, following phase 1. No deployment or live generation benchmark was performed.

## Changes and evidence

### Reopened evidence documents

WorkspaceFilePanel now uses TanStack Query instead of discarding fetched content on unmount. The cache is scoped by project, document ID and revision, with a 60-second freshness window. Reopening a fresh document renders its cached body immediately without another request. Stale content remains visible while refreshing; request failures remain visible as errors. Evidence and workflow resource signals invalidate the document collection, including inactive revisions. Inline content supplied by the caller retains precedence.

The regression initially failed because reopening showed a loading state. It now verifies immediate rendering, one request across reopen, and another request for a changed revision. Additional coverage verifies evidence-event refresh without a blank panel and isolation between projects.

### Workflow status requests

Imperative workflow waiters now use the same query cache and in-flight request as workflow cards. They reuse recent status responses and do not overwrite a cached terminal state with an older start response. Queued/running polling cadence and transient network-error handling remain in place.

Two concurrent waiters previously issued two requests for the same status; the regression now records one. A mounted workflow card and waiter also share cached responses. This consolidates network fetching, not all polling timers or the separate durable-project-event stream.

### Cost workbook generation

Cockpit bootstrap and workspace-tree reads no longer flush a pending workbook or synchronously regenerate a missing export. Missing workbooks are scheduled through the existing deferred rebuild coordinator, while the tree continues to advertise the canonical workbook path.

Preview and download still flush pending work. If the current workbook is missing after a restart or failed background rebuild, reading it repairs it on demand. Recovery does not substitute the current revision for a missing historical workspace path. Downloads addressed by a draft rebuild that specific draft's workbook when missing.

Tests cover navigation without a synchronous build, current-revision recovery, historical-path isolation, draft-specific recovery and existing preview/download flush behavior. Existing bootstrap and procurement checks remain green.

## Verification

- 85 frontend tests passed across WorkspaceFilePanel, DraftReviewPanel, workflow runs, project data/events, workbench and cockpit.
- 24 backend tests passed across workbook preview/rebuild, bootstrap and procurement. One additional draft-download recovery test was then added; all six preview/recovery tests passed (25 distinct backend tests across these runs).
- `pnpm typecheck`, `pnpm lint` and targeted backend Ruff checks passed.
- Production-mode Vite 8.0.16 build and bundle enforcement passed. Initial cockpit JavaScript is 246,611 gzip bytes versus 246,542 after phase 1 (+69 bytes); including static CSS, 281,203 versus 281,134. This is a request/wait reduction, not a bundle-size improvement.
- Final build log and measurements: `output/performance-review/phase2-build.log` and `phase2-after.json`.

The checkout contains unrelated ongoing changes. The bundle comparison uses the saved phase-1 working-tree build, not an isolated release comparison. Tests use controlled API/database seams; they do not measure production network, database, storage or model latency.

## Remaining work

Run the staged Seven Hills lifecycle in an isolated test project: RFPs, base cost/programme, PMP, appointments/invoices, revised evidence, then updated costs/PMP and workbook downloads. Compare the same build, corpus, model and cache conditions, collecting browser interaction timing and backend stage timing. Keep outbound correspondence as drafts.

DraftReviewPanel caching, cockpit remount/bootstrap reuse, event invalidation batching, export concurrency across workers and whole-corpus evidence-refresh profiling remain separate opportunities. No changes to those mechanisms or production infrastructure are claimed by this phase.
