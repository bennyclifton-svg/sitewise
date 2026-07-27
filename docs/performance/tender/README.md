# Tender Comparison speed ledgers

Sprint S0 baseline reports for the three-quote fixture package
(`Enmore.pdf`, `Kaposi.pdf`, `NexusBuilt.pdf` under
`backend/tests/tender/fixtures/`).

| File | Mode | Notes |
| --- | --- | --- |
| `three-quote-cold.md` | cold | First-pass ingest + extract + map |
| `three-quote-warm.md` | warm | Re-compare with files already ingested |

Until the live full-pipeline runner lands (`TENDER_FULL_PIPELINE_LIVE=1`), these
ledgers are synthetic S0 baselines with non-zero LLM counters so optimisation
work has a fixed format to beat. Replace them with measured runs from
`list_stage_timings` / progress `stage_timings` once instrumentation is exercised
on a real comparison.
