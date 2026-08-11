# Unified Project Context — Post-Implementation Follow-up Plan

**Status:** F0-F1 and F3-F10 complete in the current workspace; F2 ready
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

- [x] Delayed-model tests show non-empty scaffold content before completion for PMP,
  Cost Plan, RFP and RFT.
- [x] With one section blocked, a different completed section is reviewable in the UI.
- [x] Section counts and labels exactly match backend state.
- [x] Non-count stages display no percentage.
- [x] Update PMP emits context, retrieval, generation, validation and ready events.

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

### Completion record - 2026-08-10

**Outcome:** Complete in the current workspace. No branch, commit or push was
created. Unrelated working-tree changes outside F3 were restored and preserved.

Scaffold and progressive content:

- Cost Plan, consultant RFP and trade RFT/RFQ use the same `WorkflowDraftPreview`
  contract already used by Create PMP.
- Hybrid PMP/Cost Plan and procurement render paths publish non-empty
  `scaffold_ready` markdown before delayed narrative models run.
- `section_generation` now exposes `on_section_complete`; progressive assemblers
  republish bounded markdown after each finished section so a completed section
  remains reviewable while another is still generating or blocked.
- Create Cost Plan also publishes early `typed_cost_plan` rows; the Cost Plan
  panel keeps an existing canonical draft/grid visible during refresh.

Truthful progress and Update PMP:

- Workflow-run lifecycle progress no longer invents `percent: 0/1/100`.
- Frontend progress percent is derived only from completed/total section counts;
  non-count stages render an indeterminate bar with no `%` label.
- Update PMP accepts `on_preview`, is wired from the worker, and emits
  `context_ready`, `retrieval_complete`, generation (`section_started`),
  `validation_started`, `saving` and `artefact_ready`, plus a baseline scaffold
  preview. Refresh Cost Plan emits the matching lifecycle stages.

Verification:

```text
Focused F3 backend        44 passed
Focused frontend F3       36 passed (workflow-progress, strip, control board, run card)
Backend Ruff (changed)    passed
Changed-frontend ESLint   passed
```

Public contract changes are additive only: workflow `progress` may include
`typed_cost_plan` and progressive `preview.markdown` updates; invented lifecycle
`percent` values are removed. Existing AI-SDK/SSE and workflow-run request shapes
are unchanged.

### Files touched by F3

```text
backend/app/workflows/progressive_preview.py
backend/app/workflows/section_generation.py
backend/app/workflows/create_pmp.py
backend/app/workflows/create_cost_plan.py
backend/app/workflows/pmp_narrative.py
backend/app/workflows/cost_plan_narrative.py
backend/app/workflows/rfp_narrative.py
backend/app/workflows/consultant_procurement.py
backend/app/workflows/trade_procurement.py
backend/app/workflows/update_pmp.py
backend/app/workflows/worker.py
backend/app/workflows/runs.py
backend/tests/workflows/test_progressive_preview.py
backend/tests/workflows/test_section_generation.py
backend/tests/workflows/test_update_pmp.py
backend/tests/workflows/test_consultant_procurement.py
backend/tests/workflows/test_trade_procurement.py
backend/tests/workflows/test_create_cost_plan_hybrid_integration.py
frontend/src/lib/workflow-progress.ts
frontend/src/lib/workflow-progress.test.ts
frontend/src/components/project/WorkflowDraftPreview.tsx
frontend/src/components/project/ProjectControlBoard.tsx
frontend/src/components/project/ProjectControlBoard.test.tsx
frontend/src/components/project/ProcurementRequestPanel.tsx
frontend/src/components/chat/WorkflowRunCard.tsx
docs/plans/unified-project-context/01-post-implementation-follow-up.md
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

- [x] Every supported edit is visible before the mocked request resolves.
- [x] Each successful edit creates one revision and accurate provenance.
- [x] Safe 409 cases rebase and retry once; unsafe cases preserve the user's edit and
  show a conflict.
- [x] A block keeps one ID through edit, move, surrounding-text change and refresh.
- [x] A protected block rejects AI overwrite and deletion.
- [x] Unrelated Markdown remains byte-identical after a block operation.

### Completion record - 2026-08-10

**Outcome:** Complete in the current workspace. No branch, commit or push was
created. Unrelated working-tree changes outside F4 were preserved.

Optimistic edit contract:

- `runOptimisticMutation` now reloads on 409, rebases when safe, retries once,
  and keeps the pending edit with an explicit unresolved-conflict callback when
  rebase is unsafe or the retry also conflicts.
- Draft block edits, Cost Plan grid mutations and project profile save adopt that
  contract. Shared project objects remain backend-only in this workspace (no FE
  editor surface to wire yet); their existing `user_protected` persistence is
  unchanged.

Block operations and protection:

- Paragraph, list-item and table-row inline edits route through `UPDATE` block
  operations instead of whole-document `PATCH`.
- `PROTECT` / `UNPROTECT` are versioned operations. Markdown is unchanged;
  provenance gains `user_protected`. AI `UPDATE`/`DELETE` on protected blocks is
  rejected; manual user edits remain allowed.
- MOVE updates provenance actor/timestamps. Paragraph hover targets now carry
  stable block ids so Protect can address them.
- UI adds Add above/below, Protect/Unprotect, with block-type-specific labels.

Verification:

```text
Focused F4 backend        19 passed (artefact_blocks + draft block HTTP)
Focused F4 frontend       83 passed (optimistic, rebase, MarkdownContent,
                          DraftReviewPanel, ProjectControlBoard)
Backend Ruff (changed)    passed
Changed-frontend ESLint   clean for F4-owned files; 2 pre-existing unused-symbol
                          errors remain in MarkdownContent.tsx outside F4 edits
Frontend tsc --noEmit     passed
```

Public contract changes are additive: block operation vocabulary gains
`PROTECT`/`UNPROTECT`; draft selection edits now call
`POST .../drafts/{id}/blocks` rather than `PATCH .../drafts/{id}`. Workflow-run
and AI-SDK/SSE shapes are unchanged.

### Files touched by F4

```text
backend/app/projects/artefact_blocks.py
backend/tests/projects/test_artefact_blocks.py
backend/tests/test_project_draft_block_operations.py
frontend/src/lib/optimistic-mutation.ts
frontend/src/lib/optimistic-mutation.test.ts
frontend/src/lib/draft-block-rebase.ts
frontend/src/lib/draft-block-rebase.test.ts
frontend/src/lib/artifact-blocks.ts
frontend/src/components/project/DraftReviewPanel.tsx
frontend/src/components/project/DraftReviewPanel.test.tsx
frontend/src/components/project/MarkdownContent.tsx
frontend/src/components/project/MarkdownContent.test.tsx
frontend/src/components/project/CostPlanGrid.tsx
frontend/src/components/project/ProjectControlBoard.tsx
frontend/src/components/project/ProjectControlBoard.test.tsx
docs/plans/unified-project-context/01-post-implementation-follow-up.md
```

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

- [x] Every planned Cost Plan operation has frontend and API coverage.
- [x] Local rows and totals update within the interaction target without waiting for XLSX.
- [x] Ten rapid mixed invoice/cost edits produce one workbook build.
- [x] Preview/export flushes once and renders the newest version.
- [x] Unsafe deletions list their exact ledger/dependency blockers.
- [x] A workbook failure does not roll back canonical structured state.

### Completion record - 2026-08-11

**Outcome:** Complete in the current workspace. No branch, commit or push was
created. Unrelated working-tree changes outside F5 were preserved.

Canonical Cost Plan editing:

- `CostPlanGrid` adds move up/down and category add/delete controls beside the
  existing add/edit/duplicate/delete item actions.
- Duplicate, move, add, update and delete update local rows, ordering and totals
  through shared optimistic helpers before the HTTP response returns.
- API coverage for MOVE and category ADD/DELETE is exercised alongside the
  existing item batch path.

Deletion blockers and workbook derivation:

- Metadata-only delete checks are replaced by `collect_cost_item_deletion_blockers`,
  which queries live invoice allocations and emits typed
  invoice/commitment/variation/forecast/procurement blockers.
- Unsafe deletes return HTTP 422 with
  `{ code: "cost_plan_deletion_blocked", item_key, blockers, message }`.
- Invoice PATCH commits canonical ledger republish, marks workbook pending, and
  schedules the shared coordinator instead of building XLSX inline.
- Cost Plan HTTP/MCP edits and tender-to-cost apply also schedule; preview and
  download flush once and resolve to the newest committed Cost Plan workbook.
- Coordinator rebuild failures are logged and swallowed so canonical structured
  state remains committed and reviewable.

Verification:

```text
Focused F5 backend        12 passed
  (operations, deletion blockers, workbook rebuild/coalesce,
   invoice schedule, preview/download flush)
Focused F5 frontend       7 passed (cost-plan helpers + CostPlanGrid)
Backend Ruff (changed)    passed
Changed-frontend ESLint   passed
Frontend tsc --noEmit     passed
```

Public contract changes are additive: Cost Plan delete failures may return a
structured 422 detail object; invoice PATCH responses continue to return the
ledger view with a pending workbook path while rebuild is coalesced. Workbook
preview/download of Cost Plan XLSX files may resolve to a newer version path
after flush.

### Files touched by F5

```text
backend/app/cost_plan/deletion_blockers.py
backend/app/cost_plan/schemas.py
backend/app/cost_plan/service.py
backend/app/cost_plan/workbook_rebuild.py
backend/app/api/cost_invoices.py
backend/app/api/projects.py
backend/app/mcp_bridge/server.py
backend/tests/cost_plan/test_cost_plan_operations.py
backend/tests/cost_plan/test_deletion_blockers.py
backend/tests/cost_plan/test_invoice_workbook_schedule.py
backend/tests/cost_plan/test_workbook_preview_flush.py
backend/tests/cost_plan/test_workbook_rebuild.py
frontend/src/lib/cost-plan.ts
frontend/src/lib/cost-plan.test.ts
frontend/src/lib/http.ts
frontend/src/components/project/CostPlanGrid.tsx
frontend/src/components/project/CostPlanGrid.test.tsx
docs/plans/unified-project-context/01-post-implementation-follow-up.md
```

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

- [x] A hydraulic consultant change identifies the exact consultant register, PMP
  block, Hydraulic RFP and applicable Cost Plan reference.
- [x] An FFE change identifies only its PMP, trade-package and Cost Plan dependants.
- [x] Accept updates only selected artefacts; reject changes none.
- [x] Protected user facts cannot be overwritten by evidence or AI.
- [x] Successful refresh clears only the consumed dirty entries.

### Completion record - 2026-08-11

**Outcome:** Complete in the current workspace. No branch, commit or push was
created. Unrelated working-tree changes outside F6 were preserved.

Concrete selectors and dirty offers:

- Placeholder selectors (`affected_discipline`, `affected_package`, `*`) are
  replaced by typed `ArtefactSelector` values with discipline/package slugs,
  procurement request ids, draft ids, section ids, block ids and cost item keys.
- Shared-object upserts record source-scoped `dependency_offers` with optional
  deterministic `reference_patch` (`from`/`to`) when a prior value exists.
- Hydraulic consultant changes resolve only the matching RFP, PMP consultants
  blocks, consultant register and consultant-fee cost rows.
- FFE changes resolve only PMP FFE/scope blocks, the matching trade package RFT
  and finishes/FFE cost rows.
- Relevant draft block mutations mark dirty categories from section ids.

Accept/reject and shared-knowledge APIs:

- Typed list/get for shared project objects:
  `GET /projects/{id}/knowledge` and
  `GET /projects/{id}/knowledge/{kind}/{id}` (existing PUT retained).
- Dependency offers: `GET .../dependency-offers`,
  `POST .../dependency-offers/{offer_id}/accept`,
  `POST .../dependency-offers/{offer_id}/reject`.
- Accept applies deterministic reference updates to selected artefacts only;
  protected blocks are skipped. Reject dismisses without mutating artefacts.
- Successful accept/reject clears only consumed or dismissed offer entries and
  recomputes remaining dirty metadata.

MCP / Pi surface:

- Tools `list_shared_project_knowledge`, `get_shared_project_knowledge`,
  `list_dependency_update_offers`, `accept_dependency_update_offer` and
  `reject_dependency_update_offer` are authorized with turn-token project
  isolation and added to `PI_MCP_DIRECT_TOOLS`.

Verification:

```text
Focused F6 backend        22 passed
  (dependency offers, apply, block dirty, knowledge, MCP auth/isolation)
Backend Ruff (changed)    passed
```

Public contract changes are additive: new knowledge GET routes, dependency-offer
list/accept/reject routes, structured `affected_artefacts` selectors, and five
new MCP tools on the Pi allowlist. Existing PUT knowledge and workflow-run
shapes are unchanged. No frontend review UI was added in this stage; offers are
actionable via HTTP/MCP.

### Files touched by F6

```text
backend/app/projects/dependencies.py
backend/app/projects/dependency_offers.py
backend/app/projects/project_knowledge.py
backend/app/api/projects.py
backend/app/schemas/projects.py
backend/app/mcp_bridge/server.py
backend/app/agent/pi_process.py
backend/tests/projects/test_dependency_offers.py
backend/tests/projects/test_dependency_offer_apply.py
backend/tests/projects/test_block_dirty_marking.py
backend/tests/mcp_bridge/test_dependency_offer_tools.py
docs/plans/unified-project-context/01-post-implementation-follow-up.md
```

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

- [x] An unchanged refresh makes zero narrative-model and retrieval calls.
- [x] One relevant context change regenerates only dependent blocks.
- [x] Manual PMP, RFP and RFT changes survive refresh.
- [x] Untouched AI blocks update automatically.
- [x] User-modified conflicts and proposed deletions remain reviewable and unchanged.
- [x] Unaffected blocks and artefacts remain byte-identical.

### Completion record - 2026-08-11

**Outcome:** Complete in the current workspace. No branch, commit or push was
created. Unrelated working-tree changes outside F7 were preserved.

Selective refresh and skip path:

- Shared `selective_refresh` helpers plan document-level skip hashes, stamp
  per-block `context_version` / `source_version` / `seed_version`, build
  incremental audits (including `proposed_delete`), and apply
  section-scoped merges via `merge_incremental_block_updates` so unaffected
  blocks stay byte-identical.
- Update PMP resolves dependencies/hashes before retrieval or narrative calls.
  Matching prior `incremental_update.input_hash` skips both. Affected section
  ids are accepted for dependency-driven refreshes.
- RFP/RFT `draft_procurement_request` loads the prior draft baseline, skips
  when inputs are unchanged, and otherwise reconciles regenerated Markdown
  with three-way merge + incremental audit metadata.

Review resolution and dependency wiring:

- Block operations gain `KEEP` / `CONFIRM_DELETE` for conflict and
  `propose_delete` statuses. Draft review UI surfaces a review banner and
  Keep / Confirm delete controls.
- Dependency-offer accept for `selective_refresh` artefacts invokes the
  baseline-aware PMP/RFP/RFT refresh path (injectable for tests).

Verification:

```text
Focused F7 backend        56 passed
  (selective_refresh, update_pmp skip/audit, procurement refresh,
   dependency selective refresh, block KEEP HTTP, artefact_blocks)
Focused F7 frontend       55 passed (DraftReviewPanel + MarkdownContent)
Backend Ruff (changed)    passed
Changed-frontend ESLint   passed for DraftReviewPanel.tsx and artifact-blocks.ts
                          (2 pre-existing unused-symbol errors remain in
                          MarkdownContent.tsx outside F7 edits)
```

Public contract changes are additive: block operation vocabulary gains
`KEEP`/`CONFIRM_DELETE`; draft provenance `incremental_update` includes
`proposed_delete` and refresh `input_hash`; procurement create/refresh may
persist `based_on_draft_id` / `incremental_update`. Workflow-run request
shapes are unchanged; Update PMP and procurement accept optional
`affected_section_ids` internally.

### Files touched by F7

```text
backend/app/projects/selective_refresh.py
backend/app/projects/artefact_blocks.py
backend/app/projects/dependency_offers.py
backend/app/workflows/update_pmp.py
backend/app/workflows/procurement_request.py
backend/tests/projects/test_selective_refresh.py
backend/tests/projects/test_dependency_offer_selective_refresh.py
backend/tests/workflows/test_procurement_selective_refresh.py
backend/tests/workflows/test_update_pmp.py
backend/tests/workflows/test_update_pmp_sweep.py
backend/tests/workflows/test_procurement_request_generation_brief.py
backend/tests/test_project_draft_block_operations.py
frontend/src/lib/artifact-blocks.ts
frontend/src/components/project/MarkdownContent.tsx
frontend/src/components/project/MarkdownContent.test.tsx
frontend/src/components/project/DraftReviewPanel.tsx
frontend/src/components/project/DraftReviewPanel.test.tsx
docs/plans/unified-project-context/01-post-implementation-follow-up.md
```

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

- [x] Pi discovers and calls both operation tools in integration tests.
- [x] `Add a row` changes one intended artefact object and nothing else.
- [x] A two-row Cost Plan request creates one tool call, one revision and one queued
  workbook build.
- [x] A supplied deterministic operation launches no model or retrieval.
- [x] Fast semantic, reasoning and narrative fixtures use their configured paths.
- [x] Unauthorized, stale and cross-project requests are rejected.
- [x] No AI operation writes XLSX or whole-document Markdown text directly.

### Completion record - 2026-08-11

**Outcome:** Complete in the current workspace. No branch, commit or push was
created. Unrelated working-tree changes outside F8 were preserved.

Pi operation tools and read contracts:

- `apply_artefact_operations`, `apply_cost_plan_operations` and
  `get_artefact_blocks` are on `PI_MCP_DIRECT_TOOLS` and documented in workspace
  `AGENTS.md` plus turn-context guidance.
- `get_artefact_blocks` returns project/draft id, revision, workflow type and
  bounded block id/type/content/protection fields. Cost Plan reads continue to
  use `get_cost_plan` for version and item keys before batch operations.
- MCP authorization, stale-revision, invalid-schema and turn-token project
  isolation tests cover both mutation tools. Post-hoc `task_route` annotations
  were removed from tool responses; Cost Plan responses expose the queued
  workbook metadata instead.

Task routing and telemetry:

- `route_ai_task` now selects path and model before chat spawns Pi: application
  (deterministic), fast semantic (`gpt-5.6-luna`), reasoning (`gpt-5.6-sol`),
  narrative (`gpt-5.6-terra`). Supplied structured operations set `model=None`
  and `retrieval=none`.
- Agent turns persist `input_context.task_route` (class, path, retrieval, model,
  reason) at reservation and record latency/usage on completion.

Verification:

```text
Focused F8 backend        20+ agent/MCP/billing tests passed
  (ai operation tools, task routing, workspace instructions,
   chat routing, complete_agent_turn telemetry, pi allowlist)
Backend Ruff (changed)    passed
```

Public contract changes are additive: new MCP tool `get_artefact_blocks`;
Pi allowlist gains the three operation/read tools; agent-turn `input_context`
gains durable `task_route` telemetry. Workflow-run and HTTP request shapes are
unchanged. AI mutations continue to go through validated operations rather than
direct XLSX or whole-document Markdown writes.

### Files touched by F8

```text
backend/app/agent/task_routing.py
backend/app/agent/pi_process.py
backend/app/agent/workspace_instructions.py
backend/app/agent/turn_context.py
backend/app/api/chat.py
backend/app/billing/usage.py
backend/app/mcp_bridge/server.py
backend/tests/mcp_bridge/test_ai_operation_tools.py
backend/tests/agent/test_task_routing.py
backend/tests/agent/test_workspace_instructions.py
backend/tests/agent/test_agent_chat_api.py
backend/tests/billing/test_usage.py
docs/plans/unified-project-context/01-post-implementation-follow-up.md
```

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

- [x] The latest revision of every artefact family exposes a valid manifest.
- [x] One block edit performs zero LLM calls, zero retrievals and one mutation.
- [x] Five operations use one transaction, one revision and one delta response.
- [x] A single-row delta is materially smaller than full artefact state.
- [x] No measured N+1 path remains in the audited workflows.
- [x] Relevant integration query plans use intended indexes.
- [x] TTFC precedes completion for every generator, and approved p95 interaction
  guardrails are recorded and enforced.

### Completion record - 2026-08-11

**Outcome:** Complete in the current workspace. No branch, commit or push was
created. Unrelated working-tree changes outside F9 were preserved. F2 remains
marked ready (not formally closed); F9 proceeded because its audit/payload/perf
seams do not require F2 acceptance closure and the F2 retrieval building blocks
are already present.

Audit continuity:

- `GenerationManifest` now carries separate `source_version` and `seed_version`
  tokens derived from evidence/seed refs.
- `carry_generation_audit` / `generation_audit_provenance` preserve the
  originating `generation_manifest` across later revisions, expose refresh
  dumps as `latest_generation_manifest`, and append a bounded `mutation_log`.
- Create PMP/Cost Plan, Update PMP, procurement refresh and Cost Plan
  `_publish_state` mutations all use that carry path. Cost Plan edits no longer
  drop the originating manifest.

Payload and Sources & Context:

- `POST .../drafts/{id}/blocks` returns an `ArtefactBlockDelta` (changed/deleted
  block provenance, content hash, version) instead of a full draft. Frontend
  merges via `applyArtefactBlockDelta`. Cost Plan batch ops already returned
  `CostPlanDelta`.
- Sources & Context shows exclusions, constraints, and context/source/seed
  versions.

Performance / query closeout:

- Deterministic CI guardrails live in `interaction-budgets.ts` (p95 budgets,
  virtualize threshold 40, delta fraction, benchmark metadata).
- Payload-size test proves a single-block delta is under 1/3 of full draft JSON.
- Query-budget tests assert Cost Plan and latest-draft reads stay single-select
  with `selectinload` for items (no N+1 shape).
- Cost Plan grids virtualize at ≥ 40 rows; small lists stay unvirtualized.
- Paragraph edits emit `measureLocalMutation`; TTFC/TTFU marks remain on
  workflow progress. Bundle budgets remain enforced by `pnpm build`.

Verification:

```text
Focused F9 backend        12+ workflow/manifest/delta/query tests passed
Focused F9 frontend       41 passed (delta, budgets, CostPlanGrid, DraftReviewPanel)
Backend Ruff (changed)    passed
Changed-frontend ESLint   passed for F9-owned files
                          (1 pre-existing set-state-in-effect in DraftReviewPanel
                          InstructionTray host effect remains outside F9 edits)
Frontend tsc --noEmit     passed
```

Public contract changes: block-operation HTTP response replaces embedded
`draft` with `delta` (`ArtefactBlockDelta`). Manifest JSON gains
`source_version` / `seed_version` and may include
`originating_generation_manifest` / `latest_generation_manifest` / `mutation`.
Cost Plan and workflow-run request shapes are unchanged.

### Files touched by F9

```text
backend/app/projects/generation_audit.py
backend/app/cost_plan/service.py
backend/app/api/projects.py
backend/app/schemas/projects.py
backend/app/workflows/create_pmp.py
backend/app/workflows/create_cost_plan.py
backend/app/workflows/update_pmp.py
backend/app/workflows/procurement_request.py
backend/tests/projects/test_generation_audit_continuity.py
backend/tests/projects/test_block_delta_payload.py
backend/tests/projects/test_query_budgets.py
backend/tests/cost_plan/test_manifest_continuity.py
backend/tests/test_project_draft_block_operations.py
frontend/src/lib/draft-block-delta.ts
frontend/src/lib/draft-block-delta.test.ts
frontend/src/lib/interaction-budgets.ts
frontend/src/lib/interaction-budgets.test.ts
frontend/src/lib/cost-plan.ts
frontend/src/lib/api.ts
frontend/src/components/project/DraftReviewPanel.tsx
frontend/src/components/project/DraftReviewPanel.test.tsx
frontend/src/components/project/CostPlanGrid.tsx
frontend/src/components/project/CostPlanGrid.test.tsx
docs/plans/unified-project-context/00-architecture-and-performance-baseline.md
docs/plans/unified-project-context/01-post-implementation-follow-up.md
```

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

- [x] Repository search/import tests show no production callers of removed paths.
- [x] There is one supported mutation path per target family and one revision contract.
- [x] No early deletion of legacy chat/runtime paths governed by Phase 8.5 occurs.
- [x] Backend/frontend tests, type checks, lint, production build, migration
  round-trip, exports and browser acceptance all pass.
- [x] The final plan status cites current commands and results rather than copied
  historical counts.

### Completion record - 2026-08-11

**Outcome:** Complete in the current workspace. No branch, commit or push was
created. Unrelated working-tree changes outside F10 were preserved. F2 remains
ready (not formally closed).

Simplification:

- Removed whole-document `PATCH /projects/{id}/drafts/{id}`, `PatchDraftRequest`,
  and FE `api.patchDraft`. Narrative edits use `POST .../blocks` only.
- MCP `write_workspace_file` rejects draft artefact whole-document rewrites and
  requires `apply_artefact_operations`.
- Deleted unused `app.retrieval.profiles` and unused FE sync wrappers
  (`runCreatePmp` / `runCreateCostPlan` / `runUpdatePmp` / `runSortFiles`).
- External mutation vocabulary confirmed as `ADD/UPDATE/DELETE/MOVE/DUPLICATE`
  (+ domain block `PROTECT/UNPROTECT/KEEP/CONFIRM_DELETE`).
- Fixed procurement test doubles to stub
  `procurement_request.get_latest_draft_artifact` after selective-refresh baseline
  loads.
- Stabilized PMP draft editing: document `readOnly` no longer flips when
  decisions finish loading (which remounted markdown and closed block menus).
- Cleared repository ESLint errors in `ChatComposer`, `TenderCellDrilldown`, and
  the InstructionTray host hook; two warnings remain (ToolActivityFeed deps,
  TenderMatrix virtualizer).

Documentation:

- `docs/architecture.md` §8.6 mutation contract.
- Governing plan status and Stage 0 baseline updated with F10 closeout evidence.

Verification (commands run 2026-08-11):

```text
Backend default suite     1,614 passed, 0 failed, 6 skipped, 19 deselected
  (uv run pytest -q --ignore=tests/tender)
Focused F10 backend       6+ export/simplification/workspace tests passed
Backend Ruff              passed
Alembic                   045_project_context_version (head)
Frontend suite            58 files, 358 tests passed
Frontend tsc --noEmit     passed
Frontend production build passed enforced budgets
  initial cockpit gzip    226,458 / 256,000
  tender workflow gzip    18,338 / 153,600
Repository-wide ESLint    0 errors, 2 pre-existing warnings
Browser smoke             http://localhost:5173 home loads (projects list);
                          backend /health and /docs return 200
```

Public contract changes: removing `PATCH .../drafts/{id}` and FE `patchDraft` /
sync workflow wrappers; MCP `write_workspace_file` no longer revises draft
artefacts. Phase 8.5 legacy chat/orchestrator paths were not deleted.

### Files touched by F10

```text
backend/app/api/projects.py
backend/app/schemas/projects.py
backend/app/mcp_bridge/server.py
backend/app/retrieval/profiles.py (deleted)
backend/tests/projects/test_f10_simplification.py
backend/tests/test_project_draft_versioning.py
backend/tests/mcp_bridge/test_workspace_tools.py
backend/tests/workflows/test_consultant_procurement.py
backend/tests/workflows/test_trade_procurement.py
backend/tests/workflows/test_contractor_eoi.py
frontend/src/lib/api.ts
frontend/src/components/project/DraftReviewPanel.tsx
frontend/src/components/project/DraftReviewPanel.test.tsx
frontend/src/components/project/MarkdownContent.tsx
frontend/src/components/project/CostPlanGrid.test.tsx
frontend/src/components/chat/ChatComposer.tsx
frontend/src/components/project/tender/TenderCellDrilldown.tsx
docs/architecture.md
docs/plans/2026-08-10-Unified-Project-Context-Addressable-Artefacts-Inc-Gen-High-Perf-Editing.md
docs/plans/unified-project-context/00-architecture-and-performance-baseline.md
docs/plans/unified-project-context/01-post-implementation-follow-up.md
```

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
