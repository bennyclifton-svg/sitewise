# SiteWise architecture and responsiveness review

Reviewed `main` at `7d13c13dd655f39f166cd0a4bb25695bebbb0d0f`, plus the
uncommitted launch fixes recorded in [launch-readiness](2026-09-13-launch-readiness.md).
Origin: `bennyclifton-svg/sitewise`. No commit, deployment, production mutation,
external correspondence or charge was made. Existing landing/terrace work and
the launch changes were preserved. Initial status/diff, check logs and this
turn's file manifest/patch are in `.tmp/architecture-review/`.

**Conclusion:** a rewrite is not justified. There are coherent authorities and
transaction boundaries, but several real coordination defects. Five bounded
improvements were implemented and tested locally. This is not production
acceptance or a claim that the application is secure. Full customer latency and
crash recovery remain launch gates.

Root, backend and frontend `AGENTS.md` were read. The referenced canonical
architecture, Pi-only runtime and TCM PRD documents are absent from this checkout;
this map follows current code. Restore those references to reduce future drift.

## Architecture map

| Flow | Authority, transaction and visible result |
|---|---|
| Chat → routing → tools | `ChatPanel.tsx` sends authenticated AI-SDK chat with selected model. `api/chat.py` routes explicit workflow commands to the durable workflow queue; ordinary chat uses Pi task/model routing. Workflow model selection is separate from the selected conversational model (see launch report). MCP project-scoped turn capabilities authorize tool calls. Tools commit their own service transactions; an entire chat turn is **not** one atomic transaction. |
| Chat saved state → UI | User message persists before execution; assistant completion and completed turn persist together. `AgentTurn` is the durable reservation/execution/quota authority. SSE carries text/status/resources; React message state and Query caches are derived. Semaphore, turn-task registry, Pi subprocess and status-bus subscribers are process-local. |
| Upload/email → intake | Both enter `inbox/service.py:store_and_queue_inbox_file` (`email/attachments.py` delegates). Storage holds original bytes; `WorkspaceFile` holds scoped path/hash/intake state. File registration and `WorkflowRun` enqueue share the caller's SQL commit, but the object upload cannot share that transaction. Same-path/hash intake deduplication already exists. |
| Intake → retrieval | Worker downloads bytes and runs hosted ingestion off the event loop. `ingest/pipeline.py` extracts/classifies/chunks/embeds. `SourceDocument` normalized text/metadata and `DocumentChunk` retrieval data persist together in a separate synchronous transaction. Project UUID/path and platform knowledge scope remain explicit. `retrieval/retriever.py` combines vector and full-text retrieval. |
| PMP create/edit/regenerate | `DraftArtifact` revisions and block provenance are authoritative. Inline and AI edits converge through `projects/artefact_adapters.py` and the locked, expected-version publisher in `artefact_revisions.py`. AI editing releases its read transaction before the model. Regeneration uses selective refresh/provenance to preserve human blocks. Stable `PMP.md` in storage is derived, not revision history. UI applies an optimistic edit, then reconciles the confirmed revision/delta. |
| Cost/appointment/invoices/export | Canonical typed `CostPlanVersion`/items and invoice/allocation/review records govern financial state; free-form cost Markdown edits are rejected. `consultant_appointment.py` reconciles appointment facts into typed cost/PMP inputs. `invoice_service.py` keeps extraction and reviewed overlays distinct; deterministic arithmetic/mapping and service publication produce cost revisions. External proposal/run keys provide idempotency. Workbook bytes and `ArtefactExport` status are derived from typed state and the invoice register. |
| Jobs/recovery | `WorkflowRun` owns frozen inputs, request hash, queue scope, attempt count, lease, progress and result. `runs.py` uses project serialization, `SKIP LOCKED`, bounded attempts and expired-lease reclaim. `worker.py` fences final publication against lease/cancellation and commits result + completion with the work transaction. Heartbeat/preview tasks are local execution machinery. File sorting has an explicit intermediate commit; object-storage writes are outside SQL rollback. |

Large workflow files contain genuine retrieval, validation and publication
boundaries; length alone is not evidence for extraction into more layers.
`assistant/` helpers are still called by PMP/cost model execution, and the legacy
retirement gate has not passed. Neither legacy path was removed.

## Implemented, with reproduced defects

1. **Financial retries preserve review.** Identical retries previously replaced
   even a posted invoice's review state with `duplicate` and erased its issues.
   Conflicting retries similarly overwrote it with `conflict`. Those now describe
   the incoming attempt: return status/message and audit event remain, while the
   original review, issues and allocations stay intact. Six cases cover identical
   and conflicting retries of posted, ready-for-review and needs-attention records.
   Existing uniqueness/authorization/financial validation was retained.
2. **PMP generation retains its starting version.** Create previously sampled the
   version after generation; update and stamp-only publication adopted the newest
   version instead of the baseline used to generate content. The shared publisher
   therefore accepted stale output over an intervening human edit. Create captures
   the starting version; updates publish against `baseline.version`. Queued PMP
   work also carries `frozen_artefact_version`, and stale queued refreshes fail
   before model execution. Tests simulate an intervening revision and assert a
   conflict with no `artefact_ready` notification; existing validation remains.
3. **Event refresh has one timer and one invalidation per key per page.** Manual
   refresh previously left the earlier timer running; an old project's late HTTP
   response could also update caches/callbacks after navigation. Both are fixed.
   Event-page resource keys are unioned before invalidation, while every fresh
   event callback is preserved. No polling interval or cache freshness allowance
   was increased. Hidden-tab pause and cursor replay tests still pass.
4. **Unchanged intake skips provider work early.** Previously extraction and
   embeddings ran before the unchanged-content check. The same scoped hash check
   now runs first, with the final persistence check retained for competing
   importers. Forced reprocessing still runs; changed bytes still run; database
   lookup failure does not start a provider call. Tests cover project/platform
   scopes, changed/unchanged bytes and forced reprocessing. This does not discard
   evidence or introduce a lower-quality model.
5. **Failed cancellation is visible and retryable.** Chat previously said
   “Cancellation requested” when the server cancellation call failed. A persistent
   warning now says cancellation could not be confirmed and provides a retry
   button, independent of the activity display disappearing after client stop.
   The test covers failure followed by a successful retry.

## Measurements and limits

Pinned local toolchain: Python 3.12.12 / uv 0.11.25 (`--frozen`), Node 22.20.0 /
pnpm 11.5.2, installed lockfile Vite 8.0.16 and TypeScript 6.0.3. No dependency,
model, document format, evidence limit or concurrency setting changed.

**Event experiment:** same original/current hook, Vitest/jsdom build, warm six-key
Query cache, 20 ms simulated query completion, ten progress events per synthetic
workflow. Ten samples per cell. These are query-function starts, **not measured
HTTP requests or transferred bytes**. All events were delivered in both versions.

| Simultaneous workflow event sources | Events/page | Before: starts, median [range] | After: starts, median [range] | Aborted query executions before → after |
|---|---:|---:|---:|---:|
| 1 | 10 | 150 [150–150] | 6 [6–6] | 144 → 0 |
| 2 | 20 | 300 [300–300] | 6 [6–6] | 294 → 0 |
| 4 | 40 | 600 [600–600] | 6 [6–6] | 594 → 0 |

The timer reproducer observed 10 polls rather than the intended 6 over its
1.1-second simulated window (initial + immediate + periodic); after: 6.
This establishes removal of redundant work, not a proportional customer speedup.
Raw samples: [events](fixtures/2026-09-13-events.json).

**Workbook experiment:** unchanged real exporter, warm Python process, fixed
100-row synthetic typed cost plan, no invoice rows, fixed generated-at input,
same formatting/validation, seven batches each at 1/2/4 concurrent thread tasks.
No model, storage or database. Timings are whole-batch completion, not per-user
tail latency. Windows development machine; this is not production capacity.

| Concurrent exports | Batch wall ms, median [range] | Process CPU ms, median [range] | Observed process peak working set |
|---|---:|---:|---:|
| 1 | 878 [861–965] | 875 [828–922] | 116 MiB |
| 2 | 1,766 [1,741–1,822] | 1,750 [1,719–1,797] | 121 MiB |
| 4 | 3,532 [3,496–3,589] | 3,531 [3,500–3,594] | 128 MiB |

Files were approximately 40.8 KB. CPU cost grows with work; increasing concurrency
is not supported by this evidence. Independent API/worker coordinator instances
both exported the same key (2 builds): the local debounce is not shared exclusion.
No exporter change was made, so there is no claimed before/after exporter speedup.
Raw samples: [workbooks](fixtures/2026-09-13-workbook.json);
[offline harness](fixtures/measure_workbook.py).

Unchanged-intake regressions observed one extraction and embedding invocation
before, zero after for an unchanged document. Changed and forced processing still
invoke both. These are deterministic call-count checks, not provider latency tests.

| Requested customer measure | Evidence available / remaining verification |
|---|---|
| First usable project view; repeat panel navigation | Bootstrap already batches draft summaries and seeds 60-second Query caches. However it can repair/upload missing PMP/procurement files before returning, then builds evidence/platform status/snapshot. Workbench prefetch calls `ensureProgramme` (a write) and procurement requests. Actual browser navigation latency is **unmeasured**. |
| Local edit feedback vs durable save | Optimistic edit happens before the commit promise; revision conflicts are tested. Durable PMP save still includes remote storage upload. `measureLocalMutation` is called after awaiting the save, so that existing telemetry does not establish paint latency. No claim of meeting 100 ms feedback or 200 ms cached-render targets. |
| Queue/retrieval/model/validation/persistence/export | Export CPU is measured above. Queue fields and workflow traces provide instrumentation seams, but no realistic DB/model run was executed. Generation targets must come from those measurements, not guessed budgets. |
| Browser long tasks, actual request counts/bytes, server load | No authenticated browser trace or application-server load test was run. Build/bundle checks pass, but bundle size is not actual transferred bytes. Query-cache diagnostics are explicitly narrower. |
| 1/2/4 complete workflows | Local event-source and export batches above only. Full application contention, database pool capacity and provider rate limits remain unmeasured. No meaningful p95 is claimed. |

Docker and PostgreSQL executables are unavailable here. There is no disposable
database-backed customer fixture configured. Using the ignored application
credentials/production project to fill these gaps would violate this review's
constraints. Before acceptance, run the selected build against disposable
Postgres/storage, one fixed synthetic evidence corpus and the same configured
model. Capture cold and warm caches separately, ten or more samples per
1/2/4-workflow case, browser PerformanceObserver/resource timing plus backend
stage timings/CPU/RSS/pool wait. Include a realistic slower customer device.
Record median/range, exact corpus/build/model and provider errors; establish
generation targets from those results. The suggested 100/200 ms interaction
targets remain candidate acceptance criteria.

## Residual reliability risks and next gates

| Risk | Evidence and required next step |
|---|---|
| Duplicate or stale derived workbook builds | `cost_plan/workbook_rebuild.py` stores debounce state only in dictionaries/tasks. A flush removes pending state before completion; another reader can see “nothing pending” while a build runs. `create_cost_plan.py:save_cost_plan_workbook_artifact` has no durable shared claim or input-fingerprint reuse. A simple “ready” flag can be stale when ledger inputs change. Add a per-revision durable claim/input fingerprint only with two-process PostgreSQL race, failure, expiry and ledger-change tests; then measure before/after. |
| Storage ahead of committed PMP | Stable `PMP.md` upload occurs before SQL commit and before final worker publish fencing. Cancellation/rollback can leave storage representing an uncommitted revision. Move stable-path promotion behind committed revision authority, with injected upload/commit failure and concurrent edit tests. Do not claim SQL rollback undoes object storage. |
| Cancellation spends work; misleading previews | Worker heartbeat detects cancellation/lease loss but ends its heartbeat loop rather than interrupting `_dispatch`; preview publishing ignores a false heartbeat result. Final publication is fenced, but model/export work can continue and previews can overwrite “cancelling”. Needs a supervised dispatch cancellation test including blocking thread work and process restart. |
| API crash/multiple API processes | Chat registry/status bus/global semaphore are local. Keep current single-Uvicorn-process topology. Hard-crash reservations need reconciliation and truthful reload state; expired reserved turns can still count toward quota. Database capability revocation alone does not terminate a remote Pi process. |
| Unsaved edit on network failure/refresh | `optimistic-mutation.ts` rolls back non-conflict errors; selection editor closes before save. Conflict edits are retained in memory, but a failed request or browser refresh can lose an unsaved edit. Add durable local pending-operation recovery, reconcile uncertain server commit by existing client operation ID, and test refresh/network interruption. Do not silently retry as a new financial operation. |
| Polling/bootstrap cost remains | Workflow detail polls at 250 ms queued / 1 s running; events at 250 ms active / 1.5 s idle; active activity 2.5 s; email/Pulse 15 s. Page coalescing fixes duplication, not this aggregate budget. Measure real navigation/server load before changing those intervals or moving bootstrap repairs. |
| Deterministic failures retried | Generic workflow failure handling applies bounded retries even to validation/version conflicts. Frozen PMP versions now protect edits, but repeated conflicts may still waste work. Classify recoverable provider/network failures separately after exercising restart behavior. |

Locally exercised failure cases include intervening edits, stale queued PMP
refresh, duplicate/conflicting invoice replay, provider errors in existing PMP
tests, failed intake lookup, late navigation responses, hidden tabs/cursor replay,
and failed cancellation followed by retry. Existing queue/quota/authorization
checks from the launch review remain relevant. Actual worker termination/restart,
real provider timeout/429, live multi-process races and refresh during an uncertain
save were **not** verified end to end. They remain explicit gates, not assurances.

## Checks and attribution

- New regressions were first run against the old implementations: 4 backend
  failures (invoice/PMP), 5 event failures, 4 intake failures, and the cancellation
  failure reproduced. The financial tests were then extended to conflicting retries.
- Final backend financial/PMP/jobs/draft-instruction selection: **197 passed,
  2 deselected**. Full intake/inbox selection: **317 passed, 1 skipped**.
  Intake/export selection: **73 passed, 1 skipped** (overlaps; do not sum counts).
- Final focused frontend selection: **101 passed**. Broad frontend run:
  **868 passed, 5 failed** before the final cancellation display fix. Four failures
  match the existing landing-controls/procurement baseline. The fifth was the new
  cancellation test and passes in the final focused run. The previously failing
  ProjectControlBoard test passed in this run; no unrelated change was made to it.
- Backend touched-file Ruff, final frontend TypeScript/ESLint, Vite production
  build and bundle budgets passed. Frontend CLI shims for Vitest/TypeScript were
  missing, so pinned installed package entry points were invoked through pnpm;
  no install/upgrade was performed. The build reused the existing coordination
  viewer instead of rerunning its unrelated prebuild generator.
- An initial broad intake run exposed missing fresh-document database mocks after
  the early check was added; it was interrupted and those fixtures were corrected.
  The final complete intake run passes. Early create-PMP fixture failures from the
  newly earlier revision read were likewise fixed and rerun. They are not reported
  as pre-existing product failures. Routine AnyIO/AsyncMock warnings remain.
- The previous launch report's full-backend 9 pre-existing failures and unavailable
  database/acceptance checks remain recorded there; a new full-backend green claim
  is not made here. No live verification was performed during this review.

Reproduce workbook measurements from `backend/` using the command in its harness.
For event measurements, copy `fixtures/measure_events.test.tsx` into
`frontend/.tmp/architecture-review/review-events.test.tsx`, save
`git show 7d13c13:frontend/src/lib/queries/project-data.ts` beside it as
`project-data.before.ts`, then run the pinned Vitest entry point on that file.
Raw check logs remain under `.tmp/architecture-review/`; the manifest identifies
only this turn's changes. Further optional restructuring stops here: targeted
coordination/recovery work with a disposable database is justified; a broad
rewrite is not.
