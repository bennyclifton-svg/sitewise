# Phase 5 Acceptance

Date: 2026-07-03

Status: not green yet.

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

## Verification

- `uv run alembic upgrade head`: passed.
- `uv run pytest tests/mcp_bridge tests/tender -q`: passed,
  218 passed / 1 skipped.
- `uv run ruff check app/mcp_bridge tender tests/mcp_bridge tests/tender`:
  passed.
- `uv run pytest tests/tender/test_flagship_speed_gate.py -m tender_eval -q -s`:
  passed on Windows with Java available.

Timing table from the Windows JVM run:

| stage | status | duration_ms | llm_calls | input_tokens | output_tokens | cache_hits |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| odl_extract:Enmore.pdf | done | 1579 | 0 | 0 | 0 | 0 |
| odl_extract:Kaposi.pdf | done | 1348 | 0 | 0 | 0 | 0 |
| odl_extract:NexusBuilt.pdf | done | 1525 | 0 | 0 | 0 | 0 |
| package_total | done | 4454 | 0 | 0 | 0 | 0 |

## Blockers

- WSL2 Ubuntu is running, but `java -version` fails because Java is not
  installed.
- `sudo -n true` fails in WSL, so Java cannot be installed non-interactively
  from this session.
- A clean Linux Docker build from `git archive` confirmed the previous
  `openjdk-17-jre-headless` package was unavailable and that the Dockerfile
  needed `default-jre-headless`. After that fix, the clean build still timed
  out after 15 minutes before producing an image.
- Because there is no runnable Linux/WSL2 backend with Java from this session,
  the full scripted chat acceptance run was not completed.

## Decision

Do not begin Phase 6 yet. Rerun the acceptance on a Linux environment with a
working JVM/backend image, then verify:

- Candidate tender PDFs are found from chat.
- Hermes starts the tender comparison through MCP.
- The worker drains the TCM pipeline.
- The comparison panel populates.
- A `tender_report` artefact card appears in chat.
- The timing ledger is attached to the run.
