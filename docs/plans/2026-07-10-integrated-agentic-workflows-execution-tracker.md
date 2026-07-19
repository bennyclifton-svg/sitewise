# Clerk Integrated Agentic Workflows Execution Tracker

Date created: 2026-07-19

Status: not started

Authoritative specification:
[`2026-07-10-integrated-agentic-workflows-performance.md`](./2026-07-10-integrated-agentic-workflows-performance.md)

This file is the progress ledger for the authoritative implementation plan. It
does not replace, reinterpret, or weaken that plan. If the two documents
disagree, the authoritative implementation plan and the repository `AGENTS.md`
instructions win.

## How to use this tracker

For every implementation packet:

1. Confirm all named predecessors below and in the authoritative plan are green.
2. Create one isolated branch/worktree and commit for the numbered packet.
3. Begin with the smallest focused failing contract test.
4. Preserve unrelated dirty-worktree changes.
5. Record the implementation reference and exact validation evidence here.
6. Mark a packet complete only after its gate passes, not merely when code is
   written.
7. Record rollout and rollback results before closing a release gate.

Do not use this checklist as authorization to delete legacy code. Phase 8.5
legacy deletion remains blocked until the final production gate passes.

### Status convention

- `[ ]` Not started
- `[~]` In progress
- `[!]` Blocked
- `[x]` Complete and validated

Markdown checkboxes do not natively distinguish the two intermediate states;
use the literal `[~]` and `[!]` markers when needed.

### Packet completion record

Copy this block beneath a packet when work begins:

```text
Status:
Owner/agent:
Branch/worktree:
Commit/PR:
Started:
Completed:
Predecessors verified:
Validation commands and exact results:
Rollout result:
Rollback result or procedure verified:
Remaining risks/notes:
```

## Programme gates

- [x] Preflight gate — safe, green, measurable baseline
- [ ] Evidence tenancy gate — project UUID is the sole project-evidence identity
- [ ] R1 — shared Project Profile, Decisions, Snapshot, and Capability
- [ ] R2 — durable Project Plan, Cost Plan creation, sort, and consultant actions
- [ ] R3 internal — shared Tender selection and atomic immutable intake
- [ ] R3 customer — Tender evaluation and QS quality approval
- [ ] R4 — typed Cost Plan and approved-Tender proposal handoff
- [ ] Final production gate — role acceptance, recovery, rollback, and live SLOs
- [ ] Phase 8.5 legacy deletion — permitted only after the final gate

## Stage 0 — Safe baseline and runtime controls

Objective: restore a trustworthy build/test baseline, prevent destructive test
execution, harden agent runtime controls, and establish measurement.

### Build, test, and CI preflight

- [x] **0.0A — Repair the frontend production build**
  - Dependencies: none.
  - Gate: full frontend tests and production build pass without weakened types.
- [x] **0.0B — Guard destructive test databases**
  - Dependencies: none.
  - Gate: destructive migration tests refuse the application database and run
    only with a dedicated test URL and explicit opt-in.
- [x] **0.0C — Repair migration graph verification**
  - Dependencies: none.
  - Gate: the current single migration head passes and a synthetic branch fails.
- [x] **0.0D — Restore the default CI contract**
  - Dependencies: 0.0A, 0.0B, 0.0C.
  - Gate: default CI covers offline backend checks, frontend checks, migration
    graph verification, and Tender seed validation without touching an
    application database.

### Runtime safety, measurement, and quota controls

- [x] **0.7A — Terminate the complete agent process tree**
  - Dependencies: 0.0A–0.0D preflight where applicable.
  - Gate: zero direct or descendant processes remain after stop, disconnect,
    timeout, or cancellation on supported development and deployment platforms.
- [!] **0.7B — Verify and select a Hermes prompt transport**
  - Dependencies: safe smoke-test environment.
  - Gate: one non-argv transport is proven, or mutation rollout is explicitly
    blocked with an upstream issue.
- [!] **0.7C — Move Hermes prompts off argv**
  - Dependencies: 0.7B.
  - Gate: prompt text is absent from argv/logs and temporary material is always
    cleaned after success and every failure path.
- [x] **0.7D — Make mutation turn revocation durable**
  - Dependencies: 0.7A; migration safety preflight.
  - Gate: cancellation-versus-mutation races cannot commit after revocation, and
    worker restarts cannot reactivate revoked turns.
- [x] **0.8A — Add request/project/thread/turn correlation and agent timing**
  - Dependencies: 0.0 preflight.
  - Gate: a turn is traceable end to end with numerical timings and no sensitive
    prompt or tool content in logs.
- [x] **0.8B — Add workflow stage timing contracts/baselines**
  - Dependencies: instrument current synchronous paths initially; revisit after
    4.1 workflow-run persistence.
  - Gate: workflow timing fields and baseline evidence are recorded.
- [x] **0.8C — Add report-only frontend build-size measurement**
  - Dependencies: 0.0A.
  - Gate: current bundle size is recorded without prematurely enforcing the
    Phase 5 budget.
- [x] **0.9 — Make agent quota accounting runtime-neutral and race-safe**
  - Dependencies: migration safety preflight if a new table is required.
  - Gate: Hermes and Pi charge equally; a last-slot race admits exactly one;
    retries do not double-count.

### Stage 0 exit record

- [x] Production TypeScript build has zero errors.
- [x] Default test lane is offline and non-destructive.
- [ ] Runtime cancellation, revocation, prompt transport, and quota race tests pass.
- [x] `docs/performance/environment.md` records the canonical environment.
- [x] A dated baseline report records raw timings and bundle measurements.
- [ ] Rollback procedures for runtime-control changes have been exercised or
  explicitly documented and reviewed.

## Stage 1 — Project evidence UUID tenancy

Objective: eliminate slug/path-based evidence collisions and make project UUID
the sole identity and authorization key for project evidence.

Execute this sequence strictly in order.

- [x] **0.1 — Audit project evidence identity**
  - Dependencies: Stage 0 destructive-test guards.
  - Gate: read-only audit detects ambiguous and duplicate ownership fixtures and
    makes no data changes.
- [x] **0.2 — Add project UUID to SourceDocument**
  - Dependencies: 0.1 results reviewed.
  - Gate: isolated upgrade/downgrade succeeds; unambiguous rows backfill;
    ambiguous rows remain untouched; platform knowledge remains projectless.
- [x] **0.3 — Make hosted ingestion IDs project-scoped**
  - Dependencies: 0.2 expanded schema.
  - Gate: new IDs are project-scoped, historical IDs/citations remain valid,
    re-ingestion is idempotent, and platform seeds remain stable.
- [~] **0.4 — Contract legacy evidence identity and repair data**
  - Dependencies: 0.1–0.3; dual-write application deployed first.
  - Gate: no unresolved ambiguous project-evidence rows; cross-project duplicate
    paths are legal and isolated; within-project duplicates are rejected;
    production backup and rollback runbook is complete.
- [~] **0.5A — Switch retrieval schemas, queries, and retriever to project UUID**
  - Dependencies: 0.4 clean data gate.
  - Gate: all retrieval authorization and filtering uses owned project UUID.
- [~] **0.5B — Switch evidence, legacy chat, and MCP callers to project UUID**
  - Dependencies: 0.5A.
  - Gate: same-slug owners cannot read each other through evidence, legacy chat,
    or MCP tools.
- [~] **0.5C — Switch Project Plan and Cost Plan retrieval callers to UUID**
  - Dependencies: 0.5A.
  - Gate: workflow retrieval is tenant-isolated and platform guidance is
    included only through explicit platform scope.

### Stage 1 exit record

- [x] Two-owner/same-slug/same-path isolation suite passes for all read surfaces.
- [x] Historical citations resolve to the correct owning project.
- [x] No project authorization decision depends on slug.
- [ ] Production audit reports zero unresolved ambiguous evidence ownership.
- [ ] Expand–migrate–contract rollout and application rollback have been verified.

### Stage 0/1 implementation record — 2026-07-19

Working tree: `main` at base commit `18d3bdd4`; changes intentionally left
uncommitted for review. Canonical measurements and exact local commands are in
`docs/performance/2026-07-19-stage-0-baseline.md`.

| Packet | Implementation | Gate status / evidence |
| --- | --- | --- |
| 0.0A | Complete | Frontend tests, typecheck, and production build pass. |
| 0.0B | Complete | Guard requires distinct `TEST_DATABASE_URL` plus explicit opt-in; default lane is offline. |
| 0.0C | Complete | One head (`024_tender_quote_total_source`) passes; synthetic branch test fails as required. |
| 0.0D | Complete | CI covers backend offline checks, frontend checks, migration graph, and Tender seeds. |
| 0.7A | Complete | Windows tests pass; Linux Docker tests prove zero parent/descendant processes for success, failure, timeout, disconnect, stop, and cancellation. |
| 0.7B | Blocked | Hermes 0.17.0 ACP is a supported non-argv candidate. `/help` terminates, but a model turn blocks in the Windows coding-workspace `git status` probe; bypassing only that probe completes in 6.91 seconds. |
| 0.7C | Blocked | ACP cannot satisfy the no-prompt-content-in-logs gate as shipped: both `acp_adapter.server` and `agent.turn_context` log prompt prefixes. Hermes mutations are disabled by default. |
| 0.7D | Complete | Disposable-PostgreSQL revocation race and fresh-session restart checks pass. |
| 0.8A | Complete | Correlated structured timings omit prompt/tool content. |
| 0.8B | Complete | Synchronous workflow traces include numerical stage durations. |
| 0.8C | Complete | Report-only raw/gzip measurement recorded. |
| 0.9 | Complete | Runtime-neutral reservation/idempotency tests and the real last-slot PostgreSQL race pass. |
| 0.1 | Complete | Read-only aggregate audit detects ambiguous and duplicate ownership fixtures. |
| 0.2 | Complete | Isolated migration roundtrip and ambiguous/unambiguous/platform backfill checks pass. |
| 0.3 | Complete | Project-scoped IDs, historical-ID preservation, and database re-ingestion idempotency pass. |
| 0.4 | Complete in code and disposable acceptance | Repair dry-run/apply/idempotency, duplicate rules, contract migration, and guarded downgrade behavior pass; production audit/backup/rollout remain pending. |
| 0.5A–C | Complete in code and disposable acceptance | Evidence API service, legacy-chat retrieval, MCP reads, Project Plan, and Cost Plan isolate two same-slug owners; production activation remains gated by 0.4. |

Rollout result: **not performed**. Rollback result: **documented, not exercised**.
Remaining blockers are intentionally left unchecked in the packet and stage exit
lists above.

Validation commands and exact local results:

- `backend/.venv/Scripts/python.exe -m pytest -q` — 1,088 passed, 6 skipped,
  16 deselected in 198.03 s. The immediately preceding run had one
  order-dependent Tender fake-session failure after 1,085 passes; the test
  passed alone and the clean full rerun passed.
- `backend/.venv/Scripts/python.exe -m ruff check .` — passed.
- `backend/.venv/Scripts/python.exe -m alembic heads` — one head,
  `024_tender_quote_total_source` (the concurrent Tender migration follows
  `023_agent_turns`).
- `npm test -- --run` — 29 files / 93 tests passed.
- `npm run lint` — 0 errors, one existing TanStack Virtual compatibility
  warning.
- `npm run build` — TypeScript and Vite production build passed; initial entry
  1,720,350 bytes raw / 460,568 bytes gzip by the report-only measurement.
- `ALLOW_DESTRUCTIVE_TEST_DATABASE=1 TEST_DATABASE_URL=<dedicated Docker DB>
  backend/.venv/Scripts/python.exe -m pytest -q
  tests/tender/test_migrations.py::test_tender_migrations_roundtrip_against_database
  -m integration` — 1 passed.
- `ALLOW_DESTRUCTIVE_TEST_DATABASE=1 TEST_DATABASE_URL=<dedicated Docker DB>
  backend/.venv/Scripts/python.exe -m pytest -q
  tests/stage01/test_database_gates.py -m integration` — 1 passed; covers
  expand/repair/contract, citations, ingestion idempotency, duplicate rules,
  read isolation, quota race, revocation race, and restart persistence.
- `docker run --rm --init ... pytest -q -p no:cacheprovider
  --confcutdir=tests/agent tests/agent/test_process_tree.py` — 8 passed on
  Linux.

## Stage 2 — Shared Project State and agent-controlled Project Profile

Objective: give HTTP, UI, and MCP one revisioned profile, decision, snapshot,
capability, and durable-event contract.

- [x] **1.1 — Add profile revision and typed contracts**
  - Dependencies: Stage 0 migration safety.
  - Gate: omitted fields, explicit clears, no-ops, revisions, and stale conflicts
    have stable typed behavior.
  - Completed 2026-07-19 in migration `025_project_profile_revision` and the
    `ProjectProfileView`, `ProjectProfilePatch`, and `ProjectProfileChange`
    contracts. Focused schema/taxonomy/migration verification: 22 passed;
    disposable PostgreSQL roundtrip: 1 passed. HTTP 409 translation remains
    deliberately assigned to 1.3 after the deep module owns concurrency in 1.2.
- [x] **1.2 — Build the deep Project Profile module**
  - Dependencies: 1.1.
  - Gate: all validation families, dependent clearing, diffs, revisions, audit,
    and concurrency are owned by the module.
  - Completed 2026-07-19 in `app.projects.profile`. The public module owns
    normalized reads/options, taxonomy/scale/complexity/work-scope/role/state
    validation, typed dependency conflicts, explicit clearing, row-locked
    revision rechecks, derived overlay/risk state, and one before/after activity
    record. Focused module, taxonomy, and contract verification: 31 passed.
- [x] **1.3 — Make HTTP PATCH a thin adapter**
  - Dependencies: 1.2.
  - Gate: HTTP delegates without duplicated validation and preserves unrelated
    profile fields.
  - Completed 2026-07-19. `PATCH /projects/{project_id}` now accepts
    `ProjectProfilePatch`, delegates to `app.projects.profile`, and returns only
    `ProjectProfileChange`. Auth and entitlement checks remain at the boundary;
    validation is translated to 422, while stale revisions and incompatible
    dependent fields use stable typed 409 details. The frontend supplies the
    current revision and merges the returned canonical profile. Focused backend
    verification: 31 passed; Project Control Board tests: 2 passed; production
    frontend build passed.
- [x] **1.4 — Add the durable Project Event outbox**
  - Dependencies: Stage 0 migration safety; stable event contracts.
  - Gate: state mutation and event commit atomically with monotonic project
    cursors and replayable resource/workflow events.
  - Completed 2026-07-19 in migration `026_project_events` and
    `app.projects.events`. Events carry per-project monotonic sequences, schema
    and resource revisions, actor/action metadata, safe payloads, and optional
    project-scoped deduplication keys. Owned cursor reads are available at
    `GET /projects/{project_id}/events`; profile mutations and tender-worker
    completions publish in their mutation transaction. Focused offline
    verification: 54 passed; disposable PostgreSQL migration roundtrip and
    atomic rollback/concurrent deduplication integration gates: 2 passed.
- [x] **1.5 — Bind mutation intent and persist profile proposals**
  - Dependencies: 1.2, 1.4, 0.7D.
  - Gate: document-derived facts remain proposals until confirmed; explicit
    reversible user commands use bound project/turn intent.
  - Completed 2026-07-19 in migration `027_profile_proposals`,
    `app.agent.mutation_intent`, and `app.projects.profile_proposals`. The chat
    boundary hashes only the current user message and stores exact target values
    with a narrow `profile_mutation` scope for explicit imperatives. Hedged,
    quoted, document-derived, and unrelated workflow instructions receive no
    mutation scope and are directed to proposal/confirmation. Evidence-linked
    proposals persist pending/accepted/rejected state, publish project events,
    and accept/reject under a locked optimistic profile revision. Focused
    offline verification: 77 passed; disposable PostgreSQL migration/outbox and
    proposal lifecycle gates: 3 passed across the final integration runs.
- [x] **1.6 — Add profile MCP adapters**
  - Dependencies: 1.2, 1.4, 1.5.
  - Gate: narrow read/options/update tools share the Project Profile module,
    enforce expected revision, and never expose generic mutation.
  - Completed 2026-07-19. The MCP server now exposes the six narrow Project
    Profile read/options/update/propose/accept/reject tools. Direct updates pass
    the exact requested values through durable-turn authorization and require
    the server-minted `profile_mutation` scope plus `expected_revision`;
    evidence-derived facts persist proposals without touching confirmed state.
    All adapters delegate to the shared profile/proposal modules, translate
    stable conflicts, publish through their underlying services, and reject
    cross-project tokens before profile reads. Agent prompt and workspace
    guidance now describe the same policy. Complete MCP regression: 70 passed;
    Ruff checks passed.
- [x] **1.7 — Make Project Decisions a shared revisioned interface**
  - Dependencies: 1.4.
  - Gate: UI, workflows, and MCP share optimistic revisions, locked-decision
    semantics, activity, and events.
  - Completed 2026-07-19 in migration `028_project_decision_revisions` and
    `app.projects.decisions`. Project Decisions now have per-decision and
    set-wide optimistic revisions, explicit locks, durable provenance and
    evidence-conflict state, and project resource events. HTTP, PMP/Cost Plan
    regeneration, and the five narrow MCP read/update/lock adapters use the
    same service; generated selections cannot replace a locked user choice and
    are retained as an explicit conflicting suggestion. The frontend sends and
    renders the same revisions returned by HTTP/MCP. Focused backend gate and
    regression verification: 145 passed; affected frontend type-check and 5
    render tests passed; Ruff and the single-head Alembic graph passed.
- [x] **1.8 — Build the minimal deterministic Project Snapshot**
  - Dependencies: 1.2, 1.7; UUID evidence reads.
  - Gate: one deterministic snapshot composes profile, decisions, evidence, and
    selection metadata without importing TCM internals.
  - Completed 2026-07-19 in `app.projects.snapshot` and
    `app.schemas.project_snapshot`. Snapshot v1 composes tenant-scoped project
    identity and setup inputs, revisioned profile and locked decisions, bounded
    evidence/failure summaries, explicit non-persisted selection state, and
    pending profile proposals without importing TCM. Stable SHA-256 content and
    evidence fingerprints exclude generation time; missing setup remains
    `needs_input`, and bounded collections expose completeness. HTTP and MCP
    share the reader, agent turn context embeds its version/fingerprint, and
    manual PMP/Cost Plan starts persist the same snapshot provenance. Focused
    and adjacent regression verification: 247 passed, 4 skipped; Ruff passed.
- [x] **1.9 — Publish the workflow capability matrix**
  - Dependencies: 1.8.
  - Gate: UI and agent share identical readiness/unsupported results and no
    missing reference capability is filled with general model knowledge.
  - Completed 2026-07-19 in `app.projects.workflow_capabilities` and
    `app.schemas.workflow_capabilities`. The snapshot-fingerprinted matrix
    publishes deterministic `supported`, `needs_input`, and `unsupported`
    results with reasons and required fields for Project Plan, Cost Plan,
    Tender Comparison, and consultant procurement. HTTP/bootstrap, MCP,
    Hermes context, lifecycle tiles, and workflow starts consume the same
    result; Tender and consultant adapters reject unsupported work before any
    mutation or enqueue. Coverage is explicit for Class 1a Tender work and NSW
    residential architect-PM Cost Plans. Validation: full backend suite 1,153
    passed, 6 skipped, 18 deselected; focused frontend test passed; TypeScript,
    ESLint, Ruff, and `git diff --check` passed.
- [x] **1.10A — Reconcile project queries and events**
  - Dependencies: 1.4 and relevant query contracts.
  - Gate: immediate responses and durable cursor replay keep all project
    surfaces current without full-page refresh.
  - Completed 2026-07-19. Project detail/profile now uses one exact TanStack
    Query key seeded by cockpit bootstrap and updated immediately by manual HTTP
    responses. Hermes profile commits publish same-turn resource parts that
    invalidate that key, while the durable project-event cursor deduplicates by
    ID/sequence and targets only detail, evidence, workspace, or activity data.
    Polling runs at 250 ms during active work and 1.5 s while idle, pauses while
    hidden, resumes immediately on visibility, and replays without duplicate UI
    side effects. Validation: frontend 104 passed and production build passed;
    backend 1,153 passed, 6 skipped, 18 deselected; final focused frontend 9
    passed; TypeScript, ESLint, Ruff, and focused MCP profile tests passed.
- [x] **1.10B — Protect dirty profile forms**
  - Dependencies: 1.10A.
  - Gate: incoming revisions never silently overwrite local edits; conflicts
    can be reviewed and resolved.
  - Completed 2026-07-19 in `ProjectControlBoard`. Clean profile controls now
    render directly from query-backed project state; local form state exists
    only for unsaved edits and records its base revision. A newer revision
    preserves the draft, blocks saving, and offers explicit Reload latest and
    Keep editing actions. Keep editing rebases only fields changed by the user
    onto the latest server values, preserving unrelated concurrent changes.
    Validation: 5 focused component tests passed; full frontend suite 108
    passed; TypeScript, ESLint, and production build passed.
- [x] **1.10C — Isolate chat failure from the project shell**
  - Dependencies: shared query boundaries.
  - Gate: project controls remain usable when chat bootstrap or streaming fails.
  - Completed 2026-07-19. Project bootstrap errors and chat session errors now
    have separate state boundaries. Thread/message failures render as a local
    ChatRail alert with retry, while runtime failures remain in ChatPanel; none
    replace the project shell. Focused tests prove repository, workflow nav, and
    Cost Plan controls remain rendered and actionable during chat failure.
    Validation: 13 focused tests passed; full frontend suite 111 passed;
    TypeScript, ESLint, and production build passed.

### R1 release record

- [ ] Stage 1 evidence tenancy gate is green.
- [x] Profile HTTP/MCP parity and concurrent-edit tests pass.
- [x] Decisions, Snapshot, and Capability contract tests pass.
- [ ] Agent profile event becomes visible in the UI at p95 ≤500 ms.
- [ ] Additive rollout completed without removing legacy paths.
- [ ] Rollback to the prior application deployment has been rehearsed.

#### R1 gate audit — 2026-07-19

Status: **blocked; R1 is not closed**.

Repository and disposable-environment evidence:

- Profile, profile-contract, profile-MCP, decision, decision-MCP, Snapshot,
  Capability, and durable-event focused tests: 47 passed.
- Project query reconciliation, dirty-profile protection, and chat-isolation
  frontend tests: 11 passed; TypeScript type-check passed.
- Ruff passed and Alembic reports the single head
  `028_project_decision_revisions`.
- The Stage 0/1 destructive database acceptance and durable Project Event
  integration gates passed against a disposable pgvector/PostgreSQL 16
  database: 2 passed.
- The audit found and fixed a migration-order regression in the evidence repair
  script: it now reads only the legacy `projects.id`/`projects.slug` contract
  while the database is at migration `021b`, instead of loading Stage 2 ORM
  columns that do not yet exist.
- The additive implementation retains the legacy modules and paths. The active
  event-cursor contract polls at 250 ms and same-turn agent resource parts
  invalidate the exact project query immediately.

Release blockers requiring deployment evidence:

- The production evidence-ownership audit has not reported zero ambiguous rows,
  so Stage 1 Tasks 0.4 and 0.5A–C remain production-gated.
- The ≤500 ms figure is supported by the 250 ms active polling contract but has
  not been measured as a browser-to-deployment p95; a contract test is not an
  observed latency result.
- No application rollout was performed during this audit, and no legacy path
  was removed.
- Rollback to the prior application deployment has not been rehearsed. The
  earlier Stage 0/1 record remains accurate: rollback is documented but not
  exercised.

## Stage 3 — Shared Tender selection and immutable intake

Objective: make UI and chat share one ordered Tender selection and freeze exact
context and inputs at comparison intake.

- [x] **2.1 — Persist purpose-scoped document selections**
  - Dependencies: Stage 1 UUID tenancy; durable events.
  - Gate: immutable/revisioned purpose selections enforce project ownership and
    retention locks.
- [x] **2.2A — Add Tender selection HTTP and MCP adapters**
  - Dependencies: 2.1.
  - Gate: both adapters use the same expected-revision selection service.
- [x] **2.2B — Add explicit quote-group selection UI**
  - Dependencies: 2.2A.
  - Gate: UI persists and displays 2–5 ordered quote groups, including main
    quote, schedules, and addenda.
- [x] **2.3 — Build the TCM-owned project-context adapter**
  - Dependencies: Project Snapshot/Profile contracts.
  - Gate: supported facts cross the boundary through a typed DTO; TCM does not
    read RAG chunks or import core internals beyond the defined interface.
- [x] **2.4A — Add a read-only Tender preparation contract**
  - Dependencies: 2.1, 2.3.
  - Gate: preparation reports exact ready/needs-input state without mutation.
- [x] **2.4B — Implement atomic immutable Tender intake**
  - Dependencies: 2.4A.
  - Gate: selection, file versions/hashes, context, and intake identity freeze
    atomically and idempotently.
- [x] **2.4C — Cut HTTP, MCP, and UI over to atomic intake**
  - Dependencies: 2.4B.
  - Gate: all entry points use the same intake and preserve existing comparisons.
- [x] **2.5 — Fix comparison-scoped report state**
  - Dependencies: may proceed beside 2.3–2.4.
  - Gate: report, QA, and publication state cannot leak between comparisons.

### R3 internal release record

- [x] UI and MCP observe the same selection and revision.
- [x] Historical Tender context stays frozen after current-profile changes.
- [x] Selected/frozen documents cannot be deleted improperly.
- [x] Internal atomic-intake acceptance passes.
- [ ] Customer exposure, approval, and handoff remain disabled pending R3 customer.
- [ ] Rollback preserves already-created immutable comparisons.

### Stage 3 implementation record — 2026-07-19

Status: complete in code and disposable acceptance; rollout gates remain open
Owner/agent: Codex
Branch/worktree: `feature/stage3-tender-intake` / `.worktrees/stage3-tender-intake`
Commit/PR: local Stage 3 implementation commit
Started: 2026-07-19
Completed: 2026-07-19
Predecessors verified: Stage 1 UUID tenancy and Stage 2 durable Project Events,
Profile, Snapshot, and Capability implementations are present and their offline
regressions pass.
Validation commands and exact results:

- `backend/.venv/Scripts/python.exe -m pytest -q` — 1,156 passed, 6 skipped,
  19 deselected in 60.43 s.
- `backend/.venv/Scripts/python.exe -m ruff check app tender tests ...` — passed.
- `backend/.venv/Scripts/python.exe -m alembic heads` — one head,
  `030_tender_immutable_intake`.
- `pnpm test -- --run` — 31 files / 109 tests passed.
- `pnpm lint` — zero errors; one existing TanStack Virtual compatibility warning.
- `pnpm build` — TypeScript and Vite production build passed.
- Disposable pgvector PostgreSQL migration roundtrip plus Stage 3 atomic intake
  acceptance — 2 passed; covers rollback-on-invalid-input, graph atomicity,
  turn-idempotent replay after selection advancement, conflicting reuse,
  frozen file hashes/storage identities, and migration downgrade/upgrade.

Rollout result: not performed.
Rollback result or procedure verified: schema roundtrip passed in disposable
PostgreSQL; application rollback with preserved production comparisons remains
to be rehearsed.
Remaining risks/notes: customer exposure, QS approval, production rollout, and
application rollback remain gated. Legacy comparison rows remain readable; the
old partial creation endpoints return 410 and no longer create partial graphs.

## Stage 4 — Canonical Artefact Revision

Objective: give all artefacts concurrency-safe versions, edit policies, exports,
provenance, activity, and durable events.

- [ ] **3.1 — Make draft version allocation concurrency-safe**
  - Dependencies: Stage 0 migration safety.
  - Gate: concurrent allocations cannot create duplicate versions.
- [ ] **3.2A — Build the core Artefact Revision interface**
  - Dependencies: 3.1, 1.4.
  - Gate: expected-base checks, policy, provenance, export jobs, activity, and
    events share one transactionally safe interface.
- [ ] **3.2B — Add the Project Plan revision adapter**
  - Dependencies: 3.2A, 1.7.
  - Gate: Project Plan edits and decision synchronization are exact.
- [ ] **3.2C — Add the current Cost Plan revision adapter**
  - Dependencies: 3.2A.
  - Gate: current Cost Plan draft, markdown, workbook, and provenance agree.
- [ ] **3.2D — Add the consultant artefact revision adapter**
  - Dependencies: 3.2A, 1.7 where decisions are affected.
  - Gate: consultant outputs publish and navigate through exact revisions.
- [ ] **3.2E — Add the TCM-owned Tender publication adapter**
  - Dependencies: 3.2A; TCM boundary contract.
  - Gate: TCM publishes immutable report references without core importing
    Tender models or querying Tender tables.
- [ ] **3.3 — Route all existing edit paths through Artefact Revision**
  - Dependencies: matching 3.2 adapter.
  - Gate: no UI or MCP caller performs direct generic draft writes.
- [ ] **3.4A — Persist and rehydrate agent result references**
  - Dependencies: durable run/artefact reference contract.
  - Gate: sanitized result references survive thread reload.
- [ ] **3.4B — Make artefact navigation exact and durable**
  - Dependencies: 3.4A.
  - Gate: every result opens the exact artefact and revision intended.
- [ ] **3.5 — Remove repair writes from cockpit GETs**
  - Dependencies: 3.3 and all writer invariants proven.
  - Gate: cockpit reads perform zero storage/database repair writes.

### Stage 4 exit record

- [ ] Concurrent revision and stale-base suites pass.
- [ ] Canonical rows and immutable exports agree for every adapted artefact.
- [ ] Failed exports remain retryable and are never advertised as ready.
- [ ] Per-artefact additive rollout and rollback results are recorded.

## Stage 5 — Durable core workflow actions

Objective: give UI and MCP shared durable start/status/cancel/result behavior for
Project Plan, Cost Plan creation, file sort, and consultant actions.

- [ ] **4.1 — Add core workflow-run persistence**
  - Dependencies: Stage 0 migration safety; Snapshot/capability contracts.
  - Gate: frozen inputs, project-scoped idempotency, safe claims, recovery, and
    real downgrade/tenancy behavior pass.
- [ ] **4.2A — Build the core workflow worker infrastructure**
  - Dependencies: 4.1, 1.4.
  - Gate: claims, leases, heartbeat, retry, cancellation, recovery, progress,
    and terminal events are durable and idempotent.
- [ ] **4.2B — Add Project Plan worker adapters and acceptance**
  - Dependencies: 4.2A, 3.2B.
  - Gate: create/refresh pass all canonical PMP acceptance fixtures, preserving
    locked decisions and evidence status.
- [ ] **4.2C — Add the Cost Plan creation worker adapter**
  - Dependencies: 4.2A, 3.2C.
  - Gate: creation publishes matching draft, markdown, workbook, provenance,
    and event while preserving the prior accepted version on failure.
- [ ] **4.2D — Add file-sort and consultant action adapters**
  - Dependencies: 4.2A, 3.2D, 1.7.
  - Gate: UI/chat share typed services and long actions survive request timeout.
- [ ] **4.2E — Deploy the core worker**
  - Dependencies: 4.2A and at least one accepted adapter.
  - Gate: health, shutdown, lease recovery, and one-worker rollback pass on the
    deployment fixture.
- [ ] **4.3A — Add asynchronous HTTP workflow endpoints additively**
  - Dependencies: 4.1, relevant worker adapter.
  - Gate: typed start/status/cancel/result endpoints acknowledge within p95
    ≤500 ms and do not break existing callers.
- [ ] **4.3B — Add narrow MCP workflow adapters**
  - Dependencies: 4.3A/shared run service, 0.7D.
  - Gate: explicit tools share the same authorization, idempotency, run, result,
    and cancellation interfaces as HTTP.
- [ ] **4.4A — Cut the UI over to asynchronous workflow state**
  - Dependencies: 4.3A, 1.10A.
  - Gate: project surfaces update without manual refresh; cached workflow tabs
    render in under 100 ms; failures have a clear retry path.
- [ ] **4.4B — Retire superseded synchronous workflow routes**
  - Dependencies: 4.4A plus browser acceptance.
  - Gate: no cockpit/MCP caller remains; rollback is by prior deployment rather
    than a permanent compatibility shim.
- [ ] **4.5 — End-to-end action parity gate**
  - Dependencies: all intended 4.2–4.4 workflow packets.
  - Gate: the authoritative ten-step UI/chat parity script passes on Linux/WSL
    and in a browser with run IDs, revisions, timing, and screenshots.

### R2 release record

- [ ] Project Plan create/refresh acceptance is green.
- [ ] Cost Plan creation acceptance is green; refresh is not advertised yet.
- [ ] Sort and consultant action acceptance is green.
- [ ] Cancellation leaves no process, job, or later artefact orphan.
- [ ] Each workflow was released independently after its own gate.
- [ ] Worker and application rollback were exercised without losing run records.

## Stage 6 — Read-path, frontend, retrieval, and runtime performance

Objective: meet hard performance budgets from the canonical baseline without
weakening correctness, quality, or tenancy.

- [ ] **5.1 — Route-level code splitting and bundle budgets**
  - Dependencies: 0.0A, 0.8C.
  - Gate: initial JS ≤250 kB gzip; Three.js is absent from non-demo routes; lazy
    workflow entry chunks ≤150 kB gzip; build enforces budgets.
- [ ] **5.2A — Separate project-shell and chat bootstrap reads**
  - Dependencies: shared frontend queries/events.
  - Gate: no more than two critical calls; warm bootstrap p95 ≤500 ms; GETs
    perform zero writes; chat failure does not replace the shell.
- [ ] **5.2B — Add list pagination additively**
  - Dependencies: stable list contracts.
  - Gate: bounded stable first pages are cut over consumer by consumer.
- [ ] **5.3A — Bound chat history and project-file queries**
  - Dependencies: UUID-filtered data access.
  - Gate: row counts are bounded and filters execute in SQL.
- [ ] **5.3B — Share frontend agent configuration**
  - Dependencies: frontend query foundation.
  - Gate: one configuration request per cache window and no unsupported
    cross-project promise.
- [ ] **5.3C — Pool Supabase auth HTTP connections**
  - Dependencies: lifecycle baseline.
  - Gate: pooled client lifecycle is correct and cold/warm auth timings remain
    visible with unchanged behavior.
- [ ] **5.4A — Batch retrieval neighbours**
  - Dependencies: 0.5A and retrieval baseline.
  - Gate: golden results are equivalent, query count is constant, p95 improves,
    and project isolation remains intact.
- [ ] **5.4B — Decide semantic/lexical query concurrency**
  - Dependencies: retrieval benchmark fixture.
  - Gate: decision record selects a measured mechanism or explicitly retains
    sequential execution; no production implementation occurs in this packet.
- [ ] **Follow-up from 5.4B — Implement the recorded retrieval-concurrency decision, if any**
  - Dependencies: follow-up packet produced by 5.4B.
  - Gate: exact follow-up quality, pressure, latency, and isolation criteria pass.
- [ ] **5.5A — Batch uploads and refresh once**
  - Dependencies: query/event reconciliation.
  - Gate: at most two heavy ingests run concurrently; one refresh occurs per
    batch; individual failures remain visible and isolated.
- [ ] **5.5B — Batch delete with optimistic rollback**
  - Dependencies: retention locks and project-scoped delete contract.
  - Gate: cross-project IDs fail atomically, locked Tender inputs survive, and
    per-file failures roll back visibly.
- [ ] **5.6A — Share Tender queries and polling**
  - Dependencies: durable events and immutable comparison state.
  - Gate: cached transitions <100 ms and active visible progress is ≤2 s stale.
- [ ] **5.6B — Make QA acceptance optimistic**
  - Dependencies: 5.6A.
  - Gate: optimistic response <100 ms, settled p95 ≤800 ms, and failure rollback
    does not reload the full queue.
- [ ] **5.7 — Measure and decide Hermes session reuse**
  - Dependencies: agent timing baseline and runtime safety.
  - Gate: decision is based on measured ≥20% TTFT improvement plus concurrency,
    cancellation, history, and tenancy tests; no production branch is implemented.
- [ ] **5.8 — Implement the recorded Hermes session decision**
  - Dependencies: exact follow-up packet from 5.7.
  - Gate: the same measurement and safety suite passes after implementation.

### Stage 6 exit record

- [ ] All applicable Section 9 hard SLOs pass in the canonical environment.
- [ ] Raw timings and build manifests are preserved in dated reports.
- [ ] Every performance change records comparison, resource pressure, and rollback.
- [ ] No quality, correctness, or tenant-isolation regression is present.

## Stage 7 — Full Tender performance, cost, and quality

Objective: evaluate the complete Tender pipeline and obtain the customer-quality
and QS approval required for customer exposure and downstream handoff.

- [ ] **6.1 — Wire real TCM usage telemetry**
  - Dependencies: stable TCM pipeline.
  - Gate: real LLM stages record correlated non-zero usage and deterministic
    stages correctly record zero without customer/prompt content.
- [ ] **6.2 — Replace the extraction-only speed gate**
  - Dependencies: 6.1, canonical performance environment.
  - Gate: cold/warm full-pipeline ledger covers intake through report-ready or
    QA-required and identifies slow stages.
- [ ] **6.3 — Produce measured optimization packets**
  - Dependencies: 6.2.
  - Gate: each proven bottleneck produces a separate exact packet; production
    behavior is not modified by this decision task.
- [ ] **6.4 — Build the required Tender evaluation corpus**
  - Dependencies: protected fixture storage and consent/redaction process.
  - Gate: at least 30 anonymized real documents plus adversarial coverage pass
    manifest validation and access review.
- [ ] **6.5 — Run Tender evaluation and complete QS acceptance**
  - Dependencies: 6.4; frozen prompt/model/taxonomy candidate.
  - Gate: PRD thresholds and QS review pass; all report phrases come from the
    approved language file; evaluated versions are frozen.
- [ ] **6.6 — Implement measured Tender optimizations**
  - Dependencies: one exact packet from 6.3 at a time; 6.5 rerun when required.
  - Gate: each change improves its measured stage and preserves evaluation,
    deterministic arithmetic, and two-owner isolation; otherwise it is reverted.

### R3 customer release record

- [ ] Three-quote full-pipeline baseline and provider variance are recorded.
- [ ] Five-quote run meets the ≤30-minute target excluding human QA.
- [ ] Golden corpus, evaluation thresholds, report language, and QS gate pass.
- [ ] Customer exposure and approval have an explicit rollout decision.
- [ ] Frozen evaluated versions and rollback procedure are recorded.

## Stage 8 — Typed Cost Plan and cross-workflow handoffs

Objective: make typed cost state canonical, arithmetic deterministic, row edits
safe, and Tender-to-Cost handoff explicit, proposed, and reversible.

- [ ] **7.1 — Extend capabilities for typed Cost Plan actions**
  - Dependencies: 1.9, workflow contracts.
  - Gate: UI and agent share exact create/refresh/edit/handoff capability and
    unsupported reference coverage is explicit.
- [ ] **7.2A — Add canonical Cost Plan schema**
  - Dependencies: 3.2A, 4.1, migration safety.
  - Gate: immutable versions, Decimal-safe fields, constraints, tenancy,
    upgrade/downgrade, and two-owner isolation pass.
- [ ] **7.2B — Import existing Cost Plan drafts once**
  - Dependencies: 7.2A.
  - Gate: dry-run is default, warnings are explicit, totals reconcile, source
    drafts remain audit evidence, and apply is idempotent.
- [ ] **7.2C — Implement deterministic Cost Plan arithmetic**
  - Dependencies: 7.2A and explicit financial rules.
  - Gate: exact fixtures cover rounding, GST, allowances, contingency,
    escalation, variance, and invalid inputs with no float/model arithmetic.
- [ ] **7.3A — Render Cost Plan markdown from typed state**
  - Dependencies: 7.2C, Artefact Revision.
  - Gate: rendered rows/totals exactly match fixtures and retain provenance.
- [ ] **7.3B — Render the workbook from typed state**
  - Dependencies: 7.3A.
  - Gate: workbook and markdown agree exactly and no markdown reparsing remains.
- [ ] **7.4A — Add narrow Cost Plan read/edit tools**
  - Dependencies: 7.2C, 7.3A–B.
  - Gate: expected-base mutations change only typed targets, recalculate in
    Python, regenerate exports, enforce tenancy, and never rank builders.
- [ ] **7.4B — Add the approved-Tender Cost handoff**
  - Dependencies: 3.2E, R3 customer, 7.2–7.3.
  - Gate: only approved/frozen/QS-passed/operator-approved results cross through
    immutable DTOs after explicit quote/package choice; apply is idempotent and
    creates only a proposed Cost revision.
- [ ] **7.4C — Add safe Cost Plan refresh**
  - Dependencies: typed state, Workflow Run, Artefact Revision.
  - Gate: refresh uses frozen/current typed inputs plus expected base, preserves
    locked items, and returns exact conflicts/proposals without auto-acceptance.
- [ ] **7.5 — Add dependency snapshots and stale reasons**
  - Dependencies: profile, evidence, decisions, artefact, and handoff revisions.
  - Gate: deterministic stale reasons identify affected outputs; dependency
    cycles are rejected; historical Tender context remains frozen.

### R4 release record

- [ ] Typed schema/import/arithmetic/rendering gates pass.
- [ ] Row tools and refresh pass revision, conflict, provenance, and tenancy tests.
- [ ] Approved-Tender handoff passes R3 customer prerequisites.
- [ ] No budget or builder decision is silently accepted.
- [ ] Proposed revisions are visibly reversible.
- [ ] Rollback to the prior accepted Cost Plan version has been exercised.

## Stage 9 — Project intelligence, production acceptance, and cutover

Objective: provide one deterministic project overview, prove role journeys in
production, test recovery/rollback, and only then remove legacy paths.

- [ ] **8.1 — Enrich Project Snapshot with rollups and next actions**
  - Dependencies: R1–R4 components as applicable.
  - Gate: UI and agent share one snapshot; every next action names its blocking
    fact and target route/tool; unsupported workflows are never recommended.
- [ ] **8.2 — Role-based product acceptance**
  - Dependencies: 8.1 and complete isolated fixtures/harness.
  - Gate: construction manager, architect, and design manager scenarios achieve
    100% required assertions and expected typed outcomes with zero cross-project
    access or silent acceptance.
- [ ] **8.3 — Production gate and legacy cutover**
  - Dependencies: all prior applicable gates.
  - [ ] Validate DB, storage, Hermes/Pi, MCP, SSE, both workers, ODL, Stripe,
    isolation, cancellation, recovery, the full role journey, bundles, and
    latency on the live production stack.
  - [ ] Exercise production rollback and reconcile durable state successfully.
  - [ ] After the final production gate only, perform Phase 8.5 legacy deletions
    as small, individually revertible packets and update documentation and
    completion ledgers.
  - Gate: all production acceptance and rollback requirements pass before any
    legacy deletion begins.

### Final production release record

- [ ] All Phase 0–8 task gates are complete or explicitly marked not applicable
  with an approved rationale.
- [ ] Full profile → Project Plan → Cost Plan → Tender scenario passes live.
- [ ] Two owners with identical slug/path remain isolated live.
- [ ] Cancellation and worker/API recovery pass live.
- [ ] Performance, bundle, Tender evaluation, and QS gates pass.
- [ ] Role acceptance manifests and evidence are archived.
- [ ] Backup and rollback were tested successfully.
- [ ] Final cutover decision is recorded with approver and date.
- [ ] Only after all items above: Phase 8.5 deletion completed and verified.

## Cross-cutting risk register

Update this table as risks are discovered or retired.

| ID | Risk | Stage | Mitigation/gate | Status | Owner | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| R-01 | Cross-owner evidence collision through slug/path identity | 1 | UUID migration and two-owner tests | Mitigated in disposable acceptance; production rollout pending | Codex | `tests/stage01/test_database_gates.py` |
| R-02 | Destructive tests target an application database | 0 | Dedicated URL, opt-in, equality refusal | Mitigated; disposable-DB proof pending | Codex | `tests/tender/test_migrations.py` |
| R-03 | Agent cancellation races with a mutation commit | 0/2 | Durable revocation and transaction lock | Mitigated in disposable acceptance; rollout pending | Codex | `tests/stage01/test_database_gates.py` |
| R-04 | UI and agent mutations diverge | 2–5 | Shared modules and adapter parity tests | Open |  |  |
| R-05 | Database artefact and storage export diverge | 4 | Canonical row plus retryable outbox/export job | Open |  |  |
| R-06 | Worker retry publishes duplicate or stale output | 5 | Frozen inputs, leases, idempotency, base revision | Open |  |  |
| R-07 | Performance work weakens result quality or tenancy | 6/7 | Golden tests, isolation tests, measured rollback | Open |  |  |
| R-08 | Tender reaches customers without evaluation/QS approval | 7 | R3 customer hard gate | Open |  |  |
| R-09 | Cost handoff silently selects a builder or accepts budget | 8 | Explicit confirmation; proposed revision only | Open |  |  |
| R-10 | Legacy deletion occurs before recovery is proven | 9 | Final gate plus exercised rollback | Open |  |  |

## Performance and reliability gate ledger

Record the dated report link and result for every hard gate.

| Measure | Required gate | Result | Evidence/report |
| --- | --- | --- | --- |
| Cross-project evidence/mutation isolation | 100% | Pass in disposable DB; production pending | `tests/stage01/test_database_gates.py`; `docs/runbooks/evidence-uuid-tenancy-rollout.md` |
| Orphan child processes after cancel/timeout | 0 | Pass on Windows and Linux | `tests/agent/test_process_tree.py` |
| Production TypeScript build | 0 errors | Pass | `docs/performance/2026-07-19-stage-0-baseline.md` |
| Initial JavaScript | ≤250 kB gzip | Pending |  |
| Three.js on non-demo routes | 0 bytes | Pending |  |
| Warm cockpit bootstrap | p95 ≤500 ms; zero writes | Pending |  |
| Critical calls before composer usable | ≤2 | Pending |  |
| Agent profile event to visible UI | p95 ≤500 ms | Pending |  |
| Workflow enqueue acknowledgement | p95 ≤500 ms | Pending |  |
| Cached workflow tab transition | <100 ms | Pending |  |
| QA optimistic response | <100 ms | Pending |  |
| QA settled server response | p95 ≤800 ms | Pending |  |
| Three-quote cold Tender run | ≤90 s measured stretch; 60 s goal | Pending |  |
| Five-quote Tender run excluding human QA | ≤30 min | Pending |  |
| Concurrent artefact revisions | No duplicates or stale exports | Pending |  |
| Default test lane | Offline/non-destructive; shard <60 s | Correct scope; local unsharded run >60 s | `pyproject.toml`; `.github/workflows/ci.yml`; baseline report |

## Decision and exception log

Any deviation from the authoritative order or gate must be recorded here before
implementation. An exception cannot waive tenancy, destructive-test, explicit
confirmation, deterministic arithmetic, Tender evaluation/QS, or final legacy
cutover requirements.

| Date | Packet/gate | Decision or exception | Reason | Approver | Follow-up |
| --- | --- | --- | --- | --- | --- |
| 2026-07-19 | 0.0–0.5C branch discipline | Implemented in the existing `main` working tree rather than one branch/worktree and commit per packet. | The user explicitly requested continuation after updating `main`; the checkout also received commit `18d3bdd4` during implementation. Splitting already interdependent uncommitted work would add merge risk without changing gate evidence. | User request | Keep changes uncommitted for review; split into logical commits before release if required. |
| 2026-07-19 | Stage 0 before Stage 1 | Implemented Stage 1 code while 0.7B/0.7C and database acceptance remain blocked; no schema or production rollout was performed. | Hermes v0.17.0 has no verified non-argv agent-turn prompt transport, and no disposable database was supplied. UUID tenancy work is independently testable and reduces risk, but its rollout remains gated. | User request to implement both stages | Do not deploy 022/023 or enable Hermes mutations until the named gates pass. |
| 2026-07-19 | Stage 0/1 checkpoint | Create one atomic Stage 0/1 commit while leaving the concurrent Tender quote-total/QA feature and unrelated assets uncommitted. | After reviewing the completed gates, the user authorized proceeding with the recommendation to separate the mixed worktree. The Stage migrations, models, runtime gates, and evidence documentation are interdependent. | User follow-up: “proceed” | Review the isolated commit; handle the Tender feature separately. |

## Current next action

Stage 0/1 code and disposable acceptance are present in the working tree. Next:
report the minimized Hermes ACP Windows workspace-probe hang and both prompt-log
sites upstream when maintainer-authorized, then verify the released fix with
Clerk's MCP configuration. Separately perform the approved production backup,
read-only audit, expand/repair/contract rollout, post-rollout two-owner checks,
and rollback rehearsal. Hermes mutations remain disabled and the Stage 0/1
programme exits remain incomplete until those gates pass.
