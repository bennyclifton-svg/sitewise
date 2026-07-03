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

