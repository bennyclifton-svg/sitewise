# Data

This directory holds checked-in SiteWise reference data, workflow contracts,
Tender Comparison seed data, templates, and lightweight fixtures. Large project
payloads are intentionally not part of the active repo context unless a test
fixture explicitly needs them.

## Current Tree

| Path | Purpose |
| --- | --- |
| `seed/` | SiteWise reference guides used as platform knowledge. |
| `skills/` | Reusable SiteWise workflow contracts and shared PM rules. |
| `tender/` | Tender Comparison taxonomy, expectations, synonyms, benchmarks, report language, and validation tools. |
| `project-template/` | Default SiteWise project folder/template material. |
| `synthetic-mobilisation-evidence/` | Small synthetic evidence packs for mobilisation/PMP workflow checks. |
| `download.py` | Historical/local corpus helper. Do not treat it as product runtime. |

The old large local corpus folders are gitignored and are not assumed to exist
in a fresh checkout.

## Tender Seed Data

`data/tender/` is governed by the TCM PRD:

- `taxonomy.yaml`
- `expectations.yaml`
- `synonyms.base.csv`
- `synonyms.seed.csv`
- `benchmarks.seed.csv`
- `concepts.yaml`
- `report_language.yaml`
- `golden/`
- `tools/validate.py`

Run the validator from the repo root:

```bash
python data/tender/tools/validate.py
```

Report language for customer-facing TCM output must come from
`data/tender/report_language.yaml`.

## Skills And Doctrine

`data/skills/` contains workflow contracts. Clerk implements those contracts;
the files are not a parallel runtime. Existing PMP/cost workflows may still use
these until the Hermes-driven workflow pattern supersedes them.

`data/seed/` contains reference guides. Treat them as platform knowledge, not
project evidence.

## Project Templates

`data/project-template/` describes the folder-shaped SiteWise mental model that
Clerk exposes in the app. Canonical uploaded source files live in Supabase
Storage, with `workspace_files` rows mapping workspace paths to storage keys.

## Synthetic Evidence

`data/synthetic-mobilisation-evidence/` is lightweight, checked-in material for
workflow and UI verification. It is safe for agents to use in tests and manual
smoke checks.

## Git And Payloads

Do not commit large customer/project document payloads unless they are deliberate
small fixtures. The active product path stores uploads in Supabase Storage, not
in this repo.

