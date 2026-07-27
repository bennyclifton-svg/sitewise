# Cost Workbook Consolidation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Delete the duplicated Cost Breakdown markdown table and make the Cost Plan workbook the single, complete presentation of every cost line — including the unpriced `TBC` rows it silently drops today.

**Architecture:** Stop using markdown as the transport for cost lines. A new `cost_plan_lines` module owns the family taxonomies and returns structured rows; the renderer, the workbook builder and the typed importer all consume it. The workbook gains one appended `Basis` column holding a numeric key, with a key legend below the grand total. The grid renders inline in the markdown via the existing fenced-block component hook.

**Tech Stack:** Python 3.12, pytest, openpyxl, SQLAlchemy; React 19, TypeScript, Vitest, react-markdown + remark-gfm.

**Design doc:** `docs/plans/2026-07-27-cost-workbook-consolidation-design.md` — read it before starting.

---

## Background you need

Read these before Task 1. They explain *why* this is not a copy-paste job.

1. `backend/app/cost_plan/import_legacy.py:115-120` — the legacy importer skips any row whose Budget is not a number.
2. `backend/app/cost_plan/schemas.py:67-68` — `CostItemInput` rejects a row with neither a budget nor a complete quantity/unit/rate.
3. `backend/app/sitewise/cost_plan_renderer.py:1117-1143` — for every family except `residential_class1_new`, construction rows render as the literal string `TBC`.

Together those mean a commercial fit-out shows ~29 rows in the markdown table and ~2 in the workbook. Fixing that is the point of this work.

## Environment

Work in this worktree: `.worktrees/cost-workbook-consolidation`.

**Never run plain `pytest` from a checkout that has the real `backend/.env`** — `DATABASE_URL` there points at the live Supabase database. This worktree has a dummy `.env` pointing at an unreachable port, and `backend/pyproject.toml:49` sets `addopts = "-m 'not integration and not tender_eval'"`. Leave both alone.

Backend tests: `cd backend && .venv/Scripts/python.exe -m pytest <path> -q`
Frontend tests: `cd frontend && npx vitest run <path>`

Baseline at plan time — any deviation is yours:
- `tests/sitewise/test_cost_plan_workbook.py tests/sitewise/test_cost_plan_consultant_forecast.py tests/cost_plan/test_typed_cost_plan.py tests/workflows/test_create_cost_plan.py tests/workflows/test_create_cost_plan_hybrid_integration.py` → **42 passed**
- `frontend src/components/project src/lib` → **117 passed**, `src/pages` → **5 passed**

---

## Task 1: Extract structured cost lines

Move the row-building logic out of the renderer so it can feed the workbook directly.

**Files:**
- Create: `backend/app/sitewise/cost_plan_lines.py`
- Modify: `backend/app/sitewise/cost_plan_renderer.py`
- Modify: `backend/app/sitewise/cost_plan_workbook.py:68-77` (re-export `CostPlanLine`)
- Test: `backend/tests/sitewise/test_cost_plan_lines.py`

**Step 1: Write the failing test**

```python
# backend/tests/sitewise/test_cost_plan_lines.py
from __future__ import annotations

from app.sitewise.cost_plan_lines import cost_plan_lines
from tests.sitewise.factories import commercial_fitout_project, fitout_evidence_pack


def test_fitout_keeps_every_unpriced_row() -> None:
    line_set = cost_plan_lines(commercial_fitout_project(), fitout_evidence_pack())

    codes = [line.cost_code for line in line_set.lines]
    assert codes == [str(n) for n in range(1, 30)]
    assert sum(1 for line in line_set.lines if line.budget is None) >= 25


def test_basis_key_dedupes_status_basis_pairs_in_first_appearance_order() -> None:
    line_set = cost_plan_lines(commercial_fitout_project(), fitout_evidence_pack())

    assert line_set.basis_key[0].number == 1
    assert line_set.basis_key[0].status == "Approved"
    assert line_set.basis_key[0].basis == "Engagement letter"

    pairs = [(entry.status, entry.basis) for entry in line_set.basis_key]
    assert len(pairs) == len(set(pairs))

    by_number = {entry.number: entry for entry in line_set.basis_key}
    for line in line_set.lines:
        entry = by_number[line.basis_key]
        assert (entry.status, entry.basis) == (line.status, line.basis)
```

You will need `backend/tests/sitewise/factories.py` with `commercial_fitout_project()` and `fitout_evidence_pack()` helpers. Build them from the existing fixtures in `backend/tests/workflows/test_create_cost_plan.py` — grep for how `Project` and `CostPlanEvidencePack` are constructed there and lift the smallest version that satisfies `_coverage_family`.

**Step 2: Run to verify it fails**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/sitewise/test_cost_plan_lines.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.sitewise.cost_plan_lines'`

**Step 3: Create the module**

Move these from `cost_plan_renderer.py` into `cost_plan_lines.py` **unchanged**:
- every `_*_FEE_ROWS`, `_*_CONSULTANT_ROWS`, `_*_CONSTRUCTION_ROWS`, `_*_PC_ALLOWANCE_ROWS`, `_*_CONTINGENCY_CODE` constant (lines 58-370)
- the five `_*_BY_FAMILY` dicts (lines 372-444)
- `_coverage_family` (447-460)
- `_no_rate_pack_disclosure` (33-56)
- the money helpers `_money`, `_parse_amount` (508-521)

Then add:

```python
@dataclass(frozen=True, slots=True)
class CostPlanLine:
    cost_code: str
    category: str
    cost_item: str
    budget: float | None
    approved_contract: float | None
    status: str
    basis: str
    basis_key: int = 0


@dataclass(frozen=True, slots=True)
class BasisKeyEntry:
    number: int
    status: str
    basis: str


@dataclass(frozen=True, slots=True)
class CostPlanLineSet:
    lines: tuple[CostPlanLine, ...]
    basis_key: tuple[BasisKeyEntry, ...]


def _assign_basis_keys(
    rows: list[CostPlanLine],
) -> tuple[tuple[CostPlanLine, ...], tuple[BasisKeyEntry, ...]]:
    """Number each distinct (status, basis) pair in first-appearance order."""
    numbers: dict[tuple[str, str], int] = {}
    entries: list[BasisKeyEntry] = []
    keyed: list[CostPlanLine] = []
    for row in rows:
        pair = (row.status, row.basis)
        number = numbers.get(pair)
        if number is None:
            number = len(numbers) + 1
            numbers[pair] = number
            entries.append(BasisKeyEntry(number=number, status=row.status, basis=row.basis))
        keyed.append(replace(row, basis_key=number))
    return tuple(keyed), tuple(entries)


def cost_plan_lines(project: Project, pack: CostPlanEvidencePack) -> CostPlanLineSet:
    """Return every cost line for the project's coverage family, priced or not."""
    rows = _build_rows(project, pack)
    lines, basis_key = _assign_basis_keys(rows)
    return CostPlanLineSet(lines=lines, basis_key=basis_key)
```

`_build_rows` is `_render_cost_breakdown`'s body (renderer lines 1096-1157) with each
`rows.append(f"| {code} | ... |")` replaced by `rows.append(CostPlanLine(...))`.

Rules to preserve exactly:
- Row 1 is the architect/PM fee: `status="Approved"`, `basis="Engagement letter"`, budget from `pack.mobilisation.fee_total_ex_gst`.
- Fee rows → `status="Assumption"`, `basis="Benchmark"`.
- Consultant rows → `status="Assumption"`, `basis="Not yet appointed"`, except the appointed principal certifier branch (renderer 1106-1113).
- Construction rows use the benchmark split **only** when `benchmark_pct is not None and ceiling is not None`; otherwise every row is `budget=None` with the structure-only basis.
- PC-allowance and contingency rows as per renderer 1144-1157.

**Do not emit subtotal or grand-total rows.** The workbook computes those itself
(`_write_summary_total_row`, `_write_summary_grand_total_row`).

**Step 4: Re-export for back-compat**

`cost_plan_consultant_forecast.py:6` imports `CostPlanLine` from `cost_plan_workbook`. Keep that working — in `cost_plan_workbook.py`, delete the local dataclass and add:

```python
from app.sitewise.cost_plan_lines import BasisKeyEntry, CostPlanLine, CostPlanLineSet
```

Import direction is `cost_plan_lines` ← `cost_plan_renderer` and `cost_plan_lines` ← `cost_plan_workbook`. `cost_plan_lines` must import neither, or you get a cycle.

**Step 5: Point the renderer at the new module**

In `cost_plan_renderer.py`, delete the moved constants and import them instead. `_render_cost_breakdown` stays for now (Task 5 deletes it) but its row list must come from `cost_plan_lines()` so there is exactly one source of truth. `_render_commitments_allowances:756` and `_render_budget_and_breakdown:697-703` keep working via the imported `_PC_ALLOWANCE_ROWS_BY_FAMILY` and `_no_rate_pack_disclosure`.

**Step 6: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/sitewise/ tests/workflows/test_create_cost_plan.py tests/cost_plan/ -q`
Expected: PASS — new tests green, all 42 baseline tests still green. The markdown output must be byte-identical at this point; if `test_create_cost_plan.py` fails, your extraction changed behaviour.

**Step 7: Commit**

```bash
git add backend/app/sitewise/cost_plan_lines.py backend/app/sitewise/cost_plan_renderer.py backend/app/sitewise/cost_plan_workbook.py backend/tests/sitewise/test_cost_plan_lines.py backend/tests/sitewise/factories.py
git commit -m "refactor: extract cost plan lines from the markdown renderer"
```

---

## Task 2: Append the Basis column

**Files:**
- Modify: `backend/app/sitewise/cost_plan_workbook.py`
- Test: `backend/tests/sitewise/test_cost_plan_workbook.py`

**Step 1: Write the failing test**

```python
def test_summary_appends_basis_column_without_moving_existing_columns() -> None:
    workbook = build_cost_plan_workbook(
        project_title="Greenfield Demo",
        markdown=_valid_cost_plan_markdown(),
        version=1,
    )
    summary = load_workbook(BytesIO(workbook.content), data_only=False)["Summary"]

    assert [summary.cell(row=4, column=i).value for i in range(1, 14)][-1] == "Basis"
    # every pre-existing formula is untouched
    assert summary["H5"].value == "=SUM(E5:G5)"
    assert summary["I5"].value == "=D5-H5"
    assert summary.column_dimensions["N"].hidden is True
    assert summary.column_dimensions["O"].hidden is True
    assert summary.column_dimensions["M"].hidden is not True
```

**Step 2: Verify it fails**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/sitewise/test_cost_plan_workbook.py -q`
Expected: FAIL — header list has 12 entries, `N`/`O` not hidden.

**Step 3: Implement**

In `cost_plan_workbook.py`:
- `SUMMARY_HEADERS` — append `"Basis"` (13 entries).
- `_write_summary_item_row` — add `13: item.basis_key or None` to the `values` dict. Leave keys 1-12 exactly as they are.
- `_write_summary_lookup_columns` — write to columns 14/15, hide `N`/`O` instead of `M`/`N`.
- `_add_defined_names` — `CostItemLookup` → `'Summary'!$N$2:$N${last}`, `InvoiceBillingMonths` → `'Summary'!$O$2:$O$61`.
- `_style_summary_sheet` — add `"M": 8` to `widths`, change `max_col=12` → `13`, and change the lookup fill loop to `min_col=14, max_col=15`.
- Leave `SUMMARY_MONEY_COLUMNS`, the `range(4, 13)` subtotal loops, `A1:L1`, `J2/K2` and `_verify_workbook` **untouched**. Column 13 falls outside `SUMMARY_MONEY_COLUMNS`, so it stays an unformatted integer for free.

**Step 4: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/sitewise/test_cost_plan_workbook.py -q`
Expected: PASS. Note `test_build_cost_plan_workbook_preserves_sitewise_excel_contract:54-55` asserts `M`/`N` hidden — update it to `N`/`O`, and extend its header list to 13.

**Step 5: Commit**

```bash
git add backend/app/sitewise/cost_plan_workbook.py backend/tests/sitewise/test_cost_plan_workbook.py
git commit -m "feat: append Basis key column to the cost plan workbook Summary sheet"
```

---

## Task 3: Basis key block and TBC cells

**Files:**
- Modify: `backend/app/sitewise/cost_plan_workbook.py`
- Test: `backend/tests/sitewise/test_cost_plan_workbook.py`

**Step 1: Write the failing tests**

```python
def test_unpriced_rows_write_tbc_and_subtotals_ignore_it() -> None:
    ...
    assert summary.cell(row=5, column=4).value == "TBC"
    # SUM over a text cell still returns the priced total
    assert summary.cell(row=subtotal_row, column=4).value.startswith("=SUM(")


def test_basis_key_block_renders_below_the_grand_total() -> None:
    ...
    labels = [summary.cell(row=r, column=1).value for r in range(1, summary.max_row + 1)]
    assert "Basis key" in labels
    key_row = labels.index("Basis key") + 2
    assert summary.cell(row=key_row, column=1).value == 1
    assert summary.cell(row=key_row, column=2).value == "Approved — Engagement letter"


def test_preview_rollup_ignores_basis_key_rows() -> None:
    preview = workbook_preview_from_bytes(workbook.content)
    summary = next(s for s in preview.sheets if s.name == "Summary")
    grand = next(r for r in summary.rows if "Grand total" in r)
    assert grand[3] != ""  # grand total still computed
    # key rows are not rolled up as cost items
    assert all(not r[3].startswith("$") for r in summary.rows[summary.rows.index(grand) + 1:])
```

**Step 2: Verify they fail**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/sitewise/test_cost_plan_workbook.py -q`

**Step 3: Implement**

- In `_write_summary_item_row`, write `"TBC"` into column 4 when `item.budget is None`.
- Add `_write_basis_key_block(worksheet, start_row, basis_key)`: blank row, then `A` = `"Basis key"` (bold), then one row per entry with `A` = `entry.number`, `B` = `f"{entry.status} — {entry.basis}"`. Apply `_fills()["lookup"]` so the preview styles it muted.
- **Critical:** in `_summary_rollup_values` (`cost_plan_workbook.py:732-781`), `break` out of the row loop once the `"grand total"` branch fires. Without this the key rows are treated as cost items and pollute the rollup.

**Step 4: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/sitewise/ -q`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/sitewise/cost_plan_workbook.py backend/tests/sitewise/test_cost_plan_workbook.py
git commit -m "feat: add basis key legend and TBC budget cells to the workbook"
```

---

## Task 4: Build the workbook from lines

**Files:**
- Modify: `backend/app/sitewise/cost_plan_workbook.py`
- Modify: `backend/app/workflows/create_cost_plan.py:809-871`
- Test: `backend/tests/sitewise/test_cost_plan_workbook.py`

**Step 1: Write the failing test**

```python
def test_scaffold_workbook_carries_every_fitout_line() -> None:
    line_set = cost_plan_lines(commercial_fitout_project(), fitout_evidence_pack())
    workbook = build_scaffold_cost_plan_workbook(
        project_title="Meridian Fitout", line_set=line_set, version=1,
    )
    # the regression that prompted this work: 29 lines in, 29 lines out
    assert workbook.row_count == len(line_set.lines) >= 29
```

**Step 2: Verify it fails**

**Step 3: Implement**

Add alongside `build_typed_cost_plan_workbook`:

```python
def build_scaffold_cost_plan_workbook(
    *,
    project_title: str,
    line_set: CostPlanLineSet,
    version: int,
    generated_at: datetime | None = None,
) -> CostPlanWorkbook:
    """Render a workbook from renderer-produced lines, unpriced rows included."""
    return _build_workbook(
        project_title=project_title,
        items=list(line_set.lines),
        basis_key=line_set.basis_key,
        version=version,
        generated_at=generated_at or datetime.now(UTC),
        warnings=[],
    )
```

Thread `basis_key` through `_build_workbook` → `_build_summary_sheet` → `_write_basis_key_block`. Default it to `()` so `build_cost_plan_workbook` and `build_typed_cost_plan_workbook` keep working unchanged.

In `save_cost_plan_workbook_artifact`, prefer the scaffold path: accept an optional `line_set` and use `build_scaffold_cost_plan_workbook` when present, falling back to the typed and markdown paths in that order. Pass `line_set` from both call sites (`create_cost_plan.py:793` and `:1403`).

**Step 4: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/sitewise/ tests/workflows/ tests/cost_plan/ -q`

**Step 5: Commit**

```bash
git commit -am "feat: build the cost plan workbook from structured lines"
```

---

## Task 5: Delete the markdown table, emit the fence

**Files:**
- Modify: `backend/app/sitewise/cost_plan_renderer.py:619-628, 676-715, 1066-1245`
- Test: `backend/tests/workflows/test_create_cost_plan.py`

**Step 1: Write the failing test**

```python
def test_scaffold_emits_a_workbook_fence_and_no_cost_breakdown_table() -> None:
    markdown = render_cost_plan_scaffold(project, pack, "evidence_grounded")

    assert "```cost-workbook" in markdown
    assert "| Cost Code | Category |" not in markdown
    # the qualifying prose survives
    assert "### Cost breakdown" in markdown
    assert "no NSW commercial fit-out rate pack" in markdown.lower()
```

**Step 2: Verify it fails**

**Step 3: Implement**

In `_render_budget_and_breakdown`, replace `_cost_breakdown_table(project, pack)` with the literal three lines:

```python
"```cost-workbook",
"```",
```

Delete `_cost_breakdown_table` (619-628) and `_render_cost_breakdown` (1066-1245) — the taxonomy and workbook-group prose in the latter was already being discarded by the `_cost_breakdown_table` slice, so nothing user-visible is lost. Keep `_render_budget_and_breakdown`'s own `breakdown_intro`.

**Step 4: Run tests**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/workflows/test_create_cost_plan.py tests/sitewise/ -q`
Expected: several failures in Tasks 6-8 territory. That is the signal for the next tasks — do not paper over them here.

**Step 5: Commit**

```bash
git commit -am "feat: replace the cost breakdown table with a workbook fence"
```

---

## Task 6: Re-point the typed importer

**Files:**
- Modify: `backend/app/cost_plan/import_legacy.py`
- Modify: `backend/app/workflows/create_cost_plan.py:1359-1378`
- Test: `backend/tests/cost_plan/test_typed_cost_plan.py`

Add `typed_items_from_lines(line_set, draft) -> tuple[CostItemInput, ...]` filtering to `line.budget is not None` — same priced-rows-only contract as today, but sourced from lines. `parse_legacy_draft` stays for genuinely old drafts that still have tables.

Test that a fit-out yields the same priced item count as before, and that `parse_legacy_draft` still imports a legacy table-bearing draft.

Commit: `refactor: feed typed cost plan state from structured lines`

---

## Task 7: Re-point the validators

**Files:**
- Modify: `backend/app/sitewise/cost_plan_brief.py:202-214`
- Modify: `backend/app/sitewise/cost_plan_evidence_validation.py:284-343`
- Test: `backend/tests/sitewise/test_cost_plan_evidence_validation.py`

`greenfield_structure_violations` substring-matches the section for four group names; `claim_first_violations` counts `| construction |` rows. Both go silently wrong with no table. Change both to take the `CostPlanLineSet` and assert over `line.category`.

Write a test first proving the current code raises four false violations against fence-only markdown.

Commit: `fix: validate cost plan structure from lines, not markdown text`

---

## Task 8: Consultant fee forecast

**Files:**
- Modify: `backend/app/sitewise/cost_plan_consultant_forecast.py`
- Modify: `backend/app/workflows/consultant_procurement.py:1071`
- Modify: `backend/app/mcp_bridge/server.py:2326, 2366`
- Test: `backend/tests/sitewise/test_cost_plan_consultant_forecast.py`

Add `forecast_consultant_fees_for_lines(line_set, *, source_path=None)` and switch the three callers to it.

**Note the pre-existing bug:** `_rewrite_cost_breakdown` looks for a `## Cost breakdown by category` heading via `_section_bounds` (`:378-393`), which matches `## ` only. The scaffold emits `## Budget reconciliation and cost breakdown` with a `### Cost breakdown` child, so the write-back has been a silent no-op. Do not port that behaviour — return the forecast rows and let the caller decide.

Keep `forecast_consultant_fees_for_markdown` for legacy drafts.

Commit: `fix: forecast consultant fees from lines and drop the dead markdown rewrite`

---

## Task 9: Update the prompt text

**Files:**
- Modify: `backend/app/workflows/create_cost_plan_instructions.md:26-52, 79`
- Modify: `backend/app/sitewise/cost_plan_brief.py:15-19, 93-94, 142, 247-248, 261`
- Modify: `backend/app/workflows/create_cost_plan.py:435`
- Modify: `backend/app/workflows/cost_plan_narrative_instructions.md:3`

These instruct the model to emit a `Cost Code | Category | Cost Items | Budget | Status | Basis` table. Leave them and the model cheerfully re-adds a duplicate under the fence. Replace with instructions to write the qualifying prose only, and state that cost lines are rendered deterministically into the workbook.

Verify with `tests/workflows/test_create_cost_plan.py` and `tests/acceptance` if present.

Commit: `docs: stop instructing the model to emit a cost breakdown table`

---

## Task 10: Frontend — Basis column in the grid

**Files:**
- Modify: `frontend/src/components/project/WorkbookGrid.tsx:125-128, 177-184, 267-327, 514-522`
- Modify: `frontend/src/index.css:711-730`
- Test: `frontend/src/components/project/WorkbookGrid.test.tsx`

- `SUMMARY_COLUMN_COUNT` 12 → 13.
- Replace `SUMMARY_MONEY_COLUMN_START` with an explicit set: indices 3 through 11. Index 12 (Basis) must **not** be money-aligned.
- Add a `workbook-col-basis` `<col>` (width `4.5%`) after the nine money cols, and the matching CSS rule.
- `SummaryGstRow` currently renders cells at indices 9, 10 and `SUMMARY_COLUMN_COUNT - 1`. With 13 columns that skips index 11. Fix it to cover 9, 10, 11, 12 so the row spans the full table.

Commit: `feat: render the Basis key column in the workbook preview`

---

## Task 11: Frontend — inline grid via the fence

**Files:**
- Modify: `frontend/src/components/project/MarkdownContent.tsx:107-149, 269-296`
- Modify: `frontend/src/components/project/DraftReviewPanel.tsx:349-397`
- Test: `frontend/src/components/project/MarkdownContent.test.tsx`

**Step 1: Write the failing test**

```tsx
it("renders the workbook grid where a cost-workbook fence appears", () => {
  render(
    <MarkdownContent
      markdown={"## Budget\n\n```cost-workbook\n```\n"}
      projectId="p1"
      workbookPath="drafts/Cost_Plan_v01.draft.xlsx"
    />,
  );
  expect(screen.getByRole("table")).toBeInTheDocument();
});

it("renders nothing for the fence when no workbook exists", () => { /* ... */ });
```

**Step 2: Implement**

The `pre` handler already intercepts `language-pmp-decision` and swaps in `<DecisionControl>` — copy that shape exactly for `language-cost-workbook` → `<WorkbookGrid projectId={...} workbookPath={...} />`. Add optional `workbookPath` to `MarkdownContent`'s props. Render nothing if either prop is missing.

In `DraftReviewPanel`, pass `workbook?.workspace_path` into `MarkdownContent`, and gate the standalone panel (`:384-397`) on the markdown **not** containing `` ```cost-workbook ``` — that is the back-compat path for already-accepted drafts that still carry a table. Keep the **Download workbook** button unconditionally.

**Step 3: Run tests**

Run: `cd frontend && npx vitest run src/components/project src/pages`
Expected: PASS, 122+ tests

**Step 4: Commit**

```bash
git commit -am "feat: render the cost workbook inline where the breakdown table was"
```

---

## Task 12: Full verification

**Step 1:** `cd backend && .venv/Scripts/python.exe -m pytest tests/ -q`
Compare against the recorded baseline. Investigate every new failure; do not accept "was already broken" without checking the baseline list.

**Step 2:** `cd frontend && npx vitest run && npx tsc --noEmit && npm run lint`

**Step 3:** Drive the real app per the repo's `verify` skill (`.claude/skills/verify`) — generate a cost plan for a commercial fit-out project and confirm:
- no Cost Breakdown table in the document
- the grid renders inline under `### Cost breakdown`
- every taxonomy row is present with `TBC` budgets
- the Basis column shows integers and the key legend resolves them
- **Download workbook** produces an `.xlsx` whose Summary carries all rows, formulas intact

**Step 4:** REQUIRED SUB-SKILL: `superpowers:requesting-code-review` before merge.
