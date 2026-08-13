---
title: Codebase hardening and production-readiness implementation plan
status: in-progress
type: staged-implementation-plan
date: 2026-08-13
source_review: docs/plans/2026-08-13-codebase-hardening-review.md
supersedes: docs/plans/2026-08-13-Codebase-Hardending
reviewed_commit: 4480c680
active_tasks: [CH-0.3, CH-0.5]
labels: [security, reliability, performance, production-readiness, backend, frontend, ci, operations]
---

# Codebase hardening and production-readiness implementation plan

## 1. Authority, purpose, and current state

This is the durable execution artifact for hardening Clerk before meaningful
production traffic. It replaces the seven-task ordering in
[the original hardening draft](./2026-08-13-Codebase-Hardending) and turns the
findings in
[the critical review](./2026-08-13-codebase-hardening-review.md) into staged,
test-first work packets.

The repository review is complete and implementation is in progress. CH-0.0,
CH-0.2, and CH-0.4 are complete; all other tasks and GATE-0 remain open. This file is
self-contained enough to resume work in a new coding-agent session without chat
history, but it does not itself authorize a live deployment, credential change,
destructive data operation, or production test.

The plan deliberately does not prescribe a rewrite. Its architectural strategy
is to deepen a small number of important seams:

- one capability registry for MCP visibility and authorization;
- one durable queue/lease contract per worker family;
- one bounded upload interface;
- one environment/build identity;
- one release promotion path;
- one evidence ledger for production acceptance.

Those interfaces have leverage because they hide security and operational
complexity from callers. File splitting is deferred until these seams exist and
their contracts are protected.

Current verdict: **no-go for meaningful production traffic until all required
Stage 0-6 gates pass**.

## 2. Mandatory reading and non-negotiable constraints

Before starting any task, read:

1. [AGENTS.md](../../AGENTS.md)
2. [backend/AGENTS.md](../../backend/AGENTS.md) or
   [frontend/AGENTS.md](../../frontend/AGENTS.md), as applicable
3. [architecture.md](../architecture.md)
4. [Pi-only runtime plan](./2026-08-04-pi-only-agent-runtime.md)
5. [Tender Comparison PRD](./2026-06-11-tender-comparison-module-prd.md)
6. This document, including the task's dependencies and stage gate

The following constraints apply to every task:

- Pi remains the sole agent runtime. Never add Hermes or another runtime.
- Do not delete <code>backend/app/assistant/</code> or
  <code>backend/app/chat/orchestrator.py</code> before Stage 6 passes and a
  separate cutover/deletion packet is approved.
- Preserve unrelated worktree changes. Begin with <code>git status --short</code>
  and inspect the exact files the task will touch.
- App configuration comes only from <code>backend/app/config.py</code> and
  <code>frontend/src/lib/env.ts</code>.
- Do not add runtime dependencies for small helpers. Any dependency must satisfy
  the repository dependency policy and be justified in the commit message.
- Never run a broad backend test suite until CH-0.2 proves it cannot contact
  external services.
- Never point load, chaos, destructive migration, or isolation tests at
  production.
- Never print credentials, bearer tokens, signed URLs, document content, or
  customer identifiers into evidence.
- Do not increase Uvicorn worker count until CH-2.4 and CH-3.7 pass.
- Do not rewrite historical Alembic revisions. Create a new revision from the
  actual single head discovered at implementation time.
- No task may silently weaken a test, compiler flag, authorization rule, budget,
  or acceptance threshold to become green.

## 3. How an implementation session must use this file

### 3.1 Session start

1. Read the mandatory documents above.
2. Run <code>git status --short</code> and
   <code>git rev-parse --short HEAD</code>.
3. Read the ledger in Section 7. Select only a task whose dependencies are
   complete. If it defines lettered child packets, select exactly one child
   packet for the session and keep the parent task in progress.
4. Confirm no other session is editing the same files or migration head.
5. Change the selected row to <code>in-progress</code>, record owner/session and
   start time, and append the task or child-packet ID to
   <code>active_tasks</code> in the front matter. If plan-file coordination is
   unavailable, record the ownership in session commentary before editing code.
6. Execute the task's red test or baseline before implementation.

### 3.2 Task finish

1. Run targeted verification, then the task's broader verification.
2. Review <code>git diff --check</code> and the complete task-scoped diff.
3. With commit authority, create reversible **implementation commit A** at the
   task/child boundary. Do not combine the next child.
4. Create or append evidence referring to implementation commit A. Update the
   ledger with child progress/final state, commit A, owner/time, and evidence.
5. Create **coordination commit B** containing only plan/evidence updates.
   Commit B may refer to A; A cannot self-reference its own SHA.
6. Without commit authority, record a SHA-256 digest of the scoped diff in
   draft evidence, leave the task <code>in-progress</code>, and do not claim
   completion.
7. Keep the parent in progress until every required child passes. Remove only
   the completed child from <code>active_tasks</code>.
8. Do not close a stage until its explicit gate has been run against the merged
   stage state and recorded in a separate gate evidence commit.

For a task or child packet explicitly labelled **evidence/ledger coordination
only** (CH-5.5B, CH-5.9, and CH-6.1 through CH-6.3), do not create an empty
implementation commit. Keep the
release record's frozen <code>CandidateSourceSha</code>, verify every harness and
deployed-artifact digest against it, and create only the allowed sanitized
evidence/ledger <code>CoordinationSha</code> commit. Discovery of any required
source, test, script, runbook, dependency, build, or runtime-config change blocks
the task and returns to the named pre-freeze owner; it never expands the allowed
coordination diff.

### 3.3 Status and evidence convention

Allowed task states are <code>not-started</code>, <code>in-progress</code>,
<code>blocked</code>, <code>complete</code>, <code>deferred</code>, and
<code>not-applicable-approved</code>. Only a maintainer may approve the final
two.

Evidence belongs under:

    docs/acceptance/hardening/<task-id>/<YYYY-MM-DD>-<short-sha>.md

Gate evidence belongs under:

    docs/acceptance/hardening/GATE-<n>/<YYYY-MM-DD>-<short-sha>.md

An evidence record must contain:

- task ID, operator, UTC start/end, source and result SHA;
- environment and non-secret configuration;
- red/baseline result;
- exact commands and pass/fail result;
- intended test-count changes without hard-coded permanent totals;
- migrations, image digests, or deployed SHA when relevant;
- before/after performance data and raw-artifact paths when relevant;
- rollback compatibility and any residual risk;
- no secrets or customer content.

Operational raw data that is unsuitable for Git may be stored in the approved
release system; the Markdown evidence record must include its stable location
and SHA-256 digest.

### 3.4 Required task discipline

Every task below defines its objective, risk, dependencies, files/symbols, red
test or baseline, ordered implementation, verification, observability,
rollout/migration, rollback, forbidden changes, stop conditions, commit
boundary, and evidence. If the code no longer matches those instructions, stop
and update this plan through review rather than improvising.

In the same implementation commit, every task that creates or changes a
repeatable/live gate check must update CH-0.9's closed gate contract/handler and
its deliberate-failure test. A task cannot call its result release-blocking while
the owning gate has no executable handler or explicitly validated evidence-only
check for it.

The ledger's <code>Depends on</code> cell is the normative dependency/precondition
field for each task and is not repeated mechanically in every section. A local
<code>Preconditions</code> block adds to it. If a task has no schema/data steps,
its migration is explicitly “none”; its rollout/rollback paragraph still
governs deployment.

For every migration, verification means:

- identify the actual current head;
- fresh database to head;
- previous head to new head with representative rows;
- application rollback against the expanded schema;
- downgrade only on disposable data and only if the migration promises one;
- no live downgrade as a routine rollback mechanism;
- record production row count/table/index size and assess DDL lock/table rewrite;
- use bounded <code>lock_timeout</code> and <code>statement_timeout</code>;
- prefer nullable expand, resumable/batched backfill, validated constraint, then
  contract in a later compatible release;
- use concurrent index creation where PostgreSQL/Alembic transaction handling
  safely permits it;
- time the migration on representative data and record an abort threshold;
- update and run CH-1.5's explicit table/grant/RLS classification for every new
  table in the same task.

CH-1.5 is a security transition, not an additive migration. Its live execution
requires a lock/availability assessment and approved maintenance/canary plan.

### 3.5 Build compatibility specification and release record

Compatibility has two artifacts so an image never needs to contain its own
not-yet-known digest:

1. Before the one candidate build, commit the machine-readable build
   specification:

       deploy/compatibility/build-compatibility.json

   It records specification version, target Alembic head, revisions accepted by
   that build, required schema/API/tool capabilities, temporary defaults/dual
   writes, and minimum rollback-compatible capability. The image embeds this
   file and its Git blob/SHA-256 digest. Readiness reads this embedded
   specification and reports build SHA plus compatibility-spec digest; it does
   not read a mutable post-build Markdown file.
2. After the build, create the signed/checksummed release record:

       docs/acceptance/releases/<short-sha>-release.md

   It records current Git SHA, exact API/web/base image digests, embedded
   compatibility-spec digest, action/lockfile/SBOM/scan digests, CH-5.10 load/
   fault/runbook/template/gate-handler blob and contract digests, prior rollback
   SHA/digests, and the **rollback floor**. This record is never embedded back into
   or used to rebuild the candidate.

Readiness checks database compatibility against the embedded specification, not
blindly “database equals current head.” The release migration step separately
requires the exact target head, and promotion verifies the post-build release
record matches the image-reported SHA/spec digest.

A contract migration or API-field removal may occur only after:

1. the prior rollback candidate has been replaced by a newer candidate that
   understands the expanded state;
2. rollback to that newer candidate has been rehearsed;
3. a new signed release record advances the rollback floor; and
4. active compatibility-path telemetry is acceptably zero.

Never claim an old image is selectable unless its release record proves it. API
compatibility fields needed by the Stage 6 rollback candidate remain until a
separate post-acceptance cleanup release.

For performance, report p50/p95/p99, throughput, errors, CPU, RSS, database
connections/pool waits, query count, transfer bytes, and provider spend where
applicable. An optimization without a measured baseline and equivalence test is
not complete.

## 4. System invariants this plan must establish

1. **Mutation authority:** every MCP mutator is classified exactly once and
   requires a specific scope at the server seam; Pi sees only tools authorized
   for that turn.
2. **Tenant isolation:** anonymous, user A, and user B cannot cross tenant
   boundaries in Postgres or Storage, regardless of browser/API path.
3. **Environment isolation:** jobs, credentials, data stores, builds, and logs
   identify and stay within development, test, staging, or production.
4. **Durable work:** claims use renewable leases and fencing; stale workers
   cannot publish; completion and continuation are atomic or reconciled.
5. **Bounded resources:** request bytes, file count, PDF pages, work
   concurrency, queue age, database connections, external waits, retries, and
   spend have enforced ceilings.
6. **Release integrity:** only a green, immutable, tested image digest is
   promoted; production reports its SHA; the prior compatible image remains
   selectable.
7. **Observable recovery:** operators can correlate a request/job/turn, detect
   unhealthy workers and queues, and execute tested restore and rollback
   procedures without exposing customer data.
8. **Measured scale:** client polling, pagination, chat, evidence, queries, and
   assets have data-independent or explicitly bounded cost.

## 5. Traceability to the critical review

| Review finding | Required tasks |
|---|---|
| CH-P0-01 credential exposure and unsafe offline tests | CH-0.1, CH-0.2, CH-0.3 |
| CH-P0-02 MCP mutation scopes largely unenforced | CH-1.1, CH-1.2, CH-1.3 |
| CH-P0-03 DB and Storage isolation unproven | CH-1.4, CH-1.5, CH-5.4 |
| CH-P0-04 private frontend cache crosses identity | CH-1.6 |
| CH-P0-05 Tender scope, lease, continuation durability | CH-2.1, CH-2.2, CH-2.3 |
| CH-P0-06 unbounded upload/PDF/download paths | CH-3.4 |
| CH-P0-07 deployment not gated and validator cannot fail | CH-1.7, CH-1.8, CH-5.5 |
| CH-P0-08 backup, restore, retention, acceptance open | CH-1.10, CH-2.6, CH-5.10, CH-6.2, CH-6.3 |
| CH-P1-01 polling scales with history and clients | CH-4.1 |
| CH-P1-02 discarded pagination and unbounded evidence | CH-4.2, CH-4.3, CH-4.4 |
| CH-P1-03 O(history) chat submission/rendering | CH-4.5 |
| CH-P1-04 implicit DB pools/transactions/readiness | CH-3.1, CH-3.5 |
| CH-P1-05 process-local agent coordination | CH-2.4, CH-3.7 |
| CH-P1-06 Stripe duplicate/order behavior | CH-2.5 |
| CH-P1-07 non-durable Storage cleanup | CH-2.6 |
| CH-P1-08 false-green frontend CI | CH-0.4, CH-0.5, CH-0.6 |
| CH-P1-09 delivery differs from bundle accounting | CH-4.6 |
| CH-P1-10 weak production observability | CH-3.2, CH-3.3 |
| CH-P1-11 thin browser/accessibility acceptance | CH-1.9, CH-5.6 |
| CH-P1-12 speculative query/index risk | CH-4.7 |

Disposition of the original seven tasks:

| Original task | Decision |
|---|---|
| Derive profile fields and add a guard | retained and strengthened as CH-5.1 |
| Expand Ruff | retained as staged CH-5.2 |
| Add pytest-xdist globally | replaced by measured opt-in CH-5.3 |
| Consolidate workflow helpers | rejected as a shallow-loader exercise; extract only when a deep interface has real callers |
| Split project routes | conditional CH-5.7 after contracts |
| Split MCP server | conditional CH-5.8 after capability enforcement |

## 6. Approved starting defaults and decision gates

These are conservative starting proposals, not hidden product decisions. A
maintainer may change them before the owning task begins, but must record the
decision here and in task evidence.

| Decision | Starting proposal | Must be confirmed by |
|---|---|---|
| Deployment environments | separate writable non-production Supabase project; no routine local production credentials | CH-0.1 |
| File limits | 50 MiB/file, 100 MiB/request, 20 files/request | CH-3.4 |
| PDF limit | 500 pages before rendering/splitting | CH-3.4 |
| Signed download TTL | 60 seconds; private/no-store/no-referrer | CH-3.4 |
| Staging object TTL | 24 hours | CH-2.6 |
| Tender lease | 120 seconds; heartbeat every 40 seconds | CH-2.2 |
| Tender stage deadline | 30 minutes pending measured stage durations | CH-2.2 |
| Event polling | 1 second active, 15 seconds idle, 30-second max backoff | CH-4.1 |
| Browser page size | 50 for chat/Tender; 100 maximum for evidence | CH-4.2/CH-4.3 |
| Agent admission | one active turn/thread; initial two active turns/user; fast 409/429, no wait inside SSE | CH-2.4 |
| Tender admission | one process/comparison; initial two active comparisons/user | CH-3.7 |
| DB connection budget | provider ceiling first; initial total per deployment is API 7, Tender 5, workflow 3, cleanup 1, parser 1 = 17 maximum | CH-3.1 |
| Restore objective | RPO at most 15 minutes; RTO at most 4 hours | CH-1.10 |
| Soak | at least 24 hours on the release-candidate SHA | CH-6.3 |

Unresolved decisions that block their owning tasks:

- live Supabase exposed schemas, role grants, RLS and Storage policies;
- provider DB connection ceiling and current peak;
- Dokploy's approved immutable-image promotion mechanism;
- alert/error/metrics destinations and named operator;
- legal retention and litigation-hold rules;
- whether host port 8080 bypasses the intended edge;
- approved upload limits if the starting proposal does not fit real tenders;
- business availability/SLO and monthly/provider spend ceilings.

## 7. Execution ledger and stage gates

Stages are strict gates. A later required stage does not start while an earlier
stage is red. Tasks within a stage may run in parallel only when their file,
migration, and operational scopes do not overlap.

Only <code>Required=yes</code> tasks block their stage. Optional work starts
<code>not-started</code>; “proposed: defer” is a recommendation, not maintainer
approval. The Owner/session/start column is filled whenever state is
<code>in-progress</code>.

| ID | Task | Required | State | Depends on | Owner/session/start | Result/evidence |
|---|---|---:|---|---|---|---|
| CH-0.0 | Disable independent production auto-deploy | yes | complete | - | Codex /root / 2026-08-13T21:30:29Z | Probe `24f85b71`; `docs/acceptance/hardening/CH-0.0/2026-08-14-24f85b71.md` |
| CH-0.1 | Rotate credentials and isolate environments/scopes | yes | not-started | CH-0.0 | - | - |
| CH-0.2 | Default-deny offline test network and secrets | yes | complete | CH-0.0 | Codex /root / 2026-08-13T21:42:19Z | `f2584bd0`, `0824b99f`; `docs/acceptance/hardening/CH-0.2/2026-08-14-f2584bd0.md` |
| CH-0.3 | Redact secrets from all logs/errors | yes | in-progress | CH-0.2 | Codex /root / 2026-08-13T22:40:29Z | red tests pending |
| CH-0.4 | Pin one frontend toolchain | yes | complete | CH-0.0 | Codex /root / 2026-08-13T22:40:29Z | `14dc5aaa`, `e954b0c7`; `docs/acceptance/hardening/CH-0.4/2026-08-14-e954b0c7.md` |
| CH-0.5 | Make TypeScript checking real and strict | yes | in-progress | CH-0.4 | Codex /root/frontend_audit / 2026-08-13T23:06:32Z | red baseline pending |
| CH-0.6 | Restore deterministic frontend lint/tests | yes | not-started | CH-0.5 | - | A/B pending |
| CH-0.7 | Capture baseline/dependency/secret evidence | yes | not-started | CH-0.2, CH-0.6 | - | - |
| CH-0.8 | Bootstrap disposable Postgres/pgvector runner | yes | not-started | CH-0.2 | - | - |
| CH-0.9 | Add fail-capable merged-state gate runner | yes | not-started | CH-0.2, CH-0.7, CH-0.8 | - | - |
| GATE-0 | Trustworthy baseline | yes | not-started | CH-0.0, CH-0.1, CH-0.2, CH-0.3, CH-0.4, CH-0.5, CH-0.6, CH-0.7, CH-0.8, CH-0.9 | - | - |
| CH-1.1 | Create MCP capability registry/contract | yes | not-started | GATE-0 | - | - |
| CH-1.2 | Fail closed at every MCP mutation seam | yes | not-started | CH-1.1 | - | - |
| CH-1.3 | Reserve scopes/restrict Pi tool visibility | yes | not-started | CH-1.2 | - | - |
| CH-1.4 | Audit live DB grants/RLS/Storage safely | yes | not-started | GATE-0 | - | A/B pending |
| CH-1.10 | Prove backup/restore and approve retention | yes | not-started | CH-1.4, CH-0.8 | - | - |
| CH-1.13 | Add locked migration runner/compatibility spec | yes | not-started | CH-0.8, CH-1.10 | - | A/B pending |
| CH-1.5 | Enforce/test tenant security contract | yes | not-started | CH-1.4, CH-1.10, CH-1.13 | - | A/B pending |
| CH-1.6 | Clear private frontend cache on identity change | yes | not-started | GATE-0 | - | - |
| CH-1.9 | Add visible loading/error recovery | yes | not-started | GATE-0 | - | - |
| CH-1.11 | Give each service only required secrets | yes | not-started | GATE-0 | - | - |
| CH-1.12 | Harden host/Dokploy administration perimeter | yes | not-started | GATE-0 | - | - |
| CH-1.7 | Build, prove, and stage immutable release path | yes | not-started | CH-0.7, CH-1.11, CH-1.13 | - | A/B/C pending |
| CH-1.8 | Replace Hermes with fail-capable Pi core validator | yes | not-started | CH-1.1, CH-1.3, CH-1.7 | - | - |
| GATE-1 | Security, tenancy, release control | yes | not-started | CH-1.1, CH-1.2, CH-1.3, CH-1.4, CH-1.5, CH-1.6, CH-1.7, CH-1.8, CH-1.9, CH-1.10, CH-1.11, CH-1.12, CH-1.13 | - | - |
| CH-2.1 | Scope Tender jobs by environment | yes | not-started | GATE-1 | - | A/B/C pending |
| CH-2.2 | Add Tender renewable leases/fencing | yes | not-started | CH-2.1 | - | A/B/C pending |
| CH-2.3 | Make Tender completion/continuation atomic | yes | not-started | CH-2.2 | - | A/B pending |
| CH-2.4 | Make agent admission/reaping/cancel durable | yes | not-started | GATE-1 | - | A/B/C pending |
| CH-2.5 | Make Stripe state idempotent/monotonic | yes | not-started | GATE-1 | - | A/B/C pending |
| CH-2.6 | Add durable Storage cleanup/retention queue | yes | not-started | CH-1.10, CH-2.1 | - | A/B/C/D pending |
| CH-2.7 | Prove one core-workflow lock order | yes | not-started | CH-2.4, CH-0.8 | - | - |
| GATE-2 | Durable state transitions | yes | not-started | GATE-1, CH-2.1, CH-2.2, CH-2.3, CH-2.4, CH-2.5, CH-2.6, CH-2.7 | - | - |
| CH-3.0 | Approve observability destinations/ownership | yes | not-started | GATE-2 | - | - |
| CH-3.1 | Budget DB pools/timeouts/readiness | yes | not-started | GATE-2 | - | A/B pending |
| CH-3.2 | Add worker heartbeat/queue health/alerts | yes | not-started | CH-3.0, CH-3.1 | - | A/B pending |
| CH-3.3 | Add structured correlation/metrics/host-DB monitoring | yes | not-started | CH-0.3, CH-3.0, CH-3.1 | - | A/B/C/D/E pending |
| CH-3.4 | Bound uploads/PDFs/downloads/staging work | yes | not-started | CH-2.6, CH-3.1, CH-3.2 | - | A/B/C pending |
| CH-3.5 | Remove DB sessions from external waits | yes | not-started | CH-2.3, CH-3.1, CH-3.4 | - | A/B/C/D/E/F/G pending |
| CH-3.6 | Reuse external clients with deadlines/retries | yes | not-started | CH-3.3 | - | A/B/C/D/E pending |
| CH-3.7 | Enforce overload/active-work admission | yes | not-started | CH-2.4, CH-3.4 | - | A/B pending |
| CH-3.8 | Bound host disk/log/workspace/memory growth | yes | not-started | CH-3.0, CH-3.3 | - | A/B pending |
| CH-3.9 | Account for and enforce provider spend budgets | yes | not-started | CH-3.0, CH-3.3, CH-3.6 | - | A/B pending |
| CH-3.10 | Implement graceful drain/shutdown | yes | not-started | CH-2.2, CH-2.4, CH-2.6, CH-3.2, CH-3.4, CH-3.6 | - | A/B pending |
| GATE-3 | Bounded resources and operability | yes | not-started | GATE-2, CH-3.0, CH-3.1, CH-3.2, CH-3.3, CH-3.4, CH-3.5, CH-3.6, CH-3.7, CH-3.8, CH-3.9, CH-3.10 | - | - |
| CH-4.0 | Add production-browser performance harness | yes | not-started | GATE-3, CH-1.7, CH-1.9 | - | - |
| CH-4.1 | Make project-event reconciliation bounded | yes | not-started | GATE-3 | - | A/B pending |
| CH-4.2 | Consume chat/Tender cursor pagination | yes | not-started | GATE-3 | - | A/B pending |
| CH-4.3 | Add bounded versioned evidence API/search | yes | not-started | GATE-3 | - | A/B/C pending |
| CH-4.4 | Make evidence UI partial-page aware | yes | not-started | CH-4.0, CH-4.3, CH-4.7 | - | A/B pending |
| CH-4.5 | Make chat send/render/recovery bounded | yes | not-started | CH-4.0, CH-1.9 | - | A/B/C pending |
| CH-4.6 | Enforce real Nginx transfer/cache budgets | yes | not-started | GATE-3, CH-1.7, CH-4.0 | - | A/B pending |
| CH-4.7 | Batch measured N+1 paths/justify indexes | yes | not-started | GATE-3, CH-4.3 | - | A/B/C/D pending |
| GATE-4 | Measured data/traffic scale | yes | not-started | GATE-3, CH-4.0, CH-4.1, CH-4.2, CH-4.3, CH-4.4, CH-4.5, CH-4.6, CH-4.7 | - | - |
| CH-5.1 | Add profile lifecycle drift guard | no | not-started | GATE-4 | - | proposed: defer |
| CH-5.2 | Roll out high-signal Ruff rules | no | not-started | GATE-0 | - | proposed: defer |
| CH-5.3 | Benchmark opt-in xdist lane | no | not-started | GATE-0 | - | proposed: defer |
| CH-5.4 | Enrol all DB/security/concurrency contracts in CI | yes | not-started | GATE-4, CH-0.8 | - | - |
| CH-5.6 | Fix deterministic browser/a11y acceptance | yes | not-started | GATE-4, CH-4.0 | - | A/B pending |
| CH-5.10 | Build pre-freeze load/fault/acceptance harnesses | yes | not-started | GATE-4, CH-5.4 | - | A/B/C pending |
| CH-5.5 | Freeze/revalidate release-candidate supply chain | yes | not-started | CH-1.7, CH-5.4, CH-5.6, CH-5.10 | - | A/B pending |
| CH-5.9 | Run frozen-image browser/auth/SSE acceptance | yes | not-started | CH-5.5, CH-5.6 | - | A/B pending |
| CH-5.7 | Optionally split project routes | no | not-started | GATE-5 | - | proposed: defer |
| CH-5.8 | Optionally split MCP domains | no | not-started | CH-1.3, GATE-5 | - | proposed: defer |
| GATE-5 | Automated release-candidate guardrails | yes | not-started | GATE-4, CH-5.4, CH-5.5, CH-5.6, CH-5.9, CH-5.10 | - | - |
| CH-6.1 | Run reproducible staging load/soak gate | yes | not-started | GATE-5 | - | - |
| CH-6.2 | Rehearse failure/restore/immutable rollback | yes | not-started | CH-6.1 | - | A/B/C pending |
| CH-6.3 | Execute and sign production go/no-go | yes | not-started | CH-6.2 | - | - |
| GATE-6 | Signed production acceptance | yes | not-started | GATE-5, CH-6.1, CH-6.2, CH-6.3 | - | - |

### 7.1 Named child-packet index

Each letter is one bounded session. Normally it produces one implementation
commit followed by its evidence coordination commit. For tasks explicitly marked
evidence/ledger coordination only, the letter executes the frozen artifact and
produces only its evidence coordination commit; it must not create an empty or
source-changing implementation commit. The parent cannot become complete until
all listed letters pass.

| Parent | Ordered child packets |
|---|---|
| CH-0.6 | A lint/React correctness; B deterministic flaky-test/full-suite proof |
| CH-1.4 | A read-only live catalogue; B explicitly authorized synthetic active probes/cleanup |
| CH-1.5 | A DB contract/migration; B Storage policy/deployed isolation |
| CH-1.7 | A immutable staging/release contract after CH-0.0 containment; B exact hardened container build/smoke; C protected production promotion configured plus staging rollback |
| CH-1.13 | A held-connection migration runner; B embedded compatibility-spec/release wiring |
| CH-2.1 | A expand/backfill; B scoped producers/consumers; C retire temporary default after rollback-floor advance |
| CH-2.2 | A lease schema/DTO; B claim/heartbeat; C fenced worker/sweeper |
| CH-2.3 | A pipeline generation/dedup schema and all producers; B atomic fenced completion/continuation |
| CH-2.4 | A scope/index/durable admission; B local registry/revocation watcher; C staged rollback-floor advance and default removal |
| CH-2.5 | A ledger/order schema; B webhook transaction/concurrency; C checkout idempotency |
| CH-2.6 | A queue/worker; B upload/staging immutable-generation compensation; C transactional deletion/overwrite conversion; D approved retention/reconciliation |
| CH-3.1 | A pool/timeout budgets; B compatibility-aware readiness and Pi-validator check |
| CH-3.2 | A heartbeat schema/writers; B healthcheck/queue alerts/real delivery |
| CH-3.3 | A log/context schema; B application correlation/metrics; C host/container monitoring; D DB/pooler monitoring; E dashboards/alerts/runbooks |
| CH-3.4 | A bounded HTTP/Storage/download boundary; B parser benchmark/queue worker; C API 202/frontend contract |
| CH-3.5 | A DTO/instrumentation/matrix; B Tender classification/extraction; C all remaining Tender handlers; D core workflows; E billing/API file/export seams; F MCP provider/Storage seams; G parser/cleanup |
| CH-3.6 | A lifecycle/deadline foundation; B Tender adapters; C API auth/Supabase/Storage; D retrieval/title/web/embedding; E core workflow providers |
| CH-3.7 | A durable/backend admission; B trusted-edge rate policy |
| CH-3.8 | A workspace quota/reconciler; B host/container log/disk/memory policy |
| CH-3.9 | A price/usage ledger; B budgets/alerts/provider reconciliation |
| CH-3.10 | A worker drain/leases; B API/Pi drain/client closure/compose grace |
| CH-4.1 | A backend high-water contract; B frontend single-owner scheduler |
| CH-4.2 | A chat infinite page; B Tender infinite page |
| CH-4.3 | A versioned page/cursor endpoint; B batch resolution/query plans; C monitored legacy compatibility endpoint |
| CH-4.4 | A query/selection state; B folder/transmittal/event consumers |
| CH-4.5 | A constant transport contracts; B row/render profiling; C runtime-specific recovery |
| CH-4.6 | A honest measurement; B Nginx/security/delivery contract |
| CH-4.7 | A split provenance; B repair/sort; C project pagination; D justified indexes |
| CH-5.5 | A pre-build supply-chain/spec remediation and one candidate build; B post-build release record/freeze proof |
| CH-5.6 | A deterministic browser specs; B accessibility fixes |
| CH-5.9 | A frozen-image deterministic rerun; B real staging auth/SSE |
| CH-5.10 | A deterministic load harness; B default-deny fault/reconciliation harness; C Pi-only production-acceptance runbooks/templates |
| CH-6.2 | A target/dry-run attestation; B isolated runtime/dependency failures; C immutable rollback/isolated restore |

### 7.2 Gate closure protocol and command matrix

Every gate is a separate merged-state execution, not a summary of task claims.
It uses two identities:

- <code>CoordinationSha</code>: clean HEAD containing completed ledger rows,
  evidence references, release record, and the candidate implementation; and
- <code>CandidateSourceSha</code>: the tested implementation/build source commit
  recorded by the preceding coordination commits and deployed artifacts.

The gate owner checks out clean <code>CoordinationSha</code> and runs exactly:

    pwsh -NoProfile -File scripts/hardening/run-gate.ps1 `
      -Gate <GATE-N> `
      -CoordinationSha <40-character-coordination-sha> `
      -CandidateSourceSha <40-character-source-sha> `
      -Environment <test|staging|production> `
      -EvidenceOut docs/acceptance/hardening/<GATE-N>/<date>-<short-sha>.json

For staging/production checks, append <code>-AllowLiveChecks</code> only after the
runner displays and matches every reviewed target allowlist field. The adjacent
Markdown record links the JSON/raw digests and contains executor, independent
maintainer approver, and operator signature when live infrastructure is involved.

The fixed handler matrix is mandatory. Task implementations may add narrower
checks, but cannot delete or downgrade these without maintainer review:

| Gate | Environment | Required fixed handler groups | Freshness/signers |
|---|---|---|---|
| GATE-0 | test/offline | <code>repo-clean-sha</code>, <code>backend-offline</code>, <code>frontend-typecheck-lint-test-build</code>, <code>offline-network-redaction-canaries</code>, <code>dependency-secret-baseline</code>, <code>disposable-db-smoke</code>, <code>production-autodeploy-off</code> | All repeatable results from this run/source SHA; auto-deploy proof no older than 24h; executor + maintainer/operator |
| GATE-1 | staging plus authorized live read/probes | <code>mcp-capability-auth-visibility</code>, <code>db-storage-two-owner-isolation</code>, <code>frontend-auth-cache</code>, <code>migration-runner-concurrency</code>, <code>pi-core-validator</code>, <code>service-secret-matrix</code>, <code>host-admin-perimeter</code>, <code>immutable-staging-promote-rollback</code>, <code>restore-retention</code> | Same code/spec SHA; live/perimeter/promotion proof <=24h; isolated restore <=7d and after current target schema; executor + maintainer + operator |
| GATE-2 | test/disposable DB and staging | <code>queue-scope-isolation</code>, <code>tender-lease-fence-continuation</code>, <code>agent-scope-admission-reap-cancel</code>, <code>stripe-order-checkout</code>, <code>storage-cleanup-races</code>, <code>core-lock-order</code>, <code>temporary-defaults-absent</code> | Repeatable tests from source SHA; staging cross-process proof <=24h; executor + maintainer |
| GATE-3 | production-container staging | <code>pool-readiness</code>, <code>worker-health-alert-delivery</code>, <code>upload-parser-download-bounds</code>, <code>no-db-external-wait-matrix</code>, <code>external-deadline-retry</code>, <code>admission-rate-limits</code>, <code>disk-workspace-capacity</code>, <code>spend-reservations</code>, <code>graceful-forced-shutdown</code>, <code>app-host-db-observability</code> | Exact staged digests/source SHA; alert and capacity proof <=24h; executor + maintainer + operator |
| GATE-4 | built production web/API plus disposable DB | <code>event-high-water-scheduler</code>, <code>all-cursor-contracts</code>, <code>evidence-workspace-project-pages</code>, <code>chat-transport-render-recovery</code>, <code>nginx-transfer-sse-mcp</code>, <code>query-budget-plans</code>, <code>browser-performance</code>, <code>legacy-route-rollback-load</code> | Repeatable results from source SHA/digests; query plans use representative current fixture; executor + maintainer |
| GATE-5 | frozen candidate staging | <code>database-contract-ci</code>, <code>pre-freeze-load-fault-acceptance-harnesses</code>, <code>supply-chain-sbom-scans</code>, <code>release-record-no-rebuild</code>, <code>frozen-browser-deterministic</code>, <code>frozen-real-auth-sse</code>, <code>prior-spa-compatibility</code> | Exact frozen SHA/API/web/spec/harness digests; CI and four browser runs from that candidate; executor + maintainer + operator |
| GATE-6 | allowlisted staging and protected production | <code>statistical-load-soak</code>, <code>chaos-reconciliation</code>, <code>isolated-restore-rpo-rto</code>, <code>production-migration-security</code>, <code>protected-promote-rollback</code>, <code>two-owner-product-journey</code>, <code>stripe-mode-spend</code>, <code>synthetic-cleanup</code>, <code>signed-go-no-go</code> | Exact candidate record; backup age within RPO at promotion; alerts/headroom <=1h; 24h soak immediately precedes unchanged candidate; executor + independent maintainer + operator |

Each handler records the exact underlying commands/script versions in JSON. A
repeatable handler reruns its tests against the source SHA; an evidence-only live
handler verifies artifact digest, target identity, result, age, and signer and
fails if any is missing. A gate passes only when every required dependency is
complete and every handler says <code>pass</code>. Advisory checks are separately
labelled and cannot substitute for a required handler.

Failure leaves the gate <code>not-started</code> or <code>blocked</code>, records
the first failing handler plus all <code>not-run</code> handlers, and prohibits the
next stage. The runner executes from coordination SHA B while testing the code,
tree, and artifacts from candidate source SHA A. It verifies every path changed
between A and B is under an approved plan/evidence/release-record directory and
that a deterministic digest of all other tracked paths still equals A. B records
both SHAs and that tree digest. Any later change
to application code, migrations, tests, dependency locks, Docker/Nginx/compose,
compatibility specification, gate runner, or material environment configuration
reopens the affected gate and every downstream gate. A pure sanitized evidence/
ledger coordination commit does not invalidate the tested source SHA. A secret,
customer content, wrong target, or digest mismatch invalidates the run entirely.

### GATE-0 - trustworthy baseline

- credential/environment/queue scopes are explicit and isolated;
- offline tests cannot load real secrets or open external sockets;
- log redaction canaries pass;
- frontend typecheck/lint/test/build are genuinely green;
- dependency/secret baseline identifies the exact SHA;
- disposable Postgres/pgvector runner is safe and repeatable.

### GATE-1 - security, tenancy, and release control

- every mutator rejects empty/wrong scope and Pi gets least privilege;
- live anonymous/A/B/service DB and Storage isolation passes;
- user B never renders A cache;
- migration-runner concurrent-lock proof passes;
- independent production auto-deploy is disabled;
- exact hardened images are built/smoked and immutable staging promotion reports
  the expected SHA; production promotion is protected/configured but not run;
- role-specific secret mapping and host/admin perimeter tests pass;
- core Pi validator exits nonzero on required failure;
- restore and retention evidence is signed.

### GATE-2 - durable state transitions

- each queue family is scope-isolated;
- long/killed/reclaimed/stale Tender workers cannot double-publish;
- explicit continuation deduplication identity and concurrent predecessor tests
  produce one downstream generation;
- agent admission/reaping/cancellation works across processes before side effects;
- every agent-turn authority query is execution-scoped and the temporary
  production <code>execution_scope</code> default is absent/fail-closed;
- duplicate/reversed Stripe and checkout retry tests pass;
- cleanup compensation race preserves canonical objects and dead letters have an
  operator;
- core workflow lock-order test has no deadlock.

### GATE-3 - bounded resources and operability

- 413/415/429 happens before expensive work and signed download behavior passes;
- RSS/CPU/connections/pool wait/queue/retries/disk/inodes/workspace/provider
  spend meet approved budgets;
- no DB session crosses instrumented external waits;
- liveness, compatibility-aware readiness, worker health, external
  deadline/retry budgets, and full Pi validator pass;
- structured logs and application/host/DB/TLS/backup/pooler alerts reach named
  operators;
- graceful deploy and forced-kill recovery are distinct and proven;
- no API worker scaling occurs without durable cross-process tests.

### GATE-4 - measured data and traffic scale

- polling model meets thresholds without history replay;
- page two/off-page selections work;
- new versioned evidence path meets 10,000-document payload/DOM/query targets;
- legacy evidence endpoint is monitored/rate-bounded and retained only for the
  declared rollback floor;
- chat request is constant and runtime-specific recovery is deterministic;
- Nginx gzip/cache/SSE/bundle contracts match deployed behavior;
- query/index changes have plans, equivalence, and before/after measurements.

### GATE-5 - automated release-candidate guardrails

- every completed migration/security/lease/lock contract runs in required CI;
- load/fault/reconciliation drivers and Pi-only production runbooks/templates
  were committed and self-tested before candidate build, and their exact digests
  are in the release record;
- current CI actions and container bases are pinned/reviewed; image/base/action
  advisories have dispositions;
- exact tested digest is exported to release and hardened-container checks pass;
- production-container browser/auth/SSE/accessibility gates pass;
- optional profile/Ruff/xdist/file-split tasks do not block launch unless a
  maintainer explicitly changes <code>Required</code> to yes.

### GATE-6 - deployed acceptance

- candidate SHA completes statistically valid load and 24-hour soak;
- graceful and forced worker/DB/Storage/provider/Pi exercises reconcile;
- fresh isolated restore and prior-image rollback meet RPO/RTO;
- post-all-migration DB/RLS/grant/Storage audit passes;
- rollback floor and canary/maintenance traffic-shift plan are explicit;
- synthetic production fixtures are cleaned/reconciled and no unapproved live
  Stripe charge occurs;
- full two-owner product journey passes and named operator/approver sign
  <code>ready-to-open</code> while ingress remains closed; and
- only this gate's passing signed record authorizes the named operator to perform
  and separately record the controlled public-traffic-open action. A failed or
  incomplete gate leaves public traffic closed.

## 8. Stage 0 - containment and trustworthy verification

### CH-0.0 - Disable independent production auto-deploy

**Objective and risk.** Stop a push or intermediate hardening commit from
reaching production independently of required CI. This is the first action in
the entire plan; no implementation commit from CH-0.1 onward may be pushed or
merged while the current production auto-deploy path remains enabled.

**Files/systems.** Dokploy production application settings, Git provider webhook
or branch integration, <code>.github/workflows/ci.yml</code>, deployment
runbook, and sanitized operator evidence. Do not change application code.

**Red baseline.** With operator read-only inspection, record whether a push to
<code>main</code> can invoke Dokploy without waiting for required CI and whether
any second webhook/manual path can deploy. Record safe application/branch/event
names and enabled/disabled state, never tokens or webhook URLs.

**Implementation.** An authorized operator disables production Git push/branch
auto-deploy and every equivalent unprotected webhook. Leave the currently
running production digest untouched. Until CH-1.7C, the only allowed production
selection is an explicitly approved emergency/manual action by the named
operator; routine pushes do nothing. Keep staging deployable for later proof,
but clearly distinguish its application ID. Document how to verify and, only for
emergency rollback, re-enable access without restoring automatic push deploys.

**Verification.** Trigger or use a harmless documentation-only test push/branch
event approved by the operator and prove production records no deployment/build.
Inspect all Dokploy/Git deployment triggers a second time. Capture current
production SHA/digest before and after; it is identical. A manual dry-run may
show an approval prompt but must not deploy.

**Observability.** Record UTC time, operator, safe application ID hash, trigger
types, before/after enabled state, and unchanged production SHA/digest.

**Migration/rollback.** No schema or application deployment. Re-enabling
independent auto-deploy is not an acceptable rollback. Emergency manual
selection follows the existing controlled operator runbook until CH-1.7 exists.

**Do not.** Do not stop the running service, rotate unrelated credentials,
delete Dokploy applications, expose webhook URLs, or assume editing CI disables
an external deploy trigger.

**Stop if.** Operator access/ownership is unavailable, the production target is
ambiguous, or any trigger cannot be disabled without service interruption. Mark
the entire plan blocked before pushing implementation work.

**Commit/evidence.** One documentation/coordination commit after the external
setting is proven. Evidence links sanitized before/after screenshots or API
records and the unchanged production digest.

### CH-0.1 - Rotate credentials and isolate environments

**Objective and risk.** Remove any credential exposed through the audit/test
trace and make development, test, staging, and production identities explicit.
This addresses CH-P0-01 and prevents later tests from mutating production.

**Preconditions.** Maintainer/operator participation is required. Do not place
secrets in chat, Git, shell history, or evidence.

**Files and discovery.**

- <code>backend/app/config.py::Settings</code>
- <code>backend/tests/test_config.py</code>
- <code>deploy/dokploy.compose.yml</code>
- <code>deploy/env/*.env.example</code>
- <code>.github/workflows/ci.yml</code>
- <code>DEPLOYMENT.md</code>
- Discover reads with
  <code>rg -n "os.getenv|load_dotenv|DATABASE_URL|SUPABASE_URL|BUILD_SHA|queue_scope" backend deploy .github</code>.

**Red baseline.** Record a redacted matrix of environment, Supabase project
reference, DB host/database, Storage bucket, queue scopes, Dokploy application,
credential owner, and last rotation. Use hashes or last four characters only.
Confirm whether local configuration can reach production and whether
<code>BUILD_SHA</code> or deployment environment may be empty.

**Implementation.**

1. Rotate every possibly exposed credential through its provider. Credential
   rotation is an operator action and must be confirmed, not simulated.
2. Provision or confirm a separate writable non-production Supabase project.
   Remove production credentials from routine local/CI configuration.
3. Add
   <code>deployment_environment: Literal["development","test","staging","production"]</code>
   sourced from <code>DEPLOYMENT_ENVIRONMENT</code>.
4. In production, require nonempty <code>BUILD_SHA</code>, HTTPS public URL,
   non-localhost origins, and explicit, distinct
   <code>AGENT_EXECUTION_SCOPE</code>, <code>WORKFLOW_QUEUE_SCOPE</code>,
   <code>TENDER_QUEUE_SCOPE</code>,
   <code>STORAGE_CLEANUP_QUEUE_SCOPE</code>, and
   <code>PARSER_QUEUE_SCOPE</code>. Do not retain production as a silent scope
   default or reuse one queue family's scope for another.
5. Set environment/SHA explicitly for every compose service and expose them in
   health/log context without exposing credentials.
6. Document the approved, intentional production-administration path.

**Verification.** Unit tests must reject production with an empty SHA,
localhost URL, or missing explicit scope and accept safe test/development
defaults. Start each service with non-secret fixture config and confirm the same
environment/SHA. Search tracked and CI files for the production project
reference; only approved redacted documentation may match.

**Observability, migration, and rollout.** No DB schema migration. Emit environment
and build SHA at process start. Rotate credentials before code rollout, validate
each dependent service, then revoke the previous values.

**Rollback.** Never restore an exposed credential. Configuration validation may
be rolled back only while external isolation remains intact.

**Do not.** Do not log a settings object, store a secret in the evidence matrix,
or use production as a substitute for missing test infrastructure.

**Stop if.** A separate non-production project cannot be provided, any secret
appears in evidence, or ownership of an exposed credential is unknown.

**Commit/evidence.** One code/documentation commit after operator rotation.
Evidence must include the redacted matrix, rotation confirmation, test output,
and service environment/SHA.

### CH-0.2 - Default-deny offline test network and secrets

**Objective and risk.** Make ordinary <code>uv run pytest</code> incapable of
loading real credentials or opening Python external sockets unless a
specifically marked test is explicitly opted in. This is the application-level
prerequisite for trusting later backend verification; CH-0.8 and the
network-disabled CI/container lane provide the narrower database and OS-level
process-tree proofs.

**Files and discovery.**

- <code>backend/tests/conftest.py</code>
- new <code>backend/tests/offline_network.py</code>
- new <code>backend/tests/test_offline_containment.py</code>
- <code>backend/pyproject.toml</code> markers
- <code>.github/workflows/ci.yml</code>
- <code>backend/.env.example</code>
- Inspect import order with
  <code>rg -n "^from app|^import app|settings" backend/tests/conftest.py</code>.

**Red tests.**

1. Imported settings use unmistakable test sentinels, not <code>.env</code>.
2. An unmocked HTTP request to loopback raises
   <code>OfflineNetworkBlocked</code>, not a connection error.
3. An <code>integration</code> or <code>tender_eval</code> test remains blocked
   unless <code>CLERK_TEST_ALLOW_NETWORK=1</code>.
4. Test-launched subprocesses inherit sentinel values.
5. Capture <code>uv run pytest --collect-only -q</code>; record current counts,
   not the audit's historical totals.

**Implementation.**

1. Before any app import in <code>tests/conftest.py</code>, overwrite every
   required DB, Supabase, OpenAI, Stripe, Pi, search, token, runtime, and billing
   setting with safe sentinel values. Do not merely unset variables because
   settings may reload <code>.env</code>.
2. Install the socket guard before test-module collection. Cover DNS resolution,
   connection helpers, <code>socket.connect</code>, <code>connect_ex</code>, and
   UDP send entry points.
3. Grant a context-local, per-test generation lease only when the test has an
   approved external marker and the process-start opt-in variable equals one.
   Invalidate the generation at teardown so stale tasks/threads cannot reuse a
   later test's authority; fail closed on same-process parallel protocols.
4. Convert offline HTTP behavior tests to <code>httpx.MockTransport</code> or
   equivalent injected fakes; never globally permit loopback.
5. Keep CI's unreachable DB URL and explicit sentinels as defense in depth.
   Apply them at workflow scope so every Python lane that transitively imports
   runtime settings, including Tender seed validation, remains hermetic.

Generic network opt-in must keep <code>TEST_DATABASE_URL</code> unreachable and
<code>ALLOW_DESTRUCTIVE_TEST_DATABASE=0</code>. CH-0.8 alone may add a database
exception after its separate marker, parsed private-host allowlist, and database
environment marker exist. This Python guard does not claim to intercept plugins
loaded before root conftest, C-library networking, or arbitrary child processes
that discard their environment; the later network-disabled runner owns that
process-tree proof.

**Verification.**

    Set-Location backend
    uv run pytest tests/test_offline_containment.py -q
    uv run pytest -m "not integration and not tender_eval" -q

Expected: containment tests pass; there is no external network attempt; the
offline suite retains its captured pass/skip set except explained additions.

**Observability/migration/rollback.** Test-only; no migration or runtime log.
Rollback is a single revert, but doing so reopens the Stage 0 gate.

**Do not.** Do not patch only <code>httpx</code>, permit localhost globally, or
weaken the guard because a mislabeled test fails.

**Stop if.** More than five offline tests genuinely require sockets. Inventory
and reclassify them rather than broadening the escape hatch.

**Commit/evidence.** One commit for sentinels, guard, marker docs, and converted
tests. Evidence records collection counts and both commands.

### CH-0.3 - Redact secrets from all logs and client errors

**Objective and risk.** Credentials, bearer tokens, cookies, signed URLs,
database passwords, and configured secret literals never reach structlog,
stdlib logs, formatted exceptions, or API error bodies.

**Files and discovery.**

- <code>backend/app/logging.py::configure_logging</code>
- new <code>backend/app/log_redaction.py</code>
- new <code>backend/tests/test_logging_redaction.py</code>
- review <code>app/main.py</code>, <code>app/inbox/service.py</code>,
  <code>app/storage/project_files.py</code>, <code>tender/worker.py</code>
- Discover risky calls with
  <code>rg -n "logger\\.|log\\.|exc_info|headers|settings|str\\(exc\\)" backend/app backend/tender</code>.

**Red tests.** Send distinct canaries through sensitive top-level keys, nested
dict/list values, exception text, URL userinfo, query tokens, a configured
secret literal, and a stdlib logger. Assert no canary appears while request ID,
path, error class, and safe metadata remain.

**Implementation.**

1. Add one recursive redaction processor for sensitive key names, URL userinfo,
   signed-token query parameters, and configured secret literals of at least
   eight characters.
2. Format exception information before redaction.
3. Wire the same processor into structlog and
   <code>ProcessorFormatter.foreign_pre_chain</code>.
4. Replace customer-facing raw Storage/provider errors with stable generic
   messages while preserving redacted diagnostic class/context in logs.
5. Remove logging of whole headers, settings, Stripe events, MCP tokens, DSNs,
   signed URLs, prompts, and documents.

**Verification.**

    Set-Location backend
    uv run pytest tests/test_logging_redaction.py tests/test_storage_resilience.py -q
    uv run pytest -m "not integration and not tender_eval" -q

Expected: every canary is absent and safe correlation data remains.

**Observability.** Redaction must apply before both console and future JSON
renderers. Count redaction processor failures without echoing the value.

**Migration/rollout.** No schema change. Deploy the shared processor and generic
client errors atomically across API and workers, then verify canaries in each
service before accepting traffic.

**Rollback.** If structure becomes unusable, revert processor wiring but retain
generic client errors; Stage 0 becomes red.

**Do not.** Do not redact all user text indiscriminately or maintain multiple
inconsistent redaction lists.

**Stop if.** Ordinary safe fields are broadly removed or any known secret cannot
be represented as a redaction canary.

**Commit/evidence.** One commit. Evidence includes only synthetic canaries and
sanitized rendered examples.

### CH-0.4 - Pin one frontend toolchain

**Objective and risk.** Make local, CI, and Docker dependency resolution
identical. Current pnpm versions float/differ and both npm and pnpm lockfiles
exist.

**Files.** <code>frontend/package.json</code>,
<code>frontend/pnpm-lock.yaml</code>,
<code>frontend/package-lock.json</code>, <code>frontend/.npmrc</code>,
<code>frontend/.node-version</code>, <code>frontend/pnpm-workspace.yaml</code>,
<code>frontend/AGENTS.md</code>,
<code>.github/workflows/ci.yml</code>, and
<code>deploy/docker/frontend.Dockerfile</code>.

**Red baseline.** Record local Node/pnpm, CI setup, and Docker setup. The audit
observed pnpm 11.5.2 locally while CI requested floating major 10. Confirm again.

**Implementation.**

1. Maintainer selects an exact pnpm version. Prefer the confirmed working local
   version; never use only a major.
2. Pin one exact Node 22 release in <code>.node-version</code>, add exact
   <code>packageManager</code> and matching narrow Node engine constraints to
   <code>package.json</code>.
3. Make local guidance, CI, and Docker consume those exact versions and print
   Node/pnpm once.
4. Confirm <code>minimum-release-age</code> support.
5. Remove <code>frontend/package-lock.json</code>; pnpm remains the only package
   manager.
6. Run a frozen install and ensure pinning alone does not rewrite dependency
   resolutions.

**Verification.**

    Set-Location frontend
    pnpm --version
    pnpm install --frozen-lockfile
    git diff --exit-code -- pnpm-lock.yaml
    pnpm test
    pnpm lint
    pnpm build

Local, CI, and Docker must report identical Node and pnpm versions. Existing
lint, strict-TypeScript, and order-sensitive-test findings are recorded as
non-regression baselines here; CH-0.5 and CH-0.6 must clear them before GATE-0.

**Observability/migration/rollback.** No runtime migration. Revert package
metadata, CI, Docker, and lockfile removal together.

**Do not.** Do not update application packages in this task or generate an npm
lock.

**Stop if.** The selected pnpm cannot interpret <code>.npmrc</code>, frozen
install rewrites resolutions, or any environment is not Node 22.

**Commit/evidence.** One atomic toolchain commit and version/frozen-install
evidence.

### CH-0.5 - Make TypeScript checking real and strict

**Objective and risk.** Replace the root
<code>tsc --noEmit</code> no-op with a check that traverses both referenced
projects and enforces the repository's stated strict contract.

**Files/symbols.** <code>frontend/tsconfig.json</code>,
<code>tsconfig.app.json</code>, <code>tsconfig.node.json</code>,
<code>package.json</code>, <code>frontend/AGENTS.md</code>,
<code>.github/workflows/ci.yml</code>, and currently unused symbols in
<code>ProjectCockpitPage.tsx</code> and its test.

**Red baseline.**

- Show that <code>pnpm exec tsc --noEmit</code> checks no referenced source.
- Run <code>pnpm exec tsc -p tsconfig.app.json --noEmit --strict</code>.
  The audit found only three unused-symbol diagnostics; record the current set.

**Implementation.**

1. Set strict mode in app and Node configs.
2. Add <code>"typecheck": "tsc -b --pretty false"</code>.
3. Update CI and <code>frontend/AGENTS.md</code> to use
   <code>pnpm typecheck</code>.
4. Remove real unused symbols; do not suppress or cast around diagnostics.
5. Keep the root project-reference structure and invoke build mode.

**Verification.**

    Set-Location frontend
    pnpm typecheck
    pnpm build

Temporarily introduce a type-invalid assignment, prove the exact CI command
fails, then revert it before completing the task.

**Observability/migration.** CI reports Node, pnpm, TypeScript version, duration,
and diagnostic count. No runtime or schema migration.

**Rollback.** Revert config, script, documentation, CI, and cleanup together.

**Do not.** No <code>any</code>, compiler weakening, ignore directive, or
blanket exclude.

**Stop if.** Strict mode exposes additional errors beyond the recorded baseline;
report and split the remediation rather than applying broad casts.

**Commit/evidence.** One commit with zero diagnostics and the deliberate-failure
proof.

### CH-0.6 - Restore deterministic frontend lint and tests

**Objective and risk.** Establish a zero-error, zero-unexplained-warning,
repeatably green frontend gate before behavior changes.

**Files/symbols.** Current ESLint findings in chat/tool feeds, cost components,
inline editors, workflow trace, workspace/Tender UI, cost/procurement helpers,
and <code>ProjectCockpitPage</code>; <code>frontend/eslint.config.js</code>;
the RFT repository-highlight assertion in
<code>ProjectCockpitPage.test.tsx</code>.

**Red baseline.** Record the exact lint diagnostics and full Vitest failures.
The audit saw 18 errors, 4 warnings, and one order-dependent failure out of 413;
do not hard-code those as permanent totals.

**Implementation child packets.**

1. **CH-0.6A - lint and React correctness.** Fix unused values and useless
   assignment/escape. Replace render-time ref writes in inline editors with
   ordered layout-effect updates. Use lazy state initialization rather than
   render-time reads for initial table cells and include real focus dependencies.
   Prefer keyed child state for identity-change resets over synchronous state
   effects. Move non-component exports out of component modules and extract
   complex effect dependency expressions into names. Keep any third-party
   compiler exception local and justified, remove obsolete disables, and make
   lint fail on warnings except a narrow documented third-party exception.
2. **CH-0.6B - deterministic test/full-suite proof.** Fix the flaky RFT
   assertion with an eventual assertion around the state that changes; never use
   sleeps. Run the full suite three consecutive times plus the production build.

**Verification.**

    Set-Location frontend
    pnpm typecheck
    pnpm lint
    pnpm test
    pnpm test
    pnpm test
    pnpm build

Expected: zero errors, zero unexplained warnings, and three complete passes.
Test count may increase but must not fall without explanation.

**Observability/migration.** CI retains command duration, test/lint summary, and
failure artifacts without application data. No schema migration.

**Rollback.** Revert per behavioral component if needed; the release lane stays
red until a correct fix exists.

**Do not.** Do not disable a rule at file/config scope or change edit/save
semantics without a focused regression test.

**Stop if.** Any of the three runs fails or a lint fix changes behavior without
test coverage.

**Commit/evidence.** CH-0.6A and B are separate commits. Both must be complete
before moving on; evidence contains the zero-diagnostic output and three full
test summaries.

### CH-0.7 - Capture baseline and supply-chain evidence

**Objective and risk.** Create a truthful, SHA-specific reference for runtime,
quality, dependency, secret, image, and performance comparisons.

**Files.** New evidence record; <code>.github/workflows/ci.yml</code>;
<code>backend/uv.lock</code>; <code>frontend/pnpm-lock.yaml</code>; existing
bundle/performance scripts.

**Red baseline.** Record current offline test durations/collection, frontend
checks, build sizes, production-container image sizes, API idle RSS, worker idle
RSS, DB connection limits/current use, and build SHA. A missing measurement is
recorded as unknown, never zero.

**Implementation.**

1. Add lockfile integrity and dependency-advisory checks using pinned,
   maintained CI tooling. Triage advisories by reachability; do not blindly
   upgrade the locked stack.
2. Add history/worktree secret scanning with output redaction. A hit reports
   file and rule, not the secret value.
3. Pin third-party CI actions to immutable revisions under the repository's
   update policy.
4. Save the baseline record and raw-artifact digests.

**Verification.** CI must fail on a synthetic secret fixture outside the
repository and on a known test advisory policy fixture, while sanitizing values.
Normal CI passes. Baseline commands can be rerun from the record.

**Observability/migration/rollback.** No schema or runtime migration. Scanners produce SARIF or equivalent stable output
where supported. Roll back an unusable scanner lane independently, but Stage 0
stays open.

**Do not.** Do not print secret matches, auto-fix dependencies, or block on an
untriaged low-severity advisory.

**Stop if.** Tool licensing/maintenance is unclear, a scan requires uploading
source to an unapproved service, or a critical/high reachable advisory has no
disposition.

**Commit/evidence.** One CI policy commit plus the first baseline evidence
record.

Image/base/config scanning is owned entirely by CH-1.7B and CH-5.5. CH-0.7 has
no pending image requirement and can therefore close independently.

### CH-0.8 - Bootstrap a disposable Postgres/pgvector runner

**Objective and risk.** Give every migration, RLS, lease, advisory-lock, and
concurrency task a real isolated database before those tasks begin, without any
route to Supabase or production.

**Files/symbols.**

- new <code>deploy/test/docker-compose.database.yml</code> or equivalent
  repository-owned test definition
- new <code>scripts/test-database.ps1</code>
- <code>backend/pyproject.toml</code> marker declarations
- <code>backend/tests/conftest.py</code> CH-0.2 network allowlist
- CI bootstrap job, initially callable/manual until CH-5.4 enrols all contracts
- migration configuration under <code>backend/alembic/</code>

**Preconditions.** CH-0.2. The container image/version must support the
repository's Postgres extensions and be pinned by digest after maintainer
approval.

**Red tests/baseline.** The current CI cannot upgrade a fresh DB; an
<code>integration</code> marker does not distinguish disposable DB from live
providers; CH-0.2 blocks even the intended test DB until a safe exact allowlist
exists.

**Implementation.**

1. Add a private, ephemeral Postgres/pgvector service with random CI credentials,
   healthcheck, no public host binding in CI, and disposable volume.
2. Keep the normal <code>DATABASE_URL</code> sentinel unreachable. Pass
   <code>TEST_DATABASE_URL</code> only to the dedicated command.
3. Add <code>database_integration</code> marker and
   <code>DATABASE_INTEGRATION_TESTS=1</code> destructive opt-in.
4. Extend CH-0.2 only for opted-in database-integration tests and only for the
   parsed host/port in <code>TEST_DATABASE_URL</code>. Reject public IPs,
   Supabase hostnames, DNS aliases outside the container network, and any
   database carrying a production environment marker.
5. Implement <code>scripts/test-database.ps1</code> to start/wait, create
   extensions, run fresh <code>alembic upgrade head</code> and
   <code>alembic check</code>, execute selected node IDs/markers, then report and
   tear down. It must propagate nonzero status and never print the URL password.
6. Add a database environment marker table/value in the disposable setup and
   require <code>test</code>.
7. Add a minimal CI smoke that invokes the same script; CH-5.4 later adds every
   completed contract.

**Verification.**

- two fresh runs end at the same single Alembic head/schema;
- an intentionally failing migration/test returns nonzero;
- a Supabase/public/test URL substitution is rejected before connecting;
- CH-0.2 still blocks all other network;
- teardown leaves no persistent data/process and logs contain no credential.

**Observability/migration.** This runner exercises migrations but does not alter
application schema in production. Record image digest, Postgres/extension
versions, head, duration, and node list.

**Rollback.** Revert test infrastructure as a unit; doing so reopens GATE-0 and
blocks every dependent DB task.

**Do not.** Do not use a production dump, expose the DB port publicly, or call
provider APIs from this lane.

**Stop if.** The chosen image cannot reproduce required extensions, the
environment marker cannot be proven, or any hostname resolves outside the
explicit test network.

**Commit/evidence.** One runner/marker/network-policy implementation commit and
one coordination commit with two clean-run transcripts.

### CH-0.9 - Add a fail-capable merged-state gate runner

**Objective and risk.** Make GATE-0 through GATE-6 executable against an explicit
candidate source SHA plus its evidence-only coordination SHA, rather than letting
an agent infer completion from prose or stale per-task results.

**Files/symbols.** New <code>scripts/hardening/run-gate.ps1</code>,
<code>scripts/hardening/gate-contract.json</code>, focused PowerShell tests, and
the gate closure protocol in Section 7.2. PowerShell is a repository/operator
tool, not a runtime dependency.

**Red baseline.** Demonstrate that no current command verifies ledger
dependencies, exact SHA/environment, required check IDs, evidence freshness, or
nonzero propagation for a whole stage. A missing evidence file can currently be
mistaken for a pass.

**Implementation.** The JSON contract contains only data: gate ID, required task
IDs, named fixed check-handler IDs, allowed environments, maximum evidence age,
and whether operator/maintainer signatures are required. It never contains shell
source. The PowerShell runner dispatches only checked-in handler functions via a
closed <code>switch</code>; no <code>Invoke-Expression</code>, downloaded code,
or arbitrary command strings. It must:

1. require <code>-Gate</code>, full <code>-CoordinationSha</code> and
   <code>-CandidateSourceSha</code>, exact <code>-Environment</code>, and
   <code>-EvidenceOut</code>;
2. require HEAD to equal the coordination SHA and the source to be its ancestor.
   Verify changes between them are only approved plan/evidence/release-record
   paths and compute the non-coordination tree digest. Fail on a dirty worktree,
   identity/tree/artifact mismatch, unknown gate/check/task, missing dependency/
   result/evidence, expired evidence, or skipped required check;
3. run the repeatable merged-SHA checks in Section 7.2 and invoke task-owned
   checked-in scripts for live/container checks;
4. require an exact staging/production target allowlist plus explicit
   <code>-AllowLiveChecks</code> for networked checks; default operation is
   offline/test;
5. emit sanitized human output and JSON with command/check ID, start/end,
   duration, exit/result, input/evidence digest, environment, both SHAs, and the
   verified non-coordination tree digest;
6. propagate nonzero immediately while still recording remaining checks as
   <code>not-run</code>; never convert failure to warning; and
7. add GATE-0 handlers now. Every later task must add its named handler/contract
   entry with tests in the same implementation commit; a gate cannot close while
   its bullet lacks a handler or explicitly reviewed evidence-only check.

**Verification.** Invoke GATE-0 against a clean synthetic ledger/evidence fixture
and run every fixed handler against the real repository in an explicit
<code>-PreflightOnly</code> mode that does not claim/record gate completion. Then
inject wrong coordination/source SHA, non-ancestor source, a runtime/config file
between source and coordination, dirty file, absent task/evidence, stale
evidence, unknown check, failed command, production target without opt-in, and
secret canary.
Every case fails nonzero and output remains sanitized. Two clean preflight runs
produce the same check set and all repeatable commands actually execute. The
first real GATE-0 run occurs only after CH-0.9 is complete; CH-0.9 evidence must
not self-certify its parent gate.

**Observability.** Gate JSON is the coordination record; it contains no command
environment dump, credentials, URLs with tokens, customer identifiers, or raw
provider responses.

**Migration/rollback.** No application schema. The runner is permanent release
infrastructure. Reverting it reopens every gate and cannot make a release green.

**Do not.** Do not parse and execute Markdown code, trust a task's textual
<code>complete</code> without evidence, accept partial success, or let live mode
infer a target from ambient credentials.

**Stop if.** A required live check has no safe deterministic script/allowlist,
evidence freshness cannot be defined, or the runner would need to execute
unreviewed dynamic code.

**Commit/evidence.** One runner/contract/test implementation commit and one
coordination commit with deliberate-failure transcripts and two green preflight
outputs. GATE-0 produces its own later evidence.

## 9. Stage 1 - security, tenancy, and release control

### CH-1.1 - Create the MCP capability registry and contract

**Objective and risk.** Establish one checked-in classification for every MCP
tool before changing behavior. Unknown tools must be detectable and future
mutators cannot bypass review.

**Files/symbols.**

- new <code>backend/app/mcp_bridge/capabilities.py</code>
- new <code>backend/app/agent/tool_capabilities.py</code> only if intent mapping
  cannot live cleanly with the registry
- new <code>backend/tests/mcp_bridge/test_capability_contract.py</code>
- <code>backend/app/mcp_bridge/server.py</code> registrations
- <code>backend/app/agent/pi_process.py::PI_MCP_DIRECT_TOOLS</code>
- Discover registrations with
  <code>rg -n "@mcp\\.tool|name=" backend/app/mcp_bridge</code>.

**Required contract.** Each registered tool has exactly one record containing:
tool name, read-only/mutating, required scope or none, project-ID source/binding,
feature flag if any, Pi visibility policy, and owning domain.

The audit found 69 tools and these 33 mutators; rediscover and reconcile before
editing:

- <code>project_knowledge_mutation</code>:
  <code>upsert_shared_project_knowledge</code>
- <code>dependency_offer_mutation</code>:
  <code>accept_dependency_update_offer</code>,
  <code>reject_dependency_update_offer</code>
- <code>workflow_mutation</code>:
  <code>start_project_plan</code>, <code>refresh_project_plan</code>,
  <code>start_cost_plan</code>, <code>refresh_cost_plan</code>,
  <code>process_invoices</code>, <code>sort_project_files</code>,
  <code>start_transmittal</code>,
  <code>start_consultant_procurement</code>,
  <code>start_contractor_eoi</code>,
  <code>start_trade_procurement</code>,
  <code>cancel_project_workflow</code>,
  <code>start_tender_comparison</code>
- <code>cost_plan_mutation</code>:
  <code>upsert_cost_item</code>, <code>set_contingency</code>,
  <code>set_cost_plan_assumption</code>,
  <code>apply_cost_plan_operations</code>,
  <code>apply_approved_tender_to_cost_plan</code>,
  <code>apply_consultant_fee_forecast</code>,
  <code>apply_cost_plan_budget_forecast</code>
- <code>artefact_mutation</code>:
  <code>apply_artefact_operations</code>,
  <code>draft_consultant_procurement_artifact</code>
- <code>decision_mutation</code>:
  <code>update_project_decision</code>, <code>lock_project_decision</code>,
  <code>unlock_project_decision</code>
- <code>profile_mutation</code>: <code>update_project_profile</code>
- <code>profile_proposal_mutation</code>:
  <code>propose_project_profile_change</code>,
  <code>accept_project_profile_proposal</code>,
  <code>reject_project_profile_proposal</code>
- <code>tender_selection_mutation</code>:
  <code>replace_tender_quote_selection</code>
- <code>workspace_scratch_mutation</code>:
  <code>write_workspace_file</code>

**Red tests.**

1. Enumerate runtime registrations and fail if a tool is absent from the map or
   appears twice.
2. Fail if a mutator has no scope or a read-only tool has a mutation scope.
3. Fail if a Pi-visible name is not registered.
4. Snapshot complete public contracts: name, input schema, output/content shape,
   authorization class, and feature condition. Do not snapshot names only.

**Implementation.** Add immutable scope constants and records, build
lookup/validation helpers with no imports from the monolithic server, and make
the contract tests pass without yet changing authorization behavior.

**Verification.**

    Set-Location backend
    uv run pytest tests/mcp_bridge/test_capability_contract.py -q
    uv run pytest tests/mcp_bridge -q

Record discovered counts; if they differ from 69/33, explain every delta.

**Observability/migration/rollback.** No migration or runtime log. Registry
validation may run fail-fast at startup in development/test, while production
uses the same prevalidated immutable data.

**Do not.** Do not infer mutability from names at runtime, grant a catch-all
scope, or move tool implementations.

**Stop if.** Any tool's side effects or project binding are ambiguous.

**Commit/evidence.** One registry-and-contract commit. Evidence contains the
tool contract digest, never turn tokens.

### CH-1.2 - Fail closed at every MCP mutation seam

**Objective and risk.** Empty or wrong turn scopes must reject every mutator
before application logic, even if Pi is prompt-injected or calls a hidden tool
directly.

**Files/symbols.**

- <code>backend/app/mcp_bridge/auth.py::authorize_project_mutation_with_claims</code>
- <code>backend/app/billing/usage.py::require_active_mutation_turn</code>
- all mutation authorization call sites in
  <code>backend/app/mcp_bridge/server.py</code>
- registry from CH-1.1
- existing MCP auth/profile tests

**Red tests.** Parameterize every mapped mutator. Empty scope, an unrelated
scope, expired/revoked turn, and a different project must fail before a patched
application service is invoked. Correct scope reaches the stub. Unknown
mutator name fails closed.

**Implementation.**

1. Make <code>required_scope</code> non-optional in both authorization helpers;
   remove the <code>None</code> default.
2. Add <code>authorize_mutation_tool(..., tool_name=...)</code>, resolving the
   scope from CH-1.1. Unknown/read-only names are errors.
3. Update every mutator to pass its actual registered tool name. Do not copy
   scope strings through <code>server.py</code>.
4. Preserve project ownership, token hash, patch binding, expiration, and
   revocation checks.
5. Ensure rejection is stable and contains no token/scope inventory useful to
   an attacker.

**Verification.**

    Set-Location backend
    uv run pytest tests/mcp_bridge/test_capability_contract.py tests/mcp_bridge/test_auth.py tests/mcp_bridge/test_profile_tools.py -q
    uv run pytest tests/mcp_bridge -q
    uv run pytest -m "not integration and not tender_eval" -q

Expected: all mapped mutators fail with empty/wrong scopes; all registered tools
remain available under correct authority.

**Observability.** Count denials by tool/domain/reason class and correlation ID,
not token, arguments, customer content, or user-entered prompt.

**Migration/rollout.** Code-only. Deploy atomically; in-flight old turns may
lose write authority and should receive the normal retry/confirmation path.

**Rollback.** Revert the entire helper/call-site commit. A rollback reopens a P0
release blocker.

**Do not.** Do not leave an optional scope compatibility path or catch
authorization failure and continue.

**Stop if.** Any mutator lacks a stable registered name or a correct-scope test.

**Commit/evidence.** One atomic fail-closed commit; never deploy a branch with
only some mutators converted.

### CH-1.3 - Reserve scopes and restrict Pi tool visibility

**Objective and risk.** A turn receives only the mutation scopes justified by
deterministic intent and Pi's generated MCP config exposes only read tools plus
those authorized mutators. Server enforcement remains authoritative.

**Files/symbols.**

- <code>backend/app/agent/mutation_intent.py</code>
- <code>backend/app/agent/turn_context.py::turn_needs_mutation_tools</code>
- <code>backend/app/api/chat.py::post_agent_stream</code>
- <code>backend/app/agent/pi_process.py::PI_MCP_DIRECT_TOOLS</code>,
  <code>_write_pi_mcp_config</code>, <code>stream_pi_turn</code>
- agent intent, chat API, and turn-context tests

**Red tests.**

- a read-only budget question reserves no mutation scopes and sees no mutators;
- “create an RFP” sees required workflow tools but not cost/profile/decision
  mutators;
- each scope has positive phrases and nearby read-only negative phrases;
- ambiguous intent grants nothing and asks for confirmation;
- all Pi-visible names exist in the MCP contract;
- cancellation before publication cannot commit through a previously visible
  tool.

**Implementation.**

1. Replace the unused boolean mutation detector with explicit deterministic
   scope inference for every registry scope.
2. Reuse the existing profile patch-binding behavior.
3. Reserve the exact inferred set in <code>chat.py</code>; no catch-all fallback.
4. Derive <code>direct_tools_for_scopes</code> and the complement
   <code>excluded_tools_for_scopes</code> from the registry. Pi
   <code>directTools</code> is only promotion, not authorization: generate an
   explicit per-turn <code>excludeTools</code> deny-list for every ungranted
   mutator (or disable the generic MCP proxy after all permitted direct tools are
   cached). Test both discovery and direct invocation of a denied name.
5. Pass scopes explicitly through stream/process setup. Create a unique
   unpredictable MCP config path per admitted turn rather than shared project
   <code>.pi/mcp.json</code>; write atomically with owner-only permissions, pass it
   through Pi's explicit config argument, and delete it in <code>finally</code>.
   Two concurrent turns in one project must not observe or overwrite each
   other's visibility.
6. On ambiguity, grant no write tool and let the assistant obtain explicit user
   confirmation in a later turn.

**Verification.**

    Set-Location backend
    uv run pytest tests/agent/test_mutation_intent.py tests/agent/test_turn_context.py tests/agent/test_agent_chat_api.py -q
    uv run pytest tests/mcp_bridge/test_capability_contract.py tests/mcp_bridge -q
    uv run pytest -m "not integration and not tender_eval" -q

Add a concurrent-turn test with disjoint scopes. Each Pi config exposes only its
read tools and authorized mutators, its proxy cannot discover/call the other's
mutator, both files are owner-only and distinct, and both are removed afterward.

**Observability.** Log scope names and visible-tool count, never prompts, tokens,
patch payloads, or generated config contents.

**Migration/rollback.** No schema change; deploy with CH-1.2 already live or in
the same release. Rollback visibility independently only if CH-1.2 remains.

**Do not.** Do not use model-generated intent to grant authority or expose all
mutators “for convenience.”

**Stop if.** A scope cannot be tied to explicit user language without broad
false positives; require confirmation rather than expanding matching.

**Commit/evidence.** One intent/reservation/visibility commit and a sanitized
matrix of prompt class to scope/tool set.

### CH-1.4 - Audit live DB grants, RLS, exposed schemas, and Storage safely

**Objective and risk.** Establish the actual live security boundary before
writing migrations. Migration inspection alone is not proof of exposure.

**Files.**

- new <code>scripts/sql/audit-data-security.sql</code>
- new <code>docs/runbooks/data-security-audit.md</code>
- task evidence matrix
- existing <code>backend/alembic/versions/</code>
- <code>backend/app/storage/project_files.py</code>

Reference:
[Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security),
[API security](https://supabase.com/docs/guides/api/securing-your-api), and
[production checklist](https://supabase.com/docs/guides/deployment/going-into-prod).

**Preconditions.** Verified backup visibility and explicit operator approval.
CH-1.4A uses a dedicated read-only catalogue credential/transaction. CH-1.4B is
a separately authorized active probe limited to two dedicated synthetic users,
projects, rows, bucket prefixes, and a cleanup/reconciliation manifest. Never use
customer rows/paths or broaden the catalogue credential.

**Red baseline.** Inventory every exposed/public table as tenant-owned,
platform/global, internal operational, or migration metadata. Query table
owner, <code>relrowsecurity</code>, <code>relforcerowsecurity</code>, policies,
grants to public/anon/authenticated/service/backend roles, role bypass flags,
Data API exposed schemas, Realtime publications, Storage bucket privacy, and
<code>storage.objects</code> policies.

**Implementation child packets.**

1. **CH-1.4A - read-only live catalogue.** Check in catalogue queries and
   instructions that set/verify a read-only transaction before inspection.
   Inventory classifications, table ownership/bypass behavior, RLS/force flags,
   policies/grants, exposed schemas, publications, buckets, and Storage policies.
   Record names and pass/fail only; export no row contents. Obtain maintainer
   approval for every table classification and direct-browser exception. This
   child performs no mutation.
2. **CH-1.4B - authorized synthetic active probes.** First run the exact probe
   against non-production. Then, in the approved live maintenance window, create
   only the predeclared A/B fixture rows/objects under unique run-ID prefixes.
   Test anonymous/A/B negative read/write/delete/list behavior and intended
   service/backend positive read/write. Before each write, assert target owner/
   prefix/run ID. Delete fixtures through the scoped cleanup path, reconcile DB
   and Storage counts/keys to zero, and retain only hashes/counts/results. If
   fixture creation or cleanup cannot be proven, stop and leave the gate failed.

**Verification.** Anonymous/authenticated roles have no undeclared table access;
user A cannot list/read/write/delete B's object; the bucket is private; the
intended privileged backend path still works.

**Observability/migration/rollback.** No schema/policy migration. CH-1.4B creates
only temporary synthetic fixtures and must remove/reconcile them; backup is the
last-resort recovery, not routine cleanup.

**Do not.** Do not enable RLS, revoke grants, inspect customer rows, mutate from
the catalogue connection, use a broad object prefix, or assume service-role
behavior from local migrations.

**Stop if.** Any cross-tenant access succeeds, direct browser DB access is
discovered, or backend role behavior is unknown. This is an immediate launch
blocker and requires review before CH-1.5.

**Commit/evidence.** CH-1.4A and B are separate implementation/evidence pairs;
the signed redacted matrix includes fixture cleanup/reconciliation.

### CH-1.5 - Enforce and continuously test the tenant security contract

**Objective and risk.** Convert the approved CH-1.4 matrix into forward
migrations/Storage policy changes and a permanent explicit invariant.

**Files/symbols.**

- new Alembic revision(s) from current head
- new <code>backend/tests/integration/test_database_security_contract.py</code>
- model/migration registration as needed
- source-controlled idempotent Supabase Storage policy SQL if managed-schema
  policy cannot safely live in Alembic
- CH-1.4 audit script

**Red test.** Freeze an explicit required/exempt table contract. Against a
freshly migrated disposable DB, fail with exact tables lacking approved RLS or
holding unapproved grants. Add anonymous/A/B/service-role negative cases for
the approved live staging environment.

**Implementation child packets.**

1. **CH-1.5A DB security transition:** reconfirm one Alembic head; never edit
   historical revisions. Record row counts/table size, lock impact, maintenance
   window/canary, bounded DDL timeouts, and application-role compatibility.
   For backend-only application tables, revoke unneeded public/anon/authenticated
   privileges, enable RLS, and use deny-by-default.
   Add narrow policies only for specifically approved direct access. Freeze
   every table classification in the permanent executable contract.
2. **CH-1.5B Storage/live isolation:** apply private-bucket/
   <code>storage.objects</code> policy through a
   source-controlled idempotent deployment step.
   Run backend API/service-role Storage smoke tests and two-tenant negatives.

Keep exemptions literal and reviewed; no wildcard table-name rule. From this
task onward, every migration that creates a table must update and run the
classification/grant/RLS contract in the same child packet.

**Verification.**

- fresh upgrade and previous-head upgrade on disposable DB;
- security contract reports zero unclassified tables/unapproved grants;
- permanent contract reruns against the current isolated restore from CH-1.10
  (refresh the restore if its evidence is outside the approved age);
- user A/B database and Storage isolation passes;
- backend behavior remains intact;
- rerun the live read-only catalogue diff after approved deployment.

**Observability.** Log authorization outcome/correlation only at the API; never
log DB row content or Storage signed tokens.

**Migration/rollout.** Backup first. This is a security transition, not an
additive/no-impact change. Execute through CH-1.13 with the approved lock and
maintenance/canary plan. Verify backend role behavior before traffic. Storage
policy application must be idempotent and recorded.

**Rollback.** Prefer previous compatible application while investigating.
Provide a reviewed downgrade restoring prior grants/policies, but do not execute
it on live data as a reflex.

**Do not.** Do not add a permissive “authenticated can access all” policy or
silently exempt a table to green the test.

**Stop if.** The backend role becomes subject to policies without tenant context
or a frontend direct access path was omitted.

**Commit/evidence.** CH-1.5A and CH-1.5B are separate implementation/evidence
commit pairs. Both are required for completion.

### CH-1.6 - Clear private frontend caches on identity change

**Objective and risk.** User B must never see data cached for user A in the same
browser tab, even transiently.

**Files/symbols.** <code>frontend/src/components/AuthGuard.tsx</code>,
<code>src/lib/query-client.ts</code>, <code>src/lib/auth.ts</code>,
<code>src/main.tsx</code>, <code>src/App.tsx</code>, chat query keys, and new
app-lifetime auth-provider tests.

**Red tests.**

1. Seed the real test QueryClient with user-A chat/project data.
2. Apply A-to-B auth change and assert cache is absent before B-protected
   children render.
3. Apply A-to-signed-out, navigate through signed-out routes, then sign in as B;
   no route remount may bypass the clear.
4. Race the auth listener against a stale <code>getSession()</code> completion;
   the stale initial read cannot restore A after B.
5. Same-user token refresh must preserve cache and cause no refetch storm.

**Implementation.**

1. Add one app-lifetime <code>AuthSessionProvider</code> immediately under
   <code>QueryClientProvider</code>; route-mounted/unmounted guards must consume
   it rather than own independent subscriptions.
2. Subscribe to auth changes before starting <code>getSession()</code>. Track a
   monotonically increasing listener revision; ignore an initial result whose
   captured revision is stale.
3. Track last published user ID with a distinct uninitialized state.
4. On different identity or sign-out, synchronously
   <code>queryClient.clear()</code> before publishing the new session. Clear
   covers query and mutation caches; cancel in-flight private requests first and
   make their stale completion unable to repopulate after the identity revision.
5. Do not attempt a fragile query-key allowlist and do not clear on same-user
   refresh.
6. Reduce <code>AuthGuard</code> to authorization/rendering over provider state;
   it must not create a second Supabase subscription.

**Verification.**

    Set-Location frontend
    pnpm test -- AuthGuard.test.tsx
    pnpm typecheck
    pnpm lint
    pnpm test
    pnpm build

No A thread title/project ID may appear in B's DOM. Cache-clear count is zero on
same-user refresh.

**Observability/migration/rollback.** No migration. Auth events may log safe
transition class, never user IDs/tokens. Atomic code rollback reopens the P0.

**Do not.** Do not render next-user children before clear or clear on every
token event.

**Stop if.** Tests require sleeps or initial/listener races remain possible.

**Commit/evidence.** One cache-isolation commit and DOM/cache test evidence.

### CH-1.7 - Build, prove, and stage an immutable release path

**Objective and risk.** Only one tested SHA/digest can be selected by Dokploy; a
failed CI push cannot deploy; production auto-deploy is disabled; container
runtime hardening is proven before the protected production path is configured.
Production promotion is not exercised until Stage 6.

**Files/symbols.** <code>.github/workflows/ci.yml</code>, new release workflow
or release jobs, both Dockerfiles, <code>deploy/dokploy.compose.yml</code>,
health/build-version code, <code>DEPLOYMENT.md</code>, and new
<code>scripts/verify-deploy-contract.ps1</code>.

Reference: [Dokploy Compose API](https://docs.dokploy.com/docs/api/compose).

**Preconditions.** Maintainer approves registry and exact Dokploy
API/webhook/manual-promotion mechanism. CH-1.13 owns migrations and compatibility.

**Red tests/baseline.** Prove current compose permits mutable
<code>latest</code>/production builds and that a failed-CI push can independently
trigger deployment.

**Implementation child packets.**

1. **CH-1.7A - define immutable staging/release contract.** Verify CH-0.0's
   independent production auto-deploy containment is still active. Give workflows
   explicit minimal permissions, timeouts, concurrency, and protected
   environments. Production concurrency is one. Change compose to required
   image repository plus required SHA/digest; remove production build blocks,
   mutable tags, and <code>pull_policy: never</code>. Add a contract script that
   resolves compose with safe values and fails closed.
2. **CH-1.7B - build/smoke the exact hardened images.** Build API/web once after
   required checks, tag full SHA, attach OCI revision, and push to the approved
   registry. CI must prove:
   - backend runtime UID is non-root; exact Pi and MCP adapter exist;
   - <code>app.main</code> imports and health responds against disposable DB;
   - web Nginx starts and root/deep-link/hashed/missing-asset checks work;
   - no production secret/canary is present in image history, environment, or
     filesystem;
   - Docker base images are pinned by digest and have a reviewed update cadence;
   - <code>no-new-privileges</code>, dropped capabilities, read-only root
     filesystem, and tmpfs are applied wherever compatible;
   - every writable path is enumerated. Pi workspace, ODL/LibreOffice temp/cache,
     generated files, and Nginx runtime paths receive narrow volume/tmpfs
     exceptions rather than a globally writable container;
   - web and every backend role that exists in Stage 1 (API, Tender, and core
     workflow) have a healthcheck. CH-2.6A and CH-3.4B add cleanup/parser role
     healthchecks when those services are introduced.
   Export these exact digests; a later release job consumes them and never
   rebuilds.
3. **CH-1.7C - configure protected production promotion.** Use CH-1.13's
   migration runner plus compatibility specification/release record, update
   Dokploy to the tested digest, poll status,
   and verify SHA. Implement this path and test it against staging/a dry-run
   production target, but do not execute a real production promotion in this
   task. Store previous compatible SHA/rollback floor. In staging, promote the
   candidate, select the prior compatible digest, require three readiness
   responses and reconcile migration/job/object state, then restore/reverify the
   candidate. Prove rollback completes inside ten minutes. Production execution
   belongs to CH-6.3.

**Verification.**

- contract script fails on <code>latest</code>, empty SHA, production build
  blocks, or unpinned images;
- intentionally failed required CI causes no promotion/deployment;
- green staging SHA has identical registry and host digest;
- three consecutive readiness responses report expected SHA;
- staging prior-digest selection, readiness/reconciliation, and candidate
  restoration pass inside ten minutes;
- base/runtime hardening and writable-path tests pass;
- a release consumes the built digest without rebuilding;
- staging promotion completes within the approved ten-minute window;
- production auto-deploy is off and the protected production action requires
  approval.

**Observability.** Release log contains workflow/run/SHA/digest/status but no
deployment credentials.

**Migration/rollback.** CH-1.13 executes migrations. Rollback selects only the
prior SHA proven compatible by its release record and never automatically downgrades
data. The exact CH-1.7C sequence is GATE-1's staging rollback proof; production
proof is Stage 6.

**Do not.** Do not keep simultaneous auto-deploy paths, rebuild after tests, or
put API keys in commands/logs.

**Stop if.** Dokploy cannot deploy an exact digest/SHA, a migration breaks the
previous image, or promotion credentials cannot be protected.

**Commit/evidence.** CH-1.7A, B, and C are separate implementation/evidence
commit pairs. Evidence includes auto-deploy-off proof, run URL, base/image
digests, UID/Pi/writable-path/hardening output, staging SHA, and rollback floor.

### CH-1.8 - Replace Hermes with a fail-capable Pi core validator

**Objective and risk.** The core validator exercises the canonical Pi path and
exits nonzero on required failure. CH-3.1B later adds compatibility-aware
readiness; GATE-3 is the first full release-validator gate.

**Files.** <code>scripts/sitewise-vps-phase8-validate.ps1</code>,
<code>DEPLOYMENT.md</code>, Pi plan, and
<code>docs/runbooks/stage-9-production-acceptance.md</code>.

**Red baseline.** Demonstrate that the current runner converts required command
failure to warning/success and that checks/documentation still target Hermes.

**Implementation.**

1. Define required/advisory check records with name, time, duration, sanitized
   result, and expected SHA.
2. Required failure produces exit 1; missing prerequisites have a distinct
   nonzero exit; advisory failure remains visible but does not fail.
3. Remove Hermes checks. Required core checks: exact Pi version, non-root API
   UID, adapter presence, MCP initialize/list, expected CH-1.1 tool-contract
   digest and Pi-visible set, liveness/build SHA, authenticated SSE completion,
   cancellation/revocation, and zero remaining child process.
4. Put paid/live checks behind explicit switches and dedicated fixture IDs.
5. Sanitize credentials, cookies, prompts, customer data, Stripe IDs, and
   documents.
6. Emit human summary and machine-readable JSON.
7. Provide an explicit extension point/check ID for CH-3.1B readiness without
   treating the absent future check as passed.
8. Update every runbook invocation.

**Verification.** Inject required/advisory failures and assert exit behavior.
Production mode with missing expected SHA fails before paid calls. Successful
staging output has no secret canaries. Cancellation leaves no Pi child after 15
seconds.

**Observability/migration/rollback.** Validator only; previous version remains
in Git. JSON evidence becomes a release input.

**Do not.** Do not count warnings as required success, retain Hermes probes, or
print provider responses wholesale.

**Stop if.** A dedicated acceptance user/project/thread is unavailable.

**Commit/evidence.** One validator/runbook commit and sanitized JSON with tool
compatibility-spec hash.

### CH-1.9 - Add visible loading, exception boundaries, and safe failure copy

**Objective and risk.** Lazy-load, render, and connection failures must never
leave a blank or developer-facing screen.

**Files/symbols.** New <code>AppErrorBoundary.tsx</code> and tests; route/panel
pending UI; <code>main.tsx</code>, <code>App.tsx</code>,
<code>ProjectCockpitPage</code>, <code>HomePage</code>,
<code>ChatPage</code>, and <code>lib/chat-ui.ts</code>.

**Red tests.** A child render exception escapes; delayed/rejected lazy routes
produce no status because fallback is null; customer copy mentions local port
or environment variable.

**Implementation.**

1. Add catastrophic root boundary with safe summary and Reload.
2. Add location-keyed route boundary so navigation resets it.
3. Replace user-visible null Suspense fallbacks with stable
   <code>role="status"</code> shells.
4. Add compact boundaries around high-risk lazy cockpit panels without hiding
   normal API error states.
5. Replace localhost/environment instructions with customer-safe retry/support
   copy; keep details in redacted logs.
6. Preserve focus and visible keyboard focus in recovery states.

**Verification.**

    Set-Location frontend
    pnpm test
    pnpm typecheck
    pnpm lint
    pnpm build
    rg -n "port 8000|VITE_API_BASE_URL|fallback=\\{null\\}" src

Expected: deliberate route/panel errors show recoverable UI, and the search has
no customer-facing/dead fallback matches.

**Observability/migration.** Emit a sanitized route/panel failure class, build
SHA, and correlation ID to the approved sink once CH-3.3 is available; never
send stack, URL query, or customer state. No schema migration.

**Rollback.** Revert boundaries/fallback/copy together; release remains blocked.

**Do not.** Do not expose stack traces or use boundaries for ordinary API
state.

**Stop if.** Recovery loops without changing state or focus becomes trapped.

**Commit/evidence.** One resilience commit with render/lazy/keyboard tests.

### CH-1.10 - Prove backup/restore and approve retention

**Objective and risk.** Establish achievable RPO/RTO for Postgres and Storage
and an approved data-class retention matrix before security migrations or
automatic deletion.

**Files.** New <code>docs/runbooks/production-backup-restore.md</code>,
<code>docs/runbooks/data-retention.md</code>, task evidence, Tender PRD Section
on retention, and Stage 9 runbook.

**Preconditions.** Provider/operator access, isolated restricted restore target,
and business/legal approver.

**Red baseline.** Record Supabase plan, PITR window, backup frequency, Storage
backup/version/lifecycle behavior, owner, and escalation. Unknown is a failed
gate, not assumed coverage.

**Implementation.**

1. Classify source documents, Tender images/reports/observations, chat,
   artefacts, audit events, telemetry, logs, and deletion/legal holds.
2. Approve duration, legal/business basis, owner, purge/anonymize action, and
   backup interaction for every class.
3. Confirm or revise the proposed RPO <=15 minutes and RTO <=4 hours.
4. Restore a production backup into an isolated restricted environment, never
   over production.
5. Validate Alembic head, critical row counts/checksums, foreign keys, Storage
   inventory count/bytes/sample hashes, the approved CH-1.4 catalogue/grant/RLS
   baseline, and smoke reads. CH-1.5 creates the permanent executable contract
   afterward and reruns it against this restore.
6. Record secure teardown and exact point-in-time/full restore procedures.

**Verification.** Restore completes within approved objectives with zero
unexplained reconciliation differences. Every data class has an approval.

**Observability/migration/rollback.** No application migration. Restore drill is
isolated. Evidence is sanitized and operator signed.

**Do not.** Do not assume database PITR backs up Storage objects, export
customer content into Git, or implement purge before approval.

**Stop if.** No usable backup/PITR, failed restore, missing Storage coverage, or
unapproved class. This blocks go-live.

**Commit/evidence.** Runbooks/template commit plus separately signed restore and
retention evidence.

### CH-1.11 - Give each service only the secrets and settings it requires

**Objective and risk.** Compromise of a Tender, core-workflow, cleanup, or web
container must not expose unrelated Stripe, Pi, search, or other service
credentials. Current compose shares one broad backend environment anchor.

**Files/symbols.**

- <code>deploy/dokploy.compose.yml</code> and deployment env examples
- <code>backend/app/config.py</code> role-aware validation in the single
  canonical settings module
- API, Tender worker, and core worker entry points now; cleanup/parser worker
  entry points extend this contract in CH-2.6A/CH-3.4B when they are created
- new compose/settings contract tests
- Discover actual use with
  <code>rg -n "settings\\.[a-z_]+" backend/app backend/tender</code>.

**Red tests/baseline.** Resolve compose with synthetic canary values and prove
Tender/core receive Stripe/Pi secrets they do not use. Inventory the minimum
settings each process actually imports at startup and during representative
work.

**Required service contract.**

- API: DB/Supabase auth+Storage, billing/webhook, Pi/MCP, and only enabled
  provider/search credentials;
- Tender worker: DB, Storage, OpenAI and ODL only when enabled;
- core workflow worker: DB, Storage, and only its required model/provider keys;
- cleanup worker (future CH-2.6A): DB and Storage only;
- parser worker (future CH-3.4B): DB, Storage, and parser configuration only;
- web: public build-time URL/anon values only; no backend secret at runtime.

**Implementation.**

1. Add an explicit backend <code>SERVICE_ROLE</code> enum in
   <code>app/config.py</code>. Keep that module the source of truth.
2. Make genuinely role-specific secrets optional at parse time, then validate
   the exact required set for the selected role/feature flags. Add typed
   <code>require_*</code> accessors where optional typing would otherwise leak
   throughout app code; they fail fast without printing values.
3. Split the compose anchor into common non-secret values and per-service
   environment maps. Never pass a secret merely to satisfy an overbroad
   settings constructor.
4. Add a checked-in matrix of allowed and forbidden variable names for the
   currently existing API/Tender/core/web services. Define cleanup/parser rows as
   normative future entries, but do not claim their startup smoke passes before
   their entry points exist. CH-2.6A and CH-3.4B must activate those rows and add
   their role smokes in the same implementation commits.
   The resolved-compose test uses canaries and fails if a forbidden name/value
   is present.
5. Start each currently existing image role with only its allowed fixture
   environment and exercise one representative operation/import.
6. Document rotation/blast radius per credential.

**Verification.** Every Stage-1 role starts and passes its smoke with its minimal
map; removing one required setting fails at startup; forbidden secret-to-service
mappings are zero; web image/environment/history contains no backend secret.
The future cleanup/parser rows are schema-validated but remain explicitly
<code>not-yet-instantiated</code>, not falsely passed.

**Observability/migration.** Startup logs service role, enabled feature names,
environment, and SHA only. No schema migration.

**Rollback.** Revert settings and compose maps together. Do not restore the
shared secret anchor in production; if a role is missing a legitimate setting,
add that explicit mapping with test/review.

**Do not.** Do not create separate ad hoc env readers, log missing values, or
use one “worker” role that accumulates every secret.

**Stop if.** Actual runtime imports make role requirements unclear. Instrument
and inventory rather than guessing.

**Commit/evidence.** Role-aware settings and compose split are one
implementation/evidence pair with the resolved canary matrix.

### CH-1.12 - Harden the host and Dokploy administration perimeter

**Objective and risk.** Only approved public application ports and restricted
administration paths are externally reachable; host, SSH, Docker, Dokploy, and
TLS controls have an owner and emergency path.

**Files/artifacts.**

- <code>DEPLOYMENT.md</code> and a new perimeter hardening runbook
- provider firewall/security-group configuration evidence
- host firewall/SSH/Docker/Dokploy/TLS configuration (operator managed)
- external port/TLS verification script that performs read-only probes

**Preconditions.** Named host operator, out-of-band emergency access, current
backup, and a maintenance window. Never change firewall/SSH access without
proving the recovery path first.

**Red baseline.** From an external approved scanner, inventory TCP/UDP exposure,
including 22, 80, 443, 3000, 8080, Docker daemon ports, and provider console
paths. Record whether Dokploy uses TLS/auth and whether SSH is key-only. Current
documentation that firewalling is disabled/public admin is a failed gate until
proven otherwise.

**Implementation.**

1. Approve the required public surface: normally 80/443 only; redirect 80 to
   443. Restrict SSH and Dokploy administration to approved IP/VPN/identity
   access. Do not assume obscurity of a high port is protection.
2. Enable provider and host firewall defense in depth without locking out the
   emergency path.
3. Enforce SSH key-only authentication, disable direct root login, review
   sudo/admin users/keys, and document revocation.
4. Ensure Docker daemon/socket is not network-exposed and only approved local
   principals can control it.
5. Put Dokploy behind TLS and strong authentication; remove direct public
   port-3000 exposure if the approved access path does not require it.
6. Remove/loopback-bind web port 8080 bypass; CH-4.6 later verifies application
   edge behavior.
7. Prove certificate renewal and configure expiry alerts to the CH-3.0-selected
   destination when available; until then record the future wiring dependency.
8. Record emergency access, lockout recovery, patch/reboot owner, and change
   rollback.

**Verification.** External scan exposes only approved public ports/restricted
admin path; HTTP redirects safely; TLS chain/hostname/protocol pass; SSH
password/root login fails; Docker remote port is closed; authorized emergency
access is tested without publishing keys.

**Observability/migration.** Operator configuration, no DB migration. Retain
external scan timestamp/source and certificate expiry, not IP allowlist secrets.

**Rollback.** Apply firewall/admin changes in recoverable increments with an
open verified emergency session. Roll back the exact last rule if health/admin
access fails; do not reopen all ports.

**Do not.** Do not run an intrusive scan without authorization, print firewall
allowlists/keys, or disable the only recovery path.

**Stop if.** Emergency access, provider-console ownership, or exact current
network topology is unknown.

**Commit/evidence.** Runbook/verification script commit plus operator-signed
external scan and access-control evidence.

### CH-1.13 - Add a locked migration runner and build compatibility specification

**Objective and risk.** Exactly one controlled process applies an expected
forward migration from an expected source revision; concurrent deploys cannot
race; failure is bounded/sanitized; rollback compatibility is explicit.

**Files/symbols.**

- new <code>backend/app/database/migration_runner.py</code>, invoked inside the
  production backend image as
  <code>python -m app.database.migration_runner</code> using its venv
  <code>PATH</code>; <code>uv</code> is not present in that runtime image
- <code>backend/alembic/env.py</code> support for a caller-supplied connection
- new migration-runner integration tests
- release workflow/DEPLOYMENT instructions
- embedded compatibility-spec schema and post-build release-record template from
  Section 3.5

**Fixed contract.**

- advisory-lock namespace string:
  <code>clerk:production-schema-migration:v1</code>, converted in SQL with one
  checked/tested hash expression;
- runner arguments:
  <code>--expected-source</code>, <code>--target</code>,
  <code>--backup-attestation</code>, <code>--lock-wait-seconds</code>;
- default maximum advisory-lock wait 60 seconds;
- the same SQLAlchemy connection holds the advisory lock and is passed through
  Alembic <code>Config.attributes["connection"]</code>;
- source mismatch, stale/missing backup attestation, multiple heads, lock
  timeout, migration error, or target mismatch returns nonzero and sanitized
  output;
- only forward upgrade; no automatic downgrade.

**Red tests.**

1. Two concurrent runners against disposable DB: one owns the lock; the other
   waits then exits according to the bounded contract, never applies twice.
2. Wrong source/target or multiple head fails before DDL.
3. Lock is demonstrably held on the connection Alembic uses.
4. Exception releases lock/connection and preserves accurate current revision.
5. Missing/stale backup attestation blocks a production-mode invocation.

**Implementation child packets.**

1. **CH-1.13A held-connection runner:** make <code>alembic/env.py</code> use an
   injected connection when present;
   retain existing standalone behavior for local commands.
   Runner opens the approved direct/session connection, verifies environment
   identity and current revision, acquires the advisory lock with a bounded
   try-loop, rechecks revision after lock, and invokes Alembic on that connection.
   Verify target head and required schema capability queries before success.
   Create a sanitized JSON/human result with source, target, duration, build,
   and outcome; no DSN.
   Require a recent CH-1.10-compatible backup/PITR attestation file whose digest
   is recorded in release evidence. The runner validates metadata/signature or
   approved CI provenance, not a user-supplied free-form string.
2. **CH-1.13B compatibility-spec/release wiring:** validate and embed Section
   3.5's pre-build compatibility specification in CI. The release path verifies
   its digest and later creates/validates the post-build release record with
   current/prior SHA/digests and rollback floor before migration.
    Run every future production migration only through this module. CH-1.7B
    must test this exact <code>python -m</code> command in the built image; a
    development-only <code>uv run</code> wrapper is not release evidence.

**Verification.**

    Set-Location backend
    uv run pytest tests/database/test_migration_runner.py -m database_integration -q

Also run fresh, previous-head, concurrent-run, source-mismatch, migration-error,
and application-rollback compatibility scenarios through CH-0.8.

**Observability.** Lock wait, source/target, duration, outcome, release SHA, and
attestation digest. Alert on failure without DSN/DDL parameters.

**Migration/rollout.** This task changes the migration execution seam, not the
business schema. Deploy/test the runner before CH-1.5 uses it.

**Rollback.** Runner code may roll back to a previously proven runner; schema
does not automatically roll back. A release selects only a SHA compatible with
the resulting revision.

**Do not.** Do not invoke a separate <code>alembic upgrade</code> subprocess
after releasing the lock, use the transaction pooler, or accept “head” without
expected-source/specification/release-record validation in production.

**Stop if.** Alembic cannot use the held connection, backup attestation cannot be
authenticated, or the migration has no safe compatibility specification and
release record.

**Commit/evidence.** CH-1.13A and B are separate implementation/evidence pairs;
both complete the task.

## 10. Stage 2 - durable jobs and data correctness

### CH-2.1 - Scope Tender jobs by environment

**Objective and risk.** A development, staging, or production Tender worker may
claim, sweep, inspect barriers, or enqueue continuations only for its configured
environment. This closes the cross-environment queue defect in CH-P0-05.

**Files/symbols.**

- <code>backend/tender/models.py::TenderJob</code>
- <code>backend/tender/services/jobs.py</code>
- <code>backend/tender/services/continuations.py</code>
- <code>backend/tender/services/expectations.py</code> direct constructors
- <code>backend/tender/worker.py</code>
- <code>backend/app/config.py::Settings</code>
- deployment examples/compose
- new Alembic revision and
  <code>backend/tests/tender/test_queue_scope.py</code>
- Discover every query/constructor with
  <code>rg -n "TenderJob|claim_next|requeue_stale|after_job_complete" backend/tender</code>.

**Preconditions.** Stage 1 security/backup gates; identify and drain old Tender
workers; count existing rows by status and determine whether every actionable
row belongs to production.

**Red tests.**

- enqueue stamps dev/staging/production;
- a production worker cannot claim or sweep a staging row;
- scope appears in SQL before <code>FOR UPDATE SKIP LOCKED</code>;
- duplicate/readiness/continuation queries do not see another scope;
- downstream jobs inherit the completing lease's scope rather than rereading a
  mutable global;
- production config rejects a missing/blank Tender scope.

**Implementation child packets.**

1. **CH-2.1A expand/backfill:** create a migration from current head. Add nullable
   <code>queue_scope</code>, then backfill to production only after the preflight
   proves that classification. Add nonempty/non-null enforcement and an index
   beginning <code>(queue_scope, status, run_after)</code>.
2. **CH-2.1B scoped code:** consume the explicit
   <code>TENDER_QUEUE_SCOPE</code> contract created by CH-0.1. Centralize job
   creation through <code>jobs.enqueue</code>. Any exceptional
   constructor must require scope explicitly.
   Require scope on internal claim, stale recovery, progress, duplicate/barrier,
   and continuation helpers. Filter in SQL, never after fetching.
   Carry the claimed job's scope through continuation creation and all logs.
3. **CH-2.1C contract:** for rolling compatibility, the expand migration may
   temporarily provide a production server default. Remove it only after
   Section 3.5's rollback floor advances to a tested scope-aware prior SHA and
   rollback is rehearsed; then omission fails closed.

**Verification.**

    Set-Location backend
    uv run pytest tests/tender/test_queue_scope.py tests/tender/test_jobs.py tests/tender/test_worker_continuation.py -q
    uv run pytest tests/tender/test_migrations.py -m "not integration" -q

Against a disposable DB, run two real workers with different scopes and prove
they process only their own rows. Post-migration count must show no null,
blank, or unapproved scope.

**Observability.** Every worker start, claim, completion, sweep, queue-depth, and
oldest-age event includes scope and build SHA, never customer payload.

**Migration/rollout.** Drain workers, apply expand through CH-1.13, deploy all
producers/consumers, restart scoped workers, observe, advance/rehearse the
rollback floor, then remove the temporary DB default.

**Rollback.** Stop new workers before selecting old code. Keep the additive
column/default during the rollback window. Dropping it while multiple
environments share a database reintroduces the defect.

**Do not.** Do not blindly label mixed queued/running jobs production or allow a
settings fallback in production.

**Stop if.** A live actionable row cannot be classified, an old worker cannot
be drained, or a query chooses scope after row locking.

**Commit/evidence.** CH-2.1A, B, and C are separate release packets/evidence.
Evidence includes compatibility records, pre/post counts, and two-worker
results.

### CH-2.2 - Add Tender renewable leases and fenced publication

**Objective and risk.** Long Tender stages renew ownership; reclaim creates a
new fence; a stale worker cannot complete, fail, publish results, or create
continuations.

**Files/symbols.**

- <code>backend/tender/models.py::TenderJob</code>
- <code>backend/tender/services/jobs.py</code>
- <code>backend/tender/worker.py::run_once</code>,
  <code>run_worker_lane</code>, <code>run_sweeper</code>
- handler commits in ingestion/embedding and other Tender services
- configuration/deployment
- new Alembic revision; Tender job/worker/integration tests

**Lease contract.**

- add <code>heartbeat_at</code>, <code>lease_expires_at</code>, and UUID
  <code>lease_token</code>; retain <code>locked_by</code>;
- every claim mints a token and increments <code>attempts</code>;
- claim, heartbeat, complete, and fail carry
  <code>(job_id, queue_scope, worker_id, lease_token)</code>;
- suggested lease 120 seconds and heartbeat 40 seconds, adjusted only from
  measured event-loop/DB pauses;
- suggested stage deadline 30 minutes, adjusted after recording real p99;
- zero rows updated by heartbeat/publication means
  <code>LostTenderLease</code>.
- publication/failure fencing is one exact SQL rule: after stopping and awaiting
  heartbeat, begin a short transaction, lock the row
  <code>FOR UPDATE</code>, and require exact job ID, queue scope,
  <code>status = 'running'</code>, worker ID, lease token, and
  <code>lease_expires_at > clock_timestamp()</code>. No matching row means
  <code>LostTenderLease</code>. Hold that row lock through result/event/
  continuation publication and commit. Retry/failure transition uses the same
  predicate; an expired/lost owner abandons and never marks the job failed.

**Red tests.**

1. A healthy handler longer than the former ten-minute stale threshold is never
   requeued because heartbeat renews it.
2. Reclaim produces a different token.
3. Old owner cannot heartbeat, complete, fail, or commit result rows.
4. Crash/reclaim increments attempts and exhausts deterministically.
5. A handler deadline produces fenced failure/retry.
6. Heartbeat loss is observable and causes the worker to abandon publication.

**Implementation child packets.**

1. **CH-2.2A schema/DTO:** drain Tender workers and ensure no running rows
   before adding running-lease
   checks/indexes.
   Add fields/indexes and backfill non-running rows to null lease values.
   Return an immutable <code>TenderJobLease</code> DTO from claim; do not pass a
   mutable ORM object as authority.
2. **CH-2.2B claim/heartbeat:** claim queued or expired jobs with attempts
   remaining, mint token, set expiry,
   increment attempts, and commit immediately.
   Run heartbeat on a separate short-lived session; stop and await it before
   final publication.
   During the rollback window, claim/heartbeat dual-write existing
   <code>locked_by</code>/<code>locked_at</code>/status/attempt fields so the
   rollback SHA interprets every row. Heartbeat advances legacy
   <code>locked_at</code>; old and new sweepers are never active together.
3. **CH-2.2C fenced worker/sweeper:** replace detached-object
   completion/failure with conditional fenced queries.
   Sweep expired leases by scope/token/attempts. Mark exhausted jobs failed once;
   do not reset every old running row.
   Wrap each handler in an explicit stage deadline and propagate cancellation.
   Implement the exact locked predicate above for completion, failure, and retry.
   Remove internal commits on worker paths that would make a later fence
   meaningless. A handler may flush; the fenced publisher owns commit.
   Verify external writes use deterministic/idempotent keys and record any
    abandoned provider operation for reconciliation.

**Verification.**

    Set-Location backend
    uv run pytest tests/tender/test_jobs.py tests/tender/test_worker.py tests/tender/test_worker_telemetry.py -q
    uv run pytest tests/tender/test_worker_integration.py -m integration -q

Repeat the long-handler, kill/reclaim, and stale-token cases enough times to
exercise timing races. At most one committed result is allowed.

**Observability.** Emit lease age/renewal latency, lost-lease count, attempt,
deadline, reclaim, exhausted count, queue scope, worker/build, and job kind.
Customer payload and provider response stay out of logs.

**Migration/rollout.** Drain workers; expand schema; deploy new workers only;
remove obsolete stale-lock setting in the same release. Retain old lock columns
until the rollback window closes.

**Rollback.** Stop/drain new workers, verify legacy columns are current and the
release record declares the old SHA compatible, then select it while retaining
additive lease columns. Never run old and new sweepers together.

**Do not.** Do not treat <code>locked_at</code> as a renewable lease, heartbeat
through the work session, or let stale code mutate result tables before fencing.

**Stop if.** Workers cannot drain, maximum stage duration is unknown, a handler
commits internally, or an external publication is non-idempotent.

**Commit/evidence.** CH-2.2A, B, and C are separate implementation/evidence
pairs but form one undeployable parent until all pass.

### CH-2.3 - Make Tender completion and continuation atomic

**Objective and risk.** A crash cannot leave a completed Tender stage without
its required downstream job; concurrent final predecessors create exactly one
continuation.

**Files/symbols.**

- <code>backend/tender/services/jobs.py::complete</code>
- <code>backend/tender/services/continuations.py::after_job_complete</code> and
  enqueue helpers
- <code>backend/tender/worker.py::run_once</code>
- worker continuation/chain/concurrency tests

**Red tests.**

1. Raise after downstream enqueue but before commit: neither completion nor
   continuation persists.
2. Success uses one caller-owned publication commit.
3. Two last predecessor jobs complete concurrently: exactly one next job.
4. Fencing failure writes neither completion, telemetry, project event, nor
   continuation.
5. Readiness sees the current job's done state within the same transaction.

**Required continuation identity.** Before implementation, add an explicit
integer <code>pipeline_generation</code> to the comparison/jobs through an
expand migration. An automatic retry retains its generation/job identity. A
new user-requested reprocess increments the comparison generation under lock.
Every pipeline enqueue stores a globally unique
<code>deduplication_key</code>:

    <scope>:<comparison>:g<generation>:<target-kind>:<target-discriminator>:<quote-or-all>:<document-or-all>:<predecessor-kind>:g<predecessor-generation>

<code>target_discriminator</code> is mandatory and canonical; it carries the
batch/shard identity (including every silence batch) or a fixed <code>all</code>
sentinel. Use fixed sentinels for absent quote/document; never omit tuple fields.
Add a unique constraint on the stored key. Enumerate and test these edges:

- upload/process -> <code>ingest_document</code> per document;
- <code>ingest_document</code> -> <code>classify_document</code> per document;
- <code>classify_document</code> -> <code>extract_line_items</code> per document;
- <code>extract_line_items</code> -> <code>embed_items</code> per document;
- all embed/extract ready -> <code>generate_project_taxonomy</code> per
  comparison generation;
- taxonomy -> <code>map_items</code> per quote;
- all mapping ready -> <code>run_expectations</code>;
- expectations -> <code>infer_silence_batch</code> per quote/batch discriminator
  (and characterize any retained single <code>infer_silence</code> edge);
- no-silence/all-silence ready -> <code>run_analysis</code>;
- analysis -> <code>generate_flags</code>;
- flags/QA clear -> <code>assemble_report_draft</code>.

Classify generation changes before coding: initial process, accepted context/
selection/input change, manual quote retry, and manual comparison retry each
either retain the same logical job for a true technical retry or mint/increment
an explicit generation for new business work. A changed input/payload may never
reuse a completed key. Document each command's rule and test it. During the old
image window, new columns are nullable only for legacy rows, those rows receive
deterministic legacy generation/discriminator values on first touch/backfill,
and new code never emits a null key component.

If code discovery reveals another <code>TenderJob</code> constructor/enqueue,
the contract test fails until the edge and discriminator are added to this list.

**Implementation child packets.**

1. **CH-2.3A generation/deduplication:** implement the exact schema/key contract
   above for every producer. Use the unique constraint in addition to locking.
   A collision returns the existing logical job only when every identity field
   and payload hash matches; inconsistent payload under one key fails. Add edge
   inventory and collision/concurrency tests.
2. **CH-2.3B atomic publication:** remove internal commits from
   <code>jobs.complete</code> and continuation helpers; document caller
   ownership. After handler computation, stop heartbeat, verify/acquire the
   current fence,
    use CH-2.2's exact <code>FOR UPDATE</code> unexpired-lease predicate, hold
    the job lock, mark done, record result/telemetry/event, evaluate barriers under the
   existing domain lock, enqueue continuation, and commit once.
   On publication error, roll back all publication work. Use a separate session
   to record a fenced retry/failure only if the lease is still owned.
   Add deterministic barriers in a real Postgres integration test for the two
   concurrent predecessors.

**Verification.**

    Set-Location backend
    uv run pytest tests/tender/test_worker_continuation.py tests/tender/test_worker_chain.py tests/tender/test_worker.py -q
    uv run pytest tests/tender/test_worker_integration.py -m integration -q

Expected: exactly one commit boundary and one continuation; injected crash
leaves neither half.

**Observability.** One publication event reports transaction duration,
continuation kind/created-or-existing, and fence outcome.

**Migration/rollout/rollback.** CH-2.3A is the required expand migration and
CH-1.5 security-contract update. Backfill existing jobs with deterministic
legacy keys after the actionable-job preflight. CH-2.3B makes completion and
continuation atomic. Roll back worker/jobs/continuations together and retain the
additive schema.

**Do not.** Do not catch publication failure and mark the current job done in a
second transaction.

**Stop if.** Any invoked handler or event helper commits internally.

**Commit/evidence.** CH-2.3A and B are separate implementation/evidence pairs.
The parent is undeployable until both pass.

### CH-2.4 - Make agent admission, expiry reaping, and cancellation durable

**Objective and risk.** Capacity/thread conflicts return before quota or message
persistence; no request waits indefinitely inside SSE; expired turns cannot
strand a thread; cancellation is visible across API processes.

**Files/symbols.**

- <code>backend/app/database/agent_turn.py::AgentTurn</code>
- <code>backend/app/billing/usage.py::reserve_agent_turn</code>,
  <code>revoke_agent_turn</code>, new reaper
- <code>backend/app/agent/concurrency.py::AgentTurnRegistry</code>
- <code>backend/app/api/chat.py::post_agent_stream</code>,
  <code>post_agent_cancel</code>
- <code>backend/app/agent/pi_process.py::stream_pi_turn</code>
- new Alembic revision and DB concurrency tests

**Durable contract.**

- add <code>execution_scope</code> and require it;
- every authority lookup/count/mutation includes <code>execution_scope</code>:
  message/idempotency uniqueness and lookup, active thread uniqueness/lookup,
  global/per-user active counts, expiry reaper, revocation, and cancel;
- partial unique index on <code>(execution_scope, thread_id)</code> for active,
  non-null thread rows, plus the scoped idempotency constraint selected from the
  existing message-ID contract;
- index <code>(execution_scope, state, expires_at)</code>;
- one documented advisory-lock order for scope admission/reap, idempotency,
  thread uniqueness, capacity, and quota;
- DB authority is durable; local registry holds only local task/process handles.

**Red tests.**

- full capacity returns 429 plus <code>Retry-After</code>, creates no turn/user
  message, and consumes no quota;
- same active thread returns 409 before SSE;
- two concurrent admissions for one thread yield exactly one;
- expired row is reaped and stops blocking;
- same message ID retry reuses its row before capacity checks;
- cancellation from a separate registry/process revokes DB authority and ends
  stream within polling interval;
- concurrent reserve/cancel/reap meets a short lock-timeout without deadlock.

**Implementation child packets.**

1. **CH-2.4A durable admission:** preflight/revoke expired rows; add scope and
   partial index through an expand migration. Keep a temporary server default
   equal to the CH-0.1 production execution scope so the rollback SHA can insert
   rows during its declared compatibility window. Serialize reaping,
   idempotency, thread, capacity, and quota in one documented
   scoped admission transaction. Do not acquire user/thread locks in competing
   orders.
   Reject every unscoped lookup and prove a development ID cannot reuse, count,
   reap, revoke, or cancel a production-scoped turn with the same IDs.
   Check idempotent retry before capacity; check active thread and configured
   global/per-user capacity before insert.
   Move admission before message persistence and before returning
   <code>StreamingResponse</code>.
2. **CH-2.4B runtime coordination:** remove semaphore waiting from
   <code>turn_scope</code>. Local registration is
   fast and may still reject impossible duplicate local handles.
   Race Pi streaming with a lightweight DB revocation watcher. Same-process
   cancellation remains immediate; cross-process cancellation is bounded by
   polling interval.
   Revoke the admitted row if local process registration fails.
   Preserve current quota policy: admitted execution counts; rejected admission
   does not.
3. **CH-2.4C compatibility-default retirement:** after A/B are green, deploy a
   scope-aware intermediate staging SHA and make it the tested prior rollback
   candidate. Rehearse rollback to it, advance the release record's rollback
   floor, then add a contract migration/removal that drops the temporary server
   default and makes omitted <code>execution_scope</code> fail closed. Run old-
   below-floor insertion tests to prove such an image is no longer selectable,
   and rerun cross-scope admission/idempotency/reap/revoke/cancel tests. GATE-2
   cannot pass with the production default still present.

**Verification.**

    Set-Location backend
    uv run pytest tests/agent/test_concurrency.py tests/agent/test_agent_chat_api.py tests/billing/test_usage.py -q

Run the new two-connection integration tests on disposable Postgres. Assert no
semaphore wait, no duplicate active thread, and no capacity side effects.

**Observability.** Count admissions/rejections/reaps/revocations by safe reason
and scope; record admission latency and active count. Never log message body or
turn token.

**Migration/rollout.** A drains active turns, adds/backfills scope/default,
revokes expired, creates indexes, runs CH-1.5, then deploys A/B. Keep API at one
worker until cross-process tests pass. C uses the explicit intermediate
scope-aware rollback release and only then removes the temporary default.

**Rollback.** Stop agent traffic before selecting the release-record-approved old
code. Keep expanded schema/index/default. Restore traffic only with the old
single-process topology and verify the unique constraint/idempotent path; the
old image is not approved for horizontal API scaling.

**Do not.** Do not use an in-memory semaphore as global authority or wait for
capacity after opening SSE.

**Stop if.** Active turns cannot drain, lock order is undocumented, or rejection
leaves any turn/message/quota row.

**Commit/evidence.** CH-2.4A, B, and C are separate implementation/evidence
pairs. A/B deploy together; C records the intermediate rollback proof, floor
advance, absent default, and concurrency timelines.

### CH-2.5 - Make Stripe webhook state idempotent and monotonic

**Objective and risk.** Duplicate, retried, or reverse-ordered Stripe events
cannot repeat side effects or regress subscription/entitlement state; checkout
creation has an idempotency key.

**Files/symbols.**

- new <code>backend/app/database/stripe_webhook_event.py</code>
- <code>stripe_subscription.py</code>, model registration
- <code>backend/app/database/stripe_billing.py</code>
- <code>backend/app/billing/stripe_webhooks.py</code>
- <code>backend/app/api/billing.py</code>
- checkout-session creation path
- new Alembic revision and billing integration tests

Reference: [Stripe webhook delivery behavior](https://docs.stripe.com/webhooks).

**Schema/contract.**

- event ledger: unique event ID, event type, object ID, Stripe-created time,
  received/processed time, and safe outcome; no full payload;
- subscription: last event-created time, deterministic equal-time priority, and
  last event ID;
- deletion/cancellation outranks update/checkout at equal timestamp;
- current-object reconciliation is preferred where an event cannot safely
  determine current state;
- each user-initiated checkout operation has a client-generated operation UUID
  stored in a durable checkout-attempt row (or equivalent durable record) scoped
  to user/project/plan/purpose. Retries of that operation reuse one Stripe
  idempotency key; a deliberate later purchase has a new operation UUID and key.

**Red tests.**

1. Same verified event twice causes one transition.
2. Update at 200, delete at 300, stale update at 250 remains deleted.
3. Equal-time deletion cannot be overwritten.
4. Failure rolls back event claim and subscription change so retry succeeds.
5. Invalid signature writes no ledger row.
6. Retried checkout request creates/reuses one Stripe operation.
7. Two concurrent duplicate deliveries result in one processed outcome.
8. A second deliberate checkout with a new operation UUID creates a new session;
   replay/concurrency of either UUID never crosses attempts.

**Implementation child packets.**

1. **CH-2.5A ledger/order schema:** add migration/model/indexes; update/run the
   CH-1.5 table/grant/RLS contract; backfill subscription ordering fields null,
   meaning first verified event is accepted.
2. **CH-2.5B webhook transaction:** verify signature before parsing/logging
   identifiers. Validate event ID/created/type/object; insert with
   conflict-do-nothing. Apply subscription update only when ordering tuple is
   newer or current-object
   reconciliation confirms it.
   Mark event processed in the same DB transaction as state change.
   Return/log one of processed, duplicate, stale, ignored, or failed.
3. **CH-2.5C checkout idempotency:** validate/store the operation UUID, derive
   the provider key from the durable attempt identity, reuse its session while
   valid, and give a later explicit operation a new attempt. Define expiry and
   terminal states without deleting audit/idempotency history. Test replay,
   concurrency, and a second legitimate purchase.

**Verification.**

    Set-Location backend
    uv run pytest tests/billing/test_stripe_webhooks.py -q
    uv run pytest -m "not integration and not tender_eval" -q

Also run disposable-DB duplicate-concurrency and migration upgrade tests.

**Observability.** Log safe event type/action/age and correlation; hash or omit
Stripe/customer IDs and never store/log full payload.

**Migration/rollout.** Additive schema first, then code. Monitor stale/duplicate
rates and reconciliation errors.

**Rollback.** Roll back code before schema; retain ledger/columns until prior
image stability is confirmed. Dropping immediately discards replay protection.

**Do not.** Do not trust delivery order, acknowledge a failed transaction as
processed, or derive idempotency from current time.

**Stop if.** Ordering semantics or current-object reconciliation for a supported
event type is unresolved.

**Commit/evidence.** CH-2.5A, B, and C are separate implementation/evidence
pairs.

### CH-2.6 - Add durable Storage cleanup, upload compensation, and retention

**Objective and risk.** Database deletion and cleanup intent commit together;
Storage outages/process crashes cannot permanently orphan objects; staging
objects expire; destructive retention follows the signed matrix only.

**Files/symbols.**

- new <code>backend/app/database/storage_object_lifecycle.py</code> containing the
  authoritative <code>StorageObjectLifecycle</code> ownership/cleanup row
- new <code>backend/app/storage/cleanup_queue.py</code> and
  <code>cleanup_worker.py</code>
- model registration and new Alembic revision
- evidence/draft delete services and project route background tasks
- inbox staging/upload and Tender document upload paths
- deployment compose and Storage/retention tests

**Queue contract.** Internal table contains queue scope, bucket/key, action,
immutable generation ID, optional canonical owner kind/ID, caller-supplied unique
deduplication key, reason, due/run-after time, state, attempts, fenced lease
owner/token/expiry, safe last error, and timestamps. Freeze its state machine as
<code>pending -&gt; protected -&gt; delete_queued -&gt; deleting -&gt; done</code> for a
canonical object and <code>pending -&gt; deleting -&gt; done</code> for abandoned upload
compensation. Delete failure conditionally returns the same generation from
<code>deleting -&gt; delete_queued</code> for bounded retry or moves it to
<code>dead_letter</code>. Every canonical evidence/draft/file row stores the
generation ID as well as the immutable key; one generation cannot be published
by more than one canonical owner.
Bucket/key alone is not globally unique because a path may be reused.
Use the distinct <code>STORAGE_CLEANUP_QUEUE_SCOPE</code> from CH-0.1.

**Red tests.**

- DB deletion and cleanup intent commit/rollback together;
- Storage failure retries with bounded backoff;
- delete succeeded then worker died: retry treats absent as success;
- max attempts creates visible dead letter;
- analyze/upload creates delayed staging/compensation cleanup;
- DB persistence failure after upload eventually deletes the object;
- successful canonical persistence cancels compensation;
- deterministic claim -> canonical protect/cancel -> delete race leaves a valid
  final canonical object;
- logical deletion/overwrite atomically moves the exact old generation from
  <code>protected</code> to <code>delete_queued</code>, and a concurrent attempt to
  republish that generation fails before either DB publication or Storage delete;
- worker reference recheck finds an injected canonical reference, makes no
  Storage call, and dead-letters a visible <code>reference_conflict</code>;
- development worker cannot delete production-scoped objects;
- retention dry run never deletes and excludes rows younger than policy.

**Implementation child packets.**

1. **CH-2.6A lifecycle queue/worker:** add the authoritative lifecycle table,
   scoped fenced claim/retry/dead-letter,
   concurrency one, health/metrics, and a dedicated cleanup service using the
   backend image. Update/run CH-1.5's table/grant/RLS contract.
2. **CH-2.6B upload/staging compensation:** create a unique storage-object
   generation/key and durable <code>pending</code> claim before upload. Its
   <code>not_before</code> is later than twice the bounded upload+persistence
   deadline and never less than 15 minutes. Canonical DB persistence
   conditionally changes <code>pending -> protected</code> in its transaction.
   The cleanup worker conditionally changes an expired
   <code>pending -> deleting</code> under its fence, commits, then deletes.
   Protection cannot succeed after <code>deleting</code>; if cleanup wins, the
   canonical DB transaction must not publish that key and the upload path
   retries with a fresh generation/key. If protection wins, worker transition
   fails and the object survives. A crash after upload leaves a pending claim.
   Create a 24-hour staging claim and advance it after split/abandon. Freeze the
   compensation branch as <code>pending -&gt; deleting -&gt; done</code>. Delete failure
   conditionally returns the same generation to scheduled retry or exhausts to
   dead letter; <code>protected</code> is never claimable and remains until its
   owning canonical record is transactionally retired under CH-2.6C/retention
   policy.
3. **CH-2.6C DB deletion and overwrite conversion:** first inventory and convert
   every upload/replace/overwrite path to CH-2.6B's immutable generation keys;
   delayed deletion must never target a key that can be reused. Every canonical
   row stores the lifecycle generation ID. In the same short transaction as
   logical evidence/draft/file deletion or overwrite, lock that exact lifecycle
   row, prove the canonical owner still references it, retire/switch the canonical
   reference, and transition <code>protected -&gt; delete_queued</code> with reason and
   due time. The worker may claim only <code>pending</code> compensation or
   <code>delete_queued</code>, transitioning to <code>deleting</code> under a fresh
   fence. Immediately before the remote delete, it locks/rechecks the generation
   and proves no canonical FK/reference remains. Any reference or generation/key
   mismatch makes no Storage call and moves to visible
   <code>dead_letter/reference_conflict</code>. All publication helpers lock the
   same row and may publish only by <code>pending -&gt; protected</code>, so nothing can
   acquire a reference after deletion is queued. After absent/successful remote
   delete, the current fence moves <code>deleting -&gt; done</code>. Remove
   service-internal commits and FastAPI best-effort deletion. B and C may deploy
   atomically, but C must never deploy before generation conversion is green.
4. **CH-2.6D retention:** enumerate only approved signed policy classes. Default
   to dry-run for at least one production review cycle; require human approval
   of counts/samples before destructive mode. Add orphan reconciliation both
   Storage-to-DB and DB-to-Storage.

Each child packet is a separate small-model session/commit. Do not begin B-D
until A is green, and execute/deploy B before or atomically with C.

**Verification.**

    Set-Location backend
    uv run pytest tests/storage tests/test_storage_resilience.py tests/inbox/test_upload.py tests/inbox/test_split_service.py -q
    uv run pytest tests/tender/test_ingestion.py tests/tender/test_api_qa.py -q
    uv run pytest tests/tender/test_migrations.py -m "not integration" -q

Use fault injection to prove every simulated failure leaves a queued,
completed, or dead-letter row, never silent orphan state. Dry-run and destructive
candidate sets must match exactly before approval. Add deterministic barriers
for both compensation-race winners; the final canonical DB row must always
reference an existing protected object.

**Observability.** Queue depth, oldest due age, attempts, dead letters,
scope/build, and reconciliation totals. Record run ID/reason/operator without
object content or signed URL.

**Migration/rollout.** Deploy table, then worker, then producers. Retention
consumer stays dry-run until separately approved.

**Rollback.** First stop upload/overwrite/delete admission and producers. Classify
every pending/running/retry/dead-letter cleanup row: finish safe generation-key
deletes, or quarantine rows whose target could be reused by the rollback SHA.
Prove no delayed row targets a key that the old producer can create/reuse; if
that cannot be proven, retain the generation-key producer compatibility instead
of selecting old producers. Only after the queue/keys reconcile may the old
producer code resume. Keep worker/table for any compatible remainder and never
drop a nonempty queue. Purged bytes are recoverable only through verified
in-policy backup.

**Do not.** Do not rely on FastAPI background tasks, make key the only
deduplication identity, or enable destructive retention by default.

**Stop if.** A delete commits before enqueue, retention approval/restore is
missing, candidate counts are surprising, or dead letters have no operator.

**Commit/evidence.** Four child implementation/evidence pairs and
queue/fault/race/dry-run evidence.

### CH-2.7 - Prove and enforce one core-workflow lock order

**Objective and risk.** Resolve the architecture document's known
projects-row/FK/<code>FOR UPDATE</code> concurrent-launch deadlock and prevent
future lock-order inversion.

**Files/symbols.**

- <code>backend/app/workflows/runs.py</code>
- <code>backend/app/projects/locks.py</code>
- workflow launch/cancel/publish/reaper helpers
- <code>backend/tests/stage5/test_workflow_runs_integration.py</code> or a new
  focused DB concurrency test
- <code>docs/architecture.md</code>

**Preconditions.** CH-2.4's lock-order lessons; a disposable real Postgres
database with short lock/deadlock timeouts. This task does not wait for CH-5.4
CI automation.

**Red test/baseline.**

1. Use two independent connections and deterministic barriers to interleave
   launch, claim/publish, cancellation, and expired-run finalization.
2. Reproduce the documented deadlock or lock-timeout and capture only sanitized
   SQL operation names/timing.
3. Inventory every transaction that locks a project and workflow run.

**Implementation.**

1. Write the canonical rule: when both are needed, lock the project row before
   the workflow-run row; never lock a run then wait for its project.
2. Refactor candidate discovery to read IDs without retaining a conflicting row
   lock, then acquire locks in canonical order and revalidate state.
3. Keep claim's single-row <code>SKIP LOCKED</code> transaction short and
   committed before later project publication.
4. Add bounded <code>lock_timeout</code> behavior and safe retry only around
   idempotent transaction boundaries.
5. Run concurrent launch/publish/cancel/reaper test repeatedly.
6. Update architecture only after the test proves the issue resolved.

**Verification.** No deadlock/timeout across repeated deterministic schedules;
exactly one logical run/publication; event sequence remains monotonic.

**Observability.** Record safe transaction class, lock wait duration, retry
count, and correlation. Do not log SQL parameters/customer identifiers.

**Migration/rollback.** Normally code/test only. If an index is proposed, require
an <code>EXPLAIN</code>-based reason and separate migration.

**Do not.** Do not solve by serializing all projects globally or adding broad
automatic retries.

**Stop if.** The documented race cannot be reproduced under barriers. Record
the inventory/result and ask for maintainer review rather than changing locks
speculatively.

**Commit/evidence.** One lock-order/test commit and updated architecture note.

## 11. Stage 3 - resource, capacity, and operational hardening

### CH-3.0 - Approve observability destinations, ownership, and cost ceiling

**Objective and risk.** Choose the operational sinks and humans before code
wires telemetry or claims alerts work. Data residency, retention, credential
ownership, and cost must be explicit.

**Files/artifacts.**

- new <code>docs/operations/observability-decision.md</code>
- incident/on-call contact and escalation runbook
- approved provider/project configuration evidence
- no application code in this decision task

**Red baseline.** Record where application logs, metrics, errors, uptime/TLS,
host/container, DB/pooler, backup, and alert delivery currently go. “Docker
console only,” unknown retention, or no named recipient is a failed baseline.

**Implementation/decision.**

1. Select the log, metric, exception/error, public uptime/TLS, host/container,
   DB/pooler, and alert destinations. One product may cover several roles, but
   each role must be named.
2. Record region/data residency, customer-data policy, retention, access roles,
   credential owner/rotation, monthly cost ceiling, export/exit path, and
   service availability.
3. Name primary and backup operator, escalation channel, quiet-hours behavior,
   and a non-customer synthetic test-alert route.
4. Classify allowed fields and forbidden content consistently with CH-0.3.
5. Define initial SLO/error-budget review owner and incident severity mapping.
6. Obtain maintainer/operator approval. This task chooses a design; CH-3.2/3.3
   implement and prove it.

**Verification.** Every telemetry class has a sink, retention, owner, and test
route; approved credentials can be stored through the deployment secret
mechanism without exposing them; projected cost is inside ceiling.

**Observability/migration/rollback.** Decision only, no schema. A provider
selection can be changed through a new decision/review; do not silently swap.

**Do not.** Do not install an SDK, send repo/customer data during evaluation, or
assume an inbox/channel is monitored.

**Stop if.** Data residency, retention, cost, credentials, or primary/backup
ownership is unapproved.

**Commit/evidence.** One approved decision/runbook coordination commit; evidence
contains no endpoint secret.

### CH-3.1 - Budget database pools/timeouts and implement real readiness

**Objective and risk.** API and workers cannot collectively exhaust Supabase
connections; long/idle transactions are bounded; liveness stays cheap while
readiness proves DB and schema compatibility.

**Files/symbols.**

- <code>backend/app/config.py::Settings</code>
- <code>backend/app/database/session.py::get_engine</code>
- <code>backend/app/main.py</code>; new focused health module if useful
- deployment compose/examples
- new pool/readiness tests

**Preconditions.** Obtain provider session-pooler ceiling and current peak.
Reserve connections for PostgREST/dashboard/migration/admin and for two
application versions during rollout.

**Red tests/baseline.**

- engine receives configured pool size, overflow, acquisition timeout, recycle,
  connect, statement, lock, and idle-in-transaction timeouts;
- <code>/health</code> succeeds without DB and returns environment/SHA;
- <code>/ready</code> returns 503 on DB timeout, absent migration table, or
  a revision/capability outside that build's embedded compatibility spec, and never
  calls OpenAI/Auth/Storage;
- an old and new build both remain ready across an approved expand revision;
  the old build becomes incompatible only after the rollback floor advances;
- compose traffic/promotion checks use readiness.

**Implementation child packets.**

1. **CH-3.1A pool/timeouts:** calculate
   <code>sum(replicas * (pool_size + max_overflow))</code> for API, Tender,
   workflow, cleanup, an approved parser worker, migrations, and overlapping
   release. Keep the approved app allocation below provider ceiling with
   explicit reserve.
   Start only if the ceiling supports the proposed one-deployment maximum:
   API 5+2, Tender 4+1, workflow 2+1, cleanup 1+0, parser 1+0 (17 total).
   Reduce from
   measurement if two-version rollout plus reserve is unsafe.
   Add validated settings and role-specific compose overrides.
   Pass pool settings and psycopg-compatible connection/session timeouts to
   <code>create_async_engine</code>; prove options in a real connection test.
   Add pool checkout/checkin/wait/timeout telemetry without DSNs.
2. **CH-3.1B compatibility-aware readiness:** keep
   <code>/health</code> dependency-free. Add bounded
   <code>/ready</code> with <code>SELECT 1</code>, current revision, and required
   schema-capability probes. Read the build's accepted revision set/capabilities
   from Section 3.5's embedded immutable specification. Do not require exact head here:
   CH-1.13's release step separately requires target head.
   Add the readiness/SHA check to CH-1.8's validator as a required check and
   prove nonzero failure.
   Use readiness for deployment promotion/traffic; use liveness for process
   restart.

**Verification.**

    Set-Location backend
    uv run pytest tests/database/test_pool_configuration.py tests/test_readiness.py tests/test_main_lifespan.py -q
    uv run pytest -m "not integration and not tender_eval" -q

In staging, run all service roles at target concurrency. Require zero pool
timeouts, pool wait p95 below 100 ms, no idle transaction beyond configured
timeout, and total connections within formula.

**Observability.** Pool size/in-use/overflow/wait/timeout and readiness reason
class. Never log DSN.

**Migration/rollout.** Configuration/code only. Deploy compatibility-aware
health before switching compose checks. Every expand/contract release updates
the embedded accepted-set/capability specification and rehearses the overlap.

**Rollback.** Revert pool values/compose together and select prior image if
readiness is wrong. Keep diagnostic endpoints if compatible.

**Do not.** Do not guess the provider ceiling, use the transaction pooler for
Alembic, or make readiness call external providers.

**Stop if.** Ceiling is unknown, two-version formula exceeds allocation, or a
timeout would be chosen without measuring legitimate slow work.

**Commit/evidence.** CH-3.1A and B are separate implementation/evidence pairs.
Evidence includes formula, provider limit, <code>pg_stat_activity</code>,
compatibility matrix, and validator/readiness failure probes.

### CH-3.2 - Add worker heartbeat, queue health, and real alert delivery

**Objective and risk.** A running-but-stuck worker or growing queue is detected
before customer reports.

**Files/symbols.**

- new internal <code>service_heartbeats</code> model/migration
- new <code>backend/app/operations/heartbeat.py</code> and healthcheck CLI
- Tender, core workflow, and cleanup worker loops
- compose healthchecks and worker runbooks

**Red tests.** Tender has no healthcheck; core healthcheck proves only a
separate DB query rather than loop progress; repeated worker errors can be
caught forever while container remains healthy.

**Implementation child packets.**

1. **CH-3.2A heartbeat schema/writers:** add an internal table keyed by service,
   instance, environment/scope with build SHA and last-seen time. Update/run
   CH-1.5's table/grant/RLS contract. Each main polling loop upserts progress
   heartbeat independently of customer
   jobs.
2. **CH-3.2B healthcheck/alerts:** healthcheck CLI verifies fresh heartbeat,
   expected scope/SHA, and nothing downstream-latency-dependent. Add Docker
   healthchecks for every worker. Queue age, recent retry/failure rate, and dead
   letters are alert conditions only; they must not mark a progressing worker
   unhealthy and trigger a restart storm.
   Emit periodic structured queue snapshots.
   Begin with: heartbeat older than 60 seconds critical; core queue older than
   120 seconds warning; Tender older than 5 minutes warning/15 minutes critical;
   retry exhaustion/dead letter critical. Tune only with evidence.
   Configure CH-3.0's approved destination, owner, escalation, and runbook link.
   Send a real test notification and recovery.

**Verification.** Stop each worker and break a test DB credential; alert must
arrive within two minutes. An idle healthy worker stays healthy. Alert contains
service/scope/SHA/age/runbook but no customer data.

**Observability/migration/rollout.** Additive internal table. Deploy heartbeat
writers, then healthchecks/alerts. Include heartbeat cleanup/retention.

**Rollback.** Revert healthcheck config/writers while retaining harmless rows.

**Do not.** Do not equate process existence or a separate DB query with loop
health.

**Stop if.** No named recipient receives the actual test alert.

**Commit/evidence.** CH-3.2A and B are separate implementation/evidence pairs.
Alert and recovery receipts are required evidence.

### CH-3.3 - Add structured correlation plus application, host, and DB monitoring

**Objective and risk.** Operators can trace a failing request, turn, tool, job,
provider call, and build without exposing customer content or using
high-cardinality metric labels.

**Files/symbols.**

- <code>backend/app/logging.py</code> and CH-0.3 redactor
- <code>backend/app/main.py</code> request middleware/lifespan
- new focused context/event helpers if they reduce caller complexity
- API/worker/tool/provider seams
- deployment logging/monitoring configuration and incident runbook

**Precondition.** Use the CH-3.0-approved destinations/owners. Do not add an
observability SDK by default; if selected, justify maintenance/transitive
footprint.

**Red tests/baseline.** Production logs are not consistently JSON; exception
paths may omit completion; correlation does not span all work types. Capture
current ability to answer: which SHA, route/job/turn, duration, outcome, and
dependency caused an incident?

**Implementation child packets.**

1. **CH-3.3A event/context schema:** use JSON rendering outside development and
   readable console locally. Validate/generate request ID; bind normalized
   route, method, status, duration,
   environment, and SHA. Emit completion from <code>finally</code>.
   Apply CH-0.3 redaction before rendering/sending.
2. **CH-3.3B application correlation and metrics:** propagate safe correlation
   IDs through agent turn, MCP call, core/Tender/parser/cleanup job,
   Storage cleanup, Stripe processing, and external client adapters.
   Define stable low-cardinality events for HTTP/SSE, agent admission and first
   frame, tool denials, DB pool, queue/lease, external latency/status, upload
   rejection/bytes, cleanup/dead letter, and webhook outcomes. IDs may be
   searchable log fields but never metric labels.
3. **CH-3.3C host/container monitoring:** implement public uptime, TLS expiry,
   restart/OOM, CPU/RSS, disk/inodes, volume/workspace/Storage growth, and Docker/
   host capacity collection with safe labels and a synthetic source test.
4. **CH-3.3D DB/pooler monitoring:** implement DB/pooler utilization, database
   size, backup age, long/idle transactions, lock waits/deadlocks, autovacuum/
   bloat indicators, and normalized slow-query fingerprints. Use read-only
   monitoring credentials and prove collection cannot expose SQL parameters.
5. **CH-3.3E dashboards/alerts/runbooks:** build dashboards and alerts from the
   selected sinks. Add named primary/backup runbooks and test each critical
   delivery path.

**Verification/thresholds.**

- every production application line parses as JSON;
- request start/error/completion share correlation and SHA;
- synthetic end-to-end turn links request, turn, selected tools, Pi process,
  and completion without prompt/token;
- liveness p95 below 50 ms; readiness returns within two seconds;
- secret/header/body canaries absent;
- a real synthetic application, TLS/uptime, container, disk, DB lock/pooler, and
  backup-age alert is received and acknowledged or safely simulated at its
  approved source with end-to-end delivery.

**Observability.** This task creates the observability contract. Retain safe
correlation examples, metric/dashboard definitions, alert test receipts, and
cardinality checks by candidate SHA. Alert evaluation and delivery latency are
themselves measured.

**Migration/rollout/rollback.** No schema unless the selected telemetry design
explicitly requires it. Roll out event schema before dashboards/alerts. Revert a
broken sink without disabling local structured logs/redaction.

**Do not.** Do not log bodies, prompts, document names/content, auth headers,
signed URLs, raw query strings, DSNs, or unbounded exception/provider payloads.

**Stop if.** Data residency/retention for the selected sink is unapproved or no
operator owns alerts.

**Commit/evidence.** CH-3.3A through E are separate implementation/evidence
pairs. Evidence includes sanitized trace, dashboards, and alert receipts.

### CH-3.4 - Bound uploads, PDFs, downloads, and staging work

**Objective and risk.** Authenticated users cannot exhaust API memory, parser
CPU, Storage, or the sole event loop with oversized/batched/malicious files;
normal downloads do not buffer entire objects in the API.

**Files/symbols.**

- <code>backend/app/config.py</code>, env examples/compose/Nginx limit
- new <code>backend/app/uploads/limits.py</code>
- project inbox upload/analyze/download/export routes
- inbox validation and split service
- Tender quote upload/storage
- frontend upload/analyze API error handling if response contracts change
- new upload/download/parser tests

**Implementation child packets.** Execute CH-3.4A, then B, then C. Each child
uses the detailed ordered steps below and keeps the parent in progress.

**Required child packet CH-3.4A - HTTP/storage boundary.**

1. Add validated per-file, aggregate, count, page, chunk, signed-TTL, and active
   parser settings using Section 6 starting defaults.
2. Write <code>read_upload_limited</code> using 1 MiB maximum chunks and stop at
   limit plus one after enforcing limits at the ASGI multipart parser seam.
   Configure bounded spool/temp directory, per-part and request limits, and
   reject/abort while streaming before Starlette can spool an unbounded request.
   Process a batch one file at a time; never retain all file bytes simultaneously
   and clean every bounded spool file on success, rejection, disconnect, or
   cancellation.
3. Reject too many files before reading. Track aggregate while reading; if a
   later file exceeds it, schedule cleanup for earlier objects through CH-2.6.
4. Validate normalized filename, extension, declared type, magic bytes, empty
   content, path separators, control characters, and header injection.
5. Require active entitlement for analyze as well as upload.
6. Authorize download ownership, then issue a 60-second signed redirect with
   private/no-store and no-referrer policy. Never implement
   <code>StreamingResponse(iter([full_bytes]))</code>.
7. Cached exports redirect similarly. Bound the one-time render and cache it.
8. Align reverse-proxy request size slightly above the approved multipart
   aggregate, while application limits remain authoritative.

**Required child packet CH-3.4B - dedicated parser queue/worker.**

The architecture decision is made here: untrusted PDF analyze/split does not run
inside the API, a thread, Tender, or the core-workflow worker.

1. Benchmark the approved maximum plus malformed/compressed/image-heavy corpus
   to set worker memory/CPU/deadline, but not to reopen the isolation decision.
2. Add <code>backend/app/database/parser_job.py</code> and
   <code>backend/app/parsing/jobs.py</code>,
   <code>worker.py</code>, and <code>runner.py</code>. The queue owns
   <code>parser_jobs</code>, uses explicit <code>PARSER_QUEUE_SCOPE</code>,
   renewable lease/token fencing, idempotency, attempts/backoff, and the exact
   transition table: <code>queued -> running</code> under scoped SKIP LOCKED
   claim/token; running heartbeat extends only its current token; unexpired
   current token may publish <code>running -> done</code>; retryable failure or
   expired reclaim goes to <code>queued</code> with bounded run-after/attempts;
   exhausted goes to <code>failed</code>; queued cancellation goes directly to
   <code>cancelled</code>; running cancellation records request and the current
   fenced owner terminates child then publishes cancelled; a stale token cannot
   transition anything. Expired/reclaimed running work with durable
   <code>cancel_requested_at</code> transitions to <code>cancelled</code> without
   requeueing or spawning a child; every claim rechecks cancellation under its
   row lock. Add owner-crash-after-cancel-request-before-publication coverage.
   Use CH-2.2's exact locked, unexpired publication
   predicate and CH-3.2 heartbeat/alert contract. Update/run CH-1.5's
   table/grant/RLS contract.
3. The API stages the bounded object through CH-2.6 and enqueues only IDs/keys,
   never bytes. The parser worker downloads to a private bounded temp path.
4. <code>runner.py</code> is a child process with no DB/service credentials. It
   performs magic/page/decompression/image checks, inspect/detect/plan or split,
   and writes a bounded result file. The worker terminates then kills it at the
   hard deadline; child exit/signal/OOM cannot crash the API.
5. The worker publishes the result only under the current fence, emits the
   project event, and advances staging cleanup. Deterministic output/storage
   keys make retry safe.
6. Add <code>sitewise-parser-worker</code>, concurrency one initially, explicit
   CPU/memory/tmpfs limit, health/heartbeat, stop grace, and minimal secrets.

**Required child packet CH-3.4C - asynchronous API/frontend contract.**

1. Analyze and split return <code>202</code> with job ID and owned status URL.
   Add an owner-authorized bounded status/result/cancel endpoint.
2. Frontend displays queued/analyzing/splitting/progress/failure/cancel states.
   Owned bounded status polling is authoritative and resumes after reload;
   project events are optional invalidation hints until CH-4.1 later bounds that
   scheduler.
3. Failure copy is safe and retry reuses the same input generation unless the
   user explicitly uploads a new file.
4. Keep a legacy adapter for the declared rollback SPA during the compatibility
   window. It enqueues the same durable parser job and may wait only for a
   measured bounded compatibility timeout to return the old response shape; if
   still running, return the documented retryable legacy error without executing
   parsing in the API. Meter/rate-limit and rollback-test it. Remove it only after
   the rollback floor advances.

Execute CH-3.4A, then B, then C as separate sessions. Keep the parent in
progress and do not deploy the new backend contract without its frontend.

**Red tests.**

- exact limit succeeds; one byte over returns 413 before Storage/parser;
- count/aggregate fail with stable JSON and cleanup;
- empty/mismatch/magic invalid returns 400/415;
- 501-page fixture rejects before plan/render;
- analyze/split API returns 202 quickly and an event-loop sentinel progresses;
- parser child timeout/kill, worker crash/reclaim, stale fence, and process OOM
  produce no API crash or duplicate result;
- crash after durable parser cancel request cannot requeue/execute and finishes
  cancelled on reclaim;
- dev parser worker cannot claim production;
- concurrency overflow returns 429 plus <code>Retry-After</code>;
- signed download path never calls byte-buffering downloader;
- filename cannot alter key/header;
- 20 concurrent rejects do not grow RSS with body size.

**Verification.**

    Set-Location backend
    uv run pytest tests/uploads tests/inbox/test_upload.py tests/inbox/test_split_service.py tests/inbox/test_split_endpoints.py -q
    uv run pytest tests/tender/test_api_qa.py tests/tender/test_ingestion.py -q
    uv run pytest -m "not integration and not tender_eval" -q

Run adversarial/maximum fixtures in the production container. Peak RSS retains
at least 25% host/container headroom; overload has controlled 413/415/429; API
event loop remains responsive; parser child deadline and lease recovery pass.

**Observability.** Accepted/rejected size bucket, reason, route, parser
duration/RSS/deadline, active count, cleanup ID. No filename/content/signed URL.

**Migration/rollout.** CH-3.4B has an expand migration/security-contract update.
Deploy queue/worker and versioned backend, then frontend 202 behavior as one
compatible release; only then reduce Nginx limit. Keep legacy route solely for
the release record's rollback floor.

**Rollback.** Limits can be raised through reviewed config. Signed redirects
may roll back independently if content-disposition behavior fails. Do not
restore unbounded reads.

**Do not.** Do not trust MIME alone, read without a size sentinel, claim thread
offload is process isolation, import Tender from core parsing, attach parsing to
the core workflow worker, or expose a queue without renewable lease/fencing.

**Stop if.** Product limits are unapproved, edge is smaller/unknown, Supabase
client cannot make a safe filename-preserving signed URL, or adversarial parser
RSS cannot be bounded. For signed-URL failure, implement authenticated upstream
chunk streaming rather than full buffering.

**Commit/evidence.** CH-3.4A, B, and C are separate implementation/evidence
pairs. Evidence includes limit matrix, adversarial RSS/child-kill/lease/event
traces, 202/reload behavior, and signed-header tests.

### CH-3.5 - Remove DB sessions and transactions from external waits

**Objective and risk.** Tender and core workflow lanes hold DB connections only
while reading immutable input or publishing fenced output, not during
OpenAI/OCR/Storage/network latency.

**Files/symbols.**

- <code>backend/tender/worker.py</code>
- Tender classification, extraction, mapping, embedding services
- <code>backend/app/workflows/worker.py</code> and highest-duration workflow
  implementations
- DB session/pool instrumentation tests

**Required completion matrix.** Before the first refactor, enumerate every seam
that can await external I/O while a database session could be live: every Tender
handler; every core workflow dispatch path; Stripe checkout/portal and any
provider reconciliation; uploads/downloads/exports and Storage calls; MCP tools
that call providers or Storage; parser and cleanup workers. Record owner,
read/compute/publish boundary, test node, and disposition. CH-3.5 cannot complete
with an unknown/unreviewed row. A row may be documented no-change only when
instrumentation proves no checked-out connection and no active transaction
during the wait.

**Red baseline/tests.**

- block a fake LLM/network call and assert no work-session connection remains
  checked out;
- mapping loads existing mappings in a bounded query, not per line;
- fenced publication rejects lost lease and preserves human-protected mappings;
- current Tender golden/eval outputs and deterministic arithmetic are unchanged;
- record transaction/check-out durations for each stage.

**Implementation child packets.**

1. **CH-3.5A contract/instrumentation/matrix:** define immutable input/result
   DTOs, checkout/transaction timing, and freeze the complete seam matrix. No
   behavior movement yet.
2. **CH-3.5B classification/extraction:** short read transaction, close session,
   external compute, short fenced publication/continuation transaction.
3. **CH-3.5C all remaining Tender handlers:** start with mapping/embedding:
   batch-load existing/human mappings, perform model work session-free, then
   recheck protected rows and publish under fence. Defer delete/write until
   publication. Convert every other Tender matrix row before closing C.
4. **CH-3.5D core workflows:** rank every dispatch path by measured checkout time and convert
   one at a time to the same read/compute/publish shape. Preserve the explicitly
   documented non-transactional Storage-move semantics and add reconciliation
   rather than pretending Storage is transactional.
5. **CH-3.5E billing and API file/export seams:** convert Stripe checkout/portal,
   provider reconciliation, upload/download/export, and API Storage waits.
6. **CH-3.5F MCP provider/Storage seams:** convert every matrixed MCP tool that
   calls a provider or Storage while preserving CH-1 authorization boundaries.
7. **CH-3.5G parser/cleanup:** prove and, where needed, convert the dedicated
   parser and cleanup workers. Do not close the parent after only the named
   Tender examples and one core path.

Keep heartbeat active during compute. One child packet/commit per model stage;
run Tender eval after each prompt/model-affecting seam even when prompts are
unchanged.

**Verification.**

    Set-Location backend
    uv run pytest tests/tender/test_classification.py tests/tender/test_extraction_handler.py tests/tender/test_mapping_parallel.py tests/tender/test_worker.py -q
    uv run pytest tests/tender -m "not integration and not tender_eval" -q

Run approved Tender eval/speed gate and focused owner tests after each child.
Fake external waits must show zero checked-out connections and zero active
transactions, not merely an absent session variable. Every completion-matrix row
must link a passing test/trace.

**Observability.** Read/compute/publish durations, checkout duration, query
count, fence loss, stage/kind, model/provider usage and cost without inputs.

**Migration/rollback.** Normally none. Per-stage commits allow selective
rollback; keep DTO/interface tests.

**Do not.** Do not pass ORM objects across closed sessions, commit from compute
helpers, or alter Tender arithmetic/prompts/taxonomy without eval.

**Stop if.** Golden/eval metrics regress, human mappings can be overwritten, or
any handler commits before final fenced publication.

**Commit/evidence.** CH-3.5A through G are separate implementation/evidence
pairs with before/after pool/query/eval data and a zero-unknown completion matrix.

### CH-3.6 - Reuse external clients with explicit deadlines and retry policy

**Objective and risk.** OpenAI, HTTP, Auth, search, embedding, and Storage
clients are constructed once per process/worker lifetime, closed cleanly, and
cannot wait/retry beyond the owning request or renewable lease.

**Files/symbols.**

- repeated <code>AsyncOpenAI</code>/<code>httpx</code>/Supabase construction in
  Tender LLM/services, retrieval embedding, thread titles, auth dependencies,
  web research, and DB Supabase helpers
- FastAPI lifespan/dependencies
- Tender/core worker resource initialization
- configuration and timeout/retry tests

**Red tests/baseline.**

- count constructors over multiple calls and show repeated clients;
- each adapter receives connect/read/write/pool or SDK deadline settings;
- clients close once at lifespan shutdown;
- request cancellation reaches provider call;
- retry count/backoff stays within caller deadline/lease;
- non-idempotent writes/stream starts are not blindly retried.

**Implementation child packets.**

1. **CH-3.6A lifecycle/deadline foundation:** inventory each client, operation
   idempotency, current SDK retry behavior, and
   owning deadline.
   Add small process-lifetime resource containers: FastAPI app-state resources
   and <code>TenderWorkerResources</code>/<code>WorkflowWorkerResources</code>.
   Inject clients into services; do not create a service-locator global.
   Define explicit connection/read/write/pool/overall deadline and retry-budget
   configuration.
2. **CH-3.6B Tender adapters:** inject worker resources and apply the policy to
   Tender OpenAI/embedding/ODL/Storage operations. Worker
   operations must finish with margin before stage deadline; request calls
   before request/agent timeout.
3. **CH-3.6C API auth/Supabase/Storage adapters:** migrate authentication
   dependencies and API-facing Supabase/Storage operations; preserve signed-URL
   and ownership semantics.
4. **CH-3.6D retrieval/title/web/embedding adapters:** migrate retrieval
   embeddings, thread-title generation, and web-research/search HTTP clients.
5. **CH-3.6E core-workflow provider adapters:** migrate every core workflow
   provider and its Storage/reconciliation seam.

For C-E, use bounded exponential backoff with jitter only for transient,
idempotent/reconciled operations. Honor provider <code>Retry-After</code>.
Disable stacked retries across wrapper and SDK; one layer owns the budget.
Close async/sync resources at lifespan/worker shutdown and test cancellation.
Preserve deterministic client fakes in tests.

**Verification.** Focused adapter/lifespan tests plus full offline suite. Under a
faulting fake, elapsed time and attempt count must stay inside configured
budget; shutdown leaves no unclosed-client warning.

**Observability.** Provider/operation/status class, attempts, duration,
timeout/cancel, token/cost where supported. No prompt/request/response body.

**Migration/rollback.** Code/config only. Roll back one adapter at a time while
retaining explicit timeouts.

**Do not.** Do not use an unclosed module singleton, retry non-idempotent writes
without key/reconciliation, or let nested retry policies multiply.

**Stop if.** SDK timeout/retry semantics are uncertain; inspect the pinned
version's primary documentation/source and add a characterization test.

**Commit/evidence.** CH-3.6A through E are separate implementation/evidence
pairs with constructor/deadline results.

### CH-3.7 - Enforce overload and active-work admission

**Objective and risk.** Expensive traffic fails quickly and predictably before
large memory, queue, DB, or provider spend. Limits are meaningful for the
current process topology and do not trust spoofed client IPs.

**Files/symbols.**

- <code>backend/app/api/chat.py</code>
- project upload/analyze/export/search routes
- Tender processing routes/jobs
- new <code>backend/tender/models.py::TenderPipelineAdmission</code> and Alembic
  migration; do not reuse <code>TenderComparison.status</code> or one row per
  <code>TenderJob</code>
- configuration and stable API error schemas
- <code>deploy/nginx/sitewise.conf</code> and trusted-proxy setup
- concurrency/rate-limit tests

**Red tests.**

- agent per-thread/user/global caps reject before turn/message/quota;
- one active Tender process/comparison and approved per-user cap;
- parser/upload CPU concurrency rejects before parse;
- route request/result bounds prevent unbounded export/search work;
- burst limit returns 429 plus <code>Retry-After</code> and later recovers;
- spoofed forwarding headers do not bypass or frame another client;
- health and correctly verified Stripe webhook are not broken by generic rules.

**Implementation child packets.**

1. **CH-3.7A backend/durable admission:** inventory every expensive entry:
   agent, upload/analyze/split, Tender process,
   export/render, search/retrieval, and workflow start. Record resource/spend
   unit and existing durable state.
   Use CH-2.4 durable state for agent. For Tender, add dedicated
   <code>tender_pipeline_admissions</code>, owned by TCM, with ID,
   <code>queue_scope</code>, <code>comparison_id</code>,
   <code>pipeline_generation</code>, state, admission fence/version, admitted user,
   created/updated/terminal timestamps, and safe terminal reason. State is exactly
   <code>active|completed|failed_exhausted|cancelled|superseded</code>. A partial
   unique index covers <code>(queue_scope,comparison_id) WHERE state = 'active'</code>;
   a separate scoped user/state index supports the admission count. The FK to the
   comparison cascades or restricts only according to the existing TCM retention
   contract. Never overload the product lifecycle values in
   <code>TenderComparison.status</code>, and never index all queued/running
   <code>TenderJob</code> rows as if they were one pipeline admission.

   In one short transaction lock
   the comparison row, acquire a deterministic scoped per-user advisory lock,
   recheck entitlement/state, count that user's active rows in the same scope,
   and atomically insert both the active admission and its initial Tender job;
   neither may commit alone. <code>pipeline_generation</code> is payload/fence
   identity, not part of the one-active key. Every initial/continuation/retry job
   stores admission ID, generation, and admission fence. Initial process creation and
   retry of a terminal prior pipeline create a fresh admission only after that
   transaction proves no active row. A retry inside one active generation reuses
   the row and generation. A new business
   generation while an earlier generation is queued/running returns 409 unless
   an explicit cancel/supersede command first fences the old generation under the
   same comparison/advisory lock and conditionally moves its admission fence/state
   to <code>cancelled</code> or <code>superseded</code> before inserting a replacement
   generation. In that same transaction, queued jobs for the old admission become
   cancelled and the fence invalidates authority held by running workers. Claim,
   continuation enqueue, heartbeat/cancellation observation, and immediately
   before every Storage/LLM/provider/external attempt must lock or otherwise
   transactionally verify the admission is still active and its ID/generation/
   fence matches; a mismatch aborts without a further external call or
   publication. Heartbeat makes cancellation/supersede observable within its
   configured interval, and a paused old worker rechecks before resuming costly
   work. Only the fenced final pipeline-completion transaction may move
   active to <code>completed</code> or <code>failed_exhausted</code>; individual
   intermediate job completion does not release admission. Every job publication
   checks the same admission ID/generation/fence so a superseded worker cannot
   publish. Test simultaneous requests; crash at the barrier between admission
   and initial-job construction (both roll back); a new generation during prior
   active work; paused old worker then supersede/replacement (old makes no later
   provider call/publication); claim and continuation with stale admission;
   cancel/supersede race; and two comparisons at the user's cap. Derive from authoritative rows rather
   than adding a generic framework.
   Use a fast local semaphore only for bounded CPU/thread work while API remains
   one process; make the single-process limitation explicit. If multiple API
   workers are approved, replace it with a tested durable admission seam first.
   Bound search inputs/results and export concurrency/cache behavior.
2. **CH-3.7B trusted edge:** configure separate Nginx IP burst zones for
   general API, upload, and agent
   starts. Trust forwarded client IP only from the known Traefik/internal CIDR.
   Return stable 409/413/415/429 responses and <code>Retry-After</code>.
   Load-test legitimate acceptance scenarios and tune from evidence.

**Verification.** Oversize/over-cap work makes zero Storage/parser/OpenAI call;
rejected concurrency does not grow RSS with body size; rate window recovers;
legitimate scenario is not throttled; single-process and any approved
cross-process tests agree. The admission/initial-job crash barrier leaves neither
row; stale claim/continuation fails before work; and after supersede the paused old
worker makes zero additional external calls or publication while the replacement
generation proceeds.

**Observability.** Reject count by route/reason/safe scope, active count, retry
delay, and cost avoided. Do not use raw IP/user IDs as metric labels.

**Migration/rollout/rollback.** Add the dedicated Tender admission table/index,
update/run CH-1.5's explicit table/grant/RLS contract, and deploy code that dual-
reads/classifies existing active pipelines under a temporary conservative
default before enabling enforcement. Remove that default only after drain,
backfill/reconciliation, staged proof, and rollback-floor advance. Admission
rows have no time-only expiry: a scoped reconciler may terminalize an abandoned
row only after CH-2.2 lease/job reconciliation proves no authoritative active
work remains. Roll back thresholds via environment, not by removing validation;
retain the expanded admission schema for compatible app rollback.

**Do not.** Do not call an in-memory token bucket globally correct, trust
arbitrary <code>X-Forwarded-For</code>, or throttle verified Stripe delivery in
a way that causes data loss.

**Stop if.** Proxy trust chain is unknown, product limits are unapproved, or
multi-worker deployment is requested without durable tests, or an existing
comparison/generation cannot be classified safely during admission backfill.

**Commit/evidence.** CH-3.7A and B are separate implementation/evidence pairs.
Evidence includes 429/recovery/RSS and proxy-spoof tests.

### CH-3.8 - Bound host disk, logs, workspaces, and memory growth

**Objective and risk.** Persistent agent workspaces, Docker logs, volumes,
images, and temporary files cannot fill the host; memory and disk retain safe
rollout headroom.

**Files/artifacts.**

- <code>deploy/dokploy.compose.yml</code> logging/resource/volume settings
- agent workspace manager/configuration
- cleanup/reconciliation service from CH-2.6
- host-capacity runbook and CH-3.3 dashboards/alerts
- bounded workspace tests and deployment preflight script

**Red baseline.** Record host disk/inodes/RAM/swap, Docker images/volumes/logs,
agent-workspace bytes/files/age, and per-container idle/loaded RSS. Current
persistent workspace and logs have no enforced quota/rotation.

**Implementation child packets.**

1. **CH-3.8A workspace quota/reconciler:** approve per-project, per-user, and
   global agent-workspace byte/file-count
   quotas. Enforce before writing and return a stable capacity error; do not
   delete active-turn data.
   Add TTL cleanup for completed/abandoned turn workspaces through a scoped,
   auditable reconciler. Preserve litigation/incident holds.
2. **CH-3.8B host/container policy:** configure Docker log
   <code>max-size</code>/<code>max-file</code> or the
   approved logging-driver equivalent and verify applied runtime settings.
   Inventory writable volumes/tmpfs and add cleanup/size ownership for parser,
   ODL/LibreOffice, Nginx, exports, and build cache.
   Add deployment preflight that blocks rollout below approved free
   disk/inode/RAM headroom.
   Alert at disk/inode 70% warning, 85% high, and 90% critical; alert on
   container OOM/restart and anomalous workspace/DB/Storage growth.
   Set container memory reservations/limits only after CH-6-style measured
   peaks. Sum hard limits no greater than 75% host RAM, preserving at least 25%
   for OS/Docker/Traefik and overlapping rollout.

**Red tests.** Write the following cases to fail against the current unbounded
behavior before implementation.

**Verification.** After CH-3.8A/B, all of these cases must pass:

- one byte/file over workspace quota fails before write;
- concurrent writers cannot exceed the durable quota materially;
- cleanup skips active/held work and retries failure;
- generated logs rotate at the configured threshold;
- container inspection matches declared resource/log settings;
- synthetic fill/preflight and OOM/restart alert paths fire safely;
- target load leaves at least 15% disk/inodes and 25% RAM free.

**Observability.** Disk/inodes/RAM/swap, container RSS/restart/OOM, volume/log/
workspace bytes/files/oldest age, cleanup outcome, and growth slope. No
workspace names/content.

**Migration/rollout/rollback.** A durable quota/cleanup table, if needed,
updates/runs CH-1.5 security contract. Roll out accounting before enforcement;
start with alerts, then approved hard limits. Roll back a bad threshold via
config without removing measurement/cleanup intent.

**Do not.** Do not delete unknown directories, use broad recursive paths, or
claim compose limits apply without container inspection.

**Stop if.** Current data ownership/holds are unknown, quotas are unapproved, or
measured services cannot retain required headroom.

**Commit/evidence.** CH-3.8A and B are separate implementation/evidence pairs.

### CH-3.9 - Account for and enforce provider spend budgets

**Objective and risk.** Tender stages and agent turns have versioned monetary
usage where provider metadata exists, conservative behavior where it does not,
and soft/hard limits that prevent uncontrolled spend.

**Files/symbols.**

- existing Tender stage-usage/telemetry and agent-turn usage records
- new versioned model-price configuration/model and validation
- provider adapter usage extraction
- billing/usage admission and operational dashboards/alerts
- reconciliation tests and runbook

**Precondition from CH-3.6.** Every relevant adapter must expose one attempt
boundary with SDK/internal automatic retries disabled. CH-3.6 owns retry policy;
CH-3.9 wraps each actual network dispatch. If an SDK cannot expose or disable an
internal retry, that adapter is blocked because multiple provider attempts could
otherwise hide behind one reservation.

**Contract.** Store provider, exact model, input/output/cached/reasoning units as
reported, price-version ID/effective time, currency, computed amount, scope
(stage/comparison/turn/user/month), request correlation, and
<code>usage_complete</code>. Never store prompt/response. Do not fabricate zero
cost when metadata is absent. Every provider attempt uses this durable
reservation state machine:

- <code>reserved</code> means budget is held but provider dispatch has not begun;
- immediately before dispatch, atomically write provider request correlation and
  transition <code>reserved -&gt; started</code>;
- a normal response transitions <code>started -&gt; settled</code> with actual usage
  and refunds only the unused estimate;
- a lease/reaper that finds an abandoned <code>started</code> attempt transitions it
  to <code>unresolved</code>, without refunding or releasing its estimate;
- provider request lookup or invoice/export reconciliation transitions
  <code>unresolved -&gt; reconciled</code> atomically with the authoritative actual
  amount and budget adjustment: refund only authoritative excess or record an
  overage and reduce/block future admission under the approved policy; after
  bounded failed lookups it transitions to <code>dead_letter</code>, retains the
  conservative charge, alerts an owner, and can move only to
  <code>reconciled</code> through an audited operator action; and
- only a <code>reserved</code> row whose <code>started_at</code> is null may expire and
  release budget. No <code>started</code>, <code>unresolved</code>, or
  <code>dead_letter</code> row may return to <code>reserved</code> or auto-refund.

**Implementation child packets.**

1. **CH-3.9A usage/price ledger:** add a reviewed versioned price table/config
   whose effective entries are updated from official provider pricing and
   require approval. Capture usage from each adapter, compute in deterministic
   Python/Decimal, mark missing/partial metadata unknown, and update/run CH-1.5
   if a new table is added.
2. **CH-3.9B budgets/reconciliation:** define approved Tender per-comparison,
   user/month, global/month, and per-operation soft/hard ceilings. Soft sends an
   alert; hard prevents new work before provider call while allowing necessary
   status/cancel/cleanup. Where cost is unknown, fall back to conservative turn/
   job/token quotas and alert; never allow unlimited work. Enforce hard ceilings
   through an atomic estimated-cost reservation before each provider attempt,
   keyed by scope/logical operation/provider-attempt. Implement the exact durable
   state machine above, an expiry/reaper for never-started attempts, and a bounded
   reconciliation queue for abandoned started attempts. At the CH-3.6 adapter
   attempt boundary, reserve, transition to started, then issue exactly one network
   dispatch. A charged retry makes a new provider-attempt
   reservation and consumes budget even if logical output deduplicates; logical
   spend and provider-attempt spend are reported separately. Reconcile aggregates
   against provider invoices/usage exports by period/model and investigate
   variance over the approved tolerance.

**Red tests.** Write the following cases before enabling accounting or budgets.

- crash after reservation but before <code>started</code> allows exactly one expiry
  refund;
- crash after <code>started</code>, both immediately before and immediately after
  mocked provider send, never auto-refunds and remains conservatively consumed
  until reconciliation;
- provider lookup settles an unresolved attempt, while exhausted lookup moves it
  to owned <code>dead_letter</code> without releasing budget; and
- concurrent expiry, settlement, reconciliation, and retry cannot double-release
  or conceal a real provider attempt.

**Verification.** After CH-3.9A/B, all of these cases must pass:

- known usage/price computes exact currency amount with version;
- cached/uncached and price change at boundary use correct version;
- absent metadata is unknown and triggers conservative policy;
- work one unit over hard ceiling makes no provider call and returns stable
  entitlement/capacity response;
- retried/idempotent calls do not double count logical spend, while real
  provider attempts remain auditable and each charged attempt consumes its
  reservation;
- an injected transient error followed by one retry produces two distinct
  reservation/attempt identities and no hidden SDK retry;
- concurrent reservations at the remaining ceiling allow only the fitting set,
  expired never-started reservations are reclaimed once, and settlement/refund
  cannot race into negative or extra budget;
- a crash before send expires once, while a crash after dispatch begins remains
  <code>started</code>/<code>unresolved</code> and consumes the estimate until an
  authoritative reconciliation settles or dead-letters it;
- monthly reconciliation variance is within approved tolerance.

**Observability.** Spend/usage by low-cardinality product stage/model/price
version, unknown-usage rate, budget remaining, hard rejects, and invoice
variance. User/comparison IDs stay searchable logs, not metric labels.

**Migration/rollout/rollback.** Add ledger/config before enforcement. Start
alerts, validate reconciliation, then enable hard ceilings. Roll back ceiling
values by approved config; retain usage/audit rows and every started/unresolved/
dead-letter reservation until authoritative reconciliation.

**Do not.** Do not hard-code undocumented prices in scattered services, use
binary float for currency, or count missing usage as zero. Do not treat a process
crash, timeout, or ambiguous transport error as proof that the provider did not
receive a started request.

**Stop if.** Official pricing/meter semantics, currency, ceiling owner, or
provider reconciliation access is unavailable.

**Commit/evidence.** CH-3.9A and B are separate implementation/evidence pairs
with price approval and reconciliation sample.

### CH-3.10 - Implement graceful drain and bounded shutdown

**Objective and risk.** Routine deploy/restart stops new work and drains safely;
over-grace work abandons authority without publishing; forced-kill recovery
remains distinct.

**Files/symbols.**

- FastAPI lifespan/admission and Pi process registry
- Tender, core workflow, parser, and cleanup worker signal loops
- external resource containers from CH-3.6
- <code>deploy/dokploy.compose.yml</code> stop signals/grace periods
- shutdown integration/chaos tests and deployment runbook

**Red tests.** SIGTERM currently has no end-to-end contract proving new claims
stop, heartbeat continues, Pi children exit, clients close, and compose waits
long enough. Capture each service's actual behavior.

**Implementation child packets.**

1. **CH-3.10A workers:** on SIGTERM mark draining and stop claims. Continue
   heartbeat for active leased work while it finishes within an approved grace
   shorter than lease/deployment timeout. At grace, cancel child work, stop
   heartbeat, roll back unpublished DB work, and abandon ownership for safe
   lease reclaim. Flush only fenced completed publication.
2. **CH-3.10B API/Pi/resources/compose:** readiness becomes 503 and new expensive
   admission returns a retryable drain response; existing SSE gets bounded
   completion/cancel; revoke/cancel local turns and terminate/kill Pi children;
   close HTTP/OpenAI/Supabase resources. Set explicit
   <code>stop_grace_period</code> per service from measured shutdown time plus
   margin.

**Verification.**

- graceful deploy accepts no new work after drain starts;
- completing work publishes once; over-grace work publishes nothing and is
  reclaimed within lease plus two polls;
- all Pi/parser child processes and external clients are gone;
- no pool/session leak or corrupt partial object;
- compose honors configured grace;
- separate SIGKILL test still recovers through leases/reapers.

**Observability.** Drain start/active count/grace remaining/outcome, abandoned
lease, child terminate/kill, close failure, and build/instance.

**Migration/rollout/rollback.** Code/compose only. Deploy worker behavior before
using rolling restarts as evidence. Roll back to the prior release record only with
traffic/workers drained.

**Do not.** Do not immediately exit on SIGTERM, extend leases after abandoning,
or mark work failed/done without fence.

**Stop if.** A handler cannot be cancelled/abandoned without partial publication
or measured shutdown exceeds provider/Dokploy grace capability.

**Commit/evidence.** CH-3.10A and B are separate implementation/evidence pairs
with graceful and SIGKILL timelines.

## 12. Stage 4 - measured client and database performance

### CH-4.0 - Add a minimal production-browser performance harness

**Objective and risk.** Make Stage 4 browser timing/long-task thresholds
measurable before tasks depend on them, using the built Nginx image rather than
jsdom or Vite.

**Files/symbols.**

- <code>frontend/package.json</code>/<code>pnpm-lock.yaml</code>
- new <code>frontend/playwright.performance.config.ts</code>
- new <code>frontend/performance/fixtures/</code> and focused specs
- CH-1.7B built web image plus deterministic synthetic backend fixture
- CI artifact settings, initially an explicit performance command

**Dependency decision.** Add Playwright as a dev dependency. Its browser
installation/control/tracing is a standard nontrivial capability that cannot be
recreated safely in 30 lines. Record version/transitive footprint and cache the
matching browser in CI. Do not add axe in this task; CH-5.6 owns accessibility.

**Red baseline.** No production-browser harness can report scripting, commits,
long tasks, DOM rows, transfer, or interaction timing for the 100-message and
10,000-evidence fixtures.

**Implementation.**

1. Run the exact built web/Nginx image and an in-process deterministic synthetic
   API fixture; no real Supabase/provider network.
2. Add seeded routes/fixtures for 100 chat messages plus 500 stream chunks and
   10,000 evidence summaries with paged responses.
3. On the unmodified release-capable production image, capture browser
   Performance API/CDP measures, long tasks where supported, DOM mutation/row
   counts, request/transfer bytes, and trace on failure. Do not inject React
   counters or test-only code into the image. If React Profiler commit attribution
   is needed for diagnosis, use a separately labelled non-release profiling
   image only for relative analysis; its numbers never satisfy transfer/network
   or release-digest gates.
4. Fix viewport/CPU assumptions and record runner hardware. Do not use arbitrary
   sleeps; wait on app/test events.
5. Add <code>pnpm test:performance-browser</code>. Establish baseline ranges;
   task-specific hard assertions enter CH-4.4/4.5 after the related code change.
6. Run Chromium desktop; mobile/a11y/cross-view acceptance remains CH-5.6.

**Verification.** Two consecutive runs produce the expected fixture counts and
raw metrics; no external request, console/page error, or unhandled rejection;
missing instrumentation causes a failed test rather than a zero measurement.

**Observability/migration/rollback.** Test-only, no schema. Store traces only on
failure and raw synthetic metrics with SHA/runner metadata.

**Do not.** Do not use Vite dev server, customer data, production credentials,
or jsdom timing as browser performance proof.

**Stop if.** The built image cannot use deterministic fixtures without changing
production behavior, runner saturation makes results meaningless, or browser
version is unpinned.

**Commit/evidence.** One harness/dependency implementation commit and baseline
coordination commit.

### CH-4.1 - Make project-event reconciliation bounded and race-safe

**Objective and risk.** Eliminate historical replay, duplicate timers,
infinite authorization retries, and idle request amplification while preserving
events committed during cockpit bootstrap.

**Files/symbols.**

Backend:

- <code>Project.event_sequence</code>
- <code>ProjectCockpitBootstrapResponse</code>
- <code>get_project_cockpit_bootstrap</code> and
  <code>get_project_events</code>
- cockpit/event integration tests

Frontend:

- <code>ProjectCockpitBootstrap</code> type and API methods
- <code>useProjectEventCursor</code>,
  <code>applyDurableProjectEvent</code>
- <code>ProjectCockpitPage</code> and project-data tests
- <code>ApiRequestOptions</code>/<code>AbortSignal</code> plumbing

**Race/interface contract.**

- bootstrap returns <code>events_after</code>, captured from the owned project
  before evidence/workspace/draft reads;
- an event transaction increments sequence and writes the event atomically;
- polling is disabled until bootstrap cursor exists and never defaults to zero;
- one hook instance owns at most one timer, one request, and one abort
  controller;
- page size remains bounded; a full page drains immediately until a short page.

**Red tests.**

1. Bootstrap lacks cursor and a 1,000-event project starts from zero.
2. Commit an event after cursor capture but before bootstrap completes; polling
   must observe it.
3. Repeated <code>pollNow()</code> can leave multiple timers.
4. 401/403/404 retries indefinitely.
5. Hide/unmount fails to abort current work.
6. One response invalidates the same query repeatedly for duplicate event keys.

**Implementation child packets.**

1. **CH-4.1A backend high-water contract:** capture/return
   <code>events_after</code>, prove the transaction boundary, and add backend
   schema/concurrency tests.
2. **CH-4.1B frontend scheduler:** add the frontend field, store bootstrap
   cursor in the page and pass
   <code>initialAfter</code> to the hook. Reset to the new project's cursor.
   Remove the lifetime <code>seenIdsRef</code>; the monotonic sequence is the
   deduplication authority. For each response require events strictly ascending,
   every sequence greater than requested <code>after</code>, and
   <code>next_after</code> at least the last returned sequence. A full page whose
   cursor does not advance is a protocol error: stop and back off/alert rather
   than spin. Implement an explicit scheduler state machine: clear before scheduling,
   coalesce manual requests, keep one in-flight request/controller, and clean
   all on hide/unmount.
   Pass <code>AbortSignal</code> through API helpers and handle an already-aborted
   signal both before and immediately after any token acquisition.
   A 401 is terminal until CH-1.6's auth revision changes. A 403/404 is terminal
   until project identity changes or an explicit manual retry. While terminal,
   <code>pollNow()</code> is inert. Apply exponential
   network/5xx backoff with jitter capped at 30 seconds and reset on success.
   Poll immediately on visibility restoration and explicit
   resource/conversation signals.
   Deduplicate invalidation keys per response.
   Use 1-second active and 15-second idle defaults. If product requires
   subsecond updates, design long-poll/SSE rather than high-frequency idle
   polling.

**Verification/thresholds.**

- first poll uses bootstrap high-water cursor;
- boundary event is observed and 1,000 historic events cause no replay;
- visible/nonterminal state has at most one timer/request/controller after
  manual poll, error, and hide/show; hidden or unmounted has exactly zero;
- terminal auth/not-found errors make exactly one request;
- hidden/unmounted makes zero continuing requests;
- 1,000 idle clients model at most 75 requests/second; 100 active at most 100;
- no historical artefact event creates latest-draft fan-out.

**Observability.** Safe poll count, events/page, lag, drain pages, backoff,
terminal reason, invalidation count. No event payload/customer IDs as labels.

**Migration/rollout.** Additive backend field can deploy before frontend.
Frontend must refuse polling without it rather than use zero. Remove any
temporary optionality after both images are current.

**Rollback.** Roll frontend and backend together if necessary; no DB migration.
Old client may ignore the additive field.

**Do not.** Do not solve replay with client deduplication alone or permit
multiple timers.

**Stop if.** Event and sequence are not transactional, the concurrency test
misses a boundary event, or required freshness is below one second.

**Commit/evidence.** CH-4.1A and B are separate implementation/evidence pairs.
Evidence includes scheduler/request model.

### CH-4.2 - Consume existing chat and Tender cursor pages

**Objective and risk.** Make records beyond the first 50 accessible without
unbounded list loading or losing stable mutation behavior.

**Files/symbols.**

- chat/Tender frontend types and <code>api.listThreads</code> /
  <code>api.listTenderComparisons</code>
- <code>ChatSessionList</code>, chat query keys/cache mutations
- <code>useTenderComparisons</code>, <code>ComparisonList</code>
- existing backend page/cursor functions and contract tests

**Red tests.** Fixtures with at least 51 threads/comparisons cannot reach page
two; API helpers discard <code>next_cursor</code>; create/rename/delete cache
logic assumes one flat page.

**Implementation child packets.**

1. Characterize backend order/cursor behavior, including equal timestamps,
   owner/project binding, invalid/foreign cursor, and concurrent insertion.
   Declare each route parameter as <code>cursor: str | None</code> and parse it in
   owned code so malformed input returns the same non-leaking
   <code>400 {"code":"invalid_cursor"}</code>, never FastAPI's UUID
   <code>422</code>. If the retained cursor is an anchor-row UUID, a missing,
   foreign-owner, or foreign-project anchor returns that 400. If it is replaced by
   CH-4.3's signed self-contained keyset format, deletion of the anchor row is not
   an error because the signed sort tuple is sufficient. Repeating the same valid
   request is idempotent and returns the same page; the server must never emit
   <code>next_cursor == request_cursor</code>.
2. **CH-4.2A chat:** return the full chat page object and convert its hook to
   <code>useInfiniteQuery</code> with null initial page,
   verbatim cursor, and server <code>next_cursor</code>.
   Flatten pages with stable ID deduplication; preserve server order and remove
   <code>ChatSessionList</code>'s client re-sort.
   Add accessible explicit Load more controls; no endless automatic fetch.
   Update thread create/rename/delete over <code>InfiniteData</code>: create may
   prepend page one; delete removes all matches. Rename changes
   <code>updated_at</code>, so invalidate/refetch the ordered list rather than
   update in place. Prefer invalidation for any ordering-affecting mutation.
3. **CH-4.2B Tender:** return the full Tender page object and apply the same
   bounded infinite-query/load-more contract. Keep invalidations
   project/comparison scoped.
4. Both hooks share a cursor-failure rule: on the first
   <code>invalid_cursor</code> after page one, clear that query and refetch page one
   once for the current query revision while showing a non-blocking reset notice.
   A second failure is surfaced and makes no further automatic request. If a
   response ever repeats the request cursor, stop immediately, record
   <code>cursor_non_advancing</code>, and expose Retry; never loop silently.

**Verification.**

    Set-Location frontend
    pnpm test
    pnpm typecheck
    pnpm lint
    pnpm build

Page two fetches only on action; record 51+ is accessible; concurrent insert
does not duplicate/skip the existing sequence; initial request stays 50; no
mutation duplicates an ID. A repeated valid request is idempotent; injected
malformed/invalid and non-advancing cursor cases make at most one reset and never
produce <code>422</code> or an automatic loop.

**Observability/migration/rollback.** No migration. Record pages/items/request
latency as safe client telemetry if approved. Revert API shapes/hooks/UI
together.

**Do not.** Do not concatenate all pages automatically or resort client-side.

**Stop if.** Backend cursor ordering differs from its documented tuple or any
invalid cursor class does not return the identical approved
<code>invalid_cursor</code> contract, or the server emits its request cursor as
<code>next_cursor</code>.

**Commit/evidence.** CH-4.2A and B are separate implementation/evidence pairs;
both close the task.

### CH-4.3 - Add a bounded versioned evidence API, search, and resolution contracts

**Objective and risk.** Cockpit/API cost must not grow with every project
document, while selections, folders, invoice state, and transmittals remain
correct for off-page evidence. The bounded contract must be introduced without
destroying the previous image's rollback path.

**Files/symbols.**

- <code>_list_project_evidence_previews</code>
- <code>_apply_invoice_statuses</code>
- cockpit bootstrap and evidence endpoints/schemas
- <code>backend/app/config.py</code> and CH-1.11 secret matrix for API-only
  cursor signing
- new evidence cursor/query-budget tests
- source-document/workspace-file DB models and relevant indexes

**Baseline/red work.**

- capture raw/gzip bootstrap bytes and p50/p95 for 100, 1,000, and 10,000
  indexed documents;
- capture query count and plan;
- prove naive first-page truncation breaks inbox count, chat selection, folder
  contents, invoice status, or transmittal matching.

**New API contract.** Freeze the exact path before coding; the recommended
non-ambiguous path is
<code>/projects/{project_id}/cockpit-bootstrap-v2</code>. The candidate SPA must
use only versioned/bounded paths. Freeze these exact routes/schemas before
implementation:

- <code>GET /projects/{project_id}/cockpit-bootstrap-v2</code> returns the active
  project, first <code>EvidencePage</code>, bounded pending page/count, latest
  bounded draft/artefact summaries, workspace directory/count metadata, and
  <code>events_after</code>. It omits the all-projects array and all file children.
- <code>GET /projects/{project_id}/evidence-page</code> returns
  <code>EvidencePage {items,next_cursor,total_count,inbox_count}</code>.
- <code>GET /projects/{project_id}/pending-evidence-page</code> returns
  <code>PendingEvidencePage {items,next_cursor,total_count}</code>. Its population
  is exactly owned <code>WorkspaceFile</code> rows whose canonical normalized path
  is under Inbox and for which no owned <code>SourceDocument</code> with
  <code>source_type = 'project_evidence'</code> has the same canonical normalized
  path. Implement that population as bounded SQL/<code>NOT EXISTS</code>, never an
  in-memory union/subtraction. Order is exactly
  <code>(WorkspaceFile.created_at DESC, WorkspaceFile.id DESC)</code>; the cursor
  contains/binds that tuple. A newer concurrent insert is intentionally absent
  from an already-started continuation and appears after first-page refresh. If a
  pending row becomes indexed between pages, it leaves the pending population;
  continuation still advances from the signed tuple without duplicate/restart,
  and the transactional project event invalidates both pending and evidence
  queries so refresh shows it once in the indexed population. This is keyset
  read-committed behavior, not a promised multi-page snapshot.
- <code>GET /projects/{project_id}/workspace-directories?parent_id=&amp;cursor=&amp;limit=</code>
  treats omitted <code>parent_id</code> as the root and returns only direct
  children as
  <code>DirectoryPage {items,next_cursor,total_count,parent_id}</code>. Each
  <code>DirectorySummary</code> is exactly
  <code>{id,name,parent_id,direct_directory_count,direct_file_count}</code>.
  Directory IDs are opaque server-issued identities, not client-interpolated raw
  paths. Order is the recorded database normalization/collation for
  <code>name ASC</code>, then <code>id ASC</code>; the cursor also binds
  <code>parent_id</code>.
- <code>GET /projects/{project_id}/workspace-directories/{directory_id}/files?cursor=&amp;limit=</code>
  returns direct files only as
  <code>FilePage {items,next_cursor,total_count,directory_id}</code>, ordered by
  the recorded <code>filename ASC, id ASC</code> database expressions. Its cursor
  binds <code>directory_id</code> as well as project, owner, endpoint, order, and
  last tuple; replay under another directory is <code>400 invalid_cursor</code>. A missing
  or foreign directory returns the identical non-leaking
  <code>404 {"code":"directory_not_found"}</code>. No endpoint materializes a
  complete workspace tree to answer a page.
- <code>POST /projects/{project_id}/evidence-summaries:batch</code> accepts one to
  100 unique evidence IDs and returns owned summaries in request order plus an
  explicit missing-ID list. The entire JSON body is at most 32 KiB.
- <code>POST /projects/{project_id}/transmittals:resolve-evidence</code> accepts
  <code>{"rows":[...]}</code> with one to 100 parsed transmittal row objects
  <code>{row_id,document_number,title,revision,category}</code>. A client-generated
  <code>row_id</code> is nonempty and at most 128 characters; document number is
  at most 255, title 512, revision 64, and category 128 characters, and at least
   document number or title is nonempty. The body is at most 32 KiB. Duplicate
  <code>row_id</code> is <code>400 invalid_request</code>; duplicate row content is
  preserved and receives a separate ordered result.
- The transmittal response is
  <code>{results:[TransmittalResolution]}</code> in request order. Each result is
  <code>{row_id,status,match_basis,evidence,candidates,candidate_count}</code>,
  where status is <code>matched|unmatched|ambiguous</code>. Matched contains one
  owned bounded evidence summary, unmatched contains none, and ambiguous contains
  at most five owned candidate summaries plus the full candidate count; it never
  chooses arbitrarily. Normalize fields with Unicode NFKC, trim, collapse Unicode
  whitespace, and case-fold. Match in this fixed precedence: normalized exact
  document number; loose document number after removing only ASCII whitespace,
  hyphen, underscore, full stop, slash, and backslash; then normalized exact
  title. Skip both document-number tiers when the normalized input number is
  empty, and skip the title tier when normalized title is empty. Treat a
  whitespace-only revision/category as absent; otherwise each constrains every
  attempted tier. Stop at the first tier
  with candidates: one is matched and two or more are ambiguous; never fall
  through an ambiguous stronger tier or use fuzzy similarity. The frontend may
  process at most 500 transmittal rows per action in sequential chunks satisfying
  both at most 100 rows and at most 32 KiB of UTF-8 JSON, including envelope;
  therefore 500 maximum-length/multibyte rows may require more than five chunks.
  Row 501 is rejected before any request with accessible copy.

All pages default to 50 and cap at 100. Add API-only
<code>API_CURSOR_SIGNING_SECRET</code> (at least 32 random bytes, never present in
workers/web/logs) through the canonical settings module and CH-1.11 matrix. The
cursor is canonical JSON plus HMAC-SHA256, includes version and issued-at, and
expires after one hour; rotation may invalidate an old page with the normal
<code>invalid_cursor</code> response. Evidence sort keys are exactly
<code>document_number</code>, <code>title</code>, <code>revision</code>, and
<code>category</code>, with <code>asc|desc</code>; folder ID and a trimmed
maximum-200-character search string are optional filters. Before implementation,
record the exact PostgreSQL expression/collation used for each key (including
document-number natural-order behavior), <code>NULLS LAST</code> in both
directions unless a reviewed UX contract says otherwise, and UUID ID ascending/
descending as the final direction-matched tie-breaker. The opaque signed/versioned
cursor binds project, owner, endpoint, normalized filters, sort/direction, last
null marker/value, and ID; it is never an offset. Malformed, expired,
foreign-owner/project, filter-mismatched, or tampered cursors all return the
identical non-leaking <code>400 {"code":"invalid_cursor"}</code>. Every route
declares <code>cursor: str | None</code> and manually parses it so malformed input
does not become framework <code>422</code>. Because the keyset tuple is contained
in the signed cursor, deleting the former anchor row does not invalidate the next
page. A repeated valid request is idempotent; the server must never return
<code>next_cursor == request_cursor</code>.

**Implementation child packets.**

1. **CH-4.3A - versioned page/cursor endpoint.** Snapshot the existing
   <code>cockpit-bootstrap</code>, <code>evidence</code>, and
   <code>workspace-tree</code> responses for the retained prior image. Add all v2
   page/cursor schemas/routes above and one purpose/version-aware encode/decode
   helper with boundary/property tests. If existing path storage cannot answer a
   direct-child directory/file page with bounded indexed SQL, add a normalized
   workspace-directory catalogue and update it transactionally through every
   workspace mutation/reconciliation seam; do not derive a whole tree in memory.
   Page <code>SourceDocument</code> in SQL, compute counts in bounded aggregate
   queries, restrict invoice/document-usage queries to page IDs, and return only
   the first evidence/pending pages plus workspace directory/count metadata from
   v2. Omit <code>projects</code> (CH-4.7C owns navigation paging) and every
   workspace file child. Never construct an in-memory union to paginate.
2. **CH-4.3B - batch resolution and measured query plans.** Add the owned
   batch-summary endpoint and exact row-based transmittal-resolution contract,
   normalization, precedence, ambiguity, row/action, candidate, and body limits.
   Measure every allowed sort/search plan. Add an expression/composite index only
   where <code>EXPLAIN (ANALYZE, BUFFERS)</code> proves it under the global
   live-DDL rules.
3. **CH-4.3C - monitored compatibility endpoints.** Inventory and keep every
   unversioned full-array route used by the prior SPA: at minimum
   <code>cockpit-bootstrap</code>, <code>evidence</code>, and
   <code>workspace-tree</code>; CH-4.7C owns the old <code>/projects</code>
   response. Add per-route request count, response-byte, duration, and an
   explicit conservative rate limit sized/proven for expected rollback traffic.
   The prior SPA sends no build revision, so record it as
   <code>legacy-unknown</code> unless a separately deployed bridge release adds a
   header; never require a header it cannot send. Candidate code makes zero
   normal calls to any legacy route. Retain all through GATE-6 and the release
   rollback window; removal is a separate post-launch packet.

**Verification/thresholds.**

- first page no more than 100 and no more than 200 KiB raw JSON;
- query count remains constant/bounded from 100 to 10,000;
- cursor covers equal/null values, invalid/foreign cursor, anchor deletion,
  idempotent repeat, one-hour expiry, insertion, and non-advancing-output guard;
- pending evidence covers equal creation timestamps, newer concurrent insertion,
  pending-to-indexed transition between pages, and no duplicate/restart; a file
  cursor replayed across directories is rejected;
- batch lookup cannot resolve another owner, caps at 100, and enforces 32 KiB;
- transmittal exact/loose/title precedence, revision/category constraints,
  title-only, number-only, duplicate content, duplicate row ID, ambiguity, and
  no-arbitrary-pick cases pass; max-length/multibyte fixtures prove every request
  satisfies both row and encoded-byte caps;
- existing bootstrap remote p95 target remains at most 500 ms;
- v2 never builds/serializes all evidence;
- root and off-page nested workspace directories plus every direct file page are
  reachable through stable parent-bound pages without a full-tree query;
- candidate bundle has zero references/calls to every compatibility route, while
  a staged prior image completes its product journey at expected rollback load;
- compatibility traffic/bytes are visible and accepted by its rate policy.

**Observability.** Page size, query count/duration, search/sort class,
cursor-invalid reason, response bytes; no search text/document names.

**Migration/rollout.** Apply any justified index or measured directory-catalogue
migration under the repository migration rules and update/rerun CH-1.5's table
security contract. Deploy v2 first, then CH-4.4's client. Keep the old endpoint for the
recorded rollback floor through production acceptance. Contract deletion is a
future release, not part of this task.

**Rollback.** Roll the web/API to the prior release-record pair; that pair continues to
use the retained old endpoint. Keep harmless indexes during code rollback.

**Do not.** Do not paginate after loading all rows, expose raw offset, name a
partial array as if complete, require a signed cursor's anchor row still to exist,
fuzzily or arbitrarily pick transmittal evidence, or delete the compatibility
route while it is the recorded rollback floor.

**Stop if.** Pending files cannot be bounded separately, cursor order is
non-deterministic, or a consumer still assumes completeness.

**Commit/evidence.** CH-4.3A, B, and C are separate commits. Evidence includes
both response-contract digests, query plans, response bytes, candidate zero-call
proof, and a successful prior-image compatibility request.

### CH-4.4 - Make evidence UI explicitly partial-page aware

**Objective and risk.** Render bounded evidence pages/DOM while preserving
selection, folder, transmittal, chat event, delete/restore, and scroll behavior
for records not loaded on page one.

**Files/symbols.**

- evidence/bootstrap types and API
- <code>useProjectEvidence</code>
- <code>ProjectCockpitPage</code>
- <code>DocumentRepositoryPanel</code>, <code>WorkspaceFolderPanel</code>
- <code>DraftReviewPanel.handleLoadTransmittal</code>
- document selection event and transmittal-register helpers
- tests with 10,000-summary fixture and off-page selection

**Red tests.** DOM contains all fixture rows; selection/folder/transmittal logic
requires the global array; inbox count derives from loaded items; an event for
an unloaded document cannot resolve.

**Implementation child packets.**

1. **CH-4.4A - page, query, and selection state.** Rename state to
   <code>loadedEvidence</code>; never expose it as the complete project set. Use
   an infinite query keyed by project, sort, direction, search, and folder.
   Render loaded pages and use existing TanStack Virtual after the small-list
   threshold. Read total/inbox counts from server aggregates. Store selected IDs
   separately, enforce the 500-ID action limit, and resolve missing summaries in
   ordered 100-ID chunks through CH-4.3's bounded endpoint. Render generated
   artefact drafts in a separate bounded "Generated artefacts" section; never
   merge them into a globally sorted paged-evidence schedule.
2. **CH-4.4B - dependent consumers and events.** Use server batch transmittal
   resolution over the parsed row objects, assigning a stable per-action
   <code>row_id</code>, sending sequential chunks constrained by both at most 100
   rows and at most 32 KiB encoded UTF-8 JSON, and rejecting an action over 500
   rows before its first request. Render matched, unmatched, and
   ambiguous results distinctly; an ambiguous result requires an explicit user
   choice and is never auto-attached. Fetch each direct-child directory page with
   query keys <code>[workspace-directories,projectId,parentId]</code> and each file
   page with <code>[workspace-files,projectId,directoryId]</code>, instead of
   passing global evidence or a complete workspace tree. Expansion fetches only
   that directory's children and can reach a subtree whose ancestors were not on
   the initial root page. Add explicit Load more/result count, preserve scroll, and coalesce
   event invalidation to active pages. Remove complete-array assumptions from
   the candidate client. Do not remove the server compatibility endpoint;
   CH-4.3C retains it for the prior image.
3. Every v2 infinite query applies CH-4.2's failure rule: one visible
   clear-and-page-one refetch per query revision after
   <code>invalid_cursor</code>; then surface failure. Detect a response whose
   <code>next_cursor</code> equals the request cursor, stop, and alert rather than
   scheduling another page.

**Verification/thresholds.**

- DOM has at most 150 repository rows for 10,000 documents;
- no interaction long task over 50 ms on the synthetic fixture;
- settled sort/search client work p95 at most 150 ms after server response;
- target selection/transmittal/folder/delete/chat works when off page one;
- nested direct-child directory/file paging uses parent-scoped query keys and can
  expand an off-root-page subtree without loading the full tree;
- transmittal normalization precedence is preserved in the UI, ambiguity is never
  auto-picked, 500 rows use the required number of ordered row-and-byte-bounded
  chunks, and row 501 makes zero requests;
- scroll is stable after loading more/invalidation;
- v2 workspace bootstrap contains directory/count metadata only and every file
  child is reached through a bounded page;
- generated artefacts remain separately visible and do not corrupt evidence sort;
- selected-evidence summary resolution at 500 IDs succeeds in ordered chunks and
  ID 501 makes zero resolution calls;
- an expired/invalid or injected non-advancing cursor resets at most once and
  never loops.

**Observability/migration/rollback.** Frontend only; safe loaded/visible counts
and interaction durations. Deploy after CH-4.3 v2 and roll back to the prior
release-record pair, whose old endpoint remains available. A web-only rollback after a
future compatibility cleanup is forbidden.

**Do not.** Do not auto-load every page, conflate selected summaries with page
membership, or hide correctness failure with client-only searching.

**Stop if.** Any consumer still receives a partial array under a complete-data
name or off-page cases fail.

**Commit/evidence.** **CH-4.4A** owns query/selection state and **CH-4.4B** owns
folder/transmittal/event consumers. Evidence includes the v2 request trace,
off-page cases, DOM/timing profile, and zero candidate calls to the old route.

### CH-4.5 - Make chat sends, streaming render, and recovery bounded

**Objective and risk.** Per-turn network/render cost is independent of history
length and an interrupted stream reloads the canonical history appropriate to
the active runtime. Pi and the retained legacy path do not currently have the
same persistence semantics; the implementation must not invent equivalence.

**Files/symbols.**

- <code>ChatPanel</code>, <code>AssistantMessage</code>,
  <code>ChatErrorBanner</code>, <code>ChatRail</code>
- <code>ProjectCockpitPage.refreshMessages</code>
- streaming/chat component tests
- both Pi and retained legacy backend stream contract tests

**Red baseline/tests.**

1. With historical messages, fetch body contains the whole history instead of
   exactly the new final message and preserved ID.
2. Profile production-browser commits/scripting for 100 messages and 500
   chunks.
3. Interrupt Pi mid-stream; Reload must remove transient partial assistant state
   and show exactly one persisted user turn with no partial assistant turn.
4. Interrupt the retained legacy path mid-stream; Reload must show the prior
   persisted history and the optimistic user turn must disappear, because that
   path persists user and assistant together only after successful completion.

**Implementation child packets.**

1. **CH-4.5A - constant transport contracts.** Change request preparation to
   send only <code>messages.at(-1)</code> plus required body metadata. Prove both
   Pi and legacy endpoints select the final user message and reconstruct history
   server-side. Reject locally unless the final element exists, has role
   <code>user</code>, a valid ID, and a stable canonical message hash. On Pi,
   preserve the ID and harden its idempotency record: the scoped tuple includes
   execution scope, user, project, thread, message ID, and canonical message
   hash. Same ID with a different thread/hash returns 409. Active, completed,
   failed, cancelled, or revoked state follows an explicit lookup response and
   never launches a second Pi process or persists a second assistant turn. Do
   not claim same-ID idempotency for legacy; characterize/preserve its contract.
   Keep resend absent in this plan; adding it requires a separately reviewed
   retry-generation state machine, not merely a green same-ID test.
2. **CH-4.5B - bounded streaming render.** Characterize the pinned AI SDK's
   supported throttle API. Start at 40 ms (at most 25 commits/second) and profile.
   Extract a memoized message-row boundary so completed rows do not rerender on
   live deltas. Keep per-message parsing within the row and latest-live activity
   at panel level. Preserve scroll pinning while aligning layout reads/writes to
   throttled commits.
3. **CH-4.5C - runtime-specific recovery.** Thread
   <code>onReloadConversation</code> from page through rail to panel. On error,
   show Reload, fetch canonical messages, clear SDK error, remount once through a
   revision key, and discard transient assistant/optimistic state. Assert the Pi
   result is one persisted user/no partial assistant. Assert the legacy result is
   the previously persisted history with the optimistic user removed. Copy may
   say that the latest attempt was not completed; it must not promise that legacy
   saved the user turn.

**Verification/thresholds.**

- outgoing body has one final message for 1/50/100 prior messages;
- Pi keeps the unchanged ID; matching replay launches no second Pi process or
  assistant, while same ID with changed thread/hash returns 409;
- legacy tests make no idempotency claim and preserve its characterized contract;
- stream commits no more than 30/second at initial setting;
- production-browser scripting p95 per update at most 16 ms on the fixture;
- no long task over 50 ms during 500 chunks;
- scroll, Stop, document selection, tool chips, and activity remain green;
- interrupted Pi recovery displays its persisted user turn once with no partial
  assistant; interrupted legacy recovery displays prior history with no
  optimistic user turn.

**Observability.** Runtime mode, request bytes/message count, stream
chunks/commits, first frame, render long tasks, recovery outcome, and
cancellation. No message content or IDs.

**Migration/rollout/rollback.** No migration. Transport and render optimization
can roll back separately; recovery props/state/tests roll together.

**Do not.** Do not add chat virtualization before profiling, add resend, or
rewrite the retained legacy persistence model inside this optimization packet.

**Stop if.** Either backend actually depends on client history, throttle delays
status/tool UX beyond 100 ms, or memoization needs fragile deep equality.

**Commit/evidence.** CH-4.5A, B, and C are separate commits. Evidence contains
request bodies, Pi/legacy persistence assertions, and the production-browser
profile.

### CH-4.6 - Enforce actual Nginx transfer, cache, SSE, and bundle contracts

**Objective and risk.** Production serves what bundle budgets claim: compressed
text assets, immutable hashed caching, revalidated HTML, unbuffered SSE, no
unintended port bypass, and accurate immediate-load accounting.

**Files/symbols.**

- <code>frontend/scripts/measure-build-size.mjs</code>
- <code>frontend/vite.config.ts</code>, <code>index.html</code>,
  <code>src/index.css</code>
- immediately mounted lazy UI such as ChatRail
- <code>deploy/nginx/sitewise.conf</code>,
  <code>deploy/dokploy.compose.yml</code>, and frontend Dockerfile
- CI and new delivery verification script/test

**Red baseline.** Rebuild and record critical JS, immediately mounted lazy JS,
CSS, fonts, and total cold transfer. The audit estimated critical accounting
omitted ChatRail/CSS and Nginx had no explicit gzip/immutable contract; use
current values.

**Implementation child packets.**

1. **CH-4.6A - honest transfer measurement.** Refactor measurement helpers and
   add fixtures proving CSS and explicitly immediately mounted dynamic entries
   are counted. Report critical route JS, immediate lazy JS, CSS, typical en-AU
   loaded fonts, and total app-owned cold transfer separately. Keep critical
   route JS at most 250 KiB gzip. Start immediate JS+CSS at 340 KiB gzip and
   lower only from measured optimization. Bundle public style CSS through Vite
   or give unhashed files explicit revalidation; never immutable-cache them.
2. **CH-4.6B - Nginx/security/delivery contract.** Enable gzip/Vary for
   appropriate JS/CSS/JSON/SVG/font types, not already compressed binaries or
   event streams. Give hashed <code>/assets/</code> one-year immutable caching,
   index/deep-link HTML no-cache, and missing assets a real 404. Create exact chat
   SSE proxy locations for <code>/api/chat/agent/stream</code> and
   <code>/api/chat/stream</code>, with response buffering/compression disabled and
   timeout aligned to agent timeout plus margin. Inventory and test
   <code>/api/mcp</code> as FastMCP streamable HTTP/SSE; do not restore generic
   buffering on a path that carries its stream. Restore normal buffering only on
   proven ordinary APIs. Add <code>nosniff</code> and referrer/frame
   policy, introduce CSP report-only until origins are enumerated, coordinate
   HSTS with the edge, remove or loopback-bind bypass port 8080, and run
   container-level header/body/SSE verification in CI.

**Verification/thresholds.**

- critical JS <=250 KiB gzip; immediate JS+CSS <=340 KiB gzip;
- budget fails if ChatRail or CSS disappears from accounting;
- <code>nginx -t</code>;
- expected gzip plus <code>Vary: Accept-Encoding</code>;
- exact asset/index/missing cache behavior;
- SSE first frame is not proxy-batched and cancellation remains;
- public scan finds no unintended 8080 exposure.

**Observability.** Build report by SHA, Nginx access duration/status/bytes with
safe normalized path, CSP report handling without sensitive URLs.

**Migration/rollout/rollback.** Frontend image/config only. Validate container,
then staging edge because Dokploy/Traefik may rewrite headers. Prior web SHA is
rollback.

**Do not.** Do not raise budgets for unexplained growth, immutable-cache HTML,
or turn off buffering/compression globally.

**Stop if.** Deployed headers differ from container, CSP origins are incomplete
(leave report-only), or an ordinary endpoint demonstrably requires old generic
unbuffered behavior.

**Commit/evidence.** CH-4.6A and B are separate commits. Evidence includes
curl/header, SSE timing, port scan, and bundle report.

### CH-4.7 - Batch measured N+1 paths and justify every index

**Objective and risk.** Remove known query-count growth and paginate the project
list without speculative indexes or silent frontend truncation.

**Files/symbols.**

- <code>backend/app/inbox/split_service.py::_attach_split_provenance</code>
- <code>backend/app/intake/repair_service.py</code>
- <code>backend/app/intake/sort_service.py</code>
- <code>backend/app/database/projects.py::list_projects</code>
- <code>backend/app/api/projects.py::get_projects</code>
- consuming frontend project-list query/<code>HomePage</code> UI
- CH-4.3's signed cursor codec and API-only signing secret
- new query-budget/cursor integration tests

**Red baseline/tests.**

- SQL counts for 1, 25, and 100 items;
- split provenance makes per-sheet source lookup;
- repair/sort perform per-file gets;
- project list is unbounded;
- <code>HomePage</code> assumes one complete project array and has no explicit
  page-two action;
- stable project cursor order is
  <code>(updated_at DESC, id DESC)</code> with equal timestamps;
- capture <code>EXPLAIN (ANALYZE, BUFFERS)</code> on representative data.

**Implementation child packets.**

1. **CH-4.7A - split provenance.** Batch split-provenance rows by project/path
   and map in memory.
2. **CH-4.7B - repair/sort.** Batch source-document IDs for repair/sort.
3. **CH-4.7C - project pagination.** Add a new bounded project keyset endpoint
   at the exact path <code>GET /projects/paged</code>, registered/tested before the
   dynamic project-ID route so it cannot be captured. It accepts
   <code>cursor: str | None</code> and <code>limit</code> default 50/max 100 and
   returns exactly <code>ProjectPage {items,next_cursor,total_count}</code>.
   Preserve order <code>(updated_at DESC,id DESC)</code>. Reuse CH-4.3's
   purpose/version-aware HMAC codec: the one-hour cursor binds owner, endpoint,
   order, last timestamp, and ID; parse manually and return the same non-leaking
   <code>400 {"code":"invalid_cursor"}</code> for malformed, expired, foreign,
   or tampered input. Anchor deletion remains valid, repeated requests are
   idempotent, and the server never emits the request cursor as
   <code>next_cursor</code>. Convert <code>HomePage</code> to an infinite query with
   explicit accessible Load more, loaded/total count, stable ID deduplication,
   and server order. Every create/rename/archive/delete or other
   ordering-affecting mutation invalidates the project-page query instead of
   editing its order in place. Apply the one-reset/no-loop cursor rule from
   CH-4.2. Retain the old unbounded response only for the prior release-record
   image, add safe call/byte telemetry and a conservative rate limit, and create
   a post-launch cleanup packet after the rollback floor advances.
4. **CH-4.7D - justified indexes.** Use <code>pg_stat_statements</code> and
   representative plans to rank remaining queries. Add only indexes that change
   measured plan/latency enough to justify write/storage cost.

**Verification.** Query count remains constant or explicitly bounded from 1 to
100; project records after page one are accessible; equal timestamps and
concurrent insertion do not duplicate/skip the existing sequence; before/after
p50/p95 and plans improve without semantic drift. Limit 0/101, malformed,
expired, foreign, tampered, repeated, anchor-deleted, and injected non-advancing
cursor cases meet the exact response/reset contract; ordering mutations refetch
rather than leave stale page membership.

**Observability.** Normalized query fingerprint/count/duration/rows and page
response bytes; no SQL parameters.

**Migration/rollout/rollback.** Deploy the new cursor endpoint, then its client.
Retain the old response through GATE-6 and the prior-image rollback window;
contract deletion is not part of this task. Each justified index has its own
concurrent-safe migration and disposable downgrade. Keep an index during app
rollback unless harmful.

**Do not.** Do not add indexes from code inspection alone, use offsets, silently
slice the response without frontend pagination, or delete the old route while it
is the release-record rollback path.

**Stop if.** Representative data/plan is unavailable, an index does not alter
the plan, a consumer still assumes a complete list, or CH-4.3's cursor
codec/secret is not available.

**Commit/evidence.** CH-4.7A, B, C, and D are separate commits with raw
query-count/plan evidence.

## 13. Stage 5 - engineering guardrails and optional structural depth

### CH-5.1 - Add a true project-profile lifecycle drift guard

**Proposed disposition.** Defer unless a maintainer promotes this optional task
after GATE-4. The ledger remains <code>not-started</code> until that decision and
may become <code>deferred</code> only through explicit approval.

**Objective and risk.** A newly accepted profile field cannot be silently
dropped between create, persistence, patch/clear, proposal, read model, and
frontend types.

**Files/symbols.**

- <code>backend/app/schemas/projects.py::ProjectProfileField</code>
- <code>backend/app/projects/profile.py::PROFILE_FIELDS</code>
- create/read/patch routes and persistence mapping
- taxonomy/column classification and profile proposal handling
- frontend profile types
- new public-interface lifecycle tests

**Red tests/baseline.**

1. POST create with a distinct sentinel per accepted field; capture disposable
   DB or persistence arguments; GET read back.
2. PATCH each field plus explicit clear semantics.
3. Every Literal value has exactly one approved storage class and mutation path.
4. Frontend field/type parity where applicable.
5. Mutation test: remove one carried field from a mapper and prove failure.

**Implementation.**

1. Derive <code>PROFILE_FIELDS</code> from
   <code>typing.get_args(ProjectProfileField)</code> with a precise tuple type.
2. Define a small explicit lifecycle classification for taxonomy-backed,
   column-backed, computed/read-only, or proposal-only behavior. This is an
   invariant, not a generic field framework.
3. Test through public create/patch/read interfaces; do not test only a private
   mapping helper.
4. Cover proposal accept/reject for fields that use it and reject unclassified
   additions.
5. Keep sentinels semantically valid and distinct.

**Verification.**

    Set-Location backend
    uv run pytest tests/projects -k "profile" -q
    uv run pytest -m "not integration and not tender_eval" -q
    Set-Location ../frontend
    pnpm typecheck
    pnpm test

**Observability/migration/rollback.** No schema unless the test uncovers a real
missing column, which requires a separately reviewed task. Revert derivation and
tests together only if source typing changes.

**Do not.** Do not overbuild a reflection framework or declare key presence a
round trip.

**Stop if.** A field's storage/mutation semantics are ambiguous or a schema
migration is unexpectedly needed.

**Commit/evidence.** Derivation/classification and lifecycle tests in one small
commit.

### CH-5.2 - Roll out high-signal Ruff rules in reviewed layers

**Proposed disposition.** Defer unless a maintainer promotes this optional task.
It improves defect detection but is not a production runtime gate. The ledger
remains <code>not-started</code> until explicit approval records otherwise.

**Objective and risk.** Catch real Python defects without burying review under
line-length noise, FastAPI false positives, or unsafe repo-wide autofixes.

**Files.** <code>backend/pyproject.toml</code> and the files reported by each
selected rule.

Reference:
[Ruff B008 guidance](https://docs.astral.sh/ruff/rules/function-call-in-default-argument/)
and [Ruff settings](https://docs.astral.sh/ruff/settings/).

**Red baseline.** Capture rule-by-rule counts on the current SHA. The review
observed thousands when selecting all <code>E</code>, including 2,275 E501 and
249 idiomatic B008; rediscover rather than use those totals.

**Implementation packets.**

1. Pin Python target 3.12 and the existing line policy. Keep E501 excluded from
   this plan.
2. Enable/fix genuine <code>B023</code> closure and <code>B905</code>
   strict-zip findings manually with behavioral tests.
3. Audit FastAPI/Pydantic default factories and configure fully qualified known
   immutable calls. Do not ignore all B008 or all B rules.
4. Enable remaining high-signal bugbear rules and fix in domain-sized commits.
5. Add import sorting (<code>I</code>) as a mechanical-only commit and verify no
   import-cycle/side-effect change.
6. Add safe upgrade rules (<code>UP</code>) in bounded batches.
7. Treat simplification rules (<code>SIM</code>) as optional readability work;
   skip transformations that obscure domain code.

**Verification.**

    Set-Location backend
    uv run ruff check app ingest tender tests
    uv run pytest -m "not integration and not tender_eval" -q

Run focused behavior tests for every nonmechanical fix and
<code>git diff --check</code>.

**Observability/migration/rollback.** Tooling only. Each rule packet can be
reverted independently.

**Do not.** No <code>--unsafe-fixes</code>, broad noqa, E501 rollout, or mixing
logic refactors with import formatting.

**Stop if.** A rule generates broad low-signal churn, a FastAPI call's
immutability is uncertain, or behavior changes without a regression test.

**Commit/evidence.** One rule family per commit with before/after counts and
tests.

### CH-5.3 - Benchmark an opt-in bounded pytest-xdist lane

**Proposed disposition.** Defer unless a maintainer promotes this optional task.
It improves feedback time but is not a launch gate. The ledger remains
<code>not-started</code> until explicit approval records otherwise.

**Objective and risk.** Improve feedback time only when measured, without
oversubscribing developer/CI machines, parallelizing integration/evals, or
making focused debugging surprising.

**Files.** <code>backend/pyproject.toml</code> dev group/markers,
<code>.github/workflows/ci.yml</code>, backend testing documentation, and tests
requiring order/global-state fixes.

Reference:
[pytest-xdist distribution modes](https://pytest-xdist.readthedocs.io/en/stable/distribution.html).

**Preconditions.** CH-0.2 passes; all selected tests are offline and
order-independent.

**Baseline.** Warm once, then run serial, <code>-n 2</code>, and
<code>-n 4</code> three times on the actual Linux CI runner and a normal
developer machine. Record wall/CPU/peak RSS and identical node/pass/skip sets.

**Implementation.**

1. Add pytest-xdist as a dev dependency with dependency-policy justification.
2. Fix shared fixed paths, global env/cache mutation, or order dependence rather
   than grouping everything.
3. Where serialization is legitimate, mark groups and invoke
   <code>--dist loadgroup</code>; the marker alone has no effect.
4. Choose a bounded worker count from results, normally two on current hosted
   CI unless four materially improves without memory pressure.
5. Put the parallel command in a named CI step/documented command. Do not add
   <code>-n auto</code> or parallel flags to global <code>addopts</code>.
6. Retain explicit serial, focused, database-integration, Tender-eval, and debug
   commands.

**Verification/thresholds.** Identical collected node IDs/outcomes; three
repeatable passes; no network; no orphan processes; peak resource stays within
CI budget. Adopt parallel CI only if median wall time improves at least 20%
without worse flake rate. Otherwise complete as
<code>not-applicable-approved</code> and keep serial.

**Observability/migration/rollback.** CI timing only. Roll back the parallel CI
step while retaining independence fixes.

**Do not.** Do not parallelize live DB/provider/eval tests or hide failures with
reruns.

**Stop if.** Outcomes differ, flakes emerge, or memory/process use is
unacceptable.

**Commit/evidence.** Dependency/independence fixes then CI selection. Benchmark
table is required.

### CH-5.4 - Enrol every database, security, and concurrency contract in CI

**Objective and risk.** CH-0.8 already created the isolated Postgres/pgvector
runner. This task makes every completed schema, grant/RLS, lock, lease, fencing,
idempotency, and queue invariant a required release check instead of leaving the
runner as a token smoke test.

**Files/symbols.**

- <code>.github/workflows/ci.yml</code>
- CH-0.8's <code>scripts/test-database.ps1</code> and compose definition
- <code>backend/pyproject.toml</code> markers and test collection configuration
- new <code>backend/tests/database_contract_manifest.json</code> or equally
  reviewable inventory
- all DB-backed tests produced by CH-1 through CH-4

**Preconditions.** CH-0.8 passes twice from a clean checkout. CH-0.2's exact
test-DB network allowlist remains active. This task must reuse that runner rather
than add a second database service or marker.

**Red baseline.** Run CI with collection reporting and prove which completed
contracts are absent, skipped, or still hidden under the broad
<code>integration</code> marker. A green job that collects zero expected tests is
a failure.

**Required contract inventory.** Map every entry to exact test node IDs or a
narrow marker, expected minimum collection count, owning task, and migration
revision where relevant. At minimum include:

- fresh/repeated migration to one head, changed previous-head upgrade, promised
  downgrade, migration lock, and compatibility-spec/release-record checks from
  CH-1.13;
- CH-1.5 app-table catalogue, owner-scoped access, grants, RLS, and cross-owner
  negative cases for every table added anywhere in the plan;
- Tender queue-scope isolation/backfill/claim conflicts from CH-2.1;
- Tender scope/claim/heartbeat/expiry/fence and continuation publication/dedup
  from CH-2.2 and CH-2.3;
- agent-turn execution scope, admission/idempotency, expiry reaping, and
  cross-process revocation from CH-2.4;
- Stripe event ordering/idempotency from CH-2.5;
- cleanup generation/claim/canonical-object races from CH-2.6;
- core-workflow lock order, claim, publication, cancellation, and reaper
  interleavings from CH-2.7;
- parser queue scope/lease/fence/hard-timeout state transitions from CH-3.4;
- Tender pipeline-admission active-key, per-user cap, generation/fence,
  cancel/supersede, terminal-release, and abandoned-row reconciliation from
  CH-3.7;
- project-event high-water capture/concurrency from CH-4.1;
- chat/Tender invalid/foreign/non-advancing cursor isolation from CH-4.2;
- evidence page cursor/batch ownership/query-budget and workspace-directory page
  contracts from CH-4.3;
- project pagination cursor/query-plan/index contracts from CH-4.7C/D.

**Implementation.** Update the manifest whenever an owning task completes. The
CI lane must create required extensions and least-privilege test roles, migrate,
run CH-1.5 first, execute the manifest-selected tests, and run CH-1.5 again after
all migrations. Fail on missing node ID, unexpected skip/xfail, collection below
the declared minimum, external provider request, leaked credential, or a schema
head mismatch. Repeat deterministic contention/claim cases enough to exercise
their barriers (initially 20 iterations); do not multiply paid or time-based
provider tests. Keep the measured job timeout at 15 minutes initially and split
the matrix by contract family only if timings prove it necessary.

For every migration changed in the pull request, seed the prior supported head,
run CH-1.13's exact held-connection migration command to target head, exercise
the embedded compatibility specification, run the promised disposable downgrade if one
exists, and return to head. Upload only sanitized schema/plan/test diagnostics on
failure. The plain image does not reproduce Supabase Storage; Storage isolation
remains a staged/live CH-1.5 and GATE-6 proof.

**Verification.** Two clean CI runs collect at least the manifest minimums and
pass; fresh and repeated migrations end at the same head/schema; security
catalogue has zero unclassified tables; contention repeats have no lost/duplicate
commit; and attempts to substitute Supabase or contact OpenAI, Stripe, Storage,
or search fail before network I/O.

**Observability/migration/rollback.** Publish a sanitized summary containing
image digest, Postgres/extensions, migration heads, manifest digest, collected/
passed/skipped counts, repetition count, and duration. This is a permanent
required lane. Updating its database image or contract inventory is reviewed;
removing the lane reopens GATE-5.

**Do not.** Do not recreate CH-0.8, expose its DB, use production dumps, silently
exclude slow invariants, or call a provider test database integration.

**Stop if.** The manifest cannot map a claimed invariant to an exact test,
selected code contacts an external provider, test roles cannot represent the
approved DB contract, or the lane is flaky under controlled repetition.

**Commit/evidence.** One manifest/CI-enrolment implementation commit and one
coordination commit containing two green run URLs and summary digests.

### CH-5.10 - Build load, fault, and production-acceptance harnesses before freeze

**Objective and risk.** Put every executable Stage 6 driver, safety check,
reconciliation rule, runbook, and evidence template into the tested source tree
before CH-5.5 builds the final candidate. Stage 6 must exercise an immutable
candidate; it may not add scripts, tests, configuration, or runbook logic after
the candidate source/image is frozen.

**Files/artifacts.** Exact locations are:

- <code>scripts/load/run-staging-load.py</code>,
  <code>scripts/load/scenario-contract.json</code>, and focused offline tests under
  <code>backend/tests/hardening/</code>;
- <code>scripts/hardening/run-failure-rehearsal.ps1</code>,
  <code>scripts/hardening/failure-contract.json</code>, and its checked-in
  deliberate-failure/self-test fixtures;
- <code>docs/runbooks/failure-recovery-rehearsal.md</code>, the Pi-only update to
  [Stage 9 production acceptance](../runbooks/stage-9-production-acceptance.md),
  and the core-worker/deployment cross-links it invokes;
- <code>docs/acceptance/production/template.md</code> and machine-readable
  evidence schemas/templates for CH-6.1, CH-6.2, and CH-6.3; and
- CH-0.9's fixed handler contract/tests for the new pre-freeze harness check and
  later Stage 6 evidence-only handlers.

Use existing Python, <code>httpx</code>, PowerShell, and repository test tooling.
Any proposed new development dependency requires the repository dependency
justification and explicit maintainer approval; add no runtime dependency.

**Red baseline.** Prove and record all current failures before implementation:
there is no one-command statistically honest load driver, no closed fault-action
dispatcher with an exact target allowlist, no machine-verifiable reconciliation
snapshot, Stage 9 still contains obsolete Hermes assumptions, and the production
record cannot distinguish <code>ready-to-open</code> from an already-open release.
An existing prose-only command is not a passing harness.

**Implementation child packets.** These are source-changing packets and all must
finish before CH-5.5A.

1. **CH-5.10A - deterministic load harness.** Implement a stdlib/<code>httpx</code>
   scheduled-arrival driver with a versioned JSON scenario contract. Inputs are
   explicit target manifest, candidate SHA/digests, seed, synthetic fixture IDs,
   warm-up, arrival rate/concurrency, duration, request-class weights, per-class
   timeouts, provider-spend ceiling, and output directory. The target manifest
   contains the exact API origin, environment marker, Supabase project reference
   hash, Storage bucket/prefix, Dokploy application/service IDs, and expected
   image digests. It is data, never executable source.

   Record scheduled and actual start, latency, status/error class, request class,
   safe correlation/run ID, and generator CPU/RSS/network health. Detect dropped
   samples and coordinated omission. Compute percentiles only from retained raw
   samples using the Stage 6 minimum-sample rules; never merge route classes.
   Implement deterministic synthetic setup and generation-bound scoped cleanup,
   but require explicit live opt-in and the target preflight before either. Unit
   test configuration rejection, deterministic seeds, byte/time/spend caps,
   percentile fixtures, delayed-start accounting, generator-invalid conditions,
   Ctrl-C cleanup, output sanitization, and nonzero propagation against a local
   stub. The driver does not contain production credentials or a production URL.
2. **CH-5.10B - default-deny fault and reconciliation harness.** Implement a
   closed PowerShell <code>switch</code> over named fault IDs; no arbitrary command
   string, <code>Invoke-Expression</code>, downloaded code, or public fault
   endpoint. Before even displaying an actionable fault, resolve and compare the
   API origin, environment marker, Supabase project/database identity, Storage
   bucket/prefix, Dokploy application/service IDs, candidate SHA, and image
   digests to a reviewed allowlist and a hard production denylist. Unknown,
   missing, redirected, mixed, or production identity exits nonzero. Require a
   separate <code>-AllowStagingFaults</code> switch after the safe manifest is
   displayed; typing a word is not authorization.

   Freeze one-fault-at-a-time handlers for graceful/forced API, Tender, workflow,
   parser, and cleanup termination; bounded DB disconnection; fixture-scoped
   Storage upload/delete failure; provider timeout/429; Pi cancellation/child
   kill; Stripe test-mode duplicate/reversal; prior-image rollback; and isolated
   restore orchestration. Runtime fault flags are test/staging-only and production
   startup rejects them. Each handler takes a before snapshot, observes the named
   alert/recovery, restores healthy state, and compares rows, versions,
   generations, leases/fences, dedup keys, objects, accepted artefacts, and child
   processes through a versioned reconciliation schema. A no-op/dry run verifies
   identity and snapshot permissions without enabling a fault. Self-tests inject
   every wrong/missing identity, production target, unknown fault, skipped
   reconciliation, nonzero subcommand, secret canary, and cleanup-scope escape.
3. **CH-5.10C - Pi-only acceptance contracts.** Remove Hermes assumptions from
   the executable acceptance runbook and make the retained legacy PydanticAI path
   explicitly rollback-only until a separate post-acceptance cutover. Freeze the
   load, fault, restore, migration/security, two-owner product-journey, Stripe,
   cleanup, signer, freshness, release identity, and traffic-control fields in the
   Stage 6 templates. The production recommendation is exactly
   <code>ready-to-open|no-go</code>; it does not open public traffic. Only the later
   passing GATE-6 record can authorize a separately logged operator traffic-open
   action. Add CH-0.9 handlers that consume immutable CH-6 evidence and fail on a
   missing field, stale proof, wrong SHA/digest/target, or absent signer; the
   handlers may not mutate the target.

**Verification.** All of the following pass before candidate build:

    Set-Location backend
    uv run pytest tests/hardening -q
    Set-Location ..
    pwsh -NoProfile -File scripts/hardening/run-failure-rehearsal.ps1 -SelfTest

Additionally, two local-stub load runs with the same seed produce the same
request schedule/count and sanitized schema; a deliberately slow stub is marked
generator/target-invalid as designed; every fault preflight negative exits
nonzero before an action; a staging no-op proves target identity without changing
state; runbook/template validation rejects one omitted required field and obsolete
Hermes language; and CH-0.9 recognizes every fixed Stage 6 handler while refusing
an unknown one. Record script/config/template SHA-256 digests.

**Observability.** Harness output contains only safe run/handler IDs, timestamps,
candidate/target hashes, resource/sample counts, outcome classes, and raw-artifact
digests. It never records credentials, headers, prompts, document/customer
content, signed URLs, raw database/Storage identifiers, or unbounded exception
text.

**Migration/rollout.** No application schema or production rollout. Land all
three packets, run offline self-tests and the authorized staging no-op, then make
their exact Git/blob digests inputs to CH-5.5's release record. Any later harness,
scenario-contract, runbook, template, or gate-handler change is a source change
that invalidates the frozen candidate and restarts CH-5.5A.

**Rollback.** Before freeze, revert a packet as one unit and keep CH-5.10/GATE-5
red. After freeze, do not patch the harness; block Stage 6 and create a new
candidate from the corrected source.

**Do not.** Do not target production during harness development, embed a secret
or mutable environment default, permit arbitrary shell, install a load framework
without approval, fabricate percentiles, combine faults, or let a runbook edit
masquerade as evidence-only coordination after freeze.

**Stop if.** Exact target identity cannot be resolved, production denial cannot
be proved, synthetic setup/cleanup is not generation-scoped, a fault lacks a
deterministic reconciliation query, or a required provider/host action has no
authorized operator path.

**Commit/evidence.** CH-5.10A, B, and C are separate implementation/evidence
pairs. Evidence includes deliberate-failure transcripts, local-stub raw digests,
staging no-op attestation, sanitized contract digests, and the exact source commit
that CH-5.5 must build.

### CH-5.5 - Freeze and revalidate the release-candidate supply chain

**Objective and risk.** Produce one final candidate only after every workflow,
base, compatibility-spec, lockfile, and runtime input is remediated, then freeze
that exact output and prove no later gate or promotion rebuilds or changes it.
Earlier CH-1.7 images are staging proofs, not automatically the final candidate.

**Files/artifacts.** CI/release workflows, Dockerfiles, lockfiles, resolved
compose, CH-1.7 build/smoke machinery, software bill of materials (SBOM),
vulnerability reports, provenance/attestation where the selected registry
supports it, and the embedded compatibility specification and SHA-specific
release record.

**Preconditions.** CH-1.7A-C, CH-5.4, CH-5.6, and all CH-5.10 pre-freeze
harness/runbook packets are green. A maintainer has
recorded the approved registry, vulnerability severity/exception policy, scanner
and update owner, and retention location. Do not let the implementing agent
quietly choose a release policy.

**Red baseline.** Demonstrate any workflow action referenced only by a mutable
major tag, any unpinned Docker base, missing SBOM/provenance, unexplained image
growth, or a release step capable of rebuilding after the freeze instead of
consuming the candidate digests.

**Implementation child packets.**

1. **CH-5.5A - pre-build input remediation and one candidate build.** Pin
   third-party workflow actions to reviewed full commit SHAs with version
   comments. Recheck
   Docker base digests and remediate approved source/dependency/image findings.
   Finalize and commit the machine-readable build compatibility specification
   with target/accepted revisions, schema/API/tool capabilities, temporary
   defaults/dual writes, and minimum rollback capability. Any action/base/spec/
   lockfile/source change invalidates earlier digests. Only after inputs are
   stable, invoke CH-1.7B's hardened build/smoke exactly once for this candidate.
   Generate SBOMs and scans from the resulting images and record sizes; establish
   the first accepted baseline and thereafter fail unexplained growth over 5%.
2. **CH-5.5B - post-build release record and freeze proof.** Create the Section
   3.5 signed/checksummed release record containing Git SHA, API/web/base
   digests, embedded compatibility-spec digest, action SHAs, Pi version,
   lockfile/SBOM/report digests, exact CH-5.10 harness/scenario/runbook/template/
   gate-handler digests, scan exceptions with owner/expiry, final CH-1.5 security
   result, prior SHA/digests, and rollback floor. Run all container,
   delivery, readiness, and pre-freeze browser prerequisites against those frozen
   images by digest. Release/Dokploy inputs consume the exact digests; fail if a
   build occurs, a tag resolves differently, or an input differs. Any further
   source/config/build-input/runtime change creates a new candidate and restarts
   CH-5.5A; only evidence/record coordination may follow without rebuilding.

**Verification.** Re-running validation without rebuilding produces the same
API/web digests and candidate-record digest; all scans meet the approved policy;
no production secret/canary exists; UID/Pi/health/Nginx/delivery contracts still
pass; the embedded spec/release record has no unknown capability/table; and the
staging host reports the exact frozen digests.

**Observability/migration/rollback.** Publish sanitized candidate metadata and
report links, never raw credentials or proprietary file contents. A new base,
lockfile, action, exception, or image digest creates a new candidate and reruns
all dependent gates. Rollback may select only the release record's compatible
prior digest and never downgrades production data automatically.

**Do not.** Do not build before CH-5.5A inputs are final or rebuild after CH-5.5B
freeze, promote mutable tags, accept an
unowned/unbounded vulnerability exception, expose scanner findings containing a
secret, or mistake retained legacy source for a forbidden Hermes runtime.

**Stop if.** A digest cannot be traced to the green build, the registry cannot
preserve immutable identity, a critical vulnerability/secret is unresolved, a
new table is absent from CH-1.5, or the prior image is below the rollback floor.

**Commit/evidence.** CH-5.5A produces the final source/build implementation commit
and its evidence coordination commit. CH-5.5B creates only signed release-record,
evidence, and ledger coordination commits while retaining CH-5.5A's
<code>CandidateSourceSha</code>; it must not create an empty or source-changing
implementation commit. Evidence includes the candidate record, SBOM/report
digests, size delta, compatibility spec/release record, and no-post-freeze-
rebuild/staging-digest proof.

### CH-5.6 - Build deterministic browser coverage and fix accessibility

**Objective and risk.** Establish deterministic production-image browser specs
and make required accessibility/UI corrections before the final candidate is
built and frozen. This task is allowed to modify frontend code and lockfiles.

**Files/symbols.**

- CH-4.0's pinned Playwright/browser installation and performance configuration
- new general <code>frontend/playwright.config.ts</code> and
  <code>frontend/e2e/</code> that reuse the same browser version
- package/lockfile and CI
- repository/activity/recovery components
- production-image deterministic fixture configuration
- shared <code>frontend/e2e/support/browser-failure-collector.ts</code>

**Dependency decision.** Playwright was already approved and added by CH-4.0;
do not install a second copy/version. Add <code>@axe-core/playwright</code> as a
dev-only dependency. The commit must state that WCAG accessibility-tree analysis
is a standard, nontrivial capability not safely recreated in 30 lines and record
its footprint.

**Red baseline.** The required production-container/auth/accessibility suite
does not exist. Record current keyboard/focus/axe findings and demonstrate that
jsdom/Vite-only checks cannot prove Nginx delivery or same-tab A-to-B isolation.

**Required deterministic specs.**

- <code>delivery-headers.spec.ts</code>
- <code>route-resilience.spec.ts</code>
- <code>chat-stream-recovery.spec.ts</code>
- <code>repository-keyboard.spec.ts</code>
- <code>auth-cache-isolation.spec.ts</code>

**Implementation child packets.**

1. **CH-5.6A - deterministic production-container browser specs.** Extend
   CH-4.0 rather than replacing it. Run the required specs against a freshly
   built production Nginx image with approved mocked/seeded backend dependencies,
   never the Vite dev server. This is a pre-freeze image; CH-5.9 reruns the suite
   against the later frozen digest. Test desktop Chromium and a 390x844 viewport.
   Use event/assertion waits only and save trace/screenshot/video on failure.
   Add one shared collector used by this task and CH-5.9. It records every
   <code>pageerror</code> (including unhandled promise rejection), console
   <code>error</code>, and <code>requestfailed</code>. Each spec starts with an
   empty allowlist. Before injecting a deliberate route/stream failure, the spec
   must register an exact test-scoped expectation containing failure kind,
   method/URL pattern where applicable, error pattern, and exact count. Teardown
   fails on every unmatched event and every registered event not observed exactly
   that many times; expectations cannot be shared globally or use a catch-all.
2. **CH-5.6B - accessibility fixes and assertions.** Replace click-only
   repository rows with a native title button and checkbox; use selected state
   where useful, never a button-role row containing nested controls. Restore
   visible ActivityFeed focus rings and raise very small controls to at least
   24x24 CSS px, 44x44 where touch layout permits. Run axe on login, home,
   cockpit, chat-expanded, and Tender.
**Verification/thresholds.**

- zero serious/critical axe violations;
- zero unexpected page/console/unhandled-promise/network failures, and every
  deliberately injected failure occurs exactly as registered by its owning spec;
- primary repository actions keyboard-operable and focus visible;
- deep link loads through Nginx;
- deterministic interrupted-stream and A-to-B fixture cases pass;
- CH-4.6 container headers pass;
- two consecutive deterministic runs pass after all CH-5.6B fixes.

**Observability/migration/rollback.** Tests and accessibility UI only. Test
artifacts have short approved retention and synthetic data. Test-only rollback
does not justify shipping a failed runtime.

**Do not.** Do not use fixed sleeps, production users/data, or waive serious
findings without owner/reason/expiry. Do not ignore console/network errors by
substring globally or let a deliberate fault weaken another spec.

**Stop if.** Required accessibility semantics remain unresolved or deterministic
fixtures need production credentials/provider network.

**Commit/evidence.** CH-5.6A and B are separate commits. Browser run links,
axe summaries, and failure-artifact digests are evidence.

### CH-5.7 - Optional: split project routes by vertical domain

**Proposed disposition.** Defer. The ledger remains <code>not-started</code>
until a maintainer explicitly records <code>deferred</code> after all required
Stage 5 work passes; the prose itself is not approval.

**Objective and value.** Improve navigation/edit locality in the very large
project route module. This is not a runtime optimization and must not be sold as
one.

**Risk addressed.** Navigation/edit collisions and accidental cross-domain
changes after agent-generated modifications; no customer latency claim.

**Files/symbols.** <code>backend/app/api/projects.py</code>, the proposed
<code>backend/app/api/project_routes/</code> modules, router registration,
normalized OpenAPI snapshots, and route/monkeypatch contract tests.

**Preconditions/contracts.**

- snapshot normalized OpenAPI plus registration order, method/path, route name,
  operation ID, prefix, dependencies/security, response model, status, tags,
  and representative request behavior;
- inventory test monkeypatch seams under <code>app.api.projects.*</code>;
- all prior security/pagination/upload interfaces are green.

**Red baseline.** Capture the normalized route/OpenAPI digest and current patch
seams, then prove no existing test would detect a route registration/order or
dependency change caused solely by moving code.

**Implementation.**

1. Create non-colliding <code>backend/app/api/project_routes/</code>; do not
   create a package named beside <code>projects.py</code>.
2. Keep <code>projects.py</code> as stable router/facade during migration.
3. Group by vertical domain (profile/lifecycle, events/cockpit,
   workspace/inbox/files, evidence, drafts/exports, cost/workflow adapters)
   only after inventory confirms actual routes.
4. Move one domain per commit with explicit dependency injection/imports.
5. Preserve or deliberately update patch seams; avoid re-export webs that
   obscure ownership.
6. After each move, compare full OpenAPI/route snapshot and focused requests.
7. Remove facade code only when all callers/tests import the intended interface.

**Verification.** Byte-for-byte normalized contract equivalence except approved
module-only changes; full offline/backend DB/browser gates; no new circular
imports; a representative change in a domain touches fewer unrelated modules.

**Observability/migration.** No schema or runtime telemetry change is expected.
Compare startup/import errors and route registration digest during rollout.

**Rollback.** Revert one domain move at a time.

**Do not.** Do not combine behavior fixes, chase a line-count target, or alter
registration order accidentally.

**Stop if.** Snapshot differs, a circular import appears, or facade patch
compatibility requires a deeper design decision.

**Commit/evidence.** One vertical domain per commit; contract digests before and
after.

### CH-5.8 - Optional: split MCP tools by domain after capability enforcement

**Proposed disposition.** Defer. The ledger remains <code>not-started</code>
until a maintainer explicitly records <code>deferred</code> after CH-1.1-1.3 and
all required Stage 5 checks; the prose itself is not approval.

**Objective and value.** Improve locality while preserving every MCP and Pi
contract. The security benefit comes from CH-1, not from smaller files.

**Risk addressed.** High edit-collision and review cost in one registration
module; authorization behavior is already owned by CH-1.

**Files/symbols.** <code>backend/app/mcp_bridge/server.py</code>, proposed domain
registration modules, the central CH-1 capability registry, Pi tool-visibility
configuration, and tool-contract/authorization/import tests.

**Preconditions/contracts.** CH-1.1 complete snapshot covers name, description,
input schema, output/content shape, read/write, required scope, project binding,
feature gate, and Pi visibility. Test patch seams are inventoried.

**Red baseline.** Capture registration/tool-contract/Pi-visible digests and show
that current tests would fail on one injected name/schema/scope/visibility
change before moving any tool.

**Implementation.**

1. Keep a small <code>server.py</code> composition facade.
2. Create explicit domain modules with
   <code>register(mcp, dependencies)</code>; no import-time registration side
   effects.
3. Suggested domains only after inventory: project/profile, evidence/retrieval,
   workspace/files, workflows, cost/artefacts/decisions, Tender adapters.
4. Capability/authorization registry remains central and is not duplicated.
5. Preserve the Tender core import boundary: Clerk core reaches Tender only
   through approved router/MCP adapters.
6. Move one domain per commit and run full contract/authorization tests.
7. Migrate patch seams intentionally; remove temporary facade exports before
   completion where possible.

**Verification.** Complete tool-contract digest and Pi-visible set unchanged;
all 33-or-current mutators still have scope negatives; no duplicate names,
feature drift, circular imports, or import side effects.

**Observability/migration.** No schema change and no new customer telemetry.
Compare startup registration count/digest and tool-denial metrics before/after.

**Rollback.** Revert one domain registration move.

**Do not.** Do not change descriptions/schemas while moving, infer scopes in
domain files, or use wildcard imports.

**Stop if.** Any contract changes or the move would cross the Tender ownership
boundary.

**Commit/evidence.** One domain per commit with before/after contract digest.

### CH-5.9 - Run browser, auth, and SSE acceptance on the frozen candidate

**Objective and risk.** Prove the exact CH-5.5 API/web digests pass deterministic
browser and real staging identity/stream contracts without any source, build,
image, or runtime mutation after freeze.

**Files/artifacts.** CH-5.6 Playwright suite; CH-5.5 release record and image
digests; production compose/staging URL; two synthetic Supabase users and owned
projects; browser artifact/evidence paths. No application source file is an
allowed output of this task.

**Red baseline.** A pre-freeze CH-5.6 run cannot prove the frozen digest. Confirm
the staging environment either has not run the exact frozen images or lacks two
consecutive real auth/SSE runs; record this as incomplete, not as a code failure.

**Implementation child packets.**

1. **CH-5.9A - frozen-image deterministic rerun.** Resolve both running
   container digests and embedded SHA/spec digest against the CH-5.5 release
   record. Run every deterministic delivery, route/chunk fault, repository
   keyboard, auth-cache, chat-recovery, performance, and axe spec twice against
   those images. Use CH-5.6's shared failure collector unchanged: every expected
   injected failure must be registered by and observed exactly in its owning
   spec; every other page/console/unhandled-promise/network failure fails.
2. **CH-5.9B - real staging identity and Pi SSE.** Use two dedicated synthetic
   Supabase users, entitlement, and seeded projects. Prove A-to-sign-out-to-B
   cache isolation and Pi SSE interruption/reload semantics from CH-4.5 twice on
   the same frozen digests. Run the prior SPA against every CH-3.4/CH-4.3/CH-4.7
   compatibility endpoint at expected launch/rollback traffic and prove its
   conservative rate limits keep rollback usable. The legacy persistence
   contract remains deterministic test coverage; do not enable an obsolete
   runtime merely for staging.

**Verification/thresholds.** Exact SHA/API/web/spec digests match before and
after; two deterministic runs and two staging runs pass separately; zero
unexpected browser/console/promise/network errors and zero missing/over-counted
registered fault events; zero serious/critical axe
violations; A-to-B never renders A data; Pi recovery has one persisted user/no
partial assistant; compatibility journey has no rate-limit or full-array failure
at expected rollback load.

**Observability/migration/rollback.** No migration or runtime edit. Retain safe
run IDs, environment identity, digests, assertions, compatibility route counts/
bytes/rate decisions, and failure-only browser artifacts. A required source,
config, dependency, or image change invalidates CH-5.5 and returns to CH-5.5A;
do not patch the frozen candidate in this task.

**Rollback.** This is a verification gate. A failed candidate remains
unpromotable; select no production target. Prior staging image may be restored
after evidence capture.

**Do not.** Do not use Vite, mock real staging identity proof, use production
users/data, waive an unexpected error, or change source/runtime to make a frozen
run green.

**Stop if.** Digests differ, synthetic users/fixtures/entitlement are
unavailable, compatibility traffic would affect unrelated users, or any fix is
needed. Record the failure and create a new candidate after the owning task.

**Commit/evidence.** CH-5.9A and B are evidence/coordination commits only. Link
two deterministic and two staging run IDs with artifact digests.

## 14. Stage 6 - production-equivalent load, recovery, and signed acceptance

### CH-6.1 - Run a reproducible staging load and soak gate

**Objective and risk.** Establish capacity, latency, resource, queue, and spend
envelopes on the exact release-candidate image before production traffic. The
load generator and sample counts must be strong enough that percentiles describe
the service rather than the generator or a handful of requests.

**Files/artifacts.**

- CH-5.10A's frozen <code>scripts/load/run-staging-load.py</code>, scenario
  contract, offline tests, and recorded blob/config digests;
- [Stage 6 performance report](../performance/2026-07-19-stage-6-performance.md)
  as read-only historical context;
- the frozen Tender performance harness/readme; and
- new evidence only under
  <code>docs/acceptance/hardening/CH-6.1/&lt;date&gt;-&lt;short-sha&gt;.*</code> plus
  approved external raw-sample storage. No source/runbook/config path is an
  allowed output of this task.

**Preconditions.**

- staging matches image digests, service count, host class, region, DB pool,
  worker concurrency, Nginx, and feature settings; document deviations;
- the load generator runs on a separate controlled host/runner in the recorded
  region, never inside the application host or containers;
- synthetic users/projects/documents only;
- maintainer defines expected launch concurrency (1x), 2x target, and overload
  step; provider spend cap is explicit;
- all Stage 5 gates are green; and
- harness/scenario/template digests equal the CH-5.5 release record and
  CandidateSourceSha. A mismatch returns to CH-5.5A rather than being patched.

**Baseline and scenarios.**

1. Capture idle CPU/RSS/connections/disk/queues and generator CPU/RSS/network.
2. Warm up, then run separately and mixed: health/readiness, home/project and
   cockpit bootstrap, paged reads/evidence, typical/max upload, agent SSE and
   cancel, core workflows, Tender processing/QA, export, and auth transition.
3. For the ordinary API mix, run 1x and 2x for at least 30 steady-state minutes
   each after warm-up. Use a controlled overload step for at most ten minutes to
   prove 429/backpressure and recovery, not to crash the host.
4. Tender live harness follows its documented five cold/warm pairs and explicit
   cost budget. Run at least ten complete provider-backed synthetic workflows if
   the approved cap permits; otherwise mark the low-volume capacity claim
   unproven rather than inventing a percentile.
5. Retain every raw latency/resource/error sample, scheduled-versus-actual start
   time, response class, request class, scenario seed, and exact configuration.

**Implementation/execution - no source changes.** Execute CH-5.10A's exact
checked-in scenario configuration and synthetic-data setup/cleanup; prove a
one-user dry run; then run isolated stepped
scenarios, mixed 1x/2x load, controlled overload, and a two-hour pre-soak. Use a
scheduled-arrival driver for ordinary traffic and record delayed starts so queue
delay is not hidden by coordinated omission. Bound provider-heavy workflows by
concurrency and spend. Synchronize clocks and correlate a safe run ID through
client/server telemetry. Stop between phases to reconcile errors, jobs, objects,
and spend.

The run is invalid and must be repeated if generator CPU exceeds 70 percent for
more than one minute, generator memory exceeds 80 percent, outbound network is
saturated, the generator drops samples, or clocks cannot be reconciled. A larger
generator is the remedy; lowering reported load after the fact is not.

**Verification - required measurements/gates.**

- for each ordinary route/class: count, throughput, p50/p95 and p99 only with at
  least 1,000 successful samples; never merge different routes into one
  percentile;
- for low-volume paid workflows: report every observation plus median and max;
  do not present p99, and label p95 descriptive unless it has at least 100
  samples;
- warm cockpit bootstrap p95 <=500 ms;
- settled Tender QA p95 <=800 ms when the stage has at least 100 observations;
  below that count, publish every observation/median/max and require an explicit
  maintainer acceptance instead of claiming a stable p95;
- ordinary API unexpected 5xx/timeout rate below 0.5%, with expected 4xx/429
  counted separately and matched to the scenario;
- zero OOM, container restart, pool timeout, lost job, or duplicate result;
- pool wait p95 below 100 ms;
- at least 25% memory headroom and 15% disk free at peak;
- queues remain inside CH-3.2 thresholds and drain after load;
- TCM spend <=A$15/comparison;
- existing bundle/delivery budgets pass;
- Tender 90 seconds remains a measured stretch target unless separately
  promoted to a release gate;
- every other supported percentile and every low-volume max receives an explicit
  accept/fix decision, not an omitted result.

**Observability.** All Stage 3 dashboards and alerts active. Correlate safe load
run ID/SHA with resource and provider spend.

**Migration/rollback/cleanup.** No code or schema change and no production
target. Remove synthetic staging data using approved generation-scoped cleanup
and record reconciliation. A failing threshold blocks the candidate; tuning an
approved environment/concurrency value requires a new recorded run, while any
source/config/harness change restarts CH-5.5A.

**Do not.** Do not run on wrong SHA, production URL/project, customer data, or
without telemetry/spend cap.

**Stop if.** Environment mismatch, invalid generator, insufficient samples,
missing raw measurements, uncontrolled cost, or host cannot meet gates after
safe concurrency tuning. Capacity upgrade then requires maintainer approval.

**Commit/evidence.** Evidence/ledger coordination only; no implementation commit.
The record contains environment/generator manifests, immutable harness/config
digests, scenario seed, sample counts, raw digests, validity checks, summarized
results, spend, and bottleneck ranking. A needed code/runbook/config fix leaves
CH-6.1 blocked and returns to a new pre-freeze candidate.

### CH-6.2 - Rehearse failure, isolated restore, and immutable rollback

**Objective and risk.** Expected dependency/process failures recover without
lost work, duplicate committed results, corruption, secret exposure, or an
untested rollback.

**Files/artifacts.** CH-5.10B/C's frozen failure-recovery runbook, staging-only
orchestration script, contract/self-tests, reviewed staging-target allowlist,
core-worker/deployment/Stage 9 runbooks, and their CH-5.5 release-record digests.
This task may create only CH-6.2 evidence and scoped external raw artifacts; no
script, test, source, runbook, template, or runtime configuration is an allowed
output.

**Safety preflight.** The frozen CH-5.10B script is default-deny. Before exposing any fault
action it must resolve and compare all of these to a reviewed allowlist: exact
API origin, Supabase project reference, database host/name and
<code>environment=staging</code> marker, Storage bucket/prefix, Dokploy
application/service IDs, expected candidate SHA, and image digests. It must also
check an explicit production denylist. Unknown, missing, redirected, or mixed
identity aborts nonzero; an operator typing "staging" is not sufficient. Print
only safe identifiers/hashes. Run in a booked maintenance window after proving
no unrelated users or non-fixture jobs are active. Fault flags are test/staging
only; production startup rejects them. There is no public fault endpoint.

**Red/failure baseline.** Before automation, demonstrate in controlled staging
that each injected fault is detected as an unsuccessful operation and capture
the currently missing alert/recovery/reconciliation evidence. The red state is
the absent guarantee, not deliberate corruption.

**Implementation/execution child packets - no source changes.** First verify the
harness/runbook/contract digests equal CH-5.5's release record. Restore healthy
state and reconcile before starting each next scenario.

1. **CH-6.2A - target and dry-run attestation.** Execute the frozen preflight,
   production-denial self-tests, fixture inventory, safe before snapshot, scoped
   cleanup preview, and no-op/dry run. Prove target identity and all required
   permissions without enabling a fault. Any missing behavior is a CH-5.10B fix
   requiring a new candidate, not an inline script edit.
2. **CH-6.2B - isolated runtime/dependency failures.** Execute separately:
   - graceful API termination during an SSE turn and accepted upload;
   - graceful then, in a clean run, forced Tender-worker termination during a
     long leased job;
   - the same two termination modes for core workflow and parser workers;
   - DB-connectivity interruption;
   - fixture-scoped Storage upload then delete failure;
   - provider timeout then 429;
   - product-level Pi cancellation then forced child-process kill; and
   - duplicate then reversed Stripe test-mode fixtures.
3. **CH-6.2C - immutable rollback and isolated restore.** Deploy an intentionally
   unhealthy staging image, select only the prior digest allowed by the
   compatibility specification/release-record rollback floor, reconcile, and
   restore the candidate.
   Restore the candidate database and Storage recovery set into an isolated,
   network-restricted environment and rerun CH-1.5 security/reconciliation.

For every scenario snapshot revisions, row/object generations, job/continuation
dedup keys, and accepted artefacts before; observe alert,
shutdown/lease/retry/fence/cancel; reconcile after; restore the candidate SHA.

**Verification/thresholds.**

- at most one committed result/version and continuation;
- no lost queued work;
- healthy service/worker within 60 seconds after dependency restoration;
- lease recovery within expiry plus two poll intervals;
- Pi cancellation leaves zero child processes after 15 seconds;
- graceful shutdown accepts no new work after readiness drops, finishes or
  safely requeues work inside its configured grace window, and exits zero;
- forced termination leaves no unfenced late commit after lease recovery;
- prior-image rollback completes within ten minutes;
- restore meets approved RPO/RTO;
- accepted artefact, Tender input/report, Cost Plan revision, project event,
  export, webhook, and idempotency counts have zero unexplained differences;
- expected alert and recovery notification reach the named operator.

**Observability/migration/rollback.** No source or schema change; the task is the rollback proof. Never
downgrade production schema; candidate and prior images must both understand
expanded schema.

**Do not.** Do not combine faults, target production, leave flags enabled, run
while unrelated users/jobs are active, or accept "eventually looked healthy"
without reconciliation.

**Stop if.** Any allowlist field is ambiguous/production, unrelated activity is
present, backup is stale, an alert does not arrive, or the rollback image is
below the compatibility floor.

**Commit/evidence.** CH-6.2A, B, and C are separate evidence/ledger coordination
commits only. Evidence includes immutable harness/contract digests, before/after
digests, alert times, recovery, restore, and SHAs. A required implementation
change blocks the task and restarts CH-5.10/CH-5.5 for a new candidate.

### CH-6.3 - Execute and sign the production go/no-go gate

**Objective and risk.** Turn the existing aspirational acceptance runbook into
dated, SHA/digest-specific evidence. No code-only green status substitutes for
deployed proof.

**Files/artifacts.**

- [Stage 9 production acceptance](../runbooks/stage-9-production-acceptance.md)
- CH-5.10C's frozen <code>docs/acceptance/production/template.md</code> and
  runbook/template/gate-handler digests from the release record
- execution record
  <code>docs/acceptance/production/<YYYY-MM-DD>-<short-sha>.md</code>
- deployment and performance environment docs as read-only inputs. Only the
  execution record and CH-6.3/GATE-6 evidence/ledger coordination files may be
  created or changed.

**Red baseline.** Even with CH-5.10C's validated Pi-only template, this candidate
does not yet have a dated, signed SHA/digest-, final-schema-, rollback-floor-,
backup-, and live-isolation production record. Record that absence as no-go and
verify the frozen runbook/template/handler digests; do not perform a destructive
red exercise or edit a mismatching artifact in place.

**Implementation/execution - no source changes.**

1. Execute CH-5.10C's frozen Pi-only acceptance runbook and verify it contains no
   Hermes check. Keep the legacy PydanticAI source/runtime safety path until a
   separate post-acceptance cutover. Any runbook/template/handler correction
   requires a new pre-freeze candidate.
2. Confirm every required task prior to CH-6.3 and GATE-0 through GATE-5 are
   complete with raw evidence. CH-6.3 and GATE-6 are intentionally not
   preconditions of themselves. No waiver is permitted for P0 isolation,
   authorization, durability, backup, release identity, or recovery.
3. Create and freeze the production execution record, referencing without
   modifying the immutable CH-5.5 release record and copying/verifying its Git
   SHA, API/web/base digests, compatibility revisions/capabilities, rollback
   floor/prior SHA, and harness/runbook/template digests. Record operator,
   independent approver, UTC window, migration current/target head, regions,
   service settings, least-secret role assignments, queue scopes, and synthetic
   fixture IDs in the execution record, not the release record.
4. Run the frozen candidate for at least 24 hours in production-equivalent
   staging with approved synthetic traffic. Require no unexplained critical
   alert or SLO/resource/spend breach. Any code, image, migration, action, base,
   or material configuration change resets the candidate and this soak.
5. Immediately before production promotion, prove the newest backup is younger
   than the approved RPO, the isolated restore rehearsal is current for this
   candidate schema, certificate/disk/pool/queue headroom is green, alert
   transport reaches the named operator, and the prior digest is above the
   rollback floor.
6. In the protected production environment, acquire CH-1.13's migration lock,
   verify the live current head, embedded compatibility specification, and
   release record, then run the exact tested
   migration command once, and verify target head. Then run CH-1.5 against the
   final schema: zero unclassified tables, expected grants/RLS on every new
   table, and two-owner DB plus Storage negative isolation.
7. Deploy the exact frozen digests to the protected production target without
   rebuilding while public ingress remains closed. Do not send customer traffic
   or call this a public canary. Use only allowlisted synthetic/operator probes
   through the controlled acceptance path. Three consecutive readiness responses
   must report the expected SHA, schema capabilities, and service-role health.
8. Execute Pi MCP/SSE/cancel/durable-turn checks; API/Tender/core/parser/cleanup
   health; queue/lease/fence reconciliation; full auth/role cases; and the product
   journey: profile -> Project Plan -> Cost Plan -> Tender Comparison ->
   approved/proposed Cost Plan revision, including events, artefacts, exports,
   and Python arithmetic verification.
9. Verify Stripe mode, webhook ordering/idempotency, entitlement, and spend
   accounting. Staging uses test mode. No production live-mode charge is created
   without separately recorded maintainer approval, amount, refund/reconciliation
   procedure, and evidence-retention rule.
10. During the still-controlled window, select the release-record-approved prior
    digest, run the rollback smoke/reconciliation without downgrading data, then
    restore the candidate digest and reverify SHA/readiness. If production
    conditions make even this closed-window exercise unsafe, the gate is blocked;
    CH-6.2 staging proof alone is not relabelled production proof.
11. Observe the closed-ingress candidate under approved synthetic probes for at
    least 60 minutes with dashboards and alerts staffed. Remove/reconcile
    every synthetic production row, object, job, webhook fixture, and temporary
    entitlement through scoped cleanup and prove customer data was untouched.
12. Record exactly signed <code>ready-to-open</code> or <code>no-go</code> while
    public traffic remains closed. This is an input to GATE-6, not authority to
    open traffic. Only a subsequent passing GATE-6 record may authorize a named
    operator's separately logged controlled public-traffic-open action. Even then,
    legacy deletion/compatibility cleanup remains a separate post-launch packet.

The GATE-6 runner then executes its fixed read-only/evidence handlers against the
closed-ingress target. On a pass it emits a signed authorization containing the
exact candidate/coordination SHAs, digests, target, operator, and expiry. The
named operator rechecks those identities, opens traffic using the pre-reviewed
CH-5.10C procedure without rebuilding, records UTC/action/result in a separate
operator evidence append, and aborts/restores closed ingress if identity or
readiness changed. This traffic action is not another code or gate commit.

**Verification/gate.**

- every required item has linked raw evidence and passes;
- no unresolved P0/P1 or unknown live isolation state;
- zero cross-tenant access;
- final CH-1.5 catalogue includes every migration-created table with no unknown
  grant/RLS/owner classification;
- verified restore within RPO/RTO;
- GATE-3 and GATE-4 pass, and CH-6.1 performance/resource/cost thresholds pass;
- rollback/recovery has zero unexplained differences;
- 24-hour soak has zero unexplained critical alerts;
- production reports exact approved SHA/digests and alerts reach named owner;
- backup age, rollback floor, migration lock/head, traffic recommendation, Stripe mode,
  and synthetic cleanup all have explicit passing evidence.

**Observability/migration/rollout.** This task authors no migration; it executes
only CH-1.13's frozen, locked migration command and records its result. Freeze and
link the candidate dashboards, alert history,
validator JSON, queue/lease snapshots, spend report, and correlation examples
for the acceptance window. All records remain sanitized and retention-approved.

**Rollback.** Any failure is no-go. Keep traffic closed or restore the prior
compatible digest; never destructively downgrade schema, delete compatibility
paths, or cross the recorded rollback floor.

**Do not.** Do not sign from unit/jsdom/Vite-only evidence, use customer content
in records, rebuild a candidate, create an unapproved live Stripe charge, skip
post-migration security classification, or mark missing evidence passed.

**Stop if.** Any required check fails, evidence/SHA is missing, backup/restore or
alert is stale, migration identity differs, an unclassified table appears,
headroom is red, approver is unavailable, cleanup cannot prove scope, or rollback
fails.

**Commit/evidence.** Evidence/ledger coordination only. The signed execution
record contains the immutable CH-5.10/CH-5.5 artifact digests and the
<code>ready-to-open|no-go</code> recommendation. A needed runbook/source/config
change blocks the task and creates a new candidate; it is never committed here.

## 15. Post-launch operating cadence

Passing Stage 6 is the beginning of production operations, not a permanent
claim that the code is optimal. Add these recurring controls to the named
operator's calendar/runbook:

- **Every release:** immutable digest, migrations, readiness, Pi validator,
  security-contract smoke, browser smoke, rollback SHA, and change-specific
  performance evidence.
- **Daily:** critical alerts, queue/dead-letter age, 5xx, pool waits, Storage
  cleanup, provider failures, spend anomaly, backup status.
- **Weekly:** SLO/error-budget review, slow route/query ranking, agent/Tender
  latency and spend, disk/log growth, unowned alerts.
- **Monthly:** dependency/container advisory triage, access/credential review,
  capacity trend and 2x-headroom forecast, retention dry run.
- **Quarterly:** isolated restore, two-owner DB/Storage isolation, worker/Pi
  failure rehearsal, prior-image rollback, incident runbook review.
- **After an incident:** preserve sanitized timeline/evidence, add a regression
  test or invariant at the deepest responsible seam, and update this plan or
  successor runbook.

Performance work after launch remains measurement-led. Optimize the largest
verified contributor to customer latency, throughput, memory, DB pressure, or
provider spend; preserve output/auth equivalence; record before/after and
rollback. Do not pursue file size, abstraction count, or microbenchmarks as a
proxy for customer value.

## 16. Definition of plan completion

This implementation plan is complete only when:

1. every required ledger task is <code>complete</code> with evidence;
2. every stage gate has a dated result for the merged stage state;
3. every <code>Required? = no</code> task is either complete or explicitly marked
   maintainer-approved <code>deferred</code>/<code>not-applicable-approved</code>;
4. production acceptance is signed for an exact SHA and digests;
5. rollback/restore and alert ownership are current;
6. this document links the final acceptance record and is marked
   <code>complete</code>.

Until then, the durable next action is the first non-complete task whose
dependencies are complete. Do not repeat the six-month repository review unless
new evidence invalidates a finding; update the relevant task and proceed.
