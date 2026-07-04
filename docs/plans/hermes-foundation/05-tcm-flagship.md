# Phase 5: TCM Flagship Flow

## Objective

Make the flagship natural-language flow work end to end:

User asks to compare selected tenders, Hermes calls the MCP tools, the TCM
worker runs the pipeline, the comparison panel updates, and the existing TCM
report draft appears as an in-chat artefact card.

## Implementation Changes

- Prefer a separate production worker service running `python -m tender.worker`.
  Optional in-process worker mode may be added for local/dev convenience only.
- Add `list_selected_documents` only after confirming whether a real selection
  model exists. If none exists, return candidate tender PDFs from
  `workspace_files` and keep `start_tender_comparison` accepting explicit
  `workspace_paths`.
- Add or complete `get_comparison_status` and `get_comparison_result` MCP tools.
  `get_comparison_status`'s status-bus `done` event must carry a machine-readable
  `stage` (string), `percent` (number), `doneUnits`, and `totalUnits` — not just
  a status string — so Phase 4 chips can render advancing progress instead of a
  flat running/done boolean. Final structured data (including the nested
  `progress` object) still returns as the tool's own result for the artefact
  card and any caller that wants the full payload.
- Reuse `tender.services.report.build_report_draft` and the existing
  `workflow_type="tender_report"` draft artefact. Do not create a duplicate
  `workflow_type="tender_comparison"` draft unless that migration is explicitly
  approved later.
- Emit the Phase 4 artefact event using the `TenderReport.draft_id`,
  `comparison_id`, and report title.
- Add a small telemetry slice before speed/usage gates: comparison id, stage,
  duration, token/LLM counts where available, cache hits where available, and
  final status.

## Worker Decision

Production uses a separate Dokploy service in Phase 8. Long ODL and LLM jobs
should not compete with FastAPI request handling. If an in-process worker flag is
added for MVP/dev, it must default off in production examples.

## Tests

- MCP start tool creates comparison, quotes, documents, and queued jobs.
- Status/result tools return stable structured payloads.
- Report lifecycle creates a `tender_report` draft and linked tender report.
- Artefact event references the existing draft/report rather than duplicating
  artefact rows.
- Telemetry records per-stage duration for a pipeline run.
- `@pytest.mark.tender_eval` speed test prints the timing table.
- `get_comparison_status`'s status-bus `done` event includes `stage`,
  `percent`, `doneUnits`, and `totalUnits` (`backend/tests/mcp_bridge/
  test_tools_comparison_status_result.py::
  test_get_comparison_status_publishes_progress_on_done_event`).

## Gate

- Scripted manual run on Linux/WSL2: selected or candidate tenders are compared
  from chat, TCM completes, panel populates, report artefact card appears.
- Simple three-tender cold run meets the agreed speed gate or produces a timing
  ledger that identifies the bottleneck before scope expands.

## Gate Result - 2026-07-04

Status: green.

Implemented and verified:

- In-process tender worker loop exists behind `TENDER_WORKER_INPROC_ENABLED`,
  defaulting off.
- `list_selected_documents`, `get_comparison_status`, and
  `get_comparison_result` are exposed as authenticated MCP tools.
- `get_comparison_result` emits the existing `tender_report` draft/report as a
  Phase 4 artefact event when one exists.
- The worker records per-stage timing telemetry and now continues the pipeline
  toward report assembly, while preserving the QA gate before report draft
  creation.
- Comparison-level continuation jobs are guarded so mapping and silence work can
  finish in parallel without duplicate `run_expectations` or `run_analysis`
  jobs.
- Report language loaded from seeded DB rows is rebuilt into the nested report
  dictionary expected by the draft assembler.
- Local migration `uv run alembic upgrade head` passed.
- `uv run pytest tests/mcp_bridge tests/tender -q` passed: 218 passed,
  1 skipped.
- `uv run ruff check app/mcp_bridge tender tests/mcp_bridge tests/tender`
  passed.
- WSL JVM cold speed gate passed for the three pilot PDFs:
  Enmore 4386 ms, Kaposi 981 ms, NexusBuilt 1488 ms, package total 6856 ms.
- Scripted WSL chat acceptance passed with `PHASE 5 ACCEPTANCE: GREEN`.
  Evidence:
  - `comparison_id=5e7135e3-c206-4fc9-afbb-afc260583452`
  - `report_id=2e573d4a-4341-4edb-999e-d60a02d3273e`
  - `draft_id=162f9c3d-49d8-499f-8328-62cabd3fcd02`
  - `artefact_title=Tender comparison report v01`
  - `matrix_groups=16`

The acceptance run used real `/chat/agent/stream` turns. Hermes first called
MCP to list candidate tender documents and start the comparison, the worker
drained ingestion, classification, extraction, embeddings, mapping,
expectations, silence inference, analysis, flag generation, and report assembly,
and Hermes then called `get_comparison_result` to retrieve the report artefact.

Phase 6 may begin.

## Addendum - 2026-07-03: stage-progress chip data

Independent of the WSL2/Java gate blocker above: `get_comparison_status`'s
`done` status-bus event now carries `stage`/`percent`/`doneUnits`/`totalUnits`
so Phase 4's chips can show advancing progress on long-running comparisons
instead of a flat running/done state. Backend and frontend changes, tests,
and lint all verified on Windows (no JVM/WSL dependency for this fix). See the
matching addendum in `04-chat-ui.md`.
