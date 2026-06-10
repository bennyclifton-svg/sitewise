# System skill: document-intake-register-system

**Job:** Canonical document intake workflow for SiteWise projects. It governs Clerk Sort Files v1: inspect the active project's `_inbox/`, classify only confident files into known SiteWise folders, leave unclear or unsafe files in place, write a versioned intake manifest, and prepare document-register rows for review.

This system inherits `../_shared/pm-contract.md`. `02-skills/` is the canonical workflow contract; Clerk implements this workflow through its `sort-files` action.

## When to Use

Use this skill when:

- files have been dropped, dumped, emailed in, or copied into a project `_inbox/`;
- the user asks to sort files, classify incoming documents, tidy the inbox, or prepare an intake manifest;
- a later workflow needs the intake state understood before drafting from project evidence;
- the project document register needs rows drafted from newly filed source material.

This is a continuous evidence-control workflow, not a phase-gate synthesis deliverable. It still enforces the SiteWise system-skill declaration gate at the boundary because `AGENTS.md` requires the gate for system skill invocation.

## Caller Passes / Inputs

- **Active project folder path** - required.
- **Mode** - `sort-only`, `sort-and-draft-register-rows`, or `register-row-draft-only`. Defaults to `sort-only` for the current Clerk implementation.
- **Inbox path** - optional. Defaults to `<active project>/_inbox/`.
- **Clock / run timestamp** - optional. Used for manifest frontmatter and traceability.

The skill reads project evidence only from the active project folder.

## Output Location

- Intake manifest: `_inbox/intake_manifest_vNN.md`.
- Filed source files: known SiteWise lifecycle folders inside the active project.
- Draft document-register rows: target register chosen by the project evidence, typically a markdown or Excel document register under `03-design/`, `08-meetings-reporting/`, or a future document repository surface.

## Pre-flight - Step 0: Sec. 2 Declaration Gate

Before sorting or drafting:

1. Read the active project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC`.
3. If any declaration is missing, stop and ask the project lead to complete the README declaration. Do not infer the missing value from file names, folder names, address, budget or document contents.
4. Do not classify, move files, write manifests, or draft register rows until the gate passes.

The current Clerk local-v1 Sort Files path already operates against detected projects; this skill is the canonical contract that the app should continue to converge on.

## Sequence

### Step 1 - Resolve the Active Project and Inbox

Confirm the active project path is within the SiteWise workspace and that `_inbox/` is inside the active project.

If `_inbox/` is missing, create it and report the warning in the manifest. If `_inbox/` exists as a file rather than a folder, stop.

### Step 2 - Inspect Inbox Entries

Inspect source entries under `_inbox/` using lightweight metadata:

- file name and relative inbox path;
- extension and file type;
- file size;
- modified timestamp;
- short bounded preview for text and Markdown where available;
- first-page text extraction for PDF, DOCX and XLSX where available, used for drawing/report title blocks (document number, title, revision) as well as classification;
- metadata-only classification fallback when extraction is unavailable or over budget.

Clerk v1 currently treats nested inbox folder names as lightweight classification context and records nested source paths such as `_inbox/mechanical/M200.pdf`. If the practice later chooses direct-children-only behaviour, change Clerk and this skill together.

Prior `intake_manifest_vNN.md` files are audit records, not source files. They are skipped.

### Step 3 - Classify Only Confident Matches

Classify files into known SiteWise lifecycle destinations only. Typical destination families are:

- `00-brief-pmp/` for brief, scope, PMP, fee or intake material;
- `01-cost/` for cost, budget, invoice, claim, estimate and price material;
- `02-consultant/<discipline>/` for fee proposals, appointments and consultant-side commercial material;
- `03-design/<discipline>/` for drawings, reports, specifications, assessments and design submissions;
- `04-planning-and-authorities/` for DA, CDC, CC, BASIX, authority, sewer, certifier and planning evidence;
- `05-procurement/` for tender, quote, submission and procurement material;
- `06-programme/` where programme-specific evidence is clear;
- `07-construction/<subfolder>/` for contract, insurance, progress claim, variation, EOT, RFI, certificate, defect and report material;
- `08-meetings-reporting/` for minutes, action, decision and owner-update material;
- `09-handover-dlp/` for handover, warranty, O&M, as-built, PC and DLP material.

Design drawing schedules — window schedule, door schedule, finishes schedule, equipment schedule and similar consultant drawing registers — belong under `03-design/<discipline>/` (typically architect), not `06-programme/`. Reserve `06-programme/` for project time/scheduling material such as master programmes, construction programmes, milestone schedules, Gantt charts and lookaheads.

Use the established Clerk classifier and known folder map as the implementation reference for v1.

### Step 4 - Move, Leave, Skip or Refuse

For each inspected entry, return exactly one outcome:

| Outcome | Behaviour |
| --- | --- |
| `moved` | Move the source file to the known destination inside the active project. Create the destination folder only when the move needs it. |
| `already-filed` | Leave the source in place because the destination already contains identical content; report the suggested destination. |
| `unresolved` | Leave the source in `_inbox/` because there is no confident lifecycle-folder match. |
| `skipped` | Ignore a non-source entry such as a prior intake manifest. |
| `refused` | Leave the source in `_inbox/` because a guardrail blocked the move. |

### Step 5 - Enforce Guardrails

The workflow must not:

- delete source files or destination files;
- overwrite an existing destination file;
- move a file outside the active project;
- invent arbitrary destination folders;
- treat another project folder as evidence or a filing target;
- deep-parse binary files in v1;
- silently convert an unresolved or refused file into a moved file.

If the destination path exists and contains different content, refuse the move. If it contains identical content, report `already-filed`.

### Step 6 - Write the Intake Manifest

Use `../atomic/markdown-draft-for-review.md` discipline for the manifest wrapper and write `_inbox/intake_manifest_vNN.md`.

The manifest must include:

- `status: draft`;
- `author: agent`;
- run date and timestamp;
- active `project_path`;
- `inbox_path`;
- inspected count;
- moved, already-filed, unresolved, skipped and refused counts;
- inspected-file detail;
- separate sections for moved, already filed, unresolved, skipped, refused and warnings.

The manifest is an audit draft for review. It is not a substitute for source evidence or a reviewed document register.

### Step 7 - Draft Document-Register Rows

Where the caller requested register rows, use `../atomic/register-row-draft.md` one row at a time.

Minimum document-register fields:

| Field | Behaviour |
| --- | --- |
| ID | `Doc-<seq>` or existing register convention |
| Description | File title or concise document description |
| Owner | Document controller, project lead, authoring consultant, or responsible role |
| Status | `filed`, `unresolved`, `superseded`, `current`, `for-review`, or existing register vocabulary |
| Due / review date | Next review or confirmation date |
| Source / evidence reference | Original `_inbox/` path and final filed path where moved |
| Next action | Confirm metadata, resolve filing, review revision, or no action where complete |

When files are dropped into nested `_inbox/<package>/` folders, Sort Files uses the top-level inbox folder name as a classification hint (for example `_inbox/ARCHITECTURE/` → `03-design/architect/`, `_inbox/ELEC/` → `03-design/electrical/`, `_inbox/DA, MODs & STAMPED PLANS/` → `04-planning-and-authorities/`). Drawing-number patterns (CC-A-*, A###, E##, etc.) provide a secondary signal when folder hints are absent.

Clerk Sort Files v1 has implemented the sort-and-manifest path. Sort Files also renames moved files to a canonical `{documentNumber} - {title} Rev {revision}.{ext}` format when metadata can be parsed confidently, and upserts structured register rows (document number, title, revision, discipline) into the Documents tab register.

### Step 8 - Surface Gaps and Escalations

Surface:

- unresolved files needing human classification;
- refused moves needing path, duplication or destination review;
- apparent superseded drawings or revision conflicts;
- missing document metadata needed for a register row;
- evidence that should block a downstream workflow until sorted or reviewed.

Escalations route through `escalation-note-system.md`. The return summary must still name each trigger, route and recommended action.

### Step 9 - Return Summary

Return:

- manifest path;
- counts by outcome;
- moved-file destinations;
- unresolved, skipped and refused records;
- warnings;
- draft document-register rows where requested;
- open gaps and recommended next action.

## Rules / Must Not Do

- Do not bypass the active-project boundary.
- Do not guess missing overlay declarations.
- Do not delete or overwrite files.
- Do not invent a revision status.
- Do not treat unresolved files as project facts for later drafting.
- Do not write `project.db`.
- Do not issue external correspondence.

## Fixture Checks

The current worked fixtures establish the v1 intake-manifest shape:

- `04-projects/0200-bennett-residence/_inbox/intake_manifest_v01.md` - 30 inspected, 30 moved, 0 unresolved, 0 refused (after neighbour/APZ email-thread classification).
- `04-projects/1111-test/_inbox/intake_manifest_v01.md` - 30 inspected, 30 moved, 0 unresolved, 0 refused (after neighbour/APZ email-thread classification).

Future changes to the Sort Files classifier should update the fixtures, Clerk tests and this contract together.

## See Also

- `../_shared/pm-contract.md` - inherited system-skill contract.
- `../atomic/markdown-draft-for-review.md` - manifest draft wrapper discipline.
- `../atomic/register-row-draft.md` - document-register row drafting.
- `../atomic/evidence-sweep.md` - active-project evidence inventory.
- `../../AGENTS.md` Sec. 1, Sec. 2, Sec. 5, Sec. 9 and Sec. 11.
- `../../00-doctrine/doctrine.md` evidence discipline, register discipline and escalation triggers.
- `../../99-docs/issues/hermes-workspace-dashboard/025-add-project-inbox-and-sort-files-happy-path.md`.
- `../../99-docs/issues/hermes-workspace-dashboard/026-harden-sort-files-guardrails-and-manifest-behaviour.md`.
