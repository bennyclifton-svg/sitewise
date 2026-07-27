# Cost workbook consolidation

**Date:** 2026-07-27
**Status:** Design agreed, not yet implemented

Fold the markdown Cost Breakdown table into the Cost Plan workbook, delete the
table, and render the workbook inline where the table used to sit.

## Problem

A cost plan draft shows the same cost lines twice: a Cost Breakdown table inside
"Budget reconciliation and cost breakdown", and a workbook grid below the
document. They are not actually the same data.

The cost lines make three lossy hops:

```
renderer -> markdown table -> parse_legacy_draft -> typed state -> workbook
```

`parse_legacy_draft` skips any row whose Budget is not a number
(`import_legacy.py:115-120`), and `CostItemInput` rejects a row with neither a
budget nor a complete quantity/unit/rate (`schemas.py:67-68`). A commercial
fit-out has no NSW rate pack, so the renderer marks every construction,
consultant and fee line `TBC`. Those rows die at hop three.

The result: the breakdown table shows ~29 lines and the workbook shows two. The
duplication is visible; the divergence is not.

## Decisions

| Question | Decision |
| --- | --- |
| Where does the workbook render? | Inline, where the breakdown table was |
| How do Status and Basis migrate? | One numeric `Basis` column plus a key legend |
| Where does the key legend live? | Below the Summary grid, in the sheet itself |
| Which column holds the key? | `M`, after `Remaining` — purely additive |
| How does an unpriced Budget cell read? | Literal `"TBC"` text |
| Does the markdown export keep a table? | No. Cost lines live in the `.xlsx` only |

## Data flow

Stop using markdown as the transport.

New module `backend/app/sitewise/cost_plan_lines.py`:

```python
def cost_plan_lines(project, pack) -> CostPlanLineSet
```

`CostPlanLineSet` holds `lines: list[CostPlanLine]` and
`basis_key: list[BasisKeyEntry]`. The body is the row-building logic lifted out
of `_render_cost_breakdown` (`cost_plan_renderer.py:1096-1157`) — same family
taxonomies, same benchmark split, same subtotal rules — returning structs
instead of pipe-delimited strings. `CostPlanLine` already carries
`budget: float | None`, `status` and `basis`; it needs one new field,
`basis_key: int`.

The key de-duplicates `(status, basis)` pairs in first-appearance order. A
fit-out collapses to about five entries, residential to six.

Rewired callers:

- `render_cost_plan_scaffold` — uses it for the prose disclosures only; emits no
  table.
- `save_cost_plan_workbook_artifact` — builds the Summary sheet from `lines`,
  dropping its `markdown=` argument.
- `import_legacy_draft` — fed from the same `lines`, filtered to priced rows as
  today, so typed state and the workbook cannot drift.

`parse_cost_breakdown` stays. Genuinely old drafts still have tables and must
keep importing.

## Workbook Summary sheet

`Basis` is appended as column `M`, after `Remaining`:

```
A Cost Code | B Category | C Cost Items | D Budget | E Approved Contract
| F Forecast Variations | G Approved Variations | H Forecast Final Cost
| I Budget Variance | J Claimed to Date | K This Month | L Remaining | M Basis
```

Appending rather than inserting keeps every existing formula, the `J2/K2` month
control, the `A1:L1` merge, `SUMMARY_MONEY_COLUMNS = range(4, 13)` and the
subtotal loops byte-identical. `_verify_workbook` needs no change.

What does change:

- Hidden lookup columns move `M/N -> N/O`; `CostItemLookup` and
  `InvoiceBillingMonths` defined names re-point.
- `_style_summary_sheet` widens to `max_col=13` and adds an `M` width.
- Column 13 is excluded from the money format, so the key renders as a plain
  integer.
- Unpriced rows write the string `"TBC"` into `D`. Excel's `SUM` skips text, so
  subtotals stay correct.

**Basis key block.** After the grand total: one blank row, a `Basis key` label,
then numbered rows (`A` = number, `B` = `"Assumption — structure only, no rate
pack; pending head-builder tender"`) on the existing `lookup` grey fill, which
the preview already styles as muted.

**Trap.** `_summary_rollup_values` (`cost_plan_workbook.py:732-781`) walks every
row past the header and treats anything with a column-3 value as a cost item. It
must stop at the grand total, or the key rows roll up as phantom lines.

## Markdown and the inline grid

`_render_budget_and_breakdown` (`cost_plan_renderer.py:676-715`) stops calling
`_cost_breakdown_table()`. It keeps the reconciliation table and the
`### Cost breakdown` sub-heading with its no-rate-pack prose, then emits a fenced
placeholder:

````
### Cost breakdown
No NSW commercial fit-out rate pack exists yet — this is a structure-only
scaffold; every construction line is a lump-sum TBC pending QS or head-builder
pricing.

```cost-workbook
```
````

`MarkdownContent`'s `pre` handler already intercepts `language-pmp-decision`
fences and swaps in a live `<DecisionControl>` (`MarkdownContent.tsx:107-149`).
The same hook detects `language-cost-workbook` and renders `<WorkbookGrid>`.
Section nav, `Edit section` and decision controls keep working untouched;
`DraftReviewPanel` threads its existing `workbook.workspace_path` down as a new
optional prop.

The standalone "Cost workbook" panel (`DraftReviewPanel.tsx:384-397`) goes away.
The **Download workbook** button stays.

**Back-compat.** Drafts already accepted have tables and no fence. Keep the
standalone panel as a fallback when the markdown has no `cost-workbook` fence,
so old drafts render exactly as they do now.

## Knock-ons

Four consumers read the table and will break silently:

1. **`greenfield_structure_violations`** (`cost_plan_brief.py:202-214`)
   substring-matches the section for "fees and charges", "consultants",
   "construction", "contingency". With the table gone those words vanish and
   every draft raises four false violations. Re-point at `lines`.

2. **`claim_first_violations`** (`cost_plan_evidence_validation.py:315-343`)
   counts `| construction |` rows to enforce trade granularity. Count from
   `lines` instead.

3. **Consultant fee forecast**, called from `consultant_procurement.py:1071` and
   two MCP tools (`server.py:2326`, `server.py:2366`). Its write-back half is
   *already dead* on scaffold output: `_section_bounds`
   (`cost_plan_consultant_forecast.py:378-393`) matches only `## ` headings and
   hunts for `"Cost breakdown by category"`, which the scaffold never emits. It
   computes forecasts today and silently discards them. Needs a `lines`-based
   entry point either way.

4. **Prompt text** — `create_cost_plan_instructions.md:42-52` and
   `cost_plan_brief.py:15-19` instruct the model to emit the table. Left alone,
   the model re-adds a duplicate under the fence.

## Testing

- Extend `test_cost_plan_workbook.py` for column `M`, the key block, `"TBC"` in
  `D`, and lookups at `N/O`.
- Add the regression that prompted this work: a commercial fit-out must produce
  all taxonomy rows in the workbook, not two.
- Rework `test_cost_plan_consultant_forecast.py` onto `lines`.
- Update `MarkdownContent.test.tsx` for the new fence and
  `ProjectCockpitPage.test.tsx` for the removed panel.
- Capture the pre-existing test-failure baseline before starting, to separate
  new breakage from old.
