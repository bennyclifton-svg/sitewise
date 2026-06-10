# System skill: decision-record-system

**Job:** Capture project decisions in an append-only decision register, with role-shaped decision-maker logic, evidence references, consequences and follow-up actions.

This system inherits `../_shared/pm-contract.md`. It is the canonical SiteWise workflow for turning a decision, decision request, meeting outcome, owner direction, forum resolution, or project-lead decision within authority into a reviewable decision record.

## When to Use

Use this skill when:

- a decision has been made and needs to be recorded;
- a decision is required from the owner, Principal, owner-builder, project lead, consultant or forum;
- meeting minutes contain a confirmed decision that should be separated from discussion;
- procurement, cost, programme, design, authority, variation, EOT, handover or risk work depends on a recorded decision;
- a previous decision is superseded and the superseding decision needs to link back.

This is a continuous evidence-control workflow. It is not a phase-gate synthesis deliverable, but it is a system skill and therefore enforces the SiteWise declaration gate at the boundary.

## Caller Passes / Inputs

- **Active project folder path** - required.
- **Decision subject** - required.
- **Decision source / evidence reference** - required. Examples: meeting minute, owner email, signed direction, tender evaluation, approved cost plan, site instruction, consultant advice, RFI response.
- **Decision text** - required. If this is an owner or Principal direction, pass the exact wording to be quoted.
- **Decision-maker or forum** - optional if clear from evidence; otherwise the skill flags the gap.
- **Decision date** - optional if clear from evidence; otherwise the skill flags the gap.
- **Mode** - `open-register`, `append-decision`, `supersede-decision`, or `decision-request`. Defaults to `append-decision` where a decision is already evidenced.
- **Known register path** - optional. Defaults to discovery through `evidence-sweep`.

The skill reads everything else from the active project folder.

## Output Location

Default destination: `08-meetings-reporting/decision-register.md`.

Task-specific registers can also be used where project evidence has already established them:

- `03-design/design-decision-register.md` for design-gate decisions.
- `05-procurement/<package>/05-evaluation/decision-register.md` for tender-stage decisions.
- `07-construction/06-variations/variation-decision-register.md` for variation sign-off decisions where a separate register exists.

If no project-specific decision register exists, open `08-meetings-reporting/decision-register.md` as the working register.

## Pre-flight - Step 0: Sec. 2 Declaration Gate

Before drafting:

1. Read the active project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC`.
3. If any declaration is missing, stop and ask the project lead to complete the README declaration.
4. Do not run evidence-sweep, draft rows, open a register, or mark any decision until the gate passes.

## Sequence

### Step 1 - Evidence Sweep

Invoke `../atomic/evidence-sweep.md` with task subject `project decision record: <decision subject>`.

High-relevance evidence includes:

- `README.md` for overlays and role context;
- `00-brief-pmp/` for brief, PMP, contract summary, owner-supplied items and setup decisions;
- `01-cost/` for budget, contingency, claim, invoice and cost-plan decisions;
- `02-consultant/` and `03-design/` for consultant advice, drawing revisions, design responsibility and design-risk decisions;
- `04-planning-and-authorities/` for approval pathway and consent-condition decisions;
- `05-procurement/` for shortlist, RFT issue, tender recommendation and award decisions;
- `06-programme/` for baseline, milestone, staging and EOT-related decisions;
- `07-construction/` for directions, variations, RFIs, claims, certificates, defects and site decisions;
- `08-meetings-reporting/` for minutes, action registers, decision registers and owner updates;
- `09-handover-dlp/` for PC, defects, warranties, O&M and DLP close-out decisions.

The source / evidence reference is mandatory. If a decision is reported verbally with no record, produce a decision-request or confirmation-note gap instead of a committed decision row.

### Step 2 - Locate or Open the Decision Register

Find the working decision register in this order:

1. Caller-provided register path.
2. Existing `08-meetings-reporting/decision-register.md` or `.xlsx`.
3. Existing task-specific decision register surfaced by evidence-sweep.
4. New markdown register draft at `08-meetings-reporting/decision-register.md`.

If opening a new markdown register, use `../atomic/markdown-draft-for-review.md` and include a header table with the core decision fields. The opening row is normally:

`D-001 | Project decision register opened under SiteWise | Project lead | decided | <today> | README.md / setup evidence | Use this register for future decisions`

Do not create an Excel register unless project evidence or user direction already makes Excel the source of truth. Excel creation and edits go through `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md`.

### Step 3 - Determine the Decision-Maker / Forum

Use the role overlay and evidence to identify the decision-maker:

| Role | Default decision-maker logic |
| --- | --- |
| `owner-builder` | Self, recorded as owner-builder decision or park-for-decision outcome. |
| `architect-pm` | Owner decides; architect-PM advises unless an authority matrix says otherwise. |
| `builder` | Owner decides owner-facing scope/cost/time matters; builder decides within builder authority; technical matters route to the responsible consultant or engineer. |
| `d-and-c` | Owner/Principal decides changes to PPR, scope, cost and time where contract requires; D&C carries design and construction recommendation within its responsibility. |

If the decision-maker is unclear, do not invent one. Return a gap and draft an action row asking the project lead to confirm authority.

### Step 4 - Classify the Decision State

Use one of these states:

- `decided` - a decision has been made and is evidenced.
- `decision-request` - a decision is needed but not yet made.
- `superseded` - an older decision remains in the register but is replaced by a later decision.

Decision-register rows use `decided` or `superseded` as the register status. Decision requests become action rows and, where useful, decision-register draft rows with clear status that no decision has yet been made.

### Step 5 - Draft the Decision Row

Use `../atomic/register-row-draft.md` with register type `Decision register`.

Every decision row must include:

| Field | Required behaviour |
| --- | --- |
| ID | `D-<seq>` from the existing register; `D-<TBD>` only in draft output before insertion. |
| Description | The decision made, in one to three sentences. |
| Owner | The decision-maker or owner of the next action. |
| Status | `decided` or `superseded`. |
| Due / review date | Next review or follow-up date in ISO format. |
| Source / evidence reference | Active-project path, meeting reference, email/source identifier, or explicit gap basis. |
| Next action | One imperative action, or `None - decision recorded` only where no follow-up exists. |
| Decision-maker | Person, role, or forum. |
| Basis | Evidence and judgement basis for the decision. |
| Alternatives considered | Material options considered, or `Not material / not evidenced`. |
| Consequences | Cost, time, scope, quality, risk and compliance consequences. |
| Date | Decision date in ISO format. |
| Supersedes | Prior decision ID where applicable. |
| Superseded-by | Later decision ID where marking an older decision superseded. |

If any core field is missing, return a gap report instead of a row.

### Step 6 - Quote Owner / Principal Directions

Never paraphrase an owner or Principal direction.

If the decision comes from an owner or Principal direction, include a short exact quotation in the row description or basis, with a source reference. If the source wording is too long, quote the operative direction and summarise the rest as Fact / Judgement with citation.

If the direction is verbal, record that the decision is not yet evidenced and draft the next action: confirm the direction in writing.

### Step 7 - Supersede Without Rewriting History

Decision registers are append-only.

When a decision is superseded:

1. Add a new decision row for the superseding decision.
2. Reference the prior decision in `Supersedes`.
3. Mark the prior row as `superseded` only by a controlled register update or a draft row update request.
4. Add `Superseded-by` to the prior row where the register substrate supports it.
5. Do not delete, overwrite, or silently edit the historical basis of the prior decision.

If the existing register is markdown, the agent may draft the updated table for review. If the register is Excel, use `excel-safe-edit` and `excel-verify`.

### Step 8 - Feed Actions, Risks and Escalations

Where consequences require follow-up:

- draft action rows through `../atomic/register-row-draft.md`;
- draft risk rows or call `risk-register-system.md` where the decision introduces or closes material risk;
- surface escalation triggers where the decision affects budget, programme, scope, authority, compliance, role authority or safety.

Route escalation triggers through `escalation-note-system.md`, and report each trigger, route and recommended action in the return summary.

### Step 9 - Return Summary

Return:

- decision register path;
- decision row(s) drafted;
- action or risk rows drafted;
- supersession links;
- missing evidence or authority gaps;
- escalation triggers;
- recommended next action.

## Rules / Must Not Do

- Do not record conversation as a decision.
- Do not invent a decision-maker or authority.
- Do not paraphrase an owner or Principal direction.
- Do not commit a decision row without a source / evidence reference.
- Do not edit a past decision in place except to mark supersession through a controlled update.
- Do not delete historical decisions.
- Do not write `project.db`.
- Do not issue external correspondence.

## Fixture Checks

The current Bennett and `1111-test` fixtures do not contain a live decision register. A dry-run check for both fixtures therefore exercises the open-register path:

- active project README declarations are present;
- no existing decision register is found;
- default output is `08-meetings-reporting/decision-register.md`;
- opening row is `D-001`;
- source evidence remains read-only.

Future fixture runs should add an append-row and supersede-row case once a decision register fixture exists.

## See Also

- `../_shared/pm-contract.md` - inherited system-skill contract.
- `../atomic/evidence-sweep.md` - active-project evidence discovery.
- `../atomic/register-row-draft.md` - decision and action row drafting.
- `../atomic/markdown-draft-for-review.md` - markdown register draft wrapper.
- `contract-setup-system.md` - opens the standard decision register at commissioning.
- `risk-register-system.md` - risk rows for decision consequences.
- `../../00-doctrine/doctrine.md` decision discipline, register discipline, evidence discipline and escalation triggers.
- `../../01-seed/setup-and-commission-guide.md` cross-cutting registers opened at commissioning.
