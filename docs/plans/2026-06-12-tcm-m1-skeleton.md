# TCM M1 — Skeleton Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver PRD §19 milestone M1: the `backend/tender/` module scaffold, Alembic migrations for the full §8 data model, the `tender_jobs` worker loop (FOR UPDATE SKIP LOCKED), and document ingestion (storage registration, page rendering, OCR detection per §7.4) — verified against real documents.

**Architecture:** A new `tender` package lives beside `app`/`ingest` under `backend/`, owning all `tender_*` + knowledge tables. It imports Clerk's `Base`, settings, session factory, and Supabase storage helpers; nothing in `app/` imports `tender/` except the composition root (`app/main.py` mounts the router) and `alembic/env.py` (metadata registration). Jobs are rows in `tender_jobs`; a separate worker process polls with `SELECT … FOR UPDATE SKIP LOCKED`.

**Tech Stack:** FastAPI, SQLAlchemy 2 async (psycopg3), Alembic (handwritten migrations, repo convention), PyMuPDF (text-layer detection + 150 DPI PNG render), ocrmypdf/Tesseract (OCR), Supabase Storage, pgvector.

**PRD:** `docs/plans/2026-06-11-tender-comparison-module-prd.md` §§7–9, 19.

---

## Decisions & deviations (approve these explicitly)

1. **Module path / worker command.** PRD §7.1 says `backend/tender/` with `python -m backend.tender.worker`. The repo's import root is `backend/` (packages `app`, `ingest`), so the package is `backend/tender/` imported as `tender.*`, and the worker command is `python -m tender.worker` (run from `/app/backend` in the container, same as uvicorn today). Added to `[tool.hatch.build.targets.wheel] packages`.
2. **Enums as `String` + CHECK constraints, not native PG enums.** Repo idiom everywhere (`status: String(64)`); native enums make every later value addition a migration. Allowed values enforced by `CheckConstraint` in the migrations and `Literal` types in Pydantic schemas.
3. **`tender_reports.draft_id` FKs to `draft_artifacts.id`.** The PRD says `drafts`; the repo's actual table is `draft_artifacts`. (Table is created in migration 009 now; the report stage itself is M5.)
4. **`tender_documents.content_hash` column added.** §8.3 doesn't list it but §9.1 requires hash dedupe. Unique per quote: `UNIQUE (quote_id, content_hash)`.
5. **XLSX/DOCX ingestion deferred to M2.** §7.4's LibreOffice conversion path is heavy and M1's exit criterion is "ingest/OCR/page-render running on real docs" (which are PDFs). Non-PDF uploads are accepted, registered, and marked `ingest_status='unsupported_format'` with a clear error — no silent drops.
6. **OCR application is config-gated.** Detection (per-page text density via PyMuPDF) always runs and is unit-testable anywhere. Applying OCR shells out to `ocrmypdf` and requires Tesseract+Ghostscript (added to the runtime Dockerfile). `TENDER_OCR_ENABLED=false` on dev machines without Tesseract: low-text pages keep `text_content=''`, `ocr_applied=false`, warning logged. The §7.4 escape hatch (`manual_transcription_required`) is set when OCR ran but mean confidence < threshold.
7. **Minimal intake API included in M1.** The PRD's M1 exit criterion requires real docs flowing; that needs `POST /api/tender/comparisons`, `POST …/quotes`, `POST …/quotes/{id}/documents` (multipart upload → storage + row + enqueue), and `GET /api/tender/comparisons/{id}` (status poll). The rest of §15 comes later.
8. **Stale-lock recovery.** Not in the PRD, but a crashed worker would otherwise strand jobs in `running` forever. Each poll cycle requeues jobs `running` with `locked_at < now() - interval '10 minutes'` (config key).
9. **Empty `embedding` column now.** `tender_line_items.embedding vector(1536)` is created in migration 007 (extension already exists from 001) but stays null until M2/M3. `pg_trgm` extension + trigram index on `taxonomy_synonyms.phrase_norm` created now (used by T0 in M3) — extensions are cheap, re-migrating indexes later is churn.

---

## Files created / modified (complete list)

**New package:**

```
backend/tender/__init__.py
backend/tender/models.py            # all SQLAlchemy models (tender_* + knowledge + eval tables)
backend/tender/schemas.py           # Pydantic: ProjectContext (versioned), API I/O models
backend/tender/router.py            # APIRouter mounted at /api/tender (minimal intake surface)
backend/tender/worker.py            # poll loop, handler registry, shutdown, stale-lock sweep
backend/tender/services/__init__.py
backend/tender/services/jobs.py     # enqueue / claim (SKIP LOCKED) / complete / fail+backoff
backend/tender/services/ingestion.py# hash, storage registration, render, OCR detect/apply, tender_pages
backend/tender/llm/__init__.py      # empty scaffold (client lands M2)
backend/tender/llm/prompts/.gitkeep
backend/tender/seeds/__init__.py    # empty scaffold (loaders land alongside mapping, M3)
```

**New migrations (in chain order):**

```
backend/alembic/versions/007_tender_core.py
backend/alembic/versions/008_tender_knowledge.py
backend/alembic/versions/009_tender_mapping_status.py
backend/alembic/versions/010_tender_jobs_eval.py
```

**New tests:**

```
backend/tests/tender/__init__.py
backend/tests/tender/conftest.py            # fixtures: synthetic PDFs (text page / image-only page), mock session
backend/tests/tender/test_models.py         # mapper registration, table args sanity
backend/tests/tender/test_schemas.py        # ProjectContext validation
backend/tests/tender/test_jobs.py           # claim query shape, backoff math, attempt exhaustion
backend/tests/tender/test_worker.py         # registry dispatch, error → fail path, shutdown
backend/tests/tender/test_ingestion.py      # hash/dedupe, text-density detection, render, checkpoint resume
backend/tests/tender/test_router.py         # intake endpoints with mocked session/storage (repo test style)
backend/tests/tender/test_worker_integration.py  # @pytest.mark.integration: real PG, two claimers, SKIP LOCKED
```

**Modified:**

```
backend/pyproject.toml              # + ocrmypdf; hatch packages += "tender"
backend/app/config.py               # + tender_* settings (listed in Task 2)
backend/app/main.py                 # mount tender router (composition root)
backend/alembic/env.py              # + import tender.models  (metadata completeness)
deploy/docker/backend.Dockerfile    # + apt: tesseract-ocr ghoststcript → runtime stage
deploy/dokploy.compose.yml          # + tender-worker service (same image, command: python -m tender.worker)
```

---

## Task 1: Package scaffold + build wiring

**Files:** all `backend/tender/**/__init__.py` stubs above; modify `backend/pyproject.toml`.

**Steps:**
1. Create the directory tree with empty `__init__.py` files and `llm/prompts/.gitkeep`.
2. Add `"tender"` to `[tool.hatch.build.targets.wheel] packages`.
3. Verify: `cd backend && uv run python -c "import tender"` → no error; `uv run ruff check tender` → clean.
4. Commit: `feat(tender): scaffold TCM module package`.

## Task 2: Config keys

**Files:** modify `backend/app/config.py` (additions only, defaults chosen so the app boots with no new env vars).

| Setting | Default | Used by |
| --- | --- | --- |
| `tender_ocr_enabled` | `True` | ingestion (gate ocrmypdf invocation) |
| `tender_ocr_text_density_threshold` | `0.05` (chars per page-area heuristic; calibrated in Task 8 tests) | OCR detection |
| `tender_ocr_min_confidence` | `0.5` | `manual_transcription_required` escape hatch |
| `tender_page_render_dpi` | `150` | page render (§7.4) |
| `tender_worker_poll_seconds` | `2.0` | worker (§7.3) |
| `tender_job_max_attempts` | `3` | retry policy (§7.3) |
| `tender_job_backoff_base_seconds` | `30` | retry policy |
| `tender_job_stale_lock_minutes` | `10` | stale-lock sweep (Decision 8) |

`TENDER_MODEL_*` / `TENDER_EMBED_MODEL` keys (§7.5) are **not** added yet — nothing reads them until M2 (YAGNI).

**Verify:** `uv run pytest tests -k config -v` (existing suite still green); app boots: `uv run python -c "from app.config import settings; print(settings.tender_page_render_dpi)"`.

**Commit:** `feat(tender): add M1 config keys`.

## Task 3: SQLAlchemy models

**Files:** create `backend/tender/models.py`; modify `backend/alembic/env.py` (add `import tender.models  # noqa: F401`); test `backend/tests/tender/test_models.py`.

All tables from PRD §8, exactly as specified there plus Decisions 2–4. Models share `app.database.base.Base`. Highlights that need care:

- `tender_comparisons.context: JSONB` — validated at the API boundary by `ProjectContext` (Task 4), never by the DB.
- `tender_line_items.embedding: Vector(1536)` (`pgvector.sqlalchemy.Vector`), nullable.
- `tender_pages`: `UNIQUE (document_id, page_no)` — this is the per-page checkpoint key (§7.3 resume semantics).
- `tender_documents`: `content_hash String(64)`, `UNIQUE (quote_id, content_hash)`.
- `tender_cell_status`: `UNIQUE (comparison_id, quote_id, cell_code)` per §8.6.
- `tender_jobs`: `kind, comparison_id?, quote_id?, payload JSONB, status, attempts, locked_at, locked_by, last_error, run_after, created_at/updated_at` + index `(status, run_after)`.
- Knowledge tables (`taxonomy_cells`, `taxonomy_synonyms`, `expectation_rules`, `benchmarks`) and eval tables (`golden_documents`, `golden_annotations`, `eval_runs`, `eval_results`) per §8.5/§8.7.
- All status/enum-ish columns: `String` + `CheckConstraint` with the PRD's value lists.

**TDD:** write `test_models.py` first — asserts every expected `__tablename__` is in `Base.metadata.tables`, checkpoint/dedupe unique constraints exist, FK targets are `projects.id`, `users.id`, `draft_artifacts.id`. Run (fails) → implement → run (passes).

**Verify:** `uv run pytest tests/tender/test_models.py -v`; full suite still green (mapper registration must not break `app.database.models` imports).

**Commit:** `feat(tender): SQLAlchemy models for §8 data model`.

## Task 4: Pydantic schemas (`ProjectContext` + API I/O)

**Files:** create `backend/tender/schemas.py`; test `backend/tests/tender/test_schemas.py`.

- `ProjectContext` exactly per §8.1 (all `Literal` fields, `context_version: int = 1`).
- Intake I/O: `ComparisonCreate(project_id, context)`, `QuoteCreate(builder_name, …)`, `ComparisonDetail` (status + quotes + documents + per-document `ingest_status`), `JobView`.

**TDD:** tests first: valid context round-trips; bad `soil_class` rejected; `context_version` defaults to 1.

**Verify:** `uv run pytest tests/tender/test_schemas.py -v`.

**Commit:** `feat(tender): ProjectContext and intake schemas`.

## Task 5: Alembic migrations 007–010

**Files:** four new files in `backend/alembic/versions/` (chain: `006_cockpit_refresh_indexes` → 007 → 008 → 009 → 010). Handwritten, matching repo style (e.g. `003_sitewise_projects_and_drafts.py`). Split so each migration is one coherent concern and individually reversible:

| Rev | Name | Creates |
| --- | --- | --- |
| 007 | `tender_core` | `tender_comparisons`, `tender_quotes`, `tender_documents`, `tender_pages`, `tender_line_items` (+ FKs, checks, checkpoint/dedupe uniques, vector column) |
| 008 | `tender_knowledge` | `CREATE EXTENSION IF NOT EXISTS pg_trgm`; `taxonomy_cells`, `taxonomy_synonyms` (+ trigram index on `phrase_norm`, unique `(cell_code, phrase_norm)`), `expectation_rules`, `benchmarks` |
| 009 | `tender_mapping_status` | `tender_mappings`, `tender_cell_status`, `tender_flags`, `tender_corrections`, `tender_reports` (FK → `draft_artifacts`) |
| 010 | `tender_jobs_eval` | `tender_jobs` (+ `(status, run_after)` index), `golden_documents`, `golden_annotations`, `eval_runs`, `eval_results` |

Every `downgrade()` drops exactly what its `upgrade()` created (008's downgrade does **not** drop `pg_trgm` — extensions are shared).

**Verify (each migration, against the dev database):**
1. `cd backend && uv run alembic upgrade head` → applies cleanly.
2. `uv run alembic downgrade 006_cockpit_refresh_indexes && uv run alembic upgrade head` → full roundtrip clean.
3. Spot-check in psql/Supabase: `\d tender_pages` shows the unique constraint; `tender_line_items.embedding` is `vector(1536)`.

**Commit:** one commit per migration file (4 commits), e.g. `feat(tender): migration 007 core pipeline tables`.

## Task 6: Job queue service

**Files:** create `backend/tender/services/jobs.py`; test `backend/tests/tender/test_jobs.py`.

Functions (all take an `AsyncSession`):
- `enqueue(session, *, kind, comparison_id=None, quote_id=None, payload=None, run_after=None) -> TenderJob`
- `claim_next(session, *, worker_id) -> TenderJob | None` — the §7.3 query:
  ```python
  select(TenderJob)
      .where(TenderJob.status == "queued", TenderJob.run_after <= func.now())
      .order_by(TenderJob.run_after)
      .limit(1)
      .with_for_update(skip_locked=True)
  ```
  then set `status='running'`, `locked_at=now()`, `locked_by=worker_id`, commit (claim is its own transaction so the lock is released immediately and held only as a row claim, not for the duration of the work).
- `complete(session, job)` → `status='done'`, clear lock fields.
- `fail(session, job, error)` → `attempts += 1`; if `attempts >= max_attempts`: `status='failed'`, `last_error=error`; else `status='queued'`, `run_after = now() + backoff_base * 2**(attempts-1)` (30s → 60s → exhausted at 3, per §7.3).
- `requeue_stale(session, *, older_than_minutes)` → `running` + stale `locked_at` → `queued`.

**TDD:** unit tests with mocked sessions (repo style — see `tests/evidence/test_delete.py`): backoff math at attempts 1/2/3, exhaustion → `failed` with `last_error`, claim sets lock fields. The actual SKIP LOCKED concurrency behaviour is covered by Task 7's integration test.

**Verify:** `uv run pytest tests/tender/test_jobs.py -v`.

**Commit:** `feat(tender): tender_jobs queue service with SKIP LOCKED claim`.

## Task 7: Worker loop

**Files:** create `backend/tender/worker.py`; tests `backend/tests/tender/test_worker.py`, `backend/tests/tender/test_worker_integration.py`.

- `HANDLERS: dict[str, Handler]` registry; M1 registers only `"ingest_document"`. Unknown kind → `fail()` immediately with a clear error (never crashes the loop).
- `run_once(session_factory, worker_id) -> bool` — claim → dispatch → complete/fail; returns whether a job was processed (makes the loop testable without time).
- `main()` — resolves `worker_id = f"{hostname}:{pid}"`, loops: `requeue_stale` sweep, `run_once`; sleeps `tender_worker_poll_seconds` only when idle (batch 1, poll 2s per §7.3). `SIGINT`/`SIGTERM` set a shutdown flag; current job finishes before exit.
- Entry point: `python -m tender.worker` (`if __name__ == "__main__": asyncio.run(main())`), structlog logging configured same as app.

**TDD (unit):** dispatch routes by kind; handler exception → `fail` called with the traceback string; unknown kind → failed not raised; shutdown flag stops loop.

**Integration test (`@pytest.mark.integration`, real PG):** enqueue 1 job, run two concurrent `claim_next` calls in separate sessions — exactly one wins, the other gets `None`. This is the SKIP LOCKED proof.

**Verify:** `uv run pytest tests/tender/test_worker.py -v`; `uv run pytest tests/tender/test_worker_integration.py -m integration -v` (against dev DB); manual smoke: `uv run python -m tender.worker` → logs "worker started", polls idle, Ctrl-C exits cleanly.

**Commit:** `feat(tender): worker loop with handler registry and stale-lock sweep`.

## Task 8: Ingestion service (`ingest_document` stage)

**Files:** create `backend/tender/services/ingestion.py`; test `backend/tests/tender/test_ingestion.py` + synthetic-PDF fixtures in `tests/tender/conftest.py`; modify `backend/pyproject.toml` (+ `ocrmypdf`).

Pipeline for `ingest_document(session, job)` (per §7.4 / §9.1, idempotent and page-checkpointed):

1. **Load + hash.** Download bytes from storage (`app.storage.project_files.download_project_file`), compute sha256. If another `tender_documents` row in the same quote has this hash → mark `ingest_status='duplicate'`, done.
2. **Format gate.** Non-PDF → `ingest_status='unsupported_format'` (Decision 5), done.
3. **OCR detection.** Open with PyMuPDF; per page compute text density (extracted text length normalised by page area). Pages below `tender_ocr_text_density_threshold` are OCR candidates. Record per-page decision.
4. **OCR application** (if any candidates and `tender_ocr_enabled`): run `ocrmypdf --skip-text` on the file via subprocess into a temp file; reopen; record `ocr_applied=true` and per-page confidence (from Tesseract word confidences). Mean confidence < `tender_ocr_min_confidence` → `ingest_status='manual_transcription_required'` (escape hatch), stop without emitting junk pages.
5. **Render + persist, per page (checkpoint unit).** For each page not already in `tender_pages` (resume semantics — `UNIQUE (document_id, page_no)`): render PNG at `tender_page_render_dpi`, upload to storage key `tender/{comparison_id}/{document_id}/pages/page-{n:04d}.png`, insert `tender_pages` row (`image_path`, `text_content`, `ocr_confidence`), commit per page. A retry after a crash at page 12 resumes at page 12 (§7.3).
6. **Finish.** `page_count`, `ocr_applied`, `ingest_status='ingested'` on the document row.

`classify_document` is **not** in M1 (it's an LLM stage, M2); ingestion ends by enqueueing nothing.

**TDD:** fixtures build two tiny PDFs in-memory with PyMuPDF — one with a real text layer, one image-only (insert a rect/pixmap, no text). Tests: density detection flags the image-only page and not the text page; render produces a PNG of the expected pixel size for 150 DPI; duplicate hash short-circuits; resume skips pages already persisted (pre-insert page 1, assert only page 2 is rendered/uploaded); unsupported format path. Storage and session mocked (repo style). OCR application itself is **not** unit-tested (needs Tesseract) — covered by the manual real-doc verification below.

**Verify:** `uv run pytest tests/tender/test_ingestion.py -v`; `uv add ocrmypdf` lockfile updated, `uv run ruff check tender` clean.

**Commit:** `feat(tender): document ingestion — hash, OCR detection, page render, checkpointed persist`.

## Task 9: Intake API + mounting

**Files:** create `backend/tender/router.py`; modify `backend/app/main.py` (import + `include_router`); test `backend/tests/tender/test_router.py`.

Endpoints (auth via existing `get_current_user`, session via `get_db`):
- `POST /api/tender/comparisons` — body `ComparisonCreate`; validates `context` through `ProjectContext`; row with `status='intake'`.
- `POST /api/tender/comparisons/{id}/quotes` — body `QuoteCreate`.
- `POST /api/tender/quotes/{id}/documents` — multipart upload: store bytes via `upload_project_file` under `tender/{comparison_id}/{quote_id}/{sanitized-filename}`, insert `tender_documents` (`ingest_status='pending'`), `enqueue(kind='ingest_document', payload={'document_id': …})`. Returns document + job id.
- `GET /api/tender/comparisons/{id}` — `ComparisonDetail` with quotes, documents, ingest statuses (the M1 "is it working" poll).

**TDD:** repo-style TestClient tests with mocked session/storage: create-comparison validates context (bad soil class → 422); upload registers row + enqueues job; detail endpoint shape.

**Verify:** `uv run pytest tests/tender/test_router.py -v`; full suite green; `uv run uvicorn app.main:app` boots and `/api/tender` routes appear in `/docs`.

**Commit:** `feat(tender): minimal intake API mounted at /api/tender`.

## Task 10: Deployment wiring

**Files:** modify `deploy/docker/backend.Dockerfile` (runtime stage: `apt-get install -y --no-install-recommends tesseract-ocr ghostscript`), `deploy/dokploy.compose.yml` (new `tender-worker` service: same image/env as backend, `command: python -m tender.worker`, no ports).

**Verify:** `docker build -f deploy/docker/backend.Dockerfile .` succeeds locally; `docker run --rm <image> ocrmypdf --version` prints a version; compose file parses (`docker compose -f deploy/dokploy.compose.yml config`).

**Commit:** `feat(tender): worker service + OCR system deps in deploy config`.

## Task 11: End-to-end verification on real documents (M1 exit criterion)

No new files — the standing-rule check (§19: "real documents flow through the pipeline from M1 onward").

1. `uv run alembic upgrade head` against dev DB.
2. Terminal A: `uv run uvicorn app.main:app`; Terminal B: `uv run python -m tender.worker`.
3. Via `/docs`: create comparison (real-ish context), quote, upload a **real builder quote PDF** (and one scanned/image-only PDF if available).
4. Confirm: job goes `queued → running → done`; `tender_pages` rows exist with non-empty `text_content` for digital pages; PNGs present in the storage bucket at the expected keys; `GET /api/tender/comparisons/{id}` reports `ingest_status='ingested'`.
5. Failure drill: temporarily point storage at a bad bucket, upload, confirm 3 attempts with backoff then `failed` + `last_error`, restore, retry by re-enqueueing.

**Done means:** all of the above observed, full test suite green (`uv run pytest tests`), `uv run ruff check .` clean.

---

## Out of scope for M1 (explicitly)

- `classify_document` and everything LLM (`llm/client.py` bodies, prompts) — M2.
- Seed loaders for `data/tender/*` — land with mapping (M3); migrations create the empty knowledge tables now.
- XLSX/DOCX conversion (Decision 5) — M2.
- Frontend cockpit surface (§16), QA console, eval harness runner (tables exist; harness is M2).
