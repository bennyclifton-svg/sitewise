# Tender Stage 7 quality gate

Recorded: 2026-07-19 (Australia/Sydney)

Status: **blocked for customer approval, delivery, and downstream handoff**.
Internal atomic intake, processing, QA, and draft generation remain available.

## Implemented contracts

- Real TCM LLM calls record model, prompt version, provider request ID, token
  usage, cached input, and observable retry count in the worker stage ledger.
- Worker telemetry records queue wait, stage duration, retry attempt, and safe
  comparison/job/quote/document/report correlation. Prompt text, document text,
  and exception messages are excluded.
- The ODL micro-benchmark remains separate from the live full-pipeline harness.
- The paid harness begins before atomic intake, drains the actual worker chain,
  ends at report-ready or QA-required, and records cold/warm stage contribution
  and variance for Enmore/Kaposi/NexusBuilt.
- Static report labels and flag phrases come from
  `data/tender/report_language.yaml`; unapproved stored flag headlines are not
  rendered as customer copy.
- `data/tender/evaluation_release.yaml` blocks approval/delivery until corpus,
  evaluation, QS review, and frozen-version evidence all pass.

## Validation performed

`uv run ruff check tender tests/tender` from `backend/`:

```text
All checks passed!
```

`uv run pytest` from `backend/` with required test-only settings:

```text
1174 passed, 6 skipped, 23 deselected, 3 warnings in 31.04s
```

The three warnings are the existing pytest assertion-rewrite warning and two
unawaited `AsyncMock` warnings outside this packet's changes.

`python data/tender/tools/validate.py`:

```text
OK: 180 cells | 70 rules | 2580 synonyms (0 uncovered cells) | 188 benchmark rows | 3 golden documents | taxonomy bk coverage complete
```

`python data/tender/tools/validate.py --golden-release-gate` exits 1 as designed.
The blocking facts are:

- 3 real documents exist; at least 30 are required;
- 0 synthetic adversarial documents exist; at least 20 are required;
- all three real fixtures are marked `anonymised: false`;
- consent, protected-storage, provenance, and retention records are absent;
- VIC/QLD, new-build/addition, easy difficulty, multiple formats, all named
  adversarial cases, and all five silence classes are not covered;
- corpus access/redaction review is not approved.

## Evidence not performed or claimed

- No paid live-provider full-pipeline run was made. No cold/warm baseline,
  provider variance, 90-second stretch result, or five-quote result is claimed.
- No optimization packet is authorized because there is no measured live
  bottleneck ledger.
- No prompt/model/taxonomy evaluation pass is claimed.
- No QS review is claimed and no reviewer identity is fabricated.
- No customer rollout or rollback rehearsal was performed.

## Exact commands required to advance

From `backend/`, against an already migrated disposable PostgreSQL database:

```powershell
$env:ALLOW_DESTRUCTIVE_TEST_DATABASE='1'
$env:TENDER_LIVE_EVAL='1'
$env:TENDER_PERF_SAMPLE_PAIRS='5'
$env:TENDER_PERF_WRITE_REPORT='1'
uv run pytest tests/tender/performance/test_full_pipeline_speed.py::test_three_quote_live_full_pipeline_cold_and_warm -m "integration and tender_eval" -q -s
```

After protected corpus acquisition/redaction/annotation and access review:

```powershell
python data/tender/tools/validate.py --golden-release-gate
uv run pytest -m tender_eval -q
```

Only after those results and the named QS report are attached may
`evaluation_release.yaml` be changed to `status: approved` with exact frozen
model versions and report references.
