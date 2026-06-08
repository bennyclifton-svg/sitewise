# PDF Drawing-Set Auto-Split — Design

**Date:** 2026-06-08
**Status:** Validated design (not yet implemented)
**Trigger example:** `data/delivery-house/L18 CC Plans.pdf` — a single 20-page PDF where every page is a distinct A3-landscape drawing (Title Page, Site Plan, Ground Floor, First Floor, Elevations ×2, Section, Slab Plan, …).

## Problem

When a user drag-and-drops a PDF that is actually a *set of separate drawings* (one drawing per page), it currently lands in the repository as a single multi-page document. The user wants each sheet to become its own repository document, as if they had uploaded N separate PDFs — automatically detected, with the split performed for them.

## Decisions (locked during brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Trust model | **Detect → confirm preview** | Backend detects a drawing set and returns a preview; user clicks "Split into N" or "Keep as single". Makes false positives cheap and keeps the user in control. |
| Per-sheet naming | **Extract sheet title, positional fallback** | Pull the sheet name from the title-block text (reliable on vector PDFs); fall back to `Sheet NN` when a page has no extractable text (scanned). |
| Original PDF | **Discard, keep provenance** | Only the N single-page sheets become evidence; lineage is stored in each sheet's metadata. Avoids double-indexing the same content. |

Out of scope for v1 (YAGNI): OCR for scanned sets, LLM/vision title extraction, a manual "split this existing PDF" button, staging-cleanup scheduler. All are clean future upgrades behind the same interfaces.

## What the source file looks like (grounding)

- 20 pages, **all A3 landscape (1191×842 pt), identical dimensions**.
- Vector/extractable text (no OCR needed). Each page carries a title block with `SHEET: X OF 20`, `SCALE: 1:200`, `DRAWN BY`, `DATE`, and a dominant sheet caption (`SITE PLAN`, `GROUND FLOOR PLAN`, …).
- This builder identifies sheets by **name + "X OF Y"**, not a classic `A-101` drawing number — so naming keys on the sheet caption plus the sheet sequence number for uniqueness.

## Architecture — two-phase upload

Today a dropped file is stored and ingested in one immediate call (`POST /projects/{id}/inbox/upload` → `upload_inbox_files` → per-file `_upload_single_file`, which both stores to object storage and runs `ingest_hosted_file`). The split feature separates *store* from *ingest* so a PDF can be staged and analyzed before anything becomes evidence.

### Phase 1 — Analyze (no repository changes)

1. Frontend drops a `.pdf` → `POST /projects/{id}/inbox/analyze` (multipart, raw PDF).
2. Backend stores the original to a **staging** key `{project_id}/_staging/{uuid}.pdf` (never an `_inbox` path, so it is never evidence) and runs the drawing-set detector.
3. Returns:
   ```json
   {
     "staging_id": "…",
     "is_drawing_set": true,
     "confidence": 0.95,
     "scores": { "uniform_dims": 1.0, "large_format_landscape": true, "keyword_fraction": 1.0 },
     "page_count": 20,
     "pages": [ { "index": 2, "proposed_title": "Site Plan", "has_text": true }, … ]
   }
   ```
4. `is_drawing_set === false` → frontend transparently proceeds as today (single-file ingest), no prompt. `true` → frontend shows the confirm-preview.

### Phase 2 — Commit (on user choice)

- **Split into N** → `POST /projects/{id}/inbox/{staging_id}/split` → backend downloads the staged PDF, splits each page into a single-page PDF, runs the existing per-file store+ingest loop for each, deletes the staging object.
- **Keep as single** → `POST /projects/{id}/inbox/{staging_id}/commit` → moves the staged PDF into `_inbox` and ingests once (current behaviour).

Non-PDF uploads keep using the untouched `/inbox/upload` endpoint. New logic is isolated behind the PDF path; `ingest_hosted_file` is reused verbatim for each resulting sheet.

## Drawing-set detector

A scored heuristic over the staged PDF (PyMuPDF). Because the confirm step makes false positives cheap, it can lean slightly aggressive — but must not flag ordinary multi-page reports.

Signals (per page, then aggregated):
1. **Page count ≥ 2** — hard gate.
2. **Uniform dimensions** — fraction of pages matching the modal size within ~2 pt.
3. **Large-format landscape** — modal page `width > height` and long edge ≥ ~1000 pt (A3+). Strongest separator from a portrait A4 report.
4. **Title-block keywords** — fraction of pages whose text has ≥2 of `SCALE`, `SHEET`, `DRAWN`, `REV`, `DWG`, `DATE`, `\d+ OF \d+`.

Decision:
```
is_drawing_set =
    page_count >= 2
    AND uniform_dims_fraction >= 0.8
    AND large_format_landscape
    AND keyword_fraction >= 0.5
confidence = weighted blend of the fractions
```

Thresholds live in one config dataclass (tunable without touching logic). Sub-scores are returned in the API response for debugging false calls. Scanned sets with no text fail the keyword test → fall through to single-file (safe default).

## Per-sheet title extraction

Uses `page.get_text("words")` (words with positions). Cascade — first hit wins:

1. **Anchored label** — a word matching `TITLE` / `SHEET TITLE` / `DRAWING TITLE`; take the prominent text spatially adjacent (same band, right/below).
2. **Title-block region + font size** — restrict to the bottom / bottom-right region; pick the largest-font non-boilerplate span (skip firm name, copyright, address). Also capture sheet sequence via `(\d+)\s*OF\s*(\d+)` and scale via `1:\d+` as side-metadata.
3. **Positional fallback** — no usable text → `Sheet {NN}`.

Filename assembly:
```
{source_stem} - {NN} {Title}.pdf
→ "L18 CC Plans - 02 Site Plan.pdf"
```
- `NN` = zero-padded sheet number (from "X OF Y" if found, else page index) → guarantees uniqueness even when titles repeat (Elevations ×2, Landscape ×3).
- Title slugified, length-capped.
- Final collision guard against existing `_inbox` paths.

Extraction is best-effort and side-effect-free: any page that throws degrades to the positional name rather than failing the split. All proposed names appear in the preview before commit.

## Split & ingest mechanics

Splitting (lossless, vector-preserving):
```python
src = fitz.open(stream=staged_bytes, filetype="pdf")
for i in range(src.page_count):
    out = fitz.open()
    out.insert_pdf(src, from_page=i, to_page=i)
    page_bytes = out.tobytes(garbage=4, deflate=True)
```
Each sheet is a real single-page PDF — independently viewable and fully searchable by the existing ingest pipeline (no raster, no OCR). `garbage=4, deflate=True` keeps outputs small.

Ingesting — reuse, don't reinvent: each `(filename, page_bytes)` becomes an `InboxUploadItem` and runs through the **current** `_upload_single_file` path (store → `ingest_hosted_file` → upsert `workspace_file`). Sequential loop; per-sheet `InboxUploadOutcome` so partial failures report individually.

Cleanup & ordering:
1. Split all pages in memory.
2. Ingest each sheet, collecting outcomes.
3. On success, delete the staging object.
4. Commit the DB transaction once.

Guardrails: page cap (e.g. 200) → reject; encrypted/password PDF → detected at analyze, falls back to single-file; zero successful ingests → leave staging intact and error (nothing half-applied).

## Frontend confirm-preview UX

Lives in `DocumentRepositoryPanel`, extending `uploadFilesBatch`. For `.pdf` files, call analyze first:
1. `is_drawing_set === false` → normal upload path, no UI change.
2. `true` → push a pending split proposal into state; render an inline confirm card (reusing the existing drag-overlay/alert visual language — no new component system):
   ```
   L18 CC Plans.pdf — looks like a drawing set
   20 sheets detected · 95% confidence
     02  Site Plan
     03  Ground Floor Plan
     …  (scrollable, all 20)
   [ Split into 20 documents ]   [ Keep as single PDF ]
   ```
- **Split** → `api.splitStagedPdf` → `await onUploadComplete()` (existing evidence + tree refresh). Progress via existing `IngestProgressStrip` ("ingesting 7 of 20").
- **Keep as single** → `api.commitStagedPdf` → same refresh.
- Errors surface in the existing `uploadError` alert region.

Batch behaviour: multiple dropped PDFs each get their own proposal card, resolved independently. Staging lifecycle: orphaned staging objects (user navigates away) are swept by a future TTL/cleanup on the `_staging/` prefix — noted as follow-up, not built in v1.

## Data model & provenance

No schema migration. Provenance rides in existing `document_metadata` JSONB on `SourceDocument` (echoed onto `workspace_file` via the normal ingest path):
```json
{
  "split_from": "L18 CC Plans.pdf",
  "split_source_hash": "<sha256 of original>",
  "sheet_index": 2,
  "sheet_total": 20,
  "sheet_number_label": "2 OF 20",
  "sheet_scale": "1:200",
  "split_method": "heuristic_v1",
  "title": "Site Plan"
}
```
- Lineage without duplication (satisfies "discard original").
- `split_source_hash` lets a re-drop of the same combined PDF be recognised ("already split") instead of duplicating.
- `split_method` version tag distinguishes future v2 (LLM) extractions.
- Repo title surfaces through the filename → metadata `title` the classifier already reads; `_register_title`/`EvidencePreview` display it unchanged.

`source_type` stays `project_evidence`; `document_class` is classifier-assigned (likely `drawing`). Downstream (search, citations, Sort Files) needs no awareness that these came from a split.

## Testing plan

Fixtures: synthesize PDFs in-memory with PyMuPDF + the real `L18 CC Plans.pdf` as an integration fixture.

- **Detector** (`tests/inbox/test_drawing_detection.py`): real L18 → True/high confidence; portrait A4 multi-page → False; 2-page landscape no-keywords → False; single page → False; mixed sizes → False.
- **Title extraction** (`test_sheet_titles.py`): real L18 → "Site Plan", "Ground Floor Plan"; repeated titles get distinct filenames via sheet number; no-text page → `Sheet 07`; collision guard appends suffix.
- **Splitter** (`test_pdf_split.py`): 20→20 single-page PDFs; each `page_count == 1`; sheet *i* text matches source page *i*; page cap raises.
- **Service/endpoints** (`tests/inbox/test_split_flow.py`, mirroring `test_upload.py`): analyze returns proposal without creating evidence; split runs N ingests, deletes staging, returns N outcomes, ownership 403, partial-failure reporting; commit ingests once.
- **Frontend:** drawing-set analyze response renders the proposal; "Keep as single" vs "Split" call the right API; non-drawing PDFs skip the prompt.

## Blast radius

Genuinely new code: detector, title extractor, splitter, three staging endpoints, one frontend panel extension. Unchanged and reused: object storage, `ingest_hosted_file`, classification, chunking/embedding, search, citations, the evidence/register read path. The split sheets are ordinary `project_evidence` documents with richer metadata.
