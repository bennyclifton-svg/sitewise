# TCM Stage 0.5 — Ingestion, Classification & Extraction Wiring

Handoff issue set for the TCM (Tender Comparison Module) Stage 0.5 work. These
implement the per-quote **front half** of the pipeline so an uploaded quote
flows `ingest_document → classify_document → extract_line_items → embed_items`
with no manual button clicks.

**Source of truth (full code, rationale, design decisions):**
[docs/plans/2026-06-13-tcm-stage0.5-ingestion-classification.md](../../plans/2026-06-13-tcm-stage0.5-ingestion-classification.md)

## Background

The TCM worker (`backend/tender/worker.py`) is a poll-loop over the `tender_jobs`
table. Each stage is an `async def handler(session, job, *, deps=None)` registered
in `worker.HANDLERS`. Today `ingest_document` is a stub that raises
`NotImplementedError`, and `classify_document` / `extract_line_items` are not
registered at all — so uploaded quotes fail every job. These issues close that gap.

**Do NOT reuse Clerk's `backend/ingest/` RAG pipeline.** It has no OCR and no page
rendering — it chunks text for chat retrieval. TCM needs page images + per-page
text for schema-oriented vision extraction (PRD §7.1, line 154). Share only the
upload/storage layer (`app.storage.project_files`).

## Issues and dependency order

Implement in this order (each blocked by the previous unless noted):

| # | Title | Type | Blocked by |
|---|-------|------|-----------|
| TCM05-001 | Dependencies and preflight | AFK | none |
| TCM05-002 | PDF text extraction + OCR-candidate detection | AFK | 001 |
| TCM05-003 | 150-DPI page render to PNG | AFK | 002 |
| TCM05-004 | `ingest_document` handler | AFK | 003 |
| TCM05-005 | `classify_document` handler + prompt | AFK | 006 (context helper) |
| TCM05-006 | `extract_line_items` handler + shared context loader | AFK | 003 |
| TCM05-007 | Register handlers + auto-chain front half | AFK | 004, 005, 006 |
| TCM05-008 | Manual real-document verification | HITL | 007 |
| TCM05-009 | XLSX/DOCX conversion (optional) | HITL | 004 |

> 005 depends on 006 only because 006 creates the shared `tender/services/context.py`
> helper that 005 imports. If you prefer, do 006 before 005, or inline the helper in
> 005 temporarily (see TCM05-005).

## Conventions every issue follows

- **TDD, repo style.** Write the failing test first; mock session/storage/LLM; no
  network in unit tests. Reuse the existing async DB fixture used by
  `backend/tests/tender/test_jobs.py` / `test_map_items_handler.py` (match its name).
- **Handler signature:** `async def handler(session, job, *, deps=None) -> None`,
  idempotent, with external dependencies (storage/OCR/LLM) injected and defaulting to
  the real implementations.
- **Run from `backend/`:** `cd backend && uv run pytest ...` and `uv run ruff check tender`.
- **No Alembic migration** is required for 001–008 (every column already exists).
- End commit messages with the repo's `Co-Authored-By` trailer.

## Definition of done (whole set)

- `uv run pytest tests/tender -q` fully green; `uv run ruff check tender` clean.
- Worker registers all ten handlers; the front half auto-chains.
- Manual runbook (TCM05-008) passes on the three pilot PDFs; results recorded in
  [docs/plans/tcm/01-stage0-consolidation.md](../../plans/tcm/01-stage0-consolidation.md).
