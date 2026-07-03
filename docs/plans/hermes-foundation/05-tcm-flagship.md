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
  These should return stage/progress data for chips and final structured data
  for the artefact card.
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

## Gate

- Scripted manual run on Linux/WSL2: selected or candidate tenders are compared
  from chat, TCM completes, panel populates, report artefact card appears.
- Simple three-tender cold run meets the agreed speed gate or produces a timing
  ledger that identifies the bottleneck before scope expands.

## Gate Result - 2026-07-03

Status: not green yet.

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
- Local migration `uv run alembic upgrade head` passed.
- `uv run pytest tests/mcp_bridge tests/tender -q` passed: 218 passed,
  1 skipped.
- `uv run ruff check app/mcp_bridge tender tests/mcp_bridge tests/tender`
  passed.
- Windows JVM cold speed gate passed for the three pilot PDFs:
  4.454 seconds total.

Gate blockers:

- WSL2 Ubuntu is available, but Java is not installed there and passwordless
  `sudo` is unavailable, so the WSL ODL run could not be executed.
- The backend Dockerfile now uses `default-jre-headless` after the clean Linux
  build exposed that `openjdk-17-jre-headless` is unavailable on the current
  `python:3.12-slim` Debian base. A clean Docker build from `git archive` still
  timed out after 15 minutes before producing an image, due to the heavy ODL
  dependency install path.
- The full Linux/WSL2 scripted chat acceptance run has therefore not completed.

Phase 6 must not start until this gate is rerun on a Linux environment with a
working JVM/backend image and the chat-to-TCM artefact flow is observed.
