# Skill: register-row-draft

**Job:** Draft a single register row that satisfies the §register-discipline schema, in the format the caller's destination requires (Excel-row or markdown-table). Return both the row and a one-line provenance note.

This skill is the §register-discipline enforcer at the point of creation. Every register in a SiteWise project — cost, variation, EOT, decision, action, risk, defects, inspection, authority approvals, consultant advice, design responsibility, design deliverables, design RFI, subcontractor, owner-supplied items, park-for-decision queue — has rows that must carry the same fields. This skill enforces those fields so registers stay useful for claim and decision reconstruction.

## When called

Called by:
- system skills writing register entries (e.g. `contract-setup-system` writes the initial rows of the authority approvals, cost, decision registers);
- atomic skills that produce a register row as their output;
- the agent directly, when the user asks "log this in the variation register" or "open a defects register entry".

## Caller passes

- **Register type** — one of the standard register types (see table below). Required.
- **Row content** — the substantive data for this row, in whatever loose form the caller has (free text, a list of facts, an extracted email). Required.
- **Destination format** — `excel` (returns a row of cells matching the register's column order) or `markdown` (returns a pipe-table row). Required.
- **Active project folder path** — for context only (the skill does not write to the register itself; that is the caller's job). Required.
- **Source / evidence reference** — the document, email, conversation, or observation this row is derived from. Required (per the schema below; if missing, the skill flags the gap and asks).

## The §register-discipline schema

Every register row must carry these seven fields:

| Field | Definition |
|---|---|
| **ID** | Unique identifier within the register. Format conventions vary by register type (see standard register types below). |
| **Description** | Plain-English statement of what the row is about. One to three sentences. Sufficient for a future reader to understand without opening the source document. |
| **Owner** | Single named party responsible for the next action. A role title (e.g. "Builder", "Architect-PM", "Owner") is acceptable where personhood is implied; a named person is preferred where one exists. "Project" or "TBC" is not acceptable. |
| **Status** | One of: `open`, `in-progress`, `awaiting-response`, `closed`, `superseded`, or a register-specific status (see standard register types below for register-specific status vocabularies). |
| **Due date** (or review date) | ISO date format `YYYY-MM-DD`. For registers tracking ongoing review (risk, decisions), this is the next review date. For registers tracking actions, this is the due date for the next action. |
| **Source / evidence reference** | Path or identifier for the source document, email, conversation, or observation. For documents: relative path within the project folder. For emails: subject + date + sender. For conversations: meeting reference and date. For observations: site visit date and observer. |
| **Next action** | The very next action to be taken, by the named owner, by the due date. One sentence, imperative voice. Specific enough that the owner knows what to do without asking. |

If any field cannot be populated from the caller's row content, the skill **flags the gap** and asks the caller. It does not silently fill with placeholders, "TBC", or "see linked document". A gap is recorded as a §register-discipline failure to be resolved before the row is committed.

## Standard register types

The following register types are recognised. The skill applies type-specific ID conventions and status vocabularies.

| Register | ID convention | Status vocabulary | Typical folder |
|---|---|---|---|
| **Cost register** | `C-<seq>` (e.g. `C-001`) | `committed`, `forecast`, `paid`, `pending` | `01-cost/` |
| **Variation register** | `V-<seq>` (e.g. `V-014`) | `proposed`, `priced`, `owner-signed`, `in-progress`, `completed`, `disputed`, `withdrawn` | `07-construction/06-variations/` |
| **EOT register** | `E-<seq>` | `noticed`, `assessed`, `granted`, `part-granted`, `rejected`, `disputed` | `07-construction/07-programme-eot/` |
| **Progress claim register** | `PC-<seq>` (e.g. `PC-007` — note conflict with PC = Practical Completion; use `Claim-<seq>` or `PrgClm-<seq>` where ambiguity matters) | `issued`, `assessed`, `certified`, `paid`, `disputed` | `07-construction/05-progress-claims/` |
| **Decision register** | `D-<seq>` | `decided`, `superseded` (append-only per §decision-discipline) | `08-meetings-reporting/` |
| **Action register** | `A-<seq>` | `open`, `in-progress`, `closed`, `cancelled` | `08-meetings-reporting/` |
| **Risk register** | `R-<seq>` | `identified`, `mitigated`, `accepted`, `realised`, `closed` | `00-brief-pmp/` or `08-meetings-reporting/` |
| **Defects register** | `Df-<seq>` | `identified`, `notified`, `in-rectification`, `closed`, `disputed` | `07-construction/11-defects/` then `09-handover-dlp/` |
| **Inspection register** | `I-<seq>` | `scheduled`, `attended`, `passed`, `failed`, `rescheduled` | `07-construction/12-reports/` |
| **Authority approvals tracker** | `AA-<seq>` | `lodged`, `under-assessment`, `issued`, `conditional`, `refused`, `not-applicable`, `gap-report`, `superseded` | `04-planning-and-authorities/` |
| **Consent conditions register** | `CC-<seq>` | `outstanding`, `in-progress`, `evidenced`, `closed` | `04-planning-and-authorities/` |
| **Consultant appointment tracker** | `CAT-<seq>` | `proposed`, `accepted`, `appointed`, `declined`, `expired`, `gap`, `superseded` | `02-consultant/` |
| **Consultant advice register** | `CA-<seq>` | `received`, `actioned`, `superseded` | `02-consultant/` |
| **Design responsibility register** | `DRM-<seq>` | `allocated`, `under-review`, `submitted`, `accepted`, `superseded`, `gap` | `02-consultant/` or `03-design/` |
| **Design deliverables register** | `DD-<seq>` | `planned`, `in-progress`, `issued-for-review`, `submitted-to-certifier`, `issued-for-construction`, `superseded` | `03-design/` |
| **Design RFI register** | `DRFI-<seq>` | `issued`, `awaiting-response`, `responded`, `closed`, `superseded` | `03-design/` or `07-construction/08-rfi-notices/` |
| **Subcontractor register** | `S-<seq>` | `tendered`, `awarded`, `mobilising`, `active`, `completed`, `terminated` | `05-procurement/` or `07-construction/` |
| **Owner-supplied items register** | `OS-<seq>` | `committed`, `ordered`, `delivered`, `installed`, `late` | `00-brief-pmp/` or `07-construction/` |
| **Park-for-decision queue** | `PFD-<seq>` | `parked`, `due`, `overdue`, `decided`, `superseded` | `08-meetings-reporting/` |
| **RFI register** | `RFI-<seq>` (e.g. `RFI-022`) | `issued`, `awaiting-response`, `responded`, `closed`, `superseded` | `07-construction/08-rfi-notices/` |
| **Contractual notices register** | `N-<seq>` | `issued`, `acknowledged`, `responded`, `closed`, `disputed` | `07-construction/08-rfi-notices/` |

Where the caller's register type is not in this list, the skill applies the generic schema (the seven fields above) with `<TypeAbbrev>-<seq>` as the ID convention and `open / in-progress / closed` as the default status vocabulary.

## Steps

### Step 1 — Identify and validate the register type

Read the register type from the caller. Match against the standard list. If not standard, apply the generic schema.

### Step 2 — Map row content to schema fields

Extract each of the seven required fields from the caller's row content. For each field:

- if explicitly present, use as provided;
- if implicitly derivable (e.g. owner can be inferred from sender of a referenced email), derive with a §evidence-discipline Judgement label internally and surface to the caller for confirmation;
- if absent, flag the gap.

For ID:
- if the caller knows the existing register's last ID, the skill returns the next sequential ID;
- if the caller does not know, the skill returns `<TypeAbbrev>-<TBD>` and notes "ID to be assigned by caller when row is committed to the register".

For Description:
- one to three sentences;
- plain language for the register's audience (cost register reader is the project lead; defects register reader includes the owner and the subcontractor);
- do not duplicate the row's other fields in the description (don't say "Owner: Builder" in the description text when Owner is its own column).

For Owner:
- single named party or role;
- if the caller provides a generic "Project" or "TBC", the skill flags and asks for a specific owner.

For Status:
- one of the register-type-specific vocabulary;
- if the caller's input doesn't map cleanly, the skill picks the closest and flags the mapping for confirmation.

For Due date:
- ISO format;
- for register types that track actions (Action, RFI, Variation), the due date is the next-action deadline;
- for register types that track ongoing state (Risk, Decision, Cost-paid), the due date is the next review date;
- if absent, flag and ask — "no date" is not acceptable for a register row.

For Source / evidence reference:
- a verifiable pointer back to where the row's content came from;
- if absent, flag and ask — an unsourced register row breaks the §evidence-discipline audit trail.

For Next action:
- one imperative sentence;
- specific enough that the owner can act without further clarification;
- if the row's status is `closed`, the next action is "none — row closed";
- if the row is `superseded`, the next action references the superseding row.

### Step 3 — Format for destination

If destination is `excel`:
- return a row of cells matching the register's column order;
- columns are: `ID | Description | Owner | Status | Due date | Source | Next action | <register-specific columns>`;
- register-specific columns for, e.g., the variation register would include `Cost`, `Time impact`, `Date proposed`, `Date owner-signed`, `Date completed`;
- the skill suggests the register-specific columns based on the register type (see below) but the caller's existing register schema wins where established.

If destination is `markdown`:
- return a pipe-table row;
- header row format (for reference): `| ID | Description | Owner | Status | Due | Source | Next action |`;
- a single row format: `| V-014 | Replace HW unit (gas → heat pump) per BASIX update | Builder | priced | 2026-06-03 | Variation form V-014.pdf | Owner to sign by 2026-06-03 |`.

### Step 4 — Return row + provenance note

Return:

1. **The row**, formatted as requested.
2. **A one-line provenance note** suitable for a draft commit message, decision log entry, or row-creation audit trail. Format: `<RegisterType> row <ID> drafted from <source>; status <status>; owner <owner>; due <date>.`

Example provenance note:
> Variation register row V-014 drafted from email "HW system change request" dated 2026-05-22 from owner; status priced; owner Builder; due 2026-06-03.

The provenance note is what the caller logs alongside the row in the project's general audit trail.

### Step 5 — Register-type-specific columns

For each register type, the typical register-specific columns are:

| Register | Additional columns |
|---|---|
| Cost | `Cost item`, `Budget amount`, `Committed`, `Paid`, `Variance` |
| Variation | `Cost`, `Time impact (days)`, `Date proposed`, `Date owner-signed`, `Date completed`, `Cumulative variation total` |
| EOT | `Cause`, `Days claimed`, `Days granted`, `Date noticed`, `Date assessed`, `Cumulative EOT total` |
| Progress claim | `Stage`, `Amount claimed`, `Amount certified`, `Amount paid`, `Date issued`, `Date due`, `Date paid` |
| Decision | `Decision-maker`, `Basis`, `Alternatives considered`, `Consequences`, `Date`, `Supersedes`, `Superseded-by` |
| Action | `Date raised`, `Originating forum`, `Date closed` |
| Risk | `Category`, `Likelihood`, `Consequence`, `Mitigation`, `Residual rating`, `Date reviewed` |
| Defects | `Trade`, `Location`, `Severity`, `Date identified`, `Date notified`, `Date closed`, `Photo reference` |
| Inspection | `Inspection type`, `Inspector`, `Scheduled date`, `Actual date`, `Outcome`, `Evidence reference` |
| Authority approvals | `Authority`, `Application reference`, `Date lodged`, `Date issued`, `Conditions reference` |
| Consent conditions | `Condition number`, `Source approval`, `Required by stage`, `Responsible party` |
| Consultant appointment | `Consultant / firm`, `Discipline`, `Appointed by`, `Scope stage`, `Fee basis`, `Key exclusions`, `Deliverables`, `Programme dependency` |
| Consultant advice | `Consultant`, `Advice topic`, `Date received`, `Action taken` |
| Design responsibility | `Design element`, `Responsible designer`, `Reviewer`, `Deliverable reference`, `Revision status`, `Certifier submission`, `Hold point` |
| Design deliverables | `Package`, `Discipline`, `Revision`, `Issue purpose`, `Submission status`, `Construction release dependency`, `Date issued` |
| Design RFI | `Question`, `Recipient`, `Discipline`, `Date issued`, `Date response due`, `Response summary`, `Affected deliverable` |
| Subcontractor | `Trade`, `Contract value`, `Insurance currency date`, `Licence number`, `Key dates` |
| Owner-supplied items | `Item`, `Supplier`, `Expected delivery date`, `Actual delivery date`, `Programme impact` |
| Park-for-decision queue | `Decision required`, `Options considered`, `Consequence if deferred`, `Decision-maker`, `Date parked`, `Decision date`, `Supersedes`, `Superseded-by` |
| RFI | `Date issued`, `Recipient`, `Date response due`, `Date responded`, `Response summary` |
| Contractual notices | `Notice type`, `Clause reference`, `Date issued`, `Recipient`, `Acknowledgement`, `Response` |

For an Excel destination, the column order is the seven core fields followed by the register-specific columns above. The skill suggests; the caller's existing register schema is authoritative if it differs.

## Rule

This skill produces **one row at a time**. Bulk-loading register rows from a source (e.g. extracting all variations from a meeting minute set) is a sequence of calls to this skill, one per row. Bulk handling is the caller's loop, not this skill.

This skill does **not write to the register file itself**. It returns the row content for the caller to insert. The caller is responsible for opening the register, inserting the row, and saving (for Excel registers, with `excel-safe-edit` — out of scope for slice 02; for markdown registers, with standard file edit).

This skill enforces the §register-discipline schema. **A row that cannot satisfy the schema is not produced** — the skill returns a gap report instead, naming each missing field.

## See also

- `../../00-doctrine/doctrine.md §register-discipline` — the schema this skill enforces
- `../../00-doctrine/doctrine.md §evidence-discipline` — why every row needs a source reference
- `../../00-doctrine/doctrine.md §decision-discipline` — why decision register rows are append-only (this skill's `superseded` status pattern)
- `seed-targeted-read.md` — typically called before this skill, to ensure the right seed coverage informs the row content
- `evidence-sweep.md` — typically called before this skill, to identify the source / evidence reference for the row
- `markdown-draft-for-review.md` — handles narrative deliverables; this skill handles register rows
- `../systems/contract-setup-system.md` — primary caller, opens the standard registers using this skill at commissioning
