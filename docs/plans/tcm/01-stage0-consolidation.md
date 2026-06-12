# Stage 0 — Consolidate the TCM codebase onto one branch

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** All TCM work (M0–M2) lives, committed and green, on a single branch `feature/tcm-main`; the duplicate `models.py` is reconciled; the untracked working-tree files are gone from the cost-plan branch.

**Why this exists:** M1 was built on `feature/tcm-m1-skeleton` (worktree `.worktrees/tcm-m1`, 11 commits). M0/M2 (seeds, loaders, LLM client, extraction, eval) were built later as **untracked files** in the main working tree, with a second, smaller `models.py`/`schemas.py` that conflict with the branch's committed ones. Nothing from M0/M2 is committed anywhere.

**Architecture decision (made; do not relitigate):** the M1 branch is the base — its `models.py` is the canonical §8 data model and its migrations are the canonical chain. The working tree contributes everything that does not exist on the branch, plus one additive migration.

---

## Reconciliation rules

| Artifact | Keep | Discard / transform |
| --- | --- | --- |
| `backend/tender/models.py` | M1 branch version (19 tables) | Working-tree version (5 tables) — but **port `ReportLanguageEntry`** (the `report_language` table) into the branch version; it exists nowhere else |
| `backend/tender/schemas.py` | M1 branch version as base | Diff the two; port any classes the working-tree version adds that `llm/`, `services/extraction.py`, `eval/` import (`TenderDocumentPage` at minimum). Imports in ported code must keep working |
| Migrations 007–010 | M1 branch, untouched | — |
| New migration 011 | Create: `report_language` table matching `ReportLanguageEntry` (key_path unique, JSONB value, version, updated_at) | — |
| `backend/tender/llm/`, `services/extraction.py`, `eval/`, `seeds/load.py` | Working tree, verbatim | M1 branch has no equivalents (its `seeds/__init__.py` is empty scaffold) |
| `backend/tender/services/ingestion.py`, `services/jobs.py`, `worker.py` | M1 branch | Working tree has none |
| `backend/tests/tender/*` | Union of both sets (filenames do not collide: branch has jobs/worker/migrations/models/schemas tests; tree has eval/extraction/seed/openai tests) | — |
| `data/tender/**` | Working tree, verbatim (committed for the first time) | — |
| AGENTS.md TCM section | Working tree (uncommitted edit from Prompt 0) | Commit it on `feature/tcm-main` too |
| `backend/tender/llm/prompts/extract_line_items_v0.1.0.md` | Working tree | Branch has only `.gitkeep` |

**Do not copy `__pycache__` directories.**

## Tasks

### Task 1: Create the branch

```bash
git checkout -b feature/tcm-main feature/tcm-m1-skeleton
```

Work happens in a fresh checkout of this branch. Recommended: a new worktree (`git worktree add .worktrees/tcm-main feature/tcm-main`) so the cost-plan working tree is untouched until cleanup.

### Task 2: Bring over the working-tree files

Copy from the main working tree into the new branch checkout (paths relative to repo root):

- `data/tender/` (all files)
- `backend/tender/llm/` (client.py, openai_client.py, prompts/)
- `backend/tender/services/extraction.py`
- `backend/tender/eval/`
- `backend/tender/seeds/load.py`
- `backend/tests/tender/test_eval_*.py`, `test_extraction_*.py`, `test_openai_client.py`, `test_seed_*.py`

Do **not** copy `backend/tender/models.py` or `backend/tender/schemas.py`.

Commit: `chore(tender): import M0/M2 work onto consolidated branch`

### Task 3: Reconcile models

1. Open the working tree's old `models.py` (from the cost-plan checkout) and port `ReportLanguageEntry` (with its `key_path` unique constraint) into the branch's `models.py`. Match the branch file's existing style (it uses the same `Mapped`/`mapped_column` idiom).
2. Run the model tests: `uv run pytest backend/tests/tender/test_models.py -q` — expect failures only if the seed-loader tests reference `report_language` before migration 011 exists; note them.

Commit: `feat(tender): add report_language model to canonical data model`

### Task 4: Reconcile schemas

Diff working-tree `schemas.py` (125 lines) against branch `schemas.py`. Port additive classes only (whatever `llm/client.py`, `extraction.py`, `eval/` import — at minimum `TenderDocumentPage`). Fix any import breakage in the ported modules; do not restructure them.

Verify: `uv run pytest backend/tests/tender -q` collects with zero import errors (failures about missing migration are still OK at this step).

Commit: `feat(tender): merge intake and extraction schemas`

### Task 5: Migration 011

Create `backend/alembic/versions/011_tender_report_language.py` following the exact style of 008 (same author conventions, up/down both implemented). Table per `ReportLanguageEntry`.

Add it to the migration-chain test (`backend/tests/tender/test_migrations.py` already checks the chain — extend it).

Verify (needs the local DB):
```bash
uv run alembic upgrade head
uv run alembic downgrade 010
uv run alembic upgrade head
```

Commit: `feat(tender): migration 011 report_language`

### Task 6: Full green run

```bash
uv run pytest backend/tests/tender -q
uv run python -m tender.seeds.load        # adjust module path to whatever load.py's __main__ expects
uv run python -m tender.seeds.load        # second run must report zero changes (idempotency)
python data/tender/tools/validate.py
```

If the seed loader's module path differs (check `load.py` `main()` and how tests invoke it), record the **actual working commands** at the bottom of `docs/plans/tcm/00-handoff-overview.md` under a new "Verified local commands" heading.

Commit: `chore(tender): consolidated branch green`

### Task 7: Audit ingestion completeness (report only — no code)

PRD §7.4 requires: text-layer detection, ocrmypdf fallback, 150-DPI PNG per page, XLSX/DOCX conversion, `manual_transcription_required` escape hatch. The branch's `services/ingestion.py` is suspected to be a stub. Read it and `worker.py`, then append an honest gap list to this file under "## Ingestion audit findings". If gaps exist, they are **Stage 0.5** — scope it as a short follow-on session before M3 (mapping consumes line items, and line items come from extraction over ingested pages; M3 can proceed in parallel with synthetic fixtures, but real-document checkpoint in M3 needs ingestion working).

### Task 8: Clean the cost-plan working tree

In the original working tree (`feature/cost-plan-quality-fixes`), after confirming everything is committed on `feature/tcm-main`:

```bash
git status --porcelain -- backend/tender backend/tests/tender data/tender
```

Confirm the consolidated branch has every file (`git diff --stat feature/tcm-main -- <paths>` empty for these paths), **then and only then** delete the untracked copies. Get explicit user confirmation before deleting. Leave the AGENTS.md edit in place on the cost-plan branch (it belongs in both).

## Exit criteria

- [ ] `feature/tcm-main` exists; `backend/tests/tender` fully green on it (output pasted)
- [ ] Migration roundtrip 011↔010 verified (output pasted)
- [ ] Seed load twice = zero changes (output pasted)
- [ ] Ingestion audit findings appended to this doc
- [ ] Working tree clean of untracked tender files
- [ ] "Verified local commands" recorded in `00-handoff-overview.md`

## Ingestion audit findings (2026-06-13)

`backend/tender/services/ingestion.py` is a **pure stub**: one function,
`ingest_document(session, job)`, whose body is
`raise NotImplementedError("ingest_document lands in the next commit")`. Nothing
from PRD §7.4 is implemented:

| PRD §7.4 requirement | Status |
| --- | --- |
| Text-layer detection (density threshold) | Missing — config key `tender_ocr_text_density_threshold` exists, unused |
| ocrmypdf fallback for image-only PDFs | Missing — `tender_ocr_enabled` / `tender_ocr_min_confidence` exist, unused |
| 150-DPI PNG render per page | Missing — `tender_page_render_dpi` exists, unused |
| XLSX/DOCX → normalised input | Missing |
| `manual_transcription_required` escape hatch | Missing |
| Writing `tender_pages` rows / updating `tender_documents.ingest_status` | Missing |

What **does** exist and is sound:

- `worker.py` is complete (SKIP LOCKED claim, handler registry, stale-lock sweep,
  graceful shutdown) and already registers `ingest_document` as the only handler —
  the stub raising means any enqueued `ingest_document` job fails cleanly through
  `jobs.fail` with attempts/backoff.
- `services/extraction.py` (M2) is real — reconciliation + confidence gating — but
  takes `TenderDocumentPage` inputs that today only synthetic fixtures produce, and
  no job kind is registered for extraction either.

**Verdict: the gap is real → Stage 0.5 is required.** Scope: implement
`ingest_document` end-to-end (text-layer detection, ocrmypdf fallback, per-page
150-DPI PNG, XLSX/DOCX conversion, `manual_transcription_required` escape hatch,
`tender_pages` persistence + `ingest_status` transitions) plus an
`extract_quote`-style handler wiring extraction into the worker. M3 (mapping) can
start in parallel on synthetic fixtures, but the real-document checkpoint in M3
blocks on Stage 0.5.
