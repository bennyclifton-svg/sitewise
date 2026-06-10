# Skill: excel-verify

**Job:** Verify that an Excel workbook edit did not break the file. Always runs after `excel-safe-edit.md`. Returns a structured pass/fail report. Does not declare completion until every required check passes.

This skill is the second half of the controlled exception to `../../AGENTS.md §5`'s Excel-is-read-only convention. `excel-safe-edit.md` performs the edit; this skill confirms the edit did not silently break the workbook. Without this verification, the controlled exception is not safe.

## When called

Called by:
- `excel-safe-edit.md` immediately after save (this is the canonical caller per `excel-safe-edit.md §"Step 6 — Hand off to excel-verify"`);
- a caller that wants to inspect a workbook for structural integrity without editing (the verify checklist works as a read-only structural pass when run against an unedited workbook + its own self as the "backup");
- the agent directly when the user asks "is this workbook OK" or "did anything break".

This skill is read-only. It does not modify the workbook it verifies.

## Caller passes

- **Edited workbook path** — the path the edit landed at. Required.
- **Backup workbook path** — the `.bak-<YYYY-MM-DD-HHMM>.xlsx` file `excel-safe-edit.md` wrote at its Step 1. Required (for the hand-off case); optional when this skill is invoked standalone for structural inspection.
- **Approved markdown source** — path to the markdown that drove the edit. Required for the headline-total cross-check.
- **Pre-edit inventory** — the structural inventory captured by `excel-safe-edit.md` at its Step 2 (sheet names, named ranges, tables, data validations, conditional formatting, print settings). Required for the hand-off case.
- **Edit summary** — what was edited, in what mode. Required for the hand-off case.
- **Active project folder path** — required for boundary enforcement per `../../AGENTS.md §11`.

For standalone structural-inspection use, only the workbook path and active project folder path are required; the rest are skipped or marked not-applicable in the report.

## Pre-flight

1. **Confirm active-project boundary.** The workbook must be within the active project folder. Per `../../AGENTS.md §11`.
2. **Confirm the workbook file exists at the expected path.** If not, fail and report.
3. **Confirm the backup file exists at the expected path** (for hand-off case). If not, this is a failure of `excel-safe-edit.md`'s Step 1 invariant — report and stop.

## Checklist

Run each check below. Report pass / fail for each. Do not declare completion until every required check passes.

| # | Check | Required | How to verify |
|---|---|---|---|
| 1 | Edited workbook file exists at the expected path | yes | filesystem check |
| 2 | Backup file exists at the recorded path | yes (hand-off case) | filesystem check |
| 3 | Workbook ZIP integrity passes | yes | open the `.xlsx` as a zip archive and confirm all entries unpack without error |
| 4 | Workbook loads successfully | yes | open with the editing library; no parse errors |
| 5 | All expected sheet names are present | yes | compare against pre-edit inventory |
| 6 | All named ranges from pre-edit are still present | yes | enumerate named ranges; compare against pre-edit inventory |
| 7 | All Excel tables (ListObjects) from pre-edit are still present | yes | enumerate tables; compare scope and column headers |
| 8 | No `#REF!` formulas in the workbook | yes | scan all cells with formulas for `#REF!`, `#NAME?`, `#NULL!`, `#DIV/0!` (the last two are warnings unless pre-existing) |
| 9 | Formulas preserved (or deliberately rewritten per caller) | yes | for cells outside the edit scope, formula text must match pre-edit; for cells inside the edit scope, formulas must be consistent with the update mode |
| 10 | Data validations / dropdowns present where they were before | yes | enumerate data validations; compare scope and rules |
| 11 | Conditional formatting preserved | recommended | enumerate conditional formatting rules; compare scope |
| 12 | Print settings preserved | recommended | check page setup, print area, print titles, headers/footers |
| 13 | Headline total in workbook equals the approved markdown total | yes | identify the headline-total cell (typically a named range like `Total_Contract_Sum` or a labelled cell on the summary sheet); compare its value against the markdown's stated total |
| 14 | Key rollups still reference the intended invoice / variation / claim ranges | yes | for rollup formulas identified in pre-edit, confirm the formula text still references the intended ranges (no row insert pushed a reference into a blank zone) |
| 15 | Frozen panes preserved | recommended | check frozen pane positions where pre-edit captured them |
| 16 | Column widths preserved on key visible columns | recommended | spot-check column widths on summary sheets |

Required checks (yes column) **must all pass** for completion. Recommended checks (recommended column) are reported but do not block completion — the caller decides whether to act on them.

## Report format

Final response to the caller must include the structured report below. The report format is the contract `excel-safe-edit.md` and the wider harness rely on.

```text
Output workbook: <path>
Backup workbook: <path>
Total entered:   <amount> (matches markdown: yes / no — <if no, the discrepancy>)
Verification:
  - Workbook file exists: pass / fail
  - Backup file exists: pass / fail
  - ZIP integrity: pass / fail
  - Workbook loads: pass / fail
  - Sheet names: pass / fail — <if fail, missing or unexpected sheets>
  - Named ranges: pass / fail — <if fail, missing or new>
  - Tables (ListObjects): pass / fail — <if fail, missing or changed>
  - No #REF! formulas: pass / fail — <if fail, cells affected>
  - Formulas preserved outside edit scope: pass / fail — <if fail, cells affected>
  - Formulas in edit scope consistent with update mode: pass / fail
  - Data validations / dropdowns present: pass / fail — <if fail, validations affected>
  - Conditional formatting preserved: pass / fail / not-checked
  - Print settings preserved: pass / fail / not-checked
  - Headline total matches markdown: pass / fail — <if fail, workbook value vs markdown value>
  - Key rollups intact: pass / fail — <if fail, rollup formulas affected>
  - Frozen panes: pass / fail / not-checked
  - Column widths: pass / fail / not-checked
Assumptions / unresolved review items:
  - <item, if any>
Save warnings carried from excel-safe-edit:
  - <warning, if any>
```

## Rule

If any **required** check fails, **do not report success**. Either:

- fix the issue by re-running `excel-safe-edit.md` from the backup (which restores the workbook to its pre-edit state) and applying a corrected edit;
- or **stop and ask the PM** — the workbook has drifted from the approved markdown and human judgement is needed.

The most common failure modes seen in practice:

- **`#REF!` after a row insert** — an absolute formula reference (e.g. `$B$10`) did not shift with the insert; the formula now points into the wrong row or into a blank.
- **Data validation stripped** — the editing library does not preserve dynamic-array or modern validations and silently drops them on save. Detection requires comparing pre-edit and post-edit validation lists.
- **Named range lost** — a row delete or sheet rearrange knocked out a named range. Common when the range was anchored to specific cells rather than a table.
- **Headline total off** — the workbook total does not match the approved markdown. Either the edit missed a cell, or the workbook's existing formulas computed a different total because of how the edit interacted with named ranges. Either way the workbook is not what the PM approved.
- **Sheet name changed** — a sheet was renamed by the edit (e.g. the markdown said "Cost Plan v02" and the agent renamed a sheet to match, breaking cross-sheet formulas).

This skill **does not fix** failures. It detects them. Fixing is `excel-safe-edit.md`'s job (re-run from backup) or the PM's call (manual intervention).

This skill is read-only. It does not modify the workbook, the backup, or the markdown source.

This skill respects the `../../AGENTS.md §11` active-project boundary — verifies only workbooks within the active project folder.

## See also

- `../../AGENTS.md §5` — output discipline + file-type convention (Excel is source of truth for numeric data)
- `../../AGENTS.md §11` — active-project boundary
- `../../00-doctrine/doctrine.md §evidence-discipline` — why the headline-total cross-check matters (the markdown is the approved record; the workbook must match it)
- `../../00-doctrine/doctrine.md §register-discipline` — registers held in Excel rely on this skill for ongoing integrity
- `excel-safe-edit.md` — canonical caller; the hand-off contract is documented there at Step 6
- `markdown-draft-for-review.md` — the markdown total this skill cross-checks against is produced there
- `../systems/cost-plan-system.md` — primary system caller (via excel-safe-edit) for cost-workbook updates
- `../../../Harness/02-skills/atomic/excel-verify.md` — commercial parent of this skill; the report format originates there
