# Clerk Integrated Agentic Workflows and Performance Plan

Date: 2026-07-10

Status: proposed implementation plan

Audience: implementation agents, including smaller or less-capable LLMs

## 1. Objective

Turn Clerk's existing Project Plan, Cost Plan, Tender Comparison, document
repository, and chat surfaces into one fast project operating system.

The desired outcome is not a chatbot that clicks controls. The React UI and the
chat agent must be two adapters over the same validated modules:

- one canonical project profile;
- one persisted document selection;
- one artefact revision path;
- one durable workflow-run contract;
- one project state/read model;
- one event vocabulary that keeps every visible surface current.

This plan is additive to the July Hermes Foundation plans. It does not change
the locked stack or the TCM boundary. Do not perform the Phase 8.5 legacy
deletion until this plan's production gate passes.

## 2. Executive diagnosis

Clerk already has capable individual implementations. Phases 2-7 of the Hermes
Foundation are recorded green. The main problem is architectural locality:
manual UI actions, agent actions, workflow output synchronization, and frontend
state each follow different paths.

The user's reported profile problem is exactly represented in the code:

- ProjectControlBoard can manually PATCH class, work type, role, state, scale,
  complexity, and work scope.
- turn_context.py gives those values to Hermes as read-only prompt context.
- workspace_instructions.py tells Hermes to ask the user to declare missing
  values.
- the MCP server exposes no project-profile read or update tool.
- after an agent turn, ProjectCockpitPage refreshes messages, not project state.

Adding one update tool without fixing the shared mutation and state seams would
create lost updates and stale controls. The correct first product slice is a
deep Project Profile module used by both HTTP and MCP.

There is also a release-blocking tenancy risk that comes before new agent write
power:

- Project slugs are unique only per owner.
- SourceDocument identifies a project by slug string.
- SourceDocument.relative_path is globally unique.
- document and chunk UUIDs are derived from path alone.
- retrieval authorization starts with a project UUID but filters documents by
  slug.

Two owners can create the same slug and path. Their storage objects are safely
UUID-prefixed, but their indexed evidence can collide or be retrieved from the
same slug-scoped corpus. Phase 0 must migrate project evidence identity and
retrieval to project UUID before broader release.

### 2.1 Delivery strategy at a glance

| Gate | User-visible outcome | Required work |
| --- | --- | --- |
| P0 | Safe, green base | Build/test guards, UUID evidence tenancy, process-tree cancellation, measurement |
| R1 | Chat controls the same Project Profile and Decisions as the UI | Project State, durable events, snapshot, capability, frontend reconciliation |
| R2 | Chat and buttons create the same Project Plan, Cost Plan, sort, and consultant outputs | Artefact Revision, durable core runs, workflow adapters |
| R3 internal | UI/chat use the same grouped quote selection and atomic Tender intake | Tender selection/context/report corrections |
| R3 customer | Tender is evaluated and QS-approved | Real golden corpus, eval, fixed report language, full-pipeline gate |
| R4 | Safe row-level cost automation and approved-Tender proposal handoff | Typed Cost Plan, deterministic arithmetic, immutable handoff DTO |
| Final | Production cutover | Role fixtures, recovery/rollback, live acceptance, then Phase 8.5 deletion |

R1 and R2 do not wait for all Tender work. Each slice is additive, independently
accepted, and leaves the legacy path intact until its explicit cutover gate.

## 3. Verified baseline on 2026-07-10

Review base:

- branch: main at 6a50d961;
- substantial pre-existing uncommitted backend, frontend, landing, and asset
  work was present;
- this review did not modify implementation files;
- Phase 8 deploy scaffolding exists, but live sitewise.au acceptance and legacy
  cutover remain pending.

Verification:

- Frontend unit tests: 28 files, 92 tests passed.
- The current dirty frontend does not pass the production TypeScript build. It
  has seven contract/type errors across ChatPanel, CreateProjectPanel,
  DecisionControl, DraftReviewPanel tests, and MarkdownContent.
- A Vite-only build produced one 1,718.16 kB JavaScript file, 463.40 kB gzip,
  because all routes are eager and the Three.js demo is in the initial bundle.
- Focused backend review suite: 676 passed, 2 failed, 1 skipped in 139.61 s.
- One backend failure is a stale migration-head assertion fixed at revision 016
  while the actual head is 019.
- The marked integration migration test is destructive and ran against the
  configured database by default. It must be opt-in and isolated. A subsequent
  read-only check reported Alembic at 019_project_decisions.
- The existing flagship speed test measures ODL extraction only, not the full
  Tender Comparison pipeline.

Implemented strengths to preserve:

- per-project MCP authorization and turn tokens;
- Hermes/Pi subprocess adapters and AI-SDK-compatible SSE;
- Tender Comparison job queue, deterministic calculations, QA, matrix, report,
  and telemetry table;
- versioned draft artefacts and project decisions;
- project activity events;
- canonical Supabase source storage;
- strong upload progress UI;
- virtualized Tender Matrix;
- platform/project knowledge separation;
- Stripe entitlement and quota seam.

## 4. Target product journey

~~~mermaid
flowchart LR
    profile["Project profile + confirmed facts"] --> inputs["Shared project inputs"]
    decisions["Locked project decisions"] --> inputs
    brief["Run-specific brief"] --> inputs
    inputs --> snapshot["Project snapshot"]
    files["Canonical project files"] --> corpus["Project corpus"]
    select["Persisted quote groups"] --> tender["Tender Comparison"]
    snapshot --> pmp["Project Plan"]
    snapshot --> cost["Cost Plan"]
    snapshot --> tender
    corpus --> pmp
    corpus --> cost
    corpus --> tender
    pmp --> registry["Artefact registry"]
    cost --> registry
    tender --> registry
    tender --> proposal["Approved Tender -> proposed Cost revision"]
    proposal --> cost
    cost --> refresh["Accepted cost summary -> optional PMP refresh"]
    refresh --> pmp
    ui["React controls"] --> commands["Shared typed commands"]
    chat["Hermes MCP tools"] --> commands
    commands --> profile
    commands --> select
    commands --> runs["Durable workflow runs"]
    runs --> pmp
    runs --> cost
    runs --> tender
    commands --> outbox["Durable project-event outbox"]
    runs --> outbox
    outbox --> ui
    outbox --> chat
~~~

The graph is directional. Shared profile facts, evidence, and decisions feed
workflows. An artefact never becomes the hidden source of a shared fact. Tender
may create a proposed Cost Plan revision only after approval; an accepted cost
summary may explicitly request a Project Plan refresh. Dependency traversal
must reject cycles.

End-to-end behavior:

1. A user manually selects, or tells chat, "Residential refurbishment, Class
   1a house, NSW, architect/PM."
2. UI and chat call the same Project Profile interface. The server validates,
   versions, audits, and emits a resource-change event.
3. Controls, overlay gate, applicable platform knowledge, risk flags, workflow
   capability, and stale badges update without a page reload.
4. Files upload once to project-UUID-scoped Supabase storage. Core retrieval
   and TCM may derive their own representations, but TCM never consumes RAG
   chunks.
5. UI or chat sets one persisted Tender selection containing 2-5 ordered quote
   groups. Each quote group may contain a main quote, schedules, and addenda.
   Both surfaces see the same revision.
6. Project Plan and Cost Plan start through one durable workflow interface,
   regardless of whether the command came from a button or chat.
7. Tender Comparison derives supported context from the profile, asks only for
   missing tender-specific facts, then snapshots the exact context and files.
8. Core outputs publish through one artefact revision interface with workflow-
   specific edit and export rules. TCM owns Tender report editing and approval,
   then publishes the finished immutable revision through the core registry
   interface.
9. Approved outputs expose typed handoffs. An approved tender may offer a Cost
   Plan revision, but it never selects a builder or silently changes accepted
   work.
10. Every result records the profile, evidence, decision, and upstream
    artefact revisions used.

## 5. Required deep modules

These are deepening opportunities, not new tiers for their own sake. Each has
at least two real adapters and therefore a real seam.

### 5.1 Project Corpus module

Files involved:

- backend/app/database/source_document.py
- backend/ingest/ids.py
- backend/ingest/hosted.py
- backend/ingest/persist.py
- backend/app/retrieval/queries.py
- backend/app/retrieval/schemas.py
- project evidence, workflow retrieval, and MCP callers

Problem:

Project evidence identity and filtering use slug/path while authorization uses
project UUID. This weakens tenant locality and can collide across owners.

Solution:

Make project UUID the identity and authorization key for project evidence.
Platform knowledge remains projectless and explicitly marked platform scope.

Benefits:

- tenancy is testable at one interface;
- ingestion, retrieval, deletion, and MCP use the same project identity;
- same-owner and cross-owner slug reuse becomes harmless;
- path-derived UUID collisions disappear.

### 5.2 Project Profile module

Files involved:

- backend/app/schemas/projects.py
- backend/app/database/project.py
- backend/app/api/projects.py
- backend/app/sitewise/taxonomy.py
- backend/app/mcp_bridge/server.py
- backend/app/agent/turn_context.py
- frontend project profile/query/chat-event files

Problem:

The current PATCH interface can clear omitted fields, validates only part of
the profile, has no optimistic revision, and is inaccessible to the agent.

Solution:

One module owns read, options, merge-patch, validation, dependency clearing,
diff, revision, gate/risk derivation, audit, and change-event creation.

Benefits:

- HTTP and MCP behavior cannot drift;
- the interface is the test surface;
- class/type changes handle dependent fields deterministically;
- UI and agent concurrent edits do not silently overwrite one another.

### 5.3 Artefact Revision module

Files involved:

- backend/app/database/draft_artifacts.py
- backend/app/api/projects.py
- backend/app/mcp_bridge/server.py
- PMP, Cost Plan, consultant procurement, and Tender report publishers

Problem:

Generic MCP draft writes bypass workflow-specific synchronization. Version
allocation uses max+1 and can race. Cockpit GETs repair missing workspace
exports as a side effect.

Solution:

One revision interface reserves a version, verifies the expected base version,
applies edit policy, writes provenance, synchronizes derived outputs, updates
PMP decisions when required, records activity, and emits a resource event.

Benefits:

- database drafts, markdown exports, workbooks, and report exports agree;
- UI and agent edits have identical behavior;
- repair-on-read can be deleted;
- concurrent edits fail clearly instead of corrupting locality.

### 5.4 Workflow Run module

Files involved:

- backend/app/workflows/
- backend/app/api/projects.py
- backend/app/database/activity_events.py
- backend/app/mcp_bridge/server.py
- a new Postgres-backed core workflow queue/worker
- frontend workflow and activity queries

Problem:

Project Plan and Cost Plan are long synchronous HTTP calls and have no agent
action tools. Tender has a durable queue, but core workflows do not share its
run contract.

Solution:

One core workflow-run interface owns start, status, cancel, progress, result,
idempotency, and recovery. TCM keeps its own tender tables and worker; its
adapter projects the same external event shape without core importing tender
internals.

Benefits:

- buttons and chat have action parity;
- requests acknowledge quickly;
- restarts do not lose work;
- progress, cancellation, timing, and artefact-ready behavior are consistent.

### 5.5 Typed Cost Plan module

Files involved:

- backend/app/workflows/create_cost_plan.py
- backend/app/sitewise/cost_plan_workbook.py
- backend/app/sitewise/cost_plan_renderer.py
- new core cost-plan tables/modules
- Cost Plan UI and MCP adapters

Problem:

Cost rows and money are currently embedded in markdown and reparsed to build
the workbook. A one-row agent update would require fragile whole-document
editing.

Solution:

Make typed cost items and deterministic totals canonical. Render markdown and
XLSX from the typed state. Keep model work to classification and narrative.

Benefits:

- safe row-level automation;
- deterministic budget, commitment, forecast, paid, contingency, GST, and
  variance calculations;
- accepted Tender handoffs can update a new Cost Plan revision with exact
  provenance.

### 5.6 Project State module

Files involved:

- project profile and project decision services;
- a deterministic project snapshot reader;
- workflow capability rules;
- evidence-derived profile proposals;
- HTTP, MCP, and frontend project-state adapters.

Problem:

Facts, discretionary decisions, run instructions, readiness, and model-derived
suggestions are currently easy to conflate. That would let a model silently
turn evidence into an accepted project choice.

Solution:

Own each value explicitly:

| Value | Owner | Mutation rule |
| --- | --- | --- |
| Classification, location, scale, factual setup | Project Profile | Revisioned explicit update |
| Procurement route, delivery choices, locks | Project Decisions | Revisioned explicit decision |
| One-run instructions | Workflow Run brief | Frozen for that run only |
| Evidence-derived possible fact | Profile Proposal | Accept/reject before profile mutation |

The module also produces the minimal Project Snapshot and the shared workflow
capability result used by the UI, Hermes, PMP, Cost Plan, and Tender adapters.

Benefits:

- user intent never loses silently to document inference;
- unsupported workflows cannot be advertised or started;
- every workflow sees the same confirmed facts and locked decisions;
- run-specific instructions do not leak into permanent project state.

## 6. Non-negotiable rules for every task

- Read root AGENTS.md and the relevant backend/frontend AGENTS.md first.
- Read the July Hermes plans, the TCM PRD for tender work, and this plan.
- Preserve the locked stack.
- Do not delete legacy chat, cockpit, or Polar code before the final production
  gate.
- TCM stays in backend/tender and owns only tender tables. Core imports from
  TCM remain limited to the router mount and explicit MCP adapter wiring.
- TCM never reads Clerk RAG chunks.
- Supabase Storage is canonical for uploaded source files.
- Platform knowledge is guidance, never project evidence.
- LLMs do not perform arithmetic.
- A document-derived profile fact is a proposal until the user confirms it.
- An explicit user command may mutate a reversible profile or start a workflow.
- Tender approval, builder choice, accepted budget changes, and downstream
  handoffs require explicit user confirmation.
- Never expose a generic "update anything" agent tool.
- Do not add a runtime dependency unless the repository dependency policy is
  satisfied in the commit message.
- Every new project-owned table must define project/user FKs, indexes,
  downgrade behavior, RLS/grants consistent with existing tables, and a
  two-owner isolation test.
- Database state and Supabase Storage cannot commit atomically: commit a
  canonical row plus retryable outbox/export job, then advertise `ready` only
  after the immutable object exists.
- Use one task per branch/commit. Do not mix cleanup with behavior.
- Start each behavior task with a failing focused test.
- Do not run marked integration or tender-eval tests against the normal
  DATABASE_URL.
- Preserve unrelated dirty-worktree changes. Never reset or discard them.

## 7. Event contracts

The AI-SDK chat SSE stream exists only for one Hermes turn. Keep its fixed
vocabulary: during that turn, resource and workflow acknowledgements may travel
as `data-clerk-status` parts. Do not depend on that stream for a worker result
that may arrive after the turn has closed.

Every HTTP, MCP, or worker mutation writes a durable project event in the same
transaction as its state change, using an outbox/activity cursor. The UI reads
events after a cursor and adaptively polls active run IDs. Assistant
`message_data` stores the sanitized queued-run reference so its artefact card
can query status after reload. A separate authenticated project-event stream
may be added later, but it must not change the chat SSE contract.

Resource event:

~~~json
{
  "kind": "resource",
  "eventId": "uuid",
  "sequence": 1042,
  "createdAt": "2026-07-10T01:02:03Z",
  "projectId": "uuid",
  "resourceType": "project_profile",
  "resourceId": "uuid",
  "action": "updated",
  "revision": 4,
  "changedFields": ["building_class", "work_type"],
  "clearedFields": [],
  "route": "/projects/uuid"
}
~~~

Workflow event:

~~~json
{
  "kind": "workflow",
  "eventId": "uuid",
  "sequence": 1043,
  "createdAt": "2026-07-10T01:02:04Z",
  "projectId": "uuid",
  "workflowType": "create_cost_plan",
  "runId": "uuid",
  "state": "queued",
  "progress": 0,
  "changedResources": []
}
~~~

Terminal chat events and queued run references are persisted in assistant
`message_data` and rehydrated after a thread reload. The durable project event
record is the source of truth for cross-surface freshness. Transient
token/status text need not be persisted.

## 8. Execution order

Predecessor gates are binding, but phase numbers are not a big-bang release
train. Run the Phase 0 preflight first, complete the Project Profile/State
foundation, then use the dependency tracks in Section 10. A task may start when
its named predecessors are green; unrelated Tender work must not block Project
Plan or Cost Plan action parity.

### Phase 0 - Tenancy, safety, green baseline, and measurement

#### Task 0.0A - Repair the frontend production build

Files:

- the seven currently failing frontend/type-test files listed in the baseline;
- no backend files.

Work:

- fix the contract/type errors without casts that weaken the domain types;
- keep the current 92 frontend tests green;
- run the full TypeScript production build.

Gate:

- `pnpm test` and `pnpm build` pass from `frontend/`.

#### Task 0.0B - Guard destructive test databases

Files:

- backend/pyproject.toml;
- backend/tests/tender/test_migrations.py;
- one focused guard test.

Work:

- exclude `integration` and `tender_eval` markers from the default lane;
- require both a dedicated `TEST_DATABASE_URL` and an explicit destructive-test
  opt-in variable for migration round trips;
- refuse when the test URL equals the configured application `DATABASE_URL`;
- keep ordinary unit/contract tests database- and network-free.

Gate:

- the destructive test refuses the normal database and runs only against an
  isolated disposable database.

#### Task 0.0C - Repair migration graph verification

Files:

- backend/tests/tender/test_migrations.py;
- focused migration graph tests.

Work:

- replace the stale fixed revision 016 assertion;
- verify every Tender revision is an ancestor of the single application head;
- report branches/cycles clearly without upgrading a database.

Gate:

- the current 019 head passes and a synthetic branch fails.

#### Task 0.0D - Restore the default CI contract

Files:

- .github/workflows/ci.yml;
- data/tender/tools/validate.py wiring only where required.

Work:

- run backend offline tests/lint in shards, frontend typecheck/lint/test/build,
  migration graph checks, and Tender seed validation;
- keep integration, live-provider, destructive migration, and Tender eval lanes
  explicitly opt-in.

Gate:

- CI catches a deliberate type or migration failure and the default lane
  cannot touch a configured application database.

#### Task 0.1 - Audit project evidence identity

Goal:

Prove the scope of slug/path collisions before migrating.

Files:

- create a read-only audit command under backend/scripts/
- add focused tests for its query logic

Work:

- list SourceDocument rows linked by workspace_files to zero, one, or multiple
  distinct project UUIDs;
- list duplicate relative paths and document IDs across projects;
- distinguish project evidence from platform knowledge;
- produce counts only by default, with an explicit flag for identifiers;
- do not mutate data.

Gate:

- audit runs against a test fixture with two owners using the same slug/path;
- ambiguous rows are reported;
- no table or row changes occur.

#### Task 0.2 - Add project UUID to SourceDocument

Goal:

Create the new tenant identity without guessing ambiguous ownership.

Files:

- backend/app/database/source_document.py
- next free Alembic migration after current head
- backend/app/database/models.py if registration is needed
- migration tests

Work:

- add nullable source_documents.project_id FK to projects.id;
- backfill rows with exactly one distinct workspace_files.project_id;
- leave platform rows null;
- leave ambiguous rows untouched and report them through Task 0.1; Alembic must
  not perform destructive guessing or abort after applying partial DDL;
- add a partial unique index on `(project_id, relative_path)` where project_id
  is not null, plus project/source-type indexes;
- add the projectless platform partial uniqueness rule;
- retain the legacy global relative_path uniqueness during dual-write rollout;
- do not drop the legacy project string yet.

Gate:

- upgrade and downgrade work on an isolated disposable database;
- unambiguous project evidence is backfilled;
- platform knowledge remains null/projectless;
- ambiguous fixtures remain unchanged and are reported by the preflight.

#### Task 0.3 - Make hosted ingestion IDs project-scoped

Goal:

Prevent new project-document and chunk collisions.

Files:

- backend/ingest/ids.py
- backend/ingest/hosted.py
- backend/ingest/persist.py
- backend/app/inbox/service.py
- affected ingest tests

Work:

- pass project_id through hosted ingestion;
- derive IDs from project UUID plus normalized relative path only for newly
  inserted project documents;
- use `INSERT ... ON CONFLICT ... RETURNING source_documents.id` and derive
  chunk IDs from the returned persisted ID;
- persist SourceDocument.project_id;
- keep platform seed IDs stable using an explicit platform scope value;
- change upsert conflict keys to project_id plus relative_path for project
  evidence;
- never rewrite an existing document/chunk primary key merely because its ID
  recipe changed; preserve historical citations and delete only stale chunks
  belonging to that returned document during re-ingest.

Gate:

- a new path is project-scoped and an old pre-migration row keeps its ID;
- re-ingesting the same project/path remains idempotent;
- old citations still resolve and stale chunks are cleaned up;
- platform seed idempotency remains green.

#### Task 0.4 - Contract legacy evidence identity and repair data

Implementation note (2026-07-19): migration
`021b_source_doc_path_contract` performs the planned global-to-project path
uniqueness cutover between the additive 021 expand migration and the 022
ownership constraints. This preserves the dual-write rollout boundary while
allowing the repair command to create project-scoped copies.

Prerequisites:

- Tasks 0.1-0.3 are green;
- dual-write application code is deployed before the contract migration.

Work:

- add an idempotent repair command with separate `--dry-run` and explicit
  `--apply` modes for ambiguous legacy rows;
- remove global relative_path uniqueness, leaving the project and platform
  partial unique indexes from Task 0.2 in force;
- when one legacy SourceDocument was shared, explicitly split its document and
  chunks per owning project, repoint workspace_files, and reconcile citations
  by the owning thread/project; never quarantine or delete by default;
- use `INSERT ... RETURNING` in the repair and retain historical IDs wherever
  the row was not actually shared;
- refuse the read cutover while any ambiguous ownership remains;
- enforce project evidence => non-null project_id and platform knowledge =>
  null project_id plus `knowledge_scope=platform`;
- define and test the SourceDocument project FK `ON DELETE` behavior;
- document that downgrade to global uniqueness is preconditioned on removing
  cross-project duplicate paths; application rollback must tolerate the
  expanded schema.

Gate:

- the audit has no unresolved ambiguous project-evidence rows;
- duplicate paths across projects are allowed and have different persisted IDs;
- duplicate paths within one project are rejected;
- old citations still resolve to the owning project's evidence;
- production migration runbook includes backup and realistic rollback steps.

#### Task 0.5 - Switch retrieval and evidence operations to project UUID

Goal:

Make UUID tenancy the only authorization filter for project evidence after the
data gate in Task 0.4 is clean.

Files:

- backend/app/retrieval/schemas.py
- backend/app/retrieval/queries.py
- backend/app/retrieval/retriever.py
- backend/app/evidence/service.py
- PMP/Cost Plan/legacy chat/MCP retrieval callers
- retrieval, workflow, and MCP tests

Split into three assignable packets, each leaving tests green:

- 0.5A: retrieval schemas, queries, and retriever;
- 0.5B: evidence, legacy chat, and MCP callers;
- 0.5C: PMP and Cost Plan workflow callers.

Work:

- replace active_project/project slug filters with active_project_id/project_id;
- include platform knowledge only through explicit platform-scope conditions;
- keep slug/title only as display metadata;
- update all authorized callers to pass the owned project UUID;
- add two-owner/same-slug tests for search, get_document,
  find_document_text, PMP retrieval, and Cost Plan retrieval.

Gate:

- all cross-project reads are rejected or empty;
- same-slug owners retrieve only their own content;
- platform guidance remains readable when explicitly included;
- no project authorization decision depends on slug.

#### Task 0.7A - Terminate the complete agent process tree

Files:

- backend/app/agent/hermes_process.py;
- backend/app/agent/pi_process.py;
- backend/app/agent/concurrency.py;
- focused subprocess tests.

Work:

- start each runtime in an isolated process group;
- on disconnect, cancellation, or timeout, signal the group, allow a bounded
  grace period, then force-kill and await it before propagating;
- cover the platform-specific Linux deployment path and Windows development
  adapter without adding a helper dependency.

Gate:

- zero direct or descendant processes remain after stop, disconnect, timeout,
  or cancellation.

#### Task 0.7B - Verify and select a Hermes prompt transport

This is a bounded compatibility decision, not an implementation guess.

Work:

- test installed Hermes headless modes for stdin, prompt-file reference, and
  verified server/session input without placing prompt text in argv;
- record the exact supported command, cleanup behavior, multiline limit, and
  failure behavior under docs/performance/;
- do not change production invocation in this packet.

Gate:

- one mechanism is proven by an automated smoke test, or agent mutation rollout
  remains blocked with an upstream Hermes issue linked in the decision record.

#### Task 0.7C - Move Hermes prompts off argv

Files:

- backend/app/agent/hermes_process.py;
- backend/tests/agent/test_hermes_process.py.

Work:

- implement only the mechanism selected by Task 0.7B;
- clean temporary material in `finally` and never log prompt content;
- preserve streaming, provider/model selection, and both configured invocation
  modes.

Gate:

- full prompt text is absent from process argv and temporary material is gone
  after success, spawn failure, cancellation, and timeout.

#### Task 0.7D - Make mutation turn revocation durable

Files:

- backend/app/mcp_bridge/tokens.py and auth.py;
- a new core agent-turn capability model/migration;
- agent/MCP authorization tests.

Work:

- persist turn_id, project_id, user_id, state, expiry, and revocation time in
  Postgres; never store the bearer token;
- scope idempotency and indexes to the owning project/user and apply the same
  tenancy/grant policy as other project-owned core tables;
- serialize revocation and mutation commit with the same Postgres transaction
  advisory lock keyed by turn_id; under that lock, mutation re-reads active
  state immediately before commit, while cancellation marks revoked;
- on cancellation, revoke first, then terminate the process tree;
- define the guarantee as no mutation starts or commits after revocation;
- shorten JWT TTL to bounded turn duration plus grace and fail startup when
  mutation is enabled with a blank or weak signing secret.

Gate:

- a cancel-versus-mutation race test proves no post-revocation commit;
- API worker restart does not reactivate a revoked turn;
- existing read-tool authorization remains green.

#### Task 0.8 - Add timing baselines

Goal:

Measure before optimizing.

Split into independent packets:

- 0.8A: add request/project/thread/turn correlation and agent timing;
- 0.8B: add workflow stage timing once workflow runs exist; until then define
  the fields and instrument the existing synchronous paths;
- 0.8C: add a dependency-free, report-only frontend build-size script.

Work:

- record auth, entitlement/quota, prompt build, spawn, first byte, first text,
  each MCP tool, persistence, and total turn time;
- add real event timestamps/durations to workflow activity;
- remove duplicate unstructured request printing once structured logs cover it;
- report the current 463.40 kB gzip initial bundle without failing at 250 kB;
  Task 5.1 enables the hard budget after the build is green.

Gate:

- one agent turn can be traced end-to-end by IDs;
- timing values are numerical and tested;
- no sensitive prompt/tool content is logged;
- baseline report is committed under docs/performance/.

#### Task 0.9 - Make agent quota accounting runtime-neutral and race-safe

Files:

- backend/app/billing/usage.py;
- backend/app/api/chat.py;
- backend/app/agent/agent_runtimes.py;
- a core agent_turn_usage model/migration if an atomic reservation cannot be
  represented by an existing table;
- focused Hermes/Pi/concurrency tests.

Work:

- remove the current Hermes-only usage predicate so Pi cannot bypass quota;
- reserve one chargeable turn atomically when provider/runtime invocation
  starts, keyed by user plus user-message/turn ID;
- preflight/auth/needs-input failures before invocation do not consume a turn;
- retries of the same turn do not double-count; simultaneous turns cannot both
  pass the last remaining quota slot;
- record runtime/model/status and later token/cost fields without storing prompt
  content;
- apply project/user FKs, indexes, RLS/grants, downgrade, and two-user tests to
  any new table.

Gate:

- equal Hermes and Pi turns change used_turns equally;
- a two-request race at one remaining turn admits exactly one;
- cancellation/retry policy is explicit and tested.

### Phase 1 - Shared Project State and agent-controlled Project Profile

#### Task 1.1 - Add profile revision and typed contracts

Files:

- backend/app/database/project.py
- next free Alembic migration
- backend/app/schemas/projects.py
- project schema/migration tests

Work:

- add profile_revision integer, default 1, non-null;
- define ProjectProfileView, ProjectProfilePatch, and ProjectProfileChange;
- distinguish omitted fields from explicit null using model_fields_set or an
  explicit changes object;
- require expected_revision for updates;
- make `ProjectProfileChange` the only PATCH success response. It contains the
  complete `profile: ProjectProfileView`, previous/new revisions,
  changed_fields, cleared_fields, overlay status, and risk flags.

Gate:

- omitted values are not cleared;
- explicit clear is distinguishable;
- stale expected_revision returns 409;
- revision increments exactly once per effective change and not for a no-op.

#### Task 1.2 - Build the deep Project Profile module

Create:

- backend/app/projects/__init__.py
- backend/app/projects/profile.py

Interface:

- read_profile
- profile_options
- validate_profile_patch
- apply_profile_patch

Work:

- validate class/work-type/subclass combinations;
- validate scale keys, scalar types, and configured min/max;
- validate complexity keys/options for the selected class/subclasses;
- validate work-scope items for the selected work type;
- validate user role and state from the backend source of truth;
- compute overlay gate and risk flags;
- when class/type changes conflict with dependent fields, reject with a typed
  conflict list unless clear_incompatible=true;
- when clearing is explicitly allowed, return every cleared field;
- record one activity run containing before/after diff and actor source;
- do not put customer data into logs.

Gate:

- module tests cover every validation family, no-op, explicit clear,
  incompatible reset, stale revision, and concurrent updates;
- deletion test: removing this module would force validation/diff/revision
  logic back into both HTTP and MCP adapters.

#### Task 1.3 - Make HTTP PATCH a thin adapter

Files:

- backend/app/api/projects.py
- backend/tests/test_project_taxonomy_api.py

Work:

- delegate the existing project PATCH to Project Profile;
- do not duplicate validation in the route;
- preserve auth and entitlement checks;
- return `ProjectProfileChange`; do not preserve a second success shape.

Gate:

- updating only role preserves class, work type, subclasses, scale,
  complexity, and work scope;
- manual UI behavior remains green;
- route and module error codes are stable and documented.

#### Task 1.4 - Add the durable Project Event outbox

Create:

- backend/app/database/project_event.py and the next free migration;
- backend/app/projects/events.py;
- backend/app/schemas/project_events.py;
- `publish_project_event` called inside the mutation transaction;
- `GET /api/projects/{project_id}/events?after={sequence}&limit={n}`.

Required fields:

- event UUID, monotonically increasing sequence, schema version, project UUID;
- actor/source, resource type/ID/revision, action, safe payload, created_at;
- stable deduplication key when the producer may retry.

Rules:

- HTTP, MCP, core workers, and TCM's external projection adapter publish through
  this interface;
- authorization filters by owned project UUID before cursor reads;
- consumers persist the last sequence and tolerate duplicate delivery;
- retention cannot delete events still needed by an active run/card;
- use adaptive authenticated polling initially; a dedicated project SSE feed is
  a later measured enhancement, not part of chat SSE.

Gate:

- mutation plus event commit atomically, or neither does;
- replay after a cursor is ordered and tenant-isolated;
- two producers with the same deduplication key create one logical event;
- worker completion is observable after the originating chat stream closes.

#### Task 1.5 - Bind mutation intent and persist profile proposals

Create:

- backend/app/agent/mutation_intent.py;
- backend/app/database/project_profile_proposal.py plus migration;
- backend/app/projects/profile_proposals.py;
- project_profile_proposals with current/proposed values, profile revision,
  evidence references, confidence, state, proposer, and timestamps;
- accept/reject services with optimistic revision checks.

Rules:

- the chat boundary stores the current user-message hash and grants a narrow
  `profile_mutation` turn scope only for an explicit imperative such as
  set/change/update/save plus target values;
- quoted document text, retrieval output, system text, and model inference
  cannot grant that scope;
- an ambiguous message gets a proposal/confirmation response;
- evidence-derived facts always use `propose_project_profile_change` and never
  mutate the profile directly;
- accepting a proposal revalidates against the current profile revision.

Gate:

- direct "set this to residential refurbishment" grants the narrow scope;
- "the report says this may be residential" does not;
- accepted/rejected proposals survive reload with evidence links;
- profile changes between proposal and acceptance produce a typed conflict.

#### Task 1.6 - Add profile MCP adapters

Files:

- backend/app/mcp_bridge/server.py initially
- split registrations only after the shared module exists
- backend/app/agent/turn_context.py
- backend/app/agent/workspace_instructions.py
- MCP tests

Tools:

- get_project_profile
- get_project_profile_options
- propose_project_profile_change
- accept_project_profile_proposal
- reject_project_profile_proposal
- update_project_profile

Policy:

- direct updates require the server-minted `profile_mutation` turn scope from
  Task 1.5; prompt wording alone is not authorization;
- facts inferred from a document or casual statement use a persisted proposal;
- update requires expected_revision;
- cross-project tokens fail before any data is returned;
- success publishes a Project Profile resource event.

Gate:

- blank project plus "make this a residential refurbishment in NSW; I am the
  architect PM" becomes ready and persists;
- the next prompt contains the updated values;
- invalid values and stale revisions are rejected;
- unrelated fields survive;
- document-derived classification alone causes no mutation.

#### Task 1.7 - Make Project Decisions a shared revisioned interface

Files:

- backend/app/database/project_decision.py;
- backend/app/database/project_decisions.py;
- backend/app/sitewise/pmp_decisions.py;
- backend/app/projects/decisions.py as the single shared module;
- backend/app/mcp_bridge/server.py adapters;
- focused module/HTTP/MCP tests.

Ownership:

- Project Profile owns confirmed factual classification/setup;
- Project Decisions owns procurement route, delivery choices, evidence
  conflicts, acceptance state, and user locks;
- Workflow Run brief owns instructions that apply to one run only.

Interface/tools:

- list_project_decisions;
- get_project_decision;
- update_project_decision with expected decision/set revision;
- lock_project_decision and unlock_project_decision.

Work:

- deepen the existing project_decisions model/service instead of duplicating
  it;
- preserve PMP's user-locked decisions across regeneration;
- publish decision resource events and actor/provenance;
- block document/model inference from overwriting a locked decision.

Gate:

- UI and MCP see the same values and revision;
- a stale update conflicts;
- locked procurement route survives PMP refresh;
- a conflicting new source is surfaced, not silently accepted.

#### Task 1.8 - Build the minimal deterministic Project Snapshot

Interface:

- `get_project_snapshot(project_id)`.

Snapshot v1 contains:

- project identity, site/address/client fields already stored;
- profile and revision;
- decision set/revision and locks;
- evidence fingerprint, active count, and ingest failures;
- budget/timeframe/procurement inputs where confirmed;
- open profile proposals;
- schema version and generated_at.

Rules:

- missing inputs remain explicit `needs_input` values;
- `turn_context`, PMP, Cost Plan, capability, and Tender preparation use this
  reader instead of assembling divergent dictionaries;
- do not read TCM tables. TCM later publishes a generic projection through a
  core interface.

Gate:

- identical state produces the same content fingerprint;
- snapshot queries are tenant-isolated and bounded;
- agent and manual workflow preparation receive the same snapshot version.

#### Task 1.9 - Publish the workflow capability matrix

Interface:

- `workflow_capabilities(snapshot)` returns for each workflow `supported`,
  `needs_input`, or `unsupported`, with reasons and required fields.

Initial truth:

- Project Plan supports the broad taxonomy matrix;
- Tender Comparison supports only the TCM PRD's Class 1 residential work in
  NSW/VIC/QLD and supported work types;
- Cost Plan knowledge is materially narrower and must not imply equal
  confidence across all six classes;
- consultant actions advertise only when their required role/context exists.

Gate:

- UI tiles, Hermes instructions, preparation endpoints, and workflow starts use
  the same result;
- unsupported or incomplete workflows cannot enqueue;
- no general model knowledge upgrades an unsupported capability.

#### Task 1.10A - Reconcile project queries and events

Files:

- frontend/src/lib/queries/project-data.ts
- frontend/src/lib/chat-events.ts
- frontend/src/pages/ProjectCockpitPage.tsx
- frontend/src/components/project/ProjectControlBoard.tsx
- focused frontend tests

Work:

- put project detail/profile in TanStack Query;
- apply HTTP responses/chat resource parts to the exact query key;
- poll the durable project-event cursor adaptively while the cockpit is visible
  or runs are active, pause when hidden, and deduplicate by event ID/sequence;
- otherwise refresh only resources named by the event.

Gate:

- same-tab agent/manual commit reaches controls p95 within 500 ms; a separate
  open tab converges within 2 s through the event cursor;
- no full page reload;
- cursor replay after reload does not duplicate toasts or cards.

#### Task 1.10B - Protect dirty profile forms

Files:

- frontend/src/components/project/ProjectControlBoard.tsx;
- focused component tests.

Work:

- keep local state only for unsaved edits;
- sync clean controls when a newer server revision arrives;
- while dirty, show a conflict banner with reload/keep-editing actions and never
  silently overwrite either side.

Gate:

- clean forms update immediately and dirty forms preserve typed values until
  the user chooses.

#### Task 1.10C - Isolate chat failure from the project shell

Files:

- frontend/src/components/chat/ChatPanel.tsx;
- frontend/src/pages/ProjectCockpitPage.tsx;
- focused failure tests.

Gate:

- thread/message/runtime failures render inside the chat pane while profile,
  repository, workflows, and navigation remain usable.

Release gate R1:

- tenant-safe evidence Tasks 0.1-0.5 and Phase 1 gates are green;
- users may receive agent-controlled Profile/Decisions/Snapshot/Capability as
  an additive slice;
- no Project Plan/Cost Plan/Tender mutation tool is enabled before its own
  workflow/quality predecessor.

### Phase 2 - Shared document selection and correct Tender context

#### Task 2.1 - Persist purpose-scoped document selections

Files:

- backend/app/database/project_document_selection.py;
- backend/app/projects/document_selections.py;
- backend/app/schemas/document_selections.py;
- next free core migration;
- focused model/module/tenancy tests.

Create core tables/modules for:

- project_document_selections
- project_document_selection_revisions
- project_document_selection_groups
- project_document_selection_items

Required fields:

- selection and immutable selection-revision ids;
- project id;
- purpose, initially tender_comparison;
- revision;
- selected_by;
- ordered groups, each with a label/builder name;
- ordered workspace_file ids within each group;
- created/updated timestamps.

Interface:

- read_selection returns an exact immutable revision;
- replace_selection creates a new revision with expected revision;
- clear_selection creates an empty revision where the purpose permits it.

Tender adapter DTO:

~~~text
quote_candidate {
  builder_name,
  ordered_workspace_file_ids[]
}
~~~

Rules:

- enforce 2-5 quote groups, not 2-5 files;
- one quote group may contain the main quote, schedules, and addenda;
- every new project-owned table has project/user FKs, indexes, reviewed
  downgrade/RLS/grants, and two-owner isolation tests;
- source deletion is refused while a generic workflow-input retention lock from
  an active or approved comparison depends on that file.

Gate:

- every selected workspace file belongs to the project;
- revision and optimistic concurrency work;
- 2-5 quote groups are enforced and each has at least one file;
- reading an old revision reconstructs the same group/file ordering;
- source deletion never silently changes a running or historical comparison.

#### Task 2.2A - Add Tender selection HTTP and MCP adapters

Files:

- backend/app/api/projects.py;
- backend/app/mcp_bridge/server.py;
- backend tests for project selection HTTP/MCP adapters.

Work:

- expose read/replace of ordered quote groups with expected revision;
- replace heuristic `list_selected_documents` with exact Tender quote groups;
- rename the old heuristic behavior to find_candidate_tender_documents;
- add narrow tools `get_tender_quote_selection` and
  `replace_tender_quote_selection`; do not add a generic selection mutator.

Gate:

- HTTP and MCP return the same immutable revision/DTO;
- cross-project file IDs fail before any selection detail is returned.

#### Task 2.2B - Add explicit quote-group selection UI

Files:

- frontend/src/components/project/DocumentRepositoryPanel.tsx;
- frontend/src/pages/ProjectCockpitPage.tsx;
- frontend Tender intake/query files;
- focused frontend tests.

Work:

- separate preview-row selection from purpose assignment;
- let the user create/reorder 2-5 builder groups and order files inside each;
- label builder/group, file count, selection revision, and validation errors;
- persist through the shared selection interface.

Gate:

- selection survives reload;
- UI and agent list the same ordered groups/files/revision;
- manual and agent starts consume the same selection;
- no path-string-only authorization.

#### Task 2.3 - Build the TCM-owned project-context adapter

Create:

- backend/tender/services/project_context_adapter.py

Mapping:

- new to new_build;
- refurb to renovation;
- extend to addition;
- supported Class 1a residential subclasses only;
- state limited to NSW, VIC, or QLD;
- map scale.storeys and scale.gfa_sqm where present;
- map other fields only when semantics are exact.

Return:

- supported boolean;
- prepared strict ProjectContext;
- missing tender-only fields;
- unsupported reasons;

Provenance returned beside, not inside, strict `ProjectContext`:

- source profile/snapshot revision;
- source selection revision;
- ordered quote/file identities.

Rules:

- remediation, advisory, commercial, non-Class-1a, and unsupported states
  block clearly;
- never silently replace missing tender-only facts with confident defaults;
- validate every override through ProjectContext.model_validate;
- keep provenance outside the PRD's strict ProjectContext schema;
- inject the core snapshot/selection readers into this TCM adapter at the
  composition boundary. Core must not import this TCM implementation.

Gate:

- Residential/refurbishment/NSW/two-storey maps to
  renovation/NSW/storeys=2;
- commercial and unsupported work types block;
- context records source profile and selection revisions;
- TCM boundary rules remain intact.

#### Task 2.4A - Add a read-only Tender preparation contract

Files:

- backend/tender/router.py
- backend/tender/schemas.py
- backend/tender/services/project_context_adapter.py
- focused backend tests.

Work:

- add a prepare endpoint that returns readiness/missing fields without writes;
- lock or re-read the requested profile/selection revisions before returning;
- return strict ProjectContext plus separate provenance;
- use explicit builder names from quote groups and expose every missing or
  unsupported reason.

Gate:

- preparation performs no write and never returns silent blank state/build type;
- a concurrent profile/selection change yields a typed revision conflict.

#### Task 2.4B - Implement atomic immutable Tender intake

Files:

- backend/tender/router.py;
- backend/tender/schemas.py;
- new/changed TCM intake service;
- focused transaction/idempotency tests.

Work:

- add one transaction for comparison, 2-5 quotes, quote documents, provenance,
  and first job;
- lock and revalidate profile/selection revisions inside that transaction;
- snapshot for every file its workspace_file_id, content hash, canonical storage
  key/version identity, order, and quote group;
- derive idempotency from project, workflow type, turn_id, and canonical input;
- reject reuse of a key with different input;
- on validation failure create no comparison/quote/document/job graph;
- publish generic file-retention locks through a core interface;
- explicitly supersede Hermes Foundation Phase 0-2 Task 14's partial-quote
  creation contract; update its tests/instructions in this same change.

Gate:

- no comparison starts with silent blank state/build type;
- a failed batch leaves no partial rows/jobs;
- retrying the same agent tool call returns the original result;
- historical/running input remains reconstructible after selection edits.

#### Task 2.4C - Cut HTTP, MCP, and UI over to atomic intake

Files:

- backend/app/mcp_bridge/server.py;
- frontend/src/components/project/tender/TenderQuoteSelectionPanel.tsx;
- frontend/src/components/project/tender/TenderIntakePanel.tsx;
- related backend/frontend tests.

Work:

- replace raw context-dict acceptance in `start_tender_comparison`;
- make manual and agent starts use the same prepare/intake contracts;
- merge or remove the dormant duplicate intake form only after the new path is
  green.

Gate:

- UI and MCP produce equivalent comparisons from the same immutable selection;
- the prior partial intake path is unreachable and its contradictory tests are
  removed or rewritten.

#### Task 2.5 - Fix comparison-scoped report state

Files:

- backend/tender/report service/router
- frontend/src/components/project/tender/TenderReportPanel.tsx
- frontend/src/lib/queries/tender.ts (create if absent)
- tests with at least two comparisons

Work:

- add GET /api/tender/comparisons/{id}/report returning the exact report
  lifecycle and draft;
- key client state by comparison id;
- load existing HTML/PDF/status on mount;
- never use the latest project-wide tender_report to infer a comparison report.

Gate:

- routes for two comparisons always show their own draft, status, HTML, and
  PDF;
- switching tabs uses cached comparison-scoped data.

### Phase 3 - Artefact revision and durable agent events

#### Task 3.1 - Make draft version allocation concurrency-safe

Goal:

Reserve monotonically increasing versions atomically per
project/workflow_type.

Files:

- backend/app/database/draft_artifact.py;
- backend/app/database/draft_artifacts.py;
- backend/app/projects/artefact_revisions.py;
- focused concurrent transaction tests.

Work:

- take a Postgres transaction advisory lock keyed by project UUID plus
  workflow type before reading/reserving max+1;
- require expected_base_version for edits;
- test two concurrent revisions;
- retain unique constraints as a final guard.

Gate:

- concurrent edits produce unique ordered versions or one explicit conflict;
- no unhandled IntegrityError reaches users.

#### Task 3.2A - Build the core Artefact Revision interface

Interface:

- publish
- revise
- list
- get
- regenerate_exports
- mark_stale

Rules:

- core owns only generic revision storage, provenance, stale state, export job
  state, and project events;
- a canonical revision and export/outbox job commit in one DB transaction;
- Supabase Storage upload runs after commit and sets `pending`, `ready`, or
  `failed`; retain the prior ready export on failure and retry idempotently;
- expected base version and Task 3.1 allocation are mandatory;
- every new table has project/user FKs, indexes, reviewed downgrade/RLS/grants,
  and two-owner tests;
- export failures are never repaired during GET.

Gate:

- concurrent publish/revise is safe;
- an export failure leaves the canonical revision visible as failed/pending and
  the previous ready export usable;
- retry does not create a duplicate revision or storage object.

#### Task 3.2B - Add the Project Plan revision adapter

Work:

- route PMP publish/revise through Artefact Revision;
- expose `accept_project_plan_revision` with expected version and PMP policy;
- synchronize project decisions through the Project Decisions module;
- enqueue markdown export and publish exact revision/provenance events.

Gate:

- HTTP and MCP edits produce equivalent PMP revision/decision/export state;
- locked decisions cannot be overwritten by regeneration.

#### Task 3.2C - Add the current Cost Plan revision adapter

Work:

- route current markdown Cost Plan publication through Artefact Revision;
- expose `accept_cost_plan_revision` with expected version and Cost policy;
- regenerate markdown/workbook from the same accepted revision until the typed
  Cost Plan replaces this adapter in Phase 7.

Gate:

- DB revision, markdown, workbook, and provenance identify the same version.

#### Task 3.2D - Add the consultant artefact revision adapter

Work:

- route consultant procurement artefacts through core revision/export policy;
- expose only the consultant-specific acceptance transition;
- preserve current approval and access behavior.

Gate:

- the same consultant edit through UI/MCP produces one equivalent revision and
  exact export event.

#### Task 3.2E - Add the TCM-owned Tender publication adapter

Boundary:

- define `TenderArtefactPublisher` as a Protocol owned by `backend/tender/`;
- TCM owns narrative-only edits, structured-table regeneration, report-language
  lookup, mandatory QA/QS/operator approval, and HTML/PDF freezing;
- inject a core registry implementation from an explicit composition adapter;
  TCM does not import a core service and core does not query/import TCM tables;
- generic Artefact Revision has no authority to approve a Tender report.

Approval requirements:

- no mandatory item remains `needs_review`;
- the QS gate and operator permission pass;
- report phrases come from `data/tender/report_language.yaml`;
- immutable HTML and PDF objects are both ready;
- TCM freezes the version and records approved_by/approved_at before publishing
  the immutable approved projection to core.

Gate:

- structured Tender tables cannot be hand-edited;
- core cannot transition a Tender report to approved;
- no approved event is emitted while HTML/PDF is pending or failed.

#### Task 3.3 - Route all existing edit paths through Artefact Revision

Files:

- backend/app/api/projects.py
- backend/app/mcp_bridge/server.py write_workspace_file path
- workflow publishers
- DraftReviewPanel and decision APIs as required

Gate:

- generic scratch files still use scratch workspace writes;
- any draft artefact path uses Artefact Revision;
- every accept path uses its workflow-specific transition;
- no adapter independently chooses versions or export behavior.

#### Task 3.4A - Persist and rehydrate agent result references

Files:

- backend/app/api/chat.py
- frontend/src/lib/chat-ui.ts
- frontend/src/lib/chat-events.ts
- frontend/src/components/chat/ArtefactCard.tsx
- tests

Work:

- persist sanitized ordered terminal chat events plus durable project event,
  run, resource, and artefact references;
- rebuild AI-SDK data parts on thread load;
- make every run card query its runId after reload and adaptively poll only
  while non-terminal.

Gate:

- run an artefact-producing action, reload the task, and see the same terminal
  chips/card/link;
- no token/key/raw prompt is persisted in events;
- a worker completion appears even though the original chat SSE is closed.

#### Task 3.4B - Make artefact navigation exact and durable

Files:

- frontend/src/components/chat/ArtefactCard.tsx;
- project/tender route state and focused navigation tests.

Work:

- link cards to exact project/resource/version URLs;
- use URL state as the current workspace/view, not page-local state alone.

Gate:

- opening or reloading a card route selects the exact comparison/artefact
  version and never a project-wide latest report.

#### Task 3.5 - Remove repair writes from cockpit GETs

Work:

- create an explicit one-time backfill command for missing workspace exports;
- prove every publish/revise adapter creates its expected workspace entries;
- remove _ensure_pmp_workspace_file, _ensure_cost_plan_workspace_file, and
  consultant repair behavior from cockpit-bootstrap/workspace-tree GET paths;
- add a test that these GETs perform no storage upload or data mutation.

Gate:

- warm cockpit bootstrap has zero writes/storage calls;
- all existing artefacts are repaired by the explicit command before removal;
- fresh mutations maintain the invariant without GET repair.

### Phase 4 - Durable Project Plan and Cost Plan actions

#### Task 4.1 - Add core workflow-run persistence

Files:

- backend/app/database/workflow_run.py;
- backend/app/workflows/runs.py;
- next free core migration and focused model/claim tests.

Create a core workflow_runs/job model with:

- run id;
- project id;
- requested by user/thread/turn;
- workflow type;
- typed run brief;
- idempotency key;
- schema version and canonical request hash;
- frozen profile/snapshot revision, evidence fingerprint, decision set/version,
  and relevant selection/artefact versions;
- queued/running/needs_input/complete/failed/cancelled state;
- attempt, capped-attempts, lock owner, lease expiry/heartbeat, backoff/run-after;
- result artefact/ref;
- error class/message;
- timestamps.

Do not use tender_jobs for core workflows and do not move TCM out of its
module.

Rules:

- retries use the frozen input snapshot, never mutable current project state;
- idempotency is unique on `(project_id, workflow_type, idempotency_key)`;
- reuse with a different canonical request hash is a conflict;
- migration includes project/user FKs, indexes, reviewed downgrade/RLS/grants,
  and two-owner isolation tests.

Gate:

- SKIP LOCKED claim is safe with two workers;
- duplicate matching idempotency keys return the original run; mismatched input
  fails explicitly;
- abandoned locks are recoverable;
- migrations have real downgrade behavior.

#### Task 4.2A - Build the core workflow worker infrastructure

Files:

- backend/app/workflows/worker.py;
- backend/app/workflows/runs.py;
- focused claim/retry/cancel tests.

Work:

- claim with SKIP LOCKED, heartbeat leases, apply capped exponential backoff,
  and recover expired leases;
- record real stage progress/durations and durable project events;
- pass typed frozen run briefs, not arbitrary chat history;
- make cancellation cooperative between stages;
- leave the prior accepted artefact untouched on failure.

Gate:

- API restart does not lose a run;
- worker crash/retry is idempotent;
- cancel reaches a terminal state and no later artefact is published.

#### Task 4.2B - Add Project Plan worker adapters and acceptance

Adapters:

- create_project_plan delegates to run_create_pmp_workflow;
- refresh_project_plan delegates to run_update_pmp_workflow;

Required PMP acceptance before enabling agent refresh:

- zero-document scaffold;
- active-corpus refresh;
- deleted/superseded evidence downgrade;
- locked decisions survive regeneration and conflicts are surfaced;
- evidence-status labels and 2-4-page adaptive output;
- all fixtures in docs/pmp2.0/pmp2-acceptance.md.

Gate:

- both create/refresh delegate correctly and every canonical PMP acceptance
  fixture passes before broad agent rollout.

#### Task 4.2C - Add the Cost Plan creation worker adapter

Adapter:

- create_cost_plan delegates to run_create_cost_plan_workflow.

Rules:

- publish through Task 3.2C and retain the prior accepted version on failure;
- do not advertise refresh/update until typed Cost Plan state exists in Phase 7.

Gate:

- queued creation produces matching canonical draft, markdown, workbook,
  provenance, and terminal event.

#### Task 4.2D - Add file-sort and consultant action adapters

Work:

- make `sort_project_files` delegate to run_sort_files_workflow;
- inventory forecast/apply/draft consultant actions already exposed through MCP;
- queue any action that invokes retrieval/model/rendering long enough to exceed
  an ordinary request; keep fast deterministic updates synchronous;
- route consultant artefacts through Task 3.2D and decisions through Task 1.7.

Gate:

- UI and chat call the same typed service for sort, consultant fee apply, and
  consultant procurement draft;
- long actions survive request/agent timeout.

#### Task 4.2E - Deploy the core worker

Files:

- Docker/Dokploy service configuration;
- worker startup/health documentation and tests.

Work:

- add a separate production worker service;
- permit an explicitly gated in-process adapter only for local development.

Gate:

- health, graceful shutdown, lease recovery, and one-worker rollback are
  exercised on the deployment fixture.

#### Task 4.3A - Add asynchronous HTTP workflow endpoints additively

Work:

- add typed start/status/cancel/result endpoints without removing current
  synchronous routes;
- return `202` plus WorkflowRunView for queued starts;
- require expected input revisions/capability and use Task 4.1 idempotency.

Gate:

- existing frontend remains green before cutover;
- queued acknowledgement is p95 at most 500 ms in the performance harness.

#### Task 4.3B - Add narrow MCP workflow adapters

MCP tools and HTTP endpoints call the same start/status/cancel/result interface.

Explicit MCP tools:

- start_project_plan
- refresh_project_plan
- start_cost_plan
- sort_project_files
- start_consultant_procurement
- get_project_workflow_status
- get_project_workflow_result
- cancel_project_workflow

Do not build one generic execute_workflow tool.

Gate:

- "Create a cost plan" and the Cost Plan button produce equivalent run,
  artefact, provenance, activity, markdown, and workbook;
- repeat for Project Plan;
- project-decision reads/updates and consultant actions use their shared
  modules, not direct draft/table writes;
- tool authorization and idempotency are covered;
- agent timeout is not the workflow timeout.

#### Task 4.4A - Cut the UI over to asynchronous workflow state

Work:

- move workflow/draft/activity state to shared TanStack queries;
- apply immediate responses/chat parts optimistically and durable event-cursor
  updates as the cross-turn/cross-tab source;
- poll activity adaptively only while a run is non-terminal;
- keep stale data visible while revalidating;
- do not block the cockpit behind chat state.

Gate:

- nav badge, activity, workspace tree, draft list, and artefact card update
  without manual refresh;
- cached workflow tab navigation is under 100 ms on the test device;
- a failed workflow has a readable retry path.

#### Task 4.4B - Retire superseded synchronous workflow routes

Only after Task 4.4A and browser acceptance are green:

- remove or reduce the old synchronous start paths;
- update all callers and contract tests in the same change;
- retain no compatibility shim without an explicitly named external consumer.

Gate:

- route search finds no cockpit/MCP caller using the superseded path;
- rollback uses the previous deployment, not dual permanent implementations.

#### Task 4.5 - End-to-end action parity gate

Script:

1. create an incomplete project;
2. update its profile through chat;
3. create a Project Plan through chat;
4. edit it in the UI;
5. read the new revision through chat;
6. refresh the Project Plan and preserve locked decisions;
7. create a Cost Plan by button;
8. read the Cost Plan through chat and verify workbook consistency;
9. draft a consultant procurement artefact through chat;
10. cancel one run and prove no orphan process/job.

Gate:

- all checks pass on Linux/WSL and in a browser;
- the script records run IDs, artefact versions, timing, and screenshots.

Release gate R2:

- Profile/Snapshot/Capability may ship additively after Phase 1 acceptance;
- Project Plan, Cost Plan create, sort, and consultant actions may ship after
  their Phase 3/4 adapters and role acceptance pass;
- legacy paths remain available only until their explicit additive cutover;
- no release gate authorizes Phase 8.5 legacy deletion.

### Phase 5 - Read-path, frontend, retrieval, and runtime speed

#### Task 5.1 - Route-level code splitting and bundle budgets

Files:

- frontend/src/App.tsx
- top-level pages/routes
- a dependency-free build budget script

Work:

- lazy-load all non-initial routes;
- isolate StyleGenome/Three.js completely;
- lazy-load tender workflow surfaces;
- measure before adding manual chunk rules;
- reduce font variants to those actually used.

Gate:

- initial route means the authenticated Project Cockpit entry, excluding lazy
  workflow panels not opened by the user;
- initial entry JavaScript is at most 250 kB gzip;
- Three.js is absent from every non-style-demo request;
- each lazy workflow route's entry chunk is at most 150 kB gzip;
- build fails when the budget regresses.

#### Task 5.2A - Separate project-shell and chat bootstrap reads

Files:

- backend cockpit/bootstrap and chat read routes/services;
- frontend/src/pages/ProjectCockpitPage.tsx;
- frontend project/chat query modules and focused tests.

Work:

- keep cockpit bootstrap and a bounded active-thread/messages request separate
  and start them concurrently; this selected design preserves pane isolation
  while staying within two critical calls;
- remove ensure-user/default-catalog writes from hot GETs where lifecycle
  creation can own them;
- add ETag/revision support;
- keep independent pane failures independent.

Gate:

- at most two critical application calls before the composer is usable;
- warm bootstrap p95 is at most 500 ms in the Section 9 canonical harness;
- no GET performs storage writes;
- a chat failure does not replace the project shell.

#### Task 5.2B - Add list pagination additively

Files:

- evidence, workspace, thread, and comparison list routes/queries;
- matching frontend infinite/paged queries and tests.

Work:

- add cursor/limit response shapes without removing current callers;
- cut one consumer at a time, then remove the unbounded response only after all
  consumers and contracts are green.

Gate:

- first page is bounded and stable under concurrent inserts;
- no intermediate commit breaks an existing consumer.

#### Task 5.3A - Bound chat history and project-file queries

Files:

- backend chat message repository;
- backend MCP project-file query/service;
- focused query-count/result tests.

Work:

- query only the latest configured N history rows, then reverse them;
- push list_project_files query/path/limit filters into SQL;

Gate:

- chat history query row count is bounded;
- filtered file reads do not load the project tree into Python.

#### Task 5.3B - Share frontend agent configuration

Files:

- frontend agent configuration selectors/query module;
- agent-mode toggle components and tests.

Work:

- use one TanStack query/cache key for model/runtime configuration;
- remove the non-functional cross-project toggle from agent mode.

Gate:

- one config request per cache window;
- no agent UI promises cross-project behavior that the token cannot perform;

#### Task 5.3C - Pool Supabase auth HTTP connections

Files:

- backend authentication client/lifespan setup;
- focused lifecycle/auth tests.

Selected mechanism:

- use one lifespan-managed, connection-pooled async HTTP client with explicit
  timeouts/limits;
- do not introduce local JWT verification in this task.

Gate:

- cold-auth and warm-auth timings are separately visible;
- client closes on shutdown and auth behavior is unchanged.

#### Task 5.4A - Batch retrieval neighbours

Files:

- backend/app/retrieval/queries.py;
- backend/app/retrieval/retriever.py;
- retrieval golden/query-count tests.

Work:

- replace one neighbour query per fused hit with a batch query;
- preserve project UUID filters in every query.

Gate:

- retrieval results remain equivalent on the golden tests;
- query count is constant with result limit;
- retrieval p95 improves against the committed baseline;
- no cross-project cache/result leakage.

#### Task 5.4B - Decide semantic/lexical query concurrency

Work:

- compare current sequential execution, one composed SQL path, and concurrent
  execution using separate DB sessions under the retrieval fixture;
- record EXPLAIN/query count, connection pressure, p50/p95, and result equality;
- emit a follow-up packet naming the selected mechanism and exact files; do not
  implement a speculative embedding cache here.

Gate:

- the decision record selects one option or explicitly keeps sequential
  execution; no implementation agent is asked to choose architecture.

#### Task 5.5A - Batch uploads and refresh once

Work:

- bounded upload analysis/ingest concurrency of two;
- one evidence/tree/activity refresh per completed batch;

Gate:

- no more than two simultaneous heavy ingests per browser batch;
- refresh count is one per batch;
- failure of one file is isolated and visible;
- server and browser remain responsive.

#### Task 5.5B - Batch delete with optimistic rollback

Work:

- add one project-scoped batch delete endpoint with retention-lock checks;
- remove optimistically, rollback failed items, then refresh once;
- virtualize repository lists only when the committed row-count trace justifies
  a separate follow-up task.

Gate:

- cross-project IDs fail atomically;
- locked Tender inputs are not deleted;
- partial per-file failures are represented without losing successful deletes.

#### Task 5.6A - Share Tender queries and polling

Work:

- introduce comparison/list/progress/matrix/QA/report query keys;
- replace async setInterval with adaptive query polling that pauses when hidden,
  avoids overlap, and backs off on errors;
- use durable project events/immediate responses as hints and adaptive polling
  as the authoritative fallback.

Gate:

- cached Tender tab transitions are under 100 ms;
- progress freshness is at most 2 s while visible and active.

#### Task 5.6B - Make QA acceptance optimistic

Work:

- optimistically remove an accepted QA item with rollback;
- prefetch the next page image and keep comparison-scoped query keys.

Gate:

- QA item disappears within 100 ms and rolls back on failure;
- settled QA request p95 is at most 800 ms;
- no full QA queue reload occurs after one acceptance.

#### Task 5.7 - Measure and decide Hermes session reuse

Work:

- measure process setup, spawn-to-first-byte, provider TTFT, and total;
- verify Hermes resume/session behavior in isolated concurrent tests;
- record whether reuse improves measured TTFT by at least 20 percent without
  history duplication or tenant leakage;
- write a follow-up packet selecting either per-thread session mapping or
  removal of the unused hermes_session_id field; do not implement either branch
  in this decision task;
- never keep a session merely because the column exists.

Gate:

- a written decision with before/after timings;
- concurrency, cancellation, and tenant isolation tests pass.

#### Task 5.8 - Implement the recorded Hermes session decision

Implement only the branch and exact file list produced by Task 5.7. Re-run
concurrency, cancellation, history-duplication, and tenant-isolation tests plus
the same before/after performance fixture.

### Phase 6 - Full Tender performance, cost, and quality gates

#### Task 6.1 - Wire real TCM usage telemetry

Files:

- backend/tender/llm/client.py;
- backend/tender/llm/openai_client.py;
- backend/tender/services/telemetry.py;
- backend/tender/worker.py;
- focused telemetry tests.

Work:

- propagate model, prompt version, request ID, token usage, retries, cache hits,
  queue wait, and stage duration from the LLM client/worker;
- record zero only when no LLM call occurred;
- correlate comparison, job, document, and report IDs.

Gate:

- a real LLM stage produces non-zero usage;
- deterministic stages correctly record zero LLM calls;
- no prompt/customer content is placed in telemetry.

#### Task 6.2 - Replace the extraction-only speed gate

Files:

- backend/tests/tender/performance/ full-pipeline fixture/benchmark;
- backend/tender/worker.py timing boundaries;
- docs/performance/tender/ reports.

Work:

- keep the ODL micro-benchmark;
- add a separate cold and warm full-pipeline benchmark from intake through
  report-ready/QA-required state;
- include queue time, extraction, classification, mapping, expectations,
  silence, analysis, flags, and report;
- attach the stage ledger to failures.

Gate:

- 60 s is the optimization goal and <=90 s is the measured stretch target for
  the named three-quote fixture; it is not a binding release gate until the
  baseline and provider variance are recorded;
- PRD five-quote target remains at most 30 minutes excluding human QA;
- a regression identifies the slow stage rather than only failing total time.

#### Task 6.3 - Produce measured optimization packets

Work:

- use Task 6.2's ledger to rank stages by contribution and variance;
- create one follow-up packet per proven bottleneck with exact files, selected
  technique, baseline, target, quality tests, and rollback;
- do not modify production behavior in this decision task.

Allowed follow-up techniques:

- project-scoped content-hash raw extraction cache keyed by project, extractor,
  and extractor version, with retention; never return cached raw text or
  provenance across projects;
- bounded per-quote parallelism;
- batched embeddings/model calls where the schema permits;
- prompt/provider cache reuse;
- skip idempotent completed stages;
- separate CPU/JVM and LLM concurrency limits.

Rules for every generated packet:

- no TCM rewrite while stage handlers pass quality gates;
- no prompt/model/taxonomy change without the PRD evaluation run;
- all math remains Python;
- result quality and tenant isolation must remain equal or improve.

#### Task 6.4 - Build the required Tender evaluation corpus

Files:

- data/tender/golden/manifest.yaml;
- data/tender/golden/annotations/;
- anonymised protected fixture storage referenced by the manifest;
- data/tender/tools/validate.py and eval fixture tests.

Work:

- populate at least 30 anonymised real tender documents across supported
  new-build/renovation/addition cases, states, formats, and quality levels;
- add adversarial fixtures for OCR noise, duplicates, addenda, missing scope,
  conflicting totals, allowances, alternates, GST, and exclusions;
- record consent/provenance, expected labels/items/totals/flags, and retention;
- never commit identifiable customer material to the public repository.

Gate:

- the manifest is non-empty, validates, and covers every PRD critical metric;
- redaction and access review pass.

#### Task 6.5 - Run Tender evaluation and complete QS acceptance

Files:

- backend/tender/eval/;
- data/tender/report_language.yaml;
- docs/performance/tender/ evaluation/QS report;
- focused report-language tests.

Work:

- run prompt/model/taxonomy evaluation on the frozen corpus;
- meet the PRD Section 14 thresholds with no critical safety regression;
- obtain and record the QS review/gate;
- prove every customer-facing report phrase is selected from
  data/tender/report_language.yaml;
- freeze evaluated prompt/model/taxonomy versions.

Gate:

- all PRD eval and QS gates pass before Tender is exposed to customers or used
  for approved Cost Plan handoffs.

#### Task 6.6 - Implement measured Tender optimizations

Assign one packet generated by Task 6.3 at a time. Re-run the full performance
fixture, eval suite, deterministic arithmetic tests, and two-owner isolation
tests after each change. Revert a change that does not move its measured stage.

Release gate R3:

- Phase 2 Tender integration may be exercised internally after atomic intake;
- customer exposure, approval, and downstream Cost Plan handoff wait for Tasks
  6.4-6.5;
- this does not block independent Project Profile/PMP/Cost Plan releases.

### Phase 7 - Typed Cost Plan and cross-workflow handoffs

#### Task 7.1 - Extend Phase 1 capabilities for typed Cost Plan actions

Goal:

Tell users and the agent what each workflow genuinely supports.

Initial truth:

- Project Plan supports the broad taxonomy matrix;
- Tender Comparison is Class 1 residential in NSW/VIC/QLD with supported work
  types only;
- Cost Plan knowledge is materially narrower and must not imply equal
  confidence across all six classes.

Work:

- add create, refresh, row-edit, and approved-Tender-handoff capabilities to
  `workflow_capabilities(snapshot)`;
- express reference-data coverage and required confirmation explicitly;
- do not create a second capability implementation.

Gate:

- UI tiles and agent use the same capability result;
- unsupported workflows block clearly;
- no general model knowledge fills a missing reference-data capability.

#### Task 7.2A - Add canonical Cost Plan schema

Files:

- backend/app/cost_plan/models.py;
- backend/app/cost_plan/schemas.py;
- next free core migration;
- focused migration/tenancy tests.

Data must include:

- version and project;
- cost code/category/item;
- budget, committed, forecast, paid;
- allowance type;
- quantity/unit/rate when applicable;
- basis, source refs, confidence, and status;
- contingency, escalation, GST treatment, and deterministic totals.

Rules:

- versions are immutable; changes create a new version through Artefact
  Revision;
- money uses Decimal/integer-safe database types, never float;
- add project/user FKs, indexes, reviewed downgrade/RLS/grants, and two-owner
  isolation tests.

Gate:

- schema round-trip and downgrade pass on an isolated database;
- duplicate version/item identities and cross-project access are rejected.

#### Task 7.2B - Import existing Cost Plan drafts once

Files:

- backend/app/cost_plan/import_legacy.py;
- explicit operator command under backend/scripts/;
- import fixtures/tests.

Work:

- parse existing markdown into a typed import result with warnings;
- retain the original draft/version as audit source;
- never invent rows that fail parsing;
- make dry-run default and apply idempotent.

Gate:

- imported totals reconcile with accepted source drafts;
- unparsed rows are explicit;
- rerunning apply creates no duplicate version/items.

#### Task 7.2C - Implement deterministic Cost Plan arithmetic

Files:

- backend/app/cost_plan/calculations.py;
- table-driven arithmetic tests.

Work:

- calculate budget, committed, forecast, paid, variance, allowances,
  contingency, escalation, GST, and totals in Python/Decimal;
- define rounding and inclusive/exclusive GST rules explicitly;
- reject incomplete unit/rate inputs rather than guessing.

Gate:

- exact fixtures cover positive/negative/zero/rounding cases;
- no model-generated number participates in arithmetic without validated typed
  input.

#### Task 7.3A - Render Cost Plan markdown from typed state

Work:

- markdown renderer consumes typed cost state;
- narrative remains a separate typed/model-owned section;
- Artefact Revision publishes the canonical revision plus markdown export.

Gate:

- markdown rows/totals match the calculation fixture exactly;
- evidence/provenance survives rendering.

#### Task 7.3B - Render the workbook from typed state

Work:

- change backend/app/sitewise/cost_plan_workbook.py to consume typed Cost Plan
  state, never parsed markdown;
- publish through the Artefact export job.

Gate:

- markdown and workbook totals/rows agree exactly;
- editing one item creates one new version and regenerates both;
- evidence/provenance survives rendering.

#### Task 7.4A - Add narrow Cost Plan read/edit tools

Tools:

- get_cost_plan
- upsert_cost_item
- set_contingency
- set_cost_plan_assumption

Rules:

- every mutation requires expected base version;
- tools never rank builders;

Gate:

- "set demolition allowance to $80,000" changes only that typed item;
- totals and exports recalculate in Python;
- stale or unauthorized updates fail.

#### Task 7.4B - Add the approved-Tender Cost handoff

TCM-owned DTO `ApprovedTenderCostHandoff` must contain:

- approved/frozen report version with mandatory QA resolved, QS gate passed,
  and operator approval;
- explicit selected quote and package/scope;
- comparison, report, quote, and source document versions/hashes;
- mapped cost codes/items;
- stated and comparable totals;
- GST treatment, alternates, PC/PS allowances, exclusions, and qualifications;
- stable idempotency key.

Boundary:

- an explicit MCP composition adapter reads this DTO from TCM and maps it to a
  generic immutable Cost Plan external-proposal DTO;
- core Cost Plan neither imports TCM code/models nor queries tender_* tables;
- the user must explicitly choose the quote/package and confirm application;
- applying creates a proposed Cost Plan revision, never an accepted one;
- reuse of the idempotency key cannot apply the same result twice.

Gate:

- unapproved/unfrozen/incomplete-QA Tender results cannot be handed off;
- every source version and financial qualifier remains visible/auditable;
- the proposed revision is reversible and builder ranking never occurs.

#### Task 7.4C - Add safe Cost Plan refresh

Work:

- implement refresh only over typed state, current Project Snapshot, and an
  explicit expected base version;
- preserve user-locked/manual items and return conflicts/proposals for affected
  values;
- expose one shared start path to UI and MCP using Workflow Run.

Gate:

- refresh creates a proposed version with exact diff/provenance;
- locked rows survive and accepted state never changes automatically.

#### Task 7.5 - Add dependency snapshots and stale reasons

Every artefact records:

- profile revision;
- evidence snapshot/fingerprint;
- project decision revision/set;
- upstream artefact IDs/versions;
- model/prompt/runtime versions.

Compute, do not manually store when avoidable:

- profile_changed;
- evidence_added_removed_or_revised;
- decision_changed;
- upstream_artefact_revised;
- tender_approved_after_cost_plan.

Rules:

- traverse the acyclic graph in Section 4;
- profile/evidence/decisions are roots, Tender may propose Cost, and accepted
  Cost may request PMP refresh;
- reject any dependency edge that would create a cycle.

Gate:

- changing project type identifies affected outputs and why;
- an approved Tender may offer a proposed Cost Plan revision; an accepted Cost
  summary may offer a PMP refresh, and neither runs silently;
- historical Tender context remains frozen even when current profile changes.

Release gate R4:

- typed Cost Plan import/arithmetic/rendering and capability gates pass;
- row-level tools and refresh pass version/conflict/provenance tests;
- approved-Tender handoff additionally requires R3 customer quality approval;
- only a proposed Cost Plan revision is produced; no budget or builder decision
  is silently accepted.

### Phase 8 - Project intelligence, production acceptance, and cutover

#### Task 8.1 - Enrich the Phase 1 Project Snapshot with rollups/actions

Interface:

- get_project_snapshot
- get_project_next_actions

Snapshot includes:

- profile and revision;
- capability/readiness;
- evidence counts and ingest failures;
- current purpose selections;
- latest artefacts and stale reasons;
- active/failed workflow runs;
- Tender states and QA count;
- open project decisions;
- budget summary when typed Cost Plan exists.

Next actions are deterministic rules with reasons and routes. Hermes may explain
and prioritize them, but it is not the source of readiness truth.

Boundary:

- TCM publishes a generic comparison/status/QA projection through the core
  composition interface;
- Project Snapshot does not import TCM models or query tender_* tables.

Gate:

- UI overview and agent use the same snapshot;
- every recommended action names the blocking fact and target route/tool;
- no unsupported workflow is recommended.

#### Task 8.2 - Role-based product acceptance

Create:

- docs/acceptance/role-scenarios/construction-manager.yaml;
- docs/acceptance/role-scenarios/architect.yaml;
- docs/acceptance/role-scenarios/design-manager.yaml;
- anonymised/synthetic files under backend/tests/fixtures/acceptance/;
- an isolated backend acceptance harness plus focused frontend state/route
  tests; do not add a browser-test dependency until the dependency policy is
  justified.

Every manifest names the seed profile, decisions, files/quote groups, exact
commands, expected run/resource/artefact versions, forbidden state changes,
and timing measurement boundaries.

Construction manager scenario:

- create profile, upload/sort, create Project Plan and Cost Plan, select
  three quote groups, compare, QA, approve, apply the explicitly selected
  result to a proposed Cost Plan
  revision, inspect stale impacts.

Expected state:

- one accepted PMP and Cost Plan, one approved frozen Tender report, one
  proposed (not accepted) Cost revision, exact provenance, and zero silent
  builder/budget decisions.

Architect scenario:

- set class/work type/role, generate Project Plan, resolve decisions, create
  consultant RFP artefacts, track design/approval gaps, review cost effect.

Expected state:

- locked procurement/design decisions survive PMP refresh, PMP meets the
  canonical 2-4-page/evidence-status fixture, and consultant artefact route and
  version are exact.

Design manager scenario:

- inspect evidence completeness, consultant scopes, decisions, design risks,
  procurement readiness, and exact source/provenance links.

Expected state:

- deterministic next actions identify every seeded blocker and route, stale
  reasons match the changed root revisions, and no unsupported workflow is
  offered.

Automated pass thresholds:

- 100 percent of required state/provenance/route assertions pass;
- 100 percent of explicit fixture commands either complete or return the
  expected typed needs-input/unsupported result;
- zero cross-project reads/writes and zero silent acceptance transitions;
- all applicable Section 9 hard SLOs pass in the named harness.

Product-study metrics to record, not substitute for the automated gate:

- median time from upload to first usable artefact;
- median time from selected tenders to QA-ready comparison;
- manual clicks avoided by successful chat commands;
- percent of explicit commands completed without navigation;
- user correction rate per artefact/workflow;
- stale artefact detection-to-refresh time;
- LLM spend and tokens per successful workflow.

#### Task 8.3 - Production gate and legacy cutover

Before cutover:

- all Phase 0-8 gates above are green;
- live VPS validates DB, storage, Hermes/Pi, MCP, SSE, both workers, ODL,
  Stripe, tenant isolation, cancellation, and recovery;
- full profile-to-Project-Plan-to-Cost-Plan-to-Tender scenario passes;
- two owners with the same slug/path remain isolated;
- bundle and latency budgets pass;
- Tender golden/eval and QS gates required by the PRD are complete before
  customer-facing claims;
- rollback is tested.

Only then:

- perform the existing Phase 8.5 small, revertible legacy deletions;
- remove obsolete runtime fields and repair paths;
- update README, architecture, deployment, and completion ledgers.

## 9. Performance and reliability SLOs

### 9.1 Canonical performance harness

Task 0.8 must create `docs/performance/environment.md` before any p95 gate is
claimed. It records:

- git commit, production configuration, OS, CPU/RAM, worker counts;
- VPS and Supabase regions plus measured network RTT;
- browser/device profile and production frontend build hash;
- provider/model/prompt versions;
- fixture IDs/sizes, quote/page/item counts, and concurrency;
- cold cache/process definition and warm cache definition.

Measurement rules:

- HTTP/UI p95: five warmups followed by at least 30 measured samples; use
  nearest-rank p95 and publish raw timings;
- cold process/agent/Tender: at least 10 samples where practical, report every
  sample plus median/p95 and provider time separately;
- warm: same fixture and revision, initialized connection pools, no hidden data
  mutation; cold: new process where relevant and application caches empty;
- workflow enqueue starts before the request and ends when the durable run ID
  is committed/returned;
- profile visibility starts at mutation commit/event timestamp and ends after
  the target control renders the new revision;
- Tender full-pipeline starts before atomic intake and ends at report-ready or
  explicit QA-required terminal state;
- bundle size comes from the production build manifest and compressed artifact,
  not development-server transfer size;
- reports live under `docs/performance/<area>/<date>-<commit>.md`.

Hard gates do not receive a percentage-improvement waiver. If the harness
environment changes, re-baseline it explicitly and preserve the prior report.
Application and provider/network time remain separately visible.

### 9.2 Gates

| Measure | Gate |
| --- | --- |
| Cross-project evidence/mutation isolation | 100 percent |
| Orphan child processes after cancel/timeout | 0 |
| Production TypeScript build | 0 errors |
| Initial JS | at most 250 kB gzip |
| Three.js on non-demo routes | 0 bytes |
| Warm cockpit bootstrap | p95 at most 500 ms, zero writes |
| Critical calls before composer usable | at most 2 |
| Agent profile event to visible UI | p95 at most 500 ms |
| Workflow enqueue acknowledgement | p95 at most 500 ms |
| Cached workflow tab transition | under 100 ms |
| QA optimistic response | under 100 ms |
| QA settled server response | p95 at most 800 ms |
| Three-quote full cold run | <=90 s measured stretch target; 60 s goal, not a cutover gate until baselined |
| Five-quote full run excluding human QA | at most 30 min |
| Concurrent artefact revisions | no duplicate versions or stale exports |
| Default test lane | offline/non-destructive; each parallel shard under 60 s |

## 10. Parallelization map

Foundation tracks:

- run 0.0A-D before risky schema/application cutovers;
- evidence identity is strictly 0.1 -> 0.2 -> 0.3 -> 0.4 -> 0.5;
- runtime safety 0.7A-D and measurement 0.8 may run beside evidence work;
- route code-splitting 5.1 may run after 0.0A if it does not touch a current
  ProjectCockpitPage change.

After the Project State foundation:

- profile path: 1.1 -> 1.2 -> 1.3, then 1.5/1.6 and frontend 1.10;
- events: 1.4 precedes cross-turn/cross-tab UI and every async worker gate;
- decisions -> minimal snapshot -> capability is 1.7 -> 1.8 -> 1.9;
- core workflow track: 3.1 -> 3.2A -> workflow-specific 3.2 adapters, while
  4.1 -> 4.2A prepares the queue; join them at each workflow adapter and then
  4.3/4.4;
- Tender track: 2.1 -> 2.2; 2.3 -> 2.4A -> 2.4B -> 2.4C; 2.5 may run beside
  it; TCM quality 6.1-6.5 runs beside core Workflow Run work;
- frontend/read-path work in Phase 5 runs per packet after its baseline and
  shared query/event predecessor;
- typed Cost Plan work starts after 3.2A/4.1, and the approved-Tender handoff
  additionally waits for 3.2E and 6.5.

Staged additive release gates:

- R1: tenant-safe evidence plus Project Profile/Decisions/Snapshot/Capability;
- R2: each individually accepted Project Plan, Cost Plan create, sort, and
  consultant action;
- R3: internal Tender after atomic intake; customer Tender after eval/QS;
- R4: typed Cost Plan and approved-Tender proposal handoff;
- final: role acceptance/production recovery, then and only then Phase 8.5
  legacy deletion.

Must remain sequential:

- Project Profile module before HTTP/MCP adapters;
- concurrency-safe draft allocation before Artefact Revision;
- Artefact Revision before removing repair-on-read;
- workflow-run persistence before workflow MCP actions;
- typed Cost Plan before row-level Cost Plan tools or Tender handoff;
- Tender eval/QS before approval/customer exposure/handoff;
- all production gates before legacy deletion.

Do not assign two agents to backend/app/mcp_bridge/server.py or
frontend/src/pages/ProjectCockpitPage.tsx concurrently. Those files are current
merge hotspots.

## 11. Handoff template for each smaller LLM

Packet-readiness rule:

- assign only a numbered packet (`1.10A`, not "Phase 1");
- do not assign a packet until every predecessor commit is named and green;
- if a packet says measure/decide, it may write only tests, measurements, and
  its decision/follow-up packet; it may not choose and implement a production
  branch in the same change;
- the lead must replace every bracket below, including exact file list and
  commands. If that cannot be done, split or investigate the packet first;
- use an isolated branch/worktree per packet and preserve the current unrelated
  dirty worktree.

Default verification menu (narrow it for the packet):

- backend: `uv run pytest <focused-tests> -q`,
  `uv run ruff check <changed-python-files>`, and
  `uv run ruff format --check <changed-python-files>` from `backend/`;
- frontend: `pnpm test -- <focused-test>`, `pnpm tsc --noEmit`, `pnpm lint`,
  and `pnpm build` from `frontend/` as applicable;
- migrations: graph tests by default; upgrade/downgrade only with the named
  disposable `TEST_DATABASE_URL` and explicit destructive-test opt-in;
- Tender eval/live-provider work only with the named protected fixture and
  explicit marker/credentials;
- every packet: `git diff --check` and `git status --short`.

Copy this and replace the bracketed fields:

~~~text
Implement only Task [ID and title] from
docs/plans/2026-07-10-integrated-agentic-workflows-performance.md.

Read AGENTS.md, [backend/frontend]/AGENTS.md, the July Hermes plans, and the
task's governing domain document first. Preserve all unrelated dirty-worktree
changes.

Predecessors:
- Required task/commit IDs: [exact list]
- Required baseline/decision record: [exact path or none]

Scope:
- Allowed files: [exact list]
- Do not modify: [exact list]
- Required interface: [name]
- Required behavior: [one behavior]
- Exact success/error response or event: [schema]
- Required authorization/tenancy rule: [rule]
- Required deterministic/model boundary: [rule]
- Rollout/cutover rule: [additive switch/removal condition]
- Non-goals: [exact list]

Work test-first:
1. Add the smallest failing contract test.
2. Run it and record the expected failure.
3. Implement only enough for the behavior.
4. Run: [exact focused commands].
5. Show git diff --check and git status --short.

Do not add dependencies, compatibility shims, feature flags, broad refactors,
or unrelated cleanup. Do not run integration/eval tests unless the task names
an isolated test database or fixture.

Return:
- outcome;
- files changed;
- tests and exact results;
- assumptions;
- remaining risks;
- commit hash if asked to commit.
~~~

## 12. Definition of done

The application is "faster, smarter, and integrated" only when:

- project evidence is UUID-tenant-safe;
- chat can update the same Project Profile seen by the UI;
- UI and chat share the same immutable, grouped Tender quote selection;
- confirmed facts, locked decisions, run briefs, and evidence-derived proposals
  have distinct owners;
- Project Plan, Cost Plan, Tender Comparison, sort, and consultant actions are
  available through shared typed commands;
- every action updates visible project state and remains durable after reload;
- every artefact has consistent versioning, edit policy, exports, provenance,
  and stale reasons;
- Cost Plan arithmetic is typed and deterministic;
- Tender remains evidence-grounded, evaluated, and human-reviewed where
  required;
- approved Tender handoff creates only an explicit, proposed Cost Plan revision;
- performance and cancellation are measured and gated;
- the production end-to-end role scenarios pass before legacy cutover.
