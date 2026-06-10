# System skill: risk-register-system

**Job:** End-to-end residential risk-register workflow. Orchestrates seed loading, evidence sweep, existing-register review, residential risk seeding, row drafting, optional risk commentary, escalation surfacing, and return summary. Produces or refreshes a risk register under the active SiteWise project using `register-row-draft` for every row.

This is the **third system skill in SiteWise**, inheriting the `seed-targeted-read` -> `evidence-sweep` -> content atomics -> drafts/registers -> return-summary skeleton documented in `contract-setup-system.md §"Skill skeleton - for slices 06+ to inherit"` and repeated in `cost-plan-system.md §"Skill skeleton inheritance"`.

This skill enforces the §2 three-overlay declaration gate at its pre-flight. It enforces §register-discipline at every row boundary. It does not emit incomplete risk rows.

## When called

Called by:
- the agent when the user asks to open a residential risk register;
- the agent when the user asks to refresh or quality-check an existing risk register;
- the agent when programme, cost, procurement, approvals, site access, owner decisions, or handover evidence reveals unmanaged risk;
- system skills that need to turn gaps into risk rows rather than loose commentary;
- as a re-run at each regular risk review date or after material change.

The skill is **idempotent**. Re-running on a project with an existing risk register does not duplicate open rows. It refreshes matching rows where evidence has changed, drafts new rows where new risks are found, and closes or supersedes rows only when the project evidence supports that action.

## Caller passes

- **Active project folder path** - required.
- **Mode** - one of `open-register`, `refresh-register`, `risk-commentary`, or `quality-check`. Required unless the user's request makes it obvious.
- **Subject focus (optional)** - narrower task subject, e.g. `programme risk`, `approval risk`, `weather risk before slab`, or `owner change request risk`.
- **Review date (optional)** - ISO date for the next risk review. If missing, the skill proposes one and flags it for confirmation before row emission.

The skill reads everything else it needs from the active project folder.

## Pre-flight - Step 0: §2 declaration gate

Before any work:

1. Read the project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC` (per `../../AGENTS.md §2` and `../../00-doctrine/doctrine.md §seed-consultation-discipline`).
3. **If any is missing, blank, or `TBC`:** **stop**. Return:
   > Cannot produce or refresh a risk register: the README is missing one or more required overlay declarations. Please declare `archetype`, `user_role`, and `state` in the frontmatter before any system-skill work. Per `../../AGENTS.md §2` and `../../00-doctrine/doctrine.md §seed-consultation-discipline`, the agent does not guess these from project name, address, budget, site, or any other proxy.
4. **Do not load any seed, do not run evidence-sweep, do not draft.** The gate is binary.

The gate is enforced at the system-skill boundary and again by `../atomic/seed-targeted-read.md`.

## Steps

### Step 1 - seed-targeted-read

Invoke `../atomic/seed-targeted-read.md` with task subject `residential risk register` plus the caller's subject focus where one exists.

The skill loads:

- **Tier 2 archetype seed** - one of `new-dwelling-guide.md`, `renovation-guide.md`, `multi-dwelling-guide.md`, `ancillary-guide.md`, or `small-commercial-guide.md` per `archetype:`.
- **Tier 3 role overlay** - one of `role-builder.md`, `role-architect-pm.md`, `role-owner-builder.md`, or `role-d-and-c.md` per `user_role:`.
- **Required cross-cutting seeds**:
  - `program-scheduling-guide.md` - required because residential risks usually resolve into time, lead-time, critical-path, or inspection exposure;
  - `setup-and-commission-guide.md` - required because commissioning opens the standard risk register and identifies statutory / setup gaps.
- **Conditional topic seeds** where the evidence or subject focus signals them:
  - `cost-management-principles.md` for budget, contingency, PC sums, owner-supplied items, or variation-value risk;
  - `contract-administration-guide.md` for variation, EOT, notice, claim, or contractual risk;
  - `procurement-quoting-guide.md` when market response, subcontractor selection, or quote qualification risk is in play;
  - `sustainability-energy-guide.md` when BASIX / NatHERS commitments drive risk;
  - trade-specific seeds when available and the risk belongs to structural, MEP, civil, or finishes coordination.

For non-NSW states, the agent flags state-coverage gaps where the seeds reference NSW-specific instruments without a local callout (per `../../AGENTS.md §8`).

The loaded seed list is held for `seed_consulted:` in any risk commentary and for provenance notes on register rows.

### Step 2 - evidence-sweep

Invoke `../atomic/evidence-sweep.md` with task subject `residential risk register` or the caller's narrower subject focus.

High-relevance evidence:

- `README.md` - overlay declarations, state, planning pathway, budget, phase;
- `00-brief-pmp/` - brief, setup pack, existing risk register, owner-supplied items, ready-to-start checklist;
- `01-cost/` - cost plan, contingency, variation pricing, PC schedules;
- `02-consultant/` - consultant appointments, scope gaps, advice gaps;
- `03-design/01-due-diligence/` - survey, geotech, dilapidation, BAL, flood, heritage, contamination, services;
- `04-planning-and-authorities/` - DA/CDC/CC, BASIX, LSL, HBCF/HOW, Sydney Water, OSD, conditions of consent, utility approvals;
- `05-procurement/` - quote gaps, exclusions, long-lead items, market response;
- `06-programme/` - master programme, milestone tracker, lookahead, delay register;
- `07-construction/` - contract, insurance, management plans, claims, variations, EOTs, RFIs, inspections, commissioning, defects, photos;
- `08-meetings-reporting/` - minutes, action register, decision register, owner updates;
- `09-handover-dlp/` - PC, handover, defects, warranties, O&M, DLP.

The sweep returns:
- artefacts found and relevance;
- expected-but-missing artefacts;
- existing risk-register candidates;
- evidence gaps that prevent risk rows from being emitted.

### Step 3 - detect existing risk register

Find existing risk registers in:

- `00-brief-pmp/risk-register.md`;
- `00-brief-pmp/risk-register.xlsx`;
- `08-meetings-reporting/risk-register.md`;
- `08-meetings-reporting/risk-register.xlsx`;
- any `*risk*register*` file surfaced by `evidence-sweep`.

If more than one exists:
- identify the most recent reviewed register as the working register;
- treat older registers as evidence, not the write target;
- flag ambiguity to the user if reviewed status or recency is unclear.

If no register exists:
- default location is `00-brief-pmp/risk-register.md` for mobilisation / setup risks;
- use `08-meetings-reporting/risk-register.md` where the project has already moved into recurring reporting and the risk register is part of meeting governance;
- do not create an Excel register unless the user or project evidence indicates Excel is the register source of truth. Excel edits remain governed by `excel-safe-edit` and `excel-verify`.

### Step 4 - establish row schema

Every risk row must satisfy `../../00-doctrine/doctrine.md §register-discipline`:

| Core field | Required behaviour |
|---|---|
| ID | `R-<seq>` where sequence follows the existing register; `R-<TBD>` only in a draft gap report, not in a committed row |
| Description | One to three sentences describing the risk event and consequence |
| Owner | Single named person or role; not `Project`, `TBC`, or a committee |
| Status | One of `identified`, `mitigated`, `accepted`, `realised`, or `closed` |
| Due / review date | ISO date for next action or review |
| Source / evidence reference | Project path, meeting reference, document ID, or explicit Assumption basis |
| Next action | One imperative sentence, owned and date-bound |

Risk-register-specific columns should also be used where the destination supports them:

| Additional field | Use |
|---|---|
| Category | Residential risk category |
| Likelihood | Low / Medium / High unless project has its own scale |
| Consequence | Low / Medium / High unless project has its own scale |
| Mitigation | Existing or proposed control |
| Residual rating | Risk after mitigation |
| Date reviewed | ISO date of last review |

If any core field cannot be populated, the skill returns a gap report and does not emit that row. This is not optional.

### Step 5 - seed the residential baseline risks

Use `../atomic/register-row-draft.md` one row at a time. The minimum seed categories are:

| Category | Default risk event | Typical owner | Typical source basis | Default next action pattern |
|---|---|---|---|---|
| BAL/bushfire | BAL rating or AS 3959 construction requirement changes cost, procurement, or lockup timing | Builder or Architect-PM | BAL assessment / planning map / Assumption if not found | Confirm BAL status and flow requirements into design, procurement, and programme |
| Latent moisture | Wet substrate, frame moisture, leaks, or existing-condition moisture blocks linings, flooring, joinery, or PC | Builder | Site report / photos / moisture test / Assumption for renovation | Test moisture and update programme before lining or floor finish proceeds |
| Latent conditions (renovation) | Hidden structure, rot, termite damage, hazardous material, unauthorised prior work, or concealed waterproofing failure moves scope, cost, or approvals | Owner-builder / Builder / Architect-PM per role | Renovation due diligence / opening-up photos / Assumption if not investigated | Decide investigation, contingency, redesign, or staged opening-up before affected trade proceeds |
| Existing services (renovation) | Unknown sewer, stormwater, water, gas, electrical, NBN, solar, or HVAC services are damaged or force redesign | Owner-builder / Builder | Services locating / survey / trade observation / Assumption if not located | Locate, isolate, or pothole services before demolition, excavation, drilling, or saw-cutting |
| Neighbour dilapidation | No condition baseline exists before excavation or vibration-sensitive work | Project lead role | Dilapidation report / missing-evidence gap | Obtain or confirm dilapidation record before intrusive works |
| Structural intervention (renovation) | Wall removal, opening, underpinning, roof change, or temporary works proceeds without engineer sign-off or hold point | Owner-builder / Builder / Engineer | Structural advice / drawings / site observation | Obtain engineer direction and inspection hold point before demolition or load transfer |
| Heritage / character (renovation) | Heritage item, conservation area, character control, or streetscape constraint changes demolition, facade, approval, or programme | Owner-builder / Architect-PM | Planning certificate / council mapping / heritage advice / Assumption if not checked | Confirm heritage / character controls before design lock or demolition |
| Tight-block site access | Restricted access slows deliveries, spoil removal, craneage, scaffold, or trade overlap | Builder | Survey / CMP / TMP / site observation | Confirm delivery, staging, and access plan against next four-week lookahead |
| Owner change requests | Owner decisions or late selections disrupt procurement, PC sums, trade sequence, or variations | Owner or Builder depending role | Meeting minutes / variation register / selection schedule | Issue decision request or variation pathway before affected trade starts |
| Live-occupancy staging (renovation) | Owner remains in occupation and temporary services, access, dust, safety, security, or weatherproofing are not controlled | Owner-builder / Builder | Staging plan / site observation / Assumption if occupied | Confirm live-occupancy staging and safety controls before disruptive works |
| Waterproofing / tie-ins (renovation) | Old-to-new junctions, wet areas, roof tie-ins, balconies, or drainage falls fail or block inspection | Owner-builder / Builder | Details / inspection record / photos / Assumption if not detailed | Confirm waterproofing and tie-in hold points before covering work |
| Weather | Rain, heat, wind, or shutdown periods threaten external, slab, roof, or painting activities | Builder | Programme calendar / site diary / weather allowance | Update programme allowance and record contemporaneous weather evidence |
| Materials lead time | Long-lead items threaten lockup, fixing, completion, or BASIX/NatHERS compliance | Builder | Quote / purchase order / supplier commitment | Confirm order date, delivery date, and substitution pathway |
| Subcontractor no-show | Trade fails to mobilise or return, removing workface from the lookahead | Builder | Lookahead / subcontractor register / site diary | Confirm replacement plan or written recommitment before successor trade is affected |
| Multi-dwelling classification | Class 1a attached dwelling vs Class 2 classification is unresolved, moving NCC, approval, consultant, accessibility, fire, energy, or handover requirements | D&C / Architect-PM / Builder per role | Approval pathway, certifier advice, drawings, Assumption if not checked | Confirm classification and update design, approval, programme, and cost registers before design release or site start |
| Party-wall / fire separation | Party-wall continuity, penetrations, cavity barriers, fire-stopping, acoustic treatment, or inspection hold points are under-scoped | D&C / Builder | Architectural, structural, fire, acoustic, and certifier evidence / Assumption if not detailed | Confirm party-wall strategy and first-of-type inspection hold point before framing or services penetrations proceed |
| Separate metering / utilities | Per-dwelling water, electrical, gas, communications, sewer, stormwater, or meter-board strategy is missing or late | D&C / Builder | Services design, utility applications, authority correspondence / Assumption if not found | Confirm metering and utility application path before rough-in procurement or switchboard / services works proceed |
| Infrastructure contributions / authorities | Council, water, sewer, drainage, OSD, crossover, waste, street tree, or public-domain requirements are unpriced or unscheduled | D&C / Architect-PM / Builder per role | Consent conditions, authority correspondence, cost plan / Assumption if not found | Confirm contribution and authority requirements and add cost / programme actions before commencement or relevant hold point |
| Staging / OC / subdivision | Staged occupation, subdivision, strata, settlement, access, defects, or DLP assumptions do not match approval and contract evidence | D&C / Architect-PM / Builder per role | Programme, approval conditions, contract, staging plan / Assumption if not found | Confirm staged OC / subdivision / handover path and update programme, risk, and decision registers before sequencing is locked |
| D&C design responsibility | Design responsibility matrix, design deliverables register, certifier submission status, or design RFI path is missing or stale | D&C | DRM, design programme, deliverables register, RFI register / missing-evidence gap | Refresh the design responsibility matrix and open design actions before affected package release or site work proceeds |
| D&C PI / consultant scope | D&C PI, consultant PI, consultant appointment, novation, or scope boundary evidence is missing or inconsistent with design responsibility | D&C | Insurance certificates, consultant appointments, novation deeds, scope schedules / missing-evidence gap | Confirm PI and consultant scope coverage before relying on consultant output or submitting design to certifier |

Common optional categories:
- certifier / BPA inspection availability;
- utility connection delay;
- BASIX / NatHERS substitution;
- OSD / stormwater hold point;
- contract execution / insurance / HBCF / LSL setup gap;
- cost-plan contingency depletion;
- variation worked before written approval;
- EOT notice missed or late;
- defects close-out drift.

Do not seed a category just to fill a table. A seeded risk row needs evidence, owner, review date, and next action.

For `user_role: owner-builder`, any risk whose next action is really "owner-builder must choose" should also draft or refresh a `Park-for-decision queue` row using `register-row-draft`. The risk row tracks exposure; the park-for-decision row tracks the self-decision. If that row is `due` or `overdue`, it is an escalation, not a quiet action-list item.

### Step 6 - deduplicate and refresh existing rows

When an existing risk register is found:

1. Compare proposed rows against existing open rows by category, description, owner, source, and next action.
2. If a proposed row materially matches an open row, refresh the existing row rather than drafting a duplicate.
3. If the risk event has changed materially, draft a superseding row or update note according to the project's register convention.
4. If evidence shows the risk is now realised, change proposed status to `realised` and route to the appropriate system (variation, EOT, defect, claim, or action register).
5. If evidence shows the risk has closed, draft the closure row/update with source and "none - row closed" as next action.

The skill must preserve the audit trail. It does not delete old risk rows.

### Step 7 - draft register output

For markdown destination:
- use a table with the seven core fields plus the risk-specific columns;
- keep descriptions concise;
- include a short provenance note after the table where useful.

Reference header:

```markdown
| ID | Category | Description | Owner | Status | Due / review date | Source | Next action | Likelihood | Consequence | Mitigation | Residual rating | Date reviewed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
```

For Excel destination:
- do not edit directly in this skill;
- require an approved markdown source first;
- route the approved edit through `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md`.

For `quality-check` mode:
- do not rewrite the register;
- return a defect list against §register-discipline: missing IDs, duplicate IDs, missing owner, invalid status, missing review date, missing source, vague next action, no mitigation, stale review date, high risk without escalation.

### Step 8 - optional risk commentary

When the user asks for a summary, monthly report section, PMP risk section, or owner-facing update, draft narrative through `../atomic/markdown-draft-for-review.md`.

Use contractual voice for:
- `00-brief-pmp/risk-register*`;
- `06-programme/**` risk commentary;
- monthly governance reports where the audience is project-control or contract administration;
- EOT, variation, claim, or formal-notice support.

Use stakeholder voice for:
- `08-meetings-reporting/owner-risk*`;
- `08-meetings-reporting/*owner*risk*`;
- owner-facing monthly summaries.

Required commentary sections:
- top risks by residual rating;
- new risks since last review;
- risks realised since last review;
- decisions required;
- next review date;
- assumptions and evidence gaps.

### Step 9 - surface escalations

Surface explicitly:

- any high residual risk;
- any risk that threatens the critical path or next four-week lookahead;
- any owner decision blocking procurement, programme, or variation approval;
- any missing statutory, authority, or insurance evidence blocking start, CC/building permit, PC, OC, or handover;
- for `user_role: d-and-c`, any missing or stale DRM, design deliverables register, design programme, consultant appointment / novation, D&C PI, consultant PI, or certifier submission path;
- for `archetype: multi-dwelling`, any unresolved classification, party-wall / fire separation, separate metering / utilities, infrastructure contribution, authority condition, staging, OC, subdivision, or strata pathway;
- any repeated subcontractor failure;
- any risk that has become a variation, EOT, progress claim, defect, or formal notice issue;
- any stale risk review date.
- for `user_role: owner-builder`, any `Park-for-decision queue` row with status `due` or `overdue`, especially where it blocks trade award, demolition, structural intervention, BASIX compliance, insurance cover, or contingency use.

Escalation routing follows the role overlay loaded at Step 1 and `../../00-doctrine/doctrine.md §escalation-triggers`. Route each escalation through `escalation-note-system.md` and report the trigger, route and recommended action in the return summary.

### Step 10 - return summary

Return a short summary to the user:

- mode used;
- seeds loaded and recorded;
- evidence consulted;
- register target and whether it was opened, refreshed, checked, or commentary-only;
- rows drafted, refreshed, blocked by gaps, realised, or closed;
- unresolved gaps;
- escalations surfaced;
- next review date.

## Rule

This skill is the canonical risk-register entry point for SiteWise.

It **does not emit incomplete rows**. If ID, description, owner, status, due/review date, source, or next action is missing, the output is a gap report until the missing field is supplied or evidenced.

It **does not treat the existing risk register as the only source of truth**. The register is checked against current project evidence from `evidence-sweep`.

It **does not sign off risk acceptance**. Accepting a risk is a human decision and should be supported by a decision-register row where material.

It **does not edit Excel registers directly**. Excel edits route through `excel-safe-edit` and `excel-verify` after approved markdown.

It respects `../../AGENTS.md §11` active-project boundary and operates only within the active project folder.

## Skill skeleton inheritance

This skill inherits the SiteWise system-skill skeleton:

1. Pre-flight: §2 declaration gate.
2. Step 1: `seed-targeted-read` with task subject.
3. Step 2: `evidence-sweep` with task subject.
4. Steps 3 to N: content-specific atomics and drafting.
5. Step N+1: surface gaps and escalations.
6. Step N+2: return summary.

Slice 06's `progress-claim-assessment-system` and `variation-management-system`, and slice 13's `handover-pc-system`, consume risks that become claims, variations, EOTs, defects, or handover blockers.

## See also

- `../../AGENTS.md §1` - authority stack
- `../../AGENTS.md §2` - declaration gate
- `../../AGENTS.md §3` - seed loading rules
- `../../AGENTS.md §5` - output discipline
- `../../AGENTS.md §6` - voice register
- `../../AGENTS.md §8` - state callouts
- `../../AGENTS.md §9` - skill invocation
- `../../AGENTS.md §11` - active-project boundary
- `../../00-doctrine/doctrine.md §seed-consultation-discipline`
- `../../00-doctrine/doctrine.md §evidence-discipline`
- `../../00-doctrine/doctrine.md §register-discipline`
- `../../00-doctrine/doctrine.md §decision-discipline`
- `../../00-doctrine/doctrine.md §escalation-triggers`
- `../../00-doctrine/doctrine.md §voice-and-style`
- `../../00-doctrine/doctrine.md §owner-communication`
- `../../01-seed/program-scheduling-guide.md` - programme, lead-time, and risk triggers
- `../../01-seed/setup-and-commission-guide.md` - standard register opening and setup gaps
- `../../01-seed/new-dwelling-guide.md` or other Tier 2 archetype seed - archetype-specific risk posture
- `../../01-seed/role-builder.md` or other Tier 3 role overlay - role-specific ownership and escalation
- `../../01-seed/cost-management-principles.md` - cost, contingency, PC sum, and owner-supplied item risk
- `../../01-seed/contract-administration-guide.md` - variation, EOT, notice, claim, and clause-citation risk
- `../atomic/seed-targeted-read.md` - loaded at Step 1
- `../atomic/evidence-sweep.md` - loaded at Step 2
- `../atomic/register-row-draft.md` - used for every risk row
- `../atomic/markdown-draft-for-review.md` - used for risk commentary
- `../atomic/excel-safe-edit.md` and `../atomic/excel-verify.md` - used only after approved markdown where the risk register is Excel
- `contract-setup-system.md` - first SiteWise system skill and skeleton source
- `cost-plan-system.md` - second SiteWise system skill and skeleton precedent
