# Stage 9 — Consumer behaviour on the frozen contract

**Goal:** Downstream readers *use* canonical `document_class` + `document_subject`
+ metadata (`discipline`, `commercial_type`, `procurement_stage`), instead of
filename regexes that duplicate Classifier A.
**Mechanical class-string migration already landed in Stage 8.3.** Do not redo it.

**Ownership:** one packet per consumer. `RetrievalFilters` is a shared
interface — packet 9.1 is single-owner and lands first.
**Forbidden:** `ingest/types.py` vocabularies, a second classifier, a new
`invoice/` package, any Clerk-core import from `backend/tender/`.

**Predecessor:** Stage 8 `[x]`, **Stage 8B Wave A `[x]`** (8B.1–8B.4), and the
Gate 2 human signature in `TRACKER.md` — in that order — before any production
packet (9.1+). Packet 9.0 is docs-only and may run unsigned.

Wave A matters here specifically: 8B.1 changes what `document_metadata` survives
a user override, and 9.3/9.4/9.5 all assert on metadata that today gets wiped.
Writing those tests first would bake in the bug.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D1, D3, D8, canonical vocabularies
- [`01-ground-truth.md`](./01-ground-truth.md) — **stale at Gate 2; 9.0 rewrites it**
- `TRACKER.md` § Gate 2 and § Integration notes (Stage 8)
- This file

**Already true (do not rebuild):**

| Capability | Where |
|---|---|
| Filter by `document_class` | `app/retrieval/queries.py` |
| Filter by `procurement_stage` metadata | same |
| Drawing register `== "drawing"` + title-block fields | `app/retrieval/register.py` |
| Specification trade-section chunker | `ingest/chunkers/specification.py` |
| Drawing bounded chunker | `ingest/chunkers/register.py` |
| `commercial_type` / `procurement_stage` emitted at classify | `ingest/classify.py` |
| Subject persisted as `document_metadata.subject` | `ingest/persist.py` (no `document_subject` column) |

**Real gaps this stage closes:**

| # | Gap |
|---|---|
| 9.1 | `RetrievalFilters` has no `document_subject` or `discipline` |
| 9.2 | `schedule` still uses the prose chunker |
| 9.3 | Drawing register is already correct — verify + regression only |
| 9.4 | Consultant facts still sniff `_CERT_HINT` on filename |
| 9.5 | Cost Plan / invoice discovery still sniff filename+content, not `commercial_type` |
| 9.6 | PMP evidence still keys off path markers (`planning-pathway`, `heritage`) |
| 9.7 | Tender Comparison must not grow a second Clerk classifier; Clerk already exposes `procurement_stage` |
| 9.8 | Transmittal markdown does not require drawing class + revision metadata |

**Conflict warning:** 9.1 owns `retrieval/schemas.py` and `retrieval/queries.py`.
No other packet edits those files. Two agents in `retrieval/` at once will conflict.

---

## Task 9.0 — Refresh ground truth (docs only)

`01-ground-truth.md` still describes two classifiers, drawing-driven
`register_only` suppression, `inbox_pending`, and `corpus_catalog` writes.
A Wave 2 agent that trusts it will "fix" Stage 1–8.

Rewrite the file against HEAD (post-Stage-8B). Keep the same sections.
Update `00-doctrine.md` §D2 parenthetical: Sort Files no longer calls
`_file_previews`; `repair_service` still does.

**The consumer list is the part that failed.** Gate 2 certified "all 14
consumers read canonical classification" and that was true and insufficient —
`source_documents.document_type` was never on the list, so it kept legacy
values and kept rendering them to users. Rebuild the list by grep against the
column and the model, not by editing the old list. It must now include, at
minimum, everything Stage 8B touched.

Facts the rewritten file must state, because a Wave 2 agent will otherwise
"discover" them and fix them out of scope:

| Fact | Where |
|---|---|
| Content markers do **not** run on production ingest — `hosted.py` and `pipeline.py` call `classify_entry` without `extracted_text` | `ingest/hosted.py:44`, `ingest/pipeline.py:76` |
| `title_block` is never passed in production either | same |
| `machine_*` metadata keys are the classifier's own answer (8B.2) | `ingest/persist.py` |
| `document_type` is dead — do not read or write it (8B.5) | `app/database/source_document.py:28` |
| `ingest_mode` follows useful text, not class (8B.6) | `ingest/router.py` |
| `filing_destination` gates routing metadata on class (8B.1) | `app/intake/classifier.py` |
| `repair_service` is the only remaining `classify_inbox_destination` caller | `app/intake/repair_service.py:132` |

**No production code.** Commit message:

```text
docs: refresh X1 ground truth against Gate 2
```

---

## Task 9.1 — Retrieval filters for subject and discipline 🔒

Shared interface. Land this before 9.4–9.8 if they need filtered retrieval.

**Files:**
- Modify: `backend/app/retrieval/schemas.py` (`RetrievalFilters`)
- Modify: `backend/app/retrieval/queries.py` (`apply_document_filters`)
- Test: `backend/tests/retrieval/test_queries.py` (create if missing)

Subject lives in JSONB, not a column:

```python
if filters.document_subject is not None:
    stmt = stmt.where(
        SourceDocument.document_metadata["subject"].astext
        == filters.document_subject
    )
if filters.discipline is not None:
    stmt = stmt.where(
        SourceDocument.document_metadata["discipline"].astext
        == filters.discipline
    )
```

Unknown documents must still return when those filters are unset (D3).

**Failing test:**

```python
def test_apply_document_filters_matches_subject_and_discipline() -> None:
    filters = RetrievalFilters(document_subject="structural", discipline="structural")
    stmt = apply_document_filters(select(SourceDocument.id), filters)
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "subject" in sql
    assert "discipline" in sql
```

Wire `document_subject` through `app/assistant/agent.py` `search_documents`
the same way `procurement_stage` already is. Do not invent a new MCP tool.

**Commit:** `feat: filter retrieval by subject and discipline metadata`

---

## Task 9.2 — Row-aware chunker for `schedule`

**Files:**
- Create: `backend/ingest/chunkers/schedule.py` (replaces prose for this class only)
- Modify: `backend/ingest/router.py` `_chunker_for`
- Modify: `backend/tests/ingest/test_classification_contract.py` (allow `"schedule"` chunker)
- Test: `backend/tests/ingest/test_schedule_chunker.py`

Split on markdown/table rows or numbered schedule lines. One row → one chunk
when the row is short; never a single 20-page programme blob.

Specification and drawing chunkers stay. Do not "improve" them in this packet.

**Failing test:** `test_schedule_table_emits_one_chunk_per_row`

**Commit:** `feat: chunk schedules by row instead of prose windows`

---

## Task 9.3 — Drawing register regression

**Files:** none unless the test fails.
- Verify: `backend/app/retrieval/register.py` (`== "drawing"`, metadata title/revision/number)
- Test: extend `backend/tests/retrieval/` drawing-register tests if thin

Confirm a `drawing` with title-block metadata appears; a `report` with "plan"
in the filename does not.

**Add the case Stage 8B.1 fixed**, because it is the one that actually broke:
a drawing whose class a **user overrode** and then re-ingested must still carry
`drawing_number` / `revision` / `title` and still appear in the register.
Before 8B.1 the override wiped those keys and the row silently left the
register. This regression test is the guard against that returning.

**Commit only if code changes.** Otherwise tick in `TRACKER.md` with the
passing command.

---

## Task 9.4 — Consultant facts from class + subject

**Files:**
- Modify: `backend/app/projects/consultant_facts.py` `evidence_status_for_kind`
- Test: existing consultant-facts tests (grep `evidence_status_for_kind`)

Delete `_CERT_HINT` as the primary signal. Certificate class wins; subject
`planning` may still mean a CDC/CC. Filename is last resort only if class is
`unknown`.

**Failing test:** a file named `Certificate-looking-report.pdf` classified
`report` must **not** get `"Certificate/DCD on file"`.

**Commit:** `feat: derive consultant evidence status from classification`

---

## Task 9.5 — Cost Plan / invoice discovery from `commercial_type`

**This packet is larger than it looks — read this before claiming it.**
`is_invoice_document(*, filename: str, content: str)`
(`invoice_candidates.py:40`) has **no access to the document at all**. Making
discovery classification-first is a signature change plus every call site:

| Call site | Owner | Note |
|---|---|---|
| `app/cost_plan/invoice_candidates.py:149` | 9.5 | in-file |
| `app/api/projects.py:1014` | 9.5 | passes `preview.filename` / `preview.excerpt` |
| `app/cost_plan/invoice_extraction.py:50` | **Stage 11** | see below |
| `tests/cost_plan/test_invoice_processing.py:17` | 9.5 | import + cases |

**Ownership resolution:** 9.5 owns the `invoice_extraction.py:50` call site
*for the signature change only* — one line, no behaviour change. Stage 11 owns
everything else in that file. Record it as an Integration note when you claim
the packet so the Stage 11 agent is not surprised.

`_looks_like_fee_proposal(document: SourceDocument)`
(`consultant_appointment.py:525`) already receives the document — that half is
genuinely small.

**Files:**
- Modify: `backend/app/cost_plan/invoice_candidates.py` `is_invoice_document`
  (take the `SourceDocument`, or `document_class` + `document_metadata`
  explicitly; do not thread a session into it)
- Modify: `backend/app/cost_plan/consultant_appointment.py` `_looks_like_fee_proposal`
- Modify: `backend/app/api/projects.py:1014` (call site)
- Modify: `backend/app/cost_plan/invoice_extraction.py:50` (call site only)
- Test: `backend/tests/cost_plan/test_invoice_processing.py`

D1: invoice discovery reads `document_class == "commercial"` and
`document_metadata.commercial_type == "invoice"`. Keep the regex **only** as
a fallback when class is `unknown` (pre-classify uploads). Same for fee
proposals → `commercial_type == "fee_proposal"`.

Do not change `book_invoice` or extraction behaviour in this packet (Stage 10).

**Failing tests:**

```text
test_classified_invoice_is_discovered_without_filename_hint
test_unknown_class_document_still_falls_back_to_the_regex
test_non_commercial_document_with_invoice_in_the_filename_is_not_a_candidate
```

**Commit:** `feat: discover invoices and fee proposals from commercial_type`

---

## Task 9.6 — PMP evidence from class + subject

**⚠ The original framing of this packet was wrong. Corrected 2026-08-19.**

`mobilisation_evidence.py` does **not** key off path or filename markers. Two
things are actually true:

1. Its signature is
   `extract_mobilisation_evidence_pack(source_texts: list[str], evidence_refs, source_labels)`.
   It receives **raw text** and has no access to `document_class`,
   `document_subject`, or the `SourceDocument` at all.
2. Its markers are **content** scrapers over the concatenated text
   (`"heritage impact statement" not in lowered`, `mobilisation_evidence.py:492`).
   They extract *advice prose* into structured fields. Replacing them with
   `subject == "heritage"` would delete the extraction, not improve the
   selection.

Selection is not filtered at all today: `pmp_sweep.py:187` sweeps every active
document up to `settings.pmp_sweep_max_documents` and passes
`document.normalized_content` for each.

**So the real gap is selection, and it lives in the callers.** Scope this
packet to ranking/selection, and leave the content extractors alone.

**Files:**
- Modify: `backend/app/sitewise/pmp_sweep.py` — order and cap the sweep by
  classification before batching, so the cap spends its budget on planning /
  heritage / statutory evidence rather than on whatever sorted first
- Test: `backend/tests/workflows/test_update_pmp_sweep.py`

Preferred evidence: `document_class in {"report","statutory_instrument","certificate"}`
with `subject in {"planning","heritage"}`, then everything else. `unknown` rows
must still be swept — they are 43% of the corpus until Stage 8B.8 runs, and
D3 forbids classification removing evidence.

**Do not** change `extract_mobilisation_evidence_pack`'s signature. It has four
call sites (`pmp_sweep.py:187`, `cost_plan_evidence.py:239`,
`create_pmp.py:1277`, and itself), and `create_pmp.py` carries a pre-existing
baseline failure — you will not be able to tell your regression from that one.

**Failing test:** `test_sweep_prioritises_planning_and_heritage_evidence_under_cap`

**Commit:** `feat: rank PMP evidence sweep by classification`

---

## Task 9.7 — Tender Comparison (Clerk side only)

TCM has its **own** `document_classification` entity in `backend/tender/`.
That is schema-oriented extraction, not Clerk `document_class`. **Do not
merge them.**

This packet only proves Clerk can list submissions without a filename
convention:

```python
RetrievalFilters(document_class="commercial", procurement_stage="submission")
```

That filter already exists. Add a regression test under `tests/retrieval/`
that a `commercial` + `procurement_stage=submission` row matches and a
filename like `Tenderer-01.pdf` classified `unknown` does not.

**Forbidden:** editing `backend/tender/services/classification.py`.
**Commit only if a test file is added.**

---

## Task 9.8 — Transmittals carry drawing class + revision

**Files:**
- Modify: `backend/app/workflows/transmittal.py` `render_transmittal_markdown`
- Test: `backend/tests/workflows/` transmittal tests (create if missing)

Each selected drawing row must render `document_class`, `document_number` /
drawing number, and `revision` from `source_documents.document_metadata`.
Non-drawings may still appear (specs, reports) but must not be labelled as
drawings.

**Commit:** `feat: render transmittal rows from classification metadata`

---

## Exit gate

- [x] Stage 8B Wave A `[x]` and Gate 2 signed **before** 9.1 started
- [x] 9.0 ground truth rewritten from a fresh grep; `document_type` and the
      `machine_*` keys are in the consumer list; doctrine D2 parenthetical corrected
- [x] 9.1 filters compile and unknown docs still return when unfiltered
- [x] 9.2 schedule chunker in `_chunker_for`; spec/drawing unchanged
- [x] 9.3 drawing register regression green
- [x] 9.4 `_CERT_HINT` is not the primary consultant signal
- [x] 9.5 invoice/fee-proposal discovery prefers `commercial_type`; the
      `invoice_extraction.py` call-site edit is Integration-noted for Stage 11
- [x] 9.6 sweep ranks by classification; `extract_mobilisation_evidence_pack`
      signature unchanged; `unknown` rows still swept
- [x] 9.7 no new Clerk→tender imports; submission filter test exists
- [x] 9.8 transmittal lists revision for drawings
- [x] `uv run pytest -q --tb=line --import-mode=importlib` failures ⊆ baseline
      (after document_context getattr fix; 4 FAILED names match Stage 0)
- [x] LOC gate vs Stage 0.6 still <10% *or* justified (chunker addition is the likely bump)

**Do not start Stage 10 until 9.5 is `[x]`** — invoice review must discover
candidates from classification, not a third regex.
