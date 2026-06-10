# System skill: variation-management-system

**Job:** End-to-end residential variation management workflow. Orchestrates the Sec. 2 declaration gate, seed loading, evidence sweep, contract clause check, written-direction gate, scope / cost / time assessment, owner or Principal sign-off gate, register-row drafting, EOT support, owner communication split, and return summary into one workflow. Produces draft variation outputs under `07-construction/06-variations/` with contractual register.

This skill inherits the same system-skill skeleton used by `contract-setup-system.md`, `cost-plan-system.md`, `risk-register-system.md`, `procurement-evaluation-system.md`, and the sibling `progress-claim-assessment-system.md`: declaration gate -> `seed-targeted-read` -> `evidence-sweep` -> content-specific assessment -> `markdown-draft-for-review` and `register-row-draft` -> gaps and escalations -> return summary.

The core discipline is simple and hard-edged: written direction, defined scope, priced cost impact, assessed time impact, and owner / Principal sign-off before work begins. If work has already started on a verbal or unsigned variation, the skill treats it as a regularisation problem with evidentiary weakness. It does not pretend the workflow was compliant.

## When called

Called by:
- the agent when the user asks to draft, assess, price, register, regularise, or explain a variation;
- the agent when an owner request, RFI response, consultant instruction, authority condition, BASIX / NCC change, latent condition, PC sum reconciliation, or subcontractor claim may change scope, cost, or time;
- the agent when a variation has time impact and may require EOT support;
- as a re-run when new price, sign-off, programme, or evidence arrives.

The skill is **idempotent**. Re-running on a project with an existing variation draft does not overwrite reviewed records. It produces `variation-<seq-or-slug>-v<NN+1>.md` or a new draft, and uses supersede behaviour only through `markdown-draft-for-review` when explicitly requested.

## Caller passes

- **Active project folder path** - required.
- **Variation reference** - optional at first intake; required once a register row is proposed. May be a variation number, RFI reference, email subject, drawing revision, PC reconciliation item, or subcontractor reference.
- **Mode** - one of:
  - `advice-only` - conversation summary only, no draft file;
  - `markdown-only` - draft variation assessment to `07-construction/06-variations/`;
  - `markdown-then-notice` - variation draft plus EOT notice, RFI, evidence request, or owner explanation where triggered. The human reviews and issues.
- **Variation posture** - optional: `pre-work`, `work-started`, `work-complete`, `subcontractor-variation`, `PC-reconciliation`, `owner-supplied-change`, `latent-condition`, `compliance-change`. If ambiguous, classify from evidence and ask where needed.

The skill reads the active project evidence for everything else.

## Pre-flight - Step 0: Sec. 2 declaration gate

Before any work:

1. Read the active project `README.md` frontmatter.
2. Confirm `archetype`, `user_role`, and `state` are declared and not missing, blank, or `TBC` per `../../AGENTS.md Sec. 2` and `../../00-doctrine/doctrine.md Sec. seed-consultation-discipline`.
3. **If any is missing, blank, or `TBC`:** stop. Return:
   > Cannot manage a variation: the README is missing one or more required overlay declarations. Please declare `archetype`, `user_role`, and `state` in the frontmatter before variation management. Per `../../AGENTS.md Sec. 2` and `../../00-doctrine/doctrine.md Sec. seed-consultation-discipline`, the agent does not guess these from project name, address, budget, site, or any other proxy.
4. Do not load seeds, run evidence-sweep, draft, or recommend sign-off until the gate passes.

The gate is checked here and again by `seed-targeted-read`. The redundancy is intentional. Variation management is phase-gate contract administration under `../../AGENTS.md Sec. 9`.

## Steps

### Step 1 - seed-targeted-read

Invoke `../atomic/seed-targeted-read.md` with task subject `residential variation management`.

The skill loads:

- **Tier 2 archetype seed** - one of `new-dwelling-guide.md`, `renovation-guide.md`, `multi-dwelling-guide.md`, `ancillary-guide.md`, or `small-commercial-guide.md` per `archetype:`.
- **Tier 3 role overlay** - one of `role-owner-builder.md`, `role-architect-pm.md`, `role-builder.md`, or `role-d-and-c.md` per `user_role:`.
- **Cross-cutting topic seeds**:
  - `contract-administration-guide.md` - required for variation, instruction, notice, EOT, time bar, clause-citation, and contract family discipline.
  - `cost-management-principles.md` - required for HIA Schedule of Variations, cost impact, PC sums, signed variations, cost-plan reconciliation, GST, and margin posture.
  - `program-scheduling-guide.md` - required where time impact, trade cascade, critical path, EOT, or resequencing is live.
- **Optional cross-cutting seeds** where evidence points to them:
  - `procurement-quoting-guide.md` if the variation arises from trade quote scope gaps, subcontractor award qualifications, or schedule-of-rates pricing.
  - `sustainability-energy-guide.md` where BASIX / NatHERS / energy compliance changes are live (slice 12, when present).
  - `as-standards-reference.md`, `structural-residential.md`, `mep-residential.md`, `civil-residential.md`, or `finishes-residential.md` where a technical trade seed exists and the variation turns on that technical scope.

For non-NSW states, flag state-coverage gaps where the loaded seeds rely on NSW-specific HIA, HBCF, LSL, BASIX, or Security of Payment assumptions without a state callout. Do not silently extend NSW guidance.

Hold the loaded seed list for `seed_consulted:` frontmatter on every draft this skill produces.

### Step 2 - evidence-sweep

Invoke `../atomic/evidence-sweep.md` with task subject `residential variation management for <variation reference or topic>`.

High-relevance evidence:

- active project README frontmatter;
- executed head contract, subcontract, special conditions, and variation clause;
- contract summary in `00-brief-pmp/contract-summary.md`, if already drafted;
- owner / Principal direction, site instruction, consultant instruction, RFI response, addendum, authority direction, drawing revision, or meeting decision that triggered the variation;
- existing variation register and signed variation forms in `07-construction/06-variations/`;
- cost plan, cost register, PC schedule, owner-supplied items register, and current contract value;
- schedule of rates, quote, subcontractor price, supplier price, labour / material build-up, and margin basis;
- programme, lookahead, critical-path commentary, EOT register, and delay records;
- for D&C design changes, the PPR / design brief, design responsibility matrix, design deliverables register, design programme, consultant appointment / novation evidence, consultant advice, and certifier submission status;
- relevant RFIs and notices in `07-construction/08-rfi-notices/`;
- photos, inspection records, conformance certificates, authority / certifier records, BASIX / NCC evidence;
- procurement records where the variation comes from a quote qualification or scope gap;
- owner-facing decision records in `08-meetings-reporting/decision-register.md` or owner update drafts.

Medium-relevance evidence:

- design drawings and specifications that establish the original scope;
- risk register rows related to latent conditions, compliance, or owner change;
- subcontractor register and trade package award basis;
- defect records where a proposed change is actually defect rectification.

The sweep returns a relevance-ranked inventory and a gap report. Gaps become stop conditions, draft qualifications, action rows, RFIs, or owner decision requests.

### Step 3 - Identify variation role, contract family, and posture

Classify:

| Question | Required classification |
|---|---|
| Direction source | owner / Principal, architect-PM, Superintendent, consultant, certifier / authority, builder-initiated, subcontractor-initiated, latent condition, PC reconciliation, owner-supplied change |
| Contract family | HIA Lump Sum, HIA Renovation, HIA Cost Plus, HIA Trade, MBA equivalent, NSW Fair Trading prescribed, AS 4000, AS 4902, ABIC, other |
| Role pathway | builder issuing to owner, builder assessing subcontractor, architect-PM advising owner, owner-builder self-signing / paying trade, D&C carrying design and construction |
| Timing posture | pre-work, work-started, work-complete, disputed, regularisation |
| Change category | scope, cost only, time only, scope + cost + time, compliance, latent condition, PC sum, owner-supplied, defect / rectification, clarification only |

If classification is ambiguous, ask before drafting a sign-off-ready variation. Do not assume a variation exists just because the user says "change"; some changes are RFIs, defects, substitutions, PC reconciliations, or owner decisions that become variations only after the contract mechanism says so.

### Step 4 - Contract evidence gate

Before any clause-cited variation assessment:

1. Confirm the executed contract or subcontract is available.
2. Confirm special conditions affecting variations, directions, EOT, margin, GST, time bars, notices, latent conditions, or PC sums have been read.
3. Confirm the variation / direction / EOT clause text needed for the assessment is available.
4. Confirm the original scope baseline is available enough to show what changed.

If any required clause text is missing, stop. Return:

> Cannot produce a clause-cited variation assessment yet: the executed contract, special condition, variation clause, or original scope baseline is missing from project evidence. I can describe the generic residential mechanism from the seeds, but I cannot draft a project-specific variation, EOT notice, or sign-off recommendation until the executed clause text and scope baseline are available.

The generic explanation may be `advice-only` and must be labelled as general guidance. It must not become a project-specific draft.

### Step 5 - Classify the variation type

Classify into one primary type and any secondary tags:

| Type | Required treatment |
|---|---|
| Owner-directed scope change | Written owner direction or owner sign-off required before work |
| Consultant / RFI-driven change | Verify authority of the consultant response and whether owner sign-off is still required |
| Latent condition | Read latent condition clause, stop-work / notice requirement, and owner direction path |
| Authority / certifier compliance change | Confirm regulatory source, effect on scope, effect on programme, owner decision path |
| BASIX / NCC substitution | Confirm current certificate / compliance method, required reassessment, approval path |
| D&C design development | Test against the PPR / design brief, accepted design baseline, DRM, consultant scope, certifier submission status, and owner change evidence before treating it as a variation |
| PC sum reconciliation | Compare allowance, actual, margin, GST, and contract PC mechanism |
| Owner-supplied item change | Check programme delivery risk, warranty split, insurance, installation cost |
| Subcontractor variation | Assess under subcontract; decide whether it passes through to head contract |
| Quote / procurement scope gap | Link to procurement evidence and decide whether the gap is contractor risk or owner variation |
| Post-work / verbal change | Treat as regularisation with explicit evidentiary weakness |
| Defect rectification | Do not treat as a payable variation unless contract evidence proves changed scope rather than correction |

Classification must be recorded in the draft and in any register row.

### Step 6 - Apply variation control gates

Prepare a gate table:

| Gate | Pass condition | Failure handling |
|---|---|---|
| Written direction | Direction, RFI response, owner instruction, or administrator direction exists in writing | Stop if work has not started; request written direction |
| Scope defined | Inclusions, exclusions, affected drawings/specs/trades are clear | Draft RFI / scope clarification |
| Cost impact priced | Labour, material, subcontract, margin, GST, PC reconciliation, or SOR basis stated | Draft pricing request / hold sign-off |
| Time impact assessed | Direct duration and trade cascade / critical-path effect considered | Load programme evidence; draft EOT support if needed |
| Owner / Principal sign-off | Correct decision-maker signs before work starts | Stop before instruction to proceed |
| Cost-plan impact | Contract value, contingency, PC schedule, or forecast impact recorded | Draft cost register / cost-plan update action |
| Programme impact | Master programme, lookahead, EOT register, or milestone impact recorded | Draft programme / EOT / action row |
| Compliance impact | BASIX / NCC / authority / certifier implications checked | Draft RFI / authority action |

Outcomes:

- **All gates pass** - variation can be recommended for human sign-off / issue.
- **Pre-work, gates fail** - do not draft an instruction to proceed. Draft an evidence request, RFI, or owner decision request.
- **Work started / complete, gates fail** - draft a regularisation note. Label evidentiary weakness and dispute risk.

### Step 7 - Assess cost impact

Cost assessment must include:

- original scope baseline;
- changed scope;
- pricing basis: lump sum, schedule of rates, PC allowance reconciliation, cost-plus, subcontract quote, supplier price, or judgement estimate;
- labour, material, plant, subcontract, preliminaries, supervision, design / consultant fees where relevant;
- builder's margin, subcontract margin, or contract margin clause;
- GST basis;
- credits as well as additions;
- contingency impact;
- signed variation total to date and cumulative variation total after this variation, where available.

Rules:

- A variation that is not signed is pending / forecast only. It does not move current contract value.
- For `user_role: d-and-c`, design development inside the accepted PPR / design brief, contract scope, and DRM allocation is not automatically a variation. Price it as a variation only where the executed contract, owner / Principal direction, authority change, accepted baseline, consultant advice, or scope boundary shows changed entitlement.
- PC sum reconciliation must show allowance, actual, margin treatment, and net adjustment.
- Owner-supplied item changes must not be double-counted as PC sums.
- BASIX / compliance variations must include the cost of reassessment or substitute approval where needed.
- Cost estimates without quotes are Assumptions or Judgements, not Facts.

If the variation affects the cost plan or workbook, draft a markdown action or cost-register row. Do not edit a workbook from this skill. Workbook changes route through `cost-plan-system.md` and the Excel atomics after review.

### Step 8 - Assess time impact and EOT relationship

Time assessment must include:

- direct duration of the changed work;
- impact on the next affected trade;
- lead time for materials or consultant / authority response;
- whether the impact touches the critical path;
- whether an EOT notice is required;
- whether the contract's notice window may be running;
- whether the time impact should be recorded as calendar days, working days, or contract-defined days.

Rules:

- Do not record only direct work duration where the trade cascade is material.
- A variation can have zero cost and time impact, cost only, time only, or both.
- Time impact is not automatically an EOT entitlement. The executed contract decides.
- If EOT support is needed and clause text is available, draft the EOT notice / support note per Step 12.
- If EOT clause text is unavailable, stop and ask before drafting a clause-cited notice.

### Step 9 - Draft the variation assessment

For `markdown-only` and `markdown-then-notice`, invoke `../atomic/markdown-draft-for-review.md` with:

- **Target folder** - `07-construction/06-variations/`;
- **Target filename** - `variation-<seq-or-slug>-v<NN>.md`;
- **Asserted voice** - `contractual`;
- **Seed list consulted** - the seeds loaded at Step 1;
- **Evidence references** - evidence from Step 2 used in the assessment.

Required sections:

1. **Project and variation header** - project slug, variation reference, source, contract family, timing posture, date, status draft.
2. **Source evidence used** - evidence list with paths and relevance.
3. **Contract mechanism and clause excerpts** - contract form, variation clause, direction clause, margin / GST basis, EOT clause where relevant.
4. **Direction source** - who directed, when, by what evidence, and whether they had authority.
5. **Original scope baseline** - drawings, specification, contract item, PC allowance, subcontract scope, or RFI baseline.
6. **Changed scope** - inclusions, exclusions, affected trades, affected documents.
7. **Variation type and gate table** - written direction, scope, cost, time, sign-off, cost-plan, programme, compliance.
8. **Cost impact** - priced build-up, margin, GST, credits, cumulative variation position.
9. **Time impact** - direct duration, trade cascade, critical path, EOT support requirement.
10. **Compliance / BASIX / authority impact** - where applicable.
11. **Recommendation** - sign, hold, request evidence, reject, regularise, or escalate.
12. **Register rows proposed** - variation row and linked rows.
13. **Owner communication / notice drafts** - where mode is `markdown-then-notice`.
14. **Open gaps and next action** - exact owner and due date.

The draft remains `status: draft`. The agent does not sign, issue, approve, reject, or direct work to proceed.

### Step 10 - Draft variation register row

Use `../atomic/register-row-draft.md` with register type `Variation register`.

Required core fields:

- ID;
- description;
- owner;
- status;
- due date;
- source / evidence reference;
- next action.

Required variation-specific columns:

- cost;
- time impact in days;
- date proposed;
- date owner-signed / Principal-signed;
- date completed;
- cumulative variation total where available.

Status vocabulary:

- `proposed` - scope identified, not yet fully priced or signed;
- `priced` - cost and time stated, awaiting sign-off;
- `owner-signed` - signed and can proceed under the contract;
- `in-progress` - work underway after sign-off;
- `completed` - work complete and cost incorporated into the contract record;
- `disputed` - entitlement, price, or time impact disputed;
- `withdrawn` - no longer proceeding.

Do not mark `owner-signed` unless the signed evidence exists.

### Step 11 - Draft linked register rows

Use `register-row-draft` for linked rows:

- **Cost register** - when the signed variation changes contract value or forecast.
- **Action register** - when evidence, pricing, sign-off, or technical clarification is missing.
- **Decision register** - when the owner / Principal chooses to proceed, reject, or accept residual risk.
- **RFI register** - when a technical answer is needed.
- **EOT register** - when time relief is claimed or likely.
- **Risk register** - when residual or repeated variation risk remains.
- **Owner-supplied items register** - where owner supply changes delivery or installation.
- **Contractual notices register** - where a formal notice is required.

Each row must satisfy the seven-field schema. Do not create rows with `TBC` owner, due date, source, or next action.

### Step 12 - EOT notice and contractual notice support

When the variation or underlying event creates a time impact that may require an EOT notice:

1. Confirm the executed EOT clause text is available.
2. Confirm the notification window, qualifying event wording, and recipient / delivery method.
3. Confirm contemporaneous evidence exists: direction, RFI, weather / authority / owner delay evidence, programme excerpt, dated photos, correspondence.
4. Draft an EOT notice or EOT-supporting note through `markdown-draft-for-review` to either:
   - `07-construction/07-programme-eot/eot-notice-<event>-v<NN>.md`; or
   - `07-construction/08-rfi-notices/notice-eot-<event>-v<NN>.md` where the project's notice convention keeps formal notices there.
5. Assert voice `contractual`.
6. Quote the executed HIA / MBA / AS / ABIC clause text verbatim where relied on.

If clause text is unavailable, stop and ask. Do not use generic HIA wording for a project-specific EOT notice.

For payment dispute, latent condition, suspension, or direction notices triggered by the variation, follow the same clause-text gate and contractual-register treatment.

### Step 13 - Owner communication split

The formal variation form / assessment stays in contractual register under `07-construction/06-variations/`.

If the owner needs a plain-English explanation, draft a separate stakeholder-register note via `markdown-draft-for-review`, typically under `08-meetings-reporting/owner-update*` or another owner-facing destination whose voice table allows stakeholder register.

Use `../../00-doctrine/doctrine.md Sec. owner-communication`:

1. What this means for you.
2. What we need from you.
3. What's happened.
4. What's next.
5. Background detail.

The owner note may reference the formal variation draft. It must not replace the signed variation form or formal notice.

### Step 14 - Surface gaps and escalations

Surface all gaps and escalation triggers. Common triggers:

- variation work has started before signed direction;
- owner / Principal direction is verbal only;
- scope baseline is unclear;
- cost is unpriced, or margin / GST basis is unclear;
- time impact omitted or direct duration only;
- critical path may move;
- EOT notice window is running or already missed;
- BASIX / NCC / authority compliance changes are unevidenced;
- D&C design baseline, DRM responsibility, consultant scope, or certifier submission status is unclear;
- PC sum reconciliation would materially move the budget;
- owner-supplied item change creates programme or warranty risk;
- subcontractor variation is being passed through without head-contract entitlement;
- signed variation register and cost plan no longer reconcile;
- repeated small variations are accumulating into material cost risk.

Escalation routing follows the loaded role overlay:

- `builder` - owner or owner's representative under contract; technical questions to consultant / engineer; formal notices via `07-construction/08-rfi-notices/`.
- `architect-pm` - owner-facing recommendation with formal advice record.
- `owner-builder` - self-flag decision log and trade response.
- `d-and-c` - as builder, plus design-side escalation to the certifier, responsible consultant, owner, or PI insurer where compliance, PPR choice, consultant scope, or design liability is live.

Route each escalation through `escalation-note-system.md` and report the trigger, route and recommended action in the return summary.

The agent must not suppress an escalation trigger. Per `../../00-doctrine/doctrine.md Sec. escalation-triggers`.

### Step 15 - Return summary

Return:

- mode used;
- variation reference, type, and contract family;
- timing posture: pre-work, work-started, work-complete, disputed, or regularisation;
- seeds loaded and `seed_consulted:` list used in drafts;
- evidence found and evidence gaps;
- gate status: written direction, scope, cost, time, sign-off, cost-plan, programme, compliance;
- cost impact and GST basis;
- time impact and EOT need;
- recommendation;
- drafts produced;
- register rows proposed;
- escalations surfaced;
- next action, owner, and due date.

## Rule

This skill is the canonical SiteWise entry point for residential variation management. Other manual paths are valid, but they lose the discipline this skill enforces: Sec. 2 gate, seed consultation, executed-contract clause check, evidence sweep, written-direction gate, cost and time assessment, owner sign-off gate, register rows, draft-only output, folder-driven contractual voice, owner communication split, and active-project boundary.

This skill **does not sign, issue, approve, reject, or direct work to proceed**. It drafts variation assessments, sign-off packs, register rows, notices, and owner notes for human review.

This skill **does not edit source-of-truth contracts or workbooks**. Workbook updates route through `cost-plan-system.md` and the Excel atomics after reviewed markdown approval.

This skill **does not turn defects into payable variations** unless project evidence proves changed scope rather than correction.

This skill **respects `../../AGENTS.md Sec. 11` active-project boundary**. It reads and writes only inside the active project folder.

## Skill skeleton inheritance

This skill inherits the slice-06+ skeleton:

1. Pre-flight: Sec. 2 declaration gate.
2. Step 1: `seed-targeted-read` with task subject.
3. Step 2: `evidence-sweep` with task subject.
4. Steps 3-13: variation classification, contract evidence gate, gate assessment, drafting, register rows, EOT / notice support, owner communication split.
5. Step 14: surface gaps and escalations.
6. Step 15: return summary.

The sibling `progress-claim-assessment-system.md` uses the same skeleton for claims. `handover-pc-system.md` in slice 13 will consume signed variation totals, defect status, and final claim context; this skill does not become the handover system.

## See also

- `../../AGENTS.md Sec. 1` (authority stack), `Sec. 2` (declaration gate), `Sec. 3` (seed loading rules), `Sec. 5` (output discipline), `Sec. 6` (voice register), `Sec. 8` (state handling), `Sec. 9` (skill invocation), `Sec. 11` (active-project boundary)
- `../../00-doctrine/doctrine.md Sec. seed-consultation-discipline`, `Sec. evidence-discipline`, `Sec. register-discipline`, `Sec. decision-discipline`, `Sec. escalation-triggers`, `Sec. voice-and-style`, `Sec. owner-communication`
- `../../01-seed/role-builder.md` - builder-side variation issuance, owner communication, EOT posture, and subcontractor management
- `../../01-seed/contract-administration-guide.md` - variation clause discipline, written directions, EOT, notices, time bars, contract family differences
- `../../01-seed/cost-management-principles.md` - HIA Schedule of Variations, PC sums, signed variations, cost-plan reconciliation, GST, margin posture
- `../../01-seed/program-scheduling-guide.md` - time impact, trade cascade, EOT-supporting programme updates
- `../../01-seed/procurement-quoting-guide.md` - subcontractor quote qualifications, SOR, and scope-gap risk where procurement evidence drives the variation
- `../../01-seed/new-dwelling-guide.md` or other Tier 2 archetype seed per `archetype:`
- `../atomic/seed-targeted-read.md` - loaded at Step 1
- `../atomic/evidence-sweep.md` - loaded at Step 2
- `../atomic/markdown-draft-for-review.md` - used for variation assessments, EOT notices, and owner notes
- `../atomic/register-row-draft.md` - used for variation, cost, EOT, action, decision, RFI, risk, owner-supplied, and notice rows
- `contract-setup-system.md` - opens the variation and EOT registers and records contract mechanisms
- `cost-plan-system.md` - consumes signed variation totals and updates cost position after review
- `progress-claim-assessment-system.md` - sibling system for claims, including claims that include unsigned variation content
- `risk-register-system.md` - consumes repeated or material variation risks
- (Slice 13) `handover-pc-system.md` - future system for PC, OC, defects, DLP, signed variation totals, and final claim packaging
