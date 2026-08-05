# Invoice Processing into the Cost Plan

**Status:** Approved and deterministic v1 implemented on 4 August 2026.

**Implementation record:** The canonical ledger, allocation mapping, existing
workbook-register projection, durable workflow, REST/MCP/Pi routing, cockpit
action, pending-ingest feedback, and focused review counts are implemented. The
25-invoice synthetic pack, workbook render/formulas, and full backend/frontend
regression suites passed. A model fallback for invoice layouts that do not
match deterministic normalized-markdown extraction remains an evidence-driven
follow-up; those documents currently return explicit extraction errors rather
than being guessed or silently booked. The future anchored workbook editing
surface itself remains outside this plan, with stable entity IDs and versioned
publication preserved for that integration.

**Outcome:** A user can upload one or many invoices and invoke **Process
invoices** from the UI or agent. Clerk discovers every eligible ingested
invoice, extracts and validates its facts, books it once in a canonical invoice
ledger, maps its ex-GST allocations to existing Cost Plan items, and publishes
a new Cost Plan workbook version whose existing `Invoices` register drives the
existing `Summary` roll-ups.

This plan preserves the current workbook layout: `Summary`, `Invoices`, and
`Variations`. The database additions below are the canonical source behind the
existing workbook registers; they are not replacement workbook tabs.

## Governing decisions

1. Postgres is the source of truth. The `.xlsx` workbook is a versioned
   presentation and export of typed state; production code never patches a
   previously published workbook in place.
2. Booking an invoice does not alter Original Budget or Approved Contract.
   Invoice allocations drive Claimed To Date and Remaining through the existing
   workbook formulas.
3. Invoices are recorded ex GST. GST, inclusive total, due date, and extraction
   provenance remain available in the canonical ledger even where the current
   workbook has no display column for them.
4. `Paid?` defaults to `No`. Uploading, extracting, or booking an invoice never
   infers that it was paid or approved for payment.
5. Models may classify, extract, and choose among bounded mapping candidates.
   Python validates every amount, sum, GST calculation, date, duplicate, and
   workbook roll-up.
6. An invoice may have several allocations. Its identifying fields repeat on
   several workbook rows, one per allocation.
7. Allocations map only to existing Cost Plan item identities. An invoice never
   creates or changes a budget row. An unresolved allocation is recorded as
   `Unidentified`, does not roll up, and is returned for review.
8. Reprocessing identical evidence is idempotent. A business-key collision with
   different financial facts is a conflict and is never silently overwritten.
9. Clerk core owns this feature. It must not import from `backend/tender/` or
   use the Tender Comparison extraction pipeline.

## Current seams to extend

- `backend/app/cost_plan/` owns canonical typed Cost Plan state.
- `backend/app/sitewise/cost_plan_workbook.py` already creates the three tabs,
  validations, formulas, and formula-aware browser preview.
- `backend/app/workflows/` owns durable workflow execution and workbook
  publication.
- `backend/app/mcp_bridge/server.py` exposes project-scoped mutations to Pi.
- `frontend/src/components/project/WorkbookGrid.tsx` renders the workbook
  preview and remains the presentation surface.
- `data/skills/systems/cost-plan-system.md` supplies the binding invoice booking
  rules.

## Task 1 — Canonical invoice ledger

**Create or modify:**

- `backend/app/cost_plan/models.py`
- `backend/app/database/models.py`
- `backend/alembic/versions/040_cost_plan_invoice_ledger.py`
- `backend/app/cost_plan/schemas.py`
- `backend/tests/cost_plan/test_invoice_processing.py`

Add `cost_invoices` with:

- project, workspace-file, and optional source-document references;
- source content hash and source locator;
- supplier name and normalized supplier key, optional ABN;
- invoice number and normalized invoice key;
- invoice, due, and billing-month dates;
- PO number and related proposal/contract reference;
- subtotal ex GST, GST, total including GST, and currency;
- paid status, processing/review status, extraction provenance;
- workflow run and first-published Cost Plan version references;
- timestamps and optimistic revision.

Add `cost_invoice_allocations` with:

- invoice and project references;
- stable line number and source description;
- ex-GST amount and GST treatment;
- optional Cost Plan item reference plus item identity/label snapshot;
- mapping method, confidence, and review status;
- extraction source locators and timestamps.

Use decimal database types and `Decimal` in Python. Add project, source,
business-key, and allocation-order indexes; owner-scoped RLS policies matching
the existing typed Cost Plan tables. Cascading deletion is allowed only from an
invoice to its allocations. Source-document deletion must not destroy booked
financial history.

**Acceptance:** the ORM and migration agree; cross-project references are
rejected; invoice allocations reconcile exactly to the invoice subtotal;
duplicate source/business keys are handled by the service rather than an
unhelpful raw integrity failure.

## Task 2 — Discovery, extraction, validation, and mapping

**Create:**

- `backend/app/cost_plan/invoice_candidates.py`
- `backend/app/cost_plan/invoice_extraction.py`
- `backend/app/cost_plan/invoice_mapping.py`
- `backend/app/cost_plan/invoice_service.py`
- `backend/app/cost_plan/invoice_extraction_instructions.md` if an LLM fallback
  is required
- focused tests under `backend/tests/cost_plan/`

Discovery accepts explicit source/workspace-file IDs or finds every ingested,
active, unbooked project document that is recognisably an invoice. Content
classification must inspect normalized evidence, not only filenames.

Extraction uses deterministic normalized-markdown parsing first. A strict,
versioned structured-output LLM fallback may handle varied real documents. It
returns source facts and source locators, never calculated conclusions.

Python validation must enforce:

- line/allocation ex-GST sum equals invoice ex-GST subtotal;
- subtotal plus GST equals inclusive total;
- GST treatment is internally consistent, including mixed taxable and GST-free
  lines;
- an inclusive-only amount is divided by 1.1 only where the source supports
  standard GST, and the derived value is labelled in provenance;
- invoice and billing dates are real dates and billing month is the first day
  of the reporting month;
- zero, negative, or unsupported currencies are rejected for the first slice.

Mapping order is exact active Cost Plan identity, deterministic aliases and
related proposal/contract evidence, bounded model choice among active items,
then `Unidentified`. Never invent a split for a progress claim whose source does
not support one.

Deduplication uses both source identity/hash and normalized supplier plus
invoice number. Identical facts are skipped; material differences create a
reviewable conflict.

**Acceptance fixtures:** QUA-2601 maps $24,000 ex GST to the active architect
item; a mixed-GST invoice splits correctly; a multi-allocation invoice repeats
identity without changing its total; an ambiguous invoice is `Unidentified`;
an exact rerun is a no-op; a conflicting duplicate is surfaced.

## Task 3 — Existing workbook register projection

**Modify:**

- `backend/app/sitewise/cost_plan_workbook.py`
- `backend/app/workflows/create_cost_plan.py`
- `backend/tests/sitewise/test_cost_plan_workbook.py`
- relevant Cost Plan publication tests

Extend the typed workbook builder to accept the invoice ledger rows applicable
to the published Cost Plan version and write them into the existing `Invoices`
register beginning at row 5:

1. Invoice Date
2. Company
3. PO Number
4. Invoice Number
5. Invoice Description
6. Cost Item — exact active label, or `Unidentified`
7. Amount — ex GST
8. Billing Month — real first-of-month date
9. Paid? — `Yes` or `No`

Preserve all current formulas, validations, named ranges, styling, preview
roll-ups, and the `Variations` sheet. Workbook generation must query canonical
invoice state; regenerating or accepting a version must not empty the register.

Historical publication resolves ledger rows using their first-published Cost
Plan version so a previously published version remains reproducible.

**Acceptance:** QUA-2601 appears once, Summary Claimed To Date and This Month
increase by $24,000 for the mapped item, Original Budget and Approved Contract
remain unchanged, and all current workbook tests stay green.

## Task 4 — Durable `process_invoices` workflow

**Create or modify:**

- `backend/app/workflows/process_invoices.py`
- `backend/app/workflows/worker.py`
- workflow schemas and supported-workflow declarations
- `backend/tests/workflows/test_process_invoices.py`
- `backend/tests/workflows/test_workflow_runs.py`

Parameters include optional source IDs and the expected current Cost Plan
version. No IDs means all eligible unbooked invoices. The workflow freezes its
input context, then reports these stages:

1. Discovering invoices
2. Extracting invoice facts
3. Validating and deduplicating
4. Mapping Cost Plan items
5. Booking invoice ledger
6. Publishing Cost Plan
7. Verifying workbook

Persist booked ledger records and publish the new workbook atomically from the
workflow's point of view. A stale Cost Plan version produces a revision conflict.
If every candidate is an identical duplicate, complete successfully with skip
counts and do not publish another version. Unidentified allocations may publish
but are returned as review items and do not affect Summary roll-ups.

The result reports candidate, booked-invoice, register-row, duplicate, conflict,
and review counts plus the new Cost Plan version and workspace path.

## Task 5 — REST, MCP, and Pi doctrine

**Modify:**

- `backend/app/api/projects.py`
- `backend/app/schemas/projects.py`
- `backend/app/mcp_bridge/server.py`
- `backend/app/agent/pi_process.py`
- `backend/app/agent/turn_context.py`
- `backend/app/agent/workspace_instructions.py`
- focused API, MCP, authorization, allowlist, and prompt tests

Add an owner-scoped REST start endpoint and an MCP `process_invoices` mutation
using the existing durable workflow/idempotency and per-project turn-token
contracts. Explicit source IDs process a named selection; an omitted selection
processes all unbooked invoices.

Agent doctrine must distinguish:

- proposals/contracts → `refresh_cost_plan`;
- invoices → `process_invoices`;
- direct cost-row requests → typed cost-row actions;
- never use `upsert_cost_item` to book an invoice.

Add `process_invoices` to Pi's direct MCP allowlist. Keep `refresh_cost_plan`
aligned with the doctrine and allowlist where required.

## Task 6 — UI action and review result

**Modify:**

- `frontend/src/lib/types/project.ts`
- `frontend/src/lib/api.ts`
- the Cost Plan action surface and focused tests
- `frontend/src/components/project/WorkbookGrid.tsx` only where refresh or
  metadata handling is needed

Add **Process invoices** when a current Cost Plan exists. It starts the same
durable workflow and displays normal workflow progress. On completion, refresh
the draft/workbook preview and show counts for booked, duplicate, conflict, and
Unidentified records. Do not build a spreadsheet editor in this task.

Only ingested documents are processed. If uploads are still ingesting, show the
pending count and allow a later rerun rather than blocking a request thread.

## Task 7 — Synthetic and regression gate

Run the complete synthetic Kavanagh invoice pack and assert:

- all eligible invoices are discovered exactly once;
- ex-GST totals and mixed GST reconcile in Python;
- consultant allocations roll to the expected Summary items;
- ambiguous contractor claims are held for review rather than guessed;
- `Paid?` remains `No` unless explicitly changed;
- a second batch run creates no duplicate rows or unnecessary Cost Plan version;
- workbook formulas, validations, preview values, and download remain intact;
- stale versions, cross-project IDs, and unauthorized MCP calls are rejected.

Run focused backend tests, the workflow/project regression suites, Ruff,
frontend tests, TypeScript, and lint. Existing unrelated baseline failures must
be recorded rather than hidden.

## Future anchored workbook instructions compatibility

The markdown anchored-draft v1 remains unchanged and continues to exclude Cost
Plans. A later workbook feature may reuse its **Select → Instruct → Queue →
Apply** interaction and tray, but it must target typed Cost Plan state rather
than rewrite cells or reverse-map displayed text.

The invoice implementation therefore preserves these extension points:

1. Every displayed invoice row is backed by a stable invoice-allocation ID.
2. The workbook preview can expose its Cost Plan version and optional cell/row
   anchor metadata without changing the `.xlsx` layout.
3. A future anchor is shaped around `{cost_plan_version, sheet, entity_type,
   entity_id, field, observed_value}`; row numbers and A1 coordinates are
   presentation hints only.
4. Summary formula cells resolve to their driver entities. “Check this number”
   recalculates and explains contributing invoices; it does not overwrite the
   formula cell.
5. Mutating queued instructions dispatch to bounded typed actions and publish
   one audited Cost Plan version with optimistic version checking.
6. Changed entity IDs can be stamped into publication provenance for workbook
   row/cell highlighting.
7. The existing `Variations` register remains untouched. When variation state
   becomes canonical, it should use the same stable entity-anchor contract.

These provisions require no workbook-layout change and do not widen the scope
of the anchored-markdown implementation.
