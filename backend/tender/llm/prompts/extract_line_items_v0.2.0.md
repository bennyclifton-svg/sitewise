---
version: 0.2.0
purpose: tender_line_item_extraction
---

Extract every printed dollar figure from the provided builder-quote page window
into the JSON schema.

Rules:
- Capture EVERY printed dollar figure: line items, section totals, subtotals,
  grand totals, PC/PS allowance tables, optional upgrades, priced exclusions,
  and informational figures.
- Emit `figure_key` as `p{page}-{ordinal-on-page}` for figures printed in your
  window only (1-based ordinal among dollar figures on that page).
- Set `parent_figure_key` when a figure sits inside a priced section/category
  whose rollup is also extracted in this window or named in prior context.
- Set `is_rollup` true for totals of other figures (section/category/grand).
- Classify `role` as one of: `contract_component`, `pc_allowance`,
  `ps_allowance`, `optional_upgrade`, `informational`, `excluded`.
- Set `gst_basis` ONLY when printed next to the figure ("inc GST", "ex GST",
  "+GST"); otherwise `unknown`.
- Copy `printed_text` verbatim including `$` and commas. Never repair, round,
  or invent numbers.
- Set `duplicate_of_figure_key` when the same figure is a reprint in a summary
  / quoted-categories table of a body figure already extracted.
- You see a WINDOW of pages. Earlier windows' section headings may be supplied
  as context. Only emit figures printed in your window pages.
- Preserve source wording in `description_raw`.
- Use integer cents for money fields (`amount_cents`, etc.).
- Return page subtotals and quote totals only when explicit in the source.
- Do not perform reconciliation arithmetic; the backend does that.
- Set low `extraction_confidence` when a row depends on layout interpretation.
