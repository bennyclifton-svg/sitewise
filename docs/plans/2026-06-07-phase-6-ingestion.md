# Phase 6 — Ingestion Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the local `data/` corpus into (1) searchable `document_chunks` for Q&A and (2) a **document register** (`source_documents` + `document_metadata`) for transmittals and tender workflows — with idempotent re-runs and unit-tested class-aware chunking.

**Architecture:** Offline CLI under `backend/ingest/` — **discover → classify → route → extract → chunk → embed → persist**. A `document_class` router selects extractors and chunkers (contract, specification, drawing, tender_submission, trr, …). Outputs dual track: **full text** where prose matters; **register metadata** for drawings (title block, number, rev — no geometry). Doctrine (`docs/clerk-brief.md`) ingests as `source_type: doctrine`. Persistence uses deterministic UUIDs from `relative_path` + `chunk_index`. `search_vector` is Postgres-generated — ingest writes `content` only.

**Downstream:** Phases 11–12 (workflows, tender evaluation) depend on `procurement_stage` metadata and blockb ingest — see [2026-06-07-workflows-and-tender.md](2026-06-07-workflows-and-tender.md).

**Retrieval profiles (Phase 5):** Documents with `ingest_mode=register_only` (drawings) or `document_class` in `{doctrine, reference_guide}` persist `normalized_content` and metadata only — **no** `document_chunks` rows and **no** embedding API calls on ingest. Long reports and other prose types still use chunk + embed. See [2026-06-07-fast-retrieval-by-document-class.md](2026-06-07-fast-retrieval-by-document-class.md) Phase 5.

**Tech Stack:** Python 3.12, SQLAlchemy sync sessions (CLI), Alembic migration for chunk uniqueness, OpenAI `text-embedding-3-small` via existing SDK, `pymupdf` (PDF), `mammoth` (docx→HTML→markdown-ish), `tiktoken` (token-aware chunking), `structlog`, `pytest`.

**Prerequisites (already done in Phase 0–2):**
- `DATABASE_URL`, `OPENAI_API_KEY` in `backend/.env`
- Alembic migration `001_initial_schema` applied (`source_documents`, `document_chunks`, HNSW + GIN indexes)
- Corpus folders present under `data/` (see [data/README.md](../../data/README.md))

**Corpus snapshot (Phase 6 targets):**

| Folder | Files | Phase 6 role |
| ------ | ----- | ------------ |
| `procurment-demo/` | 35 | Pipeline smoke (~30 PDF/DOCX) |
| `delivery-house/` | 28 | Compact delivery evidence |
| `procurement-blockb/` | 210 | **Tender validation** — TEP→EOI→RFT→submissions→evaluation→TRR |
| `seed/` | 23 | Reference guides |
| `docs/clerk-brief.md` | 1 | Doctrine |
| `procurement-campy/` | 655 | Stretch — scale + DWG register |

---

## Design decisions (read before coding)

### 1. Folder → metadata mapping

| Path pattern | `project` | `phase` | `source_type` |
| ------------ | --------- | ------- | ------------- |
| `seed/*` | `seed` | `reference` | `reference` |
| `docs/clerk-brief.md` | `clerk-doctrine` | `reference` | `doctrine` |
| `delivery-*/*` | folder name (e.g. `delivery-house`) | `delivery` | `project_evidence` |
| `procurement-*/*` or `procurment-*/*` | folder name | `procurement` | `project_evidence` |
| `advisary-*/*` | folder name | `advisory` | `project_evidence` |
| `consultants-*/*` | folder name | `consultants` | `project_evidence` |

`relative_path` is POSIX-style from `data/` root, e.g. `procurement-blockb/03 RFT/spec.pdf`.

### 2. `document_class` + `procurement_stage`

`document_class` drives extractor/chunker routing (not just file extension):

| Class | Examples | `ingest_mode` |
| ----- | -------- | ------------- |
| `contract` | FIOA, HIA | `full_text` |
| `specification` | Spec PDF/DOCX | `full_text` (trade-section chunker) |
| `tender_submission` | `05 SUBMISSION 01/` | `full_text` |
| `trr` | `08 TRR/` | `full_text` |
| `evaluation` | `06 EVALUATION/` | `full_text` |
| `rft` / `addendum` / `eoi` / `tep` | procurement folders | `full_text` |
| `drawing` | PDF/DWG sheets | `register_only` or `hybrid` (title block text) |
| `report` / `certificate` / `correspondence` | advisory, delivery | `full_text` |
| `reference_guide` | `seed/*.md` | `full_text` |
| `doctrine` | `clerk-brief.md` | `full_text` |
| `planning_instrument` | (reserved — not in corpus yet) | — |

For `procurement-blockb/`, parse `procurement_stage` from parent folder:

| Folder prefix | `procurement_stage` | `tenderer_id` (if applicable) |
| ------------- | ------------------- | ----------------------------- |
| `01 TEP` | `tep` | — |
| `02 EOI` | `eoi` | — |
| `03 RFT` | `rft` | — |
| `04 ADDENDUM` | `addendum` | — |
| `05 SUBMISSION 01` | `submission` | `01` |
| `06 EVALUATION` | `evaluation` | — |
| `07 SUBMISSION 02` | `submission` | `02` |
| `08 TRR` | `trr` | — |

Store in `document_metadata` JSONB alongside drawing fields (`drawing_number`, `revision`, `discipline`, `title`) when applicable.

### 3. Stable IDs (idempotency)

```python
DOC_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # fixed constants in ingest/ids.py
CHUNK_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")

def document_id(relative_path: str) -> uuid.UUID:
    return uuid.uuid5(DOC_NAMESPACE, relative_path)

def chunk_id(relative_path: str, chunk_index: int) -> uuid.UUID:
    return uuid.uuid5(CHUNK_NAMESPACE, f"{relative_path}:{chunk_index}")
```

Re-ingest flow per file:
1. Upsert `source_documents` on `relative_path` (or explicit `id=document_id(...)`).
2. Upsert `document_chunks` on `(document_id, chunk_index)` with explicit `id=chunk_id(...)`.
3. Delete orphaned chunks when document shrinks (chunk count decreased).

### 4. Chunking parameters

- Target: **600 tokens** per chunk (architecture + report-indexer convention).
- Overlap: **80 tokens** between consecutive chunks for grounding continuity.
- Markdown: split on `#` / `##` / `###` headers first; sub-split oversized sections by token window.
- PDF: extract per-page text; merge pages until token budget; `page_or_section` = `"p. 3"` or `"p. 3–5"`.
- DOCX: treat as single flow unless mammoth emits heading tags → section boundaries.
- Store `token_count` via `tiktoken` (`cl100k_base`).
- Put `char_start`, `char_end`, `source_format` in `chunk_metadata` JSONB.

### 5. `search_vector`

Already defined in migration `001_initial_schema`:

```sql
ADD COLUMN search_vector tsvector
GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
```

Ingest **must not** write `search_vector` — only `content`.

### 6. Schema changes required

**Migration `002_ingest_metadata.py`**

On `source_documents`:

- `document_class` VARCHAR(64) NOT NULL DEFAULT `unknown`
- `ingest_mode` VARCHAR(32) — `full_text` | `register_only` | `hybrid`
- `document_metadata` JSONB — procurement_stage, tenderer_id, drawing register fields, etc.
- `content_hash` VARCHAR(64) — skip re-extract when file unchanged

On `document_chunks`:

- Replace non-unique `(document_id, chunk_index)` index with **unique** constraint for upserts

### 7. New dependencies (justify in commit)

| Package | Why |
| ------- | --- |
| `pymupdf` | PDF text extraction with page numbers — non-trivial to write |
| `mammoth` | DOCX → structured text/HTML — standard approach |
| `tiktoken` | Token-accurate chunk sizing aligned with embedding model |

Add via `cd backend && uv add pymupdf mammoth tiktoken`.

### 8. Config additions

In `backend/app/config.py`:

```python
data_dir: Path = _BACKEND_DIR.parent / "data"
ingest_embedding_batch_size: int = 64
ingest_supported_extensions: str = ".pdf,.docx,.md"  # parsed to set
```

### 9. Package layout

```text
backend/
├── ingest/
│   ├── __init__.py
│   ├── __main__.py
│   ├── types.py
│   ├── ids.py
│   ├── discover.py
│   ├── classify.py          # document_class + procurement_stage
│   ├── metadata.py          # project, phase, source_type, register fields
│   ├── router.py
│   ├── extractors/
│   │   ├── pdf_text.py
│   │   ├── pdf_drawing.py   # title block + filename parse
│   │   ├── docx.py
│   │   ├── markdown.py
│   │   └── dwg.py           # metadata only (Phase 6b for campy)
│   ├── chunkers/
│   │   ├── prose.py
│   │   ├── specification.py
│   │   └── register.py      # single chunk for drawing register rows
│   ├── embed.py
│   ├── persist.py
│   └── pipeline.py
├── tests/ingest/
│   ├── test_classify.py
│   ├── test_procurement_stage.py   # blockb folder paths
│   ├── test_chunk.py
│   └── test_drawing_filename.py
```

Use a **sync** SQLAlchemy engine in `ingest/db.py` (CLI script, not request path). Reuse `_async_database_url()` pattern but with `create_engine` + `psycopg`.

---

## Task 1: Schema migration — chunk uniqueness

**Files:**
- Create: `backend/alembic/versions/002_document_chunks_unique_index.py`

**Step 1: Write migration**

Replace non-unique index with unique index on `(document_id, chunk_index)`.

**Step 2: Apply locally**

```bash
cd backend && uv run alembic upgrade head
```

**Step 3: Verify in Supabase**

Table Editor → `document_chunks` → confirm unique index exists.

---

## Task 2: Config + dependencies

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/pyproject.toml` (via uv add)
- Modify: `backend/.env.example` (optional comment for `DATA_DIR` override)

**Step 1: Add dependencies**

```bash
cd backend && uv add pymupdf mammoth tiktoken
```

**Step 2: Add settings fields**

`data_dir`, `ingest_embedding_batch_size`, property `ingest_supported_extensions_set`.

**Step 3: Verify import**

```bash
cd backend && uv run python -c "from app.config import settings; print(settings.data_dir)"
```

---

## Task 3: Core types and metadata inference

**Files:**
- Create: `backend/ingest/types.py`
- Create: `backend/ingest/metadata.py`
- Create: `backend/ingest/ids.py`
- Test: `backend/tests/ingest/test_metadata.py`

**Step 1: Write failing metadata tests**

```python
@pytest.mark.parametrize("folder,expected_phase,expected_source", [
    ("procurment-demo", "procurement", "project_evidence"),
    ("delivery-house", "delivery", "project_evidence"),
    ("seed", "reference", "reference"),
])
def test_infer_phase_and_source(folder, expected_phase, expected_source):
    meta = infer_metadata(f"data/{folder}/doc.pdf")
    assert meta.phase == expected_phase
    assert meta.source_type == expected_source
    assert meta.project == folder
```

**Step 2: Run → FAIL**

```bash
cd backend && uv run pytest tests/ingest/test_metadata.py -v -m "not integration"
```

**Step 3: Implement `infer_metadata(relative_path) -> DocumentMetadata`**

**Step 4: Run → PASS**

---

## Task 4: Discover — corpus manifest

**Files:**
- Create: `backend/ingest/discover.py`
- Test: `backend/tests/ingest/test_discover.py`

**Step 1: Write failing test**

Use a tiny `tmp_path` corpus:

```python
def test_discover_builds_manifest(tmp_path):
    (tmp_path / "procurment-demo").mkdir()
    (tmp_path / "procurment-demo" / "a.pdf").write_bytes(b"%PDF")
    (tmp_path / "procurment-demo" / "skip.msg").write_bytes(b"x")
    entries = discover_corpus(tmp_path)
    assert len(entries) == 1
    assert entries[0].extension == ".pdf"
    assert entries[0].relative_path == "procurment-demo/a.pdf"
```

**Step 2: Implement `discover_corpus(data_dir) -> list[ManifestEntry]`**

- Walk only immediate project folders (not `download.py`, not `README.md`).
- Skip hidden files, zero-byte files.
- Record: `absolute_path`, `relative_path`, `project`, `filename`, `extension`, `size_bytes`.
- Filter to `settings.ingest_supported_extensions_set` for ingest; still list skipped in logs.

**Step 3: Run tests → PASS**

---

## Task 5: Extract — PDF, DOCX, Markdown

**Files:**
- Create: `backend/ingest/extract.py`
- Test: `backend/tests/ingest/test_extract.py` (markdown only — no binary fixtures)

**Step 1: Markdown extractor (trivial)**

`extract_markdown(path) -> ExtractedDocument` with `pages: list[PageText]` where each section is one pseudo-page.

**Step 2: PDF extractor**

`extract_pdf(path)` using pymupdf:
- Per-page text via `page.get_text("text")`
- Skip empty pages
- Normalized markdown: `# {filename}\n\n## Page {n}\n\n{text}`

**Step 3: DOCX extractor**

`extract_docx(path)` using mammoth → HTML → strip to plain text with heading markers.

**Step 4: `extract_document(entry) -> ExtractedDocument | None`**

Returns `None` for unsupported extensions (caller logs skip).

**Step 5: Unit test markdown round-trip**

No network, no PDF fixtures required for CI.

---

## Task 6: Chunking logic (TDD — core of Phase 6)

**Files:**
- Create: `backend/ingest/chunk.py`
- Test: `backend/tests/ingest/test_chunk.py`

**Step 1: Write failing tests**

```python
def test_chunk_markdown_respects_headers():
    text = "# Intro\n\nHello.\n\n## Details\n\n" + ("word " * 400)
    chunks = chunk_document(text, source_format="markdown", relative_path="seed/guide.md")
    assert chunks[0].page_or_section == "Intro"
    assert all(c.chunk_index == i for i, c in enumerate(chunks))
    assert chunks[0].token_count <= 600

def test_stable_chunk_indices_are_sequential():
    chunks = chunk_document("short text", source_format="markdown", relative_path="a/b.md")
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

def test_overlap_carries_context():
    long_text = "sentence. " * 500
    chunks = chunk_document(long_text, source_format="pdf", relative_path="x/y.pdf")
    assert len(chunks) > 1
    # tail of chunk N should appear near head of chunk N+1 (overlap)
```

**Step 2: Implement `chunk_document(...) -> list[TextChunk]`**

Pure function — no DB, no OpenAI.

**Step 3: Run → PASS**

```bash
cd backend && uv run pytest tests/ingest/ -v -m "not integration"
```

---

## Task 7: Embeddings

**Files:**
- Create: `backend/ingest/embed.py`

**Step 1: `embed_texts(texts: list[str]) -> list[list[float]]`**

- Batch per `settings.ingest_embedding_batch_size`
- Use `openai.OpenAI().embeddings.create(model=settings.openai_embedding_model, input=batch)`
- Validate returned dimension == `settings.openai_embedding_dimensions`

**Step 2: Integration smoke (manual, not CI)**

```bash
cd backend && uv run python -c "from ingest.embed import embed_texts; print(len(embed_texts(['hello'])[0]))"
```

Expect `1536`.

---

## Task 8: Persist — upsert documents and chunks

**Files:**
- Create: `backend/ingest/db.py` (sync engine + session factory)
- Create: `backend/ingest/persist.py`

**Step 1: `upsert_source_document(...)`**

SQLAlchemy `insert(...).on_conflict_do_update(index_elements=["relative_path"], set_={...})`.

Set explicit `id=document_id(relative_path)`.

**Step 2: `upsert_chunks(document_id, chunks, embeddings)`**

`on_conflict_do_update` on `(document_id, chunk_index)`.

**Step 3: `delete_orphan_chunks(document_id, keep_count)`**

Delete rows where `chunk_index >= keep_count`.

**Step 4: Manual verify with one markdown file from `seed/`**

---

## Task 9: Pipeline orchestrator + CLI

**Files:**
- Create: `backend/ingest/pipeline.py`
- Create: `backend/ingest/__main__.py`
- Modify: `backend/pyproject.toml` — ensure `ingest` package is discoverable (may need `[tool.hatch.build.targets.wheel] packages = ["app", "ingest"]`)

**Step 1: `ingest_file(entry) -> IngestResult`**

discover → extract → chunk → embed → persist; structlog events at each stage.

**Step 2: `ingest_folder(folder_name: str) -> FolderSummary`**

**Step 3: CLI**

```bash
cd backend
uv run python -m ingest run --folder procurment-demo      # smoke
uv run python -m ingest run --file docs/clerk-brief.md    # doctrine
uv run python -m ingest run --folder seed
uv run python -m ingest run --folder delivery-house
uv run python -m ingest run --folder procurement-blockb   # tender validation
```

Flags: `--dry-run` (discover + extract + chunk, no DB/embed), `--limit N` for debugging.

**Step 4: Register package in pyproject if needed**

---

## Task 10: End-to-end ingest — procurment-demo

**Step 1: Dry run**

```bash
cd backend && uv run python -m ingest run --folder procurment-demo --dry-run
```

Expect ~30 ingestible files, 5 skipped.

**Step 2: Full ingest**

```bash
cd backend && uv run python -m ingest run --folder procurment-demo
```

**Step 3: Verify row counts in Supabase**

| Table | Expected (approx) |
| ----- | ----------------- |
| `source_documents` | ~30 rows with `project = procurment-demo` |
| `document_chunks` | ~150–400 rows (depends on doc sizes) |
| embeddings | all non-null on those chunks |
| `search_vector` | populated automatically |

**SQL sanity check:**

```sql
SELECT project, COUNT(*) FROM source_documents GROUP BY project;
SELECT COUNT(*) FROM document_chunks WHERE embedding IS NULL;
```

---

## Task 11: End-to-end ingest — delivery-house

```bash
cd backend && uv run python -m ingest run --folder delivery-house
```

Verify ~23 documents (pdf + docx only). Re-run same command — row counts unchanged (idempotent).

---

## Task 12: Ingest seed/ separately

```bash
cd backend && uv run python -m ingest run --folder seed
```

Verify:
- `phase = reference`
- `source_type = reference`
- 23 `source_documents`

---

## Task 13: End-to-end ingest — procurement-blockb (tender validation)

**Step 1: Dry run**

```bash
cd backend && uv run python -m ingest run --folder procurement-blockb --dry-run
```

Expect ~135+ ingestible PDF/DOCX; log skips for `.msg` (42), `.jpg`, `.zip`, etc.

**Step 2: Full ingest**

Verify `document_metadata.procurement_stage` populated for all eight top-level folders.

**Step 3: Retrieval smoke (manual, post Phase 7)**

- Filter `project=procurement-blockb`, `procurement_stage=trr`
- Filter `procurement_stage=submission`, `tenderer_id=01`

---

## Task 14: Deferred folders (stretch)

```bash
uv run python -m ingest run --folder delivery-petersham
uv run python -m ingest run --folder procurement-campy   # 655 files; DWG register
```

Expand `.zip` tender submissions; `.msg` correspondence (Phase 6b).

---

## Task 15: Unit test gate + checklist update

**Step 1: Full fast test suite**

```bash
cd backend && uv run pytest -m "not integration" -v
```

**Step 2: Update `docs/todoist.md` Phase 6 checkboxes**

Mark items complete as each task lands.

---

## Done criteria (from todoist)

- [ ] Class-aware pipeline: discover, classify, route, extract, chunk, embed, persist
- [ ] Schema: `document_class`, `document_metadata`, `content_hash`, unique chunk index
- [ ] `procurment-demo/`, `delivery-house/`, `procurement-blockb/`, `seed/`, `clerk-brief.md` in Supabase
- [ ] Block B: `procurement_stage` + `tenderer_id` on submission folders; TRR retrievable
- [ ] Doctrine + seed tagged `source_type` correctly
- [ ] Idempotent re-run verified
- [ ] Unit tests: classify, procurement_stage, chunkers (no network) green
- [ ] Dashboard row counts sane

---

## Risks and mitigations

| Risk | Mitigation |
| ---- | ---------- |
| Scanned PDFs with no text layer | Log `extract_empty` warning; skip or store placeholder — do not fail batch |
| Large folders (Petersham, Campy) | `--limit`, batch embedding, progress logging; run overnight |
| OpenAI rate limits | Batch size 64, exponential backoff on 429 |
| Mammoth loses complex Word formatting | Acceptable for v1 — we need searchable text, not layout fidelity |
| `.msg` / `.xlsx` in corpus | Explicitly skipped in Phase 6; logged per file |

---

## Handoff to Phases 7–12

**Phase 7 retrieval** filters on: `project`, `phase`, `source_type`, `document_class`, `document_metadata->procurement_stage`, `document_metadata->tenderer_id`.

**Phase 8 assistant** uses doctrine (always-on instructions + retrieved `clerk-brief` chunks) and seed.

**Phases 11–12** use blockb ingest for tender evaluation workflows — see [workflows-and-tender plan](2026-06-07-workflows-and-tender.md).
