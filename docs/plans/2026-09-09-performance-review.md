# Application performance review

Reviewed 9 September 2026. Local baseline: `e7a67bc9` plus the existing uncommitted working tree. This is an assessment and implementation proposal; application code has not been changed by this review.

The strongest immediate opportunities are reducing repeated background requests, making revisited panels use cached content, removing document repair/export work from project opening, and batching procurement reads. Preserve the existing Pi runtime, evidence boundaries, deterministic arithmetic, revision checks and human edits.

## Evidence and limits

Three forms of evidence are distinguished below:

- **Reproduced:** a bounded local experiment or existing test executed during this review.
- **Observed:** visible behaviour in the deployed application, without an instrumented latency measurement.
- **Code finding:** behaviour established from the local implementation; its production cost remains to be measured.

Local unit tests, a production-mode bundle build, and a read-only walkthrough of the existing deployed Seven Hills Townhouse project were performed. The live project has a PMP v5 and Cost Plan v9; it is not a clean lifecycle baseline. No project records were deliberately edited, generated, issued or deleted during the walkthrough. The full staged generation benchmark below has **not** been executed. No production database query plans, resource metrics or model-provider latency traces were collected. Browser automation elapsed time is not an application performance metric; the available read-only page evaluator did not expose Performance API entries.

The three canonical architecture/runtime/TCM documents referenced by AGENTS.md are absent from this checkout, and a filename search did not locate replacements. This assessment follows AGENTS.md and current implementation; recovering those documents should precede architectural changes.

## Findings, in implementation order

### 1. Stabilise the Pulse feed cache identity — first priority

**Reproduced mechanism.** `frontend/src/pages/ProjectCockpitPage.tsx:197` calls `pulseSinceIso("7d")` during render. `frontend/src/lib/types/pulse.ts:57` uses the current time down to milliseconds. `frontend/src/lib/queries/pulse.ts` embeds that timestamp in the query key. Consequently, subsequent renders can create new queries even while the previous response should still be fresh. A local experiment using the actual helper and installed QueryClient produced **10 query executions and 10 cache entries for 10 simulated render timestamps**, despite a five-second stale time. This demonstrates cache fragmentation, not a measured production request rate.

There is an associated freshness mismatch: durable-event invalidation in `frontend/src/lib/queries/project-data.ts` uses the default `7d` key with exact matching, whereas the cockpit uses an ISO timestamp key.

**Change:** hold a stable window boundary per selected period, advance it intentionally, and use a shared key/prefix convention for event invalidation. Verify an idle cockpit, typing, tab changes and dismissals do not create fresh cache identities; relevant events must still update the feed.

**Benefit:** less network/database work and fewer feed-driven rerenders throughout every workflow. **Effort:** small. **Risk:** low with explicit window-refresh and invalidation tests.

### 2. Make repeated navigation reuse visible content

**Code finding.** Route remounts always start `getProjectCockpitBootstrap` and reset loading state (`ProjectCockpitPage.tsx:322` onward), even if project data already exists in QueryClient. Document previews keep their body in component state and call the API again when reopened from summary evidence (`WorkspaceFilePanel.tsx:51`). Draft panels use imperative `fetchQuery` followed by state updates; once their 30-second default freshness expires, reopening can wait for a request rather than display cached content immediately.

**Change:** use reactive cached reads for document/draft detail, preserve meaningful selection and scroll position, display the last valid revision while revalidating, and invalidate affected objects on changes. Key by project, document and revision; retain all optimistic-concurrency checks. Avoid keeping every large editor mounted indefinitely.

**Benefit:** faster repeated PMP → cost → programme → procurement → document navigation. **Effort:** medium. **Risk:** medium: stale versions, cross-project leakage and unsaved edits must be covered explicitly.

### 3. Investigate deployed Procurement's long opening delay

**Observed.** On the existing Seven Hills project, Cost Plan displayed its canonical table and Program displayed its Gantt. Procurement showed “Opening procurement…” on entry, remained there at a subsequent observation after intervening local checks, and showed the same state when revisited. It eventually displayed the Procurement Strategy on a later check. No warning/error was returned by the browser console-log tool. These are observations, not p50/p95 timings or a confirmed root cause.

**Change:** capture the lazy module request, component mount and API waterfall against the deployed build SHA. Establish whether loading is blocked on code, data, or a pending render before changing implementation. Provide a useful recoverable error state for failed module/data loading. Review the route-level null Suspense fallback in `frontend/src/App.tsx` as well.

**Benefit:** resolving a long panel-opening delay matters more than shaving milliseconds off a fast interaction. **Effort:** diagnosis first; fix size unknown. **Risk:** do not attribute this observation to the local N+1 finding without a trace.

### 4. Keep project bootstrap off the export/repair path

**Code finding.** `backend/app/api/projects.py:1677` serially loads project lists, draft summaries, workspace files, evidence, platform status and a snapshot. It also invokes `_ensure_pmp_workspace_file`, `_ensure_cost_plan_workspace_file` and `_ensure_procurement_workspace_files`. Missing artefacts can cause regeneration/storage work during opening. The cost helper explicitly flushes a pending workbook rebuild before checking whether the workbook exists (`projects.py:807`). This can move work intentionally deferred after an edit back onto the next navigation request.

**Change:** render the canonical database state first; maintain derived artefact readiness through durable background work. Retain flush-on-download/preview where an up-to-date file is actually needed. Reuse already loaded project/evidence metadata within the bootstrap where safe, and evaluate splitting noncritical sections only after measuring the existing per-stage `timings_ms`.

**Benefit:** more predictable first opening, especially just after cost-plan edits or generation. **Effort:** medium/large. **Risk:** medium: recovery and export freshness must remain reliable. Do not run concurrent operations on one AsyncSession to superficially parallelise this handler.

### 5. Batch procurement list data

**Code finding.** `projects.py:3793` awaits `_procurement_request_view` for each request. That helper (`projects.py:882`) fetches the referenced full draft even though the response exposes a summary. The list therefore adds one awaited draft lookup per populated request, with unnecessary draft-body materialisation.

**Change:** batch the referenced draft IDs and select summary columns, then assemble the list. Benchmark 5, 25 and 100 requests; query count should remain bounded as the list grows. Paginate when payload measurements justify it.

**Benefit:** faster procurement opening and bootstrap-triggered prefetch with mature projects. **Effort:** small/medium. **Risk:** low; preserve project ownership checks and absent-draft handling.

### 6. Consolidate polling and coalesce refreshes

**Code finding.** The durable project-event loop polls every 250 ms when active and 1.5 seconds otherwise. Workflow observers poll queued runs every 250 ms and running runs every second. `waitForWorkflowRun` has another direct API polling loop outside QueryClient request deduplication. Pulse additionally polls every 15 seconds. Multiple consumers can therefore overlap, and one batch of events can invalidate several resources repeatedly.

**Change:** one status subscription/poll owner per workflow, coalesce invalidations within an event batch, and use visibility-aware backoff. Preserve fast completion acknowledgement and cursor catch-up. Consider event streaming only if measured polling load warrants its operational complexity; existing SSE chat does not automatically replace durable project events.

**Benefit:** less background load and smoother interactions while generation runs. **Effort:** medium. **Risk:** medium: reconnect, cancellation and missed-event recovery are essential.

### 7. Measure the full workflow payload, then tune delivery

**Measured locally, with a toolchain caveat.** The production-mode build completed in 13.79 seconds. The existing bundle measurement calculated **254,441 gzip bytes** of initial cockpit JavaScript against a **256,000-byte** budget: only 1,559 bytes of headroom. MarkdownContent alone was approximately **125 kB gzip**, and DraftReviewPanel approximately **26 kB gzip**. Initial workbench prefetch imports the draft panel after bootstrap, so the initial static-import budget does not describe the full opening workload.

The measurement script excludes CSS/fonts and measures the tender entry file without its whole transitive dependency set. It should report route/workflow deltas and post-bootstrap prefetch bytes as well as static shell size. Do not interpret the isolated style-demo chunk warning as proof that Three.js slows the cockpit: the script found no Three.js leakage into its measured shell.

Node 22.20.0 and pnpm 11.5.2 match the declared versions, but the installed build ran **Vite 7.1.9**, while package.json declares **^8.0.12**. These are indicative working-tree measurements, not a reproducible release baseline. Resolve dependency installation/lockfile drift in an isolated baseline before accepting build comparisons; this review did not replace installed dependencies.

`deploy/nginx/sitewise.conf` has no explicit gzip or immutable hashed-asset caching directives. Confirm effective container and upstream response headers before changing them; an upstream proxy may already provide compression. Add appropriate asset caching and compression if absent, retain revalidation for HTML, and preserve unbuffered SSE.

**Benefit:** faster cold and first-workflow loads. **Effort:** medium. **Risk:** low/medium: stale HTML/chunk combinations and streamed responses require checks.

### 8. Optimise generation and cost updates from stage timings

**Code finding / profiling candidates.** Cost-plan refresh loads the current ingested corpus and scans it for reconciliation (`backend/app/cost_plan/evidence_reconciliation.py:82`, `backend/app/workflows/worker.py:153`). Repeated updates can reread unchanged evidence. PMP generation/update, retrieval and chat already expose useful timing events. Retrieval already provides bounded multi-query concurrency with separate sessions and batch neighbour loading; preserve those improvements.

**Change:** first correlate queue wait, context assembly, evidence retrieval, provider time, validation/retry, persistence/export and UI visibility. Then consider revision-keyed extraction reuse, changed-document reconciliation, reuse of immutable platform guidance, and bounded overlap of genuinely independent reads. Preserve supersession, deletions, selected proposals, provenance and conflict detection. A project-wide evidence change must never be hidden by a stale cache.

Pi starts a subprocess per turn and has bounded concurrency. Measure subprocess startup separately from first model output and tool execution before considering lifecycle changes. Keep Pi as the sole runtime. Do not switch models or reduce evidence coverage as a shortcut; quality and any applicable tender evals must pass.

**Benefit:** faster repeat cost/PMP updates and clearer progress during unavoidable generation. **Effort:** medium/large, contingent on traces. **Risk:** higher because freshness and document quality are product requirements.

### 9. Profile rendering and infrastructure under realistic load

**Candidates, not proven bottlenecks.** Large markdown documents and chat streams warrant React commit/long-task measurements; `ChatPanel` has no explicit stream-update throttle. Cost Plan already has memoised derived rows and virtualisation, so adding more virtualisation by default is unjustified. Test editing and scrolling while a workflow is active, not just an idle panel.

The deployment separates API, tender worker and core workflow worker. The core worker's `process_invoices` argument validates a required capability; it does not restrict the worker to invoices. Review CPU/RSS, event-loop delay, database pool wait, worker queue age and storage latency with 1/2/4 simultaneous workflows. The database engine uses connection pooling and pre-ping; no live pool saturation or missing index has been demonstrated. Use actual query plans before adding indexes or increasing concurrency. Preserve process-local event/concurrency/workbook coordination semantics before adding API processes.

**Benefit:** sustained responsiveness as evidence and users grow. **Effort:** profiling first. **Risk:** capacity changes can worsen shared Supabase contention.

## Seven Hills lifecycle benchmark

Use `docs/demo-corpus/seven-hills/README.md` and `00-storyboard/run-sheet.md` as the staging authority. Use a new, explicitly named performance-test project for each baseline rather than overwriting the existing demonstration. Keep control prompts and answer keys out of evidence. No external emails need to be sent.

| Stage | Actions | Correctness and performance checks |
|---|---|---|
| Establishment | Create project, stage the initial brief/handover evidence without duplicate attachments | First usable cockpit, intake-to-searchable time, evidence count, request count |
| Base controls | Create cost plan and programme before the PMP, as the corpus specifies | Acknowledgement, first useful preview, complete/save/display times; deterministic totals and explicit gaps |
| Consultant procurement | Draft RFPs before ingesting the 15 proposal outcomes; browse/revise drafts; stage first four appointment letters separately | RFP generation stages, list scaling, repeated preview navigation; proposals must not imply appointment |
| PMP lifecycle | Stage planning evidence in date order; review 12→11; create v1, civil appointment update to v2, inline edit v3 | Changed-evidence retrieval, update/display latency, preserved human edit, valid citations |
| Commercial controls | Process 25 consultant invoices, refresh costs, edit rows and revisit panels | Save acknowledgement, workbook rebuild count, ledger/total correctness, navigation while work runs |
| Design and tender | Stage design baseline with S-202 Rev B; ingest three tenders and clarification, review comparison | Intake queue, extraction/QA duration, matrix responsiveness; award evidence only after the decision |
| Construction change | Stage claims 1–3, then Rev C/DCN/QS/programme change pack; review and apply updates | End-to-end change-to-visible result; source +$68,500 and 10-day input applied deterministically; human edit survives |
| Claim review | Stage unapproved VO-007 and claim 4 | Invoice review appears promptly; no implied variation approval or certification |

At each stage run PMP → Cost Plan → Program → Procurement → source preview → PMP, both first visit and repeat. Exercise editing, scrolling and navigation during background work, then project switch away/back and browser reload. Extend beyond the 140-document corpus with separately labelled synthetic scale fixtures only after the baseline is stable.

Record build SHA, corpus stage/fingerprint, model/tier, browser/device, network conditions, cache condition, request count/bytes, backend stage times and errors. Start with ten repeated navigation cycles and three generation runs per chosen stage; report sample counts and median/range. Collect a larger sample before relying on p95. Compare equivalent builds and evidence states. Use a local production build for rendering comparisons, a disposable backend/database for mutations, and deployed checks to validate the actual network/hosting experience.

Proposed engineering targets, subject to baseline calibration: cached panel content visible within 200 ms, local edit feedback within 100 ms, no loading flash for an unchanged cached document, and background work that leaves typing/scrolling responsive. Separate immediate acknowledgement from durable save and validated completion. Set generation targets after stage measurements; do not invent an across-the-board speedup percentage.

## Verification completed

- Frontend targeted tests: **82 passed across 6 files** (cockpit, procurement, draft and query-related selection).
- Frontend `pnpm typecheck` and `pnpm lint`: **passed**.
- Backend first selection: **53 passed, 1 failed**. Failure: `tests/workflows/test_pmp_minimal_brief_lifecycle.py::test_minimal_brief_scaffold_meets_phase6_contract`; scaffold is 768 words against configured minimum 800. Pre-existing in the reviewed tree; not investigated or changed here.
- Backend additional cost operations/reconciliation, workbook, invoice, Pi and retrieval selection: **53 passed**. Combined backend result: **106 passed, 1 failed**. These offline/mocked tests are correctness evidence, not provider/database latency benchmarks.
- Seven Hills validator: **passed**, 140 evidence documents, 52 current drawings, 13 reports, 25 consultant invoices, 3 builder tenders.
- Pulse cache-fragmentation experiment: **10 simulated timestamps → 10 requests/cache entries**.
- Production-mode Vite build and existing bundle calculation completed with the toolchain caveat above. Build output: `output/performance-review/build/`.
- Existing deployed project: opened PMP, Cost Plan and Program; Procurement loading issue observed and revisited. No instrumented browser latency distribution or staged live generation result is claimed.

## Proposed delivery phases

1. **Reliable baseline and immediate fixes:** pin a reproducible environment, establish lifecycle traces, stabilise Pulse keys/invalidation, investigate Procurement loading, batch procurement summaries. These have the clearest evidence and should be first.
2. **Navigation and save responsiveness:** cached detail rendering, precise event refreshes, unified workflow observation, remove derived-file work from bootstrap, verify static delivery headers and workflow byte budgets.
3. **Generation and scale:** target the slowest measured workflow stages, introduce safe incremental reuse where justified, and tune database/worker capacity from measured contention. Validate the full Seven Hills change loop after each relevant change.

The first set of application changes has been implemented locally following approval; see [phase 1 results](2026-09-09-performance-phase-1-results.md) for measurements, tests and deployment limitations. The staged benchmark remains authorised review work and should continue in an isolated test project; it is not yet complete. Each implemented phase should return before/after measurements, correctness results and any quality tradeoffs before proceeding to broader changes.

