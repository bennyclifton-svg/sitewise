# Stage 11 — Invoice validation and reconciliation

**Goal:** Existing invoice checks become coded, severitied issues. Secondary
extraction runs only when a coded trigger fires. Never a second model call
for a clean invoice.
**Adapt validators. Do not write a second validation layer.**

**Ownership:** `backend/app/cost_plan/invoice_extraction.py`,
`invoice_mapping.py`, `invoice_service.py`, plus a small issues helper.
**Forbidden:** new invoice package, Pulse, posting, three-pane UI (Stage 12).
**Predecessor:** Stage 10 `[x]`.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D5, D6
- [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §7 Reconciliation / Validation issues
- `backend/app/cost_plan/invoice_service.py` `book_invoice` (allocation vs subtotal)
- `backend/app/cost_plan/schemas.py` `ExtractedInvoice.reconcile_totals`
- `backend/app/cost_plan/invoice_mapping.py`
- Stage 10 packet record (where totals live)

---

## Task 11.1 — Issue records on the invoice

JSONB on `cost_invoices` (no new table unless 10.3 already forced one):

```python
class InvoiceIssue(BaseModel):
    code: Literal[
        "TOTAL_MISMATCH",
        "GST_MISMATCH",
        "DUPLICATE_INVOICE",
        "CONFLICTING_DUPLICATE",
        "UNKNOWN_SUPPLIER",
        "ABN_MISMATCH",
        "UNKNOWN_COST_CODE",
        "PO_NOT_FOUND",
        "VARIATION_NOT_FOUND",
        "UNAPPROVED_VARIATION",
        "DATE_OUTSIDE_PERIOD",
        "AMOUNT_EXCEEDS_COMMITMENT",
        "COST_PLAN_OVERRUN",
        "CLAIM_EXCEEDS_REMAINING_VALUE",
        "MAPPING_LOW_CONFIDENCE",
    ]
    severity: Literal["error", "warning", "info"]
    field: str | None = None
    message: str
```

Store as `cost_invoices.issues JSONB NOT NULL DEFAULT '[]'`.
Python owns every code. LLMs must not invent codes.

**The column already exists** — Stage 10.1 adds it with the rest of the invoice
snapshot migration, because this stage owns no Alembic revision and migration
ordering is a single-owner seam. If `issues` is missing when you claim this
packet, that is a Stage 10 defect: raise an Integration note and stop. Do not
write a revision here.

**Failing test:** `test_total_mismatch_emits_coded_issue_not_exception`

---

## Task 11.2 — Adapt existing checks

Map what already runs:

| Existing behaviour | Code | Severity |
|---|---|---|
| `ExtractedInvoice.reconcile_totals` line vs subtotal | `TOTAL_MISMATCH` | error |
| subtotal + gst != inclusive | `GST_MISMATCH` | error |
| `book_invoice` duplicate same facts | `DUPLICATE_INVOICE` | info |
| `book_invoice` duplicate different facts | `CONFLICTING_DUPLICATE` | error |
| mapping `review_status=needs_review` | `MAPPING_LOW_CONFIDENCE` | warning |
| allocation total ≠ subtotal | `TOTAL_MISMATCH` | error |

Project-scoped checks (appointed supplier, ABN vs consultant fact, VO
approved, forecast movement) land **only if** the data is already on
`CostPlanState` / consultant facts. If a check needs a new table, skip it
and Integration-note it for Stage 12. Do not invent a consultant directory.

Replace raises-on-mismatch with "snapshot + issue". Booking may still refuse
to mark `booked` while any `severity=error` issue is open.

---

## Task 11.3 — Field reconciliation status

For each money/identity field, compute:

```text
status ∈ match | different | missing_primary | missing_secondary | missing_both
```

Primary = machine extraction. Reviewed = overlay. Secondary = optional second
pass (11.4). Persist under `machine_extraction.fields.<name>` or a sibling
`reconciliation` JSONB. Review UI (Stage 12) will highlight `different`.

**Failing test:** `test_reviewed_invoice_number_marks_field_different`

---

## Task 11.4 — Conditional secondary extraction

A function, not a hidden retry:

```python
def should_run_secondary(issues: list[InvoiceIssue], snapshot: dict) -> bool:
    ...
```

Triggers (from the product spec): missing required field · low confidence ·
`TOTAL_MISMATCH` / `GST_MISMATCH` · ambiguous line table · critical field
`different`. **If none fire, `should_run_secondary` is False.**

Implement the secondary pass as a **second deterministic parse** (different
regex/table heuristic), not an LLM, unless `TRACKER.md` § Accuracy already
shows the deterministic extractor failing. Default: no model.

**Failing test:** `test_clean_invoice_does_not_run_secondary_extraction`

---

## Exit gate

- [x] Clean invoice → zero error issues, no secondary pass
- [x] TOTAL_MISMATCH is a coded issue, not an uncaught ValueError
- [x] Duplicate/conflict still use existing `book_invoice` branches, now with codes
- [x] Mapping low-confidence is `MAPPING_LOW_CONFIDENCE`, not a new scorer
- [x] Failures ⊆ baseline
