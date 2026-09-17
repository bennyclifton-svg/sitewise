# Price matrix totals and Excel copy

Procurement reviews retain the model-selected item schedule. Python builds an
additive presentation after selection; the extraction and selection prompts are
unchanged.

- Canonical quote components are assigned to one row each. Explicit parent
  relationships keep bundled children from adding the same price again. Remaining
  counted items appear in **Other quoted items**.
- Quotes without a component schedule can expose standalone allowances and
  selected stage subtotals as a **Partial price schedule**. Unknown tax bases do
  not receive a reconciliation result. Rates, options and embedded allowances
  remain reference amounts in notes.
- **Item total**, **Quoted total** and **Difference** are calculated in Python.
  Difference is quoted total minus item total on the same currency/tax basis.
  Mixed bases, conflicting offers and missing totals remain unchecked. No residual
  is inserted as a made-up line item to force a match.

The canonical Markdown stays compact for the report and Word/PDF exports. A
counted amount is the leading bold money value in its cell; everything after it
is a note. The viewer recognises the currency-qualified headers and three footer
rows and renders a read-only amount-first matrix. **Separate notes** expands it
into paired columns.

**Copy for Excel** writes tab-separated amount/notes columns. Numeric cells have
no currency symbols or thousands separators. Unpriced cells stay blank and keep
their status in notes. Document tokens expand to filenames and retain page
references. Formula-like source text is escaped. Only the generated item-total
and difference cells contain formulas; relative references support pasting away
from cell A1 and recalculate after changing amounts.

## Rollout

Deploy the frontend, backend and tender worker together and reload the versioned
language catalogue with `uv run python -m tender.seeds.load` from `backend/`.
No schema migration or new dependency is required. Existing saved reviews retain
their original content; generate a new review to obtain the additive matrix and
copy control. The service reports a seed-loader error if the new language keys
have not been installed.

## Verification

Tests cover bundles, repeated prices, combined rows, omitted components, stage
subtotals, partial allowances, credits, zero versus missing, mixed currencies/tax,
conflicting totals, clipboard failure and formula-like evidence. Existing
consultant/trade/head-contractor Word/PDF profile tests remain in place. The cached
Mornington review was rendered with its original 20 selected rows, without new
model calls, and retained its three-page limit.
