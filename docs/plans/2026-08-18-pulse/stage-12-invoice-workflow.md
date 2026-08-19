# Stage 12 — Invoice workflow and review UI

**Goal:** No invoice reaches a posted/booked-as-final state without an
authorised approval (D7). Review is three panes with disagreement
highlighting. Frontend may ship against fixtures until 12.1 lands.

**Ownership:** backend `cost_plan` invoice service +
`frontend/src/components/project/CostInvoiceRegister.tsx` (extend, do not
replace with a parallel register).
**Forbidden:** Pulse, email, posting to an accounting package, new invoice app.
**Predecessor:** Stage 11 `[x]`.

**Reading list:**
- [`00-doctrine.md`](./00-doctrine.md) §D5, D6, D7
- [`../2026-08-18-pulse.md`](../2026-08-18-pulse.md) §7 States and boundary
- `backend/app/cost_plan/models.py` `processing_status`
- `frontend/src/components/project/CostInvoiceRegister.tsx`
- `frontend/src/components/project/InvoiceProcessStatus.tsx`
- Stage 10–11 packet records

---

## Task 12.1 — Explicit review states

Today: `processing_status IN ('booked','needs_review','void')` and `paid: bool`.

Add `review_state` (do not overload `paid`):

```text
received
extracting
ready_for_review
needs_attention
approved
rejected
posted          # Stage 12 may treat booked+approved as posted-in-SiteWise
duplicate
conflict
```

Payment stays separate: keep `paid` **or** replace with
`payment_status IN ('unpaid','scheduled','paid')` in the same migration.
Never conflate reviewed / approved / posted / paid.

Widen or replace `ck_cost_invoices_processing_status`
(`alembic/versions/040_cost_plan_invoice_ledger.py:106`, currently
`IN ('booked','needs_review','void')`). Prefer a new `review_state` column so
existing `booked` rows migrate.

Two mechanical notes, both verified: `processing_status` is `String(24)`
(`models.py:215`), so `ready_for_review` (16) and `needs_attention` (15) fit
without a type change; and this stage needs its own Alembic revision — `051` if
Stage 10 took `050`. Confirm with `uv run alembic heads`, do not assume.

| Old `processing_status` | New `review_state` |
|---|---|
| `booked` | `posted` (already in the ledger — record this choice) |
| `needs_review` | `needs_attention` |
| `void` | `rejected` |

**Failing test:** `test_book_invoice_without_approval_cannot_reach_posted`
for *new* invoices after this migration. Historical `booked` rows are the
grandfathered exception, listed in `TRACKER.md`.

Transitions are a Python table in `invoice_service.py`. Illegal transition
raises. Approval requires `actor_id` (existing user). No silent
high-confidence auto-approve (D7). High confidence may land in
`ready_for_review`, never `approved`.

---

## Task 12.2 — Hold / Reject / Approve API

One service used by REST and (later) Pulse cards:

```python
async def decide_invoice(
    session,
    *,
    project_id,
    invoice_id,
    actor_id,
    decision: Literal["hold", "reject", "approve"],
    reason: str | None,
) -> CostInvoice:
    ...
```

- `hold` → `needs_attention`
- `reject` → `rejected` (not void unless you document why)
- `approve` → `approved`, then existing booking/ledger publish may set `posted`

Project authorization same pattern as `PUT .../classification` (Stage 5.4).

**⚠ Corrected 2026-08-19 — the status codes below contradicted the pattern this
task says to copy.** Stage 5.4 is explicit: *"404, not 403 — do not leak
existence across tenants"*, and `backend/AGENTS.md` calls project authorization
a test-first security seam. A 403 on a cross-project invoice confirms that the
invoice exists. Use:

| Case | Status |
|---|---|
| Invoice belongs to another project | **404** — never 403 |
| Caller is not the project owner | **404** — same reason |
| Open `severity=error` issues block approval | **409** |
| Illegal state transition | **409** |

409 is correct for the last two: the caller is authorised and the resource
exists; the request conflicts with current state.

**Failing tests:**

```text
test_decide_invoice_on_another_projects_invoice_returns_404
test_decide_invoice_by_non_owner_returns_404
test_approve_with_open_error_issues_returns_409
test_illegal_transition_returns_409
```

REST: `POST /projects/{id}/invoices/{invoice_id}/decision`

---

## Task 12.3 — Three-pane review UI

Extend the register; do not add `InvoiceReviewApp.tsx` as a second product.

Panes:

1. Original — existing workspace-file preview / excerpt
2. Extraction — per-field machine | secondary | reviewed, highlight `different`
3. Cost allocation — existing allocation rows + mapping method

Bottom bar: Hold / Reject / Approve. Uncertain fields show locator + editable
reviewed value (writes Stage 10 overlay).

Until 12.1 is on the API, the pane component takes a **fixture** typed as the
eventual response. Vitest: disagreement highlight + approve disabled while
error issues exist.

**Files:**
- Create: `frontend/src/components/project/InvoiceReviewPane.tsx`
- Create: `frontend/src/components/project/InvoiceReviewPane.test.tsx`
- Modify: `CostInvoiceRegister.tsx` to open the pane on a row

**Commit:** `feat: review invoices in three panes with an approval gate`

---

## Task 12.4 — Event names only (no Pulse)

Emit `record_activity_events` with sources the Stage 13 vocabulary will reuse:

```text
invoice.received
invoice.needs_review
invoice.approved
invoice.rejected
invoice.posted
invoice.duplicate
invoice.conflict
```

Do **not** invent a Pulse table. Use existing `activity_events`.

---

## Exit gate

- [x] New invoices cannot sit in `posted`/`booked-final` without `approve`
- [x] `paid` is not a review state
- [x] Three-pane fixture tests pass; `pnpm typecheck && pnpm test && pnpm build`
- [x] Backend failures ⊆ baseline
- [x] Activity events recorded for approve/reject
- [x] Stage 13 is now eligible to expand (invoice verbs exist)

**After this stage:** expand [`stage-13`](./90-downstream-stages.md) from the
card — event spine — using the verbs above plus `document.*` already implied
by ingest/sort. **Not expanded in this session.**
