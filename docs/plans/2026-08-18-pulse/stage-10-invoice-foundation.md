# Stage 10 — Invoice review foundation

**Goal:** Every invoice has an immutable machine-extraction snapshot and a
separate reviewed overlay. Changing a reviewed value never changes the raw
value (D5).
**This stage does not add Azure Document Intelligence. It does not add
`backend/app/invoice/`.**

**Ownership:** `backend/app/cost_plan/` invoice modules + one Alembic revision.
**Forbidden:** new package, Pulse UI, email, TCM, `ingest/types.py`.
**Predecessor:** Stage 9.5 `[x]` (discovery from `commercial_type`).

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D1, D5, D6, D7
- [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §7 Immutable extraction
- `backend/app/cost_plan/models.py` (`CostInvoice`, `processing_status`)
- `backend/app/cost_plan/invoice_service.py` `book_invoice`
- `backend/app/cost_plan/invoice_extraction.py` `extract_invoice`
- `backend/app/cost_plan/schemas.py` `ExtractedInvoice`
- `TRACKER.md` Stage 9.5 packet record

---

## What already exists (extend, do not replace)

```text
invoice_candidates.py     discover candidates (9.5 makes this classification-first)
invoice_extraction.py     regex/markdown extract → ExtractedInvoice
invoice_mapping.py        construction cost-item mapping (keep)
invoice_service.py        book_invoice / ledger / field updates
evidence_reconciliation.py  fee-proposal → cost plan (not this stage)
CostInvoice               scalars + extraction_provenance JSONB
processing_status         booked | needs_review | void
InvoiceFieldsUpdate       already edits supplier/number/dates on the same row
```

**The D5 bug:** `InvoiceFieldsUpdate` writes over `CostInvoice.invoice_number`
etc. There is no copy of what the machine saw. `ExtractedInvoice.reconcile_totals`
**raises** on arithmetic mismatch, so a dirty invoice never becomes a reviewable
row.

---

## Task 10.1 — Persist the machine snapshot

Alembic revision (keep the id ≤ 32 chars, see Stage 5 note):
`050_invoice_machine_snapshot`.

Alembic head is `049_canonical_document_taxonomy` (Stage 8). Stage 8B amends 049
in place and adds **no** revision, so `050` is genuinely free — confirm with
`uv run alembic heads` before writing, not by reading this line.

Add to `cost_invoices`:

```text
machine_extraction   JSONB NOT NULL DEFAULT '{}'
reviewed_extraction  JSONB NOT NULL DEFAULT '{}'
reviewed_by_user_id  UUID NULL REFERENCES users(id)
reviewed_at          timestamptz NULL
issues               JSONB NOT NULL DEFAULT '[]'
```

`users.id` is the correct FK target (`models.py:225` already uses it).

**`issues` is added here even though Stage 11 fills it.** Stage 11's ownership
block does not include a migration, and migration ordering is a single-owner
seam (`90-downstream-stages.md`). Adding the empty column now costs one line
and removes a cross-stage collision. Do not add Stage 11's `InvoiceIssue`
*logic* here — column only.

`machine_extraction` is the `ExtractedInvoice.model_dump(mode="json")` at
extract time. Application code must refuse `UPDATE` of that column after
insert (service-layer guard + test). Do not add a Postgres trigger unless the
service guard is insufficient.

**Failing test:** `tests/cost_plan/test_invoice_machine_snapshot.py`

```python
def test_updating_reviewed_invoice_number_does_not_change_machine_snapshot() -> None:
    ...
    assert invoice.machine_extraction["invoice_number"] == "INV-1O42"
    assert effective_invoice_number(invoice) == "INV-1042"
```

---

## Task 10.2 — Effective values = reviewed overlay machine

One helper, used by booking arithmetic, ledger, and UI:

```python
def effective_extraction(invoice: CostInvoice) -> ExtractedInvoice:
    payload = {**invoice.machine_extraction, **invoice.reviewed_extraction}
    return ExtractedInvoice.model_validate(payload)
```

Empty-dict overlay means "no review yet" → machine wins.

**This shallow merge is correct for scalars and wrong for `lines`.**
`ExtractedInvoice.lines` is a list. A reviewer correcting one line amount would
have to resubmit the whole list, and any overlay containing `lines` replaces
every machine line wholesale — silently discarding lines the reviewer never
looked at. Decide explicitly and write the test:

- **Recommended:** overlay scalars only; keep `lines` machine-owned this stage
  and reject a `reviewed_extraction` payload containing `lines` with a typed
  error. Line-level review is Stage 12 UI work and needs a line identity key
  that does not exist yet.
- If you do allow line edits, merge per line on a stable key (not list index —
  a re-extract reorders them).

**Failing test:** `test_reviewed_overlay_cannot_silently_replace_machine_lines`

`book_invoice` writes scalars from the **machine** snapshot on insert, then
copies the same dump into `machine_extraction`. Subsequent `InvoiceFieldsUpdate`
writes **only** `reviewed_extraction` (+ `reviewed_by_user_id` / `reviewed_at`)
and refreshes display scalars from `effective_extraction`. It must not assign
into `machine_extraction`.

Keep `processing_status` as `booked | needs_review | void` this stage.
Stage 12 widens the state machine.

---

## Task 10.3 — Dirty invoices still persist

Today `ExtractedInvoice.reconcile_totals` raises. A TOTAL_MISMATCH must still
produce a `CostInvoice` with `processing_status="needs_review"` and the
machine numbers as observed.

Split "parse fields" from "validate arithmetic":

- `extract_invoice` always returns a snapshot (required fields may be missing).
- Python validation in Stage 11 emits coded issues.
- For 10.3, persist even when `subtotal + gst != total`.

**There are three blockers, not one.** Verified against
`alembic/versions/040_cost_plan_invoice_ledger.py:104-118` and
`app/cost_plan/schemas.py:249-267`:

| Blocker | Where | Fires on |
|---|---|---|
| `ck_cost_invoices_total_reconciles` | 040:114 | `subtotal + gst != total` |
| `ck_cost_invoices_positive_amounts` | 040:110 | `subtotal <= 0`, `gst < 0`, `total <= 0` |
| `reconcile_totals` raises | `schemas.py:256` | non-positive **and** line-total ≠ subtotal |

A scanned invoice with a missing subtotal trips the *second* constraint, not the
first. Handle all three or the packet only half-works.

**Recommended:** store untrusted machine numbers in `machine_extraction` JSONB
only, keep the typed scalars for *effective booked* amounts, and leave both
check constraints in force on those scalars. That way a dirty invoice persists
with `processing_status="needs_review"` and null/zero booked scalars, and the
ledger's arithmetic guarantees are untouched. Relaxing the constraints is the
alternative — if you choose it, say so in the packet record and explain what
now protects the ledger.

Record the choice in `TRACKER.md` Integration notes either way.

**Failing test:** `test_extract_with_total_mismatch_still_inserts_machine_snapshot`

Never a second model call in this stage.

---

## Task 10.4 — Provenance on each machine field

`ExtractedInvoice.provenance` already exists as a blob. Shape it per field:

```text
invoice_number: {source: "header_regex", locator: "line 4", confidence: 0.82}
```

No new columns. Mapping stays in `invoice_mapping.py`.

**Commit (10.1–10.4, one packet each if they sprawl):**
`feat: keep invoice machine extraction immutable beside reviewed values`

---

## Exit gate

- [x] Changing a reviewed value never mutates `machine_extraction`
- [x] Ledger/API read effective (overlay) values
- [x] Arithmetic-mismatch invoices persist as `needs_review`
- [x] No `invoice/` package; no Azure Document Intelligence
- [ ] Alembic upgrade → downgrade → upgrade rehearsed (not run — no live DB)
- [x] Failures ⊆ Stage 0 baseline
