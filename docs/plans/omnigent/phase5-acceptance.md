# Phase 5 Acceptance

Date: 2026-07-04

Status: green.

## Implemented

- In-process TCM worker loop behind `TENDER_WORKER_INPROC_ENABLED`, default off.
- MCP tools:
  - `list_selected_documents`
  - `get_comparison_status`
  - `get_comparison_result`
- Existing `workflow_type="tender_report"` draft/report artefact is emitted
  from `get_comparison_result`; no duplicate tender artefact type was added.
- Tender worker records per-stage telemetry rows.
- Worker chain continues through mapping, expectations, silence, analysis,
  flags, and report assembly when QA is clear.
- Backend Dockerfile now installs `default-jre-headless` for ODL on the current
  Debian slim base.
- Comparison-level continuation jobs are guarded so concurrent mapping and
  silence work do not create duplicate `run_expectations` or `run_analysis`
  jobs.
- The seeded report-language rows are rehydrated into the nested dictionary
  expected by report draft assembly.

## Verification

- `uv run alembic upgrade head`: passed.
- `uv run pytest tests/mcp_bridge tests/tender -q`: passed,
  218 passed / 1 skipped.
- `uv run ruff check app/mcp_bridge tender tests/mcp_bridge tests/tender`:
  passed.
- `uv run pytest tests/tender/test_flagship_speed_gate.py -m tender_eval -q -s`:
  passed on Windows with Java available.
- WSL speed gate:
  `UV_PROJECT_ENVIRONMENT=/home/bennyclifton/.cache/clerk-phase5-wsl-venv uv run pytest tests/tender/test_flagship_speed_gate.py -m tender_eval -q -s`
  passed: 1 passed in 8.20 seconds.
- Scripted WSL chat acceptance:
  `scripts/phase5_acceptance.py` passed with `PHASE 5 ACCEPTANCE: GREEN`.

Timing table from the Windows JVM run:

| stage | status | duration_ms | llm_calls | input_tokens | output_tokens | cache_hits |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| odl_extract:Enmore.pdf | done | 1579 | 0 | 0 | 0 | 0 |
| odl_extract:Kaposi.pdf | done | 1348 | 0 | 0 | 0 | 0 |
| odl_extract:NexusBuilt.pdf | done | 1525 | 0 | 0 | 0 | 0 |
| package_total | done | 4454 | 0 | 0 | 0 | 0 |

Timing table from the WSL JVM run:

| stage | status | duration_ms | llm_calls | input_tokens | output_tokens | cache_hits |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| odl_extract:Enmore.pdf | done | 4386 | 0 | 0 | 0 | 0 |
| odl_extract:Kaposi.pdf | done | 981 | 0 | 0 | 0 | 0 |
| odl_extract:NexusBuilt.pdf | done | 1488 | 0 | 0 | 0 | 0 |
| package_total | done | 6856 | 0 | 0 | 0 | 0 |

Acceptance output:

- `PHASE 5 ACCEPTANCE: GREEN`
- `comparison_id=5e7135e3-c206-4fc9-afbb-afc260583452`
- `report_id=2e573d4a-4341-4edb-999e-d60a02d3273e`
- `draft_id=162f9c3d-49d8-499f-8328-62cabd3fcd02`
- `artefact_title=Tender comparison report v01`
- `matrix_groups=16`

## Decision

Phase 5 is green. Phase 6 may begin.

Verified:

- Candidate tender PDFs are found from chat.
- Hermes starts the tender comparison through MCP.
- The worker drains the TCM pipeline.
- The comparison result contains a populated matrix.
- A `tender_report` artefact card appears in chat.
- The timing ledger is attached to the run.
