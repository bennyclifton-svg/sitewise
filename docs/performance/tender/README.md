# Tender performance ledgers

Stage timing reports for the three-quote fixture (Enmore / Kaposi / NexusBuilt).
The ODL micro-benchmark and paid full-pipeline benchmark are deliberately
separate. An ODL result is never described as a full-pipeline result.

## How to generate

From `backend/`:

```bash
# Unit ledger shape (no PDFs / no network)
uv run pytest tests/tender/performance/test_full_pipeline_speed.py::test_full_pipeline_ledger_includes_nonzero_llm_stats -q

# Cold/warm ODL micro-benchmark + write markdown here
set TENDER_PERF_WRITE_REPORT=1
uv run pytest tests/tender/performance/test_full_pipeline_speed.py::test_three_quote_cold_warm_odl_micro_benchmark -m "integration and tender_eval" -q

# Paid full pipeline: atomic intake -> report-ready or QA-required.
# TEST_DATABASE_URL must name an already migrated disposable database.
set ALLOW_DESTRUCTIVE_TEST_DATABASE=1
set TENDER_LIVE_EVAL=1
set TENDER_PERF_SAMPLE_PAIRS=5
set TENDER_PERF_WRITE_REPORT=1
uv run pytest tests/tender/performance/test_full_pipeline_speed.py::test_three_quote_live_full_pipeline_cold_and_warm -m "integration and tender_eval" -q -s
```

Reports are named `{YYYY-MM-DD}-cold-odl.md` and `{YYYY-MM-DD}-warm-odl.md`.
The live harness writes `{YYYY-MM-DD}-full-pipeline.md`, with ten raw samples
(five cold/warm pairs), per-stage median/p95/population deviation, provider
usage, queue wait, and missing-stage failures. Set `TENDER_ENFORCE_90S=1` only
after the first provider-variance baseline has been reviewed; before that,
90 seconds is a measured stretch target, not a release gate.

## What a ledger must show

- Per-stage `duration_ms`
- Non-zero `llm_calls` / token counts for LLM stages (extract, map, silence, …)
- Mapping tier metadata when present (`tiers.t0` … `tiers.t3` and `*_ms`)
- Separate **cold** and **warm** runs
- Atomic-intake time and queue wait
- Classification, extraction, mapping, expectations, silence, analysis, flags,
  and report stages (report may be absent only at a typed QA-required terminal)

Progress API also exposes the same rows as `stage_timings` on
`GET /api/tender/comparisons/{id}/progress`.

## Optimization packets

Task 6.3 may start only from a checked-in live full-pipeline report with at
least ten samples. Rank the stage table by contribution and variance, then
write one packet per proven bottleneck with exact files, one allowed technique,
baseline, target, quality/eval commands, and rollback. Do not infer a
bottleneck from the ODL reports and do not change production behavior in the
measurement/decision packet.

No optimization packet is currently authorized: the live provider baseline
and variance report have not been run in this worktree.

## Customer quality gate

`data/tender/evaluation_release.yaml` is the machine-readable customer gate.
It remains blocked until the protected corpus validates, the paid evaluation
passes, a named QS approves the seed/rule/benchmark review, and the exact
prompt/model/taxonomy/report-language versions are frozen. Draft/internal
processing remains available; report approval and delivery return HTTP 409
while this gate is blocked.
