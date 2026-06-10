# Skill: excel-safe-edit

**Job:** Edit an Excel workbook (`.xlsx` / `.xlsm`) without breaking formulas, named ranges, tables (ListObjects), data validations / dropdowns, conditional formatting, or print settings. Drive the edit from an **approved** markdown source — never from rough assumptions sitting in the agent's head.

This skill is one of the §evidence-discipline enforcers when the destination is a workbook (per `../../AGENTS.md §5` file-type convention — Excel is the source of truth for numeric data). Workbooks are the working source of truth for cost, programme, and risk registers in SiteWise. Breaking a workbook silently — stripping a dropdown, corrupting a formula, replacing a named range — destroys the audit trail this harness is built on. The hard rules in this skill exist because each has been seen to fail in practice.

## When called

Called by:
- system skills updating workbook destinations from approved markdown (e.g. `cost-plan-system` calls this skill after the markdown cost plan is approved by the PM, to push the approved totals into the project's cost workbook);
- atomic skills that need to update an existing workbook (e.g. adding a row to a tracker workbook);
- the agent directly when the user explicitly asks to update a workbook with content the agent has already produced as a markdown draft.

This skill is **not** called for:
- creating a workbook from scratch (use a template; this skill edits an existing workbook);
- reading a workbook for inspection only (no skill needed — open and inspect);
- rough edits not yet reviewed (return to `markdown-draft-for-review.md` first).

## Precondition (non-negotiable)

A PM-approved markdown source exists. The skill **drives the workbook edit from the approved markdown**, not from the agent's interpretation of the user's prompt. If the caller cannot point to an approved markdown:

- if the workbook destination is a register-row insert and the row content has been drafted via `register-row-draft.md`, the row draft is the approved source (the caller's review of the row counts as approval);
- otherwise the skill **stops** and routes the caller back to `markdown-draft-for-review.md` to produce an approved markdown first.

This precondition is the §evidence-discipline boundary for workbook edits. The commercial parent of this skill (`../../../Harness/02-skills/atomic/excel-safe-edit.md`) makes the same call for the same reason — the workbook is too easy to corrupt silently if the edit is driven by anything less disciplined than a reviewed markdown.

## Caller passes

- **Workbook path** — absolute or project-relative path to the target workbook. Required.
- **Approved markdown source** — path to the markdown draft that drives the edit. Required.
- **Specific cells, ranges, or sheets to update** — the targeted scope of the edit. Required. The skill does not infer scope from the markdown; the caller specifies.
- **Update mode** — `replace` (overwrite cell values in the target scope), `append` (add row(s) to a table or sheet), or `insert` (insert rows at a specific position). Required.
- **Active project folder path** — required for boundary enforcement per `../../AGENTS.md §11`.
- **Output path** — defaults to in-place (the workbook is updated in place). The caller can specify a separate output path to keep the original unchanged. The skill always writes a backup regardless.

## Pre-flight

Before any edit:

1. **Confirm active-project boundary.** The workbook path must sit within the active project folder. If it does not, the skill **stops** and flags — editing a sibling project's workbook is an `../../AGENTS.md §11` boundary breach.
2. **Confirm the file exists and is a workbook.** Extension must be `.xlsx` or `.xlsm`. If the file is `.xls` (legacy binary), the skill flags — the editing libraries do not preserve all legacy features safely.
3. **Confirm the approved markdown source exists.** If the caller passed a path that does not resolve, the skill stops.
4. **Confirm the workbook is not currently locked open** (no `~$<filename>.xlsx` companion lock file). If it is, the skill flags and asks the caller to close the workbook before proceeding.

## Steps

### Step 1 — Back up first

Copy the workbook to `<filename>.bak-<YYYY-MM-DD-HHMM>.xlsx` alongside the original. The backup carries the same extension as the original (`.bak-...xlsx` or `.bak-...xlsm`).

**Do not proceed if the backup did not write.** Confirm the backup file exists at the expected path and has the same byte count as the original (a corrupted truncated backup is worse than no backup — the agent thinks rollback is available when it is not).

The backup file is recorded for `excel-verify.md` to confirm in Step 6's hand-off.

### Step 2 — Open and inspect

Open the workbook. Note structural elements that **must be preserved** post-edit:

- **sheet names** — every sheet present at open must be present at save;
- **named ranges** — every named range must survive;
- **Excel tables (ListObjects)** — table names, column headers, structured reference scope;
- **data validations** — dropdown lists, list sources, validation criteria (the §evidence-discipline-critical Description / Role dropdowns and similar);
- **conditional formatting** — rules and their applied ranges;
- **print settings** — page setup, print area, print titles, headers/footers;
- **frozen panes** and column widths where the workbook's usability depends on them;
- **defined formulas** — every cell formula must either remain unchanged or be deliberately rewritten per the caller's edit scope.

This inventory is held in memory for verification at Step 6's hand-off. The skill does **not** modify these elements unless the caller's edit scope explicitly requires it.

### Step 3 — Make only the requested changes

Apply the edit per the caller's update mode and scope:

- **`replace`** — overwrite cell values in the target scope. Preserve cell formatting unless the caller asks otherwise. Do not change cell type unless the caller asks (e.g. don't turn a text cell into a number cell because the new value is numeric — this can break downstream formulas that key on cell type).
- **`append`** — add row(s) to the target table or sheet. For Excel tables (ListObjects), extend the table range so structured references continue to cover the new rows. For non-table sheets, write to the next empty row at the bottom of the target column range.
- **`insert`** — insert rows at the specific position. Shift existing rows down (or right for column insert). Watch for absolute cell references in formulas that should adjust but do not — flag these.

Hard rules during the edit:

- **Preserve existing formulas** in cells the caller did not target. Do not "tidy" formulas. Do not flatten formulas to values.
- **Preserve Excel tables and structured references.** Do not break a `=SUM(Table1[Cost])` reference by editing the table's column header.
- **Preserve data validation lists.** Never save the workbook in a way that strips them. If the editing library reports that modern data validations (e.g. dynamic array validation, regex-based) are unsupported, switch to a safer method or save and immediately verify the validation post-save (per Step 6).
- **Preserve cross-sheet text-matching alignment.** Cost-plan, claim, and variation workbooks frequently use text-equality formulas to pull values across sheets (`=VLOOKUP(A2, 'Variations'!A:B, 2, FALSE)`). An edit that changes the text in the lookup key on one sheet must also change the matching key on the other sheet — or both sheets must be edited atomically.
- **Do not flatten, rebuild, or simplify the workbook.** The user's workbook is a working artefact; if it has redundant sheets, blank columns, or odd structure, leave them. Cleanup is a separate, sanctioned task.
- **Do not overwrite the source file unless the caller explicitly asked for replacement.** Default behaviour writes to the original path with a backup beside it; if the caller passed an output path, write there instead.

### Step 4 — Force recalculation on open

Set the workbook's recalculation flag so dependent formulas refresh when the workbook is next opened. This catches stale cached values from before the edit.

### Step 5 — Save

Save the workbook to the agreed output path (in-place if the caller did not specify otherwise).

If the save raises any warning (legacy compatibility, unsupported feature, etc.), **do not silently accept it**. Capture the warning and surface it in the hand-off — `excel-verify.md` may need to confirm the affected feature still works.

### Step 6 — Hand off to excel-verify

The skill is incomplete until `../atomic/excel-verify.md` has run against the edited workbook and confirmed all required checks pass.

The hand-off passes:
- **Edited workbook path** — where the save landed;
- **Backup path** — the `.bak-...xlsx` file from Step 1;
- **Approved markdown source** — for total / line-item cross-check;
- **Edit summary** — what cells / ranges / sheets were edited, what update mode was used;
- **Pre-edit inventory** — sheet names, named ranges, tables, data validations, conditional formatting, print settings captured at Step 2 (so verify can confirm they all survived);
- **Any save warnings** — from Step 5.

If verify fails any required check, the skill is **not done**. Either fix the issue (rerunning this skill from the Step 1 backup if needed) or stop and ask the PM.

## Hard rules

- **Never strip data validations or dropdown lists.** They are part of the workbook's discipline. Stripping them silently downgrades the workbook's reliability.
- **Never overwrite the only copy of a workbook.** The backup at Step 1 is mandatory. If it failed, stop.
- **Never commit assumptions directly to the workbook.** Drive every edit from the approved markdown source. The precondition is non-negotiable.
- **Never leave `#REF!` formulas behind.** A row insert / delete that breaks an absolute reference must be detected and fixed (or the operation rolled back) before save.
- **Never edit a workbook in a sibling project folder** — `../../AGENTS.md §11` active-project boundary.
- **Never overwrite or modify the backup file.** The backup is the rollback path. If verify fails, the backup is restored — touching it removes the rollback.

## Rule

This skill is the **controlled exception** to the rule that Excel files are read-only by default (per `../../AGENTS.md §5`). It exists because some workbooks (cost trackers, programme trackers, register Excels) are the working source of truth and need to be updated as the project evolves. The discipline is what makes the exception safe: approved markdown source → backup → preserve structure → recalc → save → verify. Every step is needed.

This skill does **not** create workbooks. It edits existing ones. If a workbook does not exist, the caller needs to either copy from a template (a manual / setup step outside this skill) or use a `register-row-draft` markdown register instead.

This skill does **not** flip an existing markdown draft's `status:` to `reviewed`. Markdown status is the PM's call. The skill's precondition is that an approved markdown source exists — the markdown's `status: reviewed` flag is the evidence of approval. If the markdown is `status: draft`, the caller is responsible for confirming that the user has approved its content before invoking this skill (typical when a user accepts a draft in conversation but the file flag has not been updated).

## See also

- `../../AGENTS.md §1` — authority stack (project evidence is tier 1; the workbook is project evidence)
- `../../AGENTS.md §5` — output discipline + file-type convention (Excel is source of truth for numeric data; this skill is the controlled exception to Excel-is-read-only)
- `../../AGENTS.md §11` — active-project boundary (the boundary this skill respects)
- `../../00-doctrine/doctrine.md §evidence-discipline` — why the approved-markdown precondition exists
- `../../00-doctrine/doctrine.md §register-discipline` — workbook registers carry the seven-field schema; this skill preserves the columns that hold it
- `markdown-draft-for-review.md` — must precede this skill (the approved markdown source comes from there)
- `register-row-draft.md` — for register-row workbook inserts, the row draft is the approved source; this skill inserts the row
- `excel-verify.md` — must follow this skill (the hand-off at Step 6 is mandatory before reporting completion)
- `../systems/cost-plan-system.md` — primary caller for cost-workbook updates
- `../../../Harness/02-skills/atomic/excel-safe-edit.md` — commercial parent of this skill; the hard rules originate there
