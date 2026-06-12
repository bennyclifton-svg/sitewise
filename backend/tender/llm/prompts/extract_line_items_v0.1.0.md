---
version: 0.1.0
purpose: tender_line_item_extraction
---

Extract residential builder quote line items into the provided JSON schema.

Rules:
- Preserve source wording in `description_raw`.
- Use integer cents for all money fields.
- Use `pc_allowance` only for prime cost supply allowances.
- Use `ps_allowance` only for provisional sums where scope is not fixed.
- Return printed page subtotals and quote totals only when they are explicit in
  the source document.
- Do not do reconciliation or arithmetic beyond copying explicit source
  values; the backend performs all arithmetic checks.
- Set low confidence when a row, subtotal, status, or amount depends on layout
  interpretation rather than explicit text.

