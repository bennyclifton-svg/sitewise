# Stage 16 — Email attachments enter canonical intake

**Goal:** An email attachment is just another file on the one intake spine.
Manual upload and email receipt of the **same bytes** produce identical
classification, evidence, and invoice workflow. This is acceptance H and it
is the programme's non-negotiable email rule.

**Ownership:** `backend/app/email/` attachment ingest **adapter** only.
The adapter calls existing inbox/hosted ingest; it does not parse PDFs.
**Forbidden:** PDF/text extraction in `app/email/`, a second classifier,
Azure Document Intelligence, calling `classify_entry` directly from email
code, mutating `ingest/types.py`.
**Predecessor:** Stage 15 `[x]`.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D1, D2, D3, D8
- [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §9 "Email does not get
  its own attachment pipeline" + acceptance H
- `backend/app/inbox/service.py` (manual upload path)
- `backend/app/workflows/document_ingest.py`
- `ingest/hosted.py` `ingest_hosted_file`
- `ingest/hashing.py` `bytes_content_hash`
- `backend/app/cost_plan/invoice_service.py` `book_invoice`
- `backend/app/cost_plan/invoice_candidates.py`
- Stage 15 packet record
- This file

**The rule, again:**

```text
email attachment → canonical project intake → existing extraction
→ canonical classification → evidence → domain workflow
```

---

## Task 16.1 — Adapter: bytes in, inbox upload out

```python
# app/email/attachments.py
async def ingest_email_attachment(
    session,
    *,
    project: Project,
    email_id: uuid.UUID,
    filename: str,
    content: bytes,
    created_by_user_id: uuid.UUID,
) -> InboxUploadOutcome:
    """Store and ingest via the same inbox path as a manual upload."""
```

Must:

1. Hash with `bytes_content_hash` (same function as hosted ingest).
2. Call `inbox.service` upload (or the same `upsert_workspace_file` +
   `start_workflow_run` + `ingest_project_document` sequence that upload
   uses). **Do not fork a private ingest.** If the inbox function is too
   HTTP-shaped, extract a tiny internal helper **in `inbox/service.py`**
   and have both HTTP upload and email call it. State in the commit body
   what the helper replaces.
3. Write `content_hash` + `source_document_id` back onto
   `project_email_attachments`.
4. Pass `ingest_metadata={"source": "email", "email_id": str(email_id)}`
   so the workspace file is auditable. Classification must not read this
   key to decide class (D1).

Must not:

- Open the PDF in `app/email/`.
- Call `classify_entry`.
- Call `extract_invoice`.
- Write `document_class` itself.

**Failing tests:** `backend/tests/email/test_email_attachment_intake.py`

```text
test_ingest_email_attachment_calls_inbox_upload_not_classify_entry
test_attachment_hash_matches_bytes_content_hash
```

**Commit:** `feat: ingest email attachments through the inbox upload path`

---

## Task 16.2 — Equivalence test (exit of the email wave)

Two **different** projects, identical invoice PDF bytes (use a fixture
under `backend/tests/fixtures/` — a tiny synthetic PDF or the existing
classification fixture if it is an invoice; do not commit a real supplier
invoice).

Path A: `inbox` upload → wait ingest → `book_invoice` / process_invoices.
Path B: `ingest_email_attachment` → same.

Assert:

```text
content_hash A == content_hash B
source_documents.document_class A == B
document_metadata.commercial_type A == B   # typically invoice
cost_invoices.machine_extraction A == B    # see the volatile-field note
cost_invoices.review_state A == B
```

**⚠ `machine_extraction A == B` as raw JSON equality will fail, and it will
look like the adapter is broken when it is not.** The snapshot is
`ExtractedInvoice.model_dump(mode="json")` (Stage 10.1), and anything in it
derived from *when* or *where* the extraction ran differs between two runs
on two projects — provenance locators, per-field confidence tie-breaks,
timestamps, and any id echoed into the payload.

Compare through a normaliser, and make what it strips explicit:

```python
VOLATILE = {"extracted_at", "run_id", "source_document_id", "project_id"}

def comparable(snapshot: dict) -> dict:
    return {k: v for k, v in snapshot.items() if k not in VOLATILE}
```

Then assert `comparable(A) == comparable(B)`. Keep `VOLATILE` **as small as
you can defend** — every key you add is equivalence you stopped checking.
If you find yourself excluding `invoice_number` or a money field, stop: the
adapter really is broken and the test just caught it. Assert the money
fields explicitly and separately so they can never be normalised away:

```python
assert A["subtotal_ex_gst"] == B["subtotal_ex_gst"]
assert A["gst"] == B["gst"]
assert A["total_including_gst"] == B["total_including_gst"]
assert A["invoice_number"] == B["invoice_number"]
```

Also note `InboxUploadOutcome` in the 16.1 sketch is an **invented name** —
no such type exists today. Return whatever `inbox/service.py` upload
actually returns, or define the type in the email package and say so in the
commit body.

Do **not** run A then B on the same project — `skip_if_unchanged` and
duplicate-invoice detection would hide a broken adapter.

If `book_invoice` needs a cost plan, copy the existing
`tests/cost_plan/test_invoice_processing.py` fixture setup.

**Failing test:** `test_email_invoice_matches_manual_upload_downstream`

This test is the Stage 16 exit. If it is skipped or marked xfail, the
packet is not `[x]`.

**Commit:** `test: email and upload of the same invoice bytes agree`

---

## Task 16.3 — Unmatched email does not ingest onto a guessed project

If `project_email_interpretations.project_id` is null, attachment ingest
**refuses** (raises a typed error). Stage 17 matching / user link happens
first. Silently filing onto the wrong project is worse than leaving the
bytes on the raw email.

**Failing test:** `test_unmatched_email_attachment_is_not_ingested`

Stage 22 aliases always have `project_id`, so they pass.

**Commit:** `feat: refuse email attachment ingest without a project match`

---

## Exit gate

- [x] Equivalence test green (not skipped)
- [x] `grep classify_entry backend/app/email` empty
- [x] `grep extract_invoice backend/app/email` empty
- [x] Adapter production LOC is an inbox call plus bookkeeping
- [ ] Backend failures ⊆ baseline — extra names recorded in TRACKER (not this packet)

**After this stage:** [`stage-17-email-matching.md`](./stage-17-email-matching.md).
