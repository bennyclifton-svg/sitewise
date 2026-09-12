# Workbook save and export performance

## Changes

Cost-plan workbook construction now runs in a worker thread. The builder receives plain state and invoice data; the database session remains on the event loop. This prevents XLSX construction from blocking other requests handled by the same API process.

Workspace-file upserts return the saved ORM row directly rather than returning its ID and reading it again. `populate_existing` refreshes an already-loaded row after a conflict update. This also applies to other callers of the shared workspace registration function.

Export completion by revision/path now updates the row and returns it in one statement. Attempt counting is performed in the database. Completion/failure events retain their prior payload and deduplication key; a missing export still produces no completion event. Publication stays in the caller's transaction and is still after the storage upload.

No schema, dependency, deployment or commit changes.

## Controlled before/after profile

The harness uses Cost Plan v2 from the isolated Seven Hills benchmark, invokes the actual workbook persistence path, suppresses storage upload, and rolls back all database writes. It records SQL counts without SQL parameters. Each sample runs in a fresh Python process against the same remote database.

| Stage | Before | After | SQL queries before / after |
| --- | ---: | ---: | ---: |
| Invoice read | 0.301 s | 0.303 s | 1 / 1 |
| Workbook construction | 0.814 s | 0.868 s | 0 / 0 |
| Workspace registration | 0.650 s | 0.307 s | 2 / 1 |
| Export status and event | 1.825 s | 1.513 s | 6 / 5 |
| Total excluding upload and setup | 3.591 s | 2.991 s | 9 / 7 |

The controlled path improved by about 0.60 seconds (17%). Two fewer SQL round trips are the deterministic result. Single wall-clock samples do not establish typical latency or a percentile. Workbook construction is not faster; it no longer blocks the event loop. Network upload and full workflow timing are outside this comparison.

Harness: `output/performance-review/profile_workbook_persistence.py`. Raw results: `workbook-persistence-before.json` and `workbook-persistence-after.json` in that directory.

## Validation

- The event-loop responsiveness test failed before the change: another coroutine could not release the workbook builder until it had timed out. It now passes, showing progress while construction is still running.
- Query-budget tests failed before the change and now pass. Export tests cover ready, failed and missing-job outcomes and event attempt numbering.
- Six targeted tests and 83 related tests passed (89 total). Related coverage includes workbook rebuilds, invoice schedules, Seven Hills cost values, workflow persistence, project events, attachment intake and uploads. Ruff and whitespace checks passed.
- Before/after profiling exercised real Postgres writes, all rolled back, with no storage uploads.

The broader lifecycle findings in `2026-09-09-performance-lifecycle-run.md` remain separate. This change does not resolve RFP budget propagation or the remaining appointment, PMP and invoice acceptance stages.

## Live save and download

Restarted the local backend with the tested changes and regenerated the disposable benchmark Cost Plan once through Pi. Revision 3 (`cfd2af28-22f2-4f40-97ab-6d9e46d4654a`) completed. Read-only assertions confirmed identical cost values, commitment values, allowance types and source references between v2 and v3; revisions 1–3 remain present. All three workbook exports are ready and their hashes match their workspace-file records.

The v3 Excel download returned HTTP 200 in about 2.5 seconds. This checks availability; it is not a new workbook cell/layout review.

| Live workflow stage | Previous v2 | New v3 |
| --- | ---: | ---: |
| Draft save | 7.921 s | 7.925 s |
| Workbook export | 7.692 s | 3.889 s |
| Started to complete | 39.432 s | 36.075 s |
| Created to complete | 51.696 s | 46.246 s |

These live runs include network, scheduling and cache variation. Do not attribute their entire difference to the code change; the controlled profile isolates the two eliminated round trips. Draft-save time was essentially unchanged and remains a separate profiling target.

Evidence: `output/performance-review/workbook-performance-live-verified.json`, produced by the read-only `verify_workbook_performance.py` harness. The local API is running on port 8000 without auto-reload. No production deployment was performed.
