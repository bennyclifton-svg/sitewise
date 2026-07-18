# Tender performance ledgers

Stage timing reports for the three-quote fixture (Enmore / Kaposi / NexusBuilt).

## How to generate

From `backend/`:

```bash
# Unit ledger shape (no PDFs / no network)
uv run pytest tests/tender/performance/test_full_pipeline_speed.py::test_full_pipeline_ledger_includes_nonzero_llm_stats -q

# Cold/warm ODL package + write markdown here
set TENDER_PERF_WRITE_REPORT=1
uv run pytest tests/tender/performance/test_full_pipeline_speed.py::test_three_quote_cold_warm_odl_stage_ledger -m "integration and tender_eval" -q
```

Reports are named `{YYYY-MM-DD}-cold-odl.md` and `{YYYY-MM-DD}-warm-odl.md`.

## What a ledger must show

- Per-stage `duration_ms`
- Non-zero `llm_calls` / token counts for LLM stages (extract, map, silence, …)
- Mapping tier metadata when present (`tiers.t0` … `tiers.t3` and `*_ms`)
- Separate **cold** and **warm** runs

Progress API also exposes the same rows as `stage_timings` on
`GET /api/tender/comparisons/{id}/progress`.
