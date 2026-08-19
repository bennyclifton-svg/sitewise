# Verified Codebase Map

> Rewritten 2026-08-19 against HEAD after Stage 8B. Line numbers drift —
> **re-grep before trusting a line number**, but the file paths and shapes
> are correct.
>
> Read this once when you start a stage. It replaces exploration.
> Do not "fix" Stages 1–8 from facts that look surprising; they are current.

## One classifier (Gate 2)

**`backend/ingest/classify.py`** → `classify_entry(...) -> Classification`

Cascade: user override (Stage A) → structural signals → scored filename →
content markers. Vocabularies are frozen in `ingest/types.py` (`x1-gate-1`).

**`backend/app/intake/classifier.py`** → `filing_destination(Classification) -> str | None`

Routing only. It reads the canonical `Classification`; it does not classify.
`commercial_type` / `brief_kind` / `due_diligence` / `procurement_stage` are
consulted only when they match the current class (8B.1).

`classify_inbox_destination` remains as a classify-then-route shim.
**The only remaining production caller is `app/intake/repair_service.py`.**

## Facts a Wave 2 agent must not "discover" and fix

| Fact | Where |
|---|---|
| Content markers do **not** run on production ingest — `hosted.py` and `pipeline.py` call `classify_entry` without `extracted_text` | `ingest/hosted.py`, `ingest/pipeline.py` |
| `title_block` is never passed in production either | same |
| `machine_*` metadata keys are the classifier's own answer (8B.2) | `ingest/persist.py` |
| `document_type` is dead — do not read or write it (8B.5) | `app/database/source_document.py` column left in place |
| `ingest_mode` follows useful text, not class (8B.6) | `ingest/router.py` `has_useful_text`; persist corrects |
| `filing_destination` gates routing metadata on class (8B.1) | `app/intake/classifier.py` |
| `repair_service` is the only remaining `classify_inbox_destination` caller | `app/intake/repair_service.py` |
| Weak filename guesses score **0.55** and sit below the review gate **0.65** (`REVIEW_CONFIDENCE_MIN`) | `ingest/classify.py`, `ingest/router.py` |

## Where evidence gets indexed

`backend/ingest/router.py`:

```python
USEFUL_TEXT_MIN_CHARS = 200
REVIEW_CONFIDENCE_MIN = 0.65

def has_useful_text(text: str | None) -> bool:
    return bool(text) and len(text.strip()) >= USEFUL_TEXT_MIN_CHARS

def should_persist_chunks(plan, *, extracted_text) -> bool:
    if plan.extractor == "unsupported":
        return False
    return has_useful_text(extracted_text)
```

Class never decides whether text is indexed (D3). Drawings with useful text
are chunked by `chunk_register` (bounded) and embedded.

## Canonical `DocumentClass` (frozen at Gate 1)

`backend/ingest/types.py`:

```text
drawing specification report certificate correspondence contract
commercial schedule statutory_instrument photo unknown
```

Subject, basis, and the review threshold are served from the same contract
(`frontend/src/lib/classification.ts` + `tests/ingest/test_classification_contract.py`).

## Persistence

`backend/app/database/source_document.py`:

```python
document_class: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
ingest_mode:    Mapped[str | None] = mapped_column(String(32))
document_metadata: Mapped[dict | None] = mapped_column(JSONB)
content_hash:   Mapped[str | None] = mapped_column(String(64))
document_type:  Mapped[str | None] = mapped_column(String(128))  # dead column (8B.5)
```

**`document_class` is `String(64)`, not a Postgres enum.**

`document_metadata` holds `subject`, `basis`, `confidence`, routing extras, and
`machine_class` / `machine_subject` / `machine_confidence` / `machine_basis`
(written once, never overwritten).

## Sort Files path

```text
frontend ProjectCockpitPage.tsx
  → POST sort-files
  → app/workflows/sort_files.py run_sort_files_workflow
  → app/intake/sort_service.py sort_inbox_files
```

Also auto-invoked post-ingest: `app/workflows/document_ingest.py`.

Outcomes include `waiting` and `needs-review`. Filing **moves storage and
updates `relative_path`**; it does not re-extract, re-embed, or re-classify
(8B.11). Sort Files does not call `_file_previews`. `repair_service` still does.

## Invoice code that already exists

`backend/app/cost_plan/`: `invoice_extraction.py`, `invoice_mapping.py`,
`invoice_service.py`, `invoice_candidates.py`, `evidence_reconciliation.py`,
`calculations.py`, `models.py`, `schemas.py`.

Stages 10–12 **extend** these. Adding an `invoice/` package is a D8 violation.

## Consumers of classification (rebuild from grep, 2026-08-19)

Not just `document_class`. Include JSONB subject/discipline/`commercial_type`,
`machine_*` keys, and the dead `document_type` column so nobody revives it.

```text
backend/ingest/classify.py              writer
backend/ingest/persist.py               writer (class, metadata, machine_*, ingest_mode)
backend/ingest/hosted.py                override merge onto machine classification
backend/ingest/router.py                chunker by class; ingest_mode from text
backend/ingest/chunkers/register.py     drawing chunker
backend/ingest/chunkers/schedule.py     schedule row chunker (9.2)
backend/app/intake/classifier.py        filing_destination (class-gated metadata)
backend/app/intake/sort_service.py      persisted Classification; path move
backend/app/intake/repair_service.py    last classify_inbox_destination caller
backend/app/projects/classification_override.py  user override (preserves observation)
backend/app/database/source_document.py document_class + dead document_type column
backend/app/database/document_classification_override.py
backend/app/api/projects.py             evidence preview; classification PUT
backend/app/retrieval/queries.py        filter by class / procurement_stage
backend/app/retrieval/schemas.py        RetrievalFilters
backend/app/retrieval/register.py       drawing register == "drawing"
backend/app/retrieval/inventory.py      display
backend/app/retrieval/catalog.py        synthetic schedule rows
backend/app/projects/document_register.py
backend/app/projects/consultant_facts.py
backend/app/projects/identity_bootstrap.py
backend/app/cost_plan/consultant_appointment.py
backend/app/mcp_bridge/server.py        set_document_classification (mutation turn)
backend/app/web_research/attachments.py statutory_instrument writer
backend/app/agent/document_context.py   title from metadata, not document_type
backend/app/assistant/agent.py          search_documents filters
backend/app/sitewise/pmp_sweep.py       evidence selection
backend/app/grounding/validator.py
backend/app/workflows/procurement_register.py
backend/frontend/src/lib/classification.ts  frozen vocab + REVIEW_CONFIDENCE_MIN
```

`source_documents.document_type` is **not** a consumer. Do not read or write it.

## Commands (use these exactly)

```bash
# Backend — run from backend/
uv run pytest -q --tb=line --import-mode=importlib
uv run ruff check .
uv run alembic upgrade head

# Frontend — run from frontend/, pnpm only
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

Exact `uv run pytest -q` cannot collect (duplicate test basenames). Compare
against `docs/acceptance/x1/baseline-backend-failures.txt`.
