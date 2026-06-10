# System skill: escalation-note-system

**Job:** Draft early-warning escalation notes that turn a SiteWise trigger into a routed, evidence-labelled, action-oriented draft for review.

This system inherits `../_shared/pm-contract.md`. It is the canonical workflow for the "surface gaps and escalations" step used by other system skills.

## When to Use

Use this skill when:

- any workflow detects a doctrine escalation trigger;
- a register row is overdue, owner-less, source-conflicted, high-risk, or blocking a phase gate;
- a decision is needed from the owner, Principal, project lead, consultant, certifier, authority, insurer, subcontractor or builder;
- evidence conflicts or is missing and the conflict affects time, cost, scope, quality, compliance, safety or risk;
- the user asks for an early-warning note, escalation note, owner warning, self-flag, formal notice support, RFI support or recommended action.

This skill does not replace the domain system that found the issue. It packages the trigger into a decision-ready draft and links it back to the relevant registers and decision records.

## Caller Passes / Inputs

- **Active project folder path** - required.
- **Trigger summary** - required. One sentence stating what has been detected.
- **Trigger source** - required. System skill, register row, evidence file, meeting, email, observation or issue reference.
- **Mode** - `classify-trigger`, `draft-note`, `route-escalation`, or `link-records`. Defaults to `draft-note`.
- **Impact focus** - optional. One or more of `time`, `cost`, `scope`, `quality`, `risk`, `compliance`, `safety`, `authority`, `contract`.
- **Known recommendation** - optional. If omitted, the skill must derive a recommendation from evidence and doctrine or refuse the note as problem-only.
- **Target audience** - optional. If omitted, derive from the role overlay and trigger type.
- **Linked register rows** - optional. Risk, action, decision, RFI, notice, variation, EOT, claim, authority, defect, design or park-for-decision rows.
- **Due date / response date** - optional. Required before any register row can be drafted.

The skill reads project evidence only from the active project folder.

## Output Location

Use the role overlay and trigger route:

| Role / route | Default output |
| --- | --- |
| `owner-builder` self decision | `08-meetings-reporting/park-for-decision*` row plus optional park-for-decision note in the same folder |
| `architect-pm` owner decision | `08-meetings-reporting/owner-update-<topic>-vNN.md` or owner-facing escalation summary |
| `builder` owner / Principal decision | `07-construction/08-rfi-notices/` draft request, RFI or notice support, with stakeholder explanation where appropriate |
| `builder` technical question | `07-construction/08-rfi-notices/` RFI draft linked to the RFI register |
| `builder` authority / compliance question | `04-planning-and-authorities/` or `07-construction/08-rfi-notices/` per evidence |
| `d-and-c` design-side issue | Builder route plus `03-design/`, `04-planning-and-authorities/`, consultant / certifier path, or confidential management escalation where PI liability is live |

Every narrative output goes through `../atomic/markdown-draft-for-review.md`. Every linked row goes through `../atomic/register-row-draft.md`.

The output is a draft. It is not issued correspondence, a formal notice, an instruction, a certification or a human decision.

## Pre-flight - Step 0: Sec. 2 Declaration Gate

Before classifying or drafting:

1. Read the active project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC`.
3. If any declaration is missing, stop and ask the project lead to complete the README declaration.
4. Do not run evidence-sweep, classify the trigger, draft a note, or draft register rows until the gate passes.

## Sequence

### Step 1 - Seed Targeted Read

Invoke `../atomic/seed-targeted-read.md` with task subject `escalation note: <trigger summary>`.

Always load the role overlay because routing is role-shaped.

Load cross-cutting topic seeds only where the trigger requires them:

- `cost-management-principles.md` for budget, contingency, PC sum, claim, variation value or owner-supplied item triggers;
- `program-scheduling-guide.md` for critical-path, lead-time, milestone, delay, lookahead, EOT or handover date triggers;
- `contract-administration-guide.md` for notices, RFIs, claims, EOTs, variations, latent conditions, payment disputes or formal correspondence;
- `setup-and-commission-guide.md` for setup, authority, insurance, licence, LSL, HBCF/HOW, role or ready-to-start gaps;
- `procurement-quoting-guide.md` for tender, quote, low-bid, scope-gap, subcontractor or award triggers;
- `sustainability-energy-guide.md` for BASIX, NatHERS, energy-compliance or substitution triggers;
- role, archetype and trade seeds as selected by `seed-targeted-read`.

Record loaded seeds in `seed_consulted:` for the draft.

### Step 2 - Evidence Sweep

Invoke `../atomic/evidence-sweep.md` with task subject `escalation trigger: <trigger summary>`.

The sweep must identify:

- source evidence supporting the trigger;
- conflicting evidence;
- missing evidence that prevents the trigger from being treated as Fact;
- linked registers and rows;
- linked decisions or decision requests;
- deadlines, response dates, hold points and contractual windows.

Do not read another project folder to resolve the trigger.

### Step 3 - Classify the Trigger

Map the trigger to at least one doctrine trigger:

| Trigger class | Examples |
| --- | --- |
| Budget / contingency movement | forecast overrun, PC sum depletion, unpriced variation, owner-supplied item cost pressure |
| Critical path threatened | long-lead item, authority delay, certifier hold, utility delay, weather / EOT exposure |
| Scope unclear or changing | verbal direction, design ambiguity, trade scope gap, owner selection, latent condition |
| Approval / authority uncertainty | DA/CDC/CC/BPA/OC, consent condition, BASIX/NatHERS, Sydney Water or state equivalent |
| Late deliverable | consultant advice, subcontractor quote, design package, claim response, RFI response |
| Decision required | owner, Principal, owner-builder self, project lead, certifier, consultant or insurer decision |
| Role / authority unclear | architect-PM authority, D&C design responsibility, who can issue instructions |
| Evidence conflict | register row conflicts with current evidence, duplicate source, superseded drawing or contradictory advice |
| Safety / compliance risk | WHS, NCC, BASIX, structural, waterproofing, HBCF/HOW, insurance, PI liability |

If no trigger class applies, return a non-escalation finding and do not draft an escalation note.

### Step 4 - Label Evidence Discipline

Every material statement in the note must be classified as:

| Label | Use |
| --- | --- |
| Fact | Supported by active-project evidence or direct observation. |
| Assumption | Reasonable but not yet evidenced; must be named and assigned a confirmation action. |
| Judgement | Project lead interpretation based on evidence, doctrine and seeds. |
| Recommendation | Proposed action for the decision-maker or responsible party. |

Where Fact, Assumption and Judgement appear together, label them in the note. Never present an assumption as a fact.

### Step 5 - Establish Impact

State the likely impact across the dimensions that matter:

- time;
- cost;
- scope;
- quality;
- risk;
- compliance / authority;
- safety;
- contractual position.

Use `not material on current evidence` where a dimension has been checked and no material impact is apparent. Use `unknown - evidence gap` where it cannot be assessed.

### Step 6 - Derive the Role-Shaped Route

Use the loaded role overlay:

| `user_role` | Routing rule |
| --- | --- |
| `owner-builder` | Draft or update the park-for-decision queue in `08-meetings-reporting/`; overdue self-decisions are escalation items, not quiet tasks. |
| `architect-pm` | Draft an owner-facing summary using `owner-communication`; include recommendation, due date and cost/time/risk consequence. |
| `builder` | Route owner decisions to the owner / owner's representative; technical questions to the consultant or engineer of record; contract notices to `07-construction/08-rfi-notices/`; authority questions to the certifier or authority. |
| `d-and-c` | Apply builder routing plus design-side routing to certifier, responsible consultant, design manager, owner / Principal or PI insurer where design compliance or liability is live. |

If the role route is unclear, that uncertainty is itself an escalation trigger. Draft an authority-clarification action instead of pretending a route exists.

### Step 7 - Refuse Problem-Only Notes

An escalation note must contain all of:

1. trigger;
2. evidence classification;
3. impact;
4. recommended action;
5. responsible owner or recipient;
6. due date or response path;
7. linked register / decision / source reference, or a stated evidence gap.

If the note only says what is wrong, refuse to draft it. Return:

> Cannot draft escalation note: this is a problem-only escalation. Provide or approve a recommended action, responsible party and due date, or ask the skill to draft an action row to establish them.

If the caller asks to suppress a trigger, refuse and surface the trigger in the return summary.

### Step 8 - Draft the Escalation Note

Use `../atomic/markdown-draft-for-review.md`.

Minimum note structure:

```markdown
# Escalation Note - <topic>

## Trigger

<one sentence>

## Evidence Classification

| Label | Statement | Source |
| --- | --- | --- |
| Fact | ... | ... |
| Assumption | ... | ... |
| Judgement | ... | ... |
| Recommendation | ... | ... |

## Impact

| Dimension | Impact |
| --- | --- |
| Time | ... |
| Cost | ... |
| Scope | ... |
| Quality | ... |
| Risk | ... |
| Compliance / authority | ... |

## Recommended Action

<recipient / owner> to <specific action> by <date or response path>.

## Linked Records

- Register rows: ...
- Decision records: ...
- Source evidence: ...
```

For owner-facing stakeholder summaries, lead with `What this means for you` and `What we need from you`, then include the evidence table below.

### Step 9 - Draft Linked Register and Decision Rows

Use `../atomic/register-row-draft.md` for each required row:

- action row for the immediate next action;
- risk row where exposure remains open;
- decision row or decision-request row where the owner / Principal / self must decide;
- park-for-decision row for owner-builder self-decisions;
- RFI or notice row where the route is formal;
- variation, EOT, progress claim, authority, defect, design or consultant row where the trigger belongs to that register.

Use `decision-record-system.md` where a decision has been made or must be formally requested. Use `register-maintenance-system.md` if an existing row is stale, duplicate, source-missing or invalid.

### Step 10 - Do Not Issue

This skill drafts. It does not:

- send an email;
- issue a formal notice;
- direct work;
- certify a claim, PC, OC or compliance status;
- approve a variation, EOT, claim, cost movement or risk acceptance;
- decide for the owner, Principal, owner-builder, certifier, engineer, insurer or authority.

External issuance or approval requires human review.

### Step 11 - Return Summary

Return:

- trigger class;
- seed list and evidence consulted;
- output path or refusal reason;
- route and audience;
- recommended action;
- linked register rows drafted;
- linked decision records or decision requests;
- open evidence gaps;
- whether correspondence was issued (`no`, unless a human separately directed issuance after review).

## Rules / Must Not Do

- Do not draft a problem-only escalation note.
- Do not suppress an escalation trigger.
- Do not present assumptions as facts.
- Do not recommend action without a responsible party and due date / response path.
- Do not issue external correspondence.
- Do not route a technical question to the owner where the consultant, engineer, certifier or authority is the correct recipient.
- Do not take an owner, Principal, certifier, engineer, insurer or authority decision.
- Do not write `project.db`.
- Do not read another project folder.

## Fixture Checks

Use `../../99-docs/issues/sitewise-skills-framework-alignment/fixtures/escalation-note/critical-path-trigger-input.md` for a dry-run.

Expected result:

- trigger classified as critical-path threatened and decision required;
- evidence table labels Fact, Assumption, Judgement and Recommendation separately;
- recommended action is addressed to the owner with a due date;
- linked decision-request and risk/action rows are named as drafts;
- output matches the shape in `../../99-docs/issues/sitewise-skills-framework-alignment/fixtures/escalation-note/expected-draft-escalation-note.md`;
- `correspondence_issued: false`.

## See Also

- `../_shared/pm-contract.md` - inherited system-skill contract.
- `../atomic/seed-targeted-read.md` - targeted seed loading.
- `../atomic/evidence-sweep.md` - active-project evidence discovery.
- `../atomic/markdown-draft-for-review.md` - draft output wrapper and voice/folder discipline.
- `../atomic/register-row-draft.md` - linked register rows.
- `decision-record-system.md` - decision record and decision-request workflow.
- `register-maintenance-system.md` - stale, duplicate or invalid row repair path.
- `risk-register-system.md` - risk rows and risk commentary.
- `../../00-doctrine/doctrine.md` evidence discipline, register discipline, decision discipline and escalation triggers.
- `../../01-seed/role-owner-builder.md`, `../../01-seed/role-architect-pm.md`, `../../01-seed/role-builder.md`, `../../01-seed/role-d-and-c.md` - role-shaped escalation routing.
