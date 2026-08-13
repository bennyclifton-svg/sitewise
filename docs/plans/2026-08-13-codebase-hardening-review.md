---
title: Codebase hardening critical review and production-readiness handoff
status: review-complete-plan-written
type: assessment-and-handoff
date: 2026-08-13
source_plan: docs/plans/2026-08-13-Codebase-Hardending
implementation_plan: docs/plans/2026-08-13-codebase-hardening-implementation-plan.md
reviewed_commit: 4480c680
labels: [security, reliability, performance, production-readiness, backend, frontend, ci, operations]
---

# Codebase hardening critical review and production-readiness handoff

## 1. Purpose and current state

This document is the durable, self-contained record of the 2026-08-13 review of
[`2026-08-13-Codebase-Hardending`](./2026-08-13-Codebase-Hardending). It is
intended to survive handoffs across multiple coding-agent sessions without
depending on chat history.

The source plan has been marked superseded without changing its historical task
content. No implementation work was performed as part of this review or plan
rewrite.

Current decision state:

- Review: **complete**.
- Production-readiness verdict: **do not launch for meaningful traffic yet**.
- Source plan: **superseded; useful maintainability seed, but not a sufficient
  production hardening plan**.
- Implementation plan: **written and ready for maintainer review** at
  [2026-08-13-codebase-hardening-implementation-plan.md](./2026-08-13-codebase-hardening-implementation-plan.md).
- Next action: review that plan, resolve the first task's operator decisions,
  then execute one dependency-ready task at a time.
- Structural refactors in source-plan Tasks 6 and 7: **deferred until security,
  durability, and production gates pass**.

## 2. Instructions for the next session

A new agent should begin here, not by repeating the repository review from
scratch.

1. Read `AGENTS.md` and the canonical documents listed in Section 3.
2. Read this document completely.
3. Run `git status --short` and record the current commit. The reviewed worktree
   was already dirty; unrelated user changes must be preserved.
4. Confirm whether the immediate credential-rotation action in Finding
   `CH-P0-01` has been completed. Do not print or copy the credential.
5. Open the implementation plan's execution ledger and choose only the first
   dependency-ready task authorized by the maintainer.
6. Follow that task's red test, commit boundary, evidence, rollback, and stop
   conditions. Do not batch tasks.
7. Update the ledger and evidence record before handing off to another session.

Do not:

- Delete `backend/app/assistant/` or `backend/app/chat/orchestrator.py` before
  the live production acceptance and legacy cutover gate passes.
- Reintroduce Hermes or another agent runtime. Pi is the sole runtime.
- Run the broad backend suite while local configuration can contact production.
- Add Uvicorn workers as a quick scaling fix; agent admission, cancellation, and
  status coordination are currently process-local.
- Begin the route or MCP file splits before their required security and contract
  tests exist.

## 3. Governing repository documents

The review treated these as authoritative:

1. [`AGENTS.md`](../../AGENTS.md)
2. [`docs/architecture.md`](../architecture.md)
3. [`2026-08-04-pi-only-agent-runtime.md`](./2026-08-04-pi-only-agent-runtime.md)
4. [`2026-06-11-tender-comparison-module-prd.md`](./2026-06-11-tender-comparison-module-prd.md)

Existing work that the rewritten plan should reuse rather than duplicate:

- [`2026-07-10-integrated-agentic-workflows-execution-tracker.md`](./2026-07-10-integrated-agentic-workflows-execution-tracker.md)
- [`docs/performance/2026-07-19-stage-6-performance.md`](../performance/2026-07-19-stage-6-performance.md)
- [`docs/runbooks/stage-9-production-acceptance.md`](../runbooks/stage-9-production-acceptance.md)
- [`DEPLOYMENT.md`](../../DEPLOYMENT.md)

The repository did not contain a root `CONTEXT.md` or a `docs/adr/` decision
set during this review. Domain direction therefore came from `AGENTS.md`, the
architecture document, the Pi runtime plan, and the Tender Comparison PRD.

## 4. Executive conclusion

The source plan correctly notices several maintenance problems, especially
profile-field drift and two very large modules. Its central weakness is scope:
it concentrates on linting, test parallelism, helper consolidation, and file
decomposition while omitting higher-risk production concerns.

The repository already contains substantial functionality and a large test
base. It is not a beginner toy codebase. However, its risk profile is consistent
with rapid agent-led development without sustained review:

- stated authorization invariants are only partially wired into production;
- similar durable queues have inconsistent safety properties;
- some tests labelled offline can contact configured external systems;
- deployment and validation can report success without proving a safe release;
- several client and file-processing paths have unbounded or traffic-linear
  costs;
- production acceptance requirements are documented but remain open.

The correct response is not a broad rewrite. It is to create strong seams and
fail-closed invariants around mutation authorization, tenant isolation, durable
jobs, external I/O, deployment, and observability. Structural cleanup should
follow those protections.

## 5. Review scope and verification performed

### 5.1 Repository areas inspected

- Pi turn classification, reservation, subprocess configuration, cancellation,
  and concurrency.
- MCP registration and per-tool authorization calls.
- Project routes, profile storage, uploads, downloads, PDF analysis, drafts,
  activity, events, and evidence.
- Core workflow and Tender workers, claims, locks, leases, continuations,
  database-session lifetime, and LLM calls.
- Stripe webhook and subscription persistence.
- Alembic migrations, RLS declarations, and representative grants.
- React authentication lifecycle, TanStack Query caching, project-event
  polling, chat transport, pagination, evidence rendering, build budgets, error
  states, and accessibility.
- CI, Dockerfiles, Dokploy compose, Nginx, health checks, logging, deployment,
  rollback, and production-acceptance documentation.

### 5.2 Observed repository state

- Branch: `main`.
- Reviewed commit: `4480c680` (`feat: give prose scope a destination in the
  project profile`).
- The worktree already contained unrelated modified and deleted files, and the
  source hardening plan was untracked. The reviewer did not modify those files.
- `backend/app/api/projects.py`: approximately 3,690 physical lines, 69 routes
  on its primary router plus two SiteWise routes.
- `backend/app/mcp_bridge/server.py`: approximately 4,270 physical lines and 69
  registered MCP tools.
- Pi exposes 53 base MCP direct tools plus two optional web tools, not all 69
  registered tools.

### 5.3 Test and static-analysis results

These results describe the reviewed dirty worktree and must not be frozen as
permanent expected counts.

Backend full offline-labelled run:

```text
3 failed, 2109 passed, 7 skipped, 31 deselected
wall clock: approximately 366 seconds
```

The failures attempted configured Supabase Storage/database activity. They are
evidence that the offline test seam is incomplete, not sufficient evidence that
the product behavior itself is broken.

Backend collection:

```text
2150 total collected
2119 selected by the default marker expression
31 deselected
```

Focused tests:

- MCP/auth/profile, agent chat, Tender jobs/workers/continuations: 73 passed.
- Inbox upload/split and profile contracts: 22 passed.
- Stripe webhook and query-budget tests: 6 passed.

Frontend:

```text
Vitest: 412/413 passed; one timing/order-dependent failure
ESLint: 18 errors, 4 warnings
```

The CI command `pnpm tsc --noEmit` exits successfully without traversing the
referenced app project. The production build later invokes `tsc -b`, so this is
a false dedicated gate rather than a total absence of build-time type checking.
`tsconfig.app.json` does not enable `strict`. A real app check found only three
existing unused-symbol errors before strictness work.

Proposed Ruff selection from source-plan Task 3:

```text
2970 findings total
2275 E501 line-too-long
249 B008 function-call-in-default-argument
196 I001 import sorting
remaining findings include genuine B023/B905 and upgrade/simplification cases
```

No live production database audit, external-service integration test, load
test, restore rehearsal, rollback rehearsal, or chaos test was performed.

## 6. Immediate containment

### CH-P0-01 — Credential exposure and unsafe offline-test seam

**Status:** confirmed; immediate action required.

During the backend test run, a configured database DSN including its password
was rendered in a failure traceback. This document intentionally does not
reproduce it.

The same run showed that tests selected by the default “not integration” marker
can call real storage/database modules. For example, the confident inbox-sort
test does not replace all external collaborators, while the implementation can
download from storage and resolve ingested source documents:

- [`backend/tests/workflows/test_sort_files.py`](../../backend/tests/workflows/test_sort_files.py)
- [`backend/app/intake/sort_service.py`](../../backend/app/intake/sort_service.py)
- [CI offline environment](../../.github/workflows/ci.yml#L21)

**Required action:**

1. Rotate the exposed database credential.
2. Remove or restrict retained local/CI logs that contain the DSN.
3. Ensure exception/log rendering redacts URL user-info and known secret
   settings.
4. Add a default-deny network guard for offline tests.
5. Give offline tests sentinel database, Supabase, Storage, OpenAI, Stripe, and
   Pi configuration that fails immediately and safely.
6. Require external tests to carry an explicit integration/evaluation marker.
7. Do not run broad local tests against a `.env` that points at production.

**Acceptance evidence:** an offline run passes with outbound network disabled,
and deliberately invoking an unmocked adapter fails with a short sanitized
message that contains no credential.

## 7. P0 production blockers

### CH-P0-02 — MCP mutation scopes are not enforced for almost every write tool

**Status:** confirmed production defect.

The canonical design says mutation authorization is enforced at the MCP seam.
The implementation only completes that contract for profile mutation:

- [`classify_mutation_intent`](../../backend/app/agent/mutation_intent.py#L180)
  grants only `profile_mutation`.
- [Chat turn reservation](../../backend/app/api/chat.py#L668) stores exactly
  those scopes.
- [`turn_needs_mutation_tools`](../../backend/app/agent/turn_context.py#L585)
  identifies workflow/cost writes but has no production caller.
- [`PI_MCP_DIRECT_TOOLS`](../../backend/app/agent/pi_process.py#L20) exposes the
  same write-capable list to every turn.
- [`require_active_mutation_turn`](../../backend/app/billing/usage.py#L157)
  enforces a scope only when the caller provides `required_scope`.
- Of approximately 23 MCP mutation authorization calls, only
  [`update_project_profile`](../../backend/app/mcp_bridge/server.py#L2517)
  supplies a required scope.

This is not a demonstrated cross-tenant bypass: project and user claims are
still checked. It is an intent/capability failure. A read-only question receives
an active turn with no scope yet can invoke most project mutators if the model is
misdirected, including through prompt injection.

**Required design:**

- A checked-in tool capability matrix containing tool name, read/write class,
  required scope, project-ID extraction, feature gate, and Pi visibility.
- Named granular scopes for workflow start/cancel, cost-plan mutation, artefact
  mutation, project-decision mutation, shared-knowledge mutation, Tender
  mutation, workspace mutation, and profile mutation.
- Fail-closed server-side authorization for every mutating tool. Prompt wording
  and tool visibility are defense in depth, not the enforcement seam.
- Pi direct-tool configuration derived from capabilities granted to the turn.
- A test that enumerates every registered tool and fails if a mutator has no
  required scope.
- Negative tests proving a read-only/empty-scope turn cannot mutate.
- Cancellation/revocation-versus-commit race tests.

This capability module is a deep module: callers receive high leverage from one
small interface, while authorization knowledge and verification gain locality.
Splitting `server.py` without first creating this seam would move code without
fixing the risk.

### CH-P0-03 — Database and Storage tenant isolation are not proven

**Status:** potentially critical; migration evidence confirmed, live
exploitability unverified.

Representative project- or tenant-sensitive tables are created without an RLS
declaration in their migrations:

- [`workspace_files`](../../backend/alembic/versions/004_workspace_files.py#L22)
- [Tender core tables](../../backend/alembic/versions/007_tender_core.py#L23)
- [`project_activity_events`](../../backend/alembic/versions/017_project_activity_events.py#L22)
- [`agent_turns`](../../backend/alembic/versions/023_agent_turns.py#L18)
- [`project_profile_proposals`](../../backend/alembic/versions/027_profile_proposals.py#L40)

Other sensitive families requiring inventory include source documents/chunks,
project events/decisions, workspace files, Stripe/Polar billing, and all
`tender_*` tables.

The privileged backend performs ownership checks, but that does not settle
direct Supabase Data API, Realtime, SQL-role, or Storage exposure. Actual risk
depends on live `relrowsecurity`, policies, grants, exposed schemas, default
privileges, bucket privacy, and Storage policies.

Supabase’s production guidance requires RLS on exposed tables and recommends
using grants and RLS together:

- <https://supabase.com/docs/guides/database/postgres/row-level-security>
- <https://supabase.com/docs/guides/api/securing-your-api>
- <https://supabase.com/docs/guides/deployment/going-into-prod>

**Required action:**

1. Export a live inventory of every table/view/function/sequence, RLS flag,
   policy, grant, default privilege, exposed schema, publication, bucket, and
   Storage policy.
2. Classify each object as browser-exposed tenant data, backend-only internal
   data, or global reference data.
3. Enable and test owner RLS where browser/Data API access is intended.
4. Revoke `anon`/`authenticated` access where direct access is not intended.
5. Add anonymous, user-A, user-B, and service-role negative tests.
6. Add a migration/CI invariant: every sensitive table is either protected by
   reviewed RLS policies or explicitly non-exposed with reviewed grants.
7. Test Storage separately; database RLS does not protect bucket objects.

### CH-P0-04 — Private frontend cache survives identity changes

**Status:** confirmed tenant-isolation defect.

The SPA uses one application-lifetime TanStack Query client, retains cache data
for five minutes, and gives chat threads a global key. Auth changes update React
session state but do not clear private query data:

- [`frontend/src/main.tsx`](../../frontend/src/main.tsx)
- [`frontend/src/lib/query-client.ts`](../../frontend/src/lib/query-client.ts#L10)
- [`frontend/src/components/chat/chat-query-keys.ts`](../../frontend/src/components/chat/chat-query-keys.ts#L1)
- [`frontend/src/components/AuthGuard.tsx`](../../frontend/src/components/AuthGuard.tsx#L15)
- [`frontend/src/lib/auth.ts`](../../frontend/src/lib/auth.ts#L15)

User B signing into the same tab can briefly receive user A’s cached thread
names or project data before refetch.

**Required design:** one authenticated-app lifecycle module should own the
identity transition interface. On sign-out or a different `user.id`, it must
cancel in-flight queries and remove private data before rendering the next
identity. It must not clear on same-user token refresh.

**Acceptance evidence:** seed user-A private data, emit A-to-B and A-to-signed-out
transitions, and prove no A data is rendered or retained before B mounts.

### CH-P0-05 — Tender job isolation, leases, and continuation durability

**Status:** multiple confirmed production defects.

#### Environment scope

`TenderJob` has no `queue_scope`; enqueue and claim use only status and run time:

- [`TenderJob`](../../backend/tender/models.py#L828)
- [`enqueue`](../../backend/tender/services/jobs.py#L25)
- [`claim_query`](../../backend/tender/services/jobs.py#L51)

If local, staging, and production workers share Supabase, a worker can execute
another environment’s paid LLM job. This repeats the class of bug already fixed
for core `workflow_runs`.

#### Renewable lease and fencing

Claim sets `locked_at` once, long handlers do not renew it, and the sweeper
requeues any old running row:

- [`claim_next`](../../backend/tender/services/jobs.py#L61)
- [`run_once`](../../backend/tender/worker.py#L58)
- [`requeue_stale`](../../backend/tender/services/jobs.py#L179)

A long OCR/LLM operation can therefore run twice. The original worker can later
publish or complete after another worker owns the row because completion is not
fenced by owner/attempt.

#### Completion/continuation atomicity

The worker commits completion before downstream continuation enqueue:

- [`jobs.complete`](../../backend/tender/services/jobs.py#L81)
- [worker completion order](../../backend/tender/worker.py#L116)
- [`after_job_complete`](../../backend/tender/services/continuations.py#L14)

A crash between commits permanently stalls the pipeline.

**Required design:** port the proven core-workflow concepts: immutable queue
scope, lease expiry, heartbeat, attempt/fencing token, owner-conditional
complete/fail, and short transactions. Completion and continuation must share a
transaction or be repaired by a durable outbox/reconciler.

**Acceptance evidence:** two-environment isolation, two-worker claim exclusion,
handler duration beyond the stale interval, killed-worker recovery, stale-worker
publish rejection, one billed execution, one terminal publication, and one
continuation chain.

### CH-P0-06 — Unbounded uploads and synchronous PDF processing can exhaust the API

**Status:** confirmed resource-exhaustion risk.

Production runs one Uvicorn process:

- [`deploy/docker/backend.Dockerfile`](../../deploy/docker/backend.Dockerfile#L71)

Relevant paths:

- Nginx permits 100 MB: [`sitewise.conf`](../../deploy/nginx/sitewise.conf#L8).
- Multi-file inbox upload reads and retains every complete file:
  [`projects.py`](../../backend/app/api/projects.py#L1846).
- PDF analysis reads the complete upload:
  [`projects.py`](../../backend/app/api/projects.py#L2103).
- Inspection/detection/sheet planning then run synchronously on the event loop:
  [`split_service.py`](../../backend/app/inbox/split_service.py#L90).
- Tender quote upload also reads the complete file:
  [`tender/router.py`](../../backend/tender/router.py#L614).
- Workspace downloads buffer the complete object through FastAPI:
  [`projects.py`](../../backend/app/api/projects.py#L1816).

The analyze/split/commit path also requires an entitlement review; the analyze
route does not currently apply the same entitlement check as ordinary upload.

**Required controls:**

- configurable file count, per-file size, aggregate request size, project
  storage, PDF page/dimension, archive/decompression, and active-job limits;
- bounded chunk reads that reject one-byte-over before parser/storage work;
- extension plus MIME/magic validation;
- off-event-loop or worker-based CPU parsing;
- upload/parse/agent concurrency admission and `429 Retry-After`;
- streaming or short-lived authenticated signed downloads;
- abandoned staging-object TTL/reconciliation;
- load tests with realistic concurrent maximum files and an RSS ceiling.

### CH-P0-07 — Deployment is not gated by green CI and validation cannot fail

**Status:** confirmed release-control defect.

- CI starts on push: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml#L3).
- A push to `main` independently triggers automatic Dokploy deployment:
  [`DEPLOYMENT.md`](../../DEPLOYMENT.md#L266).
- The validator converts every failed command into a warning and success:
  [`sitewise-vps-phase8-validate.ps1`](../../scripts/sitewise-vps-phase8-validate.ps1#L26).
- The validator and runbook still test/document Hermes rather than the canonical
  Pi runtime:
  [`sitewise-vps-phase8-validate.ps1`](../../scripts/sitewise-vps-phase8-validate.ps1#L55),
  [`DEPLOYMENT.md`](../../DEPLOYMENT.md#L360).
- Compose uses mutable `latest` images with `pull_policy: never`:
  [`dokploy.compose.yml`](../../deploy/dokploy.compose.yml#L59).

A red revision can deploy before CI completes, and the recorded validator can
return success after required checks fail.

**Required release interface:**

1. Build and identify an immutable image SHA.
2. Run required CI, migration, container, and acceptance checks.
3. Promote that exact SHA only from a green release job or explicit protected
   approval.
4. Give deployment workflow concurrency, cancellation, least-privilege
   permissions, and timeouts.
5. Separate required validator checks from advisory diagnostics; aggregate
   required failures and exit nonzero.
6. Replace Hermes probes with Pi version/discovery, unprivileged runtime, MCP,
   SSE, cancellation, revocation, and mutation-scope probes.
7. Run migrations as a controlled release operation with expand/migrate/contract
   compatibility, not from an engineer’s production-bound laptop.
8. Retain immutable rollback images and rehearse application rollback without
   database downgrade.

### CH-P0-08 — Backup, restore, retention, and final acceptance are unproven

**Status:** documented requirements remain open.

The existing production runbook requires a verified restore point, reviewed
RLS/grants, two-owner isolation, Pi/MCP/SSE cancellation, worker recovery,
billing, full product journeys, SLOs, and rollback:

- [`stage-9-production-acceptance.md`](../runbooks/stage-9-production-acceptance.md)

The Tender PRD also specifies retention/purge and backup expectations. No
completed restore rehearsal or durable source-purge mechanism was found.

**Required action:** define RPO, RTO, retention, legal hold, operator ownership,
and acceptable downtime; verify PITR and Storage backup scope; implement audited
purge/reconciliation; perform a timed restore; and preserve evidence. Supabase
database backup does not automatically imply Storage-object recovery.

## 8. P1 high-value reliability and performance work

### CH-P1-01 — Project-event polling has traffic-linear and history-linear cost

**Status:** confirmed scaling defect.

The client starts every project at cursor zero, drains history in 100-event
batches, applies invalidation for each event, then polls every 250 ms while
active or 1.5 seconds while idle:

- [`useProjectEventCursor`](../../frontend/src/lib/queries/project-data.ts#L220)
- [backend ascending event query](../../backend/app/projects/events.py#L106)

One thousand idle cockpits imply approximately 667 event requests per second
before real activity. Active clients are more expensive. `pollNow()` can overlap
with an already scheduled loop, and all errors retry indefinitely without
jitter or terminal-status handling.

**Required design:** capture an event high-water mark atomically with cockpit
bootstrap, initialize the cursor from it, guarantee one request and one timer,
cancel on unmount/identity loss, use jittered backoff, stop on non-retryable
errors, and batch resource invalidation. Then load-test polling versus long-poll
or project SSE before choosing the transport.

### CH-P1-02 — Pagination is discarded and evidence remains unbounded

**Status:** confirmed product and scale defects.

- Chat reads `next_cursor` then returns only the first 50 rows:
  [`frontend/src/lib/api.ts`](../../frontend/src/lib/api.ts#L241).
- Tender comparisons repeat the pattern:
  [`frontend/src/lib/api.ts`](../../frontend/src/lib/api.ts#L311).
- The cockpit bootstrap and document repository still load/sort/render all
  evidence rows:
  [`backend/app/api/projects.py`](../../backend/app/api/projects.py#L1549),
  [`DocumentRepositoryPanel.tsx`](../../frontend/src/components/project/DocumentRepositoryPanel.tsx).

Records beyond 50 are inaccessible in two flows, while large projects pay
O(all documents) payload, sorting, and DOM costs.

**Required design:** preserve page objects/cursors, use additive keyset
pagination, deduplicate IDs, provide explicit load-more or a sentinel, and test
concurrent insertion. Establish 100/1,000/10,000-document fixtures before adding
evidence pagination/search and row virtualization. Specify cross-page selection
semantics.

### CH-P1-03 — Chat submission and rendering do avoidable O(history) work

**Status:** confirmed inefficiency; rendering optimization requires profiling.

Every send uploads the complete client message history:

- [`ChatPanel.tsx`](../../frontend/src/components/chat/ChatPanel.tsx#L153)

The backend extracts only the final user message and loads canonical history
from storage:

- [`post_agent_stream`](../../backend/app/api/chat.py#L579)

Send only the final message while preserving its ID, because the ID participates
in turn idempotency. Add a transport contract test first. Profile memoized rows
and approximately 30–50 ms stream batching before considering virtualization.
Add deterministic recovery for a dropped stream; do not add blind resend without
an idempotency test.

### CH-P1-04 — Database pools, transaction lifetime, and readiness are implicit

**Status:** confirmed operational risk.

The shared engine specifies only `pool_pre_ping`:

- [`backend/app/database/session.py`](../../backend/app/database/session.py#L26)

Default SQLAlchemy settings can permit roughly 15 connections per process. The
API, Tender worker, and core worker can therefore approach roughly 45 before
other processes, and `DEPLOYMENT.md` already records connection saturation.

Tender keeps one session through an entire handler, and mapping deletes/flushes
before awaiting model work:

- [`tender/worker.py`](../../backend/tender/worker.py#L61)
- [`tender/services/mapping.py`](../../backend/tender/services/mapping.py#L233)

Core workflow work also retains a session during long operations. External
network/LLM work should occur outside a database transaction using immutable
input, followed by a short fenced publication transaction.

The current `/health` endpoint returns configuration without checking database
or schema readiness:

- [`backend/app/main.py`](../../backend/app/main.py#L128)

Define per-process connection budgets, overflow, acquisition timeout, recycle,
statement timeout, lock timeout, and idle-transaction timeout. Expose pool
metrics. Split liveness, dependency readiness, schema readiness, worker
heartbeat, oldest queue age, and failure-rate checks.

### CH-P1-05 — The API cannot be scaled safely by adding workers

**Status:** architectural capacity constraint.

Agent admission semaphores, active-turn registry, cancellation, and status
coordination are process-local. Reservation/quota work occurs before some
admission decisions. Multiple API workers can therefore violate one-turn-per-
thread behavior or route cancellation/status to the wrong process.

**Required action:** measure the single-process capacity envelope. Add bounded,
fast admission before costly reservation. Then either create a durable
cross-process coordination seam or explicitly document and alert on the
single-process limit. Do not add worker processes until the invariants have
cross-process tests.

### CH-P1-06 — Stripe webhook state lacks replay and ordering protection

**Status:** confirmed reliability defect.

The handler consumes event type/object but does not persist event ID or event
ordering before overwriting subscription state:

- [`stripe_webhooks.py`](../../backend/app/billing/stripe_webhooks.py#L169)
- [`stripe_billing.py`](../../backend/app/database/stripe_billing.py#L111)
- [`stripe_subscription.py`](../../backend/app/database/stripe_subscription.py)

Stripe documents that webhooks can be duplicated and delivered out of order:

- <https://docs.stripe.com/webhooks>

Persist a unique processed-event ledger and guard stale transitions, preferably
by reconciling the current Stripe object where ordering matters. Add checkout
creation idempotency and tests for duplicate and reverse-ordered events.

### CH-P1-07 — Storage cleanup and staging cleanup are not durable

**Status:** confirmed orphan-data risk.

Several routes commit database deletion and then attempt object deletion as
best-effort background work. Storage deletion errors are logged/suppressed, and
abandoned `_staging` PDFs have no TTL reconciler:

- [`project_files.py`](../../backend/app/storage/project_files.py)
- [`projects.py`](../../backend/app/api/projects.py#L2022)
- [`split_service.py`](../../backend/app/inbox/split_service.py#L86)

Use a durable cleanup outbox/queue, retry policy, dead-letter visibility, and an
orphan scanner. Record retention locks and audit data before deletion.

### CH-P1-08 — Frontend CI gates currently give false confidence

**Status:** confirmed.

- CI runs `pnpm tsc --noEmit`:
  [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml#L47).
- Root TypeScript configuration contains project references but no files:
  [`frontend/tsconfig.json`](../../frontend/tsconfig.json).
- App configuration does not enable `strict`:
  [`frontend/tsconfig.app.json`](../../frontend/tsconfig.app.json).
- Current lint and test baselines are red.

Change the gate to `tsc -b --pretty false`, enable strictness after the small
existing error set is fixed, clean lint, and repair the timing-dependent test.
Run the full suite repeatedly to demonstrate the flake is gone.

The frontend tracks both `pnpm-lock.yaml` and `package-lock.json`, despite
[`frontend/AGENTS.md`](../../frontend/AGENTS.md#L28) requiring pnpm only. Pin the
Node major and exact pnpm version in package metadata/CI/Docker and keep one
lockfile.

### CH-P1-09 — Production asset delivery does not match bundle accounting

**Status:** confirmed repository configuration gap; deployed edge behavior still
requires verification.

The bundle script measures gzip bytes but excludes CSS and dynamic imports from
the primary route calculation. Chat is loaded even when initially collapsed,
making the real cockpit JavaScript larger than the enforced number.

Nginx has no repository-owned compression, immutable hashed-asset caching,
`index.html` revalidation, or application security-header policy:

- [`measure-build-size.mjs`](../../frontend/scripts/measure-build-size.mjs)
- [`sitewise.conf`](../../deploy/nginx/sitewise.conf)

Define budgets from a cold production-container browser trace: all route JS,
dynamic chunks, CSS, fonts, request count, and transfer bytes. Configure and
test compression for compressible types, immutable `/assets/`, `no-cache` for
`index.html`, `Vary: Accept-Encoding`, and staged security headers/CSP. Preserve
unbuffered SSE behavior.

### CH-P1-10 — Observability is insufficient for expected traffic

**Status:** confirmed repository gap.

Production logging uses a development console renderer:

- [`backend/app/logging.py`](../../backend/app/logging.py#L18)

Add structured JSON, request/correlation IDs, user/project-safe identifiers,
build SHA, workflow/job/turn IDs, durations, status, exception classification,
and centralized redaction. Establish metrics and alerts for:

- HTTP p50/p95/p99 and 5xx;
- DB pool use, acquisition time, statement time, and idle transactions;
- queue depth, oldest age, retries, lease expiry, failures, and heartbeat;
- API/worker RSS, CPU, restarts, disk, and event-loop lag;
- OpenAI calls, tokens, latency, errors, rate limits, and spend;
- orphan storage and failed cleanup;
- Stripe webhook age/failures;
- backup age and restore verification.

Alert delivery needs a named owner and a tested escalation route.

### CH-P1-11 — Browser failure and accessibility acceptance are thin

**Status:** confirmed coverage gap.

CI is jsdom-only. Important contracts not proven in a real production container
include auth cache isolation, lazy-chunk failure, SPA fallback, uploads, SSE
through Nginx, asset headers, focus, and keyboard behavior.

The application also uses blank Suspense fallbacks and has no root render error
recovery. Document repository rows are click-only, and some activity actions
remove visible focus styling.

Add a narrow real-browser acceptance lane rather than a large end-to-end suite.
Cover sign-in identity transitions, project load, chat SSE/cancellation,
upload/limits, lazy-chunk failure, SPA fallback, cache/compression headers, and
keyboard use of primary repository actions.

### CH-P1-12 — Query/index work must be measured, not guessed

**Status:** likely optimization opportunities identified; production impact not
measured.

Examples include per-line-item Tender mapping lookups, per-sheet provenance
lookups, and per-file repair/sort `session.get` calls. The Tender stale sweeper
filters `(status, locked_at)` while the visible job index is `(status,
run_after)`.

Enable `pg_stat_statements`; reproduce production-sized fixtures; record query
count and `EXPLAIN (ANALYZE, BUFFERS)`; then batch queries or add indexes only
where demonstrated. Every performance change needs before/after latency,
resource pressure, and rollback notes.

## 9. Positive findings to preserve

The hardening work should not erase sound existing design:

- Pi is the sole runtime and the repository clearly documents that direction.
- MCP tokens are project-bound and ownership checks are generally present.
- HMAC comparison, workspace path containment, and many project-ownership checks
  are well implemented.
- Core workflows already have queue scope, leases, heartbeat, cancellation, and
  fenced publication concepts that Tender can reuse.
- Tender arithmetic is deterministic Python rather than model-produced math.
- Tender ownership is kept within `backend/tender/` as required by the PRD.
- Route-level frontend lazy loading exists, and heavy Three.js code is isolated.
- Cost Plan/Tender tables already use virtualization in important views.
- Markdown/HTML rendering has explicit escaping/sanitization measures.
- Tender polling is visibility aware.
- The repository has a substantial unit-test base and several useful contract
  tests.

Prefer deepening these modules and interfaces over replacing them.

## 10. Critical assessment of the source plan

### Task 1 — Derive `PROFILE_FIELDS` from the schema type

**Verdict:** keep, low priority.

The two 12-element definitions currently match. Deriving the tuple is safe and
reduces one drift point, but a typing `Literal` is not the full field-lifecycle
registry. Fields also interact with create/patch schemas, column storage,
taxonomy metadata, profile proposals, read models, and frontend types.

Improve the task by adding a lifecycle invariant. If the `Literal` remains the
source, assert that every value has an explicitly classified storage and
mutation path.

### Task 2 — Add a profile-field guard test

**Verdict:** keep, but rewrite the test.

The historical accepted-but-dropped bug is real. The proposed test calls a
private mapping helper and checks key presence; that is not a round trip and does
not protect the HTTP seam where the defect occurred.

Required coverage:

- POST create route with distinct sentinel values;
- captured persistence arguments or disposable-DB persistence;
- read-back response;
- PATCH profile path and explicit clear semantics;
- taxonomy-backed versus column-backed classification;
- frontend type parity where applicable;
- a negative mutation proving removal of a carried field fails the test.

### Task 3 — Expand Ruff to `E,F,I,B,UP,SIM`

**Verdict:** worthwhile direction; unsafe instructions and wrong risk rating.

Selecting all `E` introduces 2,275 line-length findings. `B008` reports 249
idiomatic FastAPI dependency/default factories unless configured. Ruff documents
the `lint.flake8-bugbear.extend-immutable-calls` escape for known immutable
framework factories:

- <https://docs.astral.sh/ruff/rules/function-call-in-default-argument/>
- <https://docs.astral.sh/ruff/settings/>

Revised rollout:

1. Pin Python target/version and line-length policy.
2. Enable high-signal bug rules first; fix genuine `B023` loop-closure and
   `B905` strict-zip findings manually.
3. Configure fully qualified FastAPI/Pydantic immutable factories rather than
   suppressing `B` wholesale.
4. Keep `E501` out unless a separate formatting decision is made.
5. Introduce import sorting and upgrade rules in mechanical commits.
6. Treat simplification rules as optional readability work.
7. Never accept repo-wide unsafe autofixes without file-by-file review and
   behavior tests.

### Task 4 — Add `pytest-xdist -n auto`

**Verdict:** defer until offline isolation is fixed; redesign execution.

This improves engineering feedback time, not customer runtime. Machine-dependent
`auto` can oversubscribe RAM, DB connections, and Windows workstations, while a
typical CI runner may have only two cores. Adding it to global `addopts` also
slows focused debugging and unintentionally parallelizes every lane.

The source plan suggests `xdist_group`, but that marker is honored only with
`--dist loadgroup`:

- <https://pytest-xdist.readthedocs.io/en/stable/distribution.html>

Revised task:

1. Make the lane strictly offline and order-independent.
2. Benchmark serial, `-n 2`, and `-n 4` on the actual Linux runner and a normal
   developer machine.
3. Choose a bounded worker count or `--maxprocesses` from evidence.
4. Put parallel execution in a named script/CI command, not the universal local
   default.
5. Keep explicit serial, integration, evaluation, and debugging commands.
6. Use `--dist loadgroup` if group markers are required.

### Task 5 — Consolidate duplicated workflow helpers

**Verdict:** mostly reject as written.

One-line `Path.read_text` wrappers fail the deletion test: removing the proposed
helper does not force meaningful complexity back into callers. The source plan
also misses another equivalent loader. A generic `_helpers.py` would be a shallow
module with little leverage or locality.

Potentially worthwhile work:

- Consolidate `_trace` only if it becomes a real trace-construction interface
  that normalizes durations, metadata, model/provider, error classification,
  and serialization.
- Consolidate procurement slug/target normalization only within the procurement
  domain and only after compatibility/property tests for Unicode, punctuation,
  empty names, fallback behavior, and persisted workflow identifiers.

### Task 6 — Split `api/projects.py`

**Verdict:** real maintainability benefit; no production-speed benefit; defer.

The file is a navigation and edit-collision hotspot, but moving route functions
does not make requests materially faster. The proposed grouping omits several
route families and proposes `app/api/projects/` beside `app/api/projects.py`,
creating a module/package naming collision during incremental migration.

Use a non-colliding `app/api/project_routes/` package and retain `projects.py` as
a stable facade. Move one vertical route domain at a time. Existing tests patch
`app.api.projects.*`; preserve or intentionally migrate those seams.

The proposed sorted method/path diff is insufficient. Preserve registration
order, prefix, name, dependencies, response model, status, tags, security,
operation ID, and normalized OpenAPI. Add representative request-level smoke
tests. Do not use `/tmp`-specific instructions in a Windows-first plan.

### Task 7 — Split `mcp_bridge/server.py`

**Verdict:** worthwhile for locality only after `CH-P0-02`; highest-risk
structural task.

Explicit `register(mcp)` calls are better than import side effects. However, an
exact-name test alone does not protect input schemas, descriptions, authorization
requirements, feature flags, or Pi visibility.

Before movement, add a complete tool contract snapshot containing:

- unique name;
- description;
- input schema;
- read/write classification;
- required scope;
- project-ID binding;
- feature gate;
- Pi direct visibility.

Assert all Pi allowlisted tools are registered and every mutator is scoped.
Preserve or deliberately migrate tests that monkeypatch
`app.mcp_bridge.server.*`. Move one domain per commit only after capability
enforcement is green.

## 11. Secondary improvements worth retaining in the backlog

These are useful but should not displace P0/P1 work:

- Pin Node major and exact pnpm version; remove `package-lock.json`.
- Remove or reclassify unused frontend runtime dependencies after verifying no
  CLI/build use.
- Add visible loading states, root/local error recovery, and customer-safe error
  copy instead of development instructions.
- Thread `AbortSignal` through query and workflow-polling interfaces.
- Add deadlines, bounded retry, jitter, and cancellation to external model calls.
- Reuse OpenAI clients per process/worker rather than repeatedly constructing
  them.
- Resolve Pi executable/config checks during startup or off the event loop.
- Review the web container’s `8080:80` host publication and externally verify
  that it cannot bypass the intended TLS/proxy route.
- Scan dependencies and built images for known vulnerabilities and generate a
  release SBOM using an approved CI tool.

## 12. Staged structure carried into the implementation plan

The implementation plan replaces the current seven-task order with the
following stages. Stages are gates: later stages do not start while an earlier
required gate is red.

### Stage 0 — Containment and trustworthy baseline

Objective: make verification safe and truthful.

- Rotate the exposed credential and sanitize logs/errors.
- Make offline tests deny all external access.
- Establish a clean commit/worktree baseline.
- Repair frontend typecheck, lint, and flaky test.
- Record current test durations, bundle/browser transfers, API resource use,
  DB connection limits, and build SHA.
- Add dependency/image scanning and secret scanning without printing secrets.

Gate: all offline checks pass without network; no secret appears in output;
baseline artifact is checked in or attached to the release record.

### Stage 1 — Security, tenancy, and release control

Objective: make unauthorized mutation, cross-tenant access, and red deployment
fail closed.

- MCP capability matrix and per-mutator scopes.
- Live DB grants/RLS/exposed-schema and Storage-policy audit.
- Anonymous/user-A/user-B/service-role isolation tests.
- Frontend auth-cache isolation.
- Per-user/IP/concurrency limits for agent, upload, export, search, and other
  expensive routes.
- Green-CI immutable-SHA promotion and Pi-native fail-capable validator.

Gate: negative mutation and two-owner tests pass; a deliberately red revision
cannot deploy; production reports the promoted SHA.

### Stage 2 — Durable jobs and data correctness

Objective: guarantee one logical execution and recoverable state transitions.

- Tender queue scope, renewable lease, heartbeat, fencing, and atomic
  continuation/reconciliation.
- Short database transactions around external work.
- Agent-turn reaper and documented concurrent-launch deadlock resolution.
- Stripe duplicate/order ledger and checkout idempotency.
- Durable storage cleanup and staging TTL reconciliation.

Gate: multi-worker, multi-environment, killed-worker, stale-worker, duplicate
webhook, reverse-order webhook, and cleanup-retry tests pass.

### Stage 3 — Resource and capacity hardening

Objective: bound memory, CPU, connections, waits, queues, and spend.

- Upload/download/parser/page/count/storage limits and streaming.
- PDF/LLM offloading, deadlines, bounded retries, and cancellation.
- Explicit DB pool and database timeout budgets.
- Liveness/readiness/schema/worker health.
- Agent admission before expensive reservation.
- Single-process capacity measurement and cross-process coordination decision.
- Structured logs, metrics, alerts, redaction, and named operational ownership.

Gate: stated load tests meet RSS/CPU/connection/error/latency/spend ceilings and
overload returns controlled `413`/`429` responses.

### Stage 4 — Measured client and database performance

Objective: remove traffic-linear and data-linear costs that measurements show
matter.

- Event bootstrap high-water cursor and single-loop reconciliation.
- Chat/Tender pagination and evidence scale.
- Constant-size chat send and profiled stream rendering.
- Production-container gzip/cache/header and real route bundle budgets.
- Query-count baselines, `pg_stat_statements`, and plan-based batching/indexes.

Gate: documented p50/p95/p99, request counts, transfer bytes, query counts,
browser timings, and rollback for every change. Reuse the open gates in the
existing Stage 6 performance report.

### Stage 5 — Engineering guardrails and optional structural depth

Objective: make future agent changes safer and easier to review.

- True profile create/patch/read drift guards.
- Staged high-signal Ruff rollout.
- Measured bounded xdist command.
- Disposable Postgres/pgvector migration, grants, and RLS CI.
- Narrow production-container browser acceptance.
- Deep trace/capability modules where the interface earns leverage.
- Optional `project_routes/` split.
- Optional MCP domain split after capability and contract snapshots.

Gate: all checks green; no interface/OpenAPI/tool-contract drift; structural
changes demonstrate improved locality rather than only smaller files.

### Stage 6 — Production acceptance and cutover

Objective: prove the deployed system, operators, and rollback—not merely code.

- Staging soak under realistic chat, upload, workflow, and Tender concurrency.
- DB/network/worker termination and lease-recovery exercises.
- Backup restore, retention/purge, and immutable-image rollback rehearsal.
- Two-owner isolation in the deployed environment.
- Full profile -> Project Plan -> Cost Plan -> Tender -> proposed Cost Plan
  revision journey.
- Pi tool discovery, MCP scopes, SSE, cancellation, revocation, and durable
  turn recovery.
- Stripe test/live-mode acceptance as appropriate.
- SLO dashboards and alert delivery to a named operator.
- Execute and update `docs/runbooks/stage-9-production-acceptance.md`.

Gate: signed acceptance evidence, successful restore and rollback, met SLOs,
and no open predecessor gate. Only after this may legacy deletion/cutover begin.

## 13. Task specification for a smaller implementation model

Every executable task in the implementation plan must contain all of the following.
Do not rely on the implementing model to infer missing safety details.

### Required task fields

1. **Stable ID and title** — for example `CH-1.2 — Enforce MCP cost-plan scope`.
2. **Objective** — one concrete outcome.
3. **Risk addressed** — link to the finding in this document.
4. **Preconditions** — prior tasks, clean state, configuration, migration head.
5. **Exact files and symbols** — names plus a discovery command; avoid relying
   only on volatile line numbers.
6. **Interface and invariants** — everything callers/tests must know, including
   ordering, errors, auth, performance, and configuration.
7. **Forbidden changes** — unrelated files, legacy deletions, stack changes,
   compatibility shims, or broad autofixes.
8. **Red test or measured baseline first** — precise command and expected
   failure/measurement.
9. **Implementation steps** — small ordered edits with no ambiguous “refactor as
   needed” instruction.
10. **Data migration/backfill** — expand/migrate/contract order, existing-row
    behavior, index strategy, and downgrade/application-rollback implications.
11. **Targeted verification** — fastest tests for the task.
12. **Stage verification** — broader test, container, browser, load, or live
    evidence required before the gate closes.
13. **Expected output and thresholds** — not merely “tests pass.”
14. **Observability** — log/metric/alert changes and redaction requirements.
15. **Rollback** — code, configuration, data compatibility, and retained image.
16. **Stop conditions** — exact circumstances requiring maintainer review.
17. **Commit boundary** — one reversible, reviewable commit and suggested
    message intent.
18. **Evidence artifact** — path or release record containing results.

### Verification discipline

- Do not hard-code permanent test totals. Record the starting collection and
  explain intended deltas.
- Run targeted red/green tests during implementation, then the stage-level suite
  before merge. Broad tests must be offline-safe first.
- For migrations, test fresh upgrade, upgrade from the previous head,
  application rollback against the expanded schema, and any supported
  downgrade only on disposable data.
- For authorization and tenancy, prioritize negative tests.
- For performance, record before/after p50/p95/p99, throughput, errors, CPU,
  RSS, connections, query count, and spend where applicable.
- For structural movement, snapshot the whole interface, not only names or file
  sizes.

## 14. Live and maintainer decisions still required

Code inspection cannot answer these. They should become explicit discovery or
decision tasks rather than hidden assumptions:

- Do local, staging, and production currently share writable Supabase resources?
- What schemas are exposed through the live Supabase Data API?
- What are the live grants, RLS policies, Storage policies, and Realtime
  publications?
- What is the Supabase connection ceiling and current utilization?
- What upload count/size/page/project-storage limits fit the product and plan?
- What are the target p50/p95/p99, availability, RPO, RTO, retention, and spend
  ceilings?
- Which mechanism will promote a green immutable SHA to Dokploy?
- Which operator owns alerts, restore, rollback, and incident response?
- Which production observability system will receive structured logs, metrics,
  errors, and alerts?
- Is host port 8080 externally reachable, and can it bypass the intended proxy?
- What backup coverage exists for Supabase Storage objects as distinct from the
  database?

Reasonable defaults can be proposed during the plan rewrite, but choices that
change customer limits, cost, availability, or operational authority require
maintainer approval.

## 15. Review verdict on value and ordering

The source plan’s recommendations are not mostly wrong; they are mostly too
small and too early.

- Tasks 1–2: worthwhile correctness guards after the immediate release blockers.
- Task 3: worthwhile when introduced incrementally and safely.
- Task 4: worthwhile only after test isolation and measurement.
- Task 5: weak value except for a genuinely deep trace or domain-normalization
  module.
- Tasks 6–7: worthwhile for locality and AI navigation, but provide essentially
  no request-time speedup and carry high regression risk immediately before
  launch.

The largest expected gains come from bounding work, eliminating repeat/historical
requests, shortening transactions, preventing duplicate jobs, controlling DB
connections, delivering compressed/cacheable assets, and measuring real query
and browser behavior. The largest risk reduction comes from capability
enforcement, tenant isolation, green release promotion, renewable leases,
restore/rollback evidence, and operational visibility.

That is the basis on which the implementation plan should now be rewritten.
