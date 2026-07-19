# Stage 0 baseline — 2026-07-19

Environment: [canonical performance environment](environment.md).

## Offline checks

| Check | Result | Wall time |
| --- | ---: | ---: |
| Backend default test lane (final) | 1,071 passed, 3 skipped, 15 deselected | 187.12 s |
| Frontend tests | 29 files / 93 tests passed | 25.01 s |
| Backend Ruff | passed | 0.5 s |
| Frontend ESLint | 0 errors; 1 existing TanStack Virtual compatibility warning | 20.9 s |
| Targeted Stage 0/1 regression set | 44 passed | 20.79 s |
| Windows parent/descendant cancellation | 2 passed; zero surviving processes | 1.82 s |

Integration tests remain opt-in and require a dedicated database. The baseline
discovery run exposed one stale Tender manifest assertion after the speed-path
commit; it was corrected before the final green result above.

## Frontend production bundle

Report-only measurement from `npm run measure:bundle` after a production build:

| Initial entry | Raw | Gzip |
| --- | ---: | ---: |
| `/assets/index-CpGvMcCo.js` | 1,720,350 bytes | 460,568 bytes |

This does not enforce the later Phase 5 budget. The current gzip size is above
the future 250 kB target and is intentionally retained as the honest baseline.

## Runtime and workflow timing contract

Agent stream logs now correlate request, user, project, thread, durable turn,
runtime, and model, and report numeric authorization, quota, prompt-build,
first-text, and total timings. Logs record lengths and error types rather than
prompt, response, or tool content.

Current synchronous Project Plan, Cost Plan, and Sort Files traces expose
numeric durations for retrieval/inspection, generation, draft persistence, and
workbook export where applicable. Provider-backed raw latency samples were not
run because this checkout has no approved smoke-test credentials or fixture.

## Known gaps

- Disposable PostgreSQL acceptance now passes for migration roundtrip,
  expand/repair/contract, historical citations, ingestion idempotency, duplicate
  rules, quota and revocation races, restart persistence, and two-owner read
  isolation. Production audit, rollout, backup restore, and rollback rehearsal
  remain unperformed.
- Hermes Agent v0.17.0 ACP is a supported non-argv candidate, but two INFO logs
  include the prompt prefix. A minimized probe traced the apparent non-terminal
  turn to the Windows ACP coding-workspace `git status` probe: `/help` completed
  in about 4 seconds, the normal model turn exceeded 180 seconds, and bypassing
  only that upstream probe completed the model turn in 6.91 seconds. Hermes
  mutations remain disabled.
- Linux Docker process-tree validation passes all eight tests, including
  success, failure, timeout, disconnect, stop, cancellation, and SIGTERM-resistant
  descendants.

## Continuation validation

| Check | Result | Wall time |
| --- | ---: | ---: |
| Backend default lane | 1,088 passed, 6 skipped, 16 deselected | 198.03 s |
| Disposable PostgreSQL Stage 0/1 acceptance against head `024_tender_quote_total_source` | 1 passed | 7.36 s |
| Disposable PostgreSQL migration roundtrip against head `024_tender_quote_total_source` | 1 passed | 3.00 s |
| Linux process-tree suite | 8 passed | 2.63 s |
| Frontend tests | 29 files / 93 tests passed | 21.77 s |
| Frontend lint | 0 errors; 1 existing warning | combined lane |
| Frontend build and bundle measurement | passed; 1,720,350 raw / 460,568 gzip | 46.4 s combined lane |
