# Project Activity Trace — Design

Date: 2026-07-04

Status: draft, validated in conversation, not yet implemented.

## Motivation

A user uploading a document currently gets no visibility into what the app did
during the ~30 seconds of ingest (extract, classify, chunk, embed, persist) —
only console `structlog` output, which is technical, not persisted, and not
INFO-level for most stages. Separately, `create_pmp`, `create_cost_plan`, and
`sort_files` already build a rich, human-readable per-run trace
(`WorkflowTraceEvent`: step/status/message/metadata) and persist it — but only
inside that draft's `provenance_metadata` and as a chat message, so it's only
visible if you're looking at that specific draft or thread.

Goal: make the trace that already exists for PMP/cost-plan/sort ambient and
universal — cover document ingest too, unify all sources into one project-wide
feed, and surface it in a panel that's visible regardless of where the user is
in the app.

## Prior art already in the codebase

- `WorkflowTraceEvent` (`step`, `status`, `message`, `metadata`) —
  [app/schemas/projects.py](../../backend/app/schemas/projects.py), already
  used by `CreatePmpResponse.trace`, `CreateCostPlanResponse.trace`, and
  `SortFilesResponse.trace`.
- `WorkflowTracePanel` —
  [frontend/src/components/project/WorkflowTracePanel.tsx](../../frontend/src/components/project/WorkflowTracePanel.tsx),
  renders that shape today at the bottom of `DraftReviewPanel` ("Run
  complete", per-step icons, metadata summary).
- Persistence today: embedded in `draft_artifacts.provenance_metadata`
  (`seed_consulted`, `evidence_refs`, `context_refs`, `trace`) and posted as a
  chat message (`message_data.workflowTrace`) via `_persist_trace_message` in
  [app/workflows/create_pmp.py](../../backend/app/workflows/create_pmp.py).
- Tender is architecturally different: a real background job queue
  (`tender_jobs`, claimed via `SELECT ... FOR UPDATE SKIP LOCKED` in
  [tender/services/jobs.py](../../backend/tender/services/jobs.py)), not a
  synchronous request. It doesn't use `WorkflowTraceEvent` today.

## Design

### 1. Data model

New table `activity_events`:

| column | notes |
|---|---|
| `id` | uuid |
| `project_id` | fk |
| `run_id` | groups the steps of one operation into one feed entry |
| `source` | `document_ingest` \| `sort_files` \| `create_pmp` \| `create_cost_plan` \| `tender` \| … |
| `reference_type` / `reference_id` | nullable; `workspace_file` / `draft_artifact` / `tender_job`, for deep-linking |
| `step` / `status` / `message` / `metadata` | same shape as `WorkflowTraceEvent`, deliberately — nothing to translate |
| `created_at` | |

Indexes: `(project_id, created_at desc)` for the feed, `(project_id, run_id)`
for one run's steps.

One run = one feed card. A multi-file upload is **one run per file**, not one
run for the batch — avoids an ambiguous "partially running batch" state, and
matches "one card per document."

A run's status is derived, not stored: `running` until its newest event has a
terminal status (`complete`/`failed`/`blocked`/`skipped`/`refused`/etc.).

### 2. Producers

In order of effort:

1. **PMP / cost plan** — near-zero new work. Both already build a `trace`
   list and funnel every exit point through `_persist_trace_message()`; add
   the `activity_events` insert there, reusing the existing trace list.
2. **Sort files** — same idea; `sort_inbox_files` already computes a
   human-readable reason per file, each becomes one event.
3. **Document ingest** (the original ask) — new instrumentation through
   `_upload_single_file` / `ingest_hosted_file`: stored → classified →
   extracted → chunked → embedded → persisted.
4. **Tender** — fast-follow, not v1-blocking. New call sites in the worker at
   existing job status transitions; schema already accommodates it.

`record_activity_events(session, *, project_id, source, run_id,
reference_type=None, reference_id=None, events)` is the single insert helper,
wrapped in its own try/except — a failure here must never break the workflow
it's observing.

### 3. API

`GET /projects/{project_id}/activity?since=<cursor>` — paginated (~50),
most-recent-first, each run with its full event list embedded inline (small
payloads, no N+1 fetch on expand). Client polls with the newest timestamp it
already has; server returns only what's new. Same project-ownership auth
dependency as every other project route.

### 4. Frontend

`ProjectLeftNav` already persists across `activeView` changes (workbench/
file/draft/folder only swap the center content) — so "visible regardless of
where I am" is nearly free: add a fourth accordion section, **Activity**,
beside Skills/Knowledge/Admin. The panel is already resizable
(`CockpitPanelResizeHandle`); just widen the default/min-width when Activity
is open.

A new `ActivityFeed` component lists runs as collapsed one-line cards (icon,
title, status, relative time); expanding renders that run's events through
the **existing `WorkflowTracePanel`, unmodified** — same visual language
users already know from the PMP draft view.

`useProjectActivity(projectId)` polls every 2-3s only while a visible run is
non-terminal, otherwise fetches once; also force-refetches right after
actions the app already knows just completed (upload done, workflow tile
finished). Card clicks reuse the nav callbacks `ProjectLeftNav`'s parent
already passes down (`onSelectWorkspacePath`, `onOpenWorkflow`).

### 5. Error handling & edge cases

- Activity-logging failures are swallowed and logged, never propagated.
- Failed/blocked stages reuse `WorkflowTracePanel`'s existing styling — no
  new failure UI to design.
- Stalled runs: if a non-terminal run's newest event is older than a
  threshold (minutes for sync workflows, longer for tender), the frontend
  renders it as "stalled" instead of spinning forever — a rendering rule, no
  backend watchdog needed for v1.
- No retention/purge logic in v1; flagged as a future cleanup job if the
  table grows large over months.

### 6. Testing

- Backend: unit tests for `record_activity_events` (rows, ordering, run
  grouping, swallowed failures); integration tests per producer (success +
  failure paths) asserting expected rows; API tests for pagination, `since`
  cursor, and project-scoped auth.
- Frontend: component tests for `ActivityFeed` (collapsed/expanded, running,
  failed) against mock data; a test for the polling hook's on/off behavior.
- End-to-end gate script (style of `phase5_acceptance.py`): upload a file,
  confirm a row via the API; run Create PMP, confirm the same trace appears
  in both `WorkflowTracePanel` (draft view) and the new feed — one source of
  truth, not two copies that can drift.

## Explicitly out of scope for v1

- True push (SSE) — polling was chosen over extending the chat SSE pattern
  project-wide; revisit only if 2-3s latency proves to matter in practice.
- Tender worker instrumentation — schema-compatible, implemented later.
- OpenTelemetry / distributed tracing — not warranted at this app's current
  scale (one backend, one job queue); `run_id` is forward-compatible with a
  trace ID if that ever changes.
