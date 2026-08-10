# Unified Project Context — Post-Implementation Follow-up Plan

**Status:** F0-F1 complete in the current workspace; F2 ready  
**Created:** 2026-08-10  
**Governing plan:**
`docs/plans/2026-08-10-Unified-Project-Context-Addressable-Artefacts-Inc-Gen-High-Perf-Editing.md`  
**Purpose:** Close the verified implementation and acceptance gaps left by the
governing plan without reopening the parts that are already complete.

The governing plan remains the product and architectural intent. This document
governs the closeout sequence. `AGENTS.md`, the Pi-only runtime decision, and the
canonical product plans listed in `AGENTS.md` win if they conflict with this
follow-up.

---

## 1. Verified Starting Point

The 2026-08-10 audit found:

- implemented: original Stages 2, 3, 6, 9, 11 and 22;
- partially implemented: the other 20 stages;
- entirely absent: none.

The implementation is substantial, but the governing plan's blanket
`Stages 0-25 complete` status is not yet supportable.

Verification at the audit point:

```text
Backend default suite     1,803 passed, 5 failed, 7 skipped, 27 deselected
Frontend suite            319 passed
Frontend production build passed enforced bundle budgets
Backend Ruff              passed
Changed-frontend ESLint   passed
Repository-wide ESLint    3 errors in unchanged pre-existing files
```

The five backend failures are existing consultant/trade procurement assertions
whose raw Markdown rows are changed by internal block markers. The current
completion declaration and most follow-up implementation files were also still
unstaged or untracked. Re-check both facts before beginning Stage F0 because the
working tree may have moved since this audit.

The repository-wide ESLint failures observed during the audit were outside the
plan diff. Do not misattribute them to a follow-up stage, but do not claim the
full lint lane is green until they are resolved or an explicit repository-level
baseline decision is recorded.

### Already-complete foundations to preserve

Do not rebuild these unless a follow-up stage identifies a proven defect:

- typed PMP, Cost Plan, RFP and RFT context lenses;
- shared cached seed routing;
- shared generation brief concept;
- addressable paragraph, list-item and table-row model;
- generic manual structural controls;
- initial generation manifests and Sources & Context UI.

---

## 2. Execution and Handoff Rules

1. One follow-up stage per agent or implementation session.
2. Before editing, read `AGENTS.md`, the applicable nested `AGENTS.md`, the
   governing plan, and this file in full.
3. Start by recording `git status --short`. Preserve unrelated and pre-existing
   changes. Do not assume the dirty worktree is disposable.
4. Do not start a stage until all listed dependencies are green and available in
   the agent's branch/worktree.
5. Use test-first changes at revision, authorization, concurrency, persistence,
   and incremental-merge seams.
6. A stage is complete only when its acceptance criteria and verification
   commands pass. The presence of a helper, model or endpoint is not sufficient.
7. Do not expose an MCP mutation merely by defining it. Pi can use only tools in
   its `directTools` allowlist, and agent instructions and authorization tests
   must agree with that surface.
8. Preserve the legacy PydanticAI/chat paths until the Phase 8.5 cutover gate.
   This follow-up does not authorize their early deletion.
9. Do not introduce new runtime dependencies unless they satisfy the repository
   dependency policy.
10. Each handoff must report files changed, tests run, observed before/after
    behavior, remaining risks, and whether the stage changed any public
    HTTP/MCP/frontend contract.

Suggested branch names use the repository prefix, for example:

```text
codex/unified-context-f0-stabilise
codex/unified-context-f4-editing
codex/unified-context-f8-ai-routing
```

Creating, committing, or pushing a branch still requires the supervising user's
authorization for that session.

---

## 3. Stage Map

| Stage | Scope | Depends on | Can run in parallel with |
| --- | --- | --- | --- |
| F0 | Stabilise and restore a truthful green baseline | None | Nothing |
| F1 | Correct project-context revision semantics | F0 | F3, F4, F5 |
| F2 | Converge retrieval, exact briefs and consistency checks | F1 | F3, F4, F5 |
| F3 | Deliver universal scaffolds and truthful progressive content | F0 | F1, F4, F5 |
| F4 | Harden optimistic editing, block provenance and protection | F0 | F1, F3, F5 |
| F5 | Complete canonical Cost Plan editing and workbook derivation | F0 | F1, F3, F4 |
| F6 | Make dependencies and shared project knowledge actionable | F1, F4, F5 | F2, F3 |
| F7 | Implement true selective PMP/RFP/RFT refresh | F4, F6 | F5 closeout |
| F8 | Wire AI structural operations and production task routing | F4, F5 | F6, then F7 |
| F9 | Close audit continuity, payload, query and performance gaps | F2, F3, F5, F8 | Nothing material |
| F10 | Simplify, document and pass the final release gate | F1-F9 | Nothing |

The safe initial parallel wave after F0 is F1, F3, F4 and F5, provided each
agent owns a separate worktree and coordinates shared API/type files before
merge.

---

## F0 — Stabilise and Restore the Green Baseline

**Maps to original stages:** 0, 25

### Objective

Establish a trustworthy checkpoint before more architecture is layered onto the
current dirty implementation.

### Tasks

- Inventory and checkpoint the current plan-related diff without overwriting
  unrelated user work.
- Resolve the five procurement regressions caused by block-marker representation.
- Preserve valid GFM table structure and unchanged visible cell content.
- Add marker strip/render/export round-trip regression tests for PMP, RFP and RFT.
- Record the real backend/frontend/build/lint baseline in this file or a linked
  performance record. Do not copy stale counts from the governing plan.
- Change the governing plan's status only after the implementation checkpoint
  and tests support the new wording.

Do not weaken assertions merely to accept corrupted or user-visible Markdown.
If tests need to become marker-aware, separately prove that rendering, editing,
export and marker stripping preserve the original visible document.

### Acceptance criteria

- [x] The default backend suite has zero failures.
- [x] The frontend suite and production build pass.
- [x] RFP/RFT issue registers and price tables retain the same visible cells.
- [x] Internal `clerk:block` markers never appear in issued exports.
- [x] Marker stripping round-trips supported Markdown without content loss.
- [x] The documented implementation status matches the available workspace code.

### Completion record - 2026-08-10

**Outcome:** Complete in the current workspace. No branch, commit or push was
created because this implementation session did not include separate Git
authorization. The repository remains a 95-entry dirty worktree containing the
larger plan implementation as well as F0; unrelated changes were preserved.

Root cause and resolution:

- Table-row identity comments were inserted inside the final visible cell. The
  five failing procurement assertions correctly detected that canonical rows no
  longer contained their original visible Markdown.
- Table headers and delimiter rows are now structural rather than addressable.
  Editable body-row markers sit after the closing pipe, preserving both the raw
  row and valid GFM table structure.
- Marker stripping now reverses paragraph, list-item and table-row encodings
  exactly, including CRLF and terminal-newline state.
- Deterministic PMP presentation transforms detach and reattach row identity
  while parsing, ordering or rebuilding cells. Issued-output helpers strip
  markers before every Markdown renderer.
- Frontend masking was verified with the current representation, including
  table shape, canonical edit offsets, paragraphs, list items and Trace & QA.
- One dead `projectTitle` argument in the already-modified Markdown renderer was
  removed after it blocked the TypeScript production build.

Verification:

```text
Backend default suite     1,814 passed, 0 failed, 7 skipped, 27 deselected
Focused F0 backend        30 passed, 1 skipped
Frontend suite            53 files, 326 tests passed
Markdown renderer         21 tests passed
Frontend production build passed TypeScript, Vite and enforced size budgets
Initial cockpit bundle    225,227 gzip bytes / 256,000-byte budget
Backend Ruff              passed
F0 frontend ESLint        passed for MarkdownContent.tsx and its test
Repository-wide ESLint    3 pre-existing errors and 2 warnings remain
```

The repository-wide ESLint errors remain in unchanged `ChatComposer.tsx` and
`TenderCellDrilldown.tsx`; warnings remain in unchanged `ToolActivityFeed.tsx`
and `TenderMatrix.tsx`. They are recorded baseline debt, not an F0 regression.
The native PDF extraction smoke test skipped where WeasyPrint libraries were
unavailable; a renderer-boundary test independently proves that marker-bearing
Markdown is stripped before the PDF renderer is called.

No HTTP schema or persistence contract changed. The existing block-operation
schema is unchanged, but its behavioral contract is now explicit: table headers
and delimiters are not valid mutation targets. The internal Markdown contract
and its presentation boundary are documented in `docs/architecture.md`.

### Files touched by F0

```text
backend/app/projects/artefact_blocks.py
backend/app/sitewise/artifact_exports.py
backend/app/sitewise/artifact_presentation.py
backend/tests/projects/test_artefact_blocks.py
backend/tests/sitewise/test_artifact_exports.py
backend/tests/sitewise/test_artifact_presentation.py
frontend/src/components/project/MarkdownContent.tsx
frontend/src/components/project/MarkdownContent.test.tsx
docs/architecture.md
docs/plans/2026-08-10-Unified-Project-Context-Addressable-Artefacts-Inc-Gen-High-Perf-Editing.md
docs/plans/unified-project-context/01-post-implementation-follow-up.md
```

---

## F1 — Correct Project-context Revision Semantics

**Maps to original stage:** 1

### Objective

Make `context_version` represent structured project-context change rather than
general project activity.

### Tasks

- Introduce one authoritative project-context revision source.
- Increment it exactly once for relevant profile, scope, consultant,
  stakeholder, programme, procurement, decision and confirmed-fact changes.
- Do not increment it for workflow queueing, progress, draft saves, exports,
  chat activity or other non-context events.
- Update snapshots, generation-context cache keys and frozen workflow briefs.
- Add migration and concurrent-update coverage if persistent schema changes are
  required.

### Acceptance criteria

- [x] Each structured context mutation increments once.
- [x] Queueing/completing a workflow or saving a draft does not increment.
- [x] Cache reuse survives non-context events.
- [x] A durable run retains the exact context revision with which it started.
- [x] Concurrent context updates cannot publish the same next revision.

### Likely files

```text
backend/app/database/project.py
backend/app/projects/events.py
backend/app/projects/profile.py
backend/app/projects/snapshot.py
backend/app/projects/generation_context.py
backend/app/workflows/runs.py
backend/alembic/versions/
```

### Completion record - 2026-08-10

**Outcome:** Complete in the current workspace. No branch, commit or push was
created. The wider staged implementation remains uncommitted, and unrelated
working-tree changes were preserved.

Revision and mutation semantics:

- `projects.project_context_version` is now the single persistent revision for
  canonical structured project context. `event_sequence` remains an independent
  ordered audit cursor.
- Effective profile mutations, logical decision mutations and shared project
  object writes advance the context revision. Workflow lifecycle events, draft
  revisions, exports, proposal lifecycle events and other operational activity
  do not.
- Multi-row decision synchronisation advances the project context once per
  logical operation while retaining one audit event and decision-set revision
  per changed row. Decision-draft restamping is explicitly revision-neutral
  because the initiating user decision already owns the context increment.
- Locked decisions now revise when their label, section, options or workflow
  metadata changes, even when the locked selection and conflict state do not.
- Profile-proposal acceptance advances once through its effective profile
  patch; proposal creation, rejection and the outer acceptance audit event do
  not add another increment.
- Shared project-object persistence locks the Project row before its JSONB
  read/modify/write, preventing concurrent objects from overwriting each other.
  Production persistence callers use `write_shared_project_object()`; the pure
  in-memory upsert helper must not be used as a persistence boundary.

Snapshot and durable-run semantics:

- Snapshot `context_version` is read directly from the Project revision. A
  bounded read/check/retry loop rejects torn structured reads, and retry queries
  refresh preloaded Project, decision and proposal ORM identities.
- Generation-context cache identity remains `(project_id, context_version)`, so
  non-context fingerprints and operational projections do not invalidate it.
- `workflow_runs.frozen_project_context_version` records the authoritative
  revision separately from JSON. New runs compare the snapshot revision with a
  locked Project row before insert. A legitimate idempotent replay still returns
  its original frozen run after live context advances.
- Workers reject any mismatch between the frozen column, frozen snapshot and
  generation context before dispatch, and dependency manifests use the frozen
  column. TCM and snapshot-less Update PMP paths now consume the same canonical
  revision.

Migration `045_project_context_version` backfills existing Project revisions
from `event_sequence + 1` to preserve historical monotonicity, and backfills
workflow runs from their frozen generation context, then snapshot, then Project.
Both columns are non-null and constrained to positive values.

Verification:

```text
Focused F1 backend        92 passed, 2 destructive tests deselected
PostgreSQL concurrency    5 passed
PostgreSQL migrations     2 passed (round-trip and legacy backfill)
Frontend suite            53 files, 327 tests passed
Frontend production build passed TypeScript, Vite and enforced size budgets
Initial cockpit bundle    225,217 gzip bytes / 256,000-byte budget
Tender workflow bundle    25,653 gzip bytes / 153,600-byte budget
Backend Ruff              passed
Changed-frontend ESLint   passed
Backend default suite     1,826 passed, 0 failed, 7 skipped, 31 deselected
```

The PostgreSQL checks ran against disposable `pgvector/pgvector:pg16`
containers. Each container was stopped and removed after verification.

Public contract changes are additive: `WorkflowRunView` and its frontend type
now expose `frozen_project_context_version`; the Project and WorkflowRun tables
gain their corresponding persistent columns. Workflow-start request shapes did
not change. A newly submitted stale snapshot can now receive the existing 409
capability-conflict response after the server locks and rechecks the Project.
There is no visual UI change.

### Files touched by F1

```text
backend/alembic/versions/045_project_context_version.py
backend/app/api/projects.py
backend/app/database/project.py
backend/app/database/projects.py
backend/app/database/workflow_run.py
backend/app/projects/artefact_adapters.py
backend/app/projects/decisions.py
backend/app/projects/events.py
backend/app/projects/profile.py
backend/app/projects/project_knowledge.py
backend/app/projects/snapshot.py
backend/app/schemas/workflow_runs.py
backend/app/workflows/runs.py
backend/app/workflows/update_pmp.py
backend/app/workflows/worker.py
backend/tender/services/project_context_adapter.py
backend/tests/cost_plan/test_invoice_mapping_memory_integration.py
backend/tests/projects/test_decisions.py
backend/tests/projects/test_events.py
backend/tests/projects/test_events_integration.py
backend/tests/projects/test_generation_context.py
backend/tests/projects/test_profile.py
backend/tests/projects/test_profile_proposals.py
backend/tests/projects/test_project_knowledge.py
backend/tests/projects/test_snapshot.py
backend/tests/tender/test_migrations.py
backend/tests/tender/test_project_context_adapter.py
backend/tests/test_project_decisions_api.py
backend/tests/workflows/test_update_pmp_sweep.py
backend/tests/workflows/test_workflow_runs.py
frontend/src/components/chat/WorkflowRunCard.test.tsx
frontend/src/components/project/ProjectControlBoard.test.tsx
frontend/src/lib/types/project.ts
docs/architecture.md
docs/plans/2026-08-10-Unified-Project-Context-Addressable-Artefacts-Inc-Gen-High-Perf-Editing.md
docs/plans/unified-project-context/01-post-implementation-follow-up.md
```

---

## F2 — Converge Retrieval, Exact Briefs and Consistency Checks

**Maps to original stages:** 4, 6, 7

### Objective

Use one bounded retrieval and concurrent-generation contract across PMP, Cost
Plan, RFP and RFT, then validate the combined result deterministically.

### Tasks

- Move PMP and Cost Plan onto `RetrievalLevel`, `RetrievalBudget` and
  `GenerationEvidencePool`.
- Wire `select_retrieval_level()` into production and start at the lowest
  sufficient level.
- Enforce search, chunk, document, token and concurrency budgets. Character
  limits may remain as a secondary hard bound, not as the token budget.
- Deduplicate logical queries and reuse evidence categories between sections.
- Make the generation brief immutable, build it once per attempt, and persist
  the exact brief/fingerprint used by every section.
- Add a post-gather deterministic consistency gate for project/consultant names,
  procurement terminology, dates, duplicate scope and duplicate risks.
- Use an AI consistency fallback only for conflicts deterministic checks cannot
  resolve, with an explicit call counter.

### Acceptance criteria

- All four artefact families use the shared retrieval contract.
- Structured-only fixtures perform zero semantic searches.
- Each logical query executes at most once per generation attempt.
- All configured budgets are enforced.
- Every section and the persisted manifest share the same brief fingerprint.
- Valid output passes consistency checks with zero extra model calls.
- A bounded-parallel fixture completes materially faster than its sequential
  control without changing selected evidence.

---

## F3 — Universal Scaffolds and Truthful Progressive Content

**Maps to original stages:** 5, 8

### Objective

Make useful content visible before generation completes for every artefact, and
remove status that is estimated rather than observed.

### Tasks

- Render Cost Plan, consultant RFP and trade RFT/RFQ scaffold previews through
  the same visible preview contract already used by PMP.
- Show canonical typed Cost Plan state while narrative or workbook derivation
  continues.
- Publish completed-section content, or an incrementally assembled bounded
  preview, after each section completes.
- Wire real lifecycle events into Update PMP and relevant Cost Plan
  refresh/import/rebuild flows.
- Remove inherited `1%`, heartbeat and other invented percentages. Use
  indeterminate state or completed/total counts where exact progress is unknown.
- Preserve the existing AI-SDK/SSE and workflow-run contracts unless a versioned
  contract change is explicitly documented.

### Acceptance criteria

- Delayed-model tests show non-empty scaffold content before completion for PMP,
  Cost Plan, RFP and RFT.
- With one section blocked, a different completed section is reviewable in the UI.
- Section counts and labels exactly match backend state.
- Non-count stages display no percentage.
- Update PMP emits context, retrieval, generation, validation and ready events.

### Likely files

```text
backend/app/workflows/create_pmp.py
backend/app/workflows/create_cost_plan.py
backend/app/workflows/procurement_request.py
backend/app/workflows/section_generation.py
backend/app/workflows/update_pmp.py
backend/app/workflows/worker.py
frontend/src/lib/workflow-progress.ts
frontend/src/components/project/WorkflowProgressStrip.tsx
frontend/src/components/project/WorkflowDraftPreview.tsx
frontend/src/components/project/ProjectControlBoard.tsx
frontend/src/components/project/ProcurementRequestPanel.tsx
```

---

## F4 — Harden Optimistic Editing, Provenance and Protection

**Maps to original stages:** 10, 12

### Objective

Finish one reliable edit contract for paragraph, list-item, table-row, profile,
Cost Plan and shared-project-object mutations.

### Tasks

- Route paragraph edits through block operations rather than whole-document PATCH.
- Add HTTP/component coverage for paragraph, list-item and table-row edit, add,
  duplicate and delete across PMP, RFP and RFT.
- Correct block-specific action labels and accessibility text.
- Extend the shared optimistic helper with reload, safe rebase, one bounded retry
  and explicit unresolved-conflict state.
- Adopt the contract for block, Cost Plan, profile and shared-object editing.
- Update block provenance on every manual and AI mutation, including baseline
  hash, actor and timestamps.
- Add a versioned user-protection operation and UI control.
- Preserve IDs when copying forward PMP, RFP and RFT revisions.

### Acceptance criteria

- Every supported edit is visible before the mocked request resolves.
- Each successful edit creates one revision and accurate provenance.
- Safe 409 cases rebase and retry once; unsafe cases preserve the user's edit and
  show a conflict.
- A block keeps one ID through edit, move, surrounding-text change and refresh.
- A protected block rejects AI overwrite and deletion.
- Unrelated Markdown remains byte-identical after a block operation.

---

## F5 — Complete Canonical Cost Plan Editing and Workbook Derivation

**Maps to original stages:** 17, 18

### Objective

Complete the live structured Cost Plan UX and make every workbook a coalesced,
derived output.

### Tasks

- Add UI controls for cost-item move and category add/delete.
- Make duplicate, ordering and affected totals truly optimistic.
- Replace metadata-only deletion checks with explicit invoice, commitment,
  variation, forecast and procurement dependency queries.
- Return typed blockers for unsafe deletion.
- Route invoice PATCH, Cost Plan HTTP/MCP edits, preview and export through one
  rebuild coordinator.
- Remove immediate invoice workbook synchronization.
- Retain explicit flush for preview/export and always render the newest committed
  Cost Plan version.
- Ensure canonical edits remain committed and reviewable if export fails.

### Acceptance criteria

- Every planned Cost Plan operation has frontend and API coverage.
- Local rows and totals update within the interaction target without waiting for XLSX.
- Ten rapid mixed invoice/cost edits produce one workbook build.
- Preview/export flushes once and renders the newest version.
- Unsafe deletions list their exact ledger/dependency blockers.
- A workbook failure does not roll back canonical structured state.

---

## F6 — Actionable Dependencies and Shared Project Knowledge

**Maps to original stages:** 13, 20

### Objective

Turn dirty metadata into exact, reviewable cross-artefact update offers.

### Tasks

- Replace placeholder selectors with concrete discipline, package, shared-object
  and block identifiers.
- Mark dirty state from profile, shared-object and relevant block mutations.
- Add typed list/get APIs for shared project objects and affected artefacts.
- Add accept/reject flows for dependent update offers; never auto-overwrite
  protected human facts.
- Implement deterministic selected-reference updates where text generation is
  unnecessary.
- Clear only dependency entries successfully consumed or explicitly dismissed.
- Expose the read/update-offer surface to Pi only after authorization and
  project-isolation tests pass.

### Acceptance criteria

- A hydraulic consultant change identifies the exact consultant register, PMP
  block, Hydraulic RFP and applicable Cost Plan reference.
- An FFE change identifies only its PMP, trade-package and Cost Plan dependants.
- Accept updates only selected artefacts; reject changes none.
- Protected user facts cannot be overwritten by evidence or AI.
- Successful refresh clears only the consumed dirty entries.

---

## F7 — True Selective PMP/RFP/RFT Refresh

**Maps to original stages:** 14, 21

### Objective

Skip unchanged work and preserve human decisions across all narrative artefacts.

### Tasks

- Add baseline-aware refresh paths for RFP and RFT.
- Apply the existing three-way block reconciliation to PMP, RFP and RFT.
- Persist context, source, seed, input and generation versions per block.
- Resolve dependencies and compute hashes before any narrative model call.
- Generate only affected blocks and wire the unchanged-input skip path into
  production rather than tests/helpers only.
- Persist updated, preserved, conflict and proposed-delete audit metadata.
- Add UI resolution for conflicts and proposed deletion.

### Acceptance criteria

- An unchanged refresh makes zero narrative-model and retrieval calls.
- One relevant context change regenerates only dependent blocks.
- Manual PMP, RFP and RFT changes survive refresh.
- Untouched AI blocks update automatically.
- User-modified conflicts and proposed deletions remain reviewable and unchanged.
- Unaffected blocks and artefacts remain byte-identical.

---

## F8 — Product-wired AI Operations and Task Routing

**Maps to original stages:** 15, 16, 19

### Objective

Make the hosted Pi agent use the smallest adequate, authorized execution path.

### Tasks

- Add `apply_artefact_operations` and `apply_cost_plan_operations` to Pi's
  `directTools` allowlist after their security tests pass.
- Document both tools in agent workspace instructions.
- Provide bounded read contracts containing project/draft ID, revision, block or
  cost-item ID, type and content required to construct valid operations.
- Add MCP authorization, stale-revision, invalid-schema and project-isolation tests.
- Invoke task classification before selecting executor, model and retrieval mode.
- Map deterministic operations to application code; fast semantic mapping to the
  configured fast path; conflicts to targeted reasoning; bounded prose to the
  narrative path.
- Remove static route annotations added after an operation has already executed.
- Persist task class, chosen path/model, retrieval mode, latency and usage in
  durable telemetry.

### Acceptance criteria

- Pi discovers and calls both operation tools in integration tests.
- `Add a row` changes one intended artefact object and nothing else.
- A two-row Cost Plan request creates one tool call, one revision and one queued
  workbook build.
- A supplied deterministic operation launches no model or retrieval.
- Fast semantic, reasoning and narrative fixtures use their configured paths.
- Unauthorized, stale and cross-project requests are rejected.
- No AI operation writes XLSX or whole-document Markdown text directly.

---

## F9 — Audit Continuity, Payload, Query and Performance Closeout

**Maps to original stages:** 0, 22, 23, 24

### Objective

Prove the responsiveness gains, retain explainability on every revision, and
remove measured backend/payload waste.

### Tasks

- Carry the originating generation manifest plus mutation metadata into every
  later PMP, RFP, RFT and Cost Plan revision.
- Expose exclusions, constraints and separate context/source/seed versions in
  Sources & Context.
- Build a repeatable browser/API benchmark for paragraph edit, row add/delete,
  Cost Plan amount/edit/add, profiler save, TTFC, TTFU, render time and payload size.
- Record p50/p95, environment and repeat count; add deterministic CI guardrails.
- Return delta responses for block and batch mutations where the optimistic UI
  already has the rest of the state.
- Profile query counts and plans before adding indexes.
- Batch independent reads and parallelize semantic/lexical retrieval only where
  measured and safe.
- Virtualize large Cost Plans/registers above measured thresholds only; do not
  virtualize small lists.
- Preserve enforced bundle budgets.

### Acceptance criteria

- The latest revision of every artefact family exposes a valid manifest.
- One block edit performs zero LLM calls, zero retrievals and one mutation.
- Five operations use one transaction, one revision and one delta response.
- A single-row delta is materially smaller than full artefact state.
- No measured N+1 path remains in the audited workflows.
- Relevant integration query plans use intended indexes.
- TTFC precedes completion for every generator, and approved p95 interaction
  guardrails are recorded and enforced.

---

## F10 — Simplification, Documentation and Final Release Gate

**Maps to original stage:** 25

### Objective

Remove superseded paths only after every caller has migrated, then replace the
governing plan's self-declared completion with verified evidence.

### Tasks

- Remove the whole-document paragraph mutation path after block operations own
  all callers.
- Converge manual UI, AI tools and backend adapters on the external
  `ADD/UPDATE/DELETE/MOVE/DUPLICATE` vocabulary while retaining domain-specific
  validation internally.
- Remove superseded retrieval, seed, workbook-preview and duplicate compiler
  paths only when repository search and import tests show no callers.
- Do not create permanent `_v2`, `_final` or parallel compatibility layers.
- Update `docs/architecture.md`, the governing plan status and the Stage 0
  baseline with final verified behavior and measurements.
- Run the complete backend, frontend, migration, export and browser acceptance
  lanes.

### Acceptance criteria

- Repository search/import tests show no production callers of removed paths.
- There is one supported mutation path per target family and one revision contract.
- No early deletion of legacy chat/runtime paths governed by Phase 8.5 occurs.
- Backend/frontend tests, type checks, lint, production build, migration
  round-trip, exports and browser acceptance all pass.
- The final plan status cites current commands and results rather than copied
  historical counts.

---

## 4. Standard Verification Matrix

Run the smallest focused tests during development, then the applicable full
lanes before handoff.

From `backend/`:

```powershell
uv run pytest -q
uv run ruff check app
uv run alembic upgrade head
```

Any stage adding or changing a migration must also perform an explicit
upgrade-downgrade-upgrade round trip against a disposable/local database.

From `frontend/`:

```powershell
pnpm.cmd test -- --run
pnpm.cmd lint
pnpm.cmd build
```

Stages F3, F4, F5, F8 and F9 also require browser-level verification of their
user-visible or Pi-agent behavior. Unit tests alone do not close those stages.

---

## 5. Agent Handoff Template

Every implementing agent should end with:

```text
Stage:
Dependencies verified:
Files changed:
Public contracts changed:
Database migrations:
Tests and exact results:
Before/after behavior or measurements:
Known limitations:
Recommended next stage:
```

If an agent discovers a new prerequisite or a scope conflict, it should stop,
record it under the relevant stage, and hand back a bounded follow-up rather
than silently expanding its assignment.
