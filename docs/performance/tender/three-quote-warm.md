```json
{
  "fixture": "simple-three-tender",
  "generated_at": "2026-07-11T00:00:00+00:00",
  "mode": "warm",
  "note": "Synthetic S0 baseline until live runner lands; LLM counters non-zero.",
  "quotes": [
    "Enmore.pdf",
    "Kaposi.pdf",
    "NexusBuilt.pdf"
  ]
}
```

stage | status | duration_ms | llm_calls | input_tokens | output_tokens | cache_hits
--- | --- | ---: | ---: | ---: | ---: | ---:
ingest_document | done | 2000 | 0 | 0 | 0 | 0
classify_document | done | 6000 | 3 | 4500 | 300 | 0
extract_line_items | done | 5000 | 3 | 36000 | 9000 | 0
embed_items | done | 4000 | 3 | 12000 | 0 | 0
map_items | done | 120000 | 102 | 180000 | 24000 | 0
infer_silence_batch | done | 8000 | 1 | 8000 | 1500 | 0
package_total | done | 149000 | 112 | 240500 | 34800 | 0

## Stage metadata

```json
{
  "ingest_document": {
    "mode": "warm",
    "quotes": 3
  },
  "map_items": {
    "mode": "warm",
    "tier_counts": {
      "t0": 20,
      "t1": 40,
      "t2": 90,
      "t3": 12
    },
    "tier_durations_ms": {
      "t0": 200,
      "t1": 800,
      "t2": 180000,
      "t3": 59000
    }
  },
  "package_total": {
    "fixture_pdfs": [
      "Enmore.pdf",
      "Kaposi.pdf",
      "NexusBuilt.pdf"
    ],
    "mode": "warm",
    "quotes": 3
  }
}
```
