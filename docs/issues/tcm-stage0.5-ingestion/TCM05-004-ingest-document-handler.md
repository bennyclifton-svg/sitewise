---
title: Implement the ingest_document Handler
status: ready-for-agent
type: AFK
triage_label: ready-for-agent
labels: [ready-for-agent, tender, backend, ingestion, worker]
source: docs/plans/2026-06-13-tcm-stage0.5-ingestion-classification.md
---

# Implement the `ingest_document` Handler

## Parent

TCM Stage 0.5 — Ingestion, Classification & Extraction Wiring
([plan](../../plans/2026-06-13-tcm-stage0.5-ingestion-classification.md), Task 3).

## What to Build

Replace the stub at `backend/tender/services/ingestion.py` (currently
`raise NotImplementedError("ingest_document lands in the next commit")`) with the real
ingestion stage (PRD §7.4 / §9.1). End to end, for an uploaded quote document it:

1. Loads the `TenderDocument` from `job.payload["document_id"]`.
2. **Dedupes** within the quote: if another *ingested* doc in the same `quote_id` shares
   `content_hash` → mark this `ingest_status='duplicate'` and stop.
3. **Format gate:** non-PDF → `ingest_status='unsupported_format'` and stop.
4. **Per-page OCR decision:** download bytes, extract pages (TCM05-002); for OCR
   candidates render the page (TCM05-003) and run injected OCR → `(text, mean_confidence)`;
   non-candidates use the text layer (`ocr_confidence=None`).
5. **Escape hatch:** if pages were OCR'd and the mean confidence across them
   `< tender_ocr_min_confidence` → `ingest_status='manual_transcription_required'`,
   emit **no** pages, stop.
6. **Checkpointed persist:** for each page not already in `tender_pages` (resume via
   `UNIQUE(document_id, page_no)`), render PNG, upload to storage, insert the page row,
   `flush()` per page so a crash resumes mid-document.
7. **Finish:** set `page_count`, `ocr_applied`, `ingest_status='ingested'`, advance
   `quote.stage='classify_document'`, and enqueue the next job.

OCR and storage are **injected** (`downloader`, `uploader`, `ocr`) so unit tests never
touch Tesseract or Supabase. Defaults wire `app.storage.project_files` +
`pytesseract`.

## Decision baked in: render-then-OCR-the-image

For OCR-candidate pages, OCR the 150-DPI PNG we already render (via
`pytesseract.image_to_data`) rather than running `ocrmypdf` on the whole file. This
yields **per-page text and a per-page mean word confidence** in one pass. Both require
Tesseract on the host. If you prefer `ocrmypdf`, raise it before implementing.

## Files

- Rewrite: `backend/tender/services/ingestion.py`
- Test: `backend/tests/tender/test_ingestion.py`

## TDD (write these first)

Cover, with mocked downloader/uploader/ocr and synthetic PDFs (plan Task 3, Step 1 has
the full test file):

- `test_ingest_persists_pages_and_marks_ingested` — text PDF → one `tender_pages` row,
  `ingest_status='ingested'`, `page_count==1`, `ocr_applied is False`, one upload call.
- `test_unsupported_format_short_circuits` — `mime='text/plain'` → `unsupported_format`.
- `test_low_ocr_confidence_flags_manual_transcription` — image-only PDF + injected OCR
  returning `mean_confidence=0.10` → `manual_transcription_required`, **zero** pages persisted.
- `test_resume_skips_already_persisted_pages` — pre-insert page 1 → nothing re-uploaded.
- `test_duplicate_hash_short_circuits` — sibling `ingested` doc with same hash → `duplicate`.

Reuse the existing async DB fixture used by `test_jobs.py` / `test_map_items_handler.py`.

## Reference implementation

The complete handler is in the plan (Task 3, Step 3). Key shape:

```python
async def ingest_document(session, job, *, downloader=None, uploader=None, ocr=None) -> None:
    downloader = downloader or _default_downloader   # app.storage.project_files.download_project_file
    uploader = uploader or _default_uploader         # app.storage.project_files.upload_project_file
    ocr = ocr or _default_ocr                        # pytesseract.image_to_data on the PNG
    ...
```

- Image storage key:
  `tender/comparisons/{job.comparison_id}/quotes/{document.quote_id}/documents/{document.id}/pages/page-{n:04d}.png`
- Wrap the sync storage calls in `asyncio.to_thread(...)` (as the router already does).
- `OcrResult` dataclass `(text: str, mean_confidence: float)` is part of this module and
  is imported by the tests.
- Use config: `tender_ocr_enabled`, `tender_ocr_text_density_threshold`,
  `tender_ocr_min_confidence`, `tender_page_render_dpi`.
- The chain enqueue (`kind='classify_document'`) lives here; its end-to-end wiring is
  verified in TCM05-007.

## Acceptance Criteria

- [ ] `ingest_document` no longer raises `NotImplementedError`; implements steps 1–7 above.
- [ ] Dedupe, unsupported-format, escape-hatch, resume, and happy-path are all covered by passing tests.
- [ ] Pages persist one-by-one with a `flush()` per page (checkpoint/resume).
- [ ] OCR and storage are injected; no test touches Tesseract or Supabase.
- [ ] On success: `ingest_status='ingested'`, `page_count`/`ocr_applied` set, `quote.stage='classify_document'`, and a `classify_document` job is enqueued.
- [ ] `uv run pytest tests/tender/test_ingestion.py -v` passes; `uv run ruff check tender/services/ingestion.py` clean.

## Blocked By

- `TCM05-003-page-render-150dpi-png.md` (and transitively 002, 001)

## Agent Brief

**Category:** feature (worker handler)
**Summary:** Real document ingestion — dedupe, OCR detection, page render, checkpointed persist, chain to classify.
**Key interfaces:** `tender/services/pdf.py`, `app.storage.project_files`, `pytesseract`, `tender.services.jobs.enqueue`, `TenderDocument`/`TenderPage`/`TenderQuote`.
**Current behavior:** Stub raises `NotImplementedError`; every enqueued `ingest_document` job fails through retry/backoff to `failed`.
**Desired behavior:** Uploaded PDFs are ingested into `tender_pages` and the pipeline advances.
**Out of scope:** XLSX/DOCX (TCM05-009), classification (TCM05-005), extraction (TCM05-006).

### Triage Brief

> *This was generated by AI during triage.*

**Category:** enhancement
**State:** ready-for-agent
**Summary:** Replace the ingestion stub with the real PDF ingestion worker stage.

**Current behavior:**
`ingest_document` raises `NotImplementedError`, so queued ingestion jobs fail and uploaded quote documents never create `tender_pages` records or advance to classification.

**Desired behavior:**
The handler loads the target document, rejects unsupported formats, detects duplicates, extracts text, renders page PNGs, OCRs low-density pages through an injected OCR function, persists each page idempotently, records ingestion metadata, advances the quote to `classify_document`, and enqueues the next job.

**Key interfaces:**
- `ingest_document(session, job, *, deps=None, downloader=None, uploader=None, ocr=None)` - worker handler with injectable external boundaries.
- PDF helpers - extract text, decide OCR candidates, and render page PNGs.
- Storage upload/download functions - real defaults, fakeable in unit tests.
- OCR function - real default backed by pytesseract, fakeable in unit tests.
- `TenderDocument`, `TenderPage`, `TenderQuote`, and tender job enqueueing.

**Acceptance criteria:**
- [ ] PDFs ingest into one `TenderPage` per page with image path and text content.
- [ ] Existing page rows are skipped on re-run.
- [ ] Unsupported non-PDF documents are marked `unsupported_format` and do not chain.
- [ ] Duplicate documents in the same quote are marked `duplicate` and do not emit pages.
- [ ] Low-confidence OCR pages mark the document `manual_transcription_required` and emit no pages.
- [ ] Successful ingestion marks status/page count/OCR metadata, advances quote stage, and enqueues `classify_document`.
- [ ] Focused tests and lint pass.

**Out of scope:**
- XLSX/DOCX conversion.
- Document classification.
- Line-item extraction.

## Implementation Notes

- Commit: `feat(tender): implement ingest_document — dedupe, OCR detection, page render, checkpointed persist`.
